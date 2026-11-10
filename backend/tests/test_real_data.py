"""Kiểm thử dữ liệu thật (logic thuần, không gọi mạng): CFO/LNST, GDKHQ, Shark Tracker, và tích hợp vào Huyết Vũ Lâu."""

import asyncio
import shutil
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

BACKEND_DIR = Path(__file__).resolve().parent.parent
for _p in (BACKEND_DIR, BACKEND_DIR.parent):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import financial_quality as fq  # noqa: E402
import shark_tracker as st  # noqa: E402
from backend.agents.council_engine import CouncilEngine  # noqa: E402

BN = 1e9


def _q(cfo, ni, rev=100, rec=10, inv=20):
    return {"cfo": cfo * BN, "npat_parent": ni * BN, "revenue": rev * BN, "receivables": rec * BN, "inventory": inv * BN}


class TestCashflowQuality(unittest.TestCase):
    def test_good_quality(self):
        qs = [_q(12, 10)] * 8
        r = fq.analyze_cashflow_quality(qs, "NON_FINANCE")
        self.assertEqual(r["cfo_to_npat_ttm"], 1.2)
        self.assertEqual(r["verdict"], "TOT")
        self.assertEqual(r["flags"], [])

    def test_paper_profit_flags(self):
        # LNST dương, CFO âm 3/4 quý, phải thu & tồn kho phình to so với doanh thu
        latest = [_q(-5, 10, rev=110, rec=30, inv=60), _q(-4, 10), _q(-3, 10), _q(2, 10)]
        older = [_q(5, 8, rev=100, rec=10, inv=20)] * 4
        r = fq.analyze_cashflow_quality(latest + older, "NON_FINANCE")
        self.assertEqual(r["verdict"], "YEU")
        self.assertEqual(r["negative_cfo_quarters_4q"], 3)
        text = " ".join(r["flags"])
        self.assertIn("lãi trên giấy", text)
        self.assertIn("Phải thu", text)
        self.assertIn("Tồn kho", text)

    def test_bank_not_applicable_and_missing_data(self):
        self.assertEqual(fq.analyze_cashflow_quality([_q(-50, 9)] * 8, "BANK")["verdict"], "KHONG_AP_DUNG")
        self.assertEqual(fq.analyze_cashflow_quality([_q(5, 5)] * 2, "NON_FINANCE")["verdict"], "KHONG_DU_DU_LIEU")

    def test_name_matching_ignores_accents(self):
        self.assertEqual(fq._strip_accents("Lưu chuyển tiền thuần từ hoạt động kinh doanh"),
                         "luu chuyen tien thuan tu hoat dong kinh doanh")


class TestRightsEvents(unittest.TestCase):
    TODAY = date(2026, 11, 10)

    def _ev(self, typ, ex, note=""):
        return {"type": typ, "label": fq.EVENT_TYPE_LABELS.get(typ, typ), "note": note, "ex_date": ex,
                "days_to_ex": (date.fromisoformat(ex) - self.TODAY).days}

    def test_upcoming_stock_dividend_means_avoid(self):
        r = fq.evaluate_rights_events([self._ev("STOCKDIV", "2026-11-20", "Tỷ lệ 10%"),
                                       self._ev("DIVIDEND", "2026-11-12")], self.TODAY)
        self.assertEqual(r["stance"], "NE_TRUOC_CHOT")
        self.assertIn("2026-11-20", r["advice"])

    def test_recent_dilution_means_buy_after(self):
        r = fq.evaluate_rights_events([self._ev("KINDDIV", "2026-11-01")], self.TODAY)
        self.assertEqual(r["stance"], "BAT_SAU_CHIA")

    def test_cash_dividend_and_nothing(self):
        self.assertEqual(fq.evaluate_rights_events([self._ev("DIVIDEND", "2026-11-11")], self.TODAY)["stance"], "CO_TUC_TIEN")
        self.assertEqual(fq.evaluate_rights_events([self._ev("STOCKDIV", "2026-01-01")], self.TODAY)["stance"],
                         "KHONG_CO_SU_KIEN")


