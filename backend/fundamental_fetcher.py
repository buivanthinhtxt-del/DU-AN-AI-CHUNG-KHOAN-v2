"""
Dữ liệu doanh nghiệp THẬT cho phân tích (thay thế hoàn toàn bảng số liệu FA viết cứng của bản cũ).

Nguồn:
1. Bảng giá phiên gần nhất (ưu tiên API bảng giá Vietcap gọi trực tiếp; dự phòng vnstock Trading.price_board /
   SSI FastConnect): khối ngoại mua/bán, room ngoại, giá trần/sàn/tham chiếu, trạng thái giao dịch, dư mua/dư bán
   → phát hiện trắng bên mua / dư mua trần.
2. Hồ sơ công ty (vnstock Company.overview): số cổ phiếu lưu hành → vốn hóa, mô hình kinh doanh, kiểm toán.
3. Báo cáo tài chính (vnstock Finance) — best-effort, có giới hạn thời gian.
4. Tra cứu web có trích dẫn (Gemini + Google Search): KQKD các quý gần nhất, định giá, sự kiện, khuyến nghị CTCK.

Nguyên tắc: thiếu thì trả None và ghi rõ "thiếu" — tuyệt đối không điền số giả định.
"""
from __future__ import annotations

import concurrent.futures
import logging
import time
import warnings
from typing import Optional

import pandas as pd

from cache_manager import get_cache, set_cache
from data_sources import PUBLIC, SSI, VNSTOCK
import llm_client

warnings.filterwarnings("ignore")
logger = logging.getLogger("fundamental_fetcher")

_POOL = concurrent.futures.ThreadPoolExecutor(max_workers=6, thread_name_prefix="fa")


def _with_timeout(fn, timeout: float, *args, **kwargs):
    fut = _POOL.submit(fn, *args, **kwargs)
    try:
        return fut.result(timeout=timeout)
    except concurrent.futures.TimeoutError:
        logger.warning(f"[FA] {getattr(fn, '__name__', fn)} quá {timeout}s — bỏ qua")
        return None
    except SystemExit as e:  # vnai (vnstock) gọi sys.exit khi vượt hạn mức → không được làm sập backend
        VNSTOCK.note_rate_limited()
        logger.warning(f"[FA] {getattr(fn, '__name__', fn)}: vnstock vượt hạn mức request ({str(e)[:120]})")
        return None
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[FA] {getattr(fn, '__name__', fn)} lỗi: {str(e)[:200]}")
        return None


def _f(x) -> Optional[float]:
    try:
        if x is None or (isinstance(x, float) and pd.isna(x)):
            return None
        return float(x)
    except (TypeError, ValueError):
        return None


# ----------------------------------------------------------------------------------------------
# 1. Bảng giá phiên gần nhất
# ----------------------------------------------------------------------------------------------
def _price_board_raw(symbol: str) -> Optional[dict]:
    from vnstock.api.trading import Trading

    for src in ("vci", "kbs"):
        try:
            if not VNSTOCK.acquire(block=False):
                return None
            pb = Trading(source=src).price_board([symbol])
            if pb is None or pb.empty:
                continue
            row = pb.iloc[0]
            flat = {}
            for col, val in row.items():
                key = col[-1] if isinstance(col, tuple) else col
                flat.setdefault(str(key), val)
            flat["_source"] = src
            return flat
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[FA] price_board {src} lỗi với {symbol}: {str(e)[:160]}")
    return None


