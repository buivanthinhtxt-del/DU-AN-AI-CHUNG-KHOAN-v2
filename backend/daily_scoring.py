"""
Chấm điểm dự báo tự động hằng ngày (sau giờ đóng cửa 15h30 HOSE).

Với mỗi mã đã từng có khuyến nghị (forecast_records / cache forecast_audit):
  1. Lấy giá đóng cửa mới nhất.
  2. Đối chiếu dự báo gần nhất bằng audit_historical_forecast (Hướng / Biên độ / Thời điểm / Điều kiện).
  3. Lưu kết quả vào bảng forecast_scores (idempotent theo symbol + forecast_date + scored_date).

Cách kích hoạt:
  - Production (Render Free hay ngủ): GitHub Actions `.github/workflows/daily-score.yml`
    gọi POST /api/cron/daily-score kèm header X-Cron-Secret (đồng thời đánh thức container).
  - Máy chủ chạy liên tục: đặt ENABLE_INPROCESS_CRON=1 để chạy lịch nội bộ 15h45 các ngày T2–T6.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from data_fetcher import get_historical_data
from forecast_audit import audit_historical_forecast, list_tracked_symbols, save_forecast_score

logger = logging.getLogger("daily_scoring")

try:
    from zoneinfo import ZoneInfo

    VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")
except Exception:  # tzdata thiếu trên một số máy Windows
    from datetime import timezone

    VN_TZ = timezone(timedelta(hours=7))

MAX_SYMBOLS_PER_RUN = int(os.getenv("DAILY_SCORE_MAX_SYMBOLS", "200"))


def _score_one(symbol: str) -> Dict[str, Any]:
    try:
        df = get_historical_data(symbol, days=30, include_indicators=False)
        if df is None or df.empty:
            return {"symbol": symbol, "status": "no_data"}
        close = float(df["Close"].iloc[-1])
        bar_date = df.index[-1].strftime("%Y-%m-%d")
        audit = audit_historical_forecast(symbol, close, bar_date)
        if not audit.get("has_history"):
            return {"symbol": symbol, "status": "no_forecast"}
        saved = save_forecast_score(symbol, bar_date, audit)
        last = audit.get("last_audit") or {}
        return {
            "symbol": symbol,
            "status": "scored" if saved else "save_failed",
            "scored_date": bar_date,
            "close": round(close, 2),
            "forecast_date": last.get("forecast_date"),
            "overall_accuracy_pct": last.get("overall_accuracy_pct"),
            "verdict": last.get("verdict"),
        }
    except Exception as e:
        logger.warning(f"[daily_scoring] Lỗi chấm điểm {symbol}: {e}")
        return {"symbol": symbol, "status": "error", "error": str(e)[:200]}


def run_daily_scoring(symbols: Optional[List[str]] = None, max_workers: int = 4) -> Dict[str, Any]:
    """Chấm điểm toàn bộ danh mục đã khuyến nghị. Trả về bản tóm tắt."""
    started = datetime.now(VN_TZ)
    syms = [s.upper().strip() for s in (symbols or list_tracked_symbols()) if s and s.strip()]
    syms = sorted(set(syms))[:MAX_SYMBOLS_PER_RUN]

    results: List[Dict[str, Any]] = []
    if syms:
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
            results = list(ex.map(_score_one, syms))

    counts: Dict[str, int] = {}
    for r in results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    scored = [r for r in results if r["status"] == "scored"]
    avg_acc = (
        round(sum(float(r["overall_accuracy_pct"] or 0) for r in scored) / len(scored), 1) if scored else None
    )
    summary = {
        "started_at": started.isoformat(),
        "finished_at": datetime.now(VN_TZ).isoformat(),
        "total_symbols": len(syms),
        "counts": counts,
        "avg_accuracy_pct": avg_acc,
        "results": results,
    }
    logger.info(f"[daily_scoring] Hoàn tất: {len(syms)} mã, {counts}, độ chính xác TB={avg_acc}")
    return summary


def _next_run_after(now: datetime, hour: int = 15, minute: int = 45) -> datetime:
    """Thời điểm chạy kế tiếp: 15h45 giờ VN của ngày giao dịch (T2–T6) tiếp theo."""
    candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if candidate <= now:
        candidate += timedelta(days=1)
    while candidate.weekday() >= 5:  # 5 = T7, 6 = CN
        candidate += timedelta(days=1)
    return candidate


async def inprocess_scheduler_loop() -> None:
    """Vòng lặp lịch nội bộ (chỉ bật khi ENABLE_INPROCESS_CRON=1)."""
    while True:
        now = datetime.now(VN_TZ)
        nxt = _next_run_after(now)
        wait_s = max(1.0, (nxt - now).total_seconds())
        logger.info(f"[daily_scoring] Lịch nội bộ: lần chạy kế tiếp {nxt.isoformat()}")
        await asyncio.sleep(wait_s)
        try:
            await asyncio.to_thread(run_daily_scoring)
        except Exception as e:
            logger.error(f"[daily_scoring] Lỗi lịch nội bộ: {e}", exc_info=True)
