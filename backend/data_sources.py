"""
Lớp nguồn dữ liệu giá ĐA NHÀ CUNG CẤP — để hệ thống không chết theo một nguồn duy nhất.

Bối cảnh: vnstock thông báo các lớp "thế hệ 4" (Quote.history, Company.overview, Finance, Trading.price_board — chính là
các lớp dự án đang dùng) ngừng hoạt động từ 10/11/2026 và khuyến nghị chuyển sang API của công ty chứng khoán nơi
nhà đầu tư có tài khoản, hoặc dữ liệu tự chuẩn bị.

Chuỗi dự phòng (cấu hình bằng biến môi trường DATA_SOURCES, mặc định "ssi,public,vnstock,local"):
1. ssi     — SSI FastConnect Data API (chính thức, miễn phí cho chủ tài khoản SSI; phải đăng ký tại quầy/qua môi giới,
             sau đó lấy ConsumerID/ConsumerSecret trên iBoard → Dịch vụ API). Chỉ bật khi có SSI_CONSUMER_ID &
             SSI_CONSUMER_SECRET trong .env.
2. public  — gọi thẳng API công khai của bảng giá web DNSE, VNDirect, SSI iBoard, Vietcap, KBS (không cần đăng ký),
             xoay vòng theo PUBLIC_SOURCES, mỗi nguồn có cầu dao riêng. API không chính thức — có thể bị đổi/chặn.
3. vnstock — thư viện hiện tại; có "cầu dao" tự ngắt 30 phút sau 3 lần lỗi liên tiếp để không làm chậm request.
4. local   — kho CSV cục bộ backend/data/ohlcv/<MÃ>.csv. Mọi lần tải thành công từ nguồn khác được tự động GHI
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
from datetime import datetime, timedelta, timezone
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
        try:
            from vnstock.api.quote import Quote  # import trễ: thư viện có thể bị vô hiệu sau 10/11/2026
        except ImportError:
            raise RuntimeError("Thư viện vnstock không khả dụng (hệ thống tự động sử dụng chuỗi nguồn public / ssi)")

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
# Provider: API công khai của bảng giá web các CTCK (miễn phí, không cần đăng ký)
# ==============================================================================================
_VN_TZ = "Asia/Ho_Chi_Minh"
_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
       "Chrome/130.0 Safari/537.36")


class PublicEndpointsProvider:
    """
    Gọi THẲNG các API công khai mà bảng giá web của các công ty chứng khoán đang dùng — cũng chính là các nguồn mà
    vnstock bọc lại. Miễn phí, không cần tài khoản hay khóa, không phụ thuộc việc vnstock ngừng lớp thế hệ 4
    (10/11/2026) và không dính giới hạn 20 request/phút kèm sys.exit() của vnai.

    Xoay vòng theo PUBLIC_SOURCES (mặc định dnse,vndirect,ssi_iboard,vci,kbs). Dùng nguồn đầu tiên có dữ liệu tới phiên
    gần nhất; nếu nguồn đó trả dữ liệu cũ thì thử nguồn kế tiếp và giữ bản mới nhất. Mỗi nguồn có cầu dao riêng
    (3 lỗi liên tiếp → bỏ qua 15 phút; HTTP 403/429 → nghỉ 2 phút).

    RỦI RO: đây là API nội bộ, không có tài liệu hay cam kết — có thể đổi hoặc bị chặn bất cứ lúc nào. Chỉ dùng cho
    mục đích cá nhân, không phân phối lại dữ liệu. Nguồn chính thức lâu dài vẫn là SSI FastConnect.
    """
    name = "public"
    DEFAULT_ORDER = "dnse,vndirect,ssi_iboard,vci,kbs"
    BREAK_AFTER = 3
    BREAK_FOR_S = 15 * 60
    THROTTLED_FOR_S = 120
    TIMEOUT = (6, 20)  # (kết nối, đọc) giây

    # Tên chỉ số khác nhau giữa các nguồn (đã kiểm tra thực tế 08/11/2026); None = nguồn không có chỉ số đó
    INDEX_ALIASES = {
        "dnse": {"HNXINDEX": "HNX", "UPCOMINDEX": "UPCOM"},
        "vndirect": {"HNXINDEX": "HNX", "UPCOMINDEX": "UPCOM"},
        "ssi_iboard": {"UPCOMINDEX": None},
        "vci": {"HNXINDEX": "HNXIndex", "UPCOMINDEX": "HNXUpcomIndex"},
        "kbs": {},
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": _UA, "Accept": "application/json, text/plain, */*"})
        self._state: dict[str, dict] = {}
        self._slock = threading.Lock()
        self._rt_cache: dict[tuple, tuple[float, object]] = {}
        self._fetchers = {
            "dnse": self._tv_daily("dnse"), "vndirect": self._tv_daily("vndirect"),
            "ssi_iboard": self._tv_daily("ssi_iboard"), "vci": self._vci, "kbs": self._kbs,
        }

    # --- cấu hình & cầu dao ---
    def endpoints(self) -> list[str]:
        names = [n.strip().lower() for n in os.getenv("PUBLIC_SOURCES", self.DEFAULT_ORDER).split(",") if n.strip()]
        return [n for n in names if n in self._fetchers]

    def endpoint_status(self, ep: str) -> tuple[bool, str]:
        with self._slock:
            st = self._state.get(ep) or {}
            if time.time() < st.get("until", 0.0):
                return False, f"{ep}: {st.get('reason')} — thử lại sau {int(st['until'] - time.time())}s"
        return True, "ok"

    def _record(self, ep: str, err: Optional[Exception]) -> None:
        with self._slock:
            st = self._state.setdefault(ep, {"fails": 0, "until": 0.0})
            if err is None:
                st.update(fails=0, until=0.0)
                return
            st["fails"] += 1
            status = getattr(getattr(err, "response", None), "status_code", None)
            if st["fails"] >= self.BREAK_AFTER:
                st["until"] = time.time() + self.BREAK_FOR_S
                st["reason"] = f"ngắt cầu dao sau {st['fails']} lỗi liên tiếp"
                logger.warning(f"[public] {ep}: {st['fails']} lỗi liên tiếp → bỏ qua {self.BREAK_FOR_S // 60} phút")
            elif status in (403, 429):
                st["until"] = time.time() + self.THROTTLED_FOR_S
                st["reason"] = f"bị từ chối/giới hạn tần suất (HTTP {status})"

    def available(self) -> tuple[bool, str]:
        if os.getenv("DISABLE_PUBLIC_SOURCES", "").strip().lower() in ("1", "true", "yes"):
            return False, "Đã tắt bằng DISABLE_PUBLIC_SOURCES"
        eps = self.endpoints()
        if not eps:
            return False, "PUBLIC_SOURCES không chứa nguồn hợp lệ (dnse, vndirect, ssi_iboard, vci, kbs)"
        live = [ep for ep in eps if self.endpoint_status(ep)[0]]
        if not live:
            return False, "Mọi nguồn công khai đang tạm ngắt: " + "; ".join(self.endpoint_status(ep)[1] for ep in eps)
        return True, "ok: " + " → ".join(live)

    # --- HTTP & phân tích phản hồi ---
    def _request(self, method: str, url: str, site: str, **kw):
        r = self.session.request(method, url, headers={"Referer": site, "Origin": site.rstrip("/")},
                                 timeout=self.TIMEOUT, **kw)
        if r.status_code in (400, 404):
            return None  # nguồn không có mã/chỉ số này — không tính là nguồn hỏng
        r.raise_for_status()
        if not (r.content or b"").strip():
            return None  # VNDirect trả thân rỗng (HTTP 200) cho mã không tồn tại
        return r.json()

    @staticmethod
    def _ts_range(start: datetime, end: datetime) -> tuple[int, int]:
        f = datetime(start.year, start.month, start.day)
        t = datetime(end.year, end.month, end.day) + timedelta(days=1)  # gồm cả nến ngày `end`
        return int(f.timestamp()), int(t.timestamp())

    @staticmethod
    def _from_tv(j, daily: bool = True) -> pd.DataFrame:
        """Định dạng kiểu TradingView {t,o,h,l,c,v} — t là epoch (giây hoặc mili-giây). Index = giờ Việt Nam."""
        if not isinstance(j, dict) or not j.get("t"):
            return pd.DataFrame()
        t = pd.to_numeric(pd.Series(j["t"]), errors="coerce")
        unit = "ms" if float(t.max()) > 1e11 else "s"
        stamps = pd.to_datetime(t, unit=unit, utc=True).dt.tz_convert(_VN_TZ).dt.tz_localize(None)
        df = pd.DataFrame({"Open": j.get("o"), "High": j.get("h"), "Low": j.get("l"),
                           "Close": j.get("c"), "Volume": j.get("v")})
        df.index = pd.DatetimeIndex(stamps.dt.normalize() if daily else stamps)
        return df

    # Các nguồn cùng định dạng TradingView: (URL, trang gốc làm Referer, mã khung ngày). Giá cổ phiếu: nghìn đồng.
    _TV = {
        "dnse": ("https://services.entrade.com.vn/chart-api/v2/ohlcs/{kind}", "https://banggia.dnse.com.vn/", "1D"),
        "vndirect": ("https://dchart-api.vndirect.com.vn/dchart/history", "https://dchart.vndirect.com.vn/", "D"),
        "ssi_iboard": ("https://iboard-api.ssi.com.vn/statistics/charts/history", "https://iboard.ssi.com.vn/", "1D"),
    }

    def _tv(self, ep: str, sym: str, is_index: bool, f: int, t: int,
            resolution: Optional[str] = None, daily: bool = True) -> pd.DataFrame:
        url, site, daily_res = self._TV[ep]
        j = self._request("GET", url.format(kind="index" if is_index else "stock"), site,
                          params={"symbol": sym, "resolution": resolution or daily_res, "from": f, "to": t})
        if isinstance(j, dict) and "t" not in j and isinstance(j.get("data"), dict):
            j = j["data"]  # SSI iBoard bọc trong "data"
        return self._from_tv(j, daily=daily)

    def _tv_daily(self, ep: str):
        def fetch(sym: str, is_index: bool, start: datetime, end: datetime) -> pd.DataFrame:
            f, t = self._ts_range(start, end)
            return self._tv(ep, sym, is_index, f, t)
        return fetch

    @staticmethod
    def _vnd_to_thousand(df: pd.DataFrame) -> pd.DataFrame:
        cols = ["Open", "High", "Low", "Close"]
        df[cols] = df[cols].apply(pd.to_numeric, errors="coerce") / 1000.0
        return df

    # --- từng nguồn (DNSE / VNDirect / SSI iBoard dùng chung _tv ở trên) ---
    def _vci(self, sym: str, is_index: bool, start: datetime, end: datetime) -> pd.DataFrame:
        _, t = self._ts_range(start, end)  # giá cổ phiếu: ĐỒNG; API đếm lùi countBack nến tính từ `to`
        count = len(pd.bdate_range(start.date(), end.date())) + 3
        j = self._request("POST", "https://trading.vietcap.com.vn/api/chart/OHLCChart/gap-chart",
                          "https://trading.vietcap.com.vn/",
                          json={"timeFrame": "ONE_DAY", "symbols": [sym], "to": t, "countBack": count})
        if isinstance(j, dict) and "data" in j:
            j = j["data"]
        if isinstance(j, list):
            j = j[0] if j else {}
        df = self._from_tv(j)
        return df if df.empty or is_index else self._vnd_to_thousand(df)

    def _kbs(self, sym: str, is_index: bool, start: datetime, end: datetime) -> pd.DataFrame:
        # giá cổ phiếu: ĐỒNG; dữ liệu trả về theo thứ tự ngày giảm dần, số có thể ở dạng chuỗi
        j = self._request("GET", f"https://kbbuddywts.kbsec.com.vn/iis-server/investment/"
                                 f"{'index' if is_index else 'stocks'}/{sym}/data_day",
                          "https://kbbuddywts.kbsec.com.vn/",
                          params={"sdate": start.strftime("%d-%m-%Y"), "edate": end.strftime("%d-%m-%Y")})
        rows = j.get("data_day") if isinstance(j, dict) else None
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame(rows).rename(columns={"o": "Open", "h": "High", "l": "Low", "c": "Close", "v": "Volume"})
        df.index = pd.to_datetime(df["t"].astype(str).str[:10], errors="coerce")
        df = df[df.index.notna()]
        return df if is_index else self._vnd_to_thousand(df)

    # --- API của provider ---
    @staticmethod
    def _sanity(df: pd.DataFrame, symbol: str, ep: str) -> None:
        close = df["Close"]
        if (close <= 0).any():
            raise ValueError(f"{ep}: có giá đóng cửa ≤ 0")
        med = float(close.median())
        if symbol in INDEX_SYMBOLS and med < 20:
            raise ValueError(f"{ep}: thang đo chỉ số bất thường (trung vị {med:.3f})")
        if symbol not in INDEX_SYMBOLS and med > 2000:
            raise ValueError(f"{ep}: đơn vị giá bất thường (trung vị {med:.1f} nghìn đồng)")

    def fetch_endpoint(self, ep: str, symbol: str, start: datetime, end: datetime) -> pd.DataFrame:
        """Gọi đúng 1 nguồn; trả OHLCV đã chuẩn hóa (nghìn đồng), rỗng nếu nguồn không có mã này."""
        is_index = symbol in INDEX_SYMBOLS
        remote = self.INDEX_ALIASES.get(ep, {}).get(symbol, symbol) if is_index else symbol
        if remote is None:
            return pd.DataFrame()
        raw = self._fetchers[ep](remote, is_index, start, end)
        if raw is None or raw.empty:
            return pd.DataFrame()
        df = _normalize(raw, symbol)
        df = df[(df.index >= pd.Timestamp(start.date())) & (df.index <= pd.Timestamp(end.date()))]
        if not df.empty:
            self._sanity(df, symbol, ep)
        return df

    def history(self, symbol: str, start: datetime, end: datetime) -> pd.DataFrame:
        expected = _expected_last_session(end)
        best: Optional[pd.DataFrame] = None
        errors, raised = [], False
        for ep in self.endpoints():
            ok, why = self.endpoint_status(ep)
            if not ok:
                errors.append(why)
                continue
            try:
                df = self.fetch_endpoint(ep, symbol, start, end)
            except Exception as e:  # noqa: BLE001
                self._record(ep, e)
                raised = True
                errors.append(f"{ep}: {str(e)[:100] or type(e).__name__}")
                continue
            self._record(ep, None)
            if df.empty:
                errors.append(f"{ep}: không có dữ liệu")
                continue
            df.attrs["endpoint"] = ep
            if best is None or df.index[-1] > best.index[-1]:
                best = df
            if df.index[-1] >= expected:
                break  # đã tới phiên gần nhất → không cần hỏi thêm nguồn khác
        if best is not None:
            return best
        if not raised:
            return pd.DataFrame()  # sai mã / mã không giao dịch — không phải lỗi nguồn
        raise RuntimeError("; ".join(errors))

    # ------------------------------------------------------------------------------------------
    # Thời gian thực: bảng giá Vietcap + nến trong phiên (DNSE / VNDirect / SSI iBoard)
    # ------------------------------------------------------------------------------------------
    BOARD_URL = "https://trading.vietcap.com.vn/api/price/symbols/getList"
    BOARD_TTL_S = 3       # nhiều trình duyệt cùng hỏi trong 3 giây → chỉ gọi Vietcap 1 lần
    INTRADAY_TTL_S = 20
    INTRADAY_ENDPOINTS = ("dnse", "vndirect", "ssi_iboard")
    INTRADAY_RESOLUTIONS = ("1", "5", "15", "30", "60")
    EXCHANGES = {"HSX": "HOSE", "HOSE": "HOSE", "HNX": "HNX", "UPCOM": "UPCOM"}

    def _cached(self, key: tuple, ttl: float):
        with self._slock:
            hit = self._rt_cache.get(key)
            return hit[1] if hit and time.time() - hit[0] < ttl else None

    def _store(self, key: tuple, value) -> None:
        with self._slock:
            if len(self._rt_cache) > 500:
                self._rt_cache.clear()
            self._rt_cache[key] = (time.time(), value)

    @classmethod
    def parse_board_item(cls, item) -> Optional[dict]:
        """Một phần tử bảng giá Vietcap → báo giá chuẩn hóa (giá NGHÌN ĐỒNG, giá trị TỶ ĐỒNG)."""
        if not isinstance(item, dict):
            return None
        li = item.get("listingInfo") if isinstance(item.get("listingInfo"), dict) else {}
        mp = item.get("matchPrice") if isinstance(item.get("matchPrice"), dict) else {}
        ba = item.get("bidAsk") if isinstance(item.get("bidAsk"), dict) else {}
        sym = str(li.get("symbol") or mp.get("symbol") or "").upper()
        if not sym:
            return None  # mã không tồn tại: Vietcap trả listingInfo = None
        num = SSIProvider._num

        def k(v):  # đồng → nghìn đồng
            return round(v / 1000.0, 3) if v else None

        ref = num(li.get("refPrice")) or num(mp.get("referencePrice"))
        price = num(mp.get("matchPrice")) or None  # 0 = chưa có lệnh khớp
        change = price - ref if price and ref else None
        fb_vol, fs_vol = num(mp.get("foreignBuyVolume")), num(mp.get("foreignSellVolume"))
        fb_val, fs_val = num(mp.get("foreignBuyValue")), num(mp.get("foreignSellValue"))
        acc_val = num(mp.get("accumulatedValue"))  # triệu đồng

        def levels(arr):
            return [{"price": k(num(x.get("price"))), "volume": num(x.get("volume"))}
                    for x in (arr or []) if isinstance(x, dict)]

        return {
            "symbol": sym,
            "company_name": li.get("organName"), "short_name": li.get("organShortName"),
            "exchange": cls.EXCHANGES.get(str(li.get("board") or "").upper(), li.get("board")),
            "trading_date": li.get("tradingDate"),
            "session": mp.get("session") or ba.get("session"),
            "last_update": mp.get("time") or ba.get("time"),  # ISO, giờ UTC
            "price": k(price), "ref": k(ref),
            "ceiling": k(num(li.get("ceiling")) or num(mp.get("ceilingPrice"))),
            "floor": k(num(li.get("floor")) or num(mp.get("floorPrice"))),
            "open": k(num(mp.get("openPrice"))), "high": k(num(mp.get("highest"))),
            "low": k(num(mp.get("lowest"))), "avg": k(num(mp.get("avgMatchPrice"))),
            "change": round(change / 1000.0, 3) if change is not None else None,
            "change_pct": round(change / ref * 100, 2) if change is not None and ref else None,
            "volume": num(mp.get("accumulatedVolume")),
            "value_bn": round(acc_val / 1000.0, 2) if acc_val is not None else None,
            "foreign_buy_vol": fb_vol, "foreign_sell_vol": fs_vol,
            "foreign_buy_bn": round(fb_val / 1e9, 2) if fb_val is not None else None,
            "foreign_sell_bn": round(fs_val / 1e9, 2) if fs_val is not None else None,
            "foreign_net_bn": round((fb_val - fs_val) / 1e9, 2) if fb_val is not None and fs_val is not None else None,
            "foreign_room": num(mp.get("currentRoom")), "foreign_total_room": num(mp.get("totalRoom")),
            "listed_shares": num(li.get("listedShare")),
            "bid": levels(ba.get("bidPrices")), "ask": levels(ba.get("askPrices")),
            "security_status": li.get("securityStatus"), "trading_status": li.get("tradingStatus"),
            "source": "vci",
        }

    def price_board(self, symbols: list[str]) -> dict[str, dict]:
        """Bảng giá tức thời (Vietcap) cho nhiều mã trong 1 lần gọi: giá khớp, trần/sàn/TC, KL, khối ngoại, room, dư mua/bán."""
        syms = tuple(sorted({s.strip().upper() for s in symbols if s and s.strip()}))
        if not syms:
            return {}
        cached = self._cached(("board", syms), self.BOARD_TTL_S)
        if cached is not None:
            return cached
        ok, why = self.endpoint_status("vci_board")
        if not ok:
            raise RuntimeError(why)
        try:
            j = self._request("POST", self.BOARD_URL, "https://trading.vietcap.com.vn/", json={"symbols": list(syms)})
        except Exception as e:  # noqa: BLE001
            self._record("vci_board", e)
            raise
        self._record("vci_board", None)
        out = {}
        for item in j if isinstance(j, list) else []:
            q = self.parse_board_item(item)
            if q:
                out[q["symbol"]] = q
        self._store(("board", syms), out)
        return out

    def intraday(self, symbol: str, resolution: str = "1") -> pd.DataFrame:
        """Nến trong phiên giao dịch GẦN NHẤT (mặc định 1 phút). Index = giờ Việt Nam (không gắn múi giờ)."""
        symbol = symbol.upper().strip()
        if resolution not in self.INTRADAY_RESOLUTIONS:
            raise ValueError(f"Khung {resolution} không hỗ trợ (chọn {', '.join(self.INTRADAY_RESOLUTIONS)})")
        cached = self._cached(("intraday", symbol, resolution), self.INTRADAY_TTL_S)
        if cached is not None:
            return cached
        is_index = symbol in INDEX_SYMBOLS
        now = int(time.time())
        f, t = now - 6 * 86400, now + 60  # lùi 6 ngày để qua được cuối tuần / nghỉ lễ ngắn
        eps = [e for e in self.endpoints() if e in self.INTRADAY_ENDPOINTS] or list(self.INTRADAY_ENDPOINTS)
        errors, raised = [], False
        for ep in eps:
            ok, why = self.endpoint_status(ep)
            if not ok:
                errors.append(why)
                continue
            remote = self.INDEX_ALIASES.get(ep, {}).get(symbol, symbol) if is_index else symbol
            if remote is None:
                continue
            try:
                df = self._tv(ep, remote, is_index, f, t, resolution=resolution, daily=False)
            except Exception as e:  # noqa: BLE001
                self._record(ep, e)
                raised = True
                errors.append(f"{ep}: {str(e)[:100] or type(e).__name__}")
                continue
            self._record(ep, None)
            if df.empty:
                continue
            df = df.apply(pd.to_numeric, errors="coerce").dropna(subset=["Close"]).sort_index()
            df = df[~df.index.duplicated(keep="last")]
            df = df[df.index >= df.index[-1].normalize()]  # chỉ giữ phiên gần nhất
            if df.empty:
                continue
            df.attrs["endpoint"] = ep
            self._store(("intraday", symbol, resolution), df)
            return df
        if raised:
            raise RuntimeError("; ".join(errors))
        return pd.DataFrame()


def market_session(now: Optional[datetime] = None) -> dict:
    """Trạng thái phiên HOSE/HNX theo giờ Việt Nam (chưa tính ngày nghỉ lễ)."""
    if now is None:
        now = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=7)  # VN không đổi giờ mùa hè
    hm = now.hour * 60 + now.minute
    if now.weekday() >= 5:
        state, label = "closed", "Nghỉ cuối tuần"
    elif hm < 9 * 60:
        state, label = "pre_open", "Chưa mở cửa"
    elif hm < 11 * 60 + 30:
        state, label = "open", "Đang giao dịch"
    elif hm < 13 * 60:
        state, label = "lunch_break", "Nghỉ trưa"
    elif hm < 14 * 60 + 45:
        state, label = "open", "Đang giao dịch"
    elif hm < 15 * 60:
        state, label = "closing", "Đã đóng cửa — đang chốt số liệu / thỏa thuận"
    else:
        state, label = "closed", "Đã đóng cửa"
    live = now.weekday() < 5 and 8 * 60 + 45 <= hm < 15 * 60 + 5
    return {"state": state, "label": label, "live": live, "vn_time": now.strftime("%Y-%m-%d %H:%M:%S")}


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
PUBLIC = PublicEndpointsProvider()
VNSTOCK = VnstockProvider()
LOCAL = LocalStoreProvider()
_REGISTRY = {"ssi": SSI, "public": PUBLIC, "vnstock": VNSTOCK, "local": LOCAL}
DEFAULT_CHAIN = "ssi,public,vnstock,local"


def provider_chain() -> list:
    names = [n.strip().lower() for n in os.getenv("DATA_SOURCES", DEFAULT_CHAIN).split(",") if n.strip()]
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
        if df.attrs.get("endpoint"):
            info["endpoint"] = df.attrs["endpoint"]  # nguồn công khai cụ thể (dnse, vndirect, ...)
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
        src_label = prov.name + (f":{info['endpoint']}" if info.get("endpoint") else "")
        logger.info(f"[data] {symbol}: {src_label} ({len(df)} phiên, đến {info['last_date']})")
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
    symbol = symbol.upper().strip()
    end = datetime.now()
    start = end - timedelta(days=days)

    def probe(row: dict, fn) -> dict:
        t0 = time.time()
        try:
            df = fn()
            row.update(ok=not df.empty, rows=len(df), last_date=df.index[-1].strftime("%Y-%m-%d") if not df.empty else None,
                       last_close=round(float(df["Close"].iloc[-1]), 2) if not df.empty else None)
        except Exception as e:  # noqa: BLE001
            row.update(ok=False, error=str(e)[:200])
        row["latency_s"] = round(time.time() - t0, 2)
        return row

    out = []
    for name, prov in _REGISTRY.items():
        if prov is PUBLIC:
            # Kiểm tra riêng từng nguồn công khai để thấy nguồn nào đang sống
            for ep in PUBLIC.endpoints():
                ok, why = PUBLIC.endpoint_status(ep)
                row = {"source": f"public:{ep}", "enabled": ok, "detail": why}
                out.append(probe(row, lambda ep=ep: PUBLIC.fetch_endpoint(ep, symbol, start, end)) if ok else {**row, "ok": False})
            continue
        ok, why = prov.available()
        row = {"source": name, "enabled": ok, "detail": why}
        out.append(probe(row, lambda prov=prov: prov.history(symbol, start, end)) if ok else {**row, "ok": False})
    return out
