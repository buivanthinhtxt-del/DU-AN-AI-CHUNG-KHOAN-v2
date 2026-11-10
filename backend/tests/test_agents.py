"""
Automated Testing Suite for Multi-Agent Council & Audit Store (AI Workstation V5.0).

Kiểm thử toàn diện cho module backend/agents/:
1. Pydantic Schema Validation (TestPersonaSchemas):
   - 5 Persona metadata: Minh Chủ Võ Lâm, Huyết Vũ Lâu, Phong Lang Đội, Tham Mưu Các, Cẩm Y Vệ.
   - Pydantic models: MinhChuDirective, HuyetVuLauReport, PhongLangDoiReport, ThamMuuCacReport,
     AgentViolationRecord, CamYVeReport, RadarScoreCard, ExecutiveSummary, InvestmentResolution.
   - Ràng buộc biên (bounds): Điểm số 0-100, Tỷ trọng NAV <= 25%, Giá mua & cắt lỗ > 0, Đúng 3 dòng Executive Summary.
   - Bác bỏ dữ liệu không hợp lệ (missing fields, out-of-bounds, invalid literal types).

2. Điểm Công Huân & Disciplinary Progression (TestMeritAndDisciplinaryProgression):
   - Khởi tạo ban đầu: Đủ 5 Agent với đúng 20 Điểm Công Huân (Thế hệ 1).
   - Cơ chế trừ điểm: -1 điểm / mỗi lỗi vi phạm.
   - Các mốc kỷ luật & cảnh báo:
     * 15 điểm: CANH_BAO_1, user_notification=True, reported_to_minh_chu=True.
     * 10 điểm: CANH_BAO_2, user_notification=False, reported_to_minh_chu=True.
     * 5 điểm: CANH_BAO_3, user_notification=True, reported_to_minh_chu=True.
     * 0 điểm: Phế truất (is_expelled=True), thế hệ N -> N+1, điểm khôi phục 20.
   - Khôi phục Điểm Công Huân (reset_agents_merit).
   - Bền vững cơ sở dữ liệu SQLite: agent_merit_profiles, council_sessions, agent_penalties.

3. Multi-Agent Debate Workflow (TestMultiAgentDebateWorkflow):
   - Chạy DeterministicCouncilEngine và run_council_debate ở chế độ xác định.
   - Thử nghiệm trên nhiều mã: HPG, VHM, SSI (với fallback ticker).
   - Xác minh 5 giai đoạn hoàn tất, transcript chứa 6 lượt phát biểu của 5 Persona khác nhau.
   - Xác minh Khung Tóm tắt Hành động đúng 3 dòng và Radar Score Card đủ 5 chiều.

4. Mock LLM Pipeline (TestMockLLMPipeline):
   - Giả lập (Mock) Gemini Structured Output cho 5 giai đoạn không cần mạng / API key thật.
   - Xác minh engine="gemini", transcript đối thoại đầy đủ và xử lý phạt kỷ luật.
   - Kiểm thử xử lý lỗi API (Rate Limit 429 / Quota) và tự động chuyển sang Deterministic Fallback.
   - Kiểm thử trường hợp không có API key.

5. FastAPI Council Endpoints (TestFastAPICouncilEndpoints):
   - Sử dụng TestClient kiểm thử:
     * GET /api/council/agents
     * POST /api/council/debate (bao gồm cả cache và force_refresh)
     * GET /api/council/history/{symbol}
     * POST /api/council/reset-agents
   - Kiểm tra mã lỗi 400 (thiếu symbol), 404 (mã không tồn tại), 500 (lỗi nội bộ).
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pandas as pd
from pydantic import ValidationError

# Thiết lập đường dẫn import cho backend
BASE_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BASE_DIR.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.agents.personas import (
    AGENT_DEFINITIONS,
    AgentViolationRecord,
    CamYVeReport,
    ExecutiveSummary,
    HuyetVuLauReport,
    InvestmentResolution,
    MinhChuDirective,
    PhongLangDoiReport,
    RadarScoreCard,
    ThamMuuCacReport,
)
from backend.agents.audit_store import (
    AUDIT_DB_PATH,
    apply_penalty,
    get_agent_profile,
    get_all_agents,
    get_council_history,
    get_recent_penalties,
    init_audit_db,
    reset_agents_merit,
    save_council_session,
)
from backend.agents.council_engine import (
    CouncilEngine,
    DeterministicCouncilEngine,
    run_council_debate,
)
from fastapi.testclient import TestClient
from backend.api import app


def make_sample_df(n=300, drift=0.0005, vol=0.018, seed=42, start=28.0) -> pd.DataFrame:
    """Tạo DataFrame giá chứng khoán mẫu 300 phiên phục vụ test xác định offline."""
    rng = np.random.default_rng(seed)
    rets = rng.normal(drift, vol, n)
    close = start * np.exp(np.cumsum(rets))
    high = close * (1 + np.abs(rng.normal(0, 0.008, n)))
    low = close * (1 - np.abs(rng.normal(0, 0.008, n)))
    open_ = np.r_[close[0], close[:-1]]
    volume = rng.integers(5_000_000, 25_000_000, n).astype(float)
    idx = pd.bdate_range(end="2026-11-10", periods=n)
    return pd.DataFrame(
        {
            "Open": open_,
            "High": np.maximum(high, close),
            "Low": np.minimum(low, close),
            "Close": close,
            "Volume": volume,
        },
        index=idx,
    )


# ==============================================================================
# SUITE 1: PYDANTIC SCHEMA VALIDATION & INTEGRITY
# ==============================================================================
class TestPersonaSchemas(unittest.TestCase):
    """Kiểm thử tính toàn vẹn và cơ chế kiểm soát dữ liệu của các Pydantic Schemas."""

    def test_agent_definitions_metadata(self):
        """Xác minh 5 Persona trong AGENT_DEFINITIONS có đầy đủ thuộc tính kiếm hiệp."""
        expected_agents = ["minh_chu", "huyet_vu", "phong_lang", "tham_muu", "cam_y_ve"]
        self.assertEqual(set(AGENT_DEFINITIONS.keys()), set(expected_agents))

        for aid, meta in AGENT_DEFINITIONS.items():
            self.assertEqual(meta["id"], aid)
            self.assertTrue(len(meta["name"]) > 0, f"Name rỗng cho {aid}")
            self.assertTrue(len(meta["role"]) > 0, f"Role rỗng cho {aid}")
            self.assertTrue(len(meta["title"]) > 0, f"Title rỗng cho {aid}")
            self.assertTrue(len(meta["archetype"]) > 0, f"Archetype rỗng cho {aid}")
            self.assertTrue(len(meta["swordplay_tone"]) > 20, f"Khẩu khí quá ngắn cho {aid}")
            self.assertTrue(len(meta["mission"]) > 20, f"Nhiệm vụ quá ngắn cho {aid}")

    def test_minh_chu_directive_schema_valid_and_invalid(self):
        """Kiểm tra schema MinhChuDirective với dữ liệu chuẩn và từ chối khi thiếu trường bắt buộc."""
        valid_data = {
            "general_stance": "VN-Index giữ vùng 1250 điểm, dòng tiền phân hóa mạnh.",
            "focus_areas": ["Kiểm tra CFO vs NI", "Bẫy T+2.5", "Bộ 3 Chốt Chặn"],
            "directive_for_huyet_vu": "Mổ xẻ BCTC HPG xem lãi thật hay lãi ảo.",
            "directive_for_phong_lang": "Soi kỹ lệnh ATC và lực cầu hấp thụ.",
            "directive_for_tham_muu": "Đóng vai ác tìm mọi kẽ hở bác bỏ kèo mua.",
            "directive_for_cam_y_ve": "Trích lục hồ sơ đối chiếu dự báo quá khứ.",
            "martial_speech": "Quân lệnh như sơn! Toàn quân phụng mạng tác chiến!",
        }
        directive = MinhChuDirective(**valid_data)
        self.assertEqual(directive.general_stance, valid_data["general_stance"])
        self.assertEqual(len(directive.focus_areas), 3)

        # Thiếu trường focus_areas -> Phải ném ValidationError
        invalid_data = dict(valid_data)
        del invalid_data["focus_areas"]
        with self.assertRaises(ValidationError):
            MinhChuDirective(**invalid_data)

    def test_huyet_vu_lau_report_valid_and_bounds(self):
        """Kiểm tra schema HuyetVuLauReport và kiểm tra ràng buộc forensic_score (0-100)."""
        valid_data = {
            "forensic_score": 85,
            "cfo_vs_ni_analysis": "CFO thuần đạt +4,200 tỷ, vượt trội so với NI +3,800 tỷ. Lãi thật.",
            "is_paper_profit": False,
            "balance_sheet_risks": ["Nợ vay ngắn hạn 12,000 tỷ cần quan sát"],
            "rights_event_evaluation": "Né trước chốt – Bắt sau chia: Không có lịch chốt quyền trong 30 ngày.",
            "fundamental_verdict": "ƯU_TÚ",
            "martial_speech": "Dòng tiền CFO là chân khí hộ thể, két sắt dồi dào!",
        }
        report = HuyetVuLauReport(**valid_data)
        self.assertEqual(report.forensic_score, 85)
        self.assertFalse(report.is_paper_profit)
        self.assertEqual(report.fundamental_verdict, "ƯU_TÚ")

        # Bounds: forensic_score < 0
        with self.assertRaises(ValidationError):
            HuyetVuLauReport(**{**valid_data, "forensic_score": -1})

        # Bounds: forensic_score > 100
        with self.assertRaises(ValidationError):
            HuyetVuLauReport(**{**valid_data, "forensic_score": 105})

        # Literal: Giá trị phán quyết không nằm trong danh mục cho phép
        with self.assertRaises(ValidationError):
            HuyetVuLauReport(**{**valid_data, "fundamental_verdict": "CỰC_KỲ_TỐT"})

    def test_phong_lang_doi_report_valid_and_bounds(self):
        """Kiểm tra schema PhongLangDoiReport, điểm kỹ thuật 0-100 và vùng gom > 0."""
        valid_data = {
            "tactical_score": 80,
            "wyckoff_phase": "Tích lũy Pha C (Spring & Test)",
            "vsa_signals": ["No Supply Test", "Absorption Volume"],
            "t25_trap_warning": "Lô hàng nổ vol T+2.5 đã về tài khoản và được hấp thụ cạn kiệt.",
            "atc_clv_analysis": "Lệnh ATC khớp chủ động kéo giá đóng cửa sát mức cao nhất ngày, CLV=0.88.",
            "proposed_entry_low": 28.0,
            "proposed_entry_high": 28.5,
            "entry_trigger": "Khớp lệnh vượt 28.2 trong khung giờ 13h45-14h15.",
            "martial_speech": "Đao pháp sổ lệnh dứt khoát, phe mua chiếm hoàn toàn thế chủ động!",
        }
        report = PhongLangDoiReport(**valid_data)
        self.assertEqual(report.tactical_score, 80)
        self.assertEqual(report.proposed_entry_low, 28.0)

        # tactical_score ngoài khoảng 0-100
        with self.assertRaises(ValidationError):
            PhongLangDoiReport(**{**valid_data, "tactical_score": -10})
        with self.assertRaises(ValidationError):
            PhongLangDoiReport(**{**valid_data, "tactical_score": 101})

        # Giá vào lệnh <= 0
        with self.assertRaises(ValidationError):
            PhongLangDoiReport(**{**valid_data, "proposed_entry_low": 0})
        with self.assertRaises(ValidationError):
            PhongLangDoiReport(**{**valid_data, "proposed_entry_high": -5.0})

    def test_tham_muu_cac_report_valid_and_bounds(self):
        """Kiểm tra schema ThamMuuCacReport: max_position_pct không được vượt quá 25% NAV."""
        valid_data = {
            "rejection_recommended": False,
            "rejection_reasons": ["Giá quặng sắt thế giới biến động", "Tỷ giá USD/VND neo cao"],
            "pre_mortem_scenario": "Nếu giá thép giảm sốc 15% và VN-Index đánh mất mốc 1200 điểm.",
            "price_stop": 26.6,
            "thesis_stop": "Gãy đường hỗ trợ MA50 tại 27.0 kèm khối lượng bán > 1.5x trung bình 20 phiên.",
            "time_stop": "T+10 phiên nếu không thể bứt phá vùng cản 29.5.",
            "max_position_pct": 20.0,
            "martial_speech": "Kèo này dù thơm cũng tuyệt đối không được all-in, giữ mạng là trên hết!",
        }
        report = ThamMuuCacReport(**valid_data)
        self.assertEqual(report.max_position_pct, 20.0)
        self.assertEqual(report.price_stop, 26.6)

        # Vi phạm kỷ luật rủi ro: max_position_pct > 25.0
        with self.assertRaises(ValidationError):
            ThamMuuCacReport(**{**valid_data, "max_position_pct": 25.5})

        # max_position_pct < 0
        with self.assertRaises(ValidationError):
            ThamMuuCacReport(**{**valid_data, "max_position_pct": -1.0})

        # price_stop <= 0
        with self.assertRaises(ValidationError):
            ThamMuuCacReport(**{**valid_data, "price_stop": 0.0})

    def test_agent_violation_record_valid_and_literals(self):
        """Kiểm tra schema biên bản kỷ luật AgentViolationRecord."""
        record = AgentViolationRecord(
            agent_id="phong_lang",
            agent_name="Phong Lang Đội",
            violation_type="HALLUCINATION",
            points_deducted=1,
            reason="Tự ý phóng đại khối lượng lệnh kê mua ảo ở bước giá 28.0.",
        )
        self.assertEqual(record.violation_type, "HALLUCINATION")
        self.assertEqual(record.points_deducted, 1)

        # violation_type không hợp lệ
        with self.assertRaises(ValidationError):
            AgentViolationRecord(
                agent_id="phong_lang",
                agent_name="Phong Lang Đội",
                violation_type="CHEATING_INVALID",
                points_deducted=1,
                reason="Lỗi sai",
            )

    def test_cam_y_ve_report_valid_and_bounds(self):
        """Kiểm tra schema CamYVeReport: historical_accuracy_pct 0-100."""
        valid_data = {
            "historical_accuracy_pct": 78.5,
            "last_forecast_review": "Phiên 15/10 dự báo giá tăng đạt T1 sau T+3, đúng hướng và biên độ.",
            "detected_violations": [],
            "audit_verdict": "Các đường chủ tuân thủ nghiêm ngặt số liệu thực tế, không có lỗi ảo giác.",
            "martial_speech": "Sổ son Cẩm Y Vệ ghi nhận: Phiên họp kỷ cương nghiêm cẩn!",
        }
        rep = CamYVeReport(**valid_data)
        self.assertEqual(rep.historical_accuracy_pct, 78.5)

        # Bounds: historical_accuracy_pct < 0 hoặc > 100
        with self.assertRaises(ValidationError):
            CamYVeReport(**{**valid_data, "historical_accuracy_pct": -0.5})
        with self.assertRaises(ValidationError):
            CamYVeReport(**{**valid_data, "historical_accuracy_pct": 100.5})

    def test_radar_score_card_valid_and_bounds(self):
        """Kiểm tra schema RadarScoreCard: Đủ 5 trục và toàn bộ điểm số trong khoảng 0-100."""
        valid_data = {
            "co_ban": 85,
            "ky_thuat": 75,
            "dong_tien": 80,
            "quan_tri_rui_ro": 70,
            "xac_suat_thanh_cong": 78,
            "overall_score": 78,
        }
        card = RadarScoreCard(**valid_data)
        self.assertEqual(card.co_ban, 85)
        self.assertEqual(card.overall_score, 78)

        # Kiểm tra bất kỳ trục nào vượt ngưỡng 0-100 đều bị từ chối
        for axis in ["co_ban", "ky_thuat", "dong_tien", "quan_tri_rui_ro", "xac_suat_thanh_cong", "overall_score"]:
            with self.assertRaises(ValidationError):
                RadarScoreCard(**{**valid_data, axis: 101})
            with self.assertRaises(ValidationError):
                RadarScoreCard(**{**valid_data, axis: -1})

    def test_executive_summary_exact_three_lines(self):
        """Kiểm tra schema ExecutiveSummary: Bắt buộc đúng 3 dòng tóm tắt hành động."""
        valid_data = {
            "action_line": "QUAN SÁT / MUA THĂM DÒ: Giải ngân 15% tại vùng 28.0 - 28.3 trong khung 13h45-14h25.",
            "defense_stops_line": "BỘ 3 CHỐT CHẶN: Price-Stop 26.6 (-6.5%), Thesis-Stop gãy MA50 vol > 1.5x, Time-Stop T+10.",
            "directive_line": "QUÂN LỆNH MINH CHỦ: Huyết Vũ Lâu xác nhận CFO > 0; Tham Mưu Các cảnh báo rủi ro biến động giá quặng.",
            "summary_lines": [
                "QUAN SÁT / MUA THĂM DÒ: Giải ngân 15% tại vùng 28.0 - 28.3 trong khung 13h45-14h25.",
                "BỘ 3 CHỐT CHẶN: Price-Stop 26.6 (-6.5%), Thesis-Stop gãy MA50 vol > 1.5x, Time-Stop T+10.",
                "QUÂN LỆNH MINH CHỦ: Huyết Vũ Lâu xác nhận CFO > 0; Tham Mưu Các cảnh báo rủi ro biến động giá quặng.",
            ],
        }
        summary = ExecutiveSummary(**valid_data)
        self.assertEqual(len(summary.summary_lines), 3)

        # Không đủ 3 dòng (ví dụ 2 dòng) -> ValidationError
        with self.assertRaises(ValidationError):
            ExecutiveSummary(**{**valid_data, "summary_lines": ["Dòng 1", "Dòng 2"]})

        # Quá 3 dòng (ví dụ 4 dòng) -> ValidationError
        with self.assertRaises(ValidationError):
            ExecutiveSummary(**{**valid_data, "summary_lines": ["D1", "D2", "D3", "D4"]})

    def test_investment_resolution_valid_and_bounds(self):
        """Kiểm tra schema InvestmentResolution: Đầy đủ các trường phán quyết và kỷ luật NAV <= 25%."""
        radar = RadarScoreCard(
            co_ban=85,
            ky_thuat=75,
            dong_tien=80,
            quan_tri_rui_ro=70,
            xac_suat_thanh_cong=78,
            overall_score=78,
        )
        lines = [
            "MUA THĂM DÒ: 15% tại vùng 28.0 - 28.3",
            "BỘ 3 CHỐT CHẶN: Price-Stop 26.6",
            "QUÂN LỆNH MINH CHỦ: Giữ nghiêm kỷ luật",
        ]
        valid_data = {
            "action_line": lines[0],
            "defense_stops_line": lines[1],
            "directive_line": lines[2],
            "summary_lines": lines,
            "verdict": "MUA_THAM_DO",
            "radar_scores": radar,
            "entry_low": 28.0,
            "entry_high": 28.3,
            "stop_loss": 26.6,
            "target_1": 30.5,
            "target_2": 32.5,
            "rr_ratio": 2.2,
            "max_nav_pct": 20.0,
            "critique_and_modifications": "Uốn nắn Phong Lang Đội không mua đuổi.",
            "martial_speech": "Minh Chủ ban chiếu!",
        }
        res = InvestmentResolution(**valid_data)
        self.assertEqual(res.verdict, "MUA_THAM_DO")
        self.assertEqual(res.max_nav_pct, 20.0)

        # max_nav_pct > 25.0 -> ValidationError
        with self.assertRaises(ValidationError):
            InvestmentResolution(**{**valid_data, "max_nav_pct": 25.1})

        # verdict không nằm trong Literal
        with self.assertRaises(ValidationError):
            InvestmentResolution(**{**valid_data, "verdict": "MUA_ALL_IN"})


# ==============================================================================
# SUITE 2: ĐIỂM CÔNG HUÂN & DISCIPLINARY PROGRESSION (R3)
# ==============================================================================
class TestMeritAndDisciplinaryProgression(unittest.TestCase):
    """Kiểm thử toàn diện quy chế trừ điểm, cảnh báo 15/10/5, phế truất tại 0 và SQLite audit log."""

    def setUp(self):
        """Tạo một database SQLite tạm biệt lập cho từng test case."""
        self.test_dir = tempfile.mkdtemp(prefix="council_audit_test_")
        self.test_db_path = Path(self.test_dir) / "test_council_audit.db"
        init_audit_db(self.test_db_path)

    def tearDown(self):
        """Dọn dẹp database tạm sau khi test xong."""
        try:
            shutil.rmtree(self.test_dir, ignore_errors=True)
        except Exception:
            pass

    def test_initial_merit_points_and_seeding(self):
        """Xác minh ban đầu gieo mầm đúng 5 Agent, mỗi Agent sở hữu chính xác 20 Điểm Công Huân."""
        agents = get_all_agents(self.test_db_path)
        self.assertEqual(len(agents), 5)

        expected_ids = ["minh_chu", "huyet_vu", "phong_lang", "tham_muu", "cam_y_ve"]
        agent_dict = {a["agent_id"]: a for a in agents}
        self.assertEqual(set(agent_dict.keys()), set(expected_ids))

        for aid in expected_ids:
            a = agent_dict[aid]
            self.assertEqual(a["merit_points"], 20, f"Agent {aid} không bắt đầu với 20 điểm")
            self.assertEqual(a["generation"], 1, f"Agent {aid} không phải Thế hệ 1")
            self.assertEqual(a["warning_level"], 0, f"Agent {aid} có warning_level != 0")
            self.assertEqual(a["status"], "HOAT_DONG", f"Agent {aid} status != HOAT_DONG")
            self.assertEqual(a["total_violations"], 0, f"Agent {aid} violations != 0")

    def test_single_penalty_deduction(self):
        """Xác minh trừ 1 Điểm Công Huân khi vi phạm kỷ luật."""
        res = apply_penalty(
            session_id="sess_test_1",
            symbol="HPG",
            agent_id="huyet_vu",
            violation_type="HALLUCINATION",
            reason="Nhầm lẫn số liệu khấu hao quý 3.",
            points=1,
            db_path=self.test_db_path,
        )
        self.assertEqual(res["agent_id"], "huyet_vu")
        self.assertEqual(res["points_deducted"], 1)
        self.assertEqual(res["remaining_points"], 19)
        self.assertEqual(res["total_violations"], 1)
        self.assertEqual(res["status"], "HOAT_DONG")
        self.assertEqual(res["warning_level"], 0)
        self.assertFalse(res["is_expelled"])

        # Kiểm tra hồ sơ được cập nhật trong DB
        prof = get_agent_profile("huyet_vu", self.test_db_path)
        self.assertIsNotNone(prof)
        self.assertEqual(prof["merit_points"], 19)
        self.assertEqual(prof["total_violations"], 1)
        self.assertEqual(len(prof["penalties"]), 1)
        self.assertEqual(prof["penalties"][0]["violation_type"], "HALLUCINATION")

    def test_warning_milestone_15_points_canh_bao_1(self):
        """Xác minh mốc 15 điểm kích hoạt CẢNH BÁO CẤP 1 (user_notification=True, báo Minh Chủ)."""
        # Trừ 5 điểm (20 -> 15)
        res = None
        for i in range(5):
            res = apply_penalty(
                session_id=f"sess_{i}",
                symbol="HPG",
                agent_id="phong_lang",
                violation_type="BIAS_OVERCONFIDENCE",
                reason=f"Lỗi nhận định lần {i+1}",
                points=1,
                db_path=self.test_db_path,
            )

        self.assertEqual(res["remaining_points"], 15)
        self.assertEqual(res["warning_level"], 1)
        self.assertEqual(res["status"], "CANH_BAO_1")
        self.assertFalse(res["is_expelled"])

        warning = res["warning_event"]
        self.assertIsNotNone(warning)
        self.assertEqual(warning["type"], "CANH_BAO_1")
        self.assertTrue(warning["reported_to_minh_chu"])
        self.assertTrue(warning["user_notification"], "Mốc 15 điểm bắt buộc phải gửi thông báo người dùng")

    def test_warning_milestone_10_points_canh_bao_2(self):
        """Xác minh mốc 10 điểm kích hoạt CẢNH BÁO CẤP 2 (Minh Chủ khiển trách công khai)."""
        # Trừ 10 điểm (20 -> 10)
        res = None
        for i in range(10):
            res = apply_penalty(
                session_id=f"sess_{i}",
                symbol="HPG",
                agent_id="tham_muu",
                violation_type="LOGIC_CONTRADICTION",
                reason=f"Mâu thuẫn logic lần {i+1}",
                points=1,
                db_path=self.test_db_path,
            )

        self.assertEqual(res["remaining_points"], 10)
        self.assertEqual(res["warning_level"], 2)
        self.assertEqual(res["status"], "CANH_BAO_2")
        self.assertFalse(res["is_expelled"])

        warning = res["warning_event"]
        self.assertIsNotNone(warning)
        self.assertEqual(warning["type"], "CANH_BAO_2")
        self.assertTrue(warning["reported_to_minh_chu"])
        self.assertFalse(warning["user_notification"])

    def test_warning_milestone_5_points_canh_bao_3(self):
        """Xác minh mốc 5 điểm kích hoạt CẢNH BÁO CẤP 3 (Giám sát đặc biệt, báo người dùng)."""
        # Trừ 15 điểm (20 -> 5)
        res = None
        for i in range(15):
            res = apply_penalty(
                session_id=f"sess_{i}",
                symbol="HPG",
                agent_id="cam_y_ve",
                violation_type="RULE_VIOLATION",
                reason=f"Vi phạm quy tắc lần {i+1}",
                points=1,
                db_path=self.test_db_path,
            )

        self.assertEqual(res["remaining_points"], 5)
        self.assertEqual(res["warning_level"], 3)
        self.assertEqual(res["status"], "CANH_BAO_3")
        self.assertFalse(res["is_expelled"])

        warning = res["warning_event"]
        self.assertIsNotNone(warning)
        self.assertEqual(warning["type"], "CANH_BAO_3")
        self.assertTrue(warning["reported_to_minh_chu"])
        self.assertTrue(warning["user_notification"], "Mốc 5 điểm bắt buộc phải gửi thông báo người dùng")

    def test_expulsion_milestone_0_points_and_respawn(self):
        """
        Xác minh mốc 0 điểm:
        - is_expelled == True
        - Ghi án tích PHE_TRUAT vào SQLite
        - Generation tăng lên Gen 2 (current_gen + 1)
        - Điểm công huân reset về đúng 20 cho Agent thế hệ mới.
        """
        # Trừ toàn bộ 20 điểm
        res = apply_penalty(
            session_id="sess_expel",
            symbol="HPG",
            agent_id="huyet_vu",
            violation_type="HALLUCINATION",
            reason="Gian lận số liệu tài chính đặc biệt nghiêm trọng.",
            points=20,
            db_path=self.test_db_path,
        )

        self.assertTrue(res["is_expelled"], "Agent phải bị phế truất khi hết điểm")
        self.assertEqual(res["generation"], 2, "Agent thế hệ mới phải là Đời 2")
        self.assertEqual(res["remaining_points"], 20, "Agent đời mới phải được cấp lại đúng 20 điểm")
        self.assertEqual(res["status"], "HOAT_DONG")
        self.assertEqual(res["warning_level"], 0)

        warning = res["warning_event"]
        self.assertEqual(warning["type"], "PHE_TRUAT")
        self.assertEqual(warning["old_generation"], 1)
        self.assertEqual(warning["new_generation"], 2)

        # Kiểm tra án tích phế truất được lưu trong DB
        penalties = get_recent_penalties(10, self.test_db_path)
        types = [p["violation_type"] for p in penalties]
        self.assertIn("PHE_TRUAT", types)

    def test_consecutive_expulsions_increment_generation(self):
        """Xác minh việc phế truất liên tiếp tăng thế hệ từ Gen 1 -> Gen 2 -> Gen 3."""
        # Phế truất Gen 1 -> Gen 2
        res1 = apply_penalty("s1", "HPG", "minh_chu", "RULE_VIOLATION", "Sai sót", 20, self.test_db_path)
        self.assertEqual(res1["generation"], 2)
        self.assertEqual(res1["remaining_points"], 20)

        # Phế truất Gen 2 -> Gen 3
        res2 = apply_penalty("s2", "HPG", "minh_chu", "RULE_VIOLATION", "Sai sót tiếp", 20, self.test_db_path)
        self.assertEqual(res2["generation"], 3)
        self.assertEqual(res2["remaining_points"], 20)

    def test_reset_agents_merit_restores_all_to_twenty(self):
        """Xác minh hàm reset_agents_merit khôi phục toàn bộ 5 Agent về 20 điểm và Gen 1."""
        # Trừ điểm một vài agent
        apply_penalty("s1", "HPG", "huyet_vu", "HALLUCINATION", "Lỗi", 7, self.test_db_path)
        apply_penalty("s2", "HPG", "phong_lang", "RULE_VIOLATION", "Lỗi", 20, self.test_db_path)

        # Gọi reset
        reset_agents_merit(self.test_db_path)

        agents = get_all_agents(self.test_db_path)
        self.assertEqual(len(agents), 5)
        for a in agents:
            self.assertEqual(a["merit_points"], 20)
            self.assertEqual(a["generation"], 1)
            self.assertEqual(a["warning_level"], 0)
            self.assertEqual(a["status"], "HOAT_DONG")
            self.assertEqual(a["total_violations"], 0)

    def test_invalid_agent_id_raises_value_error(self):
        """Xác minh gọi apply_penalty với agent_id không tồn tại sẽ raise ValueError."""
        with self.assertRaises(ValueError):
            apply_penalty("s1", "HPG", "agent_khong_ton_tai", "HALLUCINATION", "Lỗi", 1, self.test_db_path)

    def test_sqlite_audit_log_persistence_and_queries(self):
        """Xác minh lưu vết toàn vẹn phiên họp quân cơ (save_council_session & get_council_history)."""
        session_data = {
            "session_id": "council_HPG_test_session_001",
            "symbol": "HPG",
            "target_date": "2026-11-10",
            "verdict": "MUA_THAM_DO",
            "executive_summary": {
                "action_line": "MUA THĂM DÒ 15%",
                "defense_stops_line": "Price-Stop 26.6",
                "directive_line": "Quân lệnh Minh Chủ",
                "summary_lines": ["MUA THĂM DÒ 15%", "Price-Stop 26.6", "Quân lệnh Minh Chủ"],
            },
            "radar_score_card": {
                "co_ban": 85,
                "ky_thuat": 80,
                "dong_tien": 75,
                "quan_tri_rui_ro": 70,
                "xac_suat_thanh_cong": 78,
                "overall_score": 78,
            },
            "trade_plan": {
                "entry_zone": [28.0, 28.3],
                "stop_loss": 26.6,
                "target_1": 30.5,
                "target_2": 32.5,
                "max_nav_pct": 20.0,
            },
            "debate_transcript": [
                {"round": 1, "speaker": "Minh Chủ Võ Lâm", "agent_id": "minh_chu", "content": "Khai mạc"}
            ],
            "penalties_issued": [],
        }

        # Lưu session
        saved_id = save_council_session(session_data, self.test_db_path)
        self.assertEqual(saved_id, "council_HPG_test_session_001")

        # Truy vấn lại lịch sử
        history = get_council_history("HPG", limit=5, db_path=self.test_db_path)
        self.assertEqual(len(history), 1)
        sess = history[0]
        self.assertEqual(sess["session_id"], "council_HPG_test_session_001")
        self.assertEqual(sess["symbol"], "HPG")
        self.assertEqual(sess["verdict"], "MUA_THAM_DO")
        self.assertEqual(sess["radar_score_card"]["co_ban"], 85)
        self.assertEqual(len(sess["executive_summary"]["summary_lines"]), 3)
        self.assertEqual(len(sess["debate_transcript"]), 1)


# ==============================================================================
# SUITE 3: MULTI-AGENT DEBATE WORKFLOW
# ==============================================================================
class TestMultiAgentDebateWorkflow(unittest.TestCase):
    """Kiểm thử quy trình tranh biện 5 giai đoạn bất đồng bộ và DeterministicCouncilEngine."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="council_debate_test_")
        self.test_db_path = Path(self.test_dir) / "test_debate.db"
        init_audit_db(self.test_db_path)

    def tearDown(self):
        try:
            shutil.rmtree(self.test_dir, ignore_errors=True)
        except Exception:
            pass

    def test_deterministic_council_engine_direct(self):
        """Xác minh DeterministicCouncilEngine sinh đầy đủ 6 transcript, 5 persona, 3 executive lines và 5 radar dimensions."""
        mock_quant_profile = {
            "close": 28.2,
            "trend": {"stage": 2, "stage_name": "Pha 2 Tăng giá bền vững", "label": "Tăng giá"},
            "volatility": {"atr14": 0.65},
            "baseline_plan": {
                "entry_zone": [28.0, 28.4],
                "entry_low": 28.0,
                "entry_high": 28.4,
                "stop_loss": 26.6,
                "target_1": 30.5,
                "target_2": 32.5,
                "rr_ratio": 2.3,
                "max_position_pct": 20.0,
            },
            "tactical_6step": {
                "step4_atc": {"atc_verdict": "Khớp chủ động nâng giá", "clv": 0.85},
            },
            "exit_stops": {
                "price_stop": {"price": 26.6, "distance_pct": 5.7},
                "thesis_stop": {"condition": "Gãy MA50 kèm volume lớn hơn 1.5x."},
                "time_stop": {"condition": "T+10 phiên nếu không vượt cản."},
            },
        }
        mock_forecast_audit = {
            "symbol": "HPG",
            "historical_accuracy": 78.5,
            "total_audits": 12,
            "summary": "78.5% dự báo quá khứ khớp hướng và biên độ.",
        }
        mock_financials = {
            "overview": {"pe": 12.5, "pb": 1.6, "roe": 15.2},
            "cash_flow": {"cfo": 4200.0, "net_income": 3800.0},
        }

        result = DeterministicCouncilEngine.run_debate(
            symbol="HPG",
            quant_profile=mock_quant_profile,
            forecast_audit_res=mock_forecast_audit,
            financials=mock_financials,
            risk_profile="Trung bình",
            horizon="Swing (1–3 tháng)",
            cost_basis=28.0,
            position_pct=15.0,
        )

        # 1. Kiểm tra symbol và session_id
        self.assertEqual(result["symbol"], "HPG")
        self.assertTrue(result["session_id"].startswith("council_HPG_"))

        # 2. Kiểm tra debate_transcript có đúng 6 entries và 5 distinct personas
        transcript = result["debate_transcript"]
        self.assertEqual(len(transcript), 6, "Transcript phải gồm chính xác 6 lượt phát biểu")
        personas_in_transcript = {t["agent_id"] for t in transcript}
        expected_personas = {"minh_chu", "huyet_vu", "phong_lang", "tham_muu", "cam_y_ve"}
        self.assertEqual(personas_in_transcript, expected_personas, "Transcript phải bao quát đủ 5 Persona")

        # Xác minh thứ tự các vòng
        self.assertEqual(transcript[0]["round"], 1)
        self.assertEqual(transcript[0]["agent_id"], "minh_chu")
        self.assertEqual(transcript[1]["round"], 2)
        self.assertEqual(transcript[1]["agent_id"], "huyet_vu")
        self.assertEqual(transcript[2]["round"], 2)
        self.assertEqual(transcript[2]["agent_id"], "phong_lang")
        self.assertEqual(transcript[3]["round"], 3)
        self.assertEqual(transcript[3]["agent_id"], "tham_muu")
        self.assertEqual(transcript[4]["round"], 4)
        self.assertEqual(transcript[4]["agent_id"], "cam_y_ve")
        self.assertEqual(transcript[5]["round"], 5)
        self.assertEqual(transcript[5]["agent_id"], "minh_chu")

        # 3. Kiểm tra Executive Summary có đúng 3 dòng
        exec_sum = result["executive_summary"]
        self.assertTrue("action_line" in exec_sum)
        self.assertTrue("defense_stops_line" in exec_sum)
        self.assertTrue("directive_line" in exec_sum)
        self.assertEqual(len(exec_sum["summary_lines"]), 3)

        # 4. Kiểm tra Radar Score Card có đủ 5 chiều và tổng thể
        radar = result["radar_score_card"]
        for dim in ["co_ban", "ky_thuat", "dong_tien", "quan_tri_rui_ro", "xac_suat_thanh_cong", "overall_score"]:
            self.assertIn(dim, radar)
            self.assertTrue(0 <= radar[dim] <= 100)

        # 5. Kiểm tra trade_plan nhất quán
        tp = result["trade_plan"]
        self.assertLess(tp["stop_loss"], tp["entry_zone"][0])
        self.assertLessEqual(tp["entry_zone"][0], tp["entry_zone"][1])
        self.assertLessEqual(tp["max_nav_pct"], 25.0)

    def test_run_council_debate_deterministic_mode_symbols(self):
        """Xác minh run_council_debate ở chế độ use_llm=False trên các mã HPG, VHM và fallback ticker SSI."""
        test_cases = [
            ("HPG", make_sample_df(start=28.0, seed=1)),
            ("VHM", make_sample_df(start=45.0, seed=2)),
            ("SSI", make_sample_df(start=32.0, seed=3)),
        ]
        for sym, mock_df in test_cases:
            res = asyncio.run(
                run_council_debate(
                    symbol=sym,
                    df=mock_df,
                    use_llm=False,
                    db_path=self.test_db_path,
                )
            )
            self.assertEqual(res["symbol"], sym)
            self.assertEqual(len(res["debate_transcript"]), 6)
            self.assertEqual(len(res["executive_summary"]["summary_lines"]), 3)
            self.assertEqual(len(res["merit_scores"]), 5)
            self.assertIn(res["verdict"], ["MUA_MANH", "MUA_THAM_DO", "NAM_GIU", "QUAN_SAT", "HA_TY_TRONG", "BAN_DUNG_NGOAI"])

    def test_run_council_debate_missing_data_raises_value_error(self):
        """Xác minh truyền DataFrame rỗng hoặc mã rác không tìm thấy dữ liệu sẽ ném ValueError."""
        empty_df = pd.DataFrame()
        with patch("backend.data_fetcher.get_historical_data", return_value=empty_df):
            with self.assertRaises(ValueError):
                asyncio.run(
                    run_council_debate(
                        symbol="TICKER_RAC_KHONG_TON_TAI",
                        use_llm=False,
                        db_path=self.test_db_path,
                    )
                )


