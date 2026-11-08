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

    @property
    def content(self):
        import json
        return b"" if self._body is None else json.dumps(self._body).encode()

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


# ----------------------------------------------------------------------------------------------
# Nguồn công khai (DNSE / VNDirect / SSI iBoard / Vietcap / KBS) — mô phỏng theo phản hồi thật đã ghi nhận 08/11/2026
# ----------------------------------------------------------------------------------------------
def _tv_body(dates, closes):
    ts = [int(pd.Timestamp(d).tz_localize("UTC").timestamp()) for d in dates]
    return {"t": ts, "o": closes, "h": closes, "l": closes, "c": closes, "v": [1_000_000] * len(closes), "s": "ok"}


class FakePublicSession:
    def __init__(self, handlers):
        self.handlers, self.calls = handlers, []

    def request(self, method, url, headers=None, timeout=None, params=None, json=None):
        key = ("dnse" if "entrade" in url else "vndirect" if "vndirect" in url else
               "ssi_iboard" if "iboard-api.ssi" in url else "vci" if "vietcap" in url else "kbs")
        self.calls.append((key, method, url, params if params is not None else json))
        assert headers and headers.get("Referer"), "Phải gửi Referer giống trình duyệt"
        return self.handlers[key](url, params if params is not None else json)


def _with_public_sources(order):
    import os
    old = os.environ.get("PUBLIC_SOURCES")
    os.environ["PUBLIC_SOURCES"] = order
    return old


def _restore_public_sources(old):
    import os
    if old is None:
        os.environ.pop("PUBLIC_SOURCES", None)
    else:
        os.environ["PUBLIC_SOURCES"] = old


def test_public_rotation_units_and_freshness():
    end = datetime.now()
    last = ds._expected_last_session(end)
    fresh = pd.bdate_range(end=last, periods=5)
    stale = pd.bdate_range(end=last - pd.offsets.BDay(3), periods=5)
    old = _with_public_sources("dnse,vndirect,ssi_iboard,vci,kbs")
    try:
        p = ds.PublicEndpointsProvider()
        p.session = FakePublicSession({
            "dnse": lambda u, q: FakeResp({"error": "boom"}, 500),                      # lỗi máy chủ → tính lỗi
            "vndirect": lambda u, q: FakeResp(None, 200),                                # thân rỗng = không có mã → không tính lỗi
            "ssi_iboard": lambda u, q: FakeResp({"data": _tv_body(stale, [21.0] * 5)}),  # dữ liệu cũ → thử tiếp
            "vci": lambda u, q: FakeResp([_tv_body(fresh, [21150, 21300, 21500, 21400, 21200])]),  # đơn vị đồng
            "kbs": lambda u, q: (_ for _ in ()).throw(AssertionError("Đã có dữ liệu mới, không được gọi KBS")),
        })
        df = p.history("HPG", end - timedelta(days=30), end)
        assert df.attrs["endpoint"] == "vci", df.attrs
        assert list(df.columns) == ds.OHLCV and df.index[-1] == last
        assert abs(df["Close"].iloc[-1] - 21.2) < 1e-9, "Giá Vietcap (đồng) phải quy về nghìn đồng"
        vci_call = next(c for c in p.session.calls if c[0] == "vci")
        assert vci_call[1] == "POST" and vci_call[3]["symbols"] == ["HPG"] and vci_call[3]["countBack"] >= 20
        assert p._state["dnse"]["fails"] == 1 and p._state["vndirect"]["fails"] == 0

        # 3 lỗi liên tiếp → cầu dao DNSE ngắt, lần gọi sau không còn chạm DNSE
        p.history("HPG", end - timedelta(days=30), end)
        p.history("HPG", end - timedelta(days=30), end)
        ok, why = p.endpoint_status("dnse")
        assert not ok and "cầu dao" in why
        n_dnse = sum(1 for c in p.session.calls if c[0] == "dnse")
        p.history("HPG", end - timedelta(days=30), end)
        assert sum(1 for c in p.session.calls if c[0] == "dnse") == n_dnse
        assert p.available()[0], "Các nguồn khác vẫn sống thì provider vẫn khả dụng"
    finally:
        _restore_public_sources(old)


