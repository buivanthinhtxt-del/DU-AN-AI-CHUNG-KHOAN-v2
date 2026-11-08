"""
Bộ phân tích đầu tư AI (v3).

Luồng xử lý:
1. build_analysis_context(): gom dữ liệu THẬT (giá, VN-Index/VN30, ngành, bảng giá & khối ngoại, hồ sơ DN,
   BCTC, tra cứu web có nguồn, tin tức) + hồ sơ định lượng do quant_engine tính → đánh giá chất lượng dữ liệu.
2. build_user_prompt(): điền vào mẫu PHẦN B của prompts/tro_ly_dau_tu_chung_khoan_vn.md.
3. Gọi Gemini (Structured Output, failover nhiều model qua llm_client).
4. _postprocess(): kiểm tra nhất quán (cắt lỗ < vùng mua < mục tiêu, R:R tính lại, xác suất = 100, dự báo trong dải 95%,
   độ tin cậy ≤ mức trần chất lượng dữ liệu, quy tắc phủ quyết rủi ro) và ghi rõ mọi điều chỉnh.
5. Không gọi được AI → _rule_based_report(): báo cáo định lượng đầy đủ từ cùng bộ dữ liệu (không còn bản "sơ sài").
"""
from __future__ import annotations

import json
import logging
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

import pandas as pd
from pydantic import BaseModel, Field, ValidationError, model_validator

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import llm_client  # noqa: E402
import quant_engine as qe  # noqa: E402
from data_fetcher import calculate_indicators, get_stock_sector  # noqa: E402
from fundamental_fetcher import format_company_dossier  # noqa: E402
from data_sources import get_source_info  # noqa: E402

logger = logging.getLogger("ai_analyzer")

PROMPT_FILE = BASE_DIR / "prompts" / "tro_ly_dau_tu_chung_khoan_vn.md"
MARKET_INDICES = ("VNINDEX", "VN30")
VN_TZ = timezone(timedelta(hours=7))
FALLBACK_MARKER = "Chế độ Phân tích Định lượng Tự động"

HORIZONS = {
    "Lướt sóng (1–4 tuần)": (0.20, 0.10, 0.30, 0.25, 0.15),
    "Swing (1–3 tháng)": (0.20, 0.20, 0.25, 0.20, 0.15),
    "Trung hạn (3–12 tháng)": (0.20, 0.30, 0.20, 0.15, 0.15),
    "Dài hạn (> 1 năm)": (0.15, 0.45, 0.15, 0.10, 0.15),
}
DEFAULT_HORIZON = "Swing (1–3 tháng)"
CONF_ORDER = {"Thấp": 0, "Trung bình": 1, "Cao": 2}
ACTIONS = ["Mua", "Mua thăm dò", "Nắm giữ", "Quan sát", "Hạ tỷ trọng", "Bán / Đứng ngoài"]


# ==============================================================================================
# SCHEMA đầu ra (thứ tự trường = thứ tự model sinh: phân tích trước, chấm điểm sau)
# ==============================================================================================
class ScoreDimension(BaseModel):
    score: int = Field(default=50, description="Điểm 0–100 theo thang: 80+ vượt trội, 60–79 tích cực, 40–59 trung tính, 20–39 tiêu cực, <20 rất xấu.")
    reason: str = Field(default="", description="Lý do chấm điểm 1–2 câu, BẮT BUỘC trích số liệu cụ thể.")


class FiveDimensionScores(BaseModel):
    macro_industry: ScoreDimension = Field(default_factory=ScoreDimension, description="Thời tiết thị trường & vị thế ngành.")
    fundamentals_catalyst: ScoreDimension = Field(default_factory=ScoreDimension, description="Nội lực, định giá & chất xúc tác. Thiếu BCTC → tối đa 50.")
    technical_momentum: ScoreDimension = Field(default_factory=ScoreDimension, description="Xu hướng & động lượng.")
    comparative_strength: ScoreDimension = Field(default_factory=ScoreDimension, description="Dòng tiền & sức mạnh tương đối so với VN-Index và cùng ngành.")
    action_strategy: ScoreDimension = Field(default_factory=ScoreDimension, description="Chất lượng cơ hội giao dịch hiện tại (R:R, vị trí giá so với vùng mua).")


class ReportSummary(BaseModel):
    stance: str = Field(default="Trung lập", description="Tích cực | Trung lập | Tiêu cực")
    confidence: str = Field(default="Trung bình", description="Cao | Trung bình | Thấp — không vượt mức trần chất lượng dữ liệu")
    action: str = Field(default="Quan sát", description="Mua | Mua thăm dò | Nắm giữ | Quan sát | Hạ tỷ trọng | Bán / Đứng ngoài")


class Verdict(BaseModel):
    core_thesis: str = Field(default="", description="Luận điểm đầu tư cốt lõi 1–2 câu, có số liệu.")
    short_term: str = Field(default="", description="Nhận định & hành động 1–4 tuần tới, kèm mức giá.")
    medium_term: str = Field(default="", description="Nhận định 3–12 tháng, điều kiện để thay đổi.")
    for_new_buyers: str = Field(default="", description="Lời khuyên cụ thể cho người CHƯA có cổ phiếu: làm gì, vùng giá nào, điều kiện gì.")
    for_holders: str = Field(default="", description="Lời khuyên cụ thể cho người ĐANG nắm giữ: giữ/hạ/chốt, ngưỡng bảo vệ.")
    decision_level: str = Field(default="", description="Mức giá quyết định: vượt/thủng mức nào thì nhận định thay đổi.")


class Thesis(BaseModel):
    bull_case: List[str] = Field(default_factory=list, description="3–5 luận điểm ủng hộ, mỗi luận điểm có số liệu dẫn chứng.")
    bear_case: List[str] = Field(default_factory=list, description="3–5 luận điểm phản biện/rủi ro, mỗi luận điểm có số liệu dẫn chứng.")
    key_question: str = Field(default="", description="Câu hỏi then chốt quyết định khoản đầu tư này đúng hay sai.")
    priced_in: str = Field(default="", description="Giá hiện tại đang hàm ý/định giá kỳ vọng gì.")
    variant_view: str = Field(default="", description="Điểm nhìn khác biệt của hội đồng so với số đông; không có thì nói rõ.")


class TradePlan(BaseModel):
    setup_type: str = Field(default="", description="Loại thiết lập: mua tại hỗ trợ / mua khi bứt phá / chờ điều chỉnh / đứng ngoài...")
    entry_low: float = Field(default=0, description="Cận dưới vùng mua (cùng đơn vị giá đầu vào).")
    entry_high: float = Field(default=0, description="Cận trên vùng mua.")
    entry_trigger: str = Field(default="", description="Điều kiện kích hoạt lệnh cụ thể (giá + khối lượng + nến).")
    stop_loss: float = Field(default=0, description="Giá cắt lỗ bắt buộc, thấp hơn entry_low.")
    stop_basis: str = Field(default="", description="Cơ sở đặt cắt lỗ (cấu trúc giá + ATR).")
    target_1: float = Field(default=0, description="Mục tiêu chốt lời 1.")
    target_2: float = Field(default=0, description="Mục tiêu chốt lời 2.")
    rr_ratio: float = Field(default=0, description="Tỷ lệ lợi nhuận/rủi ro = (target_1 − giữa vùng mua) / (giữa vùng mua − stop_loss).")
    max_position_pct: float = Field(default=0, description="Tỷ trọng tối đa % NAV theo công thức rủi ro % NAV ÷ % khoảng cắt lỗ.")
    scaling_plan: str = Field(default="", description="Cách giải ngân từng phần và điều kiện gia tăng.")
    time_stop: str = Field(default="", description="Điều kiện dừng theo thời gian.")
    invalidation: str = Field(default="", description="Điều kiện vô hiệu toàn bộ luận điểm.")


class Scenario(BaseModel):
    name: str = Field(default="", description="🟢 Tích cực | 🟡 Cơ sở | 🔴 Tiêu cực")
    probability: int = Field(default=0, description="Xác suất % (3 kịch bản cộng lại = 100).")
    price_target: float = Field(default=0, description="Giá mục tiêu của kịch bản.")
    trigger: str = Field(default="", description="Dấu hiệu xác nhận kịch bản.")
    action: str = Field(default="", description="Hành động khi kịch bản xảy ra.")


class Catalyst(BaseModel):
    event: str = Field(default="", description="Sự kiện/chất xúc tác.")
    timing: str = Field(default="", description="Thời điểm dự kiến.")
    impact: str = Field(default="", description="Tích cực | Tiêu cực | Chưa rõ — và mức độ.")


class RiskItem(BaseModel):
    risk: str = Field(default="", description="Rủi ro cụ thể.")
    severity: str = Field(default="Trung bình", description="Cao | Trung bình | Thấp")
    signal: str = Field(default="", description="Dấu hiệu/ngưỡng định lượng nhận biết rủi ro đang xảy ra.")
    response: str = Field(default="", description="Hành động khi rủi ro xảy ra.")