# ==============================================================================
# SUITE 4: MOCK LLM PIPELINE & FAULT TOLERANCE
# ==============================================================================
class TestMockLLMPipeline(unittest.TestCase):
    """Kiểm thử tích hợp Gemini LLM Structured Output qua cơ chế Mock và kiểm tra Fallback tự động."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="council_llm_test_")
        self.test_db_path = Path(self.test_dir) / "test_llm.db"
        init_audit_db(self.test_db_path)

        # Dữ liệu quant giả định chuẩn
        self.mock_quant_profile = {
            "close": 28.5,
            "trend": {"stage": 2, "stage_name": "Pha 2 Tăng giá"},
            "volatility": {"atr14": 0.6},
            "baseline_plan": {
                "entry_zone": [28.0, 28.5],
                "entry_low": 28.0,
                "entry_high": 28.5,
                "stop_loss": 26.8,
                "target_1": 31.0,
                "target_2": 33.0,
                "rr_ratio": 2.5,
                "max_position_pct": 20.0,
            },
            "tactical_6step": {},
            "exit_stops": {
                "price_stop": {"price": 26.8, "distance_pct": 6.0},
                "thesis_stop": {"condition": "Gãy MA50 kèm vol lớn."},
                "time_stop": {"condition": "T+10 phiên nếu không bứt phá."},
            },
        }
        self.mock_forecast_audit = {"historical_accuracy": 82.0}
        self.mock_financials = {"overview": {"pe": 12.0}}

    def tearDown(self):
        try:
            shutil.rmtree(self.test_dir, ignore_errors=True)
        except Exception:
            pass

    def test_mock_llm_successful_5_stage_debate(self):
        """
        Mock toàn bộ 5 stage Gemini API phản hồi JSON hợp lệ:
        - Xác minh engine='gemini'
        - Xác minh transcript 6 lượt
        - Xác minh xử phạt vi phạm do Cẩm Y Vệ phát hiện được thực thi và trừ Điểm Công Huân.
        """
        # Chuẩn bị dữ liệu mẫu cho từng stage
        s1 = MinhChuDirective(
            general_stance="Đại cục VN-Index thuận lợi cho vị thế mua thăm dò.",
            focus_areas=["Soi BCTC", "Soi Lệnh ATC", "Chốt Chặn"],
            directive_for_huyet_vu="Mổ xẻ BCTC HPG",
            directive_for_phong_lang="Canh bẫy T+2.5",
            directive_for_tham_muu="Tìm kẽ hở bác bỏ",
            directive_for_cam_y_ve="Kiểm toán lịch sử",
            martial_speech="Minh Chủ Võ Lâm khai mạc!",
        )
        s2a = HuyetVuLauReport(
            forensic_score=88,
            cfo_vs_ni_analysis="CFO dương 5000 tỷ, chất lượng lợi nhuận xuất sắc.",
            is_paper_profit=False,
            balance_sheet_risks=[],
            rights_event_evaluation="Né trước chốt – Bắt sau chia: An toàn.",
            fundamental_verdict="ƯU_TÚ",
            martial_speech="Huyết Vũ Lâu xác nhận nội lực thâm hậu!",
        )
        s2b = PhongLangDoiReport(
            tactical_score=85,
            wyckoff_phase="Pha C Test thành công",
            vsa_signals=["No Supply"],
            t25_trap_warning="Hàng T+2.5 đã được hấp thụ.",
            atc_clv_analysis="ATC đóng cửa ở mức cao nhất, CLV=0.92.",
            proposed_entry_low=28.0,
            proposed_entry_high=28.4,
            entry_trigger="Khớp lệnh vượt 28.2 sau 14h00.",
            martial_speech="Phong Lang Đội sẵn sàng xung trận!",
        )
        s3 = ThamMuuCacReport(
            rejection_recommended=False,
            rejection_reasons=["Rủi ro giá hàng hóa thế giới hạ nhiệt"],
            pre_mortem_scenario="Nếu thị trường xuất hiện tin tức chiến tranh.",
            price_stop=26.8,
            thesis_stop="Gãy hỗ trợ MA50",
            time_stop="T+10 phiên",
            max_position_pct=20.0,
            martial_speech="Tham Mưu Các cảnh báo rủi ro sống còn!",
        )
        # Cẩm Y Vệ phát hiện 1 lỗi thiên kiến của Phong Lang Đội để trừ điểm
        s4 = CamYVeReport(
            historical_accuracy_pct=82.0,
            last_forecast_review="Dự báo trước chuẩn xác.",
            detected_violations=[
                AgentViolationRecord(
                    agent_id="phong_lang",
                    agent_name="Phong Lang Đội",
                    violation_type="BIAS_OVERCONFIDENCE",
                    points_deducted=1,
                    reason="Nhận định chủ quan về lực kéo phiên ATC.",
                )
            ],
            audit_verdict="Phát hiện 1 lỗi thiên kiến, thi hành trừ 1 Điểm Công Huân.",
            martial_speech="Cẩm Y Vệ thực thi kỷ luật thiết huyết!",
        )
        s5 = InvestmentResolution(
            action_line="MUA THĂM DÒ: Giải ngân 15% tại vùng 28.0 - 28.4.",
            defense_stops_line="BỘ 3 CHỐT CHẶN: Price-Stop 26.8, Thesis-Stop gãy MA50, Time-Stop T+10.",
            directive_line="QUÂN LỆNH MINH CHỦ: Toàn quân chấp hành tỷ trọng <= 20% NAV.",
            summary_lines=[
                "MUA THĂM DÒ: Giải ngân 15% tại vùng 28.0 - 28.4.",
                "BỘ 3 CHỐT CHẶN: Price-Stop 26.8, Thesis-Stop gãy MA50, Time-Stop T+10.",
                "QUÂN LỆNH MINH CHỦ: Toàn quân chấp hành tỷ trọng <= 20% NAV.",
            ],
            verdict="MUA_THAM_DO",
            radar_scores=RadarScoreCard(
                co_ban=88,
                ky_thuat=85,
                dong_tien=80,
                quan_tri_rui_ro=75,
                xac_suat_thanh_cong=80,
                overall_score=82,
            ),
            entry_low=28.0,
            entry_high=28.4,
            stop_loss=26.8,
            target_1=31.0,
            target_2=33.0,
            rr_ratio=2.5,
            max_nav_pct=20.0,
            critique_and_modifications="Chấp thuận phán quyết, phê chuẩn án phạt Phong Lang Đội.",
            martial_speech="Minh Chủ Võ Lâm ban hành Nghị quyết!",
        )

        def mock_generate(prompt="", system=None, json_schema=None, label="", **kwargs):
            if "Stage1" in label:
                return s1.model_dump_json(), "gemini-3.8-flash", None
            elif "Stage2-HuyetVu" in label:
                return s2a.model_dump_json(), "gemini-3.8-flash", None
            elif "Stage2-PhongLang" in label:
                return s2b.model_dump_json(), "gemini-3.8-flash", None
            elif "Stage3" in label:
                return s3.model_dump_json(), "gemini-3.8-flash", None
            elif "Stage4" in label:
                return s4.model_dump_json(), "gemini-3.8-flash", None
            elif "Stage5" in label:
                return s5.model_dump_json(), "gemini-3.8-flash", None
            return "{}", "gemini-3.8-flash", None

        with patch("llm_client.get_api_key", return_value="fake_valid_key"), \
             patch("llm_client.generate", side_effect=mock_generate):

            engine = CouncilEngine(use_llm=True, db_path=self.test_db_path)
            res = asyncio.run(
                engine.run_debate(
                    symbol="HPG",
                    quant_profile=self.mock_quant_profile,
                    forecast_audit_res=self.mock_forecast_audit,
                    financials=self.mock_financials,
                )
            )

            self.assertEqual(res["engine"], "gemini")
            self.assertEqual(len(res["debate_transcript"]), 6)
            self.assertEqual(len(res["penalties_issued"]), 1)
            self.assertEqual(res["penalties_issued"][0]["agent_id"], "phong_lang")

            # Xác minh điểm của Phong Lang Đội đã bị trừ 1 điểm trong SQLite
            prof = get_agent_profile("phong_lang", self.test_db_path)
            self.assertEqual(prof["merit_points"], 19)

    def test_mock_llm_api_error_fallback_to_deterministic(self):
        """Xác minh khi Gemini API báo lỗi (Rate Limit 429 hoặc rớt mạng), hệ thống tự động Fallback sang DeterministicCouncilEngine mà không gây lỗi."""
        with patch("llm_client.get_api_key", return_value="fake_key"), \
             patch("llm_client.generate", side_effect=RuntimeError("Google Gemini API Rate Limit (429)")):

            engine = CouncilEngine(use_llm=True, db_path=self.test_db_path)
            res = asyncio.run(
                engine.run_debate(
                    symbol="HPG",
                    quant_profile=self.mock_quant_profile,
                    forecast_audit_res=self.mock_forecast_audit,
                    financials=self.mock_financials,
                )
            )

            # Phải hoàn tất suôn sẻ nhờ fallback
            self.assertEqual(res["symbol"], "HPG")
            self.assertEqual(len(res["debate_transcript"]), 6)
            self.assertEqual(len(res["executive_summary"]["summary_lines"]), 3)

            # Lịch sử phiên họp vẫn được lưu trữ bền vững
            hist = get_council_history("HPG", db_path=self.test_db_path)
            self.assertEqual(len(hist), 1)

    def test_mock_llm_missing_api_key_deterministic_fallback(self):
        """Xác minh khi không có API key, CouncilEngine lập tức chọn DeterministicCouncilEngine."""
        with patch("llm_client.get_api_key", return_value=None):
            engine = CouncilEngine(use_llm=True, db_path=self.test_db_path)
            res = asyncio.run(
                engine.run_debate(
                    symbol="HPG",
                    quant_profile=self.mock_quant_profile,
                    forecast_audit_res=self.mock_forecast_audit,
                    financials=self.mock_financials,
                )
            )
            self.assertEqual(res["symbol"], "HPG")
            self.assertEqual(len(res["debate_transcript"]), 6)


# ==============================================================================
# SUITE 5: FASTAPI COUNCIL ENDPOINTS
# ==============================================================================
class TestFastAPICouncilEndpoints(unittest.TestCase):
    """Kiểm thử các REST API Endpoints của Hội Đồng Quân Cơ thông qua FastAPI TestClient."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_get_council_agents_endpoint(self):
        """Xác minh GET /api/council/agents trả về HTTP 200, danh sách 5 Agent và nhật ký án phạt."""
        resp = self.client.get("/api/council/agents")
        self.assertEqual(resp.status_code, 200)

        data = resp.json()
        self.assertIn("agents", data)
        self.assertIn("recent_penalties", data)

        agents = data["agents"]
        self.assertEqual(len(agents), 5)
        for a in agents:
            self.assertIn("id", a)
            self.assertIn("name", a)
            self.assertIn("role", a)
            self.assertIn("score", a)
            self.assertIn("status", a)
            self.assertTrue(0 <= a["score"] <= 20)

    def test_post_council_reset_agents_endpoint(self):
        """Xác minh POST /api/council/reset-agents yêu cầu X-Cron-Secret, trả về HTTP 200 và khôi phục 20 điểm cho 5 Agent."""
        with patch.dict(os.environ, {"CRON_SECRET": "test-secret"}):
            self.assertEqual(self.client.post("/api/council/reset-agents").status_code, 401)
            resp = self.client.post("/api/council/reset-agents", headers={"X-Cron-Secret": "test-secret"})
        self.assertEqual(resp.status_code, 200)

        data = resp.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(len(data["agents"]), 5)
        for a in data["agents"]:
            self.assertEqual(a["merit_points"], 20)

    def test_get_council_history_endpoint(self):
        """Xác minh GET /api/council/history/{symbol} hỗ trợ query limit và trả về đúng định dạng."""
        # Query lịch sử của HPG
        resp = self.client.get("/api/council/history/HPG?limit=2")
        self.assertEqual(resp.status_code, 200)

        data = resp.json()
        self.assertEqual(data["symbol"], "HPG")
        self.assertIsInstance(data["sessions"], list)
        self.assertLessEqual(len(data["sessions"]), 2)

        # Kiểm tra mã cổ phiếu rỗng hoặc không hợp lệ -> 400
        resp_invalid = self.client.get("/api/council/history/%20")
        self.assertEqual(resp_invalid.status_code, 400)

    def test_post_council_debate_endpoint_valid_and_caching(self):
        """
        Kiểm thử POST /api/council/debate:
        - Mock run_council_debate trả về kết quả chuẩn
        - Kiểm tra status code 200 và các trường bắt buộc
        - Kiểm tra cơ chế Cache (lần gọi thứ 2 cùng tham số lấy từ Cache, không gọi lại engine)
        - Kiểm tra force_refresh=True bỏ qua Cache.
        """
        mock_result = {
            "symbol": "HPG",
            "session_id": "council_HPG_test_cache_123",
            "created_at": "2026-11-10T00:00:00Z",
            "executive_summary": {
                "action_line": "MUA THĂM DÒ 15%",
                "defense_stops_line": "Price-Stop 26.6",
                "directive_line": "Quân lệnh Minh Chủ",
                "summary_lines": ["D1", "D2", "D3"],
            },
            "verdict": "MUA_THAM_DO",
            "radar_score_card": {
                "co_ban": 85,
                "ky_thuat": 80,
                "dong_tien": 75,
                "quan_tri_rui_ro": 70,
                "xac_suat_thanh_cong": 78,
                "overall_score": 78,
            },
            "trade_plan": {"entry_zone": [28.0, 28.3]},
            "debate_transcript": [
                {"round": 1, "speaker": "Minh Chủ Võ Lâm", "agent_id": "minh_chu", "content": "Khai mạc"}
            ],
            "merit_scores": [],
        }

        with patch("backend.api.run_council_debate", new_callable=AsyncMock) as mock_engine:
            mock_engine.return_value = mock_result

            # Lần gọi 1: Cache miss, gọi mock_engine
            payload = {"symbol": "TEST_CACHE", "force_refresh": True}
            resp1 = self.client.post("/api/council/debate", json=payload)
            self.assertEqual(resp1.status_code, 200)
            data1 = resp1.json()
            self.assertEqual(data1["session_id"], "council_HPG_test_cache_123")
            self.assertEqual(mock_engine.call_count, 1)

            # Lần gọi 2: Cùng payload không force_refresh -> Cache hit, không tăng call_count
            payload_cached = {"symbol": "TEST_CACHE", "force_refresh": False}
            resp2 = self.client.post("/api/council/debate", json=payload_cached)
            self.assertEqual(resp2.status_code, 200)
            self.assertEqual(mock_engine.call_count, 1, "Lần gọi 2 phải lấy từ Cache!")

            # Lần gọi 3: Bật force_refresh=True -> Bỏ qua Cache, gọi mock_engine lần thứ 2
            payload_refresh = {"symbol": "TEST_CACHE", "force_refresh": True}
            resp3 = self.client.post("/api/council/debate", json=payload_refresh)
            self.assertEqual(resp3.status_code, 200)
            self.assertEqual(mock_engine.call_count, 2, "force_refresh=True phải kích hoạt gọi lại engine!")

    def test_post_council_debate_empty_symbol_400(self):
        """Xác minh gửi symbol rỗng ném HTTP 400 Bad Request."""
        resp = self.client.post("/api/council/debate", json={"symbol": "   "})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Mã cổ phiếu không được để trống", resp.json()["detail"])

    def test_post_council_debate_unknown_symbol_404(self):
        """Xác minh mã không tìm thấy dữ liệu (ValueError) trả về HTTP 404 Not Found."""
        with patch("backend.api.run_council_debate", new_callable=AsyncMock) as mock_engine:
            mock_engine.side_effect = ValueError("Không tìm thấy dữ liệu giá lịch sử cho mã cổ phiếu 'UNKNOWN'")
            resp = self.client.post("/api/council/debate", json={"symbol": "UNKNOWN", "force_refresh": True})
            self.assertEqual(resp.status_code, 404)
            self.assertIn("Không tìm thấy dữ liệu", resp.json()["detail"])

    def test_post_council_debate_internal_error_500(self):
        """Xác minh lỗi hệ thống không lường trước trả về HTTP 500 Internal Server Error."""
        with patch("backend.api.run_council_debate", new_callable=AsyncMock) as mock_engine:
            mock_engine.side_effect = Exception("Database crash failure")
            resp = self.client.post("/api/council/debate", json={"symbol": "CRASH", "force_refresh": True})
            self.assertEqual(resp.status_code, 500)
            self.assertIn("Lỗi thực thi Hội Đồng Quân Cơ", resp.json()["detail"])


# ==============================================================================
# MAIN TEST RUNNER
# ==============================================================================
if __name__ == "__main__":
    unittest.main()
