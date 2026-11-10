import React, { useState } from 'react';
import {
  Award,
  Crown,
  FileSearch,
  Zap,
  ShieldAlert,
  Scale,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  History,
  ShieldCheck,
  UserX,
} from 'lucide-react';

const AGENT_META = {
  minh_chu: {
    icon: Crown,
    color: '#fbbf24',
    bg: 'rgba(251, 191, 36, 0.12)',
    border: 'rgba(251, 191, 36, 0.35)',
    label: 'Supervisor / CIO',
  },
  huyet_vu: {
    icon: FileSearch,
    color: '#f87171',
    bg: 'rgba(248, 113, 113, 0.12)',
    border: 'rgba(248, 113, 113, 0.35)',
    label: 'Forensic Accounting & BCTC',
  },
  phong_lang: {
    icon: Zap,
    color: '#38bdf8',
    bg: 'rgba(56, 189, 248, 0.12)',
    border: 'rgba(56, 189, 248, 0.35)',
    label: 'Tactician & Orderflow',
  },
  tham_muu: {
    icon: ShieldAlert,
    color: '#fb923c',
    bg: 'rgba(251, 146, 60, 0.12)',
    border: 'rgba(251, 146, 60, 0.35)',
    label: 'Contrarian Risk Controller',
  },
  cam_y_ve: {
    icon: Scale,
    color: '#c084fc',
    bg: 'rgba(192, 132, 252, 0.12)',
    border: 'rgba(192, 132, 252, 0.35)',
    label: 'Audit & Continuous Improvement',
  },
};

const DEFAULT_AGENTS = [
  {
    agent_id: 'minh_chu',
    name: 'Minh Chủ Võ Lâm',
    role: 'Supervisor / CIO',
    merit_points: 20,
    status: 'HOAT_DONG',
    generation: 1,
    total_violations: 0,
    penalties: [],
  },
  {
    agent_id: 'huyet_vu',
    name: 'Huyết Vũ Lâu',
    role: 'Forensic Accounting & Financial Auditor',
    merit_points: 20,
    status: 'HOAT_DONG',
    generation: 1,
    total_violations: 0,
    penalties: [],
  },
  {
    agent_id: 'phong_lang',
    name: 'Phong Lang Đội',
    role: 'Tactician & Orderflow Specialist',
    merit_points: 20,
    status: 'HOAT_DONG',
    generation: 1,
    total_violations: 0,
    penalties: [],
  },
  {
    agent_id: 'tham_muu',
    name: 'Tham Mưu Các',
    role: 'Contrarian Risk Controller / Devil\'s Advocate',
    merit_points: 20,
    status: 'HOAT_DONG',
    generation: 1,
    total_violations: 0,
    penalties: [],
  },
  {
    agent_id: 'cam_y_ve',
    name: 'Cẩm Y Vệ',
    role: 'Audit & Continuous Improvement Officer',
    merit_points: 20,
    status: 'HOAT_DONG',
    generation: 1,
    total_violations: 0,
    penalties: [],
  },
];

function getStatusBadge(points, status) {
  const p = Number(points);
  if (p <= 0 || status === 'PHE_TRUAT') {
    return {
      text: 'Phế truất - Đời N+1',
      color: '#ef4444',
      bg: 'rgba(239, 68, 68, 0.2)',
      border: 'rgba(239, 68, 68, 0.5)',
      icon: UserX,
    };
  }
  if (p <= 5 || status === 'CANH_BAO_3') {
    return {
      text: 'Cảnh báo Cấp 3',
      color: '#f87171',
      bg: 'rgba(248, 113, 113, 0.15)',
      border: 'rgba(248, 113, 113, 0.4)',
      icon: AlertTriangle,
    };
  }
  if (p <= 10 || status === 'CANH_BAO_2') {
    return {
      text: 'Cảnh báo Cấp 2',
      color: '#fb923c',
      bg: 'rgba(251, 146, 60, 0.15)',
      border: 'rgba(251, 146, 60, 0.4)',
      icon: AlertTriangle,
    };
  }
  if (p <= 15 || status === 'CANH_BAO_1') {
    return {
      text: 'Cảnh báo Cấp 1',
      color: '#facc15',
      bg: 'rgba(250, 204, 21, 0.15)',
      border: 'rgba(250, 204, 21, 0.4)',
      icon: AlertTriangle,
    };
  }
  return {
    text: 'Hoạt động',
    color: '#10b981',
    bg: 'rgba(16, 185, 129, 0.15)',
    border: 'rgba(16, 185, 129, 0.4)',
    icon: ShieldCheck,
  };
}