def get_foreign_flow_history(symbol: str, history_close: Optional[float] = None, days: int = 45) -> Optional[dict]:
    """Chuỗi khối ngoại nhiều phiên từ SSI FastConnect (DailyStockPrice). Cần SSI_CONSUMER_ID/SECRET."""
    if not SSI.configured():
        return None
    cache_key = f"foreign_hist_{symbol}"
    cached = get_cache(cache_key, 1800)
    if cached:
        return cached
    rows = _with_timeout(SSI.daily_stock_price, 30, symbol, days)
    if not rows:
        return None
    nets = [((r["foreign_buy_val"] or 0) - (r["foreign_sell_val"] or 0)) / 1e9 for r in rows]

    def tail_sum(n):
        return round(sum(nets[-n:]), 2) if len(nets) >= 1 else None

    streak, sign = 0, 0
    for v in reversed(nets):
        s = 1 if v > 0 else -1 if v < 0 else 0
        if s == 0 or (sign and s != sign):
            break
        sign, streak = s, streak + 1
    last = rows[-1]
    div = 1000.0 if (history_close and history_close < 1000 and (last.get("close") or 0) > 1000) else 1.0
    out = {
        "sessions": len(rows),
        "last_date": last["date"].strftime("%d/%m/%Y"),
        "net_1d_bn": tail_sum(1), "net_5d_bn": tail_sum(5), "net_20d_bn": tail_sum(20),
        "streak": f"{streak} phiên {'mua' if sign > 0 else 'bán'} ròng liên tiếp" if streak else "không có chuỗi",
        "recent": [f"{r['date'].strftime('%d/%m')}: {n:+.1f} tỷ" for r, n in zip(rows[-10:], nets[-10:])],
        "last": {
            "close": round(last["close"] / div, 2) if last.get("close") else None,
            "ref": round(last["ref"] / div, 2) if last.get("ref") else None,
            "ceiling": round(last["ceiling"] / div, 2) if last.get("ceiling") else None,
            "floor": round(last["floor"] / div, 2) if last.get("floor") else None,
            "foreign_buy_bn": round((last["foreign_buy_val"] or 0) / 1e9, 2),
            "foreign_sell_bn": round((last["foreign_sell_val"] or 0) / 1e9, 2),
            "foreign_room": last.get("foreign_room"),
            "total_value_bn": round(last["total_value"] / 1e9, 1) if last.get("total_value") else None,
        },
        "source": "ssi",
    }
    set_cache(cache_key, out)
    return out


def _snapshot_from_ssi(fh: dict) -> dict:
    last = fh["last"]
    flags = []
    if last.get("close") and last.get("floor") and last["close"] <= last["floor"]:
        flags.append("GIÁ ĐÓNG CỬA Ở MỨC SÀN — cẩn trọng nguy cơ trắng bên mua")
    return {
        "source": "ssi", "company_name": None, "exchange": None, "trading_date": fh["last_date"],
        "match_price": last.get("close"), "ref_price": last.get("ref"), "ceiling": last.get("ceiling"), "floor": last.get("floor"),
        "total_value_bn": last.get("total_value_bn"),
        "foreign_buy_bn": last["foreign_buy_bn"], "foreign_sell_bn": last["foreign_sell_bn"],
        "foreign_net_bn": round(last["foreign_buy_bn"] - last["foreign_sell_bn"], 2),
        "foreign_net_volume": None, "foreign_ownership_pct": None,
        "foreign_room_left_shares": int(last["foreign_room"]) if last.get("foreign_room") else None,
        "foreign_room_left_pct_of_limit": None, "listed_shares": None, "bid_ask": {}, "flags": flags,
    }


def _board_flags(match, ceiling, floor, bid1_vol, ask1_vol, sec_status, trading_status) -> list[str]:
    flags = []
    if match and floor and match <= floor:
        flags.append("GIÁ ĐANG Ở MỨC SÀN" + (" — dư mua rất mỏng, nguy cơ TRẮNG BÊN MUA (khó thoát hàng)" if not bid1_vol else ""))
    if match and ceiling and match >= ceiling:
        flags.append("GIÁ ĐANG Ở MỨC TRẦN" + (" — trắng bên bán (cầu áp đảo)" if not ask1_vol else ""))
    # security_status 'N' = bình thường; các mã khác (W/C/R/S...) = cảnh báo / kiểm soát / hạn chế / tạm ngừng
    sec = str(sec_status or "").strip().upper()
    trading = str(trading_status or "").strip().upper()
    if sec and sec not in ("N", "NORMAL", "0", "NONE", "NAN"):
        flags.append(f"Mã trạng thái chứng khoán '{sec}' — có thể thuộc diện cảnh báo/kiểm soát/hạn chế giao dịch, cần kiểm tra trên HOSE/HNX")
    if trading and "ACTIVATED" not in trading and trading not in ("NORMAL", "NONE", "NAN"):
        flags.append(f"Trạng thái giao dịch: {trading} (có thể đang tạm ngừng/đình chỉ giao dịch)")
    return flags


