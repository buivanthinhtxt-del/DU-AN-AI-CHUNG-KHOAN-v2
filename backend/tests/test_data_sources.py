"""
Kiểm thử offline cho data_sources (không gọi mạng): parser SSI FastConnect theo mẫu phản hồi trong tài liệu,
chuỗi dự phòng, cầu dao vnstock và kho CSV cục bộ.
Chạy: python backend/tests/test_data_sources.py
"""
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import data_sources as ds  # noqa: E402


class FakeResp:
    def __init__(self, body, status=200):
        self._body, self.status_code = body, status

    def json(self):
        return self._body

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests
            raise requests.HTTPError(f"HTTP {self.status_code}")


class FakeSSISession:
    """Mô phỏng fc-data.ssi.com.vn theo mẫu trong tài liệu API (giá là chuỗi, đơn vị đồng, ngày dd/mm/yyyy)."""

    def __init__(self):
        self.calls = []

    def post(self, url, json=None, timeout=None):
        self.calls.append(("POST", url, json))
        assert url.endswith("api/v2/Market/AccessToken")
        assert set(json) == {"consumerID", "consumerSecret"}
        return FakeResp({"message": "Success", "status": 200, "data": {"accessToken": "tok123"}})

    def get(self, url, params=None, headers=None, timeout=None):
        self.calls.append(("GET", url, params))
        assert headers["Authorization"] == "Bearer tok123"
        if url.endswith("DailyOhlc"):
            rows = [
                {"Symbol": params["symbol"], "Market": "HOSE", "TradingDate": "05/11/2026", "Time": None,
                 "Open": "21150", "High": "21500", "Low": "21000", "Close": "21500", "Volume": "38460000", "Value": "820000000000"},
                {"Symbol": params["symbol"], "Market": "HOSE", "TradingDate": "06/11/2026", "Time": None,
                 "Open": "21150", "High": "21400", "Low": "21050", "Close": "21200", "Volume": "22105200", "Value": "468685315000"},
            ]
            return FakeResp({"message": "Success", "status": "Success", "totalRecord": 2, "data": rows})
        if url.endswith("DailyStockPrice"):
            rows = [
                {"TradingDate": "05/11/2026", "Symbol": "HPG", "ClosePrice": "21500", "RefPrice": "21050", "CeilingPrice": "22500",
                 "FloorPrice": "19600", "ForeignBuyValTotal": "50000000000", "ForeignSellValTotal": "20000000000", "ForeignCurrentRoom": "2290000000"},
                {"TradingDate": "06/11/2026", "Symbol": "HPG", "ClosePrice": "21200", "RefPrice": "21500", "CeilingPrice": "23000",
                 "FloorPrice": "20000", "ForeignBuyValTotal": "41240000000", "ForeignSellValTotal": "68320000000", "ForeignCurrentRoom": "2288039792"},
            ]
            return FakeResp({"message": "Success", "status": 200, "totalRecord": 2, "data": rows})
        raise AssertionError(url)


def test_ssi_parser_and_units():
    p = ds.SSIProvider()
    p.consumer_id, p.consumer_secret = "id", "secret"
    p.session = FakeSSISession()
    df = p.history("HPG", datetime(2026, 11, 1), datetime(2026, 11, 6))
    assert list(df.columns) == ds.OHLCV
    assert df.index[-1] == pd.Timestamp("2026-11-06")
    assert abs(df["Close"].iloc[-1] - 21.2) < 1e-9, "Giá cổ phiếu phải quy về nghìn đồng"
    assert df["Volume"].iloc[-1] == 22105200
    get_call = next(c for c in p.session.calls if c[0] == "GET")
    assert get_call[2]["fromDate"] == "01/11/2026" and get_call[2]["pageSize"] == 1000

    rows = p.daily_stock_price("HPG", days=10)
    assert len(rows) == 2 and rows[-1]["foreign_sell_val"] == 68320000000
    # Token được dùng lại, chỉ xin 1 lần
    assert sum(1 for c in p.session.calls if c[0] == "POST") == 1


def test_chain_fallback_breaker_and_local_store():
    tmp = Path(tempfile.mkdtemp())
    ds.STORE_DIR = tmp
    end = datetime.now()
    idx = pd.bdate_range(end=end - timedelta(days=10), periods=30)
    seed = pd.DataFrame({"Open": 20.0, "High": 21.0, "Low": 19.5, "Close": 20.5, "Volume": 1e6}, index=idx)
    ds.LOCAL.save("TST", seed)
    assert (tmp / "TST.csv").exists()

    class Broken:
        name = "vnstock"
        def available(self):
            return ds.VNSTOCK.available()
        def history(self, *a):
            return ds.VNSTOCK.history(*a)

    ds.VNSTOCK._fetch = lambda *a: (_ for _ in ()).throw(RuntimeError("Lớp thế hệ 4 đã ngừng"))  # noqa: E731
    ds._REGISTRY["vnstock"] = Broken()
    import os
    os.environ["DATA_SOURCES"] = "ssi,vnstock,local"

    for _ in range(3):
        df = ds.fetch_history("TST", end - timedelta(days=60), end)
        assert not df.empty
    info = ds.get_source_info("TST")
    assert info["source"] == "local" and info["stale_sessions"] >= 5 and "warning" in info, info
    ok, why = ds.VNSTOCK.available()
    assert not ok and "Cầu dao" in why, "Sau 3 lỗi liên tiếp phải ngắt cầu dao"

    # Gộp dữ liệu mới vào kho, không trùng ngày
    newer = pd.DataFrame({"Open": 21.0, "High": 22.0, "Low": 20.5, "Close": 21.5, "Volume": 2e6},
                         index=pd.bdate_range(start=idx[-3], periods=5))
    ds.LOCAL.save("TST", newer)
    merged = pd.read_csv(tmp / "TST.csv", index_col=0, parse_dates=True)
    assert merged.index.is_unique and len(merged) == 32 and merged["Close"].iloc[-1] == 21.5


if __name__ == "__main__":
    tests = [v for k, v in dict(globals()).items() if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
        print(f"[PASS] {t.__name__}")
    print(f"\n[+] {len(tests)} data source tests passed")
