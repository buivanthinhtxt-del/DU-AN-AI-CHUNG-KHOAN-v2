"""
Lớp nguồn dữ liệu giá ĐA NHÀ CUNG CẤP — để hệ thống không chết theo một nguồn duy nhất.

Bối cảnh: vnstock thông báo các lớp "thế hệ 4" (Quote.history, Company.overview, Finance, Trading.price_board — chính là
các lớp dự án đang dùng) ngừng hoạt động từ 10/11/2026 và khuyến nghị chuyển sang API của công ty chứng khoán nơi
nhà đầu tư có tài khoản, hoặc dữ liệu tự chuẩn bị.

Chuỗi dự phòng (cấu hình bằng biến môi trường DATA_SOURCES, mặc định "ssi,vnstock,local"):
1. ssi     — SSI FastConnect Data API (chính thức, miễn phí cho chủ tài khoản SSI; lấy ConsumerID/ConsumerSecret
             trên iBoard → Dịch vụ API). Chỉ bật khi có SSI_CONSUMER_ID & SSI_CONSUMER_SECRET trong .env.
2. vnstock — thư viện hiện tại; có "cầu dao" tự ngắt 30 phút sau 3 lần lỗi liên tiếp để không làm chậm request.
3. local   — kho CSV cục bộ backend/data/ohlcv/<MÃ>.csv. Mọi lần tải thành công từ nguồn khác được tự động GHI
             VÀO kho này, nên khi mọi nguồn trực tuyến đều hỏng vẫn còn lịch sử giá để phân tích (có cảnh báo dữ liệu cũ).
             Có thể tự thả file CSV (Date,Open,High,Low,Close,Volume; giá nghìn đồng) vào thư mục này.

Đơn vị chuẩn hóa: cổ phiếu theo NGHÌN ĐỒNG (21.2 = 21.200đ), chỉ số theo điểm.
"""
from __future__ import annotations

import concurrent.futures
import logging
import os
import tempfile
import threading
import time
from collections import deque
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd
import requests
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR.parent / ".env")
load_dotenv(BASE_DIR / ".env")

logger = logging.getLogger("data_sources")

STORE_DIR = Path(os.getenv("LOCAL_OHLCV_DIR", str(BASE_DIR / "data" / "ohlcv")))
INDEX_SYMBOLS = {"VNINDEX", "VN30", "HNXINDEX", "HNX30", "UPCOMINDEX", "VN100", "VNMIDCAP", "VNSML"}
OHLCV = ["Open", "High", "Low", "Close", "Volume"]

_POOL = concurrent.futures.ThreadPoolExecutor(max_workers=8, thread_name_prefix="ds")
_last_source: dict[str, dict] = {}
_lock = threading.Lock()


def _normalize(df: pd.DataFrame, symbol: str) -> pd.DataFrame:
    """Chuẩn hóa về index Date tăng dần, cột OHLCV dạng float, giá cổ phiếu theo nghìn đồng."""
    df = df.copy()
    df = df[[c for c in OHLCV if c in df.columns]].apply(pd.to_numeric, errors="coerce")
    df = df.dropna(subset=["Close"])
    df.index = pd.to_datetime(df.index).normalize()
    df = df[~df.index.duplicated(keep="last")].sort_index()
    if "Volume" not in df.columns:
        df["Volume"] = 0.0
    for c in ("Open", "High", "Low"):
        if c not in df.columns:
            df[c] = df["Close"]
    if symbol not in INDEX_SYMBOLS and not df.empty and float(df["Close"].median()) > 1000:
        df[["Open", "High", "Low", "Close"]] = df[["Open", "High", "Low", "Close"]] / 1000.0
    return df[OHLCV]