def _public_quote(symbol: str) -> Optional[dict]:
    ok, _ = PUBLIC.available()
    if not ok:
        return None
    return (PUBLIC.price_board([symbol]) or {}).get(symbol)


def _snapshot_from_quote(q: dict) -> dict:
    """Ảnh chụp từ bảng giá Vietcap gọi trực tiếp (data_sources.PUBLIC.price_board) — giá đã theo nghìn đồng."""
    bid, ask = q.get("bid") or [], q.get("ask") or []
    cur_room, total_room, listed = q.get("foreign_room"), q.get("foreign_total_room"), q.get("listed_shares")
    foreign_own = (total_room - cur_room) / listed * 100 if total_room and cur_room is not None and listed else None
    fb_vol, fs_vol = q.get("foreign_buy_vol"), q.get("foreign_sell_vol")
    return {
        "source": "vci (bảng giá trực tiếp)",
        "company_name": q.get("company_name"), "exchange": q.get("exchange"),
        "trading_date": q.get("trading_date") or "", "session": q.get("session"),
        "match_price": q.get("price"), "ref_price": q.get("ref"), "ceiling": q.get("ceiling"), "floor": q.get("floor"),
        "total_value_bn": round(q["value_bn"], 1) if q.get("value_bn") is not None else None,
        "foreign_buy_bn": q.get("foreign_buy_bn"), "foreign_sell_bn": q.get("foreign_sell_bn"),
        "foreign_net_bn": q.get("foreign_net_bn"),
        "foreign_net_volume": int(fb_vol - fs_vol) if fb_vol is not None and fs_vol is not None else None,
        "foreign_ownership_pct": round(foreign_own, 2) if foreign_own is not None else None,
        "foreign_room_left_shares": int(cur_room) if cur_room is not None else None,
        "foreign_room_left_pct_of_limit": round(cur_room / total_room * 100, 1) if total_room and cur_room is not None else None,
        "listed_shares": int(listed) if listed else None,
        "bid_ask": {"bid": [(x["price"], x["volume"]) for x in bid], "ask": [(x["price"], x["volume"]) for x in ask]},
        "flags": _board_flags(q.get("price"), q.get("ceiling"), q.get("floor"),
                              bid[0]["volume"] if bid else None, ask[0]["volume"] if ask else None,
                              q.get("security_status"), q.get("trading_status")),
    }


def get_price_board_snapshot(symbol: str, history_close: Optional[float] = None) -> Optional[dict]:
    """Ưu tiên: bảng giá Vietcap gọi trực tiếp → bảng giá qua vnstock → dựng lại từ SSI FastConnect."""
    cache_key = f"pb_snapshot_{symbol}"
    cached = get_cache(cache_key, 300)
    if cached:
        return cached

    fh = get_foreign_flow_history(symbol, history_close)
    snap = None
    q = _with_timeout(_public_quote, 15, symbol)
    if q and (q.get("price") or q.get("ref")):
        snap = _snapshot_from_quote(q)
    if snap is None:
        ok, _ = VNSTOCK.available()
        raw = _with_timeout(_price_board_raw, 15, symbol) if ok else None
        if raw:
            snap = _snapshot_from_vnstock(raw, history_close)
        elif fh:
            snap = _snapshot_from_ssi(fh)  # dựng ảnh chụp phiên gần nhất từ SSI
    if snap is None:
        return None
    if fh:
        snap["foreign_history"] = fh
    set_cache(cache_key, snap)
    return snap


