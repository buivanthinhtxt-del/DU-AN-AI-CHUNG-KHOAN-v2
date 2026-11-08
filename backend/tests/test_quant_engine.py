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
    ctx = ai.build_analysis_context("HPG", df, [], {}, {}, {"VNINDEX": idx}, {}, {}, False)
    rep = ai._rule_based_report(ctx, "Test")
    assert rep["engine"] == "rule_based"
    assert ai.FALLBACK_MARKER in rep["analysis"]
    for key in ("verdict", "thesis", "trade_plan", "scenarios", "risks", "monitoring", "predictions", "scores", "quant_snapshot"):
        assert rep.get(key), key
    assert len(rep["analysis"]) > 2000
    assert "tactical_6step" in rep["quant_snapshot"]
    assert "Bộ Quy Tắc Thực Chiến T+2,5" in rep["analysis"]


def test_tactical_6step_and_prompt_loading():
    # Kiểm tra phân loại 5 nhóm Tạo lập
    assert qe.classify_stock_archetype("VIC")["group_key"] == "INDEX_PILLAR"
    assert qe.classify_stock_archetype("VIX")["group_key"] == "HIGH_BETA_ECOSYSTEM"
    assert qe.classify_stock_archetype("HPG")["group_key"] == "CORE_PRODUCTION"
    assert qe.classify_stock_archetype("TCB")["group_key"] == "BANK_LIQUIDITY_KING"
    assert qe.classify_stock_archetype("OIL")["group_key"] == "GEOPOLITICAL_DEFENSIVE"

    # Kiểm tra tính toán 6 bước và công thức chốt lời 3 nhịp (30% - 50% - 20%)
    df = make_df()
    p = qe.build_quant_profile(df, symbol="HPG", snapshot={
        "bid_ask": {
            "bid": [(27.1, 500000), (27.05, 300000), (27.0, 200000)],
            "ask": [(27.15, 150000), (27.2, 100000), (27.25, 100000)],
        },
        "foreign_history": {
            "recent": True,
            "net_1d_bn": 45.2,
            "net_5d_bn": 120.5,
            "net_20d_bn": 380.0,
        },
    })
    t6 = p["tactical_6step"]
    assert t6["archetype"]["group_key"] == "CORE_PRODUCTION"
    pt = t6["profit_taking_3tier"]
    assert "tier1_sell_30pct" in pt and "tier2_hold_50pct_trailing" in pt and "tier3_hold_20pct_fomo" in pt
    assert len(t6["checklist_5m"]) == 5
    assert "TƯỜNG ĐỠ TỔ CHỨC" in t6["order_book_analysis"]
    assert "KHỐI NGOẠI" in t6["foreign_cycle_analysis"]

    # Kiểm tra nạp Master Prompt 4.0 không bị rỗng
    parts = ai.load_prompt_parts()
    sys_p, usr_t = parts["system"], parts["user"]
    assert len(sys_p) > 2000 and len(usr_t) > 500
    assert "BỘ QUY TẮC THỰC CHIẾN 6 BƯỚC" in sys_p
    assert "BỘ QUY TẮC THỰC CHIẾN 6 BƯỚC" in usr_t


