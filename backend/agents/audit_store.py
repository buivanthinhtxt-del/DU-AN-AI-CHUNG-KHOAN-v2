"""
Hệ thống Quản lý Kỷ luật & Lưu trữ Bền vững Audit Log (Điểm Công Huân & Council Audit Store).

Lưu trữ bền vững tại SQLite: `backend/data/council_audit.db`
Các quy chế chính:
- Mỗi Agent bắt đầu với quỹ 20 Điểm Công Huân (Thế hệ 1).
- Mỗi lần phạm lỗi, báo cáo sai, bịa đặt thông tin (hallucination): trừ 1 Điểm Công Huân (-1).
- Các mốc kỷ luật và cảnh báo:
  * Trừ 5 điểm (còn 15 điểm): Cảnh báo Cấp 1 (WARNING_1). Cẩm Y Vệ lập tức tấu trình Minh Chủ Võ Lâm và phát thông báo cảnh báo đến người dùng.
  * Trừ 10 điểm (còn 10 điểm): Cảnh báo Cấp 2 (WARNING_2). Minh Chủ khiển trách công khai trong trướng quân cơ.
  * Trừ 15 điểm (còn 5 điểm): Cảnh báo Cấp 3 (WARNING_3). Đưa vào diện giám sát đặc biệt.
  * Trừ 20 điểm (về 0 điểm): Phế truất (EXPELLED). Tước quyền tham gia quân cơ các, tạo Agent kế nhiệm đời mới (Generation N+1) với 20 Điểm Công Huân mới.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("audit_store")

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
AUDIT_DB_PATH = DATA_DIR / "council_audit.db"

_db_lock = threading.Lock()

INITIAL_AGENTS = [
    {
        "agent_id": "minh_chu",
        "name": "Minh Chủ Võ Lâm",
        "role": "Supervisor / CIO",
    },
    {
        "agent_id": "huyet_vu",
        "name": "Huyết Vũ Lâu",
        "role": "Forensic Accounting & Financial Auditor",
    },
    {
        "agent_id": "phong_lang",
        "name": "Phong Lang Đội",
        "role": "Tactician & Orderflow Specialist",
    },
    {
        "agent_id": "tham_muu",
        "name": "Tham Mưu Các",
        "role": "Contrarian Risk Controller / Devil's Advocate",
    },
    {
        "agent_id": "cam_y_ve",
        "name": "Cẩm Y Vệ",
        "role": "Audit & Continuous Improvement Officer",
    },
]


def _get_connection(db_path: Optional[str | Path] = None) -> sqlite3.Connection:
    target_path = Path(db_path) if db_path else AUDIT_DB_PATH
    target_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target_path), timeout=30.0)
    conn.row_factory = sqlite3.Row
    return conn


def init_audit_db(db_path: Optional[str | Path] = None) -> None:
    """Khởi tạo cơ sở dữ liệu SQLite council_audit.db nếu chưa có và gieo mầm 5 Agent ban đầu."""
    with _db_lock:
        conn = _get_connection(db_path)
        try:
            cursor = conn.cursor()
            # 1. Bảng hồ sơ Agent và Điểm Công Huân
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_merit_profiles (
                    agent_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    role TEXT NOT NULL,
                    generation INTEGER DEFAULT 1,
                    merit_points INTEGER DEFAULT 20,
                    warning_level INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'HOAT_DONG',
                    total_violations INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )

            # 2. Bảng Biên Bản Cuộc Họp Quân Cơ (Council Sessions)
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS council_sessions (
                    session_id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    target_date TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    verdict TEXT NOT NULL,
                    executive_summary_json TEXT NOT NULL,
                    radar_scores_json TEXT NOT NULL,
                    trade_plan_json TEXT NOT NULL,
                    full_debate_json TEXT NOT NULL,
                    penalties_issued_json TEXT NOT NULL
                );
                """
            )

            # 3. Bảng Nhật ký xử phạt vi phạm (Penalty Audit Log)
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_penalties (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    agent_name TEXT NOT NULL,
                    points_deducted INTEGER NOT NULL DEFAULT 1,
                    violation_type TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )

            # Gieo mầm 5 Agent ban đầu nếu bảng rỗng
            for ag in INITIAL_AGENTS:
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO agent_merit_profiles
                        (agent_id, name, role, generation, merit_points, warning_level, status, total_violations)
                    VALUES (?, ?, ?, 1, 20, 0, 'HOAT_DONG', 0);
                    """,
                    (ag["agent_id"], ag["name"], ag["role"]),
                )
            conn.commit()
        finally:
            conn.close()


def get_all_agents(db_path: Optional[str | Path] = None) -> List[Dict[str, Any]]:
    """Lấy danh sách toàn bộ 5 Agent kèm Điểm Công Huân, cấp cảnh báo và lịch sử án phạt gần nhất."""
    init_audit_db(db_path)
    with _db_lock:
        conn = _get_connection(db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT agent_id, name, role, generation, merit_points, warning_level, status, total_violations, created_at, updated_at
                FROM agent_merit_profiles
                ORDER BY
                    CASE agent_id
                        WHEN 'minh_chu' THEN 1
                        WHEN 'huyet_vu' THEN 2
                        WHEN 'phong_lang' THEN 3
                        WHEN 'tham_muu' THEN 4
                        WHEN 'cam_y_ve' THEN 5
                        ELSE 6
                    END;
                """
            )
            rows = cursor.fetchall()
            results = []
            for r in rows:
                agent_id = r["agent_id"]
                # Lấy 5 án phạt gần nhất của agent này
                cursor.execute(
                    """
                    SELECT id, session_id, symbol, points_deducted, violation_type, reason, created_at
                    FROM agent_penalties
                    WHERE agent_id = ?
                    ORDER BY id DESC LIMIT 5;
                    """,
                    (agent_id,),
                )
                penalties = [dict(p) for p in cursor.fetchall()]
                results.append(
                    {
                        "id": r["agent_id"],
                        "agent_id": r["agent_id"],
                        "name": r["name"],
                        "role": r["role"],
                        "generation": r["generation"],
                        "score": r["merit_points"],
                        "merit_points": r["merit_points"],
                        "warning_level": r["warning_level"],
                        "status": r["status"],
                        "total_violations": r["total_violations"],
                        "penalties": penalties,
                        "updated_at": r["updated_at"],
                    }
                )
            return results
        finally:
            conn.close()