def _snapshot_from_vnstock(raw: dict, history_close: Optional[float]) -> dict:
    g = raw.get
    match = _f(g("match_price")) or _f(g("close_price"))
    ceiling = _f(g("ceiling")) or _f(g("ceiling_price"))
    floor = _f(g("floor")) or _f(g("floor_price"))
    ref = _f(g("ref_price")) or _f(g("reference_price"))
    # Đồng bộ đơn vị với dữ liệu lịch sử (nghìn đồng)
    div = 1000.0 if (history_close and history_close < 1000 and match and match > 1000) else 1.0

    fb_val, fs_val = _f(g("foreign_buy_value")), _f(g("foreign_sell_value"))
    fb_vol, fs_vol = _f(g("foreign_buy_volume")), _f(g("foreign_sell_volume"))
    if fb_val is None and fb_vol is not None and match:
        fb_val, fs_val = fb_vol * match, (fs_vol or 0) * match

    cur_room = _f(g("current_room")) or _f(g("foreign_room"))
    total_room = _f(g("total_room"))
    listed = _f(g("listed_share"))
    foreign_own = None
    if total_room and cur_room is not None and listed:
        foreign_own = (total_room - cur_room) / listed * 100

    bid1_vol = _f(g("bid_1_volume")) or _f(g("bid_vol_1"))
    ask1_vol = _f(g("ask_1_volume")) or _f(g("ask_vol_1"))
    flags = _board_flags(match, ceiling, floor, bid1_vol, ask1_vol, g("security_status"), g("trading_status"))

    acc_val = _f(g("accumulated_value"))
    if acc_val is not None:
        total_value_bn = acc_val / 1e9 if acc_val > 1e8 else acc_val / 1e3  # VCI trả theo triệu đồng
    elif _f(g("total_value")):
        total_value_bn = _f(g("total_value")) / 1e9
    else:
        total_value_bn = None

    snap = {
        "source": raw.get("_source"),
        "company_name": g("organ_name"),
        "exchange": g("exchange"),
        "trading_date": str(g("trading_date") or ""),
        "match_price": round(match / div, 2) if match else None,
        "ref_price": round(ref / div, 2) if ref else None,
        "ceiling": round(ceiling / div, 2) if ceiling else None,
        "floor": round(floor / div, 2) if floor else None,
        "total_value_bn": round(total_value_bn, 1) if total_value_bn is not None else None,
        "foreign_buy_bn": round(fb_val / 1e9, 2) if fb_val is not None else None,
        "foreign_sell_bn": round(fs_val / 1e9, 2) if fs_val is not None else None,
        "foreign_net_bn": round((fb_val - fs_val) / 1e9, 2) if fb_val is not None and fs_val is not None else None,
        "foreign_net_volume": int(fb_vol - fs_vol) if fb_vol is not None and fs_vol is not None else None,
        "foreign_ownership_pct": round(foreign_own, 2) if foreign_own is not None else None,
        "foreign_room_left_shares": int(cur_room) if cur_room is not None else None,
        "foreign_room_left_pct_of_limit": round(cur_room / total_room * 100, 1) if total_room and cur_room is not None else None,
        "listed_shares": int(listed) if listed else None,
        "bid_ask": {
            "bid": [(_f(g(f"bid_{i}_price")) or _f(g(f"bid_price_{i}")), _f(g(f"bid_{i}_volume")) or _f(g(f"bid_vol_{i}"))) for i in (1, 2, 3)],
            "ask": [(_f(g(f"ask_{i}_price")) or _f(g(f"ask_price_{i}")), _f(g(f"ask_{i}_volume")) or _f(g(f"ask_vol_{i}"))) for i in (1, 2, 3)],
        },
        "flags": flags,
    }
    return snap