class PricePredictionItem(BaseModel):
    timeframe: str = Field(default="", description="'T+1 (1 phiên)', 'T+2.5 (Hàng về chiều T+2)', 'T+5 (1 tuần)', 'T+10 (2 tuần)'")
    days_future: int = Field(default=1, description="Số phiên giao dịch tương lai: 1, 2, 5, 10.")
    high: float = Field(default=0, description="Cận trên vùng giá dự kiến (trong dải 95% thống kê).")
    low: float = Field(default=0, description="Cận dưới vùng giá dự kiến.")
    reason: str = Field(default="", description="Ghi chú ngắn động lực / điều kiện kỹ thuật.")

    @model_validator(mode="after")
    def _fix(self):
        if self.days_future <= 0:
            self.days_future = 1
        if self.high < self.low:
            self.high, self.low = self.low, self.high
        return self


class StockAIReportSchema(BaseModel):
    analysis: str = Field(default="", description="Báo cáo Markdown đầy đủ theo mẫu mục 7 của System Prompt (1.500–2.500 từ).")
    verdict: Verdict = Field(default_factory=Verdict)
    thesis: Thesis = Field(default_factory=Thesis)
    trade_plan: TradePlan = Field(default_factory=TradePlan)
    scenarios: List[Scenario] = Field(default_factory=list, description="Đúng 3 kịch bản: Tích cực, Cơ sở, Tiêu cực.")
    catalysts: List[Catalyst] = Field(default_factory=list, description="Chất xúc tác & sự kiện 1–3 tháng tới.")
    risks: List[RiskItem] = Field(default_factory=list, description="3–6 rủi ro chính, gồm kết quả pre-mortem.")
    monitoring: List[str] = Field(default_factory=list, description="Checklist theo dõi, mỗi dòng có ngưỡng hành động cụ thể.")
    data_gaps: List[str] = Field(default_factory=list, description="Dữ liệu còn thiếu ảnh hưởng tới độ tin cậy.")
    predictions: List[PricePredictionItem] = Field(default_factory=list, description="4 mốc days_future = 1, 2, 5, 10.")
    scores: FiveDimensionScores = Field(default_factory=FiveDimensionScores)
    summary: ReportSummary = Field(default_factory=ReportSummary)
    overall_score: int = Field(default=50, description="Điểm tổng hợp 0–100.")


# ==============================================================================================
# Prompt
# ==============================================================================================
@lru_cache(maxsize=1)
def load_prompt_parts() -> dict:
    """Đọc System Prompt (Phần A) và Mẫu dữ liệu (Phần B) từ file prompt."""
    if not PROMPT_FILE.exists():
        return {"system": "", "user": ""}
    text = PROMPT_FILE.read_text(encoding="utf-8")
    system = re.search(r"## PHẦN A[^\n]*\n(.*?)\n---\s*\n## PHẦN B", text, re.S)
    user_template = re.search(r"## PHẦN B.*?```text\n(.*?)\n```", text, re.S)
    return {
        "system": system.group(1).strip() if system else "",
        "user": user_template.group(1).strip() if user_template else "",
    }


class _MissingAsNA(dict):
    def __missing__(self, key):
        return "N/A"


def _vn(x, nd: int = 2, sign: bool = False) -> str:
    """Định dạng số kiểu Việt Nam: 1.725,36"""
    if x is None:
        return "N/A"
    try:
        s = f"{float(x):+,.{nd}f}" if sign else f"{float(x):,.{nd}f}"
    except (TypeError, ValueError):
        return str(x)
    return s.replace(",", "§").replace(".", ",").replace("§", ".")


def _session_label(last_date) -> str:
    if hasattr(last_date, "strftime"):
        label = last_date.strftime("%d/%m/%Y")
        if qe.is_partial_session(last_date):
            label += " (phiên đang giao dịch, số liệu chưa chốt)"
        return label
    return str(last_date)


# ==============================================================================================
# Hồ sơ nhà đầu tư & chất lượng dữ liệu
# ==============================================================================================
def normalize_profile(profile: Optional[dict]) -> dict:
    p = dict(profile or {})
    horizon = p.get("horizon") if p.get("horizon") in HORIZONS else DEFAULT_HORIZON
    risk = p.get("risk_profile") if p.get("risk_profile") in qe.RISK_PROFILES else "Trung bình"
    cost = p.get("cost_basis")
    try:
        cost = float(cost) if cost not in (None, "", 0, "0") else None
    except (TypeError, ValueError):
        cost = None
    pos = p.get("position_pct")
    try:
        pos = float(pos) if pos not in (None, "") else None
    except (TypeError, ValueError):
        pos = None
    return {"horizon": horizon, "risk_profile": risk, "cost_basis": cost, "position_pct": pos}


def _profile_text(prof: dict, close: float) -> str:
    risk_nav, max_w = qe.RISK_PROFILES[prof["risk_profile"]]
    lines = [
        f"- Khung thời gian: {prof['horizon']}",
        f"- Khẩu vị rủi ro: {prof['risk_profile']} → rủi ro tối đa {risk_nav}% NAV mỗi lệnh, tỷ trọng tối đa {max_w:.0f}% NAV cho một mã",
        "- Đòn bẩy: Không dùng margin",
    ]
    if prof["cost_basis"]:
        pnl = (close / prof["cost_basis"] - 1) * 100
        lines.append(
            f"- ĐANG NẮM GIỮ: giá vốn {prof['cost_basis']} → {'lãi' if pnl >= 0 else 'lỗ'} {pnl:+.2f}%"
            + (f" | tỷ trọng {prof['position_pct']}% danh mục" if prof["position_pct"] else "")
            + " → phần 'Người đang nắm giữ' phải xử lý cụ thể vị thế này"
        )
    else:
        lines.append("- Chưa khai báo vị thế → vẫn đưa lời khuyên cho cả người chưa có và người đang có cổ phiếu")
    return "\n".join(lines)


def assess_data_quality(df: pd.DataFrame, market: Optional[dict], ranking: Optional[dict], snapshot: Optional[dict],
                        financials: Optional[dict], research: Optional[dict], news_items: list, symbol: str,
                        historical: bool, source_info: Optional[dict] = None) -> dict:
    score, gaps = 0, []
    n = len(df)
    if n >= 250:
        score += 20
    elif n >= 120:
        score += 12
        gaps.append(f"Lịch sử giá chỉ {n} phiên → MA200 và xác suất nền kém tin cậy")
    else:
        score += 5
        gaps.append(f"Lịch sử giá rất ngắn ({n} phiên) — cổ phiếu mới niêm yết hoặc dữ liệu thiếu")
    if market:
        score += 15
    else:
        gaps.append("Thiếu dữ liệu VN-Index/VN30 → chưa đánh giá được thời tiết thị trường")
    if ranking:
        score += 10
    else:
        gaps.append("Thiếu dữ liệu cổ phiếu cùng ngành để xếp hạng")
    if snapshot and snapshot.get("foreign_net_bn") is not None:
        score += 10
        if not snapshot.get("foreign_history"):
            gaps.append("Khối ngoại chỉ có số liệu phiên gần nhất (cấu hình SSI FastConnect để có chuỗi nhiều phiên)")
    else:
        gaps.append("Thiếu dữ liệu khối ngoại" + (" (phân tích ngày quá khứ — không dùng bảng giá hiện tại)" if historical else ""))
    has_fa = bool(financials) or bool(research)
    if financials:
        score += 25
    elif research:
        score += 17
        gaps.append("BCTC lấy từ tra cứu web (chưa đối chiếu BCTC gốc) — vnstock không trả được dữ liệu tài chính")
    else:
        gaps.append("THIẾU dữ liệu BCTC & định giá (P/E, P/B, ROE, KQKD) → không đánh giá được nội lực" + (
            " (phân tích ngày quá khứ — không tra cứu web để tránh dùng thông tin tương lai)" if historical else ""))
    if research:
        score += 10
    else:
        gaps.append("Chưa tra cứu được sự kiện doanh nghiệp, giao dịch nội bộ, khuyến nghị CTCK")
    matched = [x for x in (news_items or []) if re.search(rf"\b{re.escape(symbol)}\b", str(x), re.I)]
    if matched:
        score += 10
    else:
        gaps.append(f"Không có tin tức riêng về {symbol} trong RSS gần đây")
    gaps.append("Chưa có: tự doanh CTCK, dư nợ margin toàn thị trường, độ rộng thị trường (số mã tăng/giảm)")
    src = source_info or get_source_info(symbol)
    if src and src.get("warning") and not historical:
        score = max(0, score - 20)
        gaps.insert(0, f"⚠️ {src['warning']} (đến {src.get('last_date')}) — nhận định có thể không còn đúng với giá hiện tại")

    if score >= 80 and has_fa:
        cap = "Cao"
    elif score >= 50:
        cap = "Trung bình"
    else:
        cap = "Thấp"
    if not has_fa and cap == "Cao":
        cap = "Trung bình"
    return {"score": score, "max_confidence": cap, "gaps": gaps, "has_fundamentals": has_fa}