# ==============================================================================================
# Provider: SSI FastConnect Data (API chính thức)
# ==============================================================================================
class SSIProvider:
    name = "ssi"
    base_url = os.getenv("SSI_FC_DATA_URL", "https://fc-data.ssi.com.vn/").rstrip("/") + "/"
    TOKEN_TTL_S = 7 * 3600  # token sống ~8 giờ; làm mới sớm

    def __init__(self):
        self.consumer_id = (os.getenv("SSI_CONSUMER_ID") or "").strip()
        self.consumer_secret = (os.getenv("SSI_CONSUMER_SECRET") or "").strip()
        self._token: Optional[str] = None
        self._token_ts = 0.0
        self._tlock = threading.Lock()
        self.session = requests.Session()

    def configured(self) -> bool:
        return bool(self.consumer_id and self.consumer_secret)

    def available(self) -> tuple[bool, str]:
        if not self.configured():
            return False, "Chưa cấu hình SSI_CONSUMER_ID / SSI_CONSUMER_SECRET trong .env"
        return True, "ok"

    # --- HTTP ---
    def _get_token(self, force: bool = False) -> str:
        with self._tlock:
            if self._token and not force and time.time() - self._token_ts < self.TOKEN_TTL_S:
                return self._token
            r = self.session.post(
                self.base_url + "api/v2/Market/AccessToken",
                json={"consumerID": self.consumer_id, "consumerSecret": self.consumer_secret},
                timeout=15,
            )
            r.raise_for_status()
            body = r.json()
            token = (body.get("data") or {}).get("accessToken") or body.get("accessToken")
            if not token:
                raise RuntimeError(f"SSI không trả accessToken: {str(body.get('message'))[:200]}")
            self._token, self._token_ts = token, time.time()
            return token

    def _get(self, path: str, params: dict) -> dict:
        for attempt in range(2):
            token = self._get_token(force=attempt > 0)
            r = self.session.get(
                self.base_url + "api/v2/Market/" + path,
                params=params,
                headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
                timeout=20,
            )
            if r.status_code == 401 and attempt == 0:
                continue  # token hết hạn → lấy lại
            r.raise_for_status()
            return r.json()
        raise RuntimeError("SSI từ chối xác thực")

    @staticmethod
    def _rows(body: dict) -> list[dict]:
        data = body.get("data")
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for k in ("RepeatedInfo", "repeatedinfoList", "items"):
                if isinstance(data.get(k), list):
                    return data[k]
        return []

    @staticmethod
    def _norm_keys(row: dict) -> dict:
        return {str(k).lower().replace(" ", "").replace("_", ""): v for k, v in row.items()}

    @staticmethod
    def _num(v) -> Optional[float]:
        if v is None or v == "":
            return None
        try:
            return float(str(v).replace(",", ""))
        except ValueError:
            return None

    def _paged(self, path: str, params: dict, max_pages: int = 10) -> list[dict]:
        out = []
        for page in range(1, max_pages + 1):
            body = self._get(path, {**params, "pageIndex": page, "pageSize": 1000})
            status = str(body.get("status", ""))
            if status not in ("200", "Success", "success", ""):
                raise RuntimeError(f"SSI {path}: {str(body.get('message'))[:200]}")
            rows = self._rows(body)
            out.extend(rows)
            total = self._num(body.get("totalRecord"))
            if not rows or len(rows) < 1000 or (total is not None and len(out) >= total):
                break
        return out

    def _ranged(self, path: str, params: dict, start: datetime, end: datetime) -> list[dict]:
        """Thử lấy cả khoảng một lần; nếu API giới hạn khoảng ngày thì chia nhỏ 30 ngày/lần."""
        fmt = "%d/%m/%Y"
        try:
            rows = self._paged(path, {**params, "fromDate": start.strftime(fmt), "toDate": end.strftime(fmt), "ascending": "true"})
            span = (end - start).days
            if rows or span <= 31:
                return rows
        except (requests.HTTPError, RuntimeError) as e:
            logger.info(f"[SSI] {path} cả khoảng lỗi ({str(e)[:120]}) → chia nhỏ 30 ngày")
        rows, cur = [], start
        while cur <= end:
            stop = min(cur + timedelta(days=30), end)
            rows.extend(self._paged(path, {**params, "fromDate": cur.strftime(fmt), "toDate": stop.strftime(fmt), "ascending": "true"}))
            cur = stop + timedelta(days=1)
            time.sleep(0.25)
        return rows

    # --- API công khai của provider ---
    def history(self, symbol: str, start: datetime, end: datetime) -> pd.DataFrame:
        rows = self._ranged("DailyOhlc", {"symbol": symbol}, start, end)
        recs = []
        for r in rows:
            k = self._norm_keys(r)
            d = k.get("tradingdate")
            if not d:
                continue
            recs.append({
                "Date": pd.to_datetime(d, dayfirst=True),
                "Open": self._num(k.get("open")), "High": self._num(k.get("high")),
                "Low": self._num(k.get("low")), "Close": self._num(k.get("close")),
                "Volume": self._num(k.get("volume")) or 0.0,
            })
        if not recs and symbol in INDEX_SYMBOLS:
            # Một số phiên bản API chỉ trả chỉ số qua DailyIndex (không có OHLC) → O=H=L=C=IndexValue
            for r in self._ranged("DailyIndex", {"indexId": symbol}, start, end):
                k = self._norm_keys(r)
                d, v = k.get("tradingdate"), self._num(k.get("indexvalue"))
                if d and v:
                    recs.append({"Date": pd.to_datetime(d, dayfirst=True), "Open": v, "High": v, "Low": v, "Close": v,
                                 "Volume": self._num(k.get("totalmatchvol")) or 0.0})
        if not recs:
            return pd.DataFrame()
        return _normalize(pd.DataFrame(recs).set_index("Date"), symbol)

    def daily_stock_price(self, symbol: str, days: int = 40) -> list[dict]:
        """Giá & khối ngoại theo ngày (nhiều phiên) — dữ liệu mà bảng giá vnstock chỉ có cho 1 phiên."""
        end = datetime.now()
        rows = self._ranged("DailyStockPrice", {"symbol": symbol}, end - timedelta(days=days), end)
        out = []
        for r in rows:
            k = self._norm_keys(r)
            d = k.get("tradingdate")
            if not d:
                continue
            g = lambda *names: next((self._num(k.get(n)) for n in names if k.get(n) not in (None, "")), None)  # noqa: E731
            out.append({
                "date": pd.to_datetime(d, dayfirst=True),
                "close": g("closeprice"), "ref": g("refprice"), "ceiling": g("ceilingprice"), "floor": g("floorprice"),
                "total_value": g("totalmatchval", "totaltradedvalue"),
                "foreign_buy_val": g("foreignbuyvaltotal"), "foreign_sell_val": g("foreignsellvaltotal", "toreignsellvaltotal"),
                "foreign_buy_vol": g("foreignbuyvoltotal"), "foreign_sell_vol": g("foreignsellvoltotal"),
                "foreign_room": g("foreigncurrentroom"),
            })
        out.sort(key=lambda x: x["date"])
        return out

    def listed_shares(self, symbol: str) -> Optional[float]:
        rows = self._paged("SecuritiesDetails", {"symbol": symbol}, max_pages=1)
        for r in rows:
            k = self._norm_keys(r)
            if str(k.get("symbol", "")).upper() == symbol:
                return self._num(k.get("listedshare"))
        return None


