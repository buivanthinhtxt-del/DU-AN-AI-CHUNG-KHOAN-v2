"""Kiểm thử chấm điểm dự báo hằng ngày + bảo vệ endpoint quản trị (không gọi mạng)."""

import os
import shutil
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

import pandas as pd

BACKEND_DIR = Path(__file__).resolve().parent.parent
for _p in (BACKEND_DIR, BACKEND_DIR.parent):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import daily_scoring  # noqa: E402
import forecast_audit as fa  # noqa: E402


def _fake_df(close: float, day: str = "2026-11-06") -> pd.DataFrame:
    idx = pd.to_datetime(["2026-11-05", day])
    return pd.DataFrame({"Close": [close * 0.99, close]}, index=idx)


class TestDailyScoring(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self._env = mock.patch.dict(os.environ, {"DATABASE_URL": ""})
        self._env.start()
        self._patches = [
            mock.patch.object(fa, "AUDIT_CACHE_DIR", self.tmp / "forecast_audit"),
            mock.patch.object(fa, "SCORES_SQLITE_PATH", self.tmp / "scores.db"),
        ]
        for p in self._patches:
            p.start()
        fa.save_forecast_audit("AAA", {"summary": {"action": "Mua"}, "trade_plan": {"target_1": 22, "stop_loss": 18}},
                               current_price=20.0, current_date="2026-11-01")
        fa.save_forecast_audit("BBB", {"summary": {"action": "Bán"}, "trade_plan": {"target_1": 9, "stop_loss": 11}},
                               current_price=10.0, current_date="2026-11-01")

    def tearDown(self):
        for p in self._patches:
            p.stop()
        self._env.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_tracked_symbols_from_file_cache(self):
        self.assertEqual(fa.list_tracked_symbols(), ["AAA", "BBB"])

    def test_run_scores_all_and_is_idempotent(self):
        prices = {"AAA": 22.5, "BBB": 9.5, "CCC": 5.0}
        with mock.patch.object(daily_scoring, "get_historical_data", side_effect=lambda s, **k: _fake_df(prices[s])):
            res = daily_scoring.run_daily_scoring(["AAA", "BBB", "ccc"])
            res2 = daily_scoring.run_daily_scoring()  # lấy danh sách mã tự động

        self.assertEqual(res["total_symbols"], 3)
        self.assertEqual(res["counts"].get("scored"), 2)
        self.assertEqual(res["counts"].get("no_forecast"), 1)  # CCC chưa từng khuyến nghị
        aaa = next(r for r in res["results"] if r["symbol"] == "AAA")
        self.assertEqual(aaa["verdict"], "CHÍNH XÁC")
        self.assertEqual(res2["total_symbols"], 2)

        scores = fa.get_forecast_scores()
        self.assertEqual(len(scores), 2)  # chạy 2 lần cùng ngày -> không nhân đôi
        self.assertEqual({s["symbol"] for s in scores}, {"AAA", "BBB"})
        self.assertEqual(fa.get_forecast_scores("aaa")[0]["scored_date"], "2026-11-06")

    def test_data_errors_do_not_abort_run(self):
        def boom(sym, **k):
            if sym == "AAA":
                raise RuntimeError("timeout nguồn dữ liệu")
            return pd.DataFrame()

        with mock.patch.object(daily_scoring, "get_historical_data", side_effect=boom):
            res = daily_scoring.run_daily_scoring()
        self.assertEqual(res["counts"], {"error": 1, "no_data": 1})
        self.assertIsNone(res["avg_accuracy_pct"])

    def test_next_run_skips_weekend(self):
        tz = daily_scoring.VN_TZ
        fri_after = datetime(2026, 11, 13, 16, 0, tzinfo=tz)  # Thứ Sáu 16h -> Thứ Hai 15h45
        nxt = daily_scoring._next_run_after(fri_after)
        self.assertEqual((nxt.weekday(), nxt.hour, nxt.minute), (0, 15, 45))
        mon_before = datetime(2026, 11, 16, 9, 0, tzinfo=tz)
        self.assertEqual(daily_scoring._next_run_after(mon_before).day, 16)


class TestAdminEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient
        import api

        cls.api = api
        cls.client = TestClient(api.app)

    def test_cron_disabled_without_secret(self):
        with mock.patch.dict(os.environ, {"CRON_SECRET": ""}):
            r = self.client.post("/api/cron/daily-score")
        self.assertEqual(r.status_code, 503)

    def test_cron_rejects_wrong_secret(self):
        with mock.patch.dict(os.environ, {"CRON_SECRET": "s3cret"}):
            self.assertEqual(self.client.post("/api/cron/daily-score").status_code, 401)
            self.assertEqual(
                self.client.post("/api/cron/daily-score", headers={"X-Cron-Secret": "nope"}).status_code, 401
            )
            self.assertEqual(self.client.post("/api/council/reset-agents").status_code, 401)

    def test_cron_accepts_correct_secret(self):
        fake = {"total_symbols": 0, "counts": {}, "results": []}
        with mock.patch.dict(os.environ, {"CRON_SECRET": "s3cret"}), \
                mock.patch.object(self.api, "run_daily_scoring", return_value=fake) as m:
            r = self.client.post("/api/cron/daily-score", headers={"X-Cron-Secret": "s3cret"},
                                 json={"symbols": ["HPG"]})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["total_symbols"], 0)
        m.assert_called_once_with(["HPG"])

    def test_health_reports_storage(self):
        r = self.client.get("/api/health")
        self.assertEqual(r.status_code, 200)
        self.assertIn(r.json()["storage"]["backend"], ("sqlite", "postgres"))


if __name__ == "__main__":
    unittest.main()
