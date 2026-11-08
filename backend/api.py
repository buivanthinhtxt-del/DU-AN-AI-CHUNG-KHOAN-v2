import os
import sys
import io
import json
import shutil
import certifi
import tempfile
import asyncio
import logging
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
except Exception:
    pass

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("api")

import time
from collections import defaultdict
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import pandas as pd

import hashlib
import re
from datetime import datetime, timezone

from data_fetcher import get_historical_data, get_peers_performance, get_stock_sector, calculate_indicators
from news_fetcher import get_latest_news
from ai_analyzer import analyze_stock_data, MARKET_INDICES, build_analysis_context, _rule_based_report
from data_sources import PUBLIC, get_source_info, check_sources, market_session, provider_chain
from fundamental_fetcher import (
    get_price_board_snapshot,
    get_company_overview,
    get_financial_statements,
    research_fundamentals_web,
)
from forecast_audit import audit_historical_forecast, save_forecast_audit
from macro_fetcher import get_macro_data
from cache_manager import get_cache, set_cache
from database import init_db, get_watchlist, add_watchlist, remove_watchlist
from chat_engine import query_gemini_chat

# === FIX: Đường dẫn chứng chỉ SSL trên Windows có ký tự Unicode ===
try:
    _cert_src = certifi.where()
    _cert_dst = os.path.join(tempfile.gettempdir(), "cacert_ascii.pem")
    if not os.path.exists(_cert_dst):
        shutil.copy2(_cert_src, _cert_dst)
    os.environ["REQUESTS_CA_BUNDLE"] = _cert_dst
    os.environ["SSL_CERT_FILE"] = _cert_dst
except Exception:
    pass

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
load_dotenv(ROOT_DIR / ".env")
load_dotenv(BASE_DIR / ".env")

app = FastAPI(title="Nghiep Vu AI Workstation V5.0")

# --- Bộ giới hạn tần suất gọi AI theo IP (Bảo vệ hạn mức GEMINI_API_KEY khi mở Web Free 24/7) ---
AI_RATE_LIMIT_PER_HOUR = int(os.getenv("AI_RATE_LIMIT_PER_HOUR", "25"))
_ip_ai_timestamps: dict[str, list[float]] = defaultdict(list)


def _get_client_ip(request: Optional[Request]) -> str:
    if request is None:
        return "local"
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _check_ai_rate_limit(request: Optional[Request]):
    ip = _get_client_ip(request)
    if ip in ("127.0.0.1", "::1", "localhost", "local", "testclient"):
        return
    now = time.time()
    window = 3600.0
    history = [ts for ts in _ip_ai_timestamps[ip] if now - ts < window]
    if len(history) >= AI_RATE_LIMIT_PER_HOUR:
        raise HTTPException(
            status_code=429,
            detail=f"Bạn đã sử dụng hết {AI_RATE_LIMIT_PER_HOUR} lượt phân tích AI chuyên sâu miễn phí trong 1 giờ qua. Vui lòng xem bản Định lượng 6 bước tức thì hoặc thử lại sau ít phút.",
        )
    history.append(now)
    _ip_ai_timestamps[ip] = history