def get_agent_profile(agent_id: str, db_path: Optional[str | Path] = None) -> Optional[Dict[str, Any]]:
    """Lấy thông tin hồ sơ của một Agent theo agent_id."""
    init_audit_db(db_path)
    with _db_lock:
        conn = _get_connection(db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT agent_id, name, role, generation, merit_points, warning_level, status, total_violations, created_at, updated_at
                FROM agent_merit_profiles
                WHERE agent_id = ?;
                """,
                (agent_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            cursor.execute(
                """
                SELECT id, session_id, symbol, points_deducted, violation_type, reason, created_at
                FROM agent_penalties
                WHERE agent_id = ?
                ORDER BY id DESC LIMIT 10;
                """,
                (agent_id,),
            )
            penalties = [dict(p) for p in cursor.fetchall()]
            data = dict(row)
            data["penalties"] = penalties
            return data
        finally:
            conn.close()


def apply_penalty(
    session_id: str,
    symbol: str,
    agent_id: str,
    violation_type: str,
    reason: str,
    points: int = 1,
    db_path: Optional[str | Path] = None,
) -> Dict[str, Any]:
    """
    Trừ Điểm Công Huân của Agent và áp dụng các mốc kỷ luật:
    - Trừ 1 điểm mỗi vi phạm.
    - 15 điểm: Cảnh báo Cấp 1 (Cẩm Y Vệ tấu trình Minh Chủ & thông báo người dùng).
    - 10 điểm: Cảnh báo Cấp 2 (Minh Chủ khiển trách).
    - 5 điểm: Cảnh báo Cấp 3 (Giám sát đặc biệt).
    - 0 điểm: Phế truất (Expulsion) và tạo Agent mới thế hệ N+1 với 20 điểm.
    """
    init_audit_db(db_path)
    points_to_deduct = max(1, int(points))
    now_str = datetime.now(timezone.utc).isoformat()

    with _db_lock:
        conn = _get_connection(db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT agent_id, name, role, generation, merit_points, warning_level, status, total_violations
                FROM agent_merit_profiles
                WHERE agent_id = ?;
                """,
                (agent_id,),
            )
            agent = cursor.fetchone()
            if not agent:
                raise ValueError(f"Không tìm thấy Agent với id: '{agent_id}'")

            current_points = int(agent["merit_points"])
            current_violations = int(agent["total_violations"])
            current_gen = int(agent["generation"])
            agent_name = str(agent["name"])

            new_points = max(0, current_points - points_to_deduct)
            new_violations = current_violations + 1

            # Ghi vào nhật ký xử phạt agent_penalties
            cursor.execute(
                """
                INSERT INTO agent_penalties
                    (session_id, symbol, agent_id, agent_name, points_deducted, violation_type, reason, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (session_id, symbol, agent_id, agent_name, points_to_deduct, violation_type, reason, now_str),
            )
            penalty_id = cursor.lastrowid

            warning_event = None
            is_expelled = False
            new_gen = current_gen

            if new_points <= 0:
                # Mốc 0 điểm: Phế truất Agent và khởi tạo thế hệ kế nhiệm N+1
                is_expelled = True
                new_gen = current_gen + 1
                new_points = 20
                new_warning_level = 0
                new_status = "HOAT_DONG"

                # Ghi nhận biến cố phế truất vào bia kỷ luật
                expel_reason = (
                    f"PHẾ TRUẤT: {agent_name} (Đời {current_gen}) đã bị tước bỏ tư cách tham dự Quân Cơ Các "
                    f"do tiêu hao toàn bộ 20 Điểm Công Huân. Đã triệu hồi Tân Binh Đời {new_gen} kế nhiệm với 20 Điểm Công Huân mới!"
                )
                cursor.execute(
                    """
                    INSERT INTO agent_penalties
                        (session_id, symbol, agent_id, agent_name, points_deducted, violation_type, reason, created_at)
                    VALUES (?, ?, ?, ?, 0, 'PHE_TRUAT', ?, ?);
                    """,
                    (session_id, symbol, agent_id, agent_name, expel_reason, now_str),
                )
                warning_event = {
                    "level": 4,
                    "type": "PHE_TRUAT",
                    "status": "EXPELLED_AND_RESPAWNED",
                    "message": expel_reason,
                    "reported_to_minh_chu": True,
                    "user_notification": True,
                    "old_generation": current_gen,
                    "new_generation": new_gen,
                }
            elif new_points <= 5:
                new_warning_level = 3
                new_status = "CANH_BAO_3"
                warning_event = {
                    "level": 3,
                    "type": "CANH_BAO_3",
                    "status": "CANH_BAO_3",
                    "message": (
                        f"CẢNH BÁO CẤP 3 (Cực kỳ nghiêm trọng): {agent_name} chỉ còn {new_points} Điểm Công Huân. "
                        f"Cẩm Y Vệ đưa vào diện giám sát đặc biệt, nếu vi phạm thêm sẽ bị phế truất!"
                    ),
                    "reported_to_minh_chu": True,
                    "user_notification": True,
                }
            elif new_points <= 10:
                new_warning_level = 2
                new_status = "CANH_BAO_2"
                warning_event = {
                    "level": 2,
                    "type": "CANH_BAO_2",
                    "status": "CANH_BAO_2",
                    "message": (
                        f"CẢNH BÁO CẤP 2: {agent_name} còn {new_points} Điểm Công Huân. "
                        f"Minh Chủ Võ Lâm khiển trách công khai trong trướng quân cơ."
                    ),
                    "reported_to_minh_chu": True,
                    "user_notification": False,
                }
            elif new_points <= 15:
                new_warning_level = 1
                new_status = "CANH_BAO_1"
                warning_event = {
                    "level": 1,
                    "type": "CANH_BAO_1",
                    "status": "CANH_BAO_1",
                    "message": (
                        f"CẢNH BÁO CẤP 1: Cẩm Y Vệ lập tức tấu trình Minh Chủ Võ Lâm và gửi thông báo đến người dùng: "
                        f"{agent_name} đã vi phạm, tích lũy {new_violations} lỗi, còn lại {new_points} Điểm Công Huân!"
                    ),
                    "reported_to_minh_chu": True,
                    "user_notification": True,
                }
            else:
                new_warning_level = 0
                new_status = "HOAT_DONG"

            # Cập nhật hồ sơ Agent
            cursor.execute(
                """
                UPDATE agent_merit_profiles
                SET merit_points = ?,
                    generation = ?,
                    warning_level = ?,
                    status = ?,
                    total_violations = ?,
                    updated_at = ?
                WHERE agent_id = ?;
                """,
                (new_points, new_gen, new_warning_level, new_status, new_violations, now_str, agent_id),
            )
            conn.commit()

            return {
                "penalty_id": penalty_id,
                "agent_id": agent_id,
                "agent_name": agent_name,
                "points_deducted": points_to_deduct,
                "remaining_points": new_points,
                "generation": new_gen,
                "warning_level": new_warning_level,
                "status": new_status,
                "total_violations": new_violations,
                "warning_event": warning_event,
                "is_expelled": is_expelled,
            }
        finally:
            conn.close()


def save_council_session(
    session_data: Dict[str, Any],
    db_path: Optional[str | Path] = None,
) -> str:
    """Lưu trữ toàn vẹn Biên Bản Cuộc Họp Quân Cơ vào bảng council_sessions."""
    init_audit_db(db_path)
    session_id = str(session_data.get("session_id") or f"council_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    symbol = str(session_data.get("symbol") or "VNINDEX").upper()
    target_date = session_data.get("target_date")
    created_at = session_data.get("created_at") or datetime.now(timezone.utc).isoformat()
    verdict = str(session_data.get("verdict") or "QUAN_SAT")

    exec_summary = session_data.get("executive_summary") or {}
    radar_scores = session_data.get("radar_score_card") or session_data.get("radar_scores") or {}
    trade_plan = session_data.get("trade_plan") or {}
    full_debate = session_data.get("debate_transcript") or session_data.get("council_dialogue") or []
    penalties = session_data.get("penalties_issued") or []

    with _db_lock:
        conn = _get_connection(db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO council_sessions
                    (session_id, symbol, target_date, created_at, verdict,
                     executive_summary_json, radar_scores_json, trade_plan_json,
                     full_debate_json, penalties_issued_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    session_id,
                    symbol,
                    target_date,
                    created_at,
                    verdict,
                    json.dumps(exec_summary, ensure_ascii=False),
                    json.dumps(radar_scores, ensure_ascii=False),
                    json.dumps(trade_plan, ensure_ascii=False),
                    json.dumps(full_debate, ensure_ascii=False),
                    json.dumps(penalties, ensure_ascii=False),
                ),
            )
            conn.commit()
            return session_id
        finally:
            conn.close()


def get_council_history(
    symbol: str,
    limit: int = 20,
    db_path: Optional[str | Path] = None,
) -> List[Dict[str, Any]]:
    """Truy vấn các phiên họp quân cơ trước đây của một mã cổ phiếu."""
    init_audit_db(db_path)
    sym = (symbol or "").upper().strip()
    with _db_lock:
        conn = _get_connection(db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT session_id, symbol, target_date, created_at, verdict,
                       executive_summary_json, radar_scores_json, trade_plan_json,
                       full_debate_json, penalties_issued_json
                FROM council_sessions
                WHERE symbol = ?
                ORDER BY created_at DESC
                LIMIT ?;
                """,
                (sym, limit),
            )
            rows = cursor.fetchall()
            results = []
            for r in rows:
                results.append(
                    {
                        "session_id": r["session_id"],
                        "symbol": r["symbol"],
                        "target_date": r["target_date"],
                        "created_at": r["created_at"],
                        "verdict": r["verdict"],
                        "executive_summary": json.loads(r["executive_summary_json"] or "{}"),
                        "radar_score_card": json.loads(r["radar_scores_json"] or "{}"),
                        "trade_plan": json.loads(r["trade_plan_json"] or "{}"),
                        "debate_transcript": json.loads(r["full_debate_json"] or "[]"),
                        "penalties_issued": json.loads(r["penalties_issued_json"] or "[]"),
                    }
                )
            return results
        finally:
            conn.close()