# ==============================================================================================
# Provider: vnstock (có cầu dao tự ngắt)
# ==============================================================================================
class VnstockProvider:
    """
    LƯU Ý: thư viện vnai đi kèm vnstock gọi sys.exit() khi vượt hạn mức (bản khách: 20 request/phút) → SystemExit
    không bị `except Exception` bắt và có thể làm SẬP CẢ BACKEND. Vì vậy:
    - tự giới hạn ≤ VNSTOCK_RPM (mặc định 18) request/phút trước khi chạm ngưỡng của vnai;
    - bắt cả SystemExit ở mọi lệnh gọi vnstock và chuyển thành lỗi thường.
    """
    name = "vnstock"
    SOURCES = ("vci", "kbs", "msn", "dnse")
    BREAK_AFTER = 3
    BREAK_FOR_S = 30 * 60
    RATE_COOLDOWN_S = 60
    CALL_TIMEOUT_S = 25
    RPM = int(os.getenv("VNSTOCK_RPM", "18"))

    def __init__(self):
        self._fails = 0
        self._broken_until = 0.0
        self._calls: deque = deque()
        self._rl_lock = threading.Lock()
        self.wait_on_limit = False  # công cụ backfill bật True để chờ thay vì bỏ qua

    def acquire(self, block: Optional[bool] = None) -> bool:
        """Xin 1 lượt gọi trong hạn mức/phút. block=False → trả False ngay nếu đã hết lượt."""
        block = self.wait_on_limit if block is None else block
        while True:
            with self._rl_lock:
                now = time.time()
                while self._calls and now - self._calls[0] > 60:
                    self._calls.popleft()
                if len(self._calls) < self.RPM:
                    self._calls.append(now)
                    return True
                wait = 60 - (now - self._calls[0]) + 0.5
            if not block:
                return False
            time.sleep(max(0.5, wait))

    def note_rate_limited(self) -> None:
        self._broken_until = max(self._broken_until, time.time() + self.RATE_COOLDOWN_S)
        self._broken_reason = "Tạm dừng do vnstock báo vượt hạn mức request/phút"

    def available(self) -> tuple[bool, str]:
        if os.getenv("DISABLE_VNSTOCK", "").strip() in ("1", "true", "yes"):
            return False, "Đã tắt bằng DISABLE_VNSTOCK"
        if time.time() < self._broken_until:
            reason = getattr(self, "_broken_reason", None) or "Cầu dao đang ngắt sau nhiều lỗi liên tiếp"
            return False, f"{reason} — thử lại sau {int(self._broken_until - time.time())}s"
        return True, "ok"

    def _fetch(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        from vnstock.api.quote import Quote  # import trễ: thư viện có thể bị vô hiệu sau 10/11/2026

        errors, raised = [], False
        for src in self.SOURCES:
            if not self.acquire():
                raise RuntimeError(f"Đã dùng hết hạn mức {self.RPM} request/phút của vnstock (bản khách)")
            try:
                df = Quote(symbol=symbol, source=src).history(start=start, end=end, interval="1D")
                if df is None or df.empty:
                    errors.append(f"{src}: rỗng")
                    continue
                df.columns = [c.capitalize() if c.islower() else c for c in df.columns]
                if "Time" in df.columns:
                    df = df.rename(columns={"Time": "Date"})
                if "Date" in df.columns:
                    df = df.set_index(pd.to_datetime(df["Date"]))
                return _normalize(df, symbol)
            except SystemExit as e:  # vnai: "Rate limit exceeded ... Process terminated."
                self.note_rate_limited()
                raise RuntimeError(f"vnstock chặn vì vượt hạn mức request: {str(e)[:120]}") from None
            except Exception as e:  # noqa: BLE001
                raised = True
                errors.append(f"{src}: {str(e)[:80]}")
        if not raised:
            return pd.DataFrame()  # mã không có dữ liệu (sai mã / đình chỉ) — không tính là nguồn hỏng
        raise RuntimeError("; ".join(errors))

    def history(self, symbol: str, start: datetime, end: datetime) -> pd.DataFrame:
        fut = _POOL.submit(self._fetch, symbol, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
        # Chế độ chờ hạn mức (backfill) có thể phải đợi tới ~60s/lượt × 4 nguồn → nới thời gian chờ
        timeout = self.CALL_TIMEOUT_S + (4 * 62 if self.wait_on_limit else 0)
        try:
            df = fut.result(timeout=timeout)
            self._fails = 0
            return df
        except (Exception, SystemExit) as e:  # noqa: BLE001 — SystemExit từ vnai không được làm sập backend
            msg = str(e)
            if isinstance(e, SystemExit) or "hạn mức" in msg or "Rate limit" in msg:
                self.note_rate_limited()
                raise RuntimeError(f"vnstock tạm hết hạn mức request/phút: {msg[:160]}") from None
            self._fails += 1
            if self._fails >= self.BREAK_AFTER:
                self._broken_until = time.time() + self.BREAK_FOR_S
                self._broken_reason = f"Cầu dao ngắt sau {self._fails} lỗi liên tiếp (có thể vnstock đã ngừng hoạt động)"
                logger.warning(f"[vnstock] {self._fails} lần lỗi liên tiếp → ngắt cầu dao {self.BREAK_FOR_S // 60} phút")
            detail = str(e)[:200] or (f"quá {timeout}s không phản hồi" if isinstance(e, concurrent.futures.TimeoutError) else type(e).__name__)
            raise RuntimeError(f"vnstock lỗi: {detail}") from e


# ==============================================================================================
# Provider: kho CSV cục bộ (đọc + tự ghi bổ sung)
# ==============================================================================================
class LocalStoreProvider:
    name = "local"

    def path(self, symbol: str) -> Path:
        return STORE_DIR / f"{symbol.upper()}.csv"

    def available(self) -> tuple[bool, str]:
        return True, "ok"

    def history(self, symbol: str, start: datetime, end: datetime) -> pd.DataFrame:
        p = self.path(symbol)
        if not p.exists():
            raise RuntimeError(f"Chưa có file {p.name} trong kho cục bộ")
        df = pd.read_csv(p)
        date_col = next((c for c in df.columns if c.lower() in ("date", "time", "tradingdate", "ngay")), df.columns[0])
        df = df.rename(columns={c: c.capitalize() for c in df.columns if c.lower() in ("open", "high", "low", "close", "volume")})
        df = df.set_index(pd.to_datetime(df[date_col], dayfirst=False, errors="coerce"))
        df = _normalize(df[df.index.notna()], symbol)
        return df[(df.index >= pd.Timestamp(start.date())) & (df.index <= pd.Timestamp(end.date()))]

    def save(self, symbol: str, df: pd.DataFrame) -> None:
        """Gộp dữ liệu mới vào kho (ghi nguyên tử), giữ bản mới nhất cho mỗi ngày."""
        if df is None or df.empty:
            return
        try:
            STORE_DIR.mkdir(parents=True, exist_ok=True)
            p = self.path(symbol)
            new = df[OHLCV].copy()
            if p.exists():
                try:
                    old = pd.read_csv(p, index_col=0, parse_dates=True)[OHLCV]
                    new = pd.concat([old, new])
                except Exception:  # noqa: BLE001 — file hỏng thì ghi đè
                    pass
            new = new[~new.index.duplicated(keep="last")].sort_index()
            new.index.name = "Date"
            fd, tmp = tempfile.mkstemp(dir=STORE_DIR, suffix=".tmp")
            os.close(fd)
            new.round(4).to_csv(tmp, date_format="%Y-%m-%d")
            os.replace(tmp, p)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[local] Không lưu được kho {symbol}: {e}")


# ==============================================================================================
# Chuỗi dự phòng
# ==============================================================================================
SSI = SSIProvider()
VNSTOCK = VnstockProvider()
LOCAL = LocalStoreProvider()
_REGISTRY = {"ssi": SSI, "vnstock": VNSTOCK, "local": LOCAL}


def provider_chain() -> list:
    names = [n.strip().lower() for n in os.getenv("DATA_SOURCES", "ssi,vnstock,local").split(",") if n.strip()]
    chain = [_REGISTRY[n] for n in names if n in _REGISTRY]
    if LOCAL not in chain:
        chain.append(LOCAL)  # kho cục bộ luôn là chốt chặn cuối
    return chain


def _expected_last_session(end: datetime) -> pd.Timestamp:
    """Phiên giao dịch gần nhất lẽ ra phải có dữ liệu (chưa tính ngày lễ)."""
    d = pd.Timestamp(end.date())
    now = datetime.now()
    if d >= pd.Timestamp(now.date()) and now.hour < 9:  # hôm nay chưa mở cửa → phiên trước
        d -= pd.Timedelta(days=1)
    while d.weekday() >= 5:
        d -= pd.Timedelta(days=1)
    return d


def _fresh_local(symbol: str, start: datetime, end: datetime) -> Optional[pd.DataFrame]:
    """Kho cục bộ đã đủ dữ liệu tới phiên gần nhất → dùng luôn, không gọi mạng (giảm mạnh số request vnstock/SSI)."""
    try:
        df = LOCAL.history(symbol, start, end)
    except Exception:  # noqa: BLE001
        return None
    if df.empty or df.index[-1] < _expected_last_session(end):
        return None
    if df.index[0] > pd.Timestamp(start.date()) + pd.Timedelta(days=15):
        return None  # kho chưa phủ đủ khoảng thời gian yêu cầu
    return df


def fetch_history(symbol: str, start: datetime, end: datetime) -> pd.DataFrame:
    """Lấy OHLCV theo chuỗi dự phòng. Ghi nhận nguồn đã dùng (get_source_info) và lưu vào kho cục bộ."""
    symbol = symbol.upper().strip().replace(".VN", "")
    cached = _fresh_local(symbol, start, end)
    if cached is not None:
        with _lock:
            _last_source[symbol] = {"source": "local", "cache_hit": True, "rows": len(cached),
                                    "last_date": cached.index[-1].strftime("%Y-%m-%d"), "stale_sessions": 0}
        return cached
    errors = []
    for prov in provider_chain():
        ok, why = prov.available()
        if not ok:
            errors.append(f"{prov.name}: {why}")
            continue
        t0 = time.time()
        try:
            df = prov.history(symbol, start, end)
        except Exception as e:  # noqa: BLE001
            errors.append(f"{prov.name}: {str(e)[:160]}")
            continue
        if df is None or df.empty:
            errors.append(f"{prov.name}: không có dữ liệu")
            continue
        last = df.index[-1]
        lag = max(0, len(pd.bdate_range(last, _expected_last_session(end))) - 1)
        info = {
            "source": prov.name, "rows": len(df), "last_date": last.strftime("%Y-%m-%d"),
            "stale_sessions": int(lag), "latency_s": round(time.time() - t0, 2),
            "fallback_errors": errors[:],
        }
        if prov is LOCAL and lag > 0:
            info["warning"] = f"Dữ liệu từ kho cục bộ, cũ hơn {lag} phiên — các nguồn trực tuyến đang lỗi"
        with _lock:
            _last_source[symbol] = info
        if prov is not LOCAL:
            now = datetime.now()
            to_save = df
            if now.weekday() < 5 and (now.hour, now.minute) < (15, 5):
                to_save = df[df.index < pd.Timestamp(now.date())]  # không lưu nến phiên chưa chốt
            LOCAL.save(symbol, to_save)
        logger.info(f"[data] {symbol}: {prov.name} ({len(df)} phiên, đến {info['last_date']})")
        return df
    with _lock:
        _last_source[symbol] = {"source": None, "errors": errors}
    logger.warning(f"[data] {symbol}: mọi nguồn đều lỗi — {'; '.join(errors)[:300]}")
    return pd.DataFrame()


def get_source_info(symbol: str) -> Optional[dict]:
    with _lock:
        return dict(_last_source.get(symbol.upper().strip(), {})) or None


def check_sources(symbol: str = "HPG", days: int = 30) -> list[dict]:
    """Kiểm tra từng nguồn độc lập (không ghi kho) — dùng cho endpoint sức khỏe và script kiểm tra."""
    end = datetime.now()
    start = end - timedelta(days=days)
    out = []
    for name, prov in _REGISTRY.items():
        ok, why = prov.available()
        row = {"source": name, "enabled": ok, "detail": why}
        if ok:
            t0 = time.time()
            try:
                df = prov.history(symbol, start, end)
                row.update(ok=not df.empty, rows=len(df), last_date=df.index[-1].strftime("%Y-%m-%d") if not df.empty else None,
                           last_close=round(float(df["Close"].iloc[-1]), 2) if not df.empty else None)
            except Exception as e:  # noqa: BLE001
                row.update(ok=False, error=str(e)[:200])
            row["latency_s"] = round(time.time() - t0, 2)
        else:
            row["ok"] = False
        out.append(row)
    return out
