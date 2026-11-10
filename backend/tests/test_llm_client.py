"""Kiểm thử chống treo của llm_client: timeout từng lần gọi, ngân sách tổng, cách ly model quá hạn (không gọi mạng)."""

import os
import sys
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import llm_client  # noqa: E402


class _FakeModels:
    def __init__(self, behaviour):
        self.behaviour = behaviour  # model -> callable(config) -> resp | raise
        self.calls = []

    def generate_content(self, model, contents, config):
        self.calls.append((model, config.http_options.timeout))
        return self.behaviour[model](config)


def _timeout(_cfg):
    raise RuntimeError("The read operation timed out")


def _ok(text):
    return lambda _cfg: SimpleNamespace(text=text)


class TestLLMClientResilience(unittest.TestCase):
    def setUp(self):
        llm_client._cooldown.clear()
        self.env = mock.patch.dict(os.environ, {"GEMINI_API_KEY": "fake-key", "GEMINI_MODELS": "m1,m2,m3"})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        llm_client._cooldown.clear()

    def _run(self, behaviour, **kw):
        fake = SimpleNamespace(models=_FakeModels(behaviour))
        with mock.patch.object(llm_client, "_client", return_value=fake):
            try:
                return llm_client.generate("prompt", **kw), fake.models.calls
            except llm_client.LLMUnavailable as e:
                return e, fake.models.calls

    def test_timeout_classified_and_next_model_used(self):
        self.assertEqual(llm_client.classify_error(RuntimeError("The read operation timed out")), "timeout")
        (text, model, _), calls = self._run({"m1": _timeout, "m2": _ok("xin chào"), "m3": _ok("x")}, use_search=True)
        self.assertEqual((text, model), ("xin chào", "m2"))
        # Lần gọi tra cứu web dùng timeout ngắn (<= SEARCH_CALL_TIMEOUT_S), không phải 300s
        self.assertLessEqual(calls[0][1], llm_client.SEARCH_CALL_TIMEOUT_S * 1000)
        # Model quá hạn bị cách ly → request sau bỏ qua m1
        self.assertNotIn("m1", llm_client.candidate_models(use_search=True))
        self.assertIn("m1", llm_client.candidate_models(use_search=False))

    def test_budget_exhaustion_stops_trying_models(self):
        def slow_timeout(_cfg):
            time.sleep(0.2)
            raise RuntimeError("timed out")

        err, calls = self._run({"m1": slow_timeout, "m2": slow_timeout, "m3": slow_timeout}, budget_s=0.3)
        self.assertIsInstance(err, llm_client.LLMUnavailable)
        self.assertLess(len(calls), 3)  # dừng trước khi thử hết danh sách
        self.assertIn("ngân sách", str(err))

    def test_per_call_timeout_never_exceeds_remaining_budget(self):
        _, calls = self._run({"m1": _ok("ok"), "m2": _ok("x"), "m3": _ok("x")}, budget_s=30)
        self.assertLessEqual(calls[0][1], 30_000)


if __name__ == "__main__":
    unittest.main()
