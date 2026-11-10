"""
Shark Tracker bằng dữ liệu khớp lệnh THẬT từng lô (tick-by-tick) — thay cho bản mô phỏng.

Nguồn: bảng khớp lệnh công khai của Vietcap (trading.vietcap.com.vn, endpoint LEData), mỗi trang 100 lệnh,
phân trang lùi theo truncTime. Mỗi lệnh có matchType: 'b' (bên mua chủ động), 's' (bên bán chủ động),
'unknown' (khớp định kỳ ATO/ATC, không xác định chủ động).

Phân tầng theo GIÁ TRỊ lệnh khớp (khối lượng × giá):
  🦈 Cá Mập  > 1 tỷ đồng      🐺 Sói  200 triệu – 1 tỷ      🐟 Cá Con < 200 triệu

Giới hạn trung thực:
  - Tải tuần tự, có giới hạn số trang (SHARK_MAX_PAGES, mặc định 60 ≈ 6.000 lệnh) để không gây tải cho nguồn;
    mã thanh khoản cao có thể chỉ phủ một phần phiên → luôn trả "coverage_pct" (tỷ lệ khối lượng đã phân tích /
    tổng khối lượng khớp của phiên) để người dùng biết độ phủ.
  - "Chủ động mua/bán" là suy luận theo phía khớp lệnh, không phải danh tính nhà đầu tư.
"""

from __future__ import annotations

import logging
import os
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import requests

from cache_manager import get_cache, set_cache

logger = logging.getLogger("shark_tracker")

LE_URL = "https://trading.vietcap.com.vn/api/market-watch/LEData/getAll"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Referer": "https://trading.vietcap.com.vn/",
    "Origin": "https://trading.vietcap.com.vn",
}
PAGE_SIZE = 100
MAX_PAGES = int(os.getenv("SHARK_MAX_PAGES", "60"))
PAGE_DELAY_S = float(os.getenv("SHARK_PAGE_DELAY_S", "0.15"))
SHARK_MIN_VND = 1_000_000_000
WOLF_MIN_VND = 200_000_000
VN_TZ = timezone(timedelta(hours=7))

TIERS = {
    "shark": {"label": "Cá Mập", "range": "> 1 tỷ"},
    "wolf": {"label": "Sói", "range": "200 triệu – 1 tỷ"},
    "sheep": {"label": "Cá Con", "range": "< 200 triệu"},
}


def classify_value(value_vnd: float) -> str:
    if value_vnd > SHARK_MIN_VND:
        return "shark"
    if value_vnd >= WOLF_MIN_VND:
        return "wolf"
    return "sheep"


def _price_to_vnd(price: float) -> float:
    # Vietcap trả giá theo đồng (vd 21250); phòng trường hợp nguồn trả nghìn đồng (vd 21.25)
    return price * 1000 if price < 1000 else price


def fetch_ticks(symbol: str, max_pages: int = MAX_PAGES) -> Dict[str, Any]:
    """Tải tuần tự các lệnh khớp của phiên gần nhất (mới nhất trước)."""
    session = requests.Session()
    session.headers.update(_HEADERS)
    ticks: List[dict] = []
    seen = set()
    trunc_time = None
    session_day = None
    complete = False
    for page in range(max_pages):
        resp = session.post(LE_URL, json={"symbol": symbol, "limit": PAGE_SIZE, "truncTime": trunc_time}, timeout=15)
        resp.raise_for_status()
        rows = resp.json() or []
        if not isinstance(rows, list) or not rows:
            complete = True
            break
        stop = False
        for r in rows:
            if r.get("id") in seen:
                continue
            day = (r.get("createdAt") or "")[:10]
            session_day = session_day or day
            if day != session_day:  # đã lùi sang phiên trước
                stop = True
                break
            seen.add(r.get("id"))
            ticks.append(r)
        if stop or len(rows) < PAGE_SIZE:
            complete = True
            break
        trunc_time = rows[-1].get("truncTime")
        if PAGE_DELAY_S:
            time.sleep(PAGE_DELAY_S)
    return {"ticks": ticks, "complete": complete, "session_day": session_day}


