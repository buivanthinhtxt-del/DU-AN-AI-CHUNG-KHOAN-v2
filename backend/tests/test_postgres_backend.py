"""
Kiểm thử tích hợp PostgreSQL cho lớp lưu trữ bền vững (db_backend).

Chỉ chạy khi có biến môi trường TEST_DATABASE_URL, ví dụ:
    docker run -d --rm --name pgtest -e POSTGRES_PASSWORD=test -p 55432:5432 postgres:16-alpine
    set TEST_DATABASE_URL=postgresql://postgres:test@localhost:55432/postgres
    python -m pytest tests/test_postgres_backend.py -q

CẢNH BÁO: test sẽ XÓA các bảng của ứng dụng trong database được chỉ định -> chỉ dùng DB thử nghiệm.
"""

import os
import sys
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
for _p in (BACKEND_DIR, BACKEND_DIR.parent):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

TEST_URL = os.getenv("TEST_DATABASE_URL", "").strip()

APP_TABLES = [
    "agent_penalties", "council_sessions", "agent_merit_profiles",
    "forecast_records", "forecast_scores", "watchlist",
]


@unittest.skipUnless(TEST_URL, "Cần TEST_DATABASE_URL để chạy kiểm thử Postgres")
class TestPostgresBackend(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._old_url = os.environ.get("DATABASE_URL")
        os.environ["DATABASE_URL"] = TEST_URL
        import db_backend
        import forecast_audit
        from agents import audit_store

        cls.db = db_backend
        cls.fa = forecast_audit
        cls.store = audit_store
        with db_backend.connect("unused.db") as conn:
            for t in APP_TABLES:
                conn.execute(f"DROP TABLE IF EXISTS {t};")
        audit_store._initialized_targets.discard("postgres")
        forecast_audit._pg_ready = False

    @classmethod
    def tearDownClass(cls):
        if cls._old_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = cls._old_url

    def test_01_backend_detection(self):
        self.assertTrue(self.db.postgres_enabled())
        self.assertEqual(self.db.dialect(), "postgres")
        self.assertEqual(self.db.dialect("x.db"), "sqlite")
        self.assertEqual(self.db.storage_info()["backend"], "postgres")

    def test_02_agents_seed_and_penalty(self):
        self.store.init_audit_db()
        agents = self.store.get_all_agents()
        self.assertEqual(len(agents), 5)
        self.assertTrue(all(a["merit_points"] == 20 for a in agents))

        res = self.store.apply_penalty("pg_s1", "HPG", "huyet_vu", "HALLUCINATION", "Bịa số liệu", 5)
        self.assertIsInstance(res["penalty_id"], int)
        self.assertEqual(res["remaining_points"], 15)
        self.assertEqual(res["warning_level"], 1)

        # Phế truất & tái sinh thế hệ mới
        res2 = self.store.apply_penalty("pg_s2", "HPG", "huyet_vu", "RULE_VIOLATION", "Tái phạm", 20)
        self.assertTrue(res2["is_expelled"])
        self.assertEqual(res2["generation"], 2)
        self.assertEqual(res2["remaining_points"], 20)

        prof = self.store.get_agent_profile("huyet_vu")
        self.assertEqual(prof["generation"], 2)
        self.assertGreaterEqual(len(prof["penalties"]), 3)
        self.assertIsInstance(prof["created_at"], str)  # datetime đã được chuẩn hóa sang ISO

        self.store.reset_agents_merit()
        self.assertEqual(self.store.get_agent_profile("huyet_vu")["generation"], 1)

    def test_03_council_session_upsert(self):
        data = {
            "session_id": "pg_sess_1", "symbol": "fpt", "verdict": "MUA",
            "executive_summary": {"line_1": "Mua thăm dò"},
            "debate_transcript": [{"agent": "minh_chu", "text": "Khai mạc"}],
        }
        self.store.save_council_session(data)
        data["verdict"] = "QUAN_SAT"
        self.store.save_council_session(data)  # upsert, không lỗi trùng khóa
        hist = self.store.get_council_history("FPT")
        self.assertEqual(len(hist), 1)
        self.assertEqual(hist[0]["verdict"], "QUAN_SAT")
        self.assertEqual(hist[0]["debate_transcript"][0]["text"], "Khai mạc")

    def test_04_forecast_records_and_scores(self):
        sym = "PGTEST"
        for i in range(25):
            ok = self.fa.save_forecast_audit(
                sym,
                {"summary": {"action": "Mua"}, "trade_plan": {"target_1": 22, "stop_loss": 18},
                 "forecast_id_hint": i},
                current_price=20.0, current_date="2026-11-01",
            )
            self.assertTrue(ok)
        # forecast_id theo giây có thể trùng -> upsert; số bản ghi luôn <= giới hạn
        recs = self.fa.load_forecast_records(sym)
        self.assertGreaterEqual(len(recs), 1)
        self.assertLessEqual(len(recs), self.fa.MAX_RECORDS_PER_SYMBOL)
        self.assertIn(sym, self.fa.list_tracked_symbols())

        audit = self.fa.audit_historical_forecast(sym, 21.0, "2026-11-05")
        self.assertTrue(audit["has_history"])
        self.assertTrue(self.fa.save_forecast_score(sym, "2026-11-05", audit))
        self.assertTrue(self.fa.save_forecast_score(sym, "2026-11-05", audit))  # idempotent
        scores = self.fa.get_forecast_scores(sym)
        self.assertEqual(len(scores), 1)
        self.assertEqual(scores[0]["scored_date"], "2026-11-05")
        self.assertIn("overall_accuracy_pct", scores[0]["detail"])

    def test_05_watchlist(self):
        import database
        database.init_db()
        database.add_watchlist("vnm")
        database.add_watchlist("VNM")  # upsert
        database.add_watchlist("HPG")
        syms = [w["symbol"] for w in database.get_watchlist()]
        self.assertEqual(sorted(syms), ["HPG", "VNM"])
        database.remove_watchlist("HPG")
        self.assertEqual([w["symbol"] for w in database.get_watchlist()], ["VNM"])


if __name__ == "__main__":
    unittest.main()