export default function AgentMeritBoard({
  agents = [],
  recentPenalties = [],
  onRefresh,
}) {
  const [expandedAgent, setExpandedAgent] = useState(null);
  const [showAllPenalties, setShowAllPenalties] = useState(false);

  // Gộp danh sách agent từ API hoặc fallback
  const agentList =
    Array.isArray(agents) && agents.length > 0
      ? agents.map((a) => {
          const fallback = DEFAULT_AGENTS.find((d) => d.agent_id === a.agent_id || d.agent_id === a.id);
          return {
            ...fallback,
            ...a,
            agent_id: a.agent_id || a.id || fallback?.agent_id,
            merit_points: a.merit_points ?? a.score ?? 20,
          };
        })
      : DEFAULT_AGENTS;

  const toggleExpand = (id) => {
    setExpandedAgent((prev) => (prev === id ? null : id));
  };

  return (
    <div className="ws-panel ws-merit-board">
      <div className="ws-panel-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Award size={15} style={{ color: '#fbbf24' }} />
          <span>Điểm Công Huân & Trạng Thái Kỷ Luật</span>
        </div>
        <span className="ws-merit-header-badge">5 Tác Nhân</span>
      </div>

      <div className="ws-merit-content">
        <div className="ws-merit-rule-note">
          <span>Quỹ 20 điểm/Agent · Phạm lỗi -1 điểm · Phế truất tại 0 điểm</span>
        </div>

        <div className="ws-merit-list">
          {agentList.map((agent) => {
            const meta = AGENT_META[agent.agent_id] || {
              icon: Award,
              color: '#38bdf8',
              bg: 'rgba(56, 189, 248, 0.12)',
              border: 'rgba(56, 189, 248, 0.35)',
              label: agent.role,
            };
            const Icon = meta.icon;
            const points = Number(agent.merit_points ?? 20);
            const badge = getStatusBadge(points, agent.status);
            const BadgeIcon = badge.icon;
            const pct = Math.min(100, Math.max(0, (points / 20) * 100));
            const isExpanded = expandedAgent === agent.agent_id;
            const agentPenalties = agent.penalties || [];

            return (
              <div
                key={agent.agent_id}
                className={`ws-agent-card ${isExpanded ? 'expanded' : ''}`}
                onClick={() => toggleExpand(agent.agent_id)}
              >
                <div className="ws-agent-row">
                  <div
                    className="ws-agent-avatar"
                    style={{ background: meta.bg, borderColor: meta.border, color: meta.color }}
                  >
                    <Icon size={16} />
                  </div>

                  <div className="ws-agent-info">
                    <div className="ws-agent-name-line">
                      <span className="ws-agent-name">{agent.name}</span>
                      <span className="ws-agent-gen">Đời {agent.generation || 1}</span>
                    </div>
                    <div className="ws-agent-role">{meta.label}</div>
                  </div>

                  <div className="ws-agent-score-col">
                    <div className="ws-agent-score-val" style={{ color: badge.color }}>
                      <strong>{points}</strong>
                      <span className="ws-agent-score-max">/20</span>
                    </div>
                    <span
                      className="ws-agent-status-badge"
                      style={{
                        color: badge.color,
                        background: badge.bg,
                        borderColor: badge.border,
                      }}
                    >
                      <BadgeIcon size={10} />
                      {badge.text}
                    </span>
                  </div>

                  <div className="ws-agent-expand-icon">
                    {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                  </div>
                </div>

                {/* Progress bar Điểm Công Huân */}
                <div className="ws-agent-progress-track">
                  <div
                    className="ws-agent-progress-fill"
                    style={{
                      width: `${pct}%`,
                      background: `linear-gradient(90deg, ${badge.color}88, ${badge.color})`,
                    }}
                  />
                </div>

                {/* Phần mở rộng chi tiết vi phạm kỷ luật */}
                {isExpanded && (
                  <div
                    className="ws-agent-detail"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <div className="ws-agent-detail-stats">
                      <span>Tổng vi phạm: <strong>{agent.total_violations || agentPenalties.length || 0}</strong></span>
                      <span>Trạng thái: <strong style={{ color: badge.color }}>{badge.text}</strong></span>
                      <span>Thế hệ: <strong>Đời {agent.generation || 1}</strong></span>
                    </div>

                    <div className="ws-agent-penalty-log">
                      <div className="ws-agent-log-title">
                        <History size={12} />
                        <span>Nhật ký Án phạt Kỷ luật</span>
                      </div>
                      {agentPenalties.length > 0 ? (
                        <div className="ws-agent-log-list">
                          {agentPenalties.map((pen, idx) => (
                            <div key={pen.id || idx} className="ws-agent-log-item">
                              <span className="ws-log-deduct">-{pen.points_deducted || 1}đ</span>
                              <span className="ws-log-type">{pen.violation_type || 'VI PHẠM'}</span>
                              <span className="ws-log-reason">{pen.reason}</span>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className="ws-agent-log-empty">
                          <ShieldCheck size={13} style={{ color: '#10b981' }} />
                          <span>Chưa có ghi nhận vi phạm · Tác phong chuẩn mực</span>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Nút xem toàn bộ nhật ký kỷ luật chung */}
        {recentPenalties.length > 0 && (
          <div className="ws-merit-footer">
            <button
              type="button"
              className="ws-merit-toggle-btn"
              onClick={() => setShowAllPenalties((prev) => !prev)}
            >
              <History size={12} />
              <span>{showAllPenalties ? 'Thu gọn biên bản án phạt' : `Xem toàn bộ án phạt (${recentPenalties.length})`}</span>
            </button>

            {showAllPenalties && (
              <div className="ws-all-penalties-box">
                {recentPenalties.map((p, idx) => (
                  <div key={p.id || idx} className="ws-all-penalty-row">
                    <span className="ws-penalty-agent">{p.agent_id}</span>
                    <span className="ws-penalty-pts">-{p.points_deducted}đ</span>
                    <span className="ws-penalty-sym">[{p.symbol}]</span>
                    <span className="ws-penalty-desc">{p.reason}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
