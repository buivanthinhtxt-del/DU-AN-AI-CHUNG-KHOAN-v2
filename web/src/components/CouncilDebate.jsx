import React, { useState } from 'react';
import {
  Crown,
  FileSearch,
  Zap,
  ShieldAlert,
  Scale,
  Swords,
  ScrollText,
  Flame,
  CheckCircle2,
  RefreshCw,
  Filter,
  ChevronDown,
  ChevronUp,
  MessageSquare,
  Sparkles,
} from 'lucide-react';

const AGENT_CONFIG = {
  minh_chu: {
    name: 'Minh Chủ Võ Lâm',
    title: 'Supervisor / CIO · Tổng Trưởng Quân Cơ',
    icon: Crown,
    color: '#fbbf24',
    bg: 'rgba(251, 191, 36, 0.1)',
    border: 'rgba(251, 191, 36, 0.4)',
    badgeBg: 'rgba(251, 191, 36, 0.2)',
    tone: 'Quyền uy, công tâm, điều phối tranh biện và ban hành phán quyết tối hậu',
  },
  huyet_vu: {
    name: 'Huyết Vũ Lâu',
    title: 'Forensic Accounting & BCTC · Pháp Y Tài Chính',
    icon: FileSearch,
    color: '#f87171',
    bg: 'rgba(248, 113, 113, 0.1)',
    border: 'rgba(248, 113, 113, 0.4)',
    badgeBg: 'rgba(248, 113, 113, 0.2)',
    tone: 'Lạnh lùng, bóc trần dòng tiền ảo (CFO vs NI), né bẫy chia tách và sự kiện quyền',
  },
  phong_lang: {
    name: 'Phong Lang Đội',
    title: 'Tactician & Orderflow Specialist · Tiên Phong Bảng Điện',
    icon: Zap,
    color: '#38bdf8',
    bg: 'rgba(56, 189, 248, 0.1)',
    border: 'rgba(56, 189, 248, 0.4)',
    badgeBg: 'rgba(56, 189, 248, 0.2)',
    tone: 'Sắc bén, chớp thời cơ nến ngày, Wyckoff, VSA, phục kích bẫy T+2.5 và lệnh ATC',
  },
  tham_muu: {
    name: 'Tham Mưu Các',
    title: 'Contrarian Risk Controller · Quân Sư Vai Ác',
    icon: ShieldAlert,
    color: '#fb923c',
    bg: 'rgba(251, 146, 60, 0.1)',
    border: 'rgba(251, 146, 60, 0.4)',
    badgeBg: 'rgba(251, 146, 60, 0.2)',
    tone: 'Gai góc, luôn tìm lý do BÁC BỎ kèo mua, khóa chặt Bộ 3 Chốt Chặn, siết tỷ trọng ≤ 25%',
  },
  cam_y_ve: {
    name: 'Cẩm Y Vệ',
    title: 'Audit & Continuous Improvement · Chấp Pháp Kỷ Luật',
    icon: Scale,
    color: '#c084fc',
    bg: 'rgba(192, 132, 252, 0.1)',
    border: 'rgba(192, 132, 252, 0.4)',
    badgeBg: 'rgba(192, 132, 252, 0.2)',
    tone: 'Thiết diện vô tư, tra cứu lịch sử Forecast Audit, bắt lỗi bịa đặt và trừ Điểm Công Huân',
  },
};

const VERDICT_STYLES = {
  'CHỈ THỊ': { color: '#fbbf24', bg: 'rgba(251, 191, 36, 0.15)', border: '#fbbf2466' },
  'BÁO CÁO': { color: '#38bdf8', bg: 'rgba(56, 189, 248, 0.15)', border: '#38bdf866' },
  'PHẢN BIỆN': { color: '#fb923c', bg: 'rgba(251, 146, 60, 0.15)', border: '#fb923c66' },
  'THANH TRA': { color: '#c084fc', bg: 'rgba(192, 132, 252, 0.15)', border: '#c084fc66' },
  'NGHỊ QUYẾT': { color: '#10b981', bg: 'rgba(16, 185, 129, 0.15)', border: '#10b98166' },
};

function formatTranscriptContent(text) {
  if (!text) return null;
  const paragraphs = text.split('\n\n');
  return paragraphs.map((p, idx) => {
    const trimmed = p.trim();
    if (!trimmed) return null;
    const isHeading = /^[⚔️🩸⚡🔥💀🛡️🔍⚖️📜🏛️🚩🎯]/.test(trimmed);
    const isQuote = trimmed.startsWith('"') || trimmed.startsWith('“');
    return (
      <div
        key={idx}
        className={`ws-debate-paragraph ${isHeading ? 'heading' : ''} ${isQuote ? 'quote' : ''}`}
      >
        {trimmed.split('\n').map((line, lIdx) => {
          if (line.startsWith('- ')) {
            return (
              <div key={lIdx} className="ws-debate-bullet">
                <span className="ws-debate-dot">•</span>
                <span>{line.replace(/^- /, '')}</span>
              </div>
            );
          }
          return <div key={lIdx}>{line}</div>;
        })}
      </div>
    );
  });
}