def test_public_kbs_index_aliases_and_sanity():
    end = datetime.now()
    last = ds._expected_last_session(end)
    days = pd.bdate_range(end=last, periods=4)
    old = _with_public_sources("ssi_iboard,dnse,kbs")
    try:
        p = ds.PublicEndpointsProvider()
        kbs_rows = [{"t": f"{d:%Y-%m-%d} 07:00", "o": "21150", "h": "21500", "l": "21000", "c": c, "v": "22105200.0"}
                    for d, c in zip(reversed(days), ["21200", "21400", "21500", "21300"])]  # KBS: ngày giảm dần, số dạng chuỗi
        p.session = FakePublicSession({
            "ssi_iboard": lambda u, q: (_ for _ in ()).throw(AssertionError("SSI iBoard không có UPCOMINDEX")),
            "dnse": lambda u, q: FakeResp(_tv_body(days, [121.0, 121.5, 121.2, 121.75])
                                          if q["symbol"] == "UPCOM" and u.endswith("/index") else {"t": []}),
            "kbs": lambda u, q: FakeResp({"symbol": "HPG", "data_day": kbs_rows}),
        })
        idx = p.history("UPCOMINDEX", end - timedelta(days=20), end)
        assert idx.attrs["endpoint"] == "dnse" and abs(idx["Close"].iloc[-1] - 121.75) < 1e-9, "Chỉ số giữ nguyên điểm"
        assert not any(c[0] == "ssi_iboard" for c in p.session.calls)

        os_order = _with_public_sources("kbs")
        try:
            hpg = p.history("HPG", end - timedelta(days=20), end)
        finally:
            _restore_public_sources(os_order)
        assert hpg.index.is_monotonic_increasing and hpg.index[-1] == last
        assert abs(hpg["Close"].iloc[-1] - 21.2) < 1e-9 and hpg["Volume"].iloc[-1] == 22105200

        # Thang đo sai (SSI iBoard trả HNXIndex = 0.26) → loại, tính là lỗi nguồn
        bad = ds.PublicEndpointsProvider()
        bad.session = FakePublicSession({"ssi_iboard": lambda u, q: FakeResp({"data": _tv_body(days, [0.25, 0.26, 0.26, 0.26])})})
        os_order = _with_public_sources("ssi_iboard")
        try:
            raised = False
            try:
                bad.history("HNXINDEX", end - timedelta(days=20), end)
            except RuntimeError as e:
                raised = "thang đo" in str(e)
            assert raised and bad._state["ssi_iboard"]["fails"] == 1
        finally:
            _restore_public_sources(os_order)
    finally:
        _restore_public_sources(old)


def test_fetch_history_uses_public_and_saves_local():
    import os
    tmp = Path(tempfile.mkdtemp())
    ds.STORE_DIR = tmp
    end = datetime.now()
    last = ds._expected_last_session(end)
    days = pd.bdate_range(end=last, periods=10)
    old_chain, old_session = os.environ.get("DATA_SOURCES"), ds.PUBLIC.session
    old_order = _with_public_sources("dnse")
    os.environ["DATA_SOURCES"] = "public,local"
    try:
        ds.PUBLIC.session = FakePublicSession({"dnse": lambda u, q: FakeResp(_tv_body(days, [26.0 + i * 0.1 for i in range(10)]))})
        df = ds.fetch_history("FPT", end - timedelta(days=30), end)
        info = ds.get_source_info("FPT")
        assert not df.empty and info["source"] == "public" and info["endpoint"] == "dnse" and info["stale_sessions"] == 0
        assert (tmp / "FPT.csv").exists(), "Dữ liệu từ nguồn công khai phải được lưu vào kho cục bộ"
        assert [p.name for p in ds.provider_chain()] == ["public", "local"]
    finally:
        ds.PUBLIC.session = old_session
        _restore_public_sources(old_order)
        if old_chain is None:
            os.environ.pop("DATA_SOURCES", None)
        else:
            os.environ["DATA_SOURCES"] = old_chain


# ----------------------------------------------------------------------------------------------
# Thời gian thực: bảng giá Vietcap (mẫu phản hồi thật HPG phiên 06/11/2026) và nến trong phiên
# ----------------------------------------------------------------------------------------------
VCI_HPG = {
    "listingInfo": {"symbol": "HPG", "ceiling": 23000, "floor": 20000, "refPrice": 21500, "board": "HSX",
                    "tradingStatus": "TRADING_ACTIVATED", "securityStatus": "N", "listedShare": 8442964520,
                    "organName": "Công ty Cổ phần Tập đoàn Hòa Phát", "organShortName": "Hòa Phát", "tradingDate": "2026-11-06"},
    "matchPrice": {"accumulatedValue": 468685.315, "accumulatedVolume": 22105200, "avgMatchPrice": 21202.49,
                   "currentRoom": 2288039792, "totalRoom": 4137052614, "foreignBuyVolume": 1940683, "foreignSellVolume": 3219206,
                   "foreignBuyValue": 41238945600, "foreignSellValue": 68317201950, "highest": 21400, "lowest": 21050,
                   "matchPrice": 21200, "openPrice": 21150, "session": "ENDED", "time": "2026-11-06T07:45:00.011Z"},
    "bidAsk": {"askPrices": [{"price": 21200, "volume": 12900}, {"price": 21250, "volume": 109300}, {"price": 21300, "volume": 90800}],
               "bidPrices": [{"price": 21150, "volume": 1104000}, {"price": 21100, "volume": 929500}, {"price": 21050, "volume": 1161800}]},
}


