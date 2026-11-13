import React from 'react';
import {
  Compass,
  Crosshair,
  Scale,
  ShieldAlert,
  ListChecks,
  CalendarClock,
  Sigma,
  ExternalLink,
  Cpu,
  TriangleAlert,
  History,
  Activity,
} from 'lucide-react';
function getVerificationBadgeClass(tag) {
  if (tag.startsWith('[Nguồn')) return 'badge-tag badge-source';
  if (tag.startsWith('[Tính toán')) return 'badge-tag badge-calc';
  if (tag.startsWith('[Suy luận')) return 'badge-tag badge-deduce';
  if (tag.startsWith('[Giả định')) return 'badge-tag badge-assume';
  if (tag.startsWith('[Chưa xác định')) return 'badge-tag badge-unknown';
  if (tag.startsWith('[Mâu thuẫn nguồn')) return 'badge-tag badge-conflict';
  return 'badge-tag';
}

function renderInlineFormatting(text) {
  if (!text || typeof text !== 'string') return text;
  const parts = text.split(/(\*\*.*?\*\*|\*[^*]+\*|\[(?:Nguồn|Tính toán|Suy luận|Giả định|Chưa xác định|Mâu thuẫn nguồn)[^\]]*\])/g);
  return parts.map((part, pi) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      const inner = part.slice(2, -2);
      if (/^\[(?:Nguồn|Tính toán|Suy luận|Giả định|Chưa xác định|Mâu thuẫn nguồn)/.test(inner)) {
        return (
          <span key={pi} className={getVerificationBadgeClass(inner)}>
            {inner}
          </span>
        );
      }
      return (
        <strong key={pi} style={{ color: 'var(--text-active)' }}>
          {inner}
        </strong>
      );
    }
    if (part.startsWith('*') && part.endsWith('*') && part.length > 2) {
      return (
        <em key={pi} style={{ color: 'var(--text-secondary)' }}>
          {part.slice(1, -1)}
        </em>
      );
    }
    if (part.startsWith('[') && part.endsWith(']') && /^\[(?:Nguồn|Tính toán|Suy luận|Giả định|Chưa xác định|Mâu thuẫn nguồn)/.test(part)) {
      return (
        <span key={pi} className={getVerificationBadgeClass(part)}>
          {part}
        </span>
      );
    }
    return part;
  });
}

// Định dạng số kiểu Việt Nam: 1.725,36
const vn = (x, nd = 2) => {
  const n = Number(x);
  if (x === null || x === undefined || Number.isNaN(n)) return 'N/A';
  return n.toLocaleString('vi-VN', { minimumFractionDigits: nd, maximumFractionDigits: nd });
};
const pct = (x, nd = 2) => {
  const n = Number(x);
  if (x === null || x === undefined || Number.isNaN(n)) return 'N/A';
  return `${n > 0 ? '+' : ''}${vn(n, nd)}%`;
};

const ACTION_COLORS = {
  Mua: 'var(--up-color)',
  'Mua thăm dò': '#34d399',
  'Nắm giữ': 'var(--accent-blue)',
  'Quan sát': 'var(--accent-gold)',
  'Hạ tỷ trọng': '#fb923c',
  'Bán / Đứng ngoài': 'var(--down-color)',
};

function Section({ icon, title, children, className = '' }) {
  return (
    <div className={`thesis-block ${className}`}>
      <div className="thesis-block-title">
        {icon}
        <span>{title}</span>
      </div>
      {children}
    </div>
  );
}

function rrColor(rr) {
  if (rr >= 2) return 'var(--up-color)';
  if (rr >= 1.5) return 'var(--accent-gold)';
  return 'var(--down-color)';
}