@app.api_route("/api/health", methods=["GET", "HEAD"])
async def api_health():
    """Endpoint kiểm tra trạng thái sống 24/7 cho Render / Hugging Face Spaces / UptimeRobot."""
    return {
        "status": "ok",
        "service": "nghiep-vu-ai-workstation-v5",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

# [P0-SEC-01] Cấu hình CORS chuẩn RFC 6454: chỉ định danh sách Origin tin cậy, không dùng wildcard "*" khi có credentials
cors_origins_env = os.getenv("ALLOWED_ORIGINS", "")
if cors_origins_env:
    allowed_origins = [o.strip() for o in cors_origins_env.split(",") if o.strip()]
else:
    allowed_origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    # Khởi tạo database non-blocking
    await asyncio.to_thread(init_db)


class AnalyzeRequest(BaseModel):
    symbol: str
    target_date: Optional[str] = None
    force_refresh: Optional[bool] = False
    # Hồ sơ nhà đầu tư (tùy chọn) — giúp AI đưa lời khuyên đúng hoàn cảnh
    horizon: Optional[str] = None          # "Lướt sóng (1–4 tuần)" | "Swing (1–3 tháng)" | "Trung hạn (3–12 tháng)" | "Dài hạn (> 1 năm)"
    risk_profile: Optional[str] = None     # "Thấp" | "Trung bình" | "Cao"
    cost_basis: Optional[float] = None     # Giá vốn nếu đang nắm giữ (cùng đơn vị giá hiển thị)
    position_pct: Optional[float] = None   # Tỷ trọng hiện tại trong danh mục (%)


class WatchlistRequest(BaseModel):
    symbol: str


class ConfigRequest(BaseModel):
    gemini_api_key: str


class ChatRequest(BaseModel):
    message: str
    history: Optional[list[dict]] = []
    symbol: Optional[str] = None


def _df_to_clean_records(df: pd.DataFrame) -> list[dict]:
    """Chuyển DataFrame (kèm chỉ báo TA) sang list dict sạch, không chứa NaN/Inf."""
    if df is None or df.empty:
        return []
    df_reset = df.reset_index()
    if "Date" in df_reset.columns:
        df_reset["Date"] = pd.to_datetime(df_reset["Date"]).dt.strftime("%Y-%m-%d")
    num_cols = df_reset.select_dtypes(include=["number"]).columns
    df_reset[num_cols] = df_reset[num_cols].replace([float("inf"), float("-inf")], 0).fillna(0).round(3)
    return df_reset.to_dict(orient="records")


@app.post("/api/market_data")
async def fetch_market_data(req: AnalyzeRequest):
    symbol = req.symbol.upper().strip()
    target_date = req.target_date

    cache_key = f"market_data_v3_{symbol}_{target_date}"
    if not req.force_refresh:
        cached_data = get_cache(cache_key, 1800)  # 30 mins
        if cached_data:
            return cached_data

    try:
        days = 730  # 2 năm: đủ cho MA200, đỉnh/đáy 52 tuần và thống kê xác suất nền
        macro_cache_key = f"macro_data_v2_{target_date}"
        macro_cached = None if req.force_refresh else get_cache(macro_cache_key, 900)

        # [P0-PERF-01] Chuyển đổi các tác vụ I/O mạng nặng sang asyncio.to_thread không chặn Event Loop
        tasks = [
            asyncio.to_thread(get_historical_data, symbol, days, target_date, True),
            asyncio.to_thread(get_peers_performance, symbol, target_date),
            asyncio.to_thread(get_latest_news, symbol),
            asyncio.to_thread(get_historical_data, "VNINDEX", 400, target_date, True),
        ]
        if not macro_cached:
            tasks.append(asyncio.to_thread(get_macro_data, target_date, False))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        df = results[0] if not isinstance(results[0], Exception) else None
        if isinstance(results[0], Exception):
            logger.error(f"[!] Lỗi tải historical_data cho {symbol}: {results[0]}")

        peers_info = results[1] if not isinstance(results[1], Exception) and results[1] else {}
        news_items = results[2] if not isinstance(results[2], Exception) and results[2] else []
        vnindex_df = results[3] if len(results) > 3 and not isinstance(results[3], Exception) else None

        if macro_cached:
            macro_info = macro_cached
        else:
            macro_res = results[4] if len(results) > 4 and not isinstance(results[4], Exception) else None
            macro_info = macro_res or {"VNINDEX": "N/A", "VN30": "N/A", "GOLD": "N/A", "OIL": "N/A", "USD_VND": "N/A"}
            set_cache(macro_cache_key, macro_info)

        if df is None or df.empty:
            raise HTTPException(
                status_code=404,
                detail=f"Không tìm thấy dữ liệu lịch sử hoặc mã cổ phiếu '{symbol}' không hợp lệ.",
            )

        historical_records = _df_to_clean_records(df)
        latest_row = historical_records[-1] if historical_records else {}
        sector_name = get_stock_sector(symbol)

        # Tính nhanh Báo cáo Định lượng Tức thì (Instant Quant Baseline) để giao diện hiển thị ngay lập tức (<1s)
        instant_report = None
        try:
            last_close = float(df["Close"].iloc[-1])
            last_date_str = df.index[-1].strftime("%Y-%m-%d") if not df.empty else None
            audit_res = await asyncio.to_thread(audit_historical_forecast, symbol, last_close, last_date_str)
            mk_dfs = {"VNINDEX": vnindex_df} if (vnindex_df is not None and not vnindex_df.empty) else {}
            profile = {
                "horizon": req.horizon,
                "risk_profile": req.risk_profile,
                "cost_basis": req.cost_basis,
                "position_pct": req.position_pct,
            }
            ctx = await asyncio.to_thread(
                build_analysis_context,
                symbol=symbol,
                df=df,
                news_items=news_items,
                peers_info=peers_info,
                macro_info=macro_info,
                market_data=mk_dfs,
                profile=profile,
                extras={"data_source": get_source_info(symbol), "forecast_audit": audit_res},
                historical=bool(target_date),
            )
            instant_report = await asyncio.to_thread(
                _rule_based_report,
                ctx,
                "Bản Phân tích Định lượng Tức thì (Đang chạy thẩm định sâu bằng Hội đồng AI...)",
            )
        except Exception as qe_err:
            logger.warning(f"[!] Lỗi tạo instant_report cho {symbol}: {qe_err}")

        payload = {
            "symbol": symbol,
            "sector": sector_name,
            "target_date": target_date,
            "history": historical_records,
            "indicators": {
                "EMA10": latest_row.get("EMA10", 0),
                "SMA20": latest_row.get("SMA20", 0),
                "MA50": latest_row.get("MA50", 0),
                "RSI": latest_row.get("RSI", 50),
                "MACD": latest_row.get("MACD", 0),
                "Signal": latest_row.get("Signal", 0),
                "Histogram": latest_row.get("Histogram", 0),
                "Volatility": latest_row.get("Volatility", 0),
                "VolMA20": latest_row.get("VolMA20", 0),
            },
            "macro": macro_info,
            "peers": peers_info,
            "news": news_items,
            "data_source": get_source_info(symbol),
            "instant_report": instant_report,
        }

        set_cache(cache_key, payload)
        return payload

    except HTTPException:
        raise
    except Exception as e:
        # [P0-SEC-01] Ghi log lỗi nội bộ và không làm lộ đường dẫn ổ đĩa tuyệt đối Windows ra client
        logger.error(f"[!] Lỗi khi xử lý market_data cho {symbol}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Lỗi xử lý dữ liệu thị trường. Vui lòng thử lại sau.")


@app.post("/api/ai_report")
async def fetch_ai_report(req: AnalyzeRequest, request: Request = None):
    symbol = req.symbol.upper().strip()
    target_date = req.target_date

    profile = {
        "horizon": req.horizon,
        "risk_profile": req.risk_profile,
        "cost_basis": req.cost_basis,
        "position_pct": req.position_pct,
    }
    profile_key = hashlib.md5(json.dumps(profile, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:8]
    cache_key = f"ai_report_v3_{symbol}_{target_date}_{profile_key}"
    if not req.force_refresh:
        cached_report = get_cache(cache_key, 6 * 3600)  # 6 giờ
        if cached_report:
            return cached_report

    # Kiểm tra giới hạn lượt gọi AI trực tiếp theo IP khi không có sẵn trong Cache
    _check_ai_rate_limit(request)

    try:
        mk_cache_key = f"market_data_v3_{symbol}_{target_date}"
        mk_data = get_cache(mk_cache_key, 3600)
        if not mk_data:
            mk_data = await fetch_market_data(req)

        df_records = mk_data.get("history", [])
        if not df_records:
            raise HTTPException(status_code=404, detail="Không có dữ liệu lịch sử để phân tích.")

        df = pd.DataFrame(df_records)
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.set_index("Date")
        last_close = float(df["Close"].iloc[-1])
        historical = bool(target_date)

        # Bảng giá phiên gần nhất trước (nhanh, cho biết tên doanh nghiệp để tra cứu web chính xác hơn).
        # Khi phân tích một ngày trong quá khứ: KHÔNG dùng bảng giá / tra cứu web hiện tại (tránh look-ahead).
        snapshot = None
        if not historical:
            snapshot = await asyncio.to_thread(get_price_board_snapshot, symbol, last_close)

        async def _none():
            return None

        sector = get_stock_sector(symbol)
        today = datetime.now().strftime("%d/%m/%Y")
        results = await asyncio.gather(
            asyncio.to_thread(get_historical_data, "VNINDEX", 730, target_date, True),
            asyncio.to_thread(get_historical_data, "VN30", 400, target_date, True),
            asyncio.to_thread(get_company_overview, symbol),
            asyncio.to_thread(get_financial_statements, symbol) if not historical else _none(),
            asyncio.to_thread(
                research_fundamentals_web, symbol,
                (snapshot or {}).get("company_name") or symbol, sector, (snapshot or {}).get("exchange") or "", today,
            ) if not historical else _none(),
            return_exceptions=True,
        )
        ok = lambda r: None if isinstance(r, Exception) else r  # noqa: E731
        vnindex_res, vn30_res, overview, financials, research = (ok(r) for r in results)
        for name, r in zip(("VNINDEX", "VN30", "overview", "financials", "research"), results):
            if isinstance(r, Exception):
                logger.warning(f"[!] {name} lỗi khi phân tích {symbol}: {r}")

        market_index_dfs = {}
        if vnindex_res is not None and not vnindex_res.empty:
            market_index_dfs["VNINDEX"] = vnindex_res
        if vn30_res is not None and not vn30_res.empty:
            market_index_dfs["VN30"] = vn30_res

        # Tự động đọc và đối chiếu dự báo cũ (Forecast Audit Self-Correction Loop)
        last_date_str = df.index[-1].strftime("%Y-%m-%d") if not df.empty else None
        audit_res = await asyncio.to_thread(audit_historical_forecast, symbol, last_close, last_date_str)

        # [P0-PERF-01] Gọi analyze_stock_data qua asyncio.to_thread (giải phóng Event Loop trong khi gọi Gemini)
        analysis_json_str = await asyncio.to_thread(
            analyze_stock_data,
            symbol=symbol,
            df=df,
            news_items=mk_data.get("news", []),
            peers_info=mk_data.get("peers", {}),
            macro_info=mk_data.get("macro", {}),
            market_data=market_index_dfs,
            profile=profile,
            extras={"snapshot": snapshot, "overview": overview, "financials": financials, "research": research,
                    "data_source": mk_data.get("data_source"), "forecast_audit": audit_res},
            historical=historical,
        )

        ai_data = json.loads(analysis_json_str)
        # Gắn thẻ đối chiếu dự báo cũ vào ai_data và payload phản hồi
        if "forecast_audit" not in ai_data or not ai_data.get("forecast_audit"):
            ai_data["forecast_audit"] = audit_res
        payload = {"ai_report": ai_data, "forecast_audit": audit_res}

        # Tự động lưu bản ghi dự báo gốc mới vào cache forecast_audit
        await asyncio.to_thread(save_forecast_audit, symbol, ai_data, last_close, last_date_str)

        # Chỉ lưu cache khi báo cáo do AI tạo (bản định lượng dự phòng sẽ được thử lại AI ở lần sau)
        if str(ai_data.get("engine", "")).startswith("gemini:"):
            set_cache(cache_key, payload)

        return payload

    except HTTPException:
        raise
    except Exception as e:
        # [P0-SEC-01] Ghi log lỗi nội bộ, bảo mật thông tin
        logger.error(f"[!] Lỗi khi xử lý ai_report cho {symbol}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Lỗi phân tích AI hoặc máy chủ xử lý dữ liệu. Vui lòng thử lại sau.")


@app.get("/api/data_sources/health")
async def api_data_sources_health(symbol: str = "HPG"):
    """Kiểm tra từng nguồn dữ liệu giá (SSI / vnstock / kho cục bộ) — dùng để biết nguồn nào còn sống."""
    sym = symbol.upper().strip()[:10]
    try:
        return {"symbol": sym, "chain": [p.name for p in provider_chain()],
                "sources": await asyncio.to_thread(check_sources, sym)}
    except Exception as e:
        logger.error(f"[!] Lỗi kiểm tra nguồn dữ liệu: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Không kiểm tra được nguồn dữ liệu.")


# --- Thời gian thực (API công khai, không chính thức: bảng giá Vietcap + nến trong phiên DNSE/VNDirect/SSI iBoard) ---
_SYMBOL_RE = re.compile(r"^[A-Z0-9]{2,12}$")


@app.get("/api/realtime/quote")
async def api_realtime_quote(symbols: str = "HPG"):
    """Bảng giá tức thời cho tối đa 30 mã (phân tách bằng dấu phẩy). Giá: nghìn đồng; giá trị: tỷ đồng."""
    syms = [s.strip().upper() for s in symbols.split(",") if s.strip()][:30]
    bad = [s for s in syms if not _SYMBOL_RE.match(s)]
    if not syms or bad:
        raise HTTPException(status_code=400, detail=f"Mã không hợp lệ: {', '.join(bad) or '(trống)'}")
    try:
        quotes = await asyncio.to_thread(PUBLIC.price_board, syms)
    except Exception as e:
        logger.warning(f"[realtime] bảng giá lỗi: {e}")
        raise HTTPException(status_code=502, detail="Không lấy được bảng giá trực tiếp (nguồn Vietcap đang lỗi hoặc bị chặn).")
    return {"quotes": quotes, "missing": [s for s in syms if s not in quotes],
            "market": market_session(), "source": "vci"}


@app.get("/api/realtime/intraday/{symbol}")
async def api_realtime_intraday(symbol: str, resolution: str = "1"):
    """Nến trong phiên gần nhất. `time` = giờ Việt Nam ghi như UTC (để biểu đồ hiển thị đúng giờ VN)."""
    sym = symbol.upper().strip()
    if not _SYMBOL_RE.match(sym):
        raise HTTPException(status_code=400, detail="Mã không hợp lệ")
    if resolution not in PUBLIC.INTRADAY_RESOLUTIONS:
        raise HTTPException(status_code=400, detail=f"Khung chỉ nhận: {', '.join(PUBLIC.INTRADAY_RESOLUTIONS)} (phút)")
    try:
        df = await asyncio.to_thread(PUBLIC.intraday, sym, resolution)
    except Exception as e:
        logger.warning(f"[realtime] nến trong phiên {sym} lỗi: {e}")
        raise HTTPException(status_code=502, detail="Không lấy được nến trong phiên từ các nguồn công khai.")
    bars = [
        {"time": int(ts.replace(tzinfo=timezone.utc).timestamp()), "open": float(r.Open), "high": float(r.High),
         "low": float(r.Low), "close": float(r.Close), "volume": float(r.Volume or 0)}
        for ts, r in df.iterrows()
    ] if not df.empty else []
    return {"symbol": sym, "resolution": resolution, "date": df.index[-1].strftime("%Y-%m-%d") if bars else None,
            "bars": bars, "source": df.attrs.get("endpoint") if bars else None, "market": market_session()}


# --- Watchlist APIs (hoàn toàn non-blocking với asyncio.to_thread) ---
@app.get("/api/watchlist")
async def api_get_watchlist():
    try:
        return await asyncio.to_thread(get_watchlist)
    except Exception as e:
        logger.error(f"[!] Lỗi đọc watchlist: {e}", exc_info=True)
        return []


@app.post("/api/watchlist")
async def api_add_watchlist(req: WatchlistRequest):
    try:
        await asyncio.to_thread(add_watchlist, req.symbol)
        return {"status": "success"}
    except Exception as e:
        logger.error(f"[!] Lỗi thêm watchlist: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Không thể lưu mã vào danh mục theo dõi.")


@app.delete("/api/watchlist/{symbol}")
async def api_remove_watchlist(symbol: str):
    try:
        await asyncio.to_thread(remove_watchlist, symbol)
        return {"status": "success"}
    except Exception as e:
        logger.error(f"[!] Lỗi xóa watchlist: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Không thể xóa mã khỏi danh mục theo dõi.")


# --- AI Gemini Real-time Search & Chat API (Non-blocking) ---
@app.post("/api/chat")
async def api_chat_query(req: ChatRequest, request: Request = None):
    """
    Endpoint tra cứu thông tin chứng khoán thời gian thực với AI Gemini và Google Search Grounding.
    Tự động gắn kết bối cảnh cổ phiếu đang theo dõi, tin tức tài chính và dữ liệu vĩ mô.
    """
    if not req.message or not req.message.strip():
        raise HTTPException(status_code=400, detail="Nội dung câu hỏi không được để trống.")
    _check_ai_rate_limit(request)
    try:
        result = await asyncio.to_thread(
            query_gemini_chat,
            message=req.message,
            history=req.history,
            current_symbol=req.symbol,
        )
        return result
    except Exception as e:
        logger.error(f"[!] Lỗi api_chat_query: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Không thể hoàn thành tra cứu AI vào lúc này.")


# --- PHỤC VỤ GIAO DIỆN WEB REACT TÍCH HỢP (ALL-IN-ONE CLOUD WORKSTATION) ---
WEB_DIST_DIR = ROOT_DIR / "web" / "dist"
if (WEB_DIST_DIR / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=str(WEB_DIST_DIR / "assets")), name="web_assets")


@app.get("/fiintrade_demo.html", include_in_schema=False)
async def serve_demo_html():
    demo_dist = WEB_DIST_DIR / "fiintrade_demo.html"
    if demo_dist.is_file():
        return FileResponse(str(demo_dist))
    demo_root = ROOT_DIR / "fiintrade_demo.html"
    if demo_root.is_file():
        return FileResponse(str(demo_root))
    raise HTTPException(status_code=404, detail="Không tìm thấy trang fiintrade_demo.html")


@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa_frontend(full_path: str):
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="API endpoint không tồn tại.")
    if WEB_DIST_DIR.is_dir():
        candidate = (WEB_DIST_DIR / full_path).resolve()
        if str(candidate).startswith(str(WEB_DIST_DIR.resolve())) and candidate.is_file():
            return FileResponse(str(candidate))
        index_file = WEB_DIST_DIR / "index.html"
        if index_file.is_file():
            return FileResponse(str(index_file))
    return {
        "service": "Nghiệp Vụ AI Workstation V5.0 API",
        "status": "running",
        "docs": "/docs",
        "health": "/api/health",
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("api:app", host="0.0.0.0", port=port, reload=False)