# ----------------------------------------------------------------------------------------------
# 2. Hồ sơ công ty
# ----------------------------------------------------------------------------------------------
def _overview_raw(symbol: str) -> Optional[dict]:
    from vnstock.api.company import Company

    for src in ("kbs", "vci"):
        try:
            if not VNSTOCK.acquire(block=False):
                return None
            ov = Company(source=src, symbol=symbol).overview()
            if isinstance(ov, pd.DataFrame) and not ov.empty:
                d = ov.iloc[0].to_dict()
                d["_source"] = src
                return d
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[FA] overview {src} lỗi với {symbol}: {str(e)[:160]}")
    return None


def get_company_overview(symbol: str) -> Optional[dict]:
    cache_key = f"company_overview_{symbol}"
    cached = get_cache(cache_key, 7 * 86400)
    if cached:
        return cached
    ok, _ = VNSTOCK.available()
    raw = _with_timeout(_overview_raw, 15, symbol) if ok else None
    if not raw:
        shares = _with_timeout(SSI.listed_shares, 15, symbol) if SSI.configured() else None
        if not shares:
            return None
        out = {"outstanding_shares": shares, "charter_capital": None, "exchange": None, "listing_date": None,
               "auditor": None, "employees": None, "business_model": "", "as_of": "SSI SecuritiesDetails (CP niêm yết)"}
        set_cache(cache_key, out)
        return out

    def clean(t, n=700):
        t = str(t or "").replace("\r", " ").strip()
        return (t[:n] + "…") if len(t) > n else t

    out = {
        "outstanding_shares": _f(raw.get("outstanding_shares")) or _f(raw.get("issue_share")),
        "charter_capital": _f(raw.get("charter_capital")),
        "exchange": raw.get("exchange"),
        "listing_date": raw.get("listing_date"),
        "auditor": raw.get("auditor"),
        "employees": raw.get("number_of_employees"),
        "business_model": clean(raw.get("business_model") or raw.get("company_profile")),
        "as_of": str(raw.get("as_of_date") or ""),
    }
    set_cache(cache_key, out)
    return out


# ----------------------------------------------------------------------------------------------
# 3. Báo cáo tài chính (vnstock) — best effort
# ----------------------------------------------------------------------------------------------
def _df_brief(df, max_rows=35, max_cols=7, max_chars=2600) -> Optional[str]:
    if not isinstance(df, pd.DataFrame) or df.empty:
        return None
    d = df.copy()
    if isinstance(d.columns, pd.MultiIndex):
        d.columns = [" ".join(str(x) for x in c if str(x) != "nan").strip() for c in d.columns]
    d = d.iloc[:max_rows, :max_cols]
    txt = d.to_string(max_colwidth=28)
    return txt[:max_chars]


def _financials_raw(symbol: str) -> Optional[dict]:
    from vnstock.api.financial import Finance

    for src in ("kbs", "vci"):
        try:
            if not VNSTOCK.acquire(block=False):
                return None
            f = Finance(source=src, symbol=symbol, period="quarter")
            ratio = _df_brief(f.ratio())
            income = _df_brief(f.income_statement())
            if ratio or income:
                return {"source": src, "ratio": ratio, "income": income}
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[FA] Finance {src} lỗi với {symbol}: {str(e)[:160]}")
    return None


def get_financial_statements(symbol: str) -> Optional[dict]:
    cache_key = f"financials_{symbol}"
    cached = get_cache(cache_key, 86400)
    if cached:
        if cached.get("ok"):
            return cached
        if time.time() - cached.get("ts", 0) < 6 * 3600:
            return None
    if not VNSTOCK.available()[0]:
        return None
    raw = _with_timeout(_financials_raw, 25, symbol)
    # Lưu cả kết quả thất bại (negative cache 6h) để không làm chậm mọi request khi nguồn BCTC đang lỗi
    set_cache(cache_key, {"ok": bool(raw), **(raw or {})} if raw else {"ok": False, "ts": time.time()})
    return raw