# ==============================================================================================
# Ngữ cảnh phân tích
# ==============================================================================================
def build_analysis_context(symbol: str, df: pd.DataFrame, news_items: list = None, peers_info: dict = None,
                           macro_info: dict = None, market_data: dict = None, profile: dict = None,
                           extras: dict = None, historical: bool = False) -> dict:
    extras = extras or {}
    prof = normalize_profile(profile)
    # Luôn tính lại chỉ báo từ OHLCV gốc: dữ liệu đi qua JSON bị điền 0 vào MA50/MA200 ở các phiên đầu,
    # làm sai thống kê xác suất nền và độ dốc MA.
    ohlcv = [c for c in ("Open", "High", "Low", "Close", "Volume") if c in df.columns]
    df = calculate_indicators(df[ohlcv].astype(float))
    idx_df = (market_data or {}).get("VNINDEX")
    vn30_df = (market_data or {}).get("VN30")
    quant = qe.build_quant_profile(
        df, idx_df, prof["risk_profile"], prof["cost_basis"],
        symbol=symbol, snapshot=extras.get("snapshot"),
    )
    market = qe.market_regime(idx_df, vn30_df)
    sector = get_stock_sector(symbol)
    ranking = qe.sector_ranking(symbol, quant["returns"]["1m"], quant["returns"]["3m"], peers_info or {})
    dq = assess_data_quality(df, market, ranking, extras.get("snapshot"), extras.get("financials"),
                             extras.get("research"), news_items or [], symbol, historical, extras.get("data_source"))
    fa = extras.get("forecast_audit")
    if fa is None and hasattr(qe, "audit_historical_forecast"):
        try:
            last_date_str = df.index[-1].strftime("%Y-%m-%d") if not df.empty else None
            last_close = quant.get("close", 0.0)
            fa = qe.audit_historical_forecast(symbol, last_close, last_date_str)
        except Exception:
            fa = None

    return {
        "symbol": symbol, "df": df, "sector": sector, "profile": prof, "quant": quant, "market": market,
        "ranking": ranking, "peers": peers_info or {}, "macro": macro_info or {}, "news": news_items or [],
        "snapshot": extras.get("snapshot"), "overview": extras.get("overview"),
        "financials": extras.get("financials"), "research": extras.get("research"),
        "data_quality": dq, "historical": historical, "forecast_audit": fa,
    }


def build_user_prompt(ctx: dict) -> str:
    q, prof, dq = ctx["quant"], ctx["profile"], ctx["data_quality"]
    close = q["close"]
    macro = ctx["macro"]
    macro_lines = [
        f"- Vàng thế giới: {macro.get('GOLD', 'N/A')} | Dầu Brent: {macro.get('OIL', 'N/A')} | USD/VND: {macro.get('USD_VND', 'N/A')}",
    ] if macro else ["- Chưa có dữ liệu vĩ mô quốc tế"]

    fin = ctx.get("financials")
    if fin:
        fin_txt = f"(nguồn vnstock/{fin.get('source')})\n[Chỉ số tài chính]\n{fin.get('ratio') or 'N/A'}\n[Kết quả kinh doanh]\n{fin.get('income') or 'N/A'}"
    else:
        fin_txt = "- Không tải được BCTC từ vnstock (nguồn VCI/KBS đang lỗi hoặc ngừng cung cấp) → dùng mục E nếu có, nếu không ghi rõ thiếu."

    res = ctx.get("research")
    if res:
        src = "\n".join(f"  [{i+1}] {s.get('title')}" for i, s in enumerate(res.get("sources", [])[:10]))
        web_txt = f"(tra cứu ngày {res.get('as_of')} bằng {res.get('model')} — dữ kiện web, cần đối chiếu nguồn gốc)\n{res['text']}\nNguồn tham khảo:\n{src or '  (không có metadata nguồn)'}"
    elif ctx["historical"]:
        web_txt = "- Không tra cứu web vì đang phân tích một ngày trong quá khứ (tránh dùng thông tin tương lai)."
    else:
        web_txt = "- Không tra cứu được (chưa có GEMINI_API_KEY hoặc hết quota tra cứu)."

    df = ctx["df"]
    cols = [c for c in ["Open", "High", "Low", "Close", "Volume", "EMA10", "SMA20", "RSI"] if c in df.columns]
    price_table = df[cols].tail(15).round(2).to_string()

    dq_txt = (
        f"- Điểm chất lượng dữ liệu: {dq['score']}/100 → MỨC TRẦN ĐỘ TIN CẬY: {dq['max_confidence']}\n"
        + "\n".join(f"- Thiếu/hạn chế: {g}" for g in dq["gaps"])
    )

    fa = ctx.get("forecast_audit")
    if fa and isinstance(fa, dict):
        if fa.get("summary_for_prompt"):
            fa_txt = fa["summary_for_prompt"]
        elif fa.get("has_history") and fa.get("last_audit"):
            la = fa["last_audit"]
            fa_txt = (
                f"- Lần dự báo trước: Ngày {la.get('forecast_date')} tại giá {la.get('as_of_price')} (Kỳ vọng: {la.get('predicted_direction')}, Mục tiêu: {la.get('predicted_target')})\n"
                f"- Kết quả đối chiếu với giá hiện tại {la.get('actual_price')} ({la.get('price_change_pct', 0.0):+.1f}%): Đánh giá [{la.get('verdict')}] (Độ chính xác {la.get('overall_accuracy_pct')}%)\n"
                f"  • Hướng: {la.get('direction_score')} | Biên độ: {la.get('amplitude_score')} | Thời điểm: {la.get('time_score')} | Điều kiện: {la.get('condition_score')}\n"
                f"- Bài học kinh nghiệm: {la.get('lessons_learned')}"
            )
        else:
            fa_txt = "- Chưa có dữ liệu đối chiếu dự báo cũ cho mã này (lần đầu tạo hồ sơ hoặc chưa có bản ghi trước)."
    else:
        fa_txt = "- Chưa có dữ liệu đối chiếu dự báo cũ cho mã này (lần đầu tạo hồ sơ hoặc chưa có bản ghi trước)."

    values = {
        "symbol": ctx["symbol"],
        "investor_profile": _profile_text(prof, close),
        "data_quality": dq_txt,
        "market": qe.format_market_dossier(ctx["market"]),
        "macro": "\n".join(macro_lines),
        "sector": qe.format_sector_dossier(ctx["sector"], ctx["ranking"], ctx["peers"]),
        "company": format_company_dossier(ctx.get("snapshot"), ctx.get("overview"), close),
        "financials": fin_txt,
        "web_research": web_txt,
        "price_unit": q["price_unit"],
        "quant": qe.format_quant_dossier(q),
        "price_table": price_table,
        "news": "\n".join(ctx["news"][:10]) if ctx["news"] else "- Không có tin tức mới.",
        "forecast_audit": fa_txt,
        "question": (
            f"Lập báo cáo đầu tư chuyên sâu cho {ctx['symbol']} theo chuẩn Version 5.0 (Kiến trúc Phễu Kiểm Chứng 2 Tầng: "
            f"Thực chiến T+2,5 & Đọc vị Tạo lập × Kiểm chứng Giả thuyết CFA). Đóng khung các mốc quan trọng trong bảng "
            f"(T+1, T+2.5, T+5, T+10, Pivot, 3 Stops, 95% range); chỉ gắn 6 nhãn kiểm chứng ([Nguồn], [Tính toán], [Suy luận], "
            f"[Giả định], [Chưa xác định], [Mâu thuẫn nguồn]) ở các câu kết luận then chốt; tích hợp Ma trận 6 giả thuyết, "
            f"Bộ 3 chốt chặn (Price-Stop, Thesis-Stop, Time-Stop), đối chiếu dự báo cũ và kết thúc bằng 3 câu hỏi tự kiểm tra. "
            f"Độ tin cậy không vượt '{dq['max_confidence']}'."
        ),
    }
    template = load_prompt_parts()["user"]
    if not template:
        return "\n\n".join(f"[{k}]\n{v}" for k, v in values.items())
    return template.format_map(_MissingAsNA(values))


# ==============================================================================================
# Hậu kiểm nhất quán
# ==============================================================================================
def _valid_price(x, ref: float) -> bool:
    try:
        x = float(x)
    except (TypeError, ValueError):
        return False
    return x > 0 and 0.3 * ref < x < 3 * ref


def _weighted_overall(scores: dict, horizon: str) -> int:
    w = HORIZONS.get(horizon, HORIZONS[DEFAULT_HORIZON])
    keys = ["macro_industry", "fundamentals_catalyst", "technical_momentum", "comparative_strength", "action_strategy"]
    vals = [max(0, min(100, int((scores.get(k) or {}).get("score", 50)))) for k in keys]
    return int(round(sum(a * b for a, b in zip(w, vals))))