export default function CouncilDebate({
  debate,
  loading = false,
  symbol = 'HPG',
  onRefresh,
}) {
  const [selectedRound, setSelectedRound] = useState('ALL');
  const [selectedAgent, setSelectedAgent] = useState('ALL');
  const [collapsedCards, setCollapsedCards] = useState({});

  const transcript = debate?.debate_transcript || [];
  const sessionId = debate?.session_id || `council_${symbol}_session`;
  const engineType = debate?.engine || 'Multi-Agent Asyncio Debate Loop';
  const execSummary = debate?.executive_summary || {};
  const radar = debate?.radar_score_card || {};

  // Lọc transcript theo round và agent
  const filteredTranscript = transcript.filter((item) => {
    if (selectedRound !== 'ALL' && Number(item.round) !== Number(selectedRound)) {
      return false;
    }
    if (selectedAgent !== 'ALL' && item.agent_id !== selectedAgent) {
      return false;
    }
    return true;
  });

  const toggleCollapse = (idx) => {
    setCollapsedCards((prev) => ({ ...prev, [idx]: !prev[idx] }));
  };

  const rounds = [
    { id: 'ALL', label: 'Tất Cả 5 Vòng' },
    { id: '1', label: 'Vòng 1: Khởi Xướng' },
    { id: '2', label: 'Vòng 2: Mổ Xẻ & Bảng Điện' },
    { id: '3', label: 'Vòng 3: Phản Biện Bác Bỏ' },
    { id: '4', label: 'Vòng 4: Soát Xét Lịch Sử' },
    { id: '5', label: 'Vòng 5: Nghị Quyết Tối Hậu' },
  ];

  return (
    <div className="ws-council-debate-container">
      {/* Banner Tiêu Đề Quân Cơ */}
      <div className="ws-council-hero">
        <div className="ws-council-hero-left">
          <div className="ws-council-emblem">
            <Swords size={28} className="ws-emblem-icon" />
          </div>
          <div>
            <div className="ws-council-title">
              BIÊN BẢN CUỘC HỌP QUÂN CƠ CÁC
            </div>
            <div className="ws-council-subtitle">
              Tranh biện đối kháng & Soát lỗi (Critique Loop) giữa 5 Tác Nhân · Phân tích chiến lược mã <strong>{symbol}</strong>
            </div>
            <div className="ws-council-meta-row">
              <span className="ws-council-tag ws-tag-gold">
                <Crown size={12} /> Minh Chủ Võ Lâm Chủ Tọa
              </span>
              <span className="ws-council-tag ws-tag-blue">
                <Sparkles size={12} /> {engineType}
              </span>
              <span className="ws-council-tag ws-tag-purple">
                <ScrollText size={12} /> {sessionId}
              </span>
            </div>
          </div>
        </div>

        <div className="ws-council-hero-actions">
          {onRefresh && (
            <button
              type="button"
              className="ws-council-refresh-btn"
              onClick={onRefresh}
              disabled={loading}
            >
              <RefreshCw size={14} className={loading ? 'ws-spin' : ''} />
              <span>{loading ? 'Đang tranh biện...' : 'Triệu tập lại Hội Đồng'}</span>
            </button>
          )}
        </div>
      </div>

      {/* Thanh Lọc Theo Vòng & Agent */}
      <div className="ws-council-filter-bar">
        <div className="ws-filter-group">
          <span className="ws-filter-label">
            <Filter size={13} /> Lọc Vòng Tranh Luận:
          </span>
          <div className="ws-filter-chips">
            {rounds.map((r) => (
              <button
                key={r.id}
                type="button"
                className={`ws-filter-chip ${selectedRound === r.id ? 'active' : ''}`}
                onClick={() => setSelectedRound(r.id)}
              >
                {r.label}
              </button>
            ))}
          </div>
        </div>

        <div className="ws-filter-group">
          <span className="ws-filter-label">Lọc Tác Nhân:</span>
          <div className="ws-filter-chips">
            <button
              type="button"
              className={`ws-filter-chip ${selectedAgent === 'ALL' ? 'active' : ''}`}
              onClick={() => setSelectedAgent('ALL')}
            >
              Tất Cả 5 Agent
            </button>
            {Object.entries(AGENT_CONFIG).map(([key, cfg]) => (
              <button
                key={key}
                type="button"
                className={`ws-filter-chip ${selectedAgent === key ? 'active' : ''}`}
                onClick={() => setSelectedAgent(key)}
                style={
                  selectedAgent === key
                    ? { borderColor: cfg.color, color: cfg.color, backgroundColor: cfg.bg }
                    : {}
                }
              >
                {cfg.name}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Diễn Biến Tranh Biện (Transcript Timeline) */}
      <div className="ws-council-timeline">
        {loading ? (
          <div className="ws-council-loading">
            <RefreshCw size={24} className="ws-spin" style={{ color: '#fbbf24' }} />
            <div className="ws-loading-text">
              Hội Đồng Quân Cơ đang tranh luận nảy lửa... Vui lòng đợi trong giây lát!
            </div>
            <div className="ws-loading-sub">
              Huyết Vũ Lâu mổ xẻ BCTC · Phong Lang Đội canh bảng điện · Tham Mưu Các chuẩn bị bác bỏ...
            </div>
          </div>
        ) : filteredTranscript.length > 0 ? (
          filteredTranscript.map((item, idx) => {
            const agentKey = item.agent_id || 'minh_chu';
            const agentCfg = AGENT_CONFIG[agentKey] || AGENT_CONFIG.minh_chu;
            const IconComponent = agentCfg.icon;
            const verdict = item.verdict || 'BÁO CÁO';
            const vStyle = VERDICT_STYLES[verdict] || VERDICT_STYLES['BÁO CÁO'];
            const isCollapsed = Boolean(collapsedCards[idx]);

            return (
              <div
                key={idx}
                className="ws-debate-card"
                style={{ borderColor: agentCfg.border }}
              >
                {/* Header thẻ phát biểu */}
                <div
                  className="ws-debate-card-header"
                  style={{ backgroundColor: agentCfg.bg }}
                  onClick={() => toggleCollapse(idx)}
                >
                  <div className="ws-debate-speaker-info">
                    <div
                      className="ws-debate-avatar"
                      style={{
                        backgroundColor: agentCfg.badgeBg,
                        color: agentCfg.color,
                        borderColor: agentCfg.border,
                      }}
                    >
                      <IconComponent size={18} />
                    </div>
                    <div>
                      <div className="ws-debate-speaker-name-line">
                        <span className="ws-debate-speaker-name" style={{ color: agentCfg.color }}>
                          {item.speaker || agentCfg.name}
                        </span>
                        <span className="ws-debate-round-badge">
                          Vòng {item.round}
                        </span>
                        <span
                          className="ws-debate-verdict-badge"
                          style={{
                            color: vStyle.color,
                            backgroundColor: vStyle.bg,
                            borderColor: vStyle.border,
                          }}
                        >
                          {verdict}
                        </span>
                      </div>
                      <div className="ws-debate-card-title">{item.title}</div>
                    </div>
                  </div>

                  <div className="ws-debate-header-right">
                    <span className="ws-debate-tone-hint">{agentCfg.tone}</span>
                    <button type="button" className="ws-debate-collapse-btn">
                      {isCollapsed ? <ChevronDown size={16} /> : <ChevronUp size={16} />}
                    </button>
                  </div>
                </div>

                {/* Nội dung lời thoại kiếm hiệp */}
                {!isCollapsed && (
                  <div className="ws-debate-card-body">
                    {formatTranscriptContent(item.content)}
                  </div>
                )}
              </div>
            );
          })
        ) : (
          <div className="ws-council-empty">
            <MessageSquare size={32} style={{ color: '#64748b' }} />
            <div>Không tìm thấy biên bản phù hợp với bộ lọc hiện tại.</div>
          </div>
        )}
      </div>

      {/* Hộp Tổng Kết Nghị Quyết Cuối Phiên */}
      {execSummary.directive_line && (
        <div className="ws-council-resolution-box">
          <div className="ws-res-box-header">
            <Crown size={18} style={{ color: '#fbbf24' }} />
            <span>NGHỊ QUYẾT TỐI HẬU ĐƯỢC PHÊ CHUẨN</span>
          </div>
          <div className="ws-res-box-content">
            <div className="ws-res-row">
              <strong>Hành động:</strong> {execSummary.action_line}
            </div>
            <div className="ws-res-row">
              <strong>Phòng thủ:</strong> {execSummary.defense_stops_line}
            </div>
            <div className="ws-res-row">
              <strong>Quân lệnh:</strong> {execSummary.directive_line}
            </div>
          </div>
          {radar.overall_score && (
            <div className="ws-res-scores-bar">
              <span className="ws-res-score-item">Cơ bản: <strong>{radar.co_ban}</strong></span>
              <span className="ws-res-score-item">Kỹ thuật: <strong>{radar.ky_thuat}</strong></span>
              <span className="ws-res-score-item">Dòng tiền: <strong>{radar.dong_tien}</strong></span>
              <span className="ws-res-score-item">Quản trị rủi ro: <strong>{radar.quan_tri_rui_ro}</strong></span>
              <span className="ws-res-score-item">Xác suất thành công: <strong>{radar.xac_suat_thanh_cong}%</strong></span>
              <span className="ws-res-score-item ws-res-score-total">
                Tổng thể: <strong>{radar.overall_score}/100</strong>
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