# ----------------------------------------------------------------------------------------------
# 4. Tra cứu web có trích dẫn (Gemini + Google Search)
# ----------------------------------------------------------------------------------------------
SECTOR_METRICS = {
    "Ngân hàng": "NIM, tăng trưởng tín dụng, tỷ lệ nợ xấu (NPL) & nợ nhóm 2, tỷ lệ bao phủ nợ xấu, CASA, CAR, chi phí dự phòng",
    "Bất động sản Dân dụng": "doanh số bán hàng/presales, người mua trả tiền trước, hàng tồn kho, nợ vay/VCSH, trái phiếu sắp đáo hạn, pháp lý dự án trọng điểm",
    "BĐS Khu công nghiệp & Cao su": "diện tích đất KCN cho thuê mới, quỹ đất sẵn sàng cho thuê, giá thuê, doanh thu chưa thực hiện, FDI",
    "Thép & Vật liệu": "sản lượng tiêu thụ, giá HRC/thép xây dựng, giá quặng sắt & than cốc, biên lợi nhuận gộp, hàng tồn kho, phòng vệ thương mại",
    "Công nghệ & Viễn thông": "doanh thu khối công nghệ/nước ngoài, hợp đồng ký mới (backlog), biên lợi nhuận, tăng trưởng nhân sự",
    "Bán lẻ & Tiêu dùng (F&B)": "doanh thu theo chuỗi, doanh thu/cửa hàng (SSSG), số cửa hàng, biên gộp, vòng quay tồn kho",
    "Chứng khoán": "dư nợ cho vay ký quỹ (margin), kết quả tự doanh, thị phần môi giới, vốn chủ sở hữu, kế hoạch tăng vốn",
    "Dầu khí": "giá dầu Brent, sản lượng, backlog hợp đồng, giá thuê giàn khoan, tiến độ dự án Lô B – Ô Môn",
    "Hóa chất & Phân bón": "giá urê/DAP/phốt pho vàng, giá khí đầu vào, sản lượng, biên lợi nhuận gộp",
    "Cảng biển & Vận tải biển": "sản lượng container qua cảng, giá cước vận tải/thuê tàu, công suất khai thác",
    "Xây dựng & Đầu tư công": "giá trị hợp đồng tồn đọng (backlog), hợp đồng mới trúng thầu, biên gộp, khoản phải thu, giải ngân đầu tư công",
    "Điện & Nước": "sản lượng điện, giá bán bình quân, thủy văn (El Niño/La Niña), giá than/khí, dự án mới",
    "Thủy sản & Nông nghiệp": "giá xuất khẩu, sản lượng, thị trường xuất khẩu chính (Mỹ/Trung Quốc/EU), thuế chống bán phá giá",
    "Dệt may": "đơn hàng, giá trị xuất khẩu, thị trường chính, biên lợi nhuận gộp",
    "Hàng không & Dịch vụ sân bay": "lượng khách, giá nhiên liệu bay, tỷ giá, hệ số sử dụng ghế",
}