def test_sector_forensic_and_disambiguation():
    # 1. Kiểm tra từ điển đặc thù ngành SECTOR_FORENSIC_GUIDE
    for sym in ["VIC", "VHM", "VRE", "SSI", "VIX", "HPG", "OIL", "CTD", "FPT", "TCB", "VCB", "BANK"]:
        guide = qe.get_sector_forensic_guide(sym)
        assert guide is not None, f"Thiếu forensic guide cho {sym}"
        assert guide["sector"] and len(guide["key_metrics"]) >= 2
        assert len(guide["accounting_red_flags"]) >= 1
        assert len(guide["trading_caveats"]) > 20

    # Kiểm tra nội dung đặc thù của một số mã cốt lõi
    vic_g = qe.get_sector_forensic_guide("VIC")
    assert any("VinFast" in m for m in vic_g["key_metrics"])
    assert "CFO" in str(vic_g["accounting_red_flags"])

    hpg_g = qe.get_sector_forensic_guide("HPG")
    assert any("Dung Quất 2" in m for m in hpg_g["key_metrics"])

    oil_g = qe.get_sector_forensic_guide("OIL")
    assert any("Quỹ bình ổn giá" in m for m in oil_g["key_metrics"])
    assert "KHÔNG phải công ty khai thác dầu thô" in oil_g["trading_caveats"]

    # 2. Kiểm tra bộ lọc phân biệt thực thể ENTITY_DISAMBIGUATION
    for sym in ["OIL", "VIX", "GAS", "HPG", "PLX", "PVD", "PVS"]:
        ed = qe.get_entity_disambiguation(sym)
        assert ed is not None, f"Thiếu entity disambiguation cho {sym}"
        assert ed["stock_entity"] and ed["business_nature"]
        assert ed["common_confusion"] and ed["disambiguation_rule"]

    # Kiểm tra chi tiết triệt tiêu ảo giác
    oil_ed = qe.get_entity_disambiguation("OIL")
    assert "KHÔNG PHẢI là giá dầu thô thế giới" in oil_ed["disambiguation_rule"]
    assert "Brent" in oil_ed["common_confusion"]

    vix_ed = qe.get_entity_disambiguation("VIX")
    assert "KHÔNG PHẢI là chỉ số đo lường tâm lý phố Wall" in vix_ed["disambiguation_rule"]
    assert "CBOE" in vix_ed["common_confusion"]

    gas_ed = qe.get_entity_disambiguation("GAS")
    assert "Henry Hub" in gas_ed["disambiguation_rule"] or "Henry Hub" in gas_ed["common_confusion"]

    pvd_ed = qe.get_entity_disambiguation("PVD")
    assert "giàn khoan" in pvd_ed["disambiguation_rule"]


def test_analyze_atc_and_clv():
    # 1. Kịch bản nến kéo dứt khoát sát đỉnh phiên (CLV cao >= 0.85)
    df_strong = pd.DataFrame(
        {"Open": [28.0], "High": [30.0], "Low": [27.0], "Close": [29.7], "Volume": [1_000_000.0]},
        index=pd.to_datetime(["2026-11-06"]),
    )
    atc_strong = qe._analyze_atc(df_strong)
    assert atc_strong["clv"] >= 0.85, atc_strong
    assert "sát đỉnh" in atc_strong["session_close_position"] or "Kéo dứt khoát" in atc_strong["atc_pattern"]

    # 2. Kịch bản nến bị đạp sát đáy phiên (CLV thấp <= 0.15)
    df_weak = pd.DataFrame(
        {"Open": [29.5], "High": [30.0], "Low": [27.0], "Close": [27.2], "Volume": [1_000_000.0]},
        index=pd.to_datetime(["2026-11-06"]),
    )
    atc_weak = qe._analyze_atc(df_weak)
    assert atc_weak["clv"] <= 0.15, atc_weak
    assert "sát đáy" in atc_weak["session_close_position"] or "Đè đạp" in atc_weak["atc_pattern"]

    # 3. Kịch bản nến râu trên dài (bị đạp ATC / cụt đầu)
    df_wick = pd.DataFrame(
        {"Open": [27.5], "High": [30.0], "Low": [27.4], "Close": [27.6], "Volume": [1_000_000.0]},
        index=pd.to_datetime(["2026-11-06"]),
    )
    atc_wick = qe._analyze_atc(df_wick)
    assert atc_wick["upper_wick"] > 2.0
    assert "cụt đầu" in atc_wick["atc_pattern"] or "đạp" in atc_wick["atc_pattern"]

    # 4. Kịch bản nến rút chân mạnh cuối phiên (râu dưới dài)
    df_spring = pd.DataFrame(
        {"Open": [29.0], "High": [29.2], "Low": [26.5], "Close": [28.9], "Volume": [1_000_000.0]},
        index=pd.to_datetime(["2026-11-06"]),
    )
    atc_spring = qe._analyze_atc(df_spring)
    assert atc_spring["lower_wick"] > 2.0
    assert "Rút chân" in atc_spring["atc_pattern"]

    # 5. Kiểm tra tuần đáo hạn phái sinh VN30F (Thứ Năm tuần thứ 3 tháng 11/2026 là ngày 19/11/2026)
    df_deriv = pd.DataFrame(
        {"Open": [28.0], "High": [29.0], "Low": [27.5], "Close": [28.5], "Volume": [1_000_000.0]},
        index=pd.to_datetime(["2026-11-19"]),
    )
    atc_deriv = qe._analyze_atc(df_deriv)
    assert atc_deriv["derivative_week_warning"] is True

    # Ngày đầu tháng không phải tuần đáo hạn
    df_non_deriv = pd.DataFrame(
        {"Open": [28.0], "High": [29.0], "Low": [27.5], "Close": [28.5], "Volume": [1_000_000.0]},
        index=pd.to_datetime(["2026-11-02"]),
    )
    atc_non = qe._analyze_atc(df_non_deriv)
    assert atc_non["derivative_week_warning"] is False


