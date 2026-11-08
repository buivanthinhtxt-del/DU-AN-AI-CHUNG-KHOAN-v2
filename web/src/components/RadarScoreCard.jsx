import React from 'react';
import { Activity } from 'lucide-react';

export default function RadarScoreCard({ scores, overallScore, summary }) {
  if (!scores) return null;

  const labels = ['Vĩ mô & Ngành', 'FA & Catalyst', 'TA & Xu hướng', 'Dòng tiền', 'Chiến lược'];
  const keys = [
    'macro_industry',
    'fundamentals_catalyst',
    'technical_momentum',
    'comparative_strength',
    'action_strategy',
  ];
  const size = 260;
  const center = size / 2;
  const radius = size / 2 - 35;

  const getPoint = (val, index, total) => {
    const angle = (Math.PI * 2 * index) / total - Math.PI / 2;
    const r = (val / 100) * radius;
    return { x: center + r * Math.cos(angle), y: center + r * Math.sin(angle) };
  };

  const total = 5;
  const ticks = [20, 40, 60, 80, 100];
  const webs = ticks.map((t) => {
    const pts = Array.from({ length: total })
      .map((_, i) => Object.values(getPoint(t, i, total)).join(','))
      .join(' ');
    return <polygon key={`web-${t}`} points={pts} fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="1" />;
  });

  const scorePts = keys
    .map((k, i) => {
      const v = scores[k]?.score || 0;
      return Object.values(getPoint(v, i, total)).join(',');
    })
    .join(' ');

  const labelEls = keys.map((_, i) => {
    const pt = getPoint(125, i, total);
    return (
      <text
        key={`lbl-${i}`}
        x={pt.x}
        y={pt.y}
        fill="var(--text-secondary)"
        fontSize="11"
        textAnchor="middle"
        dominantBaseline="middle"
      >
        {labels[i]}
      </text>
    );
  });

  const progressItems = [
    { key: 'macro_industry', label: '🌍 BƯỚC 1: Vĩ mô & Sóng ngành' },
    { key: 'fundamentals_catalyst', label: '🏢 BƯỚC 2: Nội lực Cơ bản & Chất xúc tác' },
    { key: 'technical_momentum', label: '📈 BƯỚC 3: Kỹ thuật & Xu hướng (TA)' },
    { key: 'comparative_strength', label: '🧱 BƯỚC 4: Dòng tiền & Sức mạnh tương quan' },
    { key: 'action_strategy', label: '🎯 BƯỚC 5: Chiến lược & Kịch bản hành động' },
  ];

  const badgeBg =
    (overallScore || 0) >= 65 ? '#3fb950' : (overallScore || 0) < 40 ? '#f85149' : 'var(--accent-gold)';

  return (
    <div className="bottom-cards-row">
      <div className="glass-panel analysis-card">
        <div className="section-title" style={{ flexWrap: 'wrap', gap: '0.75rem' }}>
          <Activity size={18} color="var(--accent-gold)" />
          <h2>Bảng Chấm Điểm 5 Chiều Thực Chiến</h2>

          {summary && (
            <div style={{ display: 'flex', gap: '0.5rem', marginLeft: '0.5rem', flexWrap: 'wrap' }}>
              {summary.stance && <span className="summary-pill">Trạng thái: {summary.stance}</span>}
              {summary.confidence && <span className="summary-pill">Độ tin cậy: {summary.confidence}</span>}
              {summary.action && <span className="summary-pill action">Khuyến nghị: {summary.action}</span>}
            </div>
          )}

          <span
            style={{
              marginLeft: 'auto',
              background: badgeBg,
              color: '#010409',
              padding: '4px 12px',
              borderRadius: '6px',
              fontWeight: 'bold',
            }}
          >
            Điểm tổng hợp: {overallScore ?? 'N/A'}/100
          </span>
        </div>

        <div
          className="scoring-container"
          style={{ display: 'flex', gap: '3rem', marginTop: '1.5rem', flexWrap: 'wrap', alignItems: 'center' }}
        >
          <div className="radar-chart" style={{ flex: '1', minWidth: '250px', display: 'flex', justifyContent: 'center' }}>
            <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
              {webs}
              <polygon points={scorePts} fill="rgba(47, 129, 247, 0.25)" stroke="var(--accent-blue)" strokeWidth="2" />
              {keys.map((k, i) => {
                const v = scores[k]?.score || 0;
                const pt = getPoint(v, i, total);
                return <circle key={`dot-${i}`} cx={pt.x} cy={pt.y} r="4" fill="var(--accent-gold)" />;
              })}
              {labelEls}
            </svg>
          </div>

          <div className="progress-bars" style={{ flex: '2', minWidth: '300px', display: 'flex', flexDirection: 'column' }}>
            {progressItems.map((item, idx) => {
              const val = scores[item.key]?.score || 0;
              const reason = scores[item.key]?.reason || 'Chưa có dữ liệu đánh giá';
              let color = '#f85149';
              if (val >= 40) color = '#d29922';
              if (val >= 70) color = '#3fb950';

              return (
                <div key={idx} className="progress-item" style={{ marginBottom: '14px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: '6px' }}>
                    <span style={{ color: 'var(--text-active)', fontWeight: '600' }}>{item.label}</span>
                    <span style={{ color, fontWeight: 'bold' }}>{val}/100</span>
                  </div>
                  <div
                    style={{
                      width: '100%',
                      height: '6px',
                      background: 'rgba(255,255,255,0.05)',
                      borderRadius: '3px',
                      overflow: 'hidden',
                    }}
                  >
                    <div
                      style={{
                        width: `${val}%`,
                        height: '100%',
                        background: color,
                        transition: 'width 0.8s ease-out',
                      }}
                    ></div>
                  </div>
                  <div
                    style={{
                      fontSize: '0.8rem',
                      color: 'var(--text-secondary)',
                      marginTop: '4px',
                      fontStyle: 'italic',
                      lineHeight: '1.4',
                    }}
                  >
                    ↳ {reason}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

