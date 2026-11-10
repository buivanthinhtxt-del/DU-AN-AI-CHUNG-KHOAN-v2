"""Kiểm thử luồng tiến độ Hội Đồng Quân Cơ (progress callback + SSE endpoint), không gọi mạng/LLM."""

import asyncio
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

BACKEND_DIR = Path(__file__).resolve().parent.parent
for _p in (BACKEND_DIR, BACKEND_DIR.parent):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from backend.agents.council_engine import CouncilEngine, emit_progress  # noqa: E402


def _parse_sse(text: str):
    events = []
    for block in text.split("\n\n"):
        lines = [ln for ln in block.splitlines() if ln and not ln.startswith(":")]
        if not lines:
            continue
        ev = next(ln[7:] for ln in lines if ln.startswith("event: "))
        data = json.loads(next(ln[6:] for ln in lines if ln.startswith("data: ")))
        events.append((ev, data))
    return events


class TestProgressCallback(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_emit_progress_supports_sync_async_and_broken_callbacks(self):
        got = []

        async def acb(ev):
            got.append(("a", ev["stage"], ev["label"]))

        def broken(ev):
            raise RuntimeError("callback hỏng")

        async def go():
            await emit_progress(None, 1, "running")
            await emit_progress(lambda ev: got.append(("s", ev["stage"])), 2, "done")
            await emit_progress(acb, 3, "running")
            await emit_progress(broken, 4, "done")  # không được ném lỗi ra ngoài

        asyncio.run(go())
        self.assertEqual(got[0], ("s", 2))
        self.assertEqual(got[1][:2], ("a", 3))
        self.assertIn("Tham Mưu", got[1][2])

    def test_deterministic_engine_reports_all_five_stages(self):
        events = []
        engine = CouncilEngine(use_llm=False, db_path=self.tmp / "audit.db")
        res = asyncio.run(engine.run_debate(
            symbol="HPG", quant_profile={}, forecast_audit_res={}, financials={},
            progress_cb=lambda ev: events.append((ev["stage"], ev["status"])),
        ))
        self.assertEqual(events, [(i, "done") for i in range(1, 6)])
        self.assertTrue(res.get("debate_transcript"))


class TestCouncilStreamEndpoint(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient
        import api

        cls.api = api
        cls.client = TestClient(api.app)

    def _fake_run(self, result=None, exc=None):
        async def fake(**kwargs):
            cb = kwargs["progress_cb"]
            for st in range(0, 6):
                await cb({"stage": st, "status": "running"})
                await cb({"stage": st, "status": "done"})
            if exc:
                raise exc
            return result
        return fake

    def test_stream_emits_progress_then_result(self):
        result = {"session_id": "s1", "symbol": "HPG", "verdict": "MUA"}
        with mock.patch.object(self.api, "run_council_debate", side_effect=self._fake_run(result)), \
                mock.patch.object(self.api, "get_cache", return_value=None), \
                mock.patch.object(self.api, "set_cache") as set_cache:
            r = self.client.post("/api/council/debate/stream", json={"symbol": "hpg", "force_refresh": True})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.headers["content-type"].startswith("text/event-stream"))
        events = _parse_sse(r.text)
        self.assertEqual([e for e, _ in events].count("progress"), 12)
        self.assertEqual(events[-1], ("result", result))
        set_cache.assert_called_once()

    def test_stream_uses_cache(self):
        cached = {"session_id": "cached", "verdict": "QUAN_SAT"}
        with mock.patch.object(self.api, "get_cache", return_value=cached), \
                mock.patch.object(self.api, "run_council_debate") as run:
            r = self.client.post("/api/council/debate/stream", json={"symbol": "FPT"})
        events = _parse_sse(r.text)
        self.assertEqual(events[-1], ("result", cached))
        self.assertTrue(events[0][1].get("cached"))
        run.assert_not_called()

    def test_stream_reports_errors_as_events(self):
        with mock.patch.object(self.api, "run_council_debate",
                               side_effect=self._fake_run(exc=ValueError("Không có dữ liệu XYZ"))), \
                mock.patch.object(self.api, "get_cache", return_value=None):
            r = self.client.post("/api/council/debate/stream", json={"symbol": "XYZ", "force_refresh": True})
        ev, data = _parse_sse(r.text)[-1]
        self.assertEqual(ev, "error")
        self.assertEqual(data["status"], 404)

    def test_empty_symbol_rejected(self):
        r = self.client.post("/api/council/debate/stream", json={"symbol": "  "})
        self.assertEqual(r.status_code, 400)


if __name__ == "__main__":
    unittest.main()
