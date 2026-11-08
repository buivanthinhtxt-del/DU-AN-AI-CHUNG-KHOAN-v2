"""
Adversarial Stress Test Suite for VN Stock AI Analysis System v5.0
Empirical verification of mathematical, indicator, forecast audit, and disambiguation invariants.
"""
import calendar
import concurrent.futures
import datetime
import json
import os
import random
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

# Add backend directory to sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

import forecast_audit as fa
import quant_engine as qe


class TestAdversarialV5Suite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Ensure clean test environment in cache
        cls.test_symbols = [
            "ADV_TEST_ATC",
            "ADV_TEST_FA",
            "ADV_TEST_ZERO",
            "ADV_TEST_CORRUPT",
            "ADV_CONCURRENCY",
        ]
        cls._cleanup_test_cache()

    @classmethod
    def tearDownClass(cls):
        cls._cleanup_test_cache()

    @classmethod
    def _cleanup_test_cache(cls):
        for sym in cls.test_symbols:
            p = fa.get_audit_cache_path(sym)
            if p.exists():
                try:
                    p.unlink()
                except Exception:
                    pass
            tmp_p = p.with_suffix(".tmp")
            if tmp_p.exists():
                try:
                    tmp_p.unlink()
                except Exception:
                    pass

    # =========================================================================
    # OBJECTIVE 1: Mathematical & Indicator Invariants
    # =========================================================================

    def test_analyze_atc_edge_cases(self):
        """Stress-test _analyze_atc against null, empty, flat, single-candle, and spike data."""
        # 1. None DataFrame
        res_none = qe._analyze_atc(None)
        self.assertEqual(res_none["clv"], 0.5)
        self.assertEqual(res_none["clv_pct"], 50.0)
        self.assertFalse(res_none["derivative_week_warning"])

        # 2. Empty DataFrame
        res_empty = qe._analyze_atc(pd.DataFrame())
        self.assertEqual(res_empty["clv"], 0.5)
        self.assertFalse(res_empty["derivative_week_warning"])

        # 3. Flat candle (High == Low == Close == Open) -> Zero price range
        df_flat = pd.DataFrame(
            {"Close": [30.0], "High": [30.0], "Low": [30.0], "Open": [30.0]},
            index=[pd.Timestamp("2026-11-05")],
        )
        res_flat = qe._analyze_atc(df_flat)
        self.assertEqual(res_flat["clv"], 0.5)
        self.assertEqual(res_flat["upper_wick"], 0.0)
        self.assertEqual(res_flat["lower_wick"], 0.0)
        self.assertIn("Cân bằng", res_flat["session_close_position"])

        # 4. Single-candle DataFrame
        df_single = pd.DataFrame(
            {"Close": [25.0], "High": [26.0], "Low": [24.0], "Open": [24.5]},
            index=[pd.Timestamp("2026-11-05")],
        )
        res_single = qe._analyze_atc(df_single)
        self.assertEqual(res_single["clv"], 0.5)
        self.assertEqual(res_single["upper_wick"], 1.0)
        self.assertEqual(res_single["lower_wick"], 0.5)

        # 5. Extreme spike (High is 1,000x Close, Close == Low)
        df_spike = pd.DataFrame(
            {"Close": [10.0], "High": [10000.0], "Low": [10.0], "Open": [15.0]},
            index=[pd.Timestamp("2026-11-05")],
        )
        res_spike = qe._analyze_atc(df_spike)
        self.assertEqual(res_spike["clv"], 0.0)
        self.assertTrue(res_spike["clv_pct"] == 0.0)
        self.assertGreaterEqual(res_spike["upper_wick"], 9980.0)

        # 6. Derivative week detection across 3rd Thursdays of 2026
        # In Nov 2026: 3rd Thursday is Nov 19.
        # Monday is Nov 16, Friday is Nov 20.
        df_thu3 = pd.DataFrame(
            {"Close": [25.0], "High": [26.0], "Low": [24.0], "Open": [25.0]},
            index=[pd.Timestamp("2026-11-19")],
        )
        self.assertTrue(qe._analyze_atc(df_thu3)["derivative_week_warning"])

        df_mon = pd.DataFrame(
            {"Close": [25.0], "High": [26.0], "Low": [24.0], "Open": [25.0]},
            index=[pd.Timestamp("2026-11-16")],
        )
        self.assertTrue(qe._analyze_atc(df_mon)["derivative_week_warning"])

        df_fri = pd.DataFrame(
            {"Close": [25.0], "High": [26.0], "Low": [24.0], "Open": [25.0]},
            index=[pd.Timestamp("2026-11-20")],
        )
        self.assertTrue(qe._analyze_atc(df_fri)["derivative_week_warning"])

        # Non-derivative trading day (Nov 10, 2026 - Tuesday of week 2)
        df_non_deriv = pd.DataFrame(
            {"Close": [25.0], "High": [26.0], "Low": [24.0], "Open": [25.0]},
            index=[pd.Timestamp("2026-11-10")],
        )
        self.assertFalse(qe._analyze_atc(df_non_deriv)["derivative_week_warning"])

    def test_exit_stops_invariants(self):
        """
        Verify exit_stops triad properties:
        - Price-Stop buffer must strictly satisfy >= 1.5*ATR (when within risk ceiling)
        - Absolute stop distance must never exceed 12% risk ceiling
        - All three stops (Price-Stop, Thesis-Stop, Time-Stop) must be populated.
        """
        # Test across multiple price and volatility regimes
        test_scenarios = [
            ("Low Volatility", 100.0, 0.5),      # ATR = 0.5% of price
            ("Normal Volatility", 100.0, 2.0),   # ATR = 2.0% of price
            ("High Volatility", 100.0, 5.0),     # ATR = 5.0% of price
            ("Extreme Volatility", 100.0, 12.0), # ATR = 12.0% of price
            ("Penny Stock Low Vol", 5.0, 0.05),  # ATR = 1.0% of price
            ("Penny Stock High Vol", 5.0, 0.6),  # ATR = 12.0% of price
        ]

        for desc, close, atr in test_scenarios:
            plan = qe._baseline_plan(close=close, atr=atr, levels={}, stage=2, risk_profile="Trung bình")
            stops = plan.get("exit_stops", {})

            self.assertIn("price_stop", stops, f"[{desc}] Missing price_stop")
            self.assertIn("thesis_stop", stops, f"[{desc}] Missing thesis_stop")
            self.assertIn("time_stop", stops, f"[{desc}] Missing time_stop")

            ps = stops["price_stop"]
            mid = (plan["entry_low"] + plan["entry_high"]) / 2
            stop_dist = mid - ps["price"]
            stop_pct = ps["distance_pct"]

            # Mathematical invariant 1: Stop risk cannot exceed 12.0% (tolerance 0.05 for rounding)
            self.assertLessEqual(
                stop_pct,
                12.05,
                f"[{desc}] Stop percentage {stop_pct}% exceeded 12% risk ceiling!",
            )

            # Mathematical invariant 2: When 1.5*ATR <= 12% of mid, stop_dist >= 1.5*ATR
            if 1.5 * atr <= mid * 0.12:
                self.assertGreaterEqual(
                    stop_dist,
                    (1.5 * atr) - 1e-6,
                    f"[{desc}] Stop distance {stop_dist} is less than 1.5*ATR ({1.5 * atr})",
                )

            # Invariant 3: Time-Stop sessions must be within [5, 15]
            ts = stops["time_stop"]
            self.assertTrue(5 <= ts.get("sessions", 0) <= 15)

            # Invariant 4: Thesis-Stop must have actionable signals
            ths = stops["thesis_stop"]
            self.assertTrue(len(ths.get("condition", "")) > 0)
            self.assertTrue(len(ths.get("trigger_signals", [])) >= 2)

    def test_causal_hypotheses_1000_random_profiles(self):
        """
        Stress test _evaluate_causal_hypotheses across 1,000 randomized profiles:
        Prove that sum(prob_i) == 1.0 (within 1e-4 tolerance) across all inputs,
        and all 6 hypotheses have valid bounds [0.0, 1.0].
        """
        random.seed(1337)
        stages = [1, 2, 3, 4, 5, 0, -1, None]
        dist_options = [0, 1, 4, 6, 15, None]
        accu_options = [0, 2, 5, 10, None]
        vol_ratios = [0.2, 0.9, 1.25, 2.5, 5.0, None]
        betas = [-1.5, 0.0, 0.8, 1.35, 2.5, None]
        clvs = [0.0, 0.12, 0.35, 0.5, 0.85, 1.0, None]
        spring_opts = ["Spring loại 1", "Spring loại 2", "Test cung", "None", None]
        foreign_opts = ["MUA RÒNG MẠNH", "BÁN RÒNG MẠNH", "CÂN BẰNG", None]

        for i in range(1000):
            prof = {
                "trend": {"stage": random.choice(stages)},
                "flow": {
                    "distribution_days_25": random.choice(dist_options),
                    "accumulation_days_25": random.choice(accu_options),
                    "up_down_volume_ratio_20d": random.choice(vol_ratios),
                },
                "relative_strength": {
                    "beta_120d": random.choice(betas),
                    "excess_20d": random.choice([-10.0, 0.0, 5.0, None]),
                    "rs_line_vs_ma50": random.choice(["nằm trên", "nằm dưới", None]),
                },
                "atc_analysis": {
                    "clv": random.choice(clvs),
                    "derivative_week_warning": random.choice([True, False]),
                },
                "tactical_6step": {
                    "spring_analysis": random.choice(spring_opts),
                    "foreign_cycle_analysis": random.choice(foreign_opts),
                },
            }

            hyps = qe._evaluate_causal_hypotheses(prof)
            self.assertEqual(len(hyps), 6, f"Iteration {i}: expected 6 hypotheses")
            prob_sum = sum(h["prob"] for h in hyps)
            self.assertAlmostEqual(
                prob_sum,
                1.0,
                places=4,
                msg=f"Iteration {i}: Probability sum {prob_sum} deviates from 1.0",
            )
            for h in hyps:
                self.assertGreaterEqual(h["prob"], 0.0, f"Iteration {i}: Negative prob {h}")
                self.assertLessEqual(h["prob"], 1.0, f"Iteration {i}: Prob > 1.0: {h}")

    def test_entity_disambiguation_robustness(self):
        """Verify ENTITY_DISAMBIGUATION and SECTOR_FORENSIC_GUIDE handle casing, whitespace, unknown."""
        # 1. Known entities with whitespace and casing
        oil = qe.get_entity_disambiguation("  oIl \n")
        self.assertIsNotNone(oil)
        self.assertIn("PVOIL", oil["stock_entity"])
        self.assertIn("KHÔNG PHẢI là giá dầu thô thế giới", oil["disambiguation_rule"])

        vix = qe.get_entity_disambiguation("\tVix\r\n")
        self.assertIsNotNone(vix)
        self.assertIn("Chứng khoán VIX", vix["stock_entity"])
        self.assertIn("KHÔNG PHẢI là chỉ số đo lường tâm lý phố Wall", vix["disambiguation_rule"])

        # 2. Other mapped entities
        for sym in ["GAS", "HPG", "PLX", "PVD", "PVS", "BSR"]:
            d = qe.get_entity_disambiguation(sym.lower())
            self.assertIsNotNone(d, f"Failed for {sym}")
            self.assertTrue(len(d["disambiguation_rule"]) > 20)

        # 3. Unknown and empty tickers
        self.assertIsNone(qe.get_entity_disambiguation("UNKNOWN"))
        self.assertIsNone(qe.get_entity_disambiguation(""))
        self.assertIsNone(qe.get_entity_disambiguation(None))

        # 4. Sector forensic guide bank archetype propagation
        vcb_guide = qe.get_sector_forensic_guide("  VCB  ")
        self.assertIsNotNone(vcb_guide)
        self.assertEqual(vcb_guide["sector"], "Ngân hàng Thương mại (VCB)")
        self.assertIn("NIM", str(vcb_guide["key_metrics"]))

        # Suffix BANK
        tech_bank = qe.get_sector_forensic_guide("VIETINBANK")
        self.assertIsNotNone(tech_bank)

    # =========================================================================
    # OBJECTIVE 2: Forecast Audit Persistence & Scoring
    # =========================================================================

    def test_forecast_audit_missing_and_corrupt_cache(self):
        """Test audit_historical_forecast with missing cache and corrupted JSON files."""
        # 1. Missing cache
        res_missing = fa.audit_historical_forecast("ADV_TEST_MISSING", current_price=25.0)
        self.assertFalse(res_missing["has_history"])
        self.assertEqual(res_missing["audit_count"], 0)
        self.assertIsNone(res_missing["last_audit"])

        # 2. Corrupted JSON file (syntax error)
        p_corrupt = fa.get_audit_cache_path("ADV_TEST_CORRUPT")
        p_corrupt.write_text("{{malformed_json: true", encoding="utf-8")
        res_corrupt = fa.audit_historical_forecast("ADV_TEST_CORRUPT", current_price=25.0)
        self.assertFalse(res_corrupt["has_history"])
        self.assertEqual(res_corrupt["audit_count"], 0)

        # 3. Corrupted JSON structure (list instead of dict)
        p_corrupt.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
        res_list = fa.audit_historical_forecast("ADV_TEST_CORRUPT", current_price=25.0)
        self.assertFalse(res_list["has_history"])
        self.assertEqual(res_list["audit_count"], 0)

    def test_forecast_audit_future_and_zero_prices(self):
        """Test audit_historical_forecast with future dates, zero prices, and negative prices."""
        sym = "ADV_TEST_ZERO"
        rec = {
            "as_of_price": 20.0,
            "target_1": 22.0,
            "stop_loss": 18.0,
            "action": "Mua",
            "stance": "Tích cực",
            "date": "2026-11-01",
        }
        fa.save_forecast_audit(sym, rec, current_price=20.0, current_date="2026-11-01")

        # 1. Future date test (current_date far in the future)
        res_future = fa.audit_historical_forecast(sym, current_price=22.0, current_date="2099-12-31")
        self.assertTrue(res_future["has_history"])
        self.assertEqual(res_future["last_audit"]["time_score"], 0.4)

        # 2. Invalid date format
        res_inv_date = fa.audit_historical_forecast(sym, current_price=22.0, current_date="NOT-A-DATE")
        self.assertTrue(res_inv_date["has_history"])
        self.assertEqual(res_inv_date["last_audit"]["time_score"], 1.0)  # falls back to elapsed_days=5

        # 3. Current price is zero (extreme crash or suspended)
        res_zero = fa.audit_historical_forecast(sym, current_price=0.0, current_date="2026-11-05")
        self.assertTrue(res_zero["has_history"])
        self.assertEqual(res_zero["last_audit"]["direction_score"], 0.0)
        self.assertEqual(res_zero["last_audit"]["actual_price"], 0.0)

    def test_forecast_audit_zero_division_guard(self):
        """
        Adversarial test: If target_1 evaluates to 0.0 (e.g. from string '0' or zero target in historical cache),
        audit_historical_forecast must not raise ZeroDivisionError.
        """
        sym = "ADV_TEST_ZERO_DIV"
        p = fa.get_audit_cache_path(sym)
        # Manually create a cache record with target_1 = 0.0 and predicted_direction = DOWN
        corrupted_record = {
            "symbol": sym,
            "records": [
                {
                    "as_of_price": 25.0,
                    "target_1": "0",  # String '0' becomes float 0.0
                    "stop_loss": 20.0,
                    "predicted_direction": "DOWN",
                    "date": "2026-11-01",
                }
            ],
        }
        p.write_text(json.dumps(corrupted_record), encoding="utf-8")
        try:
            # When current_price is 30.0 (price increased instead of dropping),
            # this triggers the amplitude_score calculation path.
            audit = fa.audit_historical_forecast(sym, current_price=30.0)
            # If guarded, amplitude_score should be a valid float (e.g. 0.0)
            self.assertTrue(audit["has_history"])
            self.assertIsInstance(audit["last_audit"]["amplitude_score"], (int, float))
        except ZeroDivisionError as e:
            # We explicitly record this finding for the challenge report
            self.fail(f"CRITICAL VULNERABILITY: ZeroDivisionError in audit_historical_forecast: {e}")
        finally:
            if p.exists():
                p.unlink(missing_ok=True)

    def test_concurrency_stress_and_cache_integrity(self):
        """
        Stress test concurrent save_forecast_audit calls across 10 worker threads.
        Verify whether cache remains uncorrupted valid JSON despite OS file locks.
        """
        sym = "ADV_CONCURRENCY"
        p = fa.get_audit_cache_path(sym)

        def worker(idx):
            return fa.save_forecast_audit(
                sym,
                {
                    "as_of_price": 30.0 + idx,
                    "target_1": 33.0 + idx,
                    "stop_loss": 27.0 + idx,
                    "action": "Mua",
                    "stance": "Tích cực",
                },
                current_price=30.0 + idx,
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            results = list(executor.map(worker, range(16)))

        # Verify cache file exists and is valid JSON
        self.assertTrue(p.exists(), "Cache file was not created")
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            self.assertEqual(data["symbol"], sym)
            self.assertIsInstance(data["records"], list)
            self.assertGreater(len(data["records"]), 0)
        except Exception as e:
            self.fail(f"Cache file was corrupted after concurrent writes: {e}")


if __name__ == "__main__":
    unittest.main()
