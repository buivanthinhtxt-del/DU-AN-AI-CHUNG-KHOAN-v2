"""
Backend Multi-Agent Council & Audit Store Package (AI Workstation V5.0).

Bao gồm:
- 5 Persona kiếm hiệp / quân cơ (Minh Chủ Võ Lâm, Huyết Vũ Lâu, Phong Lang Đội, Tham Mưu Các, Cẩm Y Vệ).
- Quy chế Điểm Công Huân & SQLite Audit Store bền vững tại `backend/data/council_audit.db`.
- Động cơ Tranh biện & Phản biện 5 Giai đoạn (Asyncio Debate & Critique Loop).
- Động cơ Dự phòng Xác định (Deterministic Council Engine) phục vụ offline & kiểm thử.
"""

from backend.agents.personas import (
    AGENT_DEFINITIONS,
    MinhChuDirective,
    HuyetVuLauReport,
    PhongLangDoiReport,
    ThamMuuCacReport,
    AgentViolationRecord,
    CamYVeReport,
    RadarScoreCard,
    ExecutiveSummary,
    InvestmentResolution,
)
from backend.agents.audit_store import (
    AUDIT_DB_PATH,
    init_audit_db,
    get_all_agents,
    get_agent_profile,
    apply_penalty,
    save_council_session,
    get_council_history,
    get_recent_penalties,
    reset_agents_merit,
)
from backend.agents.council_engine import (
    CouncilEngine,
    DeterministicCouncilEngine,
    run_council_debate,
)

__all__ = [
    "AGENT_DEFINITIONS",
    "MinhChuDirective",
    "HuyetVuLauReport",
    "PhongLangDoiReport",
    "ThamMuuCacReport",
    "AgentViolationRecord",
    "CamYVeReport",
    "RadarScoreCard",
    "ExecutiveSummary",
    "InvestmentResolution",
    "AUDIT_DB_PATH",
    "init_audit_db",
    "get_all_agents",
    "get_agent_profile",
    "apply_penalty",
    "save_council_session",
    "get_council_history",
    "get_recent_penalties",
    "reset_agents_merit",
    "CouncilEngine",
    "DeterministicCouncilEngine",
    "run_council_debate",
]
