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
} from 'lucide-react';

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
        <div className="verdict-action" style={{ color: actionColor }}>
          {summary.action || 'Quan sát'}
          <span className="verdict-sub">
            {summary.stance} · Độ tin cậy {summary.confidence}
          </span>
        </div>
        <p className="verdict-thesis">{verdict.core_thesis}</p>
      </div>

      <div className="verdict-grid">
        <div className="verdict-cell">
          <span className="verdict-label">Người chưa có cổ phiếu</span>
          <p>{verdict.for_new_buyers || '—'}</p>
        </div>
        <div className="verdict-cell">
          <span className="verdict-label">Người đang nắm giữ</span>
          <p>{verdict.for_holders || '—'}</p>
        </div>
        <div className="verdict-cell">
          <span className="verdict-label">1–4 tuần tới</span>
          <p>{verdict.short_term || '—'}</p>
        </div>
        <div className="verdict-cell">
          <span className="verdict-label">3–12 tháng</span>
          <p>{verdict.medium_term || '—'}</p>
        </div>
      </div>
      {verdict.decision_level && (
        <div className="decision-level">
          <Crosshair size={14} /> <strong>Mức giá quyết định:</strong> {verdict.decision_level}
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
                  {tp.stop_basis ? <div className="muted small">{tp.stop_basis}</div> : null}
                </td>
              </tr>
              <tr>
                <td>Mục tiêu 1 / 2</td>
                <td className="mono up-color">{vn(tp.target_1)} / {vn(tp.target_2)}</td>
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
              <strong>Câu hỏi then chốt:</strong> {thesis.key_question}
            </p>
          )}
          {thesis.priced_in && (
            <p>
              <strong>Giá đang phản ánh:</strong> {thesis.priced_in}
            </p>
          )}
          {thesis.variant_view && (
            <p>
              <strong>Góc nhìn khác biệt:</strong> {thesis.variant_view}
            </p>
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