export default function InvestmentThesis({ report }) {
  if (!report || !report.trade_plan) return null;

  const {
    verdict = {},
    thesis = {},
    trade_plan: tp = {},
    scenarios = [],
    catalysts = [],
    risks = [],
    monitoring = [],
    data_gaps: gaps = [],
    consistency_notes: notes = [],
    sources = [],
    summary = {},
    quant_snapshot: qs = {},
    data_quality: dq = {},
  } = report;

  const isAI = String(report.engine || '').startsWith('gemini:');
  const engineLabel = isAI ? `AI ${report.engine.replace('gemini:', '')}` : 'Định lượng tự động (không dùng AI)';
  const actionColor = ACTION_COLORS[summary.action] || 'var(--accent-gold)';
  const rr = Number(tp.rr_ratio) || 0;
  const baseRates = qs.base_rates?.results || {};

  const fa = report.forecast_audit || qs.forecast_audit;
  const stops = tp.exit_stops || qs.exit_stops || qs.tactical_6step?.exit_stops;
  const priceStop = stops?.price_stop || {};
  const thesisStop = stops?.thesis_stop || {};
  const timeStop = stops?.time_stop || {};
  const hypotheses = (report.causal_hypotheses && report.causal_hypotheses.length > 0)
    ? report.causal_hypotheses
    : (qs.causal_hypotheses || []);
  const tac = qs.tactical_6step || {};

  return (
    <div className="glass-panel analysis-card thesis-card">
      <div className="section-title" style={{ flexWrap: 'wrap', gap: '0.6rem' }}>
        <Compass size={18} color="var(--accent-gold)" />
        <h2>Quyết Định Đầu Tư & Kế Hoạch Hành Động</h2>
        <span className="thesis-chip" title="Nguồn tạo báo cáo">
          <Cpu size={12} /> {engineLabel}
        </span>
        {dq.score !== undefined && (
          <span className="thesis-chip" title="Mức độ đầy đủ của dữ liệu đầu vào — giới hạn độ tin cậy của nhận định">
            Dữ liệu {dq.score}/100 · trần tin cậy {dq.max_confidence}
          </span>
        )}
        {report.as_of && <span className="thesis-chip">Dữ liệu đến {report.as_of}</span>}
      </div>

      {/* KẾT LUẬN */}
      <div className="verdict-hero" style={{ borderColor: actionColor }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.4rem', marginBottom: '0.4rem' }}>
          <div className="verdict-action" style={{ color: actionColor }}>
            {summary.action || 'Quan sát'}
            <span className="verdict-sub">
              {summary.stance} · Độ tin cậy {summary.confidence}
            </span>
          </div>
          <div className="thesis-chip" style={{ fontSize: '0.8rem', padding: '0.2rem 0.6rem', background: 'rgba(255,255,255,0.06)' }}>
            📅 Phiên: <strong style={{ color: 'var(--text-active)' }}>{report.as_of || 'Hôm nay'}</strong> · Giá tham chiếu: <strong className="mono" style={{ color: 'var(--accent-gold)' }}>{vn(qs.close || report.price || tp.entry_high)}</strong>
          </div>
        </div>
        <p className="verdict-thesis">{renderInlineFormatting(verdict.core_thesis)}</p>
      </div>

      <div className="verdict-grid">
        <div className="verdict-cell">
          <span className="verdict-label">Người chưa có cổ phiếu</span>
          <p>{renderInlineFormatting(verdict.for_new_buyers) || '—'}</p>
        </div>
        <div className="verdict-cell">
          <span className="verdict-label">Người đang nắm giữ</span>
          <p>{renderInlineFormatting(verdict.for_holders) || '—'}</p>
        </div>
        <div className="verdict-cell">
          <span className="verdict-label">1–4 tuần tới</span>
          <p>{renderInlineFormatting(verdict.short_term) || '—'}</p>
        </div>
        <div className="verdict-cell">
          <span className="verdict-label">3–12 tháng</span>
          <p>{renderInlineFormatting(verdict.medium_term) || '—'}</p>
        </div>
      </div>
      {verdict.decision_level && (
        <div className="decision-level">
          <Crosshair size={14} /> <strong>Mức giá quyết định:</strong> {renderInlineFormatting(verdict.decision_level)}
        </div>
      )}

      {/* THẺ ĐỐI CHIẾU DỰ BÁO CŨ (FORECAST AUDIT & SELF-CALIBRATION) */}
      {fa && (
        <div className="forecast-audit-panel">
          <div className="audit-header">
            <div className="audit-title">
              <History size={16} color="var(--accent-blue)" />
              <span>ĐỐI CHIẾU DỰ BÁO CŨ & TỰ HIỆU CHỈNH (FORECAST AUDIT)</span>
            </div>
            {fa.has_history && fa.last_audit ? (
              <span className={`audit-badge ${
                fa.last_audit.verdict === 'CHÍNH XÁC' ? 'audit-badge-correct' :
                fa.last_audit.verdict === 'ĐẠT MỘT PHẦN' ? 'audit-badge-partial' : 'audit-badge-wrong'
              }`}>
                {fa.last_audit.verdict} · {fa.last_audit.overall_accuracy_pct}% CHUẨN XÁC
              </span>
            ) : (
              <span className="audit-badge audit-badge-partial">LẦN ĐẦU THẨM ĐỊNH · ĐÃ LƯU BASELINE VÀO CACHE</span>
            )}
          </div>

          {fa.has_history && fa.last_audit ? (
            <>
              <div className="audit-meta">
                Lần thẩm định trước: <strong>{fa.last_audit.forecast_date}</strong> · Giá lúc dự báo: <strong className="mono">{vn(fa.last_audit.as_of_price)}</strong> &rarr; Giá thực tế hiện tại: <strong className="mono">{vn(fa.last_audit.actual_price)}</strong> ({pct(fa.last_audit.price_change_pct)})
              </div>
              <div className="audit-grid-4">
                <div className="audit-cell">
                  <div className="audit-cell-label">1. Hướng đi (Direction)</div>
                  <div className="audit-cell-val" style={{ color: fa.last_audit.direction_score >= 1.0 ? 'var(--up-color)' : 'var(--down-color)' }}>
                    {fa.last_audit.direction_score >= 1.0 ? '🟢 ĐÚNG' : '🔴 SAI'} ({fa.last_audit.predicted_direction} &rarr; {fa.last_audit.actual_direction})
                  </div>
                </div>
                <div className="audit-cell">
                  <div className="audit-cell-label">2. Biên độ (Amplitude)</div>
                  <div className="audit-cell-val" style={{ color: fa.last_audit.amplitude_score >= 0.8 ? 'var(--up-color)' : 'var(--accent-gold)' }}>
                    {Math.round(fa.last_audit.amplitude_score * 100)}% (Mục tiêu {vn(fa.last_audit.predicted_target)})
                  </div>
                </div>
                <div className="audit-cell">
                  <div className="audit-cell-label">3. Thời điểm (Timing)</div>
                  <div className="audit-cell-val" style={{ color: fa.last_audit.time_score >= 0.8 ? 'var(--up-color)' : 'var(--accent-gold)' }}>
                    {Math.round(fa.last_audit.time_score * 100)}% (Chu kỳ T+)
                  </div>
                </div>
                <div className="audit-cell">
                  <div className="audit-cell-label">4. Điều kiện (Condition)</div>
                  <div className="audit-cell-val" style={{ color: fa.last_audit.condition_score >= 1.0 ? 'var(--up-color)' : 'var(--down-color)' }}>
                    {fa.last_audit.condition_score >= 1.0 ? '🟢 BẢO TOÀN' : '🔴 VI PHẠM STOP'}
                  </div>
                </div>
              </div>
              <div className="audit-lessons">
                <strong>Bài học tự đúc rút:</strong> {renderInlineFormatting(fa.last_audit.lessons_learned || fa.lessons_learned)}
              </div>
            </>
          ) : (
            <div style={{ marginTop: '0.6rem', padding: '0.8rem', background: 'rgba(59, 130, 246, 0.05)', borderRadius: '6px', border: '1px dashed rgba(59, 130, 246, 0.3)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.4rem', color: 'var(--accent-blue)', fontWeight: 700, fontSize: '0.84rem' }}>
                <ShieldAlert size={16} />
                <span>CẨM Y VỆ: ĐÃ KHỞI TẠO HỒ SƠ GIÁM SÁT DỰ BÁO (AUDIT BASELINE ACTIVE)</span>
              </div>
              <p style={{ margin: '0.2rem 0 0.5rem 0', fontSize: '0.82rem', lineHeight: '1.5' }}>
                Đây là phiên thẩm định đầu tiên của mã <strong>{report.symbol}</strong> tại ngày <strong>{report.as_of || 'T0'}</strong> (Giá chốt: <strong className="mono">{vn(qs.close || report.price || tp.entry_high)}</strong>). Toàn bộ vùng mua ({vn(tp.entry_low)}–{vn(tp.entry_high)}), mục tiêu ({vn(tp.target_1)} / {vn(tp.target_2)}) và cắt lỗ ({vn(tp.stop_loss)}) đã được ký số lưu vào Sổ Nam Tào.
              </p>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '0.5rem', marginTop: '0.5rem' }}>
                <div style={{ background: 'rgba(0,0,0,0.2)', padding: '0.4rem 0.6rem', borderRadius: '4px' }}>
                  <div className="muted small" style={{ fontSize: '0.7rem' }}>CHU KỲ TỰ ĐỐI CHIẾU</div>
                  <div className="mono" style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-active)' }}>T+2.5, T+5, T+10 phiên</div>
                </div>
                <div style={{ background: 'rgba(0,0,0,0.2)', padding: '0.4rem 0.6rem', borderRadius: '4px' }}>
                  <div className="muted small" style={{ fontSize: '0.7rem' }}>4 CHIỀU THẨM ĐỊNH</div>
                  <div className="mono" style={{ fontSize: '0.78rem', color: 'var(--accent-gold)' }}>Hướng · Biên độ · Thời gian · Kỷ luật</div>
                </div>
                <div style={{ background: 'rgba(0,0,0,0.2)', padding: '0.4rem 0.6rem', borderRadius: '4px' }}>
                  <div className="muted small" style={{ fontSize: '0.7rem' }}>QUY CHẾ CÔNG HUÂN</div>
                  <div className="mono" style={{ fontSize: '0.78rem', color: 'var(--down-color)' }}>Trừ -1đ nếu sai lệch giá &gt; 5%</div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      <div className="thesis-grid">
        {/* KẾ HOẠCH GIAO DỊCH */}
        <Section icon={<Crosshair size={15} color="var(--accent-blue)" />} title="Kế hoạch giao dịch">
          <div className="plan-setup">{tp.setup_type}</div>
          <table className="plan-table">
            <tbody>
              <tr>
                <td>Vùng mua</td>
                <td className="mono">{vn(tp.entry_low)} – {vn(tp.entry_high)}</td>
              </tr>
              <tr>
                <td>Điều kiện kích hoạt</td>
                <td>{tp.entry_trigger}</td>
              </tr>
              <tr>
                <td>Cắt lỗ bắt buộc</td>
                <td>
                  <span className="mono down-color">{vn(tp.stop_loss)}</span>
                  {tp.stop_pct ? <span className="muted"> (−{vn(tp.stop_pct)}%)</span> : null}
                  <div className="muted small" style={{ fontSize: '0.75rem', marginTop: '0.2rem' }}>
                    <strong>Nguyên nhân chốt chặn:</strong> {tp.stop_basis || 'Thủng hỗ trợ nền S1 kèm đệm an toàn 1.5× ATR'}
                  </div>
                </td>
              </tr>
              <tr>
                <td>Mục tiêu 1 / 2</td>
                <td>
                  <span className="mono up-color">{vn(tp.target_1)} / {vn(tp.target_2)}</span>
                  <div className="muted small" style={{ fontSize: '0.75rem', marginTop: '0.2rem' }}>
                    <strong>Nguyên nhân & Cơ sở khai thác:</strong> Vùng cản kỹ thuật POC / Đỉnh cũ & Dải thống kê 68%–95% chu kỳ T+
                  </div>
                </td>
              </tr>
              <tr>
                <td>Tỷ lệ R:R</td>
                <td>
                  <span className="mono" style={{ color: rrColor(rr), fontWeight: 700 }}>1 : {vn(rr)}</span>
                  <span className="muted small"> {rr >= 2 ? 'đạt chuẩn' : rr >= 1.5 ? 'tạm chấp nhận' : 'chưa đạt – chờ giá tốt hơn'}</span>
                </td>
              </tr>
              <tr>
                <td>Tỷ trọng tối đa</td>
                <td className="mono">{vn(tp.max_position_pct, 1)}% NAV</td>
              </tr>
              {tp.scaling_plan && (
                <tr>
                  <td>Giải ngân</td>
                  <td>{tp.scaling_plan}</td>
                </tr>
              )}
              {tp.time_stop && (
                <tr>
                  <td>Dừng theo thời gian</td>
                  <td>{tp.time_stop}</td>
                </tr>
              )}
              {tp.invalidation && (
                <tr>
                  <td>Vô hiệu khi</td>
                  <td>{tp.invalidation}</td>
                </tr>
              )}
            </tbody>
          </table>
        </Section>

        {/* KỊCH BẢN */}
        <Section icon={<Scale size={15} color="var(--accent-gold)" />} title="Kịch bản xác suất">
          {scenarios.map((s, i) => {
            const color = s.name?.includes('🟢') ? 'var(--up-color)' : s.name?.includes('🔴') ? 'var(--down-color)' : 'var(--accent-gold)';
            return (
              <div className="scenario-row" key={i}>
                <div className="scenario-head">
                  <span>{s.name}</span>
                  <span className="mono">
                    {s.probability}% · mục tiêu {vn(s.price_target)}
                  </span>
                </div>
                <div className="prob-bar">
                  <div style={{ width: `${Math.max(0, Math.min(100, s.probability))}%`, background: color }} />
                </div>
                <div className="muted small">
                  <strong>Xác nhận:</strong> {s.trigger} · <strong>Hành động:</strong> {s.action}
                </div>
              </div>
            );
          })}

          {Object.keys(baseRates).length > 0 && (
            <div className="base-rates">
              <div className="thesis-block-title" style={{ marginTop: '0.9rem' }}>
                <Sigma size={14} color="var(--accent-blue)" />
                <span>Xác suất nền lịch sử</span>
              </div>
              <div className="muted small">{qs.base_rates.condition}</div>
              {Object.entries(baseRates).map(([h, s]) => (
                <div key={h} className="small">
                  Sau {h} phiên: <strong>{vn(s.win_rate, 1)}%</strong> lần tăng (bình thường {vn(s.all_days_win_rate, 1)}%), trung vị{' '}
                  {pct(s.median)} · n={s.n}
                </div>
              ))}
            </div>
          )}
        </Section>

        {/* 3 CHỐT CHẶN THOÁT LỆNH: TRẢI RỘNG TOÀN KHUNG (FULL-WIDTH 3 Ô VUÔNG CÂN ĐỐI) */}
        {(stops?.price_stop || stops?.thesis_stop || stops?.time_stop || tp.stop_loss) && (
          <div className="thesis-block stops-full-row">
            <div className="thesis-block-title" style={{ marginBottom: '0.6rem' }}>
              <ShieldAlert size={15} color="var(--down-color)" />
              <span>3 Chốt Chặn Thoát Lệnh (Three-Stop Exit Defense System)</span>
            </div>
            <div className="stops-grid">
              <div className="stop-card price-stop">
                <div className="stop-header">
                  <span className="stop-badge stop-badge-price">PRICE-STOP</span>
                  <span className="stop-title">Cắt Lỗ Kỹ Thuật</span>
                </div>
                <div className="stop-val down-color mono">
                  {vn(priceStop.price || tp.stop_loss)} {priceStop.pct ? `(${priceStop.pct}%)` : tp.stop_pct ? `(-${tp.stop_pct}%)` : ''}
                </div>
                <div className="stop-desc">
                  <strong>Ngưỡng đệm:</strong> {priceStop.desc || priceStop.basis || tp.stop_basis || 'Dưới đáy nến gom lớn nhất ≥ 1.5×ATR14 (tối đa 12%)'}
                </div>
                <div className="stop-action">
                  <strong>Hành động:</strong> {priceStop.action || 'Kích hoạt lệnh dừng tự động (Stop-Order) cắt lỗ 100% vị thế, không do dự'}
                </div>
              </div>

              <div className="stop-card thesis-stop">
                <div className="stop-header">
                  <span className="stop-badge stop-badge-thesis">THESIS-STOP</span>
                  <span className="stop-title">Gãy Luận Điểm</span>
                </div>
                <div className="stop-val mono" style={{ color: '#c084fc' }}>
                  {thesisStop.price ? vn(thesisStop.price) : 'Bẻ Gãy Luận Điểm'}
                </div>
                <div className="stop-desc">
                  <strong>Điều kiện:</strong> {thesisStop.condition || 'Gãy nền hỗ trợ then chốt kèm vol > 1,5× TB20 hoặc luận điểm cơ bản bị bác bỏ'}
                </div>
                <div className="stop-action">
                  <strong>Hành động:</strong> {thesisStop.action || 'Bán chủ động ngay trong phiên, không chờ chạm Price-Stop'}
                </div>
              </div>

              <div className="stop-card time-stop">
                <div className="stop-header">
                  <span className="stop-badge stop-badge-time">TIME-STOP</span>
                  <span className="stop-title">Giới Hạn Kẹp Vốn</span>
                </div>
                <div className="stop-val mono" style={{ color: 'var(--accent-gold)' }}>
                  T+{timeStop.sessions || 10} Phiên
                </div>
                <div className="stop-desc">
                  <strong>Điều kiện:</strong> {timeStop.condition || tp.time_stop || 'Sau T+10 không vượt được mục tiêu 1 và thanh khoản trôi dưới MA20'}
                </div>
                <div className="stop-action">
                  <strong>Hành động:</strong> {timeStop.action || 'Sau T+10 không bứt phá khỏi vùng nền thì hạ 50% tỷ trọng, sau T+15 tất toán để thu hồi vốn'}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* LUẬN ĐIỂM */}
        <Section icon={<Compass size={15} color="var(--up-color)" />} title="Luận điểm ủng hộ" className="bull">
          <ul>
            {(thesis.bull_case || []).map((x, i) => (
              <li key={i}>{x}</li>
            ))}
          </ul>
        </Section>
        <Section icon={<ShieldAlert size={15} color="var(--down-color)" />} title="Luận điểm phản biện" className="bear">
          <ul>
            {(thesis.bear_case || []).map((x, i) => (
              <li key={i}>{x}</li>
            ))}
          </ul>
        </Section>
      </div>

      {(thesis.key_question || thesis.priced_in || thesis.variant_view) && (
        <div className="thesis-questions">
          {thesis.key_question && (
            <p>
              <strong>Câu hỏi then chốt:</strong> {renderInlineFormatting(thesis.key_question)}
            </p>
          )}
          {thesis.priced_in && (
            <p>
              <strong>Giá đang phản ánh:</strong> {renderInlineFormatting(thesis.priced_in)}
            </p>
          )}
          {thesis.variant_view && (
            <p>
              <strong>Góc nhìn khác biệt:</strong> {renderInlineFormatting(thesis.variant_view)}
            </p>
          )}
        </div>
      )}

      {/* MA TRẬN 6 GIẢ THUYẾT NGUYÊN NHÂN BIẾN ĐỘNG GIÁ */}
      {hypotheses.length > 0 && (
        <div className="thesis-block" style={{ marginTop: '1.2rem' }}>
          <div className="thesis-block-title">
            <Scale size={16} color="var(--accent-gold)" />
            <span>Ma Trận 6 Giả Thuyết Biến Động Giá (Causal Hypotheses Matrix)</span>
          </div>
          <div className="data-table-wrapper" style={{ overflowX: 'auto', marginTop: '0.6rem' }}>
            <table className="fiin-table hypo-table">
              <thead>
                <tr>
                  <th style={{ width: '55px' }}>MÃ</th>
                  <th style={{ width: '220px' }}>GIẢ THUYẾT NGUYÊN NHÂN</th>
                  <th style={{ width: '130px' }}>XÁC SUẤT</th>
                  <th>ĐỘNG LỰC / BẰNG CHỨNG HỖ TRỢ</th>
                  <th>ĐIỀU KIỆN KIỂM CHỨNG & NGƯỠNG PHỦ ĐỊNH</th>
                  <th style={{ width: '110px' }}>PHÁN QUYẾT</th>
                </tr>
              </thead>
              <tbody>
                {hypotheses.map((h, i) => {
                  const probPct = Math.round((h.prob || 0) * 100);
                  const barColor = probPct >= 35 ? 'var(--up-color)' : probPct >= 15 ? 'var(--accent-blue)' : probPct >= 8 ? 'var(--accent-gold)' : 'var(--text-secondary)';
                  return (
                    <tr key={i}>
                      <td className="mono" style={{ fontWeight: 700, color: barColor }}>{h.id}</td>
                      <td><strong>{h.name}</strong></td>
                      <td>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <span className="mono" style={{ fontWeight: 700, color: barColor }}>{probPct}%</span>
                          <span className="muted small">Điểm: {h.likelihood_score || 0}</span>
                        </div>
                        <div className="hypo-bar-container">
                          <div className="hypo-bar" style={{ width: `${probPct}%`, background: barColor }} />
                        </div>
                      </td>
                      <td className="small">{renderInlineFormatting(h.driver)}</td>
                      <td className="small">{renderInlineFormatting(h.verifiable_by)}</td>
                      <td>
                        <span className={`tag ${
                          h.verdict === 'Ủng hộ mạnh' ? 'score-high' :
                          h.verdict === 'Khả năng cao' ? 'score-mid' :
                          h.verdict === 'Trung bình' ? 'c-yellow' : 'c-red'
                        }`}>
                          {h.verdict}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* KẾ HOẠCH TÁC CHIẾN T+2,5 & CHỐT LỜI 3 NHỊP */}
      {(tac.profit_taking_3tier || tac.intraday_clock || tac.checklist_5m) && (
        <div className="thesis-block" style={{ marginTop: '1.2rem' }}>
          <div className="thesis-block-title">
            <CalendarClock size={16} color="var(--accent-blue)" />
            <span>Kế Hoạch Tác Chiến T+2,5 & Công Thức Chốt Lời 3 Nhịp</span>
          </div>

          {/* 3 Khung giờ tác chiến */}
          {tac.intraday_clock && (
            <div className="clock-grid" style={{ marginTop: '0.6rem' }}>
              <div className="clock-card clock-red">
                <div className="clock-time" style={{ color: 'var(--down-color)', fontWeight: 700 }}>
                  🕘 09h00 – 10h30: BẪY HƯNG PHẤN
                </div>
                <div className="clock-desc small muted">
                  {tac.intraday_clock['09h00_10h30'] || 'Đứng ngoài quan sát, tuyệt đối không mua đuổi Gap Up đầu phiên.'}
                </div>
              </div>
              <div className="clock-card clock-yellow">
                <div className="clock-time" style={{ color: 'var(--accent-gold)', fontWeight: 700 }}>
                  🕐 13h00 – 13h45: THỬ LỬA HÀNG T+2,5
                </div>
                <div className="clock-desc small muted">
                  {tac.intraday_clock['13h00_13h45'] || 'Đánh giá tốc độ hấp thụ nguồn cung chốt lời của phiên nổ vol.'}
                </div>
              </div>
              <div className="clock-card clock-green">
                <div className="clock-time" style={{ color: 'var(--up-color)', fontWeight: 700 }}>
                  🕑 13h45 – 14h25: KHUNG GIỜ PHÁN QUYẾT
                </div>
                <div className="clock-desc small muted">
                  {tac.intraday_clock['13h45_14h25'] || 'Thời điểm bấm nút duy nhất sau 14h00 theo nến đóng cửa ngày.'}
                </div>
              </div>
            </div>
          )}

          {/* Bảng chốt lời 3 nhịp */}
          {tac.profit_taking_3tier && (
            <div className="data-table-wrapper" style={{ marginTop: '0.8rem' }}>
              <div className="table-caption">
                <span>Bản Thiết Kế Chốt Lời 3 Nhịp (30% - 50% - 20%)</span>
                <span className="tag score-high">KỶ LUẬT BẢO TOÀN LỢI NHUẬN</span>
              </div>
              <table className="fiin-table">
                <thead>
                  <tr>
                    <th style={{ width: '180px' }}>NHỊP CHỐT LỜI</th>
                    <th style={{ width: '160px' }}>MỨC GIÁ / THÔNG SỐ</th>
                    <th>QUY TẮC THỰC CHIẾN</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td style={{ color: 'var(--up-color)', fontWeight: 700 }}>🎯 Nhịp 1 (Bán 30%)</td>
                    <td className="mono up-color">{vn(tac.profit_taking_3tier.tier1_sell_30pct?.price)}</td>
                    <td className="small">{renderInlineFormatting(tac.profit_taking_3tier.tier1_sell_30pct?.rule)}</td>
                  </tr>
                  <tr>
                    <td style={{ color: 'var(--accent-gold)', fontWeight: 700 }}>🛡️ Nhịp 2 (Giữ 50%)</td>
                    <td className="mono" style={{ color: 'var(--accent-gold)' }}>
                      Trailing {vn(tac.profit_taking_3tier.tier2_hold_50pct_trailing?.trailing_2_0pct)} – {vn(tac.profit_taking_3tier.tier2_hold_50pct_trailing?.trailing_1_5pct)}
                    </td>
                    <td className="small">{renderInlineFormatting(tac.profit_taking_3tier.tier2_hold_50pct_trailing?.rule)}</td>
                  </tr>
                  <tr>
                    <td style={{ color: 'var(--accent-blue)', fontWeight: 700 }}>🚀 Nhịp 3 (Giữ 20%)</td>
                    <td className="mono" style={{ color: 'var(--accent-blue)' }}>
                      Mục tiêu 2: {vn(tac.profit_taking_3tier.tier3_hold_20pct_fomo?.target_2)}
                    </td>
                    <td className="small">{renderInlineFormatting(tac.profit_taking_3tier.tier3_hold_20pct_fomo?.rule)}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          )}

          {/* Checklist 5 phút */}
          {Array.isArray(tac.checklist_5m) && tac.checklist_5m.length > 0 && (
            <div className="data-table-wrapper" style={{ marginTop: '0.8rem' }}>
              <div className="table-caption">
                <span>📋 Checklist 5 Phút Trước Khi Bấm Lệnh</span>
                <span className="tag score-high">KIỂM SOÁT AN TOÀN TRƯỚC LỆNH</span>
              </div>
              <table className="fiin-table">
                <thead>
                  <tr>
                    <th style={{ width: '220px' }}>TIÊU CHÍ AN TOÀN</th>
                    <th style={{ width: '180px' }}>TRẠNG THÁI</th>
                    <th>CHI TIẾT KIỂM TRA NHANH</th>
                  </tr>
                </thead>
                <tbody>
                  {tac.checklist_5m.map((c, ci) => (
                    <tr key={ci}>
                      <td><strong>{c.step}</strong></td>
                      <td>
                        <span className={`tag ${
                          c.status?.includes('🟢') ? 'score-high' :
                          c.status?.includes('🟡') ? 'c-yellow' : 'c-red'
                        }`}>
                          {c.status}
                        </span>
                      </td>
                      <td className="small">{renderInlineFormatting(c.detail)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* ĐỌC VỊ TẠO LẬP & VI CẤU TRÚC BẢNG ĐIỆN */}
      {(tac.archetype || tac.spring_analysis || tac.order_book_analysis || tac.foreign_cycle_analysis) && (
        <div className="thesis-block" style={{ marginTop: '1.2rem' }}>
          <div className="thesis-block-title">
            <Activity size={16} color="var(--accent-blue)" />
            <span>Đọc Vị Tạo Lập, Cú Rũ Hàng Spring & Vi Cấu Trúc Bảng Điện</span>
          </div>
          <div className="action-grid-2" style={{ marginTop: '0.6rem' }}>
            {tac.archetype && (
              <div className="action-card" style={{ background: 'rgba(47, 129, 247, 0.05)', borderColor: 'rgba(47, 129, 247, 0.25)' }}>
                <div className="action-card-header" style={{ color: 'var(--accent-blue)' }}>
                  🏷️ ĐỊNH DANH BẢN CHẤT TẠO LẬP
                </div>
                <p style={{ fontSize: '0.82rem' }}>
                  <strong>{tac.archetype.name}</strong> ({tac.archetype.group_key}): {tac.archetype.desc}
                </p>
                <div className="small muted" style={{ marginTop: '4px' }}>
                  Chiến thuật: {tac.archetype.tactics} · Cắt lỗ mẫu: {tac.archetype.max_stop_pct}% · Tỷ trọng tối đa: {tac.archetype.max_nav_pct}% NAV
                </div>
              </div>
            )}
            {tac.spring_analysis && (
              <div className="action-card" style={{ background: 'rgba(0, 192, 118, 0.05)', borderColor: 'rgba(0, 192, 118, 0.25)' }}>
                <div className="action-card-header" style={{ color: 'var(--up-color)' }}>
                  🌪️ THẨM ĐỊNH CÚ SPRING RŨ HÀNG
                </div>
                <p style={{ fontSize: '0.82rem' }}>{renderInlineFormatting(tac.spring_analysis)}</p>
              </div>
            )}
          </div>
          {(tac.order_book_analysis || tac.foreign_cycle_analysis) && (
            <div className="data-table-wrapper" style={{ marginTop: '0.6rem', padding: '0.8rem', fontSize: '0.82rem', lineHeight: '1.6' }}>
              {tac.order_book_analysis && (
                <p>• <strong>Tường đỡ Sổ lệnh (Order Book):</strong> {renderInlineFormatting(tac.order_book_analysis)}</p>
              )}
              {tac.foreign_cycle_analysis && (
                <p style={{ marginTop: '4px' }}>• <strong>Chu kỳ Dòng tiền Khối ngoại & Tự doanh:</strong> {renderInlineFormatting(tac.foreign_cycle_analysis)}</p>
              )}
            </div>
          )}
        </div>
      )}

      {/* VÙNG GIÁ + BỐI CẢNH ĐỊNH LƯỢNG */}
      {(qs.supports || qs.resistances) && (
        <div className="thesis-grid">
          <Section icon={<Crosshair size={15} color="var(--accent-blue)" />} title="Vùng giá then chốt (tính từ dữ liệu)">
            <table className="plan-table">
              <tbody>
                {[...(qs.resistances || [])].reverse().map((r, i) => (
                  <tr key={`r${i}`}>
                    <td className="mono up-color">{vn(r.price)}</td>
                    <td>
                      Kháng cự {r.strength?.toLowerCase()} ({pct(r.distance_pct)})<div className="muted small">{r.basis}</div>
                    </td>
                  </tr>
                ))}
                {[...(qs.supports || [])].map((s, i) => (
                  <tr key={`s${i}`}>
                    <td className="mono down-color">{vn(s.price)}</td>
                    <td>
                      Hỗ trợ {s.strength?.toLowerCase()} ({pct(s.distance_pct)})<div className="muted small">{s.basis}</div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Section>
          <Section icon={<Sigma size={15} color="var(--accent-gold)" />} title="Bối cảnh định lượng">
            <table className="plan-table">
              <tbody>
                <tr><td>Thị trường</td><td>{qs.market_status || 'N/A'} · tỷ trọng cổ phiếu {qs.equity_allocation || 'N/A'}</td></tr>
                <tr><td>Xu hướng mã</td><td>{qs.trend}</td></tr>
                <tr><td>Sức mạnh tương đối</td><td>{qs.relative_strength || 'N/A'}{qs.sector_rank ? ` · hạng ${qs.sector_rank} trong ngành` : ''}</td></tr>
                <tr><td>Dòng tiền</td><td>{qs.flow}</td></tr>
                <tr><td>Thanh khoản TB 20 phiên</td><td className="mono">{vn(qs.avg_value_20d_bn, 1)} tỷ/phiên</td></tr>
                <tr><td>Khối ngoại phiên gần nhất</td><td className="mono">{qs.foreign_net_bn === null || qs.foreign_net_bn === undefined ? 'N/A' : `${qs.foreign_net_bn > 0 ? '+' : ''}${vn(qs.foreign_net_bn)} tỷ`}</td></tr>
                <tr><td>Biến động (ATR)</td><td className="mono">{vn(qs.atr_pct)}%/phiên · cách đỉnh 52 tuần {pct(qs.from_52w_high_pct)}</td></tr>
                {qs.returns && (
                  <tr><td>Hiệu suất</td><td className="mono small">1T {pct(qs.returns['1m'])} · 3T {pct(qs.returns['3m'])} · 6T {pct(qs.returns['6m'])} · 1N {pct(qs.returns['1y'])}</td></tr>
                )}
              </tbody>
            </table>
          </Section>
        </div>
      )}

      {/* RỦI RO & THEO DÕI */}
      <div className="thesis-grid">
        {risks.length > 0 && (
          <Section icon={<ShieldAlert size={15} color="var(--down-color)" />} title="Rủi ro chính & pre-mortem">
            <table className="plan-table">
              <tbody>
                {risks.map((r, i) => (
                  <tr key={i}>
                    <td>
                      <span className={`sev sev-${r.severity === 'Cao' ? 'high' : r.severity === 'Thấp' ? 'low' : 'mid'}`}>{r.severity}</span>
                    </td>
                    <td>
                      <strong>{r.risk}</strong>
                      {r.signal ? <div className="muted small">Dấu hiệu: {r.signal}</div> : null}
                      {r.response ? <div className="muted small">Xử lý: {r.response}</div> : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Section>
        )}
        <Section icon={<ListChecks size={15} color="var(--accent-blue)" />} title="Checklist theo dõi">
          <ul>
            {monitoring.map((m, i) => (
              <li key={i}>{m}</li>
            ))}
          </ul>
          {catalysts.length > 0 && (
            <>
              <div className="thesis-block-title" style={{ marginTop: '0.9rem' }}>
                <CalendarClock size={14} color="var(--accent-gold)" />
                <span>Chất xúc tác & lịch sự kiện</span>
              </div>
              <ul>
                {catalysts.map((c, i) => (
                  <li key={i}>
                    <strong>{c.timing}</strong> — {c.event} <span className="muted">({c.impact})</span>
                  </li>
                ))}
              </ul>
            </>
          )}
        </Section>
      </div>

      {(gaps.length > 0 || notes.length > 0 || sources.length > 0) && (
        <div className="thesis-footer">
          {notes.length > 0 && (
            <div>
              <div className="thesis-block-title">
                <TriangleAlert size={14} color="var(--accent-gold)" />
                <span>Hệ thống đã tự kiểm tra & điều chỉnh</span>
              </div>
              <ul className="small">
                {notes.map((n, i) => (
                  <li key={i}>{n}</li>
                ))}
              </ul>
            </div>
          )}
          {gaps.length > 0 && (
            <div>
              <div className="thesis-block-title">
                <TriangleAlert size={14} color="var(--text-secondary)" />
                <span>Dữ liệu còn thiếu</span>
              </div>
              <ul className="small muted">
                {gaps.map((g, i) => (
                  <li key={i}>{g}</li>
                ))}
              </ul>
            </div>
          )}
          {sources.length > 0 && (
            <div>
              <div className="thesis-block-title">
                <ExternalLink size={14} color="var(--accent-blue)" />
                <span>Nguồn tra cứu</span>
              </div>
              <ul className="small">
                {sources.map((s, i) => (
                  <li key={i}>
                    <a href={s.url} target="_blank" rel="noreferrer" className="chat-link">
                      {s.title}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
      <p className="muted small" style={{ marginTop: '1rem' }}>
        Phân tích mang tính tham khảo, không phải khuyến nghị mua/bán của tổ chức được cấp phép. Nhà đầu tư tự chịu trách nhiệm với
        quyết định của mình.
      </p>
    </div>
  );
}