def test_exit_stops_triad():
    df = make_df()
    p = qe.build_quant_profile(df, symbol="HPG")
    bp = p["baseline_plan"]
    assert "exit_stops" in bp
    stops = bp["exit_stops"]
    assert p["exit_stops"] == stops
    assert p["tactical_6step"]["exit_stops"] == stops

    # 1. Price-Stop
    ps = stops["price_stop"]
    assert ps["price"] < bp["entry_low"]
    assert ps["pct"] < 0
    assert ps["distance_pct"] <= 12.01
    assert "Stop-Order" in ps["action"]

    # 2. Thesis-Stop
    ts = stops["thesis_stop"]
    assert ts["price"] > 0
    assert ts["condition"]
    assert len(ts["trigger_signals"]) >= 2
    assert "không chờ chạm Price-Stop" in ts["action"]

    # 3. Time-Stop
    t_stop = stops["time_stop"]
    assert t_stop["sessions"] in (10, 15)
    assert "T+10" in t_stop["condition"] or "15 phiên" in t_stop["condition"]
    assert "hạ 50% tỷ trọng" in t_stop["action"]


def test_causal_hypotheses_matrix():
    df = make_df()
    p = qe.build_quant_profile(df, symbol="HPG")
    hyps = p["causal_hypotheses"]
    assert len(hyps) == 6
    expected_ids = ["H1", "H2", "H3", "H4", "H5", "H6"]
    assert [h["id"] for h in hyps] == expected_ids

    total_prob = sum(h["prob"] for h in hyps)
    assert abs(total_prob - 1.0) < 1e-4, f"Tổng xác suất giả thuyết phải bằng 1.0, nhận được: {total_prob}"

    for h in hyps:
        assert 0.0 <= h["prob"] <= 1.0
        assert h["name"] and h["driver"] and h["verifiable_by"]
        assert h["verdict"] in ("Ủng hộ mạnh", "Khả năng cao", "Trung bình", "Ít khả năng")
        assert 0 <= h["likelihood_score"] <= 100