RESEARCH_PROMPT = """Bạn là chuyên viên nghiên cứu dữ liệu tại một công ty chứng khoán Việt Nam. Hôm nay là {today}.
Dùng Google Search để thu thập DỮ KIỆN MỚI NHẤT về cổ phiếu {symbol} ({company}) — ngành {sector}, sàn {exchange}.

NGUYÊN TẮC BẮT BUỘC:
- Chỉ ghi số liệu TÌM THẤY trên nguồn uy tín (CafeF, Vietstock, VnExpress, NDH, Thanh Niên, website doanh nghiệp, HOSE/HNX/UBCKNN,
  báo cáo của CTCK...). Mỗi số liệu phải kèm (Nguồn: tên trang, ngày đăng hoặc kỳ báo cáo).
- Không tìm thấy → ghi đúng chữ "Không tìm thấy". TUYỆT ĐỐI không ước lượng, không dùng trí nhớ, không bịa.
- Ưu tiên dữ liệu kỳ gần nhất; ghi rõ kỳ (VD: Q3/2026, 9T/2026). Đơn vị tỷ đồng, %, lần.

Trả lời bằng tiếng Việt, đúng các mục sau (gạch đầu dòng, ngắn gọn, nhiều số):
1. KẾT QUẢ KINH DOANH: doanh thu & lợi nhuận sau thuế công ty mẹ các quý gần nhất (tối đa 4 quý) kèm % so với cùng kỳ;
   lũy kế năm và % hoàn thành kế hoạch năm; nguyên nhân chính của tăng/giảm lợi nhuận; khoản lãi/lỗ bất thường nếu có.
2. ĐỊNH GIÁ & SỨC KHỎE TÀI CHÍNH: EPS 4 quý, P/E, P/B, ROE, ROA, nợ vay/VCSH (hoặc chỉ số đặc thù ngành), cổ tức gần nhất.
   Chỉ số đặc thù ngành cần tìm: {sector_metrics}.
3. SỰ KIỆN & CHẤT XÚC TÁC: sự kiện đã/ sắp diễn ra (GDKHQ, ĐHĐCĐ, phát hành thêm, mua lại cổ phiếu, dự án lớn, M&A,
   thay đổi chính sách ngành) — kèm ngày.
4. GIAO DỊCH CỦA KHỐI NGOẠI, TỰ DOANH, NỘI BỘ & CỔ ĐÔNG LỚN trong 1 tháng gần nhất (mua/bán ròng, đăng ký giao dịch).
5. KHUYẾN NGHỊ CỦA CÁC CÔNG TY CHỨNG KHOÁN: tên CTCK, ngày, khuyến nghị, giá mục tiêu, luận điểm chính (tối đa 4 báo cáo mới nhất).
6. RỦI RO ĐẶC THÙ: pháp lý, trái phiếu, nợ xấu, cảnh báo/kiểm soát, tranh chấp, rủi ro hàng hóa/tỷ giá.
7. BỐI CẢNH VĨ MÔ/NGÀNH 2 TUẦN GẦN NHẤT ảnh hưởng trực tiếp tới {symbol} (lãi suất, tỷ giá, chính sách, giá hàng hóa).
"""


def research_fundamentals_web(symbol: str, company: str, sector: str, exchange: str, today: str) -> Optional[dict]:
    """Gemini + Google Search → bản tóm tắt dữ kiện có nguồn. Cache 12 giờ."""
    if not llm_client.get_api_key():
        return None
    cache_key = f"web_research_{symbol}_{today.replace('/', '-')}"
    cached = get_cache(cache_key, 12 * 3600)
    if cached:
        return cached

    prompt = RESEARCH_PROMPT.format(
        today=today, symbol=symbol, company=company or symbol, sector=sector, exchange=exchange or "N/A",
        sector_metrics=SECTOR_METRICS.get(sector, "P/E, P/B, ROE, tăng trưởng EPS, dòng tiền kinh doanh, nợ vay/VCSH"),
    )
    try:
        # Không chờ thử lại khi bị giới hạn: tra cứu web là phần bổ trợ, không được làm chậm cả báo cáo
        text, model, resp = llm_client.generate(prompt, use_search=True, temperature=0.1, label=f"Research {symbol}",
                                                retry_on_rate_limit=False)
    except (llm_client.LLMAuthError, llm_client.LLMUnavailable) as e:
        logger.warning(f"[FA] Tra cứu web {symbol} thất bại: {str(e)[:300]}")
        return None

    out = {
        "text": text[:9000],
        "sources": llm_client.grounding_sources(resp)[:12],
        "model": model,
        "as_of": today,
    }
    set_cache(cache_key, out)
    return out