def _postprocess(rep: dict, ctx: dict, engine: str) -> dict:
    q, dq, prof = ctx["quant"], ctx["data_quality"], ctx["profile"]
    close = float(q["close"])
    atr = q["volatility"].get("atr14") or close * 0.02
    bp = q["baseline_plan"]
    stage = q["trend"].get("stage")
    market_red = bool(ctx["market"] and "🔴" in ctx["market"]["status"])
    notes = []

    # --- 1. Kế hoạch giao dịch
    tp = dict(rep.get("trade_plan") or {})
    for k in ("entry_low", "entry_high", "stop_loss", "target_1", "target_2"):
        if not _valid_price(tp.get(k), close):
            tp[k] = bp[k]
            notes.append(f"{k} thiếu/không hợp lệ → dùng kế hoạch cơ sở ({bp[k]})")
        tp[k] = round(float(tp[k]), 2)
    for k in ("setup_type", "entry_trigger", "stop_basis"):
        if not tp.get(k):
            tp[k] = bp.get(k, "")
    if tp["entry_low"] > tp["entry_high"]:
        tp["entry_low"], tp["entry_high"] = tp["entry_high"], tp["entry_low"]
    if tp["stop_loss"] >= tp["entry_low"]:
        new_stop = round(min(bp["stop_loss"], tp["entry_low"] - 0.5 * atr), 2)
        notes.append(f"Cắt lỗ {tp['stop_loss']} không thấp hơn vùng mua → chỉnh về {new_stop}")
        tp["stop_loss"] = new_stop
    mid = (tp["entry_low"] + tp["entry_high"]) / 2
    # Khoảng cắt lỗ tối thiểu 1,5×ATR (hàng T+2 chưa về → không thể cắt lỗ sớm hơn ~2,5 phiên) và tối đa 12%.
    # Cắt lỗ quá sát làm R:R "đẹp" một cách ảo tưởng.
    min_dist, max_dist = 1.5 * atr, 0.12 * mid
    risk = mid - tp["stop_loss"]
    tol = 0.011  # sai số làm tròn giá tới 0,01
    if risk < min_dist - tol or risk > max_dist + tol:
        new_risk = min(max(risk, min_dist), max_dist)
        new_stop = round(mid - new_risk, 2)
        notes.append(
            f"Cắt lỗ {tp['stop_loss']} cách giữa vùng mua {risk / mid * 100:.1f}% "
            + (f"(< 1,5×ATR = {min_dist:.2f}, dễ bị quét khi hàng T+2 chưa về)" if risk < min_dist else "(> 12%)")
            + f" → chỉnh về {new_stop}"
        )
        tp["stop_loss"] = new_stop
        tp["stop_basis"] = (tp.get("stop_basis") or "") + " [Hệ thống điều chỉnh theo chuẩn 1,5×ATR–12%]"
        risk = mid - new_stop
    if tp["target_1"] <= tp["entry_high"]:
        new_t1 = round(bp["target_1"] if bp["target_1"] > tp["entry_high"] else mid + 2 * risk, 2)
        notes.append(f"Mục tiêu 1 {tp['target_1']} không cao hơn vùng mua → chỉnh về {new_t1}")
        tp["target_1"] = new_t1
    if tp["target_2"] < tp["target_1"]:
        tp["target_2"] = round(max(bp["target_2"], tp["target_1"] + atr), 2)
    rr = (tp["target_1"] - mid) / risk if risk > 0 else 0
    if abs(rr - float(tp.get("rr_ratio") or 0)) > 0.15:
        notes.append(f"R:R tính lại từ số liệu: 1:{rr:.2f} (AI ghi 1:{float(tp.get('rr_ratio') or 0):.2f})")
    tp["rr_ratio"] = round(rr, 2)
    tp["stop_pct"] = round(risk / mid * 100, 2) if mid else None

    risk_nav, max_w = qe.RISK_PROFILES[prof["risk_profile"]]
    cap_w = risk_nav / (risk / mid * 100) * 100 if risk > 0 else max_w
    cap_w = min(cap_w, max_w)
    if market_red:
        cap_w = min(cap_w, max_w * 0.5)
    if stage == 4:
        cap_w = min(cap_w, max_w * 0.33)
    try:
        w = float(tp.get("max_position_pct") or 0)
    except (TypeError, ValueError):
        w = 0
    if w <= 0 or w > cap_w + 0.5:
        if w > cap_w + 0.5:
            notes.append(f"Tỷ trọng {w:.1f}% vượt giới hạn quản trị rủi ro → giảm về {cap_w:.1f}%")
        w = cap_w
    tp["max_position_pct"] = round(w, 1)
    rep["trade_plan"] = tp

    # --- 2. Quy tắc phủ quyết khuyến nghị
    summ = dict(rep.get("summary") or {})
    action = summ.get("action") if summ.get("action") in ACTIONS else "Quan sát"
    if action == "Mua" and (rr < 1.5 or stage == 4):
        action = "Quan sát" if rr < 1.5 else "Mua thăm dò"
        notes.append(f"Hạ khuyến nghị 'Mua' → '{action}' (R:R {rr:.2f}{', cổ phiếu ở giai đoạn 4' if stage == 4 else ''})")
    summ["action"] = action
    conf = summ.get("confidence") if summ.get("confidence") in CONF_ORDER else "Trung bình"
    if CONF_ORDER[conf] > CONF_ORDER[dq["max_confidence"]]:
        notes.append(f"Độ tin cậy '{conf}' vượt mức trần chất lượng dữ liệu → '{dq['max_confidence']}'")
        conf = dq["max_confidence"]
    summ["confidence"] = conf
    if summ.get("stance") not in ("Tích cực", "Trung lập", "Tiêu cực"):
        summ["stance"] = "Trung lập"
    rep["summary"] = summ

    # --- 3. Điểm số
    scores = rep.get("scores") or {}
    fa = scores.get("fundamentals_catalyst") or {}
    if not dq["has_fundamentals"] and int(fa.get("score", 50)) > 50:
        fa["score"] = 50
        fa["reason"] = "Thiếu dữ liệu BCTC → giới hạn 50. " + fa.get("reason", "")
        scores["fundamentals_catalyst"] = fa
    rep["scores"] = scores
    rep["overall_score"] = _weighted_overall(scores, prof["horizon"])

    # --- 4. Kịch bản: xác suất cộng = 100
    scen = [dict(s) for s in (rep.get("scenarios") or []) if isinstance(s, dict)]
    if scen:
        probs = [max(0, int(s.get("probability") or 0)) for s in scen]
        tot = sum(probs)
        if tot <= 0:
            probs = [100 // len(scen)] * len(scen)
            tot = sum(probs)
        scaled = [round(p * 100 / tot) for p in probs]
        scaled[scaled.index(max(scaled))] += 100 - sum(scaled)
        for s, p in zip(scen, scaled):
            s["probability"] = p
        if tot != 100:
            notes.append(f"Xác suất kịch bản cộng {tot}% → chuẩn hóa về 100%")
    rep["scenarios"] = scen

    # --- 5. Dự báo: đủ 4 mốc, nằm trong dải 95%
    bands = {s["days"]: s for s in q.get("stat_ranges", [])}
    names = {1: "T+1 (1 phiên)", 2: "T+2.5 (Hàng về chiều T+2)", 5: "T+5 (1 tuần)", 10: "T+10 (2 tuần)"}
    by_day = {}
    for p in rep.get("predictions") or []:
        try:
            by_day[int(p.get("days_future"))] = dict(p)
        except (TypeError, ValueError):
            continue
    preds, clamped = [], False
    for d in (1, 2, 5, 10):
        b = bands.get(d)
        p = by_day.get(d) or {}
        lo, hi = p.get("low"), p.get("high")
        if not (_valid_price(lo, close) and _valid_price(hi, close)):
            lo, hi = (b["low_68"], b["high_68"]) if b else (close * 0.97, close * 1.03)
            p["reason"] = p.get("reason") or "Dải dao động thống kê 68% theo biến động thực tế"
        lo, hi = float(min(lo, hi)), float(max(lo, hi))
        if b and (lo < b["low_95"] or hi > b["high_95"]):
            lo, hi = max(lo, b["low_95"]), min(hi, b["high_95"])
            clamped = True
        if hi <= lo:
            lo, hi = (b["low_68"], b["high_68"]) if b else (close * 0.97, close * 1.03)
        preds.append({"timeframe": names[d], "days_future": d, "low": round(lo, 2), "high": round(hi, 2), "reason": p.get("reason", "")})
    if clamped:
        notes.append("Một số vùng dự báo vượt dải 95% thống kê → đã thu hẹp về dải 95%")
    rep["predictions"] = preds

    # --- 6. Siêu dữ liệu cho giao diện
    gaps = list(dict.fromkeys((rep.get("data_gaps") or []) + dq["gaps"]))
    rep["data_gaps"] = gaps[:10]
    # Ghi chú điều chỉnh chỉ có ý nghĩa với đầu ra của AI (báo cáo dự phòng do chính hệ thống tính)
    rep["consistency_notes"] = notes if engine != "rule_based" else []
    rep["engine"] = engine
    rep["data_quality"] = {"score": dq["score"], "max_confidence": dq["max_confidence"]}
    rep["as_of"] = q["last_date"]
    rep["generated_at"] = datetime.now(VN_TZ).strftime("%H:%M %d/%m/%Y")
    rep["profile"] = prof
    res = ctx.get("research") or {}
    rep["sources"] = res.get("sources", [])[:10]
    rep["quant_snapshot"] = {
        "trend": q["trend"]["label"],
        "market_status": ctx["market"]["status"] if ctx["market"] else None,
        "market_trend": ctx["market"]["trend"]["label"] if ctx["market"] else None,
        "equity_allocation": ctx["market"]["equity_allocation"] if ctx["market"] else None,
        "relative_strength": (q.get("relative_strength") or {}).get("verdict"),
        "sector_rank": f"{ctx['ranking']['rank']}/{ctx['ranking']['of']}" if ctx["ranking"] else None,
        "flow": q["flow"]["flow_verdict"],
        "avg_value_20d_bn": q["flow"]["avg_value_20d_bn"],
        "atr_pct": q["volatility"]["atr_pct"],
        "from_52w_high_pct": q["volatility"]["from_52w_high_pct"],
        "foreign_net_bn": (ctx.get("snapshot") or {}).get("foreign_net_bn"),
        "supports": q["levels"]["supports"],
        "resistances": q["levels"]["resistances"],
        "base_rates": q.get("base_rates"),
        "returns": q["returns"],
        "tactical_6step": q.get("tactical_6step"),
        "exit_stops": q.get("exit_stops") or (q.get("tactical_6step") or {}).get("exit_stops"),
        "causal_hypotheses": q.get("causal_hypotheses"),
        "market_layers": q.get("market_layers"),
        "atc_analysis": q.get("atc_analysis"),
    }
    if "forecast_audit" not in rep or not rep.get("forecast_audit"):
        rep["forecast_audit"] = ctx.get("forecast_audit")
    return rep


# ==============================================================================================
# Báo cáo dự phòng dựa trên quy tắc định lượng (khi không gọi được AI)
# ==============================================================================================
def _rule_based_report(ctx: dict, reason: str) -> dict:
    q, mk, rk, prof, dq = ctx["quant"], ctx["market"], ctx["ranking"], ctx["profile"], ctx["data_quality"]
    sym, close = ctx["symbol"], float(q["close"])
    t, m, vr, fl = q["trend"], q["momentum"], q["volatility"], q["flow"]
    rs = q.get("relative_strength") or {}
    bp = q["baseline_plan"]
    lv = q["levels"]
    stage = t.get("stage")
    market_red = bool(mk and "🔴" in mk["status"])
    market_green = bool(mk and "🟢" in mk["status"])
    snap = ctx.get("snapshot") or {}
    br = (q.get("base_rates") or {}).get("results", {})
    br20 = br.get("20") or br.get("10")

    t6 = q.get("tactical_6step") or {}
    arch = t6.get("archetype") or {}
    arch_name = arch.get("name") or "Cổ phiếu sản xuất cơ bản & Nội tại thật"
    arch_rule = arch.get("core_rule") or "Mua gom tại nền tích lũy cạn cung No Supply"

    ex_stops = bp.get("exit_stops") or q.get("exit_stops") or {}
    p_stop = ex_stops.get("price_stop") or {}
    th_stop = ex_stops.get("thesis_stop") or {}
    tm_stop = ex_stops.get("time_stop") or {}
    price_stop_val = _vn(p_stop.get("price") or bp["stop_loss"])
    price_stop_pct = _vn(p_stop.get("pct") or bp["stop_pct"])
    thesis_stop_cond = th_stop.get("condition") or f"Gãy MA50 hoặc đóng cửa dưới {_vn(bp['stop_loss'])}"
    time_stop_act = tm_stop.get("action") or bp["time_stop"]

    atc = q.get("atc_analysis") or {}
    clv_val = _vn(atc.get("clv", 0.5))
    atc_eval = atc.get("evaluation", "Giao dịch bình thường")
    exp_warn = f" (⚠️ {atc['expiration_warning']})" if atc.get("expiration_warning") else ""

    # --- Điểm số
    macro_s = 70 if market_green else 32 if market_red else 52
    if rk:
        macro_s += 8 if rk["rank"] <= max(1, rk["of"] // 3) else -8 if rk["rank"] > rk["of"] * 2 // 3 else 0
    tech_s = {2: 70, 1: 50, 3: 42, 4: 28}.get(stage, 45)
    tech_s += 5 if m["macd_vs_signal"] == "trên" else -5
    tech_s += 5 if m["rsi"] and 50 <= m["rsi"] <= 70 else -5 if m["rsi"] and m["rsi"] < 40 else 0
    if m.get("divergence"):
        tech_s += 5 if m["divergence"].startswith("Phân kỳ dương") else -7
    if vr.get("base_pattern"):
        tech_s += 5
    flow_s = 50 + (12 if fl["flow_verdict"].startswith("Tích lũy") else -12 if fl["flow_verdict"].startswith("Phân phối") else 0)
    ex60, ex20 = rs.get("excess_60d"), rs.get("excess_20d")
    if ex60 is not None:
        flow_s += 10 if ex60 > 5 else -10 if ex60 < -5 else 0
    if ex20 is not None:
        flow_s += 5 if ex20 > 0 else -5
    rr = bp["rr_ratio"] or 0
    act_s = (70 if rr >= 2 else 55 if rr >= 1.5 else 35) - (10 if stage == 4 else 0) - (10 if market_red else 0)
    clamp = lambda v: int(max(5, min(95, v)))  # noqa: E731

    scores = {
        "macro_industry": {"score": clamp(macro_s), "reason": f"VN-Index {mk['trend']['label'].lower() if mk else 'chưa có dữ liệu'}; {mk['distribution_days_25'] if mk else 'N/A'} ngày phân phối/25 phiên; xếp hạng ngành {rk['rank']}/{rk['of']}." if rk else f"Thị trường: {mk['status'] if mk else 'N/A'}; chưa xếp hạng được trong ngành."},
        "fundamentals_catalyst": {"score": 50, "reason": "Chưa đánh giá — báo cáo dự phòng không đọc được BCTC/tra cứu web (cần AI)."},
        "technical_momentum": {"score": clamp(tech_s), "reason": f"{t['label']}; RSI {_vn(m['rsi'])}; MACD {m['macd_vs_signal']} Signal."},
        "comparative_strength": {"score": clamp(flow_s), "reason": f"{fl['flow_verdict']}; vượt trội VN-Index 1 tháng {_vn(ex20, sign=True)}%, 3 tháng {_vn(ex60, sign=True)}%."},
        "action_strategy": {"score": clamp(act_s), "reason": f"R:R kế hoạch cơ sở 1:{_vn(rr)} → {bp['rr_quality']}."},
    }

    # --- Khuyến nghị
    if stage == 4:
        action = "Bán / Đứng ngoài" if (market_red and (ex60 or 0) < 0) else "Quan sát"
    elif rr >= 2 and stage == 2 and not market_red and not bp["setup_type"].startswith("Chờ"):
        action = "Mua"
    elif rr >= 1.5 and stage in (1, 2):
        action = "Mua thăm dò"
    else:
        action = "Quan sát"
    stance = "Tích cực" if (stage == 2 and not market_red) else "Tiêu cực" if (stage == 4 or (market_red and stage == 3)) else "Trung lập"

    # --- Kịch bản (xuất phát từ xác suất nền)
    p_up = br20["win_rate"] if br20 else 45.0
    p_up += (5 if stage == 2 else -5 if stage == 4 else 0) + (-5 if market_red else 3 if market_green else 0)
    p_up += 5 if fl["flow_verdict"].startswith("Tích lũy") else -5 if fl["flow_verdict"].startswith("Phân phối") else 0
    bull = int(max(10, min(50, p_up - 15)))
    bear = int(max(10, min(50, 100 - p_up - 15)))
    base = 100 - bull - bear
    s2 = lv["supports"][1]["price"] if len(lv["supports"]) > 1 else bp["stop_loss"]
    b10 = next((s for s in q["stat_ranges"] if s["days"] == 10), None)
    scenarios = [
        {"name": "🟢 Tích cực", "probability": bull, "price_target": bp["target_2"],
         "trigger": f"Đóng cửa trên {_vn(bp['target_1'])} với KL ≥ 1,5× TB20", "action": "Gia tăng phần còn lại của kế hoạch, nâng cắt lỗ lên giá vốn"},
        {"name": "🟡 Cơ sở", "probability": base, "price_target": round((b10["low_68"] + b10["high_68"]) / 2, 2) if b10 else close,
         "trigger": f"Giá dao động {_vn(b10['low_68']) if b10 else 'N/A'}–{_vn(b10['high_68']) if b10 else 'N/A'} trong 10 phiên", "action": "Chỉ giải ngân tại vùng mua, không mua đuổi"},
        {"name": "🔴 Tiêu cực", "probability": bear, "price_target": s2,
         "trigger": f"Đóng cửa dưới {_vn(bp['stop_loss'])}", "action": "Cắt lỗ theo kế hoạch, không bình quân giá xuống"},
    ]

    # --- Báo cáo Markdown
    sup_rows = "\n".join(f"| Hỗ trợ {i+1} | {_vn(s['price'])} ({_vn(s['distance_pct'], sign=True)}%) | {s['basis']} | {s['strength']} |" for i, s in enumerate(lv["supports"]))
    res_rows = "\n".join(f"| Kháng cự {i+1} | {_vn(r['price'])} ({_vn(r['distance_pct'], sign=True)}%) | {r['basis']} | {r['strength']} |" for i, r in enumerate(lv["resistances"]))
    br_txt = ""
    if q.get("base_rates"):
        bq = q["base_rates"]
        br_txt = f"- **Điều kiện hiện tại:** {bq['condition']}\n" + "\n".join(
            f"- Sau **{h} phiên**: {s['n']} lần tương tự, tỷ lệ tăng **{_vn(s['win_rate'], 1)}%** (mọi ngày {_vn(s['all_days_win_rate'], 1)}%), "
            f"trung vị {_vn(s['median'], sign=True)}% (mọi ngày {_vn(s['all_days_median'], sign=True)}%), 10% xấu nhất ≤ {_vn(s['p10'], sign=True)}%"
            for h, s in bq["results"].items()) + f"\n- *{bq['note']}*"
    holder_txt = ""
    if bp.get("holder"):
        h = bp["holder"]
        holder_txt = f"- **Vị thế của bạn:** giá vốn {_vn(h['cost_basis'])} → {'lãi' if h['pnl_pct'] >= 0 else 'lỗ'} {_vn(h['pnl_pct'], sign=True)}%. Ngưỡng bảo vệ/dừng lỗ động: **{_vn(h['trailing_stop'])}**.\n"
    spikes = "; ".join(fl["volume_spikes_20d"]) or "không có"
    foreign = (
        f"Khối ngoại phiên gần nhất **{_vn(snap['foreign_net_bn'], sign=True)} tỷ** (mua {_vn(snap['foreign_buy_bn'])} / bán {_vn(snap['foreign_sell_bn'])}), sở hữu nước ngoài ~{_vn(snap.get('foreign_ownership_pct'))}%."
        if snap.get("foreign_net_bn") is not None else "Chưa có dữ liệu khối ngoại."
    )
    flags = "".join(f"\n> ⚠️ {f}" for f in snap.get("flags", []) if "TRADING_ACTIVATED" not in f)

    # Forecast audit table
    fa = ctx.get("forecast_audit")
    if fa and isinstance(fa, dict) and fa.get("has_history") and fa.get("last_audit"):
        la = fa["last_audit"]
        audit_table = (
            f"| Ngày {la.get('forecast_date')} tại giá {_vn(la.get('as_of_price', 0))} | "
            f"{la.get('predicted_direction')} (Target {_vn(la.get('predicted_target', 0))}) | "
            f"Giá {_vn(la.get('actual_price', close))} ({la.get('price_change_pct', 0):+.1f}%) | "
            f"[{la.get('verdict', 'N/A')}] ({la.get('overall_accuracy_pct', 0)}%) `[Tính toán]` | "
            f"{la.get('lessons_learned', '')} `[Suy luận]` |"
        )
    else:
        audit_table = (
            f"| Lần đầu phân tích ({q['last_date']}) | Khởi tạo hồ sơ cơ sở | Điểm tham chiếu {_vn(close)} | "
            f"Khởi tạo baseline `[Tính toán]` | Thiết lập mốc theo dõi chu kỳ T+2,5 cho các phiên tới `[Giả định]` |"
        )

    # Causal hypotheses table
    hypos = q.get("causal_hypotheses") or []
    if hypos:
        hypo_rows = "\n".join(
            f"| {h.get('id', f'H{i+1}')}: {h.get('name', 'N/A')} | {h.get('driver', '')} | `[Tính toán]` | {int(round(h.get('prob', 0) * 100))}% | {h.get('verifiable_by', '')} |"
            for i, h in enumerate(hypos)
        )
    else:
        hypo_rows = (
            "| H1: Gom hàng & Hấp thụ | Tạo lập gom ngầm vùng hỗ trợ | `[Tính toán]` | 40% | Vol cạn kiệt, giữ nền |\n"
            "| H2: Phân phối & Neo giá xả ngầm | Neo giá xanh nhẹ dụ cầu | `[Suy luận]` | 15% | Vol lớn nến cụt đầu |\n"
            "| H3: Quỹ tái cơ cấu (ETF/NAV) | Tác động review quỹ ngoại/nội | `[Giả định]` | 10% | Khớp lệnh ATC đột biến |\n"
            "| H4: Luân chuyển Ngành tự nhiên | Dòng tiền xoay vòng ngành | `[Nguồn]` | 15% | Cả ngành đồng loạt bứt phá |\n"
            "| H5: Tái định giá Căn bản (Re-rating) | KQKD quý tăng trưởng đột biến | `[Suy luận]` | 15% | Lợi nhuận ròng tăng > 20% |\n"
            "| H6: Bán tháo Kỹ thuật / Call Margin | Lực bán giải chấp chéo | `[Chưa xác định]` | 5% | Lệnh bán MP sàn áp đảo |"
        )

    # Stat ranges T+ table
    stat_rows = []
    days_labels = {1: "T+1 (1 phiên)", 2: "T+2.5 (Hàng về chiều T+2)", 5: "T+5 (1 tuần)", 10: "T+10 (2 tuần)"}
    for s in q.get("stat_ranges", []):
        d = s["days"]
        lbl = days_labels.get(d, f"T+{d}")
        stat_rows.append(f"| {lbl} | {_vn(s['low_95'])} – {_vn(s['high_95'])} `[Tính toán]` | {_vn(s['high_68'])} | Khớp lệnh theo dõi | Quản trị theo Price-Stop |")
    stat_table_txt = "\n".join(stat_rows) if stat_rows else "| T+2.5 (Hàng về chiều T+2) | N/A – N/A | N/A | Khớp lệnh theo dõi | Quản trị theo Price-Stop |"

    md = f"""> ⚠️ **{FALLBACK_MARKER} (không dùng AI):** {reason} Báo cáo dưới đây được tính hoàn toàn từ dữ liệu giao dịch thật theo quy tắc định lượng Version 5.0; phần nội lực doanh nghiệp chưa được đánh giá bằng LLM.
{flags}
## 📌 {sym} — {snap.get('company_name') or sym} | {snap.get('exchange') or ''} | {ctx['sector']} | {arch_name}
*Bản trình Hội đồng Đầu tư Định chế × Tác chiến T+2,5 (Version 5.0) · Dữ liệu đến: {q['last_date']} · Đơn vị giá: {q['price_unit']} · Hồ sơ: {prof['horizon']}, rủi ro {prof['risk_profile']}*

### 🎯 KẾT LUẬN & QUYẾT NGHỊ CỦA HỘI ĐỒNG (BLUF)
- **Quyết định:** {action} `[Suy luận]` — **Độ tin cậy:** {"Thấp" if not dq['has_fundamentals'] else "Trung bình"} (chưa có đánh giá cơ bản) — **Định danh bàn cờ Tạo lập:** {arch_name} `[Nguồn]`
- **Luận điểm cốt lõi:** {t['label']}; {fl['flow_verdict'].lower()}; R:R kế hoạch 1:{_vn(rr)} `[Tính toán]`
- **Chỉ thị người CHƯA có vị thế:** {bp['setup_type']}. Vùng mua {_vn(bp['entry_low'])}–{_vn(bp['entry_high'])}; {bp['entry_trigger']} `[Tính toán]`
- **Chỉ thị người ĐANG nắm giữ:** giữ khi giá còn trên {price_stop_val}; thủng mức này → hạ tỷ trọng dứt khoát `[Tính toán]`
{holder_txt}- **Mức giá bản lề (Pivot Level):** vượt {_vn(bp['target_1'])} kèm thanh khoản → cải thiện; thủng {price_stop_val} → luận điểm mua mất hiệu lực `[Tính toán]`

### 1. Đối chiếu & Rút kinh nghiệm từ Dự báo Cũ (Forecast Audit)
| Kỳ dự báo trước | Nhận định cũ | Thực tế diễn biến | Chấm điểm (Hướng / Biên độ / Thời điểm / Điều kiện) | Bài học kinh nghiệm & Tự sửa sai |
| :--- | :--- | :--- | :--- | :--- |
{audit_table}

### 2. Định danh Bản chất Cổ phiếu & Thời tiết Thị trường (Tránh bẫy "Xanh vỏ đỏ lòng")
- **Định danh Tạo lập:** {arch_name} — {arch_rule} `[Nguồn]`
- **Thời tiết thị trường:** VN-Index {(mk['trend']['label'] + f"; {mk['distribution_days_25']} ngày phân phối trong 25 phiên; 1 tháng {_vn(mk['ret_20d'], sign=True)}%") if mk else 'chưa có dữ liệu'}.
- **Trạng thái:** {mk['status'] if mk else 'N/A'} → tỷ trọng cổ phiếu tổng thể tham khảo **{mk['equity_allocation'] if mk else 'N/A'}**. {mk.get('breadth_hint', '') if mk else ''}
- Beta của {sym} so với VN-Index (120 phiên): {_vn(rs.get('beta_120d'))} → {'biến động mạnh hơn thị trường' if (rs.get('beta_120d') or 0) > 1.1 else 'biến động ít hơn hoặc tương đương thị trường'}.
- **Đối chiếu 3 Giả thuyết Thay thế Không-Thao-túng:**
  1. *Quỹ tái cơ cấu (Fund Rebalance):* Rà soát danh mục ETF ngoại/nội định kỳ `[Giả định]`.
  2. *Luân chuyển dòng tiền ngành (Sector Rotation):* {(f"Xếp hạng ngành {rk['rank']}/{rk['of']}" if rk else "Theo dõi dòng tiền nhóm ngành")} `[Nguồn]`.
  3. *Tái định giá theo nội tại (Fundamental Re-rating):* Cần AI đọc BCTC để xác nhận `[Chưa xác định]`.

### 3. Đọc Bảng điện, Sổ lệnh & Dòng tiền ẩn (Tape Reading & Đọc vị Tạo lập)
- **Độ sâu thị trường & Tường đỡ:** {t6.get('order_book_analysis') or 'Đang theo dõi lệnh kê 3 bước giá.'} `[Nguồn]`
- **Bất đối xứng Khối ngoại:** {t6.get('foreign_cycle_analysis') or foreign} `[Nguồn]`
- **Phân biệt Spring vs. Gãy thật:** {t6.get('spring_analysis') or 'Chưa ghi nhận cú rũ bỏ Spring rõ rệt.'} `[Suy luận]`
- **Phân tích phiên ATC & CLV:** Chỉ số Close Location Value CLV = {clv_val} → Đánh giá ATC: **{atc_eval}**{exp_warn}. `[Tính toán]`

### 4. Ma trận 6 Giả thuyết Biến động Giá (Causal Hypotheses Matrix)
| Giả thuyết nguyên nhân | Diễn giải & Bằng chứng thực tế | Nhãn kiểm chứng | Xác suất (%) | Điều kiện xác nhận / Bác bỏ |
| :--- | :--- | :--- | :--- | :--- |
{hypo_rows}

### 5. Nội lực Doanh nghiệp, Bóc tách BCTC (Forensic) & Khoảng cách Kỳ vọng (Priced-in)
- Chưa đánh giá trong chế độ dự phòng (cần AI đọc BCTC/tra cứu web). Không dùng nhận định này cho quyết định trung – dài hạn `[Chưa xác định]`.
- {('Xếp hạng hiệu suất 3 tháng: **' + str(rk['rank']) + '/' + str(rk['of']) + '** trong nhóm ' + ctx['sector'] + ' → ' + rk['verdict'] + f"; trung vị 1 tháng của ngành {_vn(rk['peer_median_ret20'], sign=True)}% so với {sym} {_vn(q['returns']['1m'], sign=True)}%.") if rk else 'Chưa xếp hạng được trong ngành.'}

### 6. Cấu trúc Kỹ thuật, Volume Profile (POC) & Các Vùng giá Then chốt
- **{t['label']}.** {t.get('ma_alignment', '')}. Giá cách MA50 {_vn(t['vs_ma50_pct'], sign=True)}%, MA200 {_vn(t['vs_ma200_pct'], sign=True)}%.
- RSI {_vn(m['rsi'])}, MACD {m['macd_vs_signal']} Signal và {m['macd_vs_zero']} 0. {m.get('divergence') or 'Không có phân kỳ RSI rõ ràng.'}
- Cách đỉnh 52 tuần {_vn(vr['from_52w_high_pct'], sign=True)}%, ATR {_vn(vr['atr_pct'])}%/phiên. {vr.get('base_pattern') or ''}

| Vùng | Giá | Cơ sở | Độ mạnh |
| :--- | :--- | :--- | :--- |
{res_rows}
| Giá hiện tại | {_vn(close)} | Điểm tham chiếu thị trường | |
{sup_rows}

### 7. Đồng hồ Sinh học T+2,5 & Bộ lọc Sự kiện Quyền (GDKHQ / Điểm rơi BCTC)
- **Chu kỳ T+2,5 hàng về:** Canh mốc `13h00 chiều T+2,5` của các phiên nổ thanh khoản kỷ lục.
- **3 Khung giờ tác chiến chuẩn:**
  - `09h00 – 10h00`: Khung giờ Bẫy hưng phấn / Mở Gap sáng (Đứng ngoài quan sát, cấm mua đuổi giá xanh).
  - `11h00 – 11h30`: Khung giờ Biến động trưa / Kiểm định lực cầu phiên sáng.
  - `13h45 – 14h30 / ATC`: Khung giờ Phán quyết & Chốt chặn ATC (Thời điểm ra quyết định bấm nút Mua/Bán).
- **Bộ lọc sự kiện quyền:** Kiểm tra kỹ hiệu sự kiện quyền (•), áp dụng triệt để quy tắc **"Né trước chốt – Bắt sau chia"**.

### 8. Xác suất Nền (Base-rate), Dải Thống kê 95% & Bảng Mốc Thời gian T+
{br_txt or '- Không đủ mẫu lịch sử.'}

| Mốc thời gian | Dải giá thống kê 95% | Giá mục tiêu kỳ vọng | Dấu hiệu xác nhận trên bảng điện | Hành động kiểm soát rủi ro |
| :--- | :--- | :--- | :--- | :--- |
{stat_table_txt}

### 9. Kế hoạch Tác chiến & Bộ Quy Tắc Thực Chiến T+2,5 (Exit Stops Triad)
| Hạng mục | Thông số khuyến nghị | Cơ sở thực chiến & Kỷ luật đi vốn |
| :--- | :--- | :--- |
| Thiết lập giao dịch | {bp['setup_type']} | `[Suy luận]` Phù hợp chu kỳ sóng và dòng tiền |
| Vùng mua gom | {_vn(bp['entry_low'])} – {_vn(bp['entry_high'])} | `[Tính toán]` Vùng nền tích lũy cạn cung |
| Khung giờ & Điều kiện kích hoạt | `13h45 – 14h30 / ATC` | {bp['entry_trigger']} |
| **Price-Stop (Chốt chặn Giá)** | {price_stop_val} (−{price_stop_pct}%) | `[Tính toán]` Đệm an toàn ≥ 1,5× ATR và ≤ 12% |
| **Thesis-Stop (Chốt chặn Luận điểm)** | {thesis_stop_cond} | Thoát ngay khi luận điểm sai, không chờ giá `[Suy luận]` |
| **Time-Stop (Chốt chặn Thời gian)** | {time_stop_act} | Giới hạn chi phí cơ hội, chủ động thu hồi vốn `[Giả định]` |
| Chốt lời Nhịp 1 (Bán 30%) | {_vn(bp['target_1'])} | Khóa lãi cơ bản tại Kháng cự 1 |
| Chốt lời Nhịp 2 (Giữ 50% Trailing) | Trailing Stop trượt 1,5%–2% từ đỉnh | Cưỡi sóng bằng lệnh điều kiện tự động |
| Chốt lời Nhịp 3 (Giữ 20% Gap FOMO) | Bán lúc 09h15–09h30 sáng hôm sau | Ăn trọn quán tính FOMO mở Gap |
| Tỷ lệ Lợi nhuận / Rủi ro (R:R) | 1 : {_vn(bp['rr_ratio'])} — {bp['rr_quality']} | Chuẩn CFA $\ge 1:2$ `[Tính toán]` |
| Tỷ trọng tối đa & Đi vốn | {_vn(bp['max_position_pct'], 1)}% NAV — {bp['sizing_rule']} | Giải ngân 2 bước tại nền `[Tính toán]` |

### 10. Luận điểm Ủng hộ vs. Phản biện & Pre-Mortem (Mổ xẻ kịch bản thua lỗ)
- **Luận điểm ủng hộ:** {fl['flow_verdict']}; RSI {_vn(m['rsi'])}; R:R 1:{_vn(rr)}.
- **Rủi ro & Pre-Mortem:** Nếu VN-Index gãy hỗ trợ hoặc lực bán ATC áp đảo dẫn tới thủng {price_stop_val}, kịch bản tiêu cực xảy ra và phải cắt lỗ dứt khoát.

### 11. Bảng Checklist 5 Phút Trước Khi Bấm Lệnh (Dành cho người bận rộn ngoài công trường)
""" + "\n".join(
        f"- **[{it['status']}] {it['step']}:** {it['detail']}"
        for it in (t6.get("checklist_5m") or [])
    ) + f"""

### 12. Bộ 3 Câu Hỏi Tự Kiểm Tra (Self-Reflection) Trước Khi Phê Duyệt
1. `[ ]` **Kiểm tra Thiên kiến & Giả định ngầm:** Báo cáo dự phòng này dựa hoàn toàn trên dữ liệu kỹ thuật và dòng tiền, chưa có thẩm định BCTC chuyên sâu.
2. `[ ]` **Kiểm tra Kế hoạch Thoát hiểm & Thesis-Stop:** Mức cắt lỗ kỹ thuật {price_stop_val} và điều kiện Thesis-Stop đã được thiết lập tự động.
3. `[ ]` **Kiểm tra Kỷ luật Khung giờ Tác chiến & Bẫy T+2,5:** Tuyệt đối không bấm lệnh mua đuổi trước 10h00 sáng; chỉ kích hoạt sau 13h45.

### 🔍 Dữ liệu còn thiếu
""" + "\n".join(f"- {g}" for g in dq["gaps"]) + """

> *Báo cáo phân tích định lượng Version 5.0 tự động, mang tính tham khảo, không phải khuyến nghị mua/bán.*"""

    rep = {
        "analysis": md,
        "verdict": {
            "core_thesis": f"{t['label']}; {fl['flow_verdict'].lower()}; R:R kế hoạch 1:{_vn(rr)}.",
            "short_term": f"{action}: {bp['setup_type'].lower()}, vùng mua {_vn(bp['entry_low'])}–{_vn(bp['entry_high'])}, cắt lỗ {_vn(bp['stop_loss'])}.",
            "medium_term": "Chưa đánh giá nội lực doanh nghiệp — cần AI để đọc BCTC và định giá.",
            "for_new_buyers": bp["entry_trigger"],
            "for_holders": (bp.get("holder") or {}).get("note") or f"Giữ khi giá còn trên {_vn(bp['stop_loss'])}; thủng thì hạ tỷ trọng.",
            "decision_level": f"Vượt {_vn(bp['target_1'])} / thủng {_vn(bp['stop_loss'])}",
        },
        "thesis": {
            "bull_case": [x for x in [
                fl["flow_verdict"] if fl["flow_verdict"].startswith("Tích lũy") else None,
                rs.get("verdict") if rs.get("verdict", "").startswith(("Dẫn dắt", "Đang cải thiện")) else None,
                vr.get("base_pattern"),
                m.get("divergence") if (m.get("divergence") or "").startswith("Phân kỳ dương") else None,
                f"Xác suất nền {br20['win_rate']}% tăng sau {br20['n']} lần tương tự" if br20 and br20["win_rate"] > 55 else None,
            ] if x],
            "bear_case": [x for x in [
                t["label"] if stage in (3, 4) else None,
                f"Thị trường {mk['status']} với {mk['distribution_days_25']} ngày phân phối" if mk and not market_green else None,
                fl["flow_verdict"] if fl["flow_verdict"].startswith("Phân phối") else None,
                rs.get("verdict") if rs.get("verdict", "").startswith(("Tụt hậu", "Đang suy yếu")) else None,
                m.get("divergence") if (m.get("divergence") or "").startswith("Phân kỳ âm") else None,
                f"Xác suất nền chỉ {br20['win_rate']}% tăng (mọi ngày {br20['all_days_win_rate']}%)" if br20 and br20["win_rate"] < 45 else None,
            ] if x],
            "key_question": f"Giá có giữ được hỗ trợ {_vn(lv['supports'][0]['price']) if lv['supports'] else _vn(bp['stop_loss'])} và vượt {_vn(bp['target_1'])} kèm thanh khoản không?",
            "priced_in": "Chưa đánh giá (cần dữ liệu cơ bản).",
            "variant_view": "Không có — báo cáo dự phòng chỉ dựa trên dữ liệu giá.",
        },
        "trade_plan": {k: bp[k] for k in ("setup_type", "entry_low", "entry_high", "entry_trigger", "stop_loss", "stop_basis", "target_1", "target_2", "rr_ratio", "max_position_pct")}
        | {"scaling_plan": "50% tại vùng mua khi có tín hiệu kích hoạt, 50% khi vượt mục tiêu 1", "time_stop": bp["time_stop"], "invalidation": f"Đóng cửa dưới {_vn(bp['stop_loss'])}", "exit_stops": ex_stops},
        "scenarios": scenarios,
        "catalysts": [],
        "risks": [x for x in [
            {"risk": "Thị trường chung trong xu hướng rủi ro", "severity": "Cao", "signal": f"VN-Index {mk['trend']['label']}", "response": "Giảm tỷ trọng tối đa còn một nửa"} if market_red else None,
            {"risk": "Thanh khoản thấp, khó thoát hàng", "severity": "Cao", "signal": f"GTGD TB {fl['avg_value_20d_bn']} tỷ/phiên", "response": "Giới hạn quy mô vị thế"} if fl["liquidity_tier"].startswith("Thấp") else None,
            {"risk": "Rủi ro T+2: không thể cắt lỗ trong ~2,5 phiên đầu", "severity": "Trung bình", "signal": f"ATR {vr['atr_pct']}%/phiên", "response": "Chỉ mua gần hỗ trợ, tránh mua đuổi phiên tăng mạnh"},
        ] if x],
        "monitoring": [
            f"Đóng cửa dưới {_vn(bp['stop_loss'])} → cắt lỗ",
            f"Vượt {_vn(bp['target_1'])} với KL ≥ 1,5× TB20 → xác nhận kịch bản tích cực",
            "Số ngày phân phối của VN-Index ≥ 6/25 phiên → giảm tỷ trọng chung",
        ],
        "data_gaps": dq["gaps"],
        "predictions": [
            {"timeframe": "", "days_future": s["days"], "low": s["low_68"], "high": s["high_68"], "reason": "Dải thống kê 68% theo biến động thực tế"}
            for s in q["stat_ranges"]
        ],
        "scores": scores,
        "summary": {"stance": stance, "confidence": "Thấp" if not dq["has_fundamentals"] else "Trung bình", "action": action},
        "overall_score": 0,
        "forecast_audit": fa,
    }
    return _postprocess(rep, ctx, "rule_based")


# ==============================================================================================
# Điểm vào chính
# ==============================================================================================
def _parse_json(text: str) -> dict:
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t, flags=re.S)
    return json.loads(t)


def analyze_stock_data(
    symbol: str,
    df: pd.DataFrame,
    news_items: list = None,
    peers_info: dict = None,
    macro_info: dict = None,
    market_data: dict = None,
    profile: dict = None,
    extras: dict = None,
    historical: bool = False,
) -> str:
    """Phân tích một mã và trả về JSON string của báo cáo."""
    if df is None or df.empty:
        return json.dumps({"analysis": "Không có dữ liệu lịch sử giá.", "predictions": []}, ensure_ascii=False)

    ctx = build_analysis_context(symbol, df, news_items, peers_info, macro_info, market_data, profile, extras, historical)

    if not llm_client.get_api_key():
        rep = _rule_based_report(ctx, "Chưa cấu hình `GEMINI_API_KEY` trong file `.env`.")
        return json.dumps(rep, ensure_ascii=False)

    system_instruction = load_prompt_parts().get("system") or "Bạn là Giám đốc Đầu tư chứng khoán Việt Nam."
    user_prompt = build_user_prompt(ctx)
    schema = llm_client.force_required(StockAIReportSchema.model_json_schema())

    models = llm_client.candidate_models()
    last_err = None
    t0 = time.time()
    while models:
        try:
            text, model, _ = llm_client.generate(
                user_prompt, system=system_instruction, json_schema=schema, temperature=0.35,
                models=models, label=f"Analyze {symbol}",
            )
        except llm_client.LLMAuthError as e:
            last_err = e
            break
        except llm_client.LLMUnavailable as e:
            last_err = e
            break
        try:
            parsed = StockAIReportSchema.model_validate(_parse_json(text)).model_dump()
            if len(parsed.get("analysis", "")) < 400:
                raise ValueError("Báo cáo quá ngắn")
            logger.info(f"[AI] {symbol} hoàn tất bằng {model} sau {time.time() - t0:.1f}s")
            return json.dumps(_postprocess(parsed, ctx, f"gemini:{model}"), ensure_ascii=False)
        except (json.JSONDecodeError, ValidationError, ValueError) as e:
            last_err = e
            logger.warning(f"[AI] {model} trả JSON không hợp lệ ({str(e)[:160]}) → thử model kế tiếp")
            models = models[models.index(model) + 1:] if model in models else []

    reason = (
        "Khóa `GEMINI_API_KEY` không hợp lệ." if isinstance(last_err, llm_client.LLMAuthError)
        else f"Tạm thời không gọi được Gemini (hết quota hoặc quá tải: {str(last_err)[:220]})."
    )
    logger.warning(f"[AI] {symbol}: chuyển sang báo cáo định lượng — {reason}")
    return json.dumps(_rule_based_report(ctx, reason), ensure_ascii=False)


if __name__ == "__main__":
    pass