def get_recent_penalties(
    limit: int = 50,
    db_path: Optional[str | Path] = None,
) -> List[Dict[str, Any]]:
    """Lấy danh sách các án phạt kỷ luật gần nhất trên toàn hệ thống."""
    init_audit_db(db_path)
    with _db_lock:
        conn = _get_connection(db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, session_id, symbol, agent_id, agent_name, points_deducted, violation_type, reason, created_at
                FROM agent_penalties
                ORDER BY id DESC
                LIMIT ?;
                """,
                (limit,),
            )
            return [dict(r) for r in cursor.fetchall()]
        finally:
            conn.close()


def reset_agents_merit(db_path: Optional[str | Path] = None) -> None:
    """Khôi phục lại quỹ 20 Điểm Công Huân ban đầu cho toàn bộ 5 Agent (phục vụ testing & bảo trì)."""
    init_audit_db(db_path)
    now_str = datetime.now(timezone.utc).isoformat()
    with _db_lock:
        conn = _get_connection(db_path)
        try:
            cursor = conn.cursor()
            for ag in INITIAL_AGENTS:
                cursor.execute(
                    """
                    INSERT INTO agent_merit_profiles
                        (agent_id, name, role, generation, merit_points, warning_level, status, total_violations, updated_at)
                    VALUES (?, ?, ?, 1, 20, 0, 'HOAT_DONG', 0, ?)
                    ON CONFLICT(agent_id) DO UPDATE SET
                        generation = 1,
                        merit_points = 20,
                        warning_level = 0,
                        status = 'HOAT_DONG',
                        total_violations = 0,
                        updated_at = ?;
                    """,
                    (ag["agent_id"], ag["name"], ag["role"], now_str, now_str),
                )
            conn.commit()
        finally:
            conn.close()
