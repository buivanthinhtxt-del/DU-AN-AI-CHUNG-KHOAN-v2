"""
Kiểm thử offline cho quant_engine và lớp hậu kiểm của ai_analyzer (không cần mạng, không gọi Gemini).
Chạy: python backend/tests/test_quant_engine.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import quant_engine as qe  # noqa: E402
import ai_analyzer as ai  # noqa: E402


def make_df(n=520, drift=0.0005, vol=0.018, seed=7, start=20.0):
    rng = np.random.default_rng(seed)
    rets = rng.normal(drift, vol, n)
    close = start * np.exp(np.cumsum(rets))
    high = close * (1 + np.abs(rng.normal(0, 0.008, n)))
    low = close * (1 - np.abs(rng.normal(0, 0.008, n)))
    open_ = np.r_[close[0], close[:-1]]
    volume = rng.integers(5_000_000, 25_000_000, n).astype(float)
    idx = pd.bdate_range(end="2026-11-06", periods=n)
    return pd.DataFrame({"Open": open_, "High": np.maximum(high, close), "Low": np.minimum(low, close),
                         "Close": close, "Volume": volume}, index=idx)


def test_profile_shapes_and_consistency():
    df, idx = make_df(), make_df(seed=11, start=1700, vol=0.01)
    p = qe.build_quant_profile(df, idx, "Trung bình", cost_basis=22.0)
    bp = p["baseline_plan"]
    assert bp["stop_loss"] < bp["entry_low"] <= bp["entry_high"] < bp["target_1"] <= bp["target_2"], bp
    # Cắt lỗ tối thiểu 1,5×ATR (T+2) và tối đa 12%
    mid = (bp["entry_low"] + bp["entry_high"]) / 2
    atr = p["volatility"]["atr14"]
    assert mid - bp["stop_loss"] >= 1.5 * atr - 0.02, (mid, bp["stop_loss"], atr)
    assert bp["stop_pct"] <= 12.01
    assert 0 < bp["max_position_pct"] <= 20
    assert all(s["price"] < p["close"] for s in p["levels"]["supports"])
    assert all(r["price"] > p["close"] for r in p["levels"]["resistances"])
    assert len(p["stat_ranges"]) == 4 and p["stat_ranges"][0]["low_95"] < p["stat_ranges"][0]["low_68"]
    assert p["relative_strength"] and "beta_120d" in p["relative_strength"]
    assert "holder" in bp
    text = qe.format_quant_dossier(p)
    assert "[VÙNG GIÁ QUAN TRỌNG" in text and "[XÁC SUẤT LỊCH SỬ" in text


def test_strong_uptrend_is_stage_2():
    df = make_df(drift=0.003, vol=0.01, seed=3)
    p = qe.build_quant_profile(df)
    assert p["trend"]["stage"] == 2, p["trend"]


def test_downtrend_is_stage_4_and_market_red():
    df = make_df(drift=-0.003, vol=0.01, seed=5)
    p = qe.build_quant_profile(df)
    assert p["trend"]["stage"] == 4, p["trend"]
    mk = qe.market_regime(df)
    assert "🔴" in mk["status"], mk["status"]


def test_postprocess_fixes_inconsistent_ai_output():
    df, idx = make_df(), make_df(seed=11, start=1700, vol=0.01)
    ctx = ai.build_analysis_context("TST", df, [], {}, {}, {"VNINDEX": idx}, {"risk_profile": "Trung bình"}, {}, False)
    close = ctx["quant"]["close"]
    bad = ai.StockAIReportSchema(
        analysis="x" * 500,
        trade_plan=ai.TradePlan(entry_low=close, entry_high=close * 0.99, stop_loss=close * 1.01,
                                target_1=close * 0.98, target_2=close * 0.97, rr_ratio=5, max_position_pct=90),
        scenarios=[ai.Scenario(name="🟢", probability=50), ai.Scenario(name="🟡", probability=50), ai.Scenario(name="🔴", probability=40)],
        predictions=[ai.PricePredictionItem(days_future=1, low=close * 0.5, high=close * 1.9)],
        summary=ai.ReportSummary(stance="Tích cực", confidence="Cao", action="Mua"),
    ).model_dump()
    rep = ai._postprocess(bad, ctx, "test")
    tp = rep["trade_plan"]
    assert tp["stop_loss"] < tp["entry_low"] <= tp["entry_high"] < tp["target_1"] <= tp["target_2"], tp
    assert tp["max_position_pct"] <= 20
    assert sum(s["probability"] for s in rep["scenarios"]) == 100
    assert [p["days_future"] for p in rep["predictions"]] == [1, 2, 5, 10]
    b1 = ctx["quant"]["stat_ranges"][0]
    assert rep["predictions"][0]["low"] >= b1["low_95"] and rep["predictions"][0]["high"] <= b1["high_95"]
    # Không có BCTC → độ tin cậy không được "Cao"
    assert rep["summary"]["confidence"] != "Cao"
    assert rep["consistency_notes"], "Phải ghi lại các điều chỉnh"


def test_rule_based_report_is_complete():
    df, idx = make_df(), make_df(seed=11, start=1700, vol=0.01)
    ctx = ai.build_analysis_context("TST", df, [], {}, {}, {"VNINDEX": idx}, {}, {}, False)
    rep = ai._rule_based_report(ctx, "Test")
    assert rep["engine"] == "rule_based"
    assert ai.FALLBACK_MARKER in rep["analysis"]
    for key in ("verdict", "thesis", "trade_plan", "scenarios", "risks", "monitoring", "predictions", "scores", "quant_snapshot"):
        assert rep.get(key), key
    assert len(rep["analysis"]) > 2000


if __name__ == "__main__":
    tests = [v for k, v in dict(globals()).items() if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
        print(f"[PASS] {t.__name__}")
    print(f"\n[+] {len(tests)} quant tests passed")