def test_price_board_parse_cache_and_snapshot():
    p = ds.PublicEndpointsProvider()
    board_calls = []

    def board(url, payload):
        board_calls.append(payload)
        return FakeResp([VCI_HPG, {"listingInfo": None, "bidAsk": "", "matchPrice": ""}])  # mã sai → listingInfo None

    p.session = FakePublicSession({"vci": board})
    out = p.price_board(["hpg", "ZZZZ"])
    assert set(out) == {"HPG"}, out
    q = out["HPG"]
    assert q["price"] == 21.2 and q["ref"] == 21.5 and q["ceiling"] == 23.0 and q["floor"] == 20.0
    assert q["change"] == -0.3 and q["change_pct"] == -1.4 and q["exchange"] == "HOSE"
    assert q["value_bn"] == 468.69 and q["volume"] == 22105200
    assert q["foreign_net_bn"] == round((41238945600 - 68317201950) / 1e9, 2)
    assert q["bid"][0] == {"price": 21.15, "volume": 1104000} and len(q["ask"]) == 3
    p.price_board(["HPG", "ZZZZ"])
    assert len(board_calls) == 1, "Gọi lại trong 3 giây phải dùng bộ nhớ đệm"

    import fundamental_fetcher as ff
    snap = ff._snapshot_from_quote(q)
    assert snap["match_price"] == 21.2 and snap["foreign_net_volume"] == 1940683 - 3219206
    assert abs(snap["foreign_ownership_pct"] - (4137052614 - 2288039792) / 8442964520 * 100) < 0.01
    assert snap["flags"] == [], "HPG phiên 06/11 không có cảnh báo"
    text = ff.format_company_dossier(snap, None, 21.2)
    assert "21.15×1,104,000" in text and "ĐANG DIỄN RA" not in text

    floor_q = dict(q, price=20.0, bid=[], session="LO")
    floor_snap = ff._snapshot_from_quote(floor_q)
    assert any("TRẮNG BÊN MUA" in f for f in floor_snap["flags"])
    assert "ĐANG DIỄN RA" in ff.format_company_dossier(floor_snap, None, 20.0)


def test_intraday_and_market_session():
    old = _with_public_sources("dnse,vndirect,ssi_iboard,vci,kbs")
    try:
        p = ds.PublicEndpointsProvider()
        day1 = [pd.Timestamp("2026-11-05 02:15", tz="UTC") + pd.Timedelta(minutes=i) for i in range(3)]
        day2 = [pd.Timestamp("2026-11-06 02:15", tz="UTC") + pd.Timedelta(minutes=i) for i in range(4)]
        ts = [int(x.timestamp()) for x in day1 + day2]
        body = {"t": ts, "o": [21.0] * 7, "h": [21.3] * 7, "l": [20.9] * 7,
                "c": [21.0, 21.1, 21.2, 21.15, 21.2, 21.25, 21.2], "v": [1000] * 7}
        p.session = FakePublicSession({
            "dnse": lambda u, q: FakeResp({"error": "down"}, 503),
            "vndirect": lambda u, q: FakeResp(body if q["resolution"] == "1" else {"t": []}),
        })
        df = p.intraday("HPG", "1")
        assert df.attrs["endpoint"] == "vndirect" and len(df) == 4, "Chỉ giữ phiên gần nhất"
        assert df.index[0] == pd.Timestamp("2026-11-06 09:15"), "Giờ phải là giờ Việt Nam"
        assert not any(c[0] in ("vci", "kbs") for c in p.session.calls), "Vietcap/KBS không dùng cho nến phút"
        try:
            p.intraday("HPG", "2")
            raise AssertionError("Khung 2 phút phải bị từ chối")
        except ValueError:
            pass
    finally:
        _restore_public_sources(old)

    s = ds.market_session(datetime(2026, 11, 9, 10, 0))
    assert s["state"] == "open" and s["live"]
    assert ds.market_session(datetime(2026, 11, 9, 12, 0))["state"] == "lunch_break"
    assert ds.market_session(datetime(2026, 11, 8, 10, 0))["state"] == "closed"  # Chủ nhật
    assert not ds.market_session(datetime(2026, 11, 9, 16, 0))["live"]


if __name__ == "__main__":
    tests = [v for k, v in dict(globals()).items() if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
        print(f"[PASS] {t.__name__}")
    print(f"\n[+] {len(tests)} data source tests passed")