def aggregate_ticks(ticks: List[dict]) -> Dict[str, Any]:
    """Tổng hợp dòng tiền theo tầng lệnh & phía chủ động. Hàm thuần."""
    tiers: Dict[str, Dict[str, float]] = {
        k: {"buy_value_bn": 0.0, "sell_value_bn": 0.0, "unknown_value_bn": 0.0, "count": 0} for k in TIERS
    }
    total_vol = 0.0
    largest: List[dict] = []
    for t in ticks:
        vol = float(t.get("matchVol") or 0)
        price = _price_to_vnd(float(t.get("matchPrice") or 0))
        value = vol * price
        tier = classify_value(value)
        side = {"b": "buy", "s": "sell"}.get(t.get("matchType"), "unknown")
        tiers[tier][f"{side}_value_bn"] += value / 1e9
        tiers[tier]["count"] += 1
        total_vol += vol
        if tier == "shark":
            largest.append({"time": (t.get("createdAt") or "")[11:19], "side": side, "volume": int(vol),
                            "price": price, "value_bn": round(value / 1e9, 2)})
    out = {}
    for k, v in tiers.items():
        out[k] = {
            **TIERS[k],
            "count": v["count"],
            "buy_value_bn": round(v["buy_value_bn"], 2),
            "sell_value_bn": round(v["sell_value_bn"], 2),
            "unknown_value_bn": round(v["unknown_value_bn"], 2),
            "net_value_bn": round(v["buy_value_bn"] - v["sell_value_bn"], 2),
        }
    largest.sort(key=lambda x: x["value_bn"], reverse=True)

    shark_net, sheep_net = out["shark"]["net_value_bn"], out["sheep"]["net_value_bn"]
    if shark_net > 0 and sheep_net < 0:
        signal = "CA_MAP_GOM_CA_CON_BAN"
        note = "Cá Mập mua chủ động ròng trong khi Cá Con bán ròng — dấu hiệu tích lũy (cần xác nhận nhiều phiên)."
    elif shark_net < 0 and sheep_net > 0:
        signal = "CA_MAP_XA_CA_CON_MUA"
        note = "Cá Mập bán chủ động ròng trong khi Cá Con mua đuổi — cảnh báo phân phối."
    elif shark_net > 0:
        signal = "CA_MAP_MUA_RONG"
        note = "Dòng lệnh lớn nghiêng về mua chủ động."
    elif shark_net < 0:
        signal = "CA_MAP_BAN_RONG"
        note = "Dòng lệnh lớn nghiêng về bán chủ động."
    else:
        signal = "TRUNG_TINH"
        note = "Không có chênh lệch đáng kể ở nhóm lệnh lớn."
    return {"tiers": out, "analyzed_volume": int(total_vol), "signal": signal, "signal_note": note,
            "largest_shark_orders": largest[:10]}


def get_shark_flow(symbol: str, force_refresh: bool = False) -> Dict[str, Any]:
    """Shark Tracker phiên gần nhất. Cache 2 phút trong giờ giao dịch, 6 giờ ngoài giờ."""
    sym = (symbol or "").upper().strip()
    now = datetime.now(VN_TZ)
    in_session = now.weekday() < 5 and (9 <= now.hour < 15)
    ttl = 120 if in_session else 6 * 3600
    key = f"shark_flow_v1_{sym}"
    if not force_refresh:
        cached = get_cache(key, ttl)
        if cached:
            return cached
    t0 = time.time()
    try:
        raw = fetch_ticks(sym)
        ticks = raw["ticks"]
        if not ticks:
            raise ValueError("nguồn không trả lệnh khớp nào (mã không giao dịch hoặc ngoài dữ liệu)")
        agg = aggregate_ticks(ticks)
        session_volume = float(ticks[0].get("accumulatedVolume") or 0)
        coverage = round(min(100.0, agg["analyzed_volume"] / session_volume * 100), 1) if session_volume else None
        result = {
            "available": True,
            "is_mock": False,
            "symbol": sym,
            "source": "Vietcap — bảng khớp lệnh từng lô (công khai)",
            "session_date": raw["session_day"],
            "first_tick_utc": ticks[-1].get("createdAt"),
            "last_tick_utc": ticks[0].get("createdAt"),
            "tick_count": len(ticks),
            "session_volume": int(session_volume),
            "coverage_pct": coverage,
            "complete_session": bool(raw["complete"]) and (coverage or 0) >= 99,
            "fetch_seconds": round(time.time() - t0, 1),
            "thresholds_vnd": {"shark": SHARK_MIN_VND, "wolf": WOLF_MIN_VND},
            "caveat": "Chủ động mua/bán suy ra từ phía khớp lệnh; không xác định danh tính nhà đầu tư.",
            **agg,
        }
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[shark_tracker] Lỗi tải tick {sym}: {e}")
        # Không cache lỗi (TTL ngoài giờ là 6 giờ) để lần gọi sau thử lại nguồn
        return {"available": False, "is_mock": False, "symbol": sym, "error": str(e)[:200]}
    set_cache(key, result)
    return result