def test_market_layers():
    df = make_df()
    p = qe.build_quant_profile(df, symbol="HPG")
    ml = p["market_layers"]
    assert "layer_1_macro" in ml
    assert "layer_2_market" in ml
    assert "layer_3_sector" in ml
    assert "layer_4_stock" in ml

    assert "SBV" in str(ml["layer_1_macro"]["key_metrics"])
    assert "VN-Index" in ml["layer_2_market"]["name"]
    assert "HPG" in ml["layer_4_stock"]["symbol"]
    assert "Price-Stop" in ml["layer_4_stock"]["exit_stops_triad"]

    # Kiểm tra format_quant_dossier xuất đầy đủ các section mới
    dossier = qe.format_quant_dossier(p)
    assert "[PHÂN TÍCH PHIÊN ATC & VI CẤU TRÚC CUỐI PHIÊN]" in dossier
    assert "[3 CHỐT CHẶN THOÁT LỆNH: PRICE-STOP | THESIS-STOP | TIME-STOP]" in dossier
    assert "[MA TRẬN 6 GIẢ THUYẾT NGUYÊN NHÂN BIẾN ĐỘNG GIÁ (CAUSAL HYPOTHESES)]" in dossier
    assert "[4 LỚP THỊ TRƯỜNG CHUNG (MARKET LAYERS)]" in dossier
    assert "[TỪ ĐIỂN ĐẶC THÙ NGÀNH & BẢNG ĐIỆN PHÂN BIỆT THỰC THỂ]" in dossier


def test_forecast_audit_lifecycle():
    test_sym = "TEST_HPG"
    cache_path = qe.get_audit_cache_path(test_sym)
    if cache_path.exists():
        cache_path.unlink()

    try:
        # 1. Khi chưa có lịch sử
        aud_none = qe.audit_historical_forecast(test_sym, current_price=28.0)
        assert aud_none["has_history"] is False
        assert aud_none["audit_count"] == 0
        assert aud_none["last_audit"] is None

        # 2. Lưu dự báo gốc mới
        mock_report = {
            "trade_plan": {
                "entry_low": 27.0,
                "entry_high": 27.5,
                "target_1": 29.5,
                "target_2": 31.0,
                "stop_loss": 25.5,
                "entry_trigger": "Bứt phá MA20 kèm vol > 1,5x TB20",
            },
            "summary": {"stance": "Tích cực", "action": "Mua"},
            "as_of_price": 27.2,
            "engine": "gemini:gemini-2.5-pro",
        }
        saved = qe.save_forecast_audit(test_sym, mock_report, current_price=27.2, current_date="2026-11-01")
        assert saved is True
        assert cache_path.exists()

        # 3. Đối chiếu kịch bản giá tăng đúng kỳ vọng (UP -> đạt gần mục tiêu)
        aud_win = qe.audit_historical_forecast(test_sym, current_price=29.2, current_date="2026-11-06")
        assert aud_win["has_history"] is True
        assert aud_win["audit_count"] == 1
        la = aud_win["last_audit"]
        assert la["predicted_direction"] == "UP"
        assert la["actual_direction"] == "UP"
        assert la["direction_score"] == 1.0
        assert la["amplitude_score"] >= 0.8
        assert la["condition_score"] == 1.0
        assert la["overall_accuracy_pct"] >= 75.0
        assert la["verdict"] == "CHÍNH XÁC"
        assert "chuẩn xác" in aud_win["lessons_learned"] or "đúng" in aud_win["lessons_learned"]

        # 4. Đối chiếu kịch bản giá gãy ngược chiều (DOWN -> thủng cắt lỗ)
        aud_loss = qe.audit_historical_forecast(test_sym, current_price=24.5, current_date="2026-11-06")
        la_l = aud_loss["last_audit"]
        assert la_l["direction_score"] == 0.0
        assert la_l["condition_score"] == 0.0
        assert la_l["overall_accuracy_pct"] < 50.0
        assert la_l["verdict"] == "SAI LỆCH"
        assert "cắt lỗ" in aud_loss["lessons_learned"]

    finally:
        if cache_path.exists():
            cache_path.unlink()


if __name__ == "__main__":
    tests = [v for k, v in dict(globals()).items() if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
        print(f"[PASS] {t.__name__}")
    print(f"\n[+] {len(tests)} quant tests passed")