# ----------------------------------------------------------------------------------------------
# Định dạng cho prompt
# ----------------------------------------------------------------------------------------------
def format_company_dossier(snapshot: Optional[dict], overview: Optional[dict], close: float) -> str:
    lines = []
    if overview:
        shares = overview.get("outstanding_shares")
        mult = 1000.0 if close < 1000 else 1.0
        mcap = close * mult * shares / 1e9 if shares else None
        lines += [
            f"- Số cổ phiếu lưu hành: {shares:,.0f}" if shares else "- Số cổ phiếu lưu hành: N/A",
            f"- Vốn hóa (giá hiện tại × CP lưu hành): {mcap:,.0f} tỷ đồng" if mcap else "- Vốn hóa: N/A",
            f"- Sàn: {overview.get('exchange') or 'N/A'} | Niêm yết: {overview.get('listing_date') or 'N/A'} | Kiểm toán: {overview.get('auditor') or 'N/A'}",
        ]
        if overview.get("business_model"):
            lines.append(f"- Mô hình kinh doanh: {overview['business_model']}")
    else:
        lines.append("- Hồ sơ công ty: chưa tải được")

    if snapshot:
        lines.append(f"- Tên doanh nghiệp: {snapshot.get('company_name') or 'N/A'} | Nguồn bảng giá: {snapshot.get('source')}")
        session = str(snapshot.get("session") or "").upper()
        live_note = f" (phiên {snapshot.get('trading_date')} ĐANG DIỄN RA, trạng thái {session} — số liệu tạm tính)" \
            if session and session not in ("ENDED", "CLOSED") else ""
        lines.append(
            f"- Phiên gần nhất{live_note}: giá {snapshot.get('match_price')} | tham chiếu {snapshot.get('ref_price')} | trần {snapshot.get('ceiling')} | sàn {snapshot.get('floor')} | GTGD {snapshot.get('total_value_bn')} tỷ"
        )
        if snapshot.get("foreign_net_bn") is not None:
            lines.append(
                f"- KHỐI NGOẠI phiên gần nhất (dữ liệu thật từ bảng giá): mua {snapshot['foreign_buy_bn']} tỷ / bán {snapshot['foreign_sell_bn']} tỷ → "
                f"ròng {snapshot['foreign_net_bn']:+.2f} tỷ ({snapshot.get('foreign_net_volume') or 0:+,} cp)"
            )
        if snapshot.get("foreign_ownership_pct") is not None:
            lines.append(
                f"- Sở hữu nước ngoài ước tính: {snapshot['foreign_ownership_pct']}% | Room còn lại: {snapshot.get('foreign_room_left_shares'):,} cp "
                f"({snapshot.get('foreign_room_left_pct_of_limit')}% hạn mức)"
            )
        ba = snapshot.get("bid_ask") or {}
        if ba.get("bid"):
            fmt = lambda arr: ", ".join(f"{p:,.2f}×{v:,.0f}" if p < 1000 else f"{p:,.0f}×{v:,.0f}"  # noqa: E731
                                        for p, v in arr if p and v)
            lines.append(f"- Sổ lệnh cuối phiên: Dư mua [{fmt(ba['bid']) or 'trống'}] | Dư bán [{fmt(ba['ask']) or 'trống'}]")
        fh = snapshot.get("foreign_history")
        if fh:
            lines.append(
                f"- KHỐI NGOẠI NHIỀU PHIÊN (SSI, đến {fh['last_date']}): ròng 1 phiên {fh['net_1d_bn']:+.1f} tỷ | 5 phiên {fh['net_5d_bn']:+.1f} tỷ | "
                f"20 phiên {fh['net_20d_bn']:+.1f} tỷ | {fh['streak']}"
            )
            lines.append("  10 phiên gần nhất: " + "; ".join(fh["recent"]))
        for fl in snapshot.get("flags", []):
            lines.append(f"- ⚠️ {fl}")
    else:
        lines.append("- Bảng giá/khối ngoại phiên gần nhất: chưa tải được → THIẾU dữ liệu khối ngoại")
    return "\n".join(lines)