class TestSharkTracker(unittest.TestCase):
    def _t(self, vol, price, side):
        return {"matchVol": str(vol), "matchPrice": str(price), "matchType": side, "createdAt": "2026-11-10T07:00:00Z"}

    def test_tier_thresholds(self):
        self.assertEqual(st.classify_value(1_000_000_001), "shark")
        self.assertEqual(st.classify_value(1_000_000_000), "wolf")
        self.assertEqual(st.classify_value(200_000_000), "wolf")
        self.assertEqual(st.classify_value(199_999_999), "sheep")

    def test_accumulation_signal_and_units(self):
        ticks = [
            self._t(100_000, 20000, "b"),  # 2 tỷ mua chủ động -> Cá Mập
            self._t(1_000, 20.0, "s"),     # giá dạng nghìn đồng -> 20 triệu bán -> Cá Con
            self._t(20_000, 20000, "unknown"),  # ATC 400 triệu -> Sói, không xác định phía
        ]
        r = st.aggregate_ticks(ticks)
        self.assertEqual(r["tiers"]["shark"]["net_value_bn"], 2.0)
        self.assertEqual(r["tiers"]["sheep"]["net_value_bn"], -0.02)
        self.assertEqual(r["tiers"]["wolf"]["unknown_value_bn"], 0.4)
        self.assertEqual(r["signal"], "CA_MAP_GOM_CA_CON_BAN")
        self.assertEqual(r["analyzed_volume"], 121_000)

    def test_fetch_stops_at_previous_session(self):
        page1 = [{"id": i, "createdAt": "2026-11-10T07:00:00Z", "truncTime": str(1000 - i)} for i in range(100)]
        page2 = [{"id": 100, "createdAt": "2026-11-10T02:15:00Z", "truncTime": "1"},
                 {"id": 101, "createdAt": "2026-11-07T07:00:00Z", "truncTime": "0"}]
        responses = iter([page1, page2])

        class _Resp:
            def __init__(self, data):
                self.data = data

            def raise_for_status(self):
                pass

            def json(self):
                return self.data

        with mock.patch.object(st.requests.Session, "post", side_effect=lambda *a, **k: _Resp(next(responses))), \
                mock.patch.object(st, "PAGE_DELAY_S", 0):
            out = st.fetch_ticks("HPG", max_pages=5)
        self.assertEqual(len(out["ticks"]), 101)  # bỏ lệnh của phiên 07/11
        self.assertTrue(out["complete"])
        self.assertEqual(out["session_day"], "2026-11-10")


class TestHuyetVuUsesRealData(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _huyet_vu(self, financials, quant=None):
        res = asyncio.run(CouncilEngine(use_llm=False, db_path=self.tmp / "a.db").run_debate(
            symbol="NVL", quant_profile=quant or {}, forecast_audit_res={}, financials=financials))
        return " ".join(str(x) for x in res["debate_transcript"])

    def test_paper_profit_and_rights_from_real_data(self):
        cfq = {"available": True, "source": "VNDirect", "latest_period": "Q3/2026", "cfo_ttm_bn": -3500.0,
               "npat_ttm_bn": 9000.0, "cfo_to_npat_ttm": -0.39, "verdict": "YEU", "is_financial_company": False,
               "flags": ["LNST 4 quý dương nhưng CFO 4 quý âm — lợi nhuận chưa chuyển thành tiền."]}
        ev = {"stance": "NE_TRUOC_CHOT", "advice": "Né trước chốt: Cổ tức bằng cổ phiếu GDKHQ ngày 2026-11-20"}
        text = self._huyet_vu({"cashflow_quality": cfq, "corporate_events": ev})
        self.assertIn("-0.39x", text)
        self.assertIn("2026-11-20", text)
        self.assertNotIn("trên 0.85x", text)  # câu khẳng định cố định cũ đã bị loại bỏ

    def test_missing_data_is_stated_not_invented(self):
        text = self._huyet_vu({})
        self.assertIn("CHƯA CÓ dữ liệu BCTC quý", text)
        self.assertNotIn("Không có lịch chốt quyền", text)


if __name__ == "__main__":
    unittest.main()
