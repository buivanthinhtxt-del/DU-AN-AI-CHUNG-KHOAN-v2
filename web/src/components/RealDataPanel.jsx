import React, { useCallback, useEffect, useState } from 'react';
import { CalendarClock, FileSearch, Fish, RefreshCw, AlertTriangle, CheckCircle2 } from 'lucide-react';
import { fetchCashflowQuality, fetchCorporateEvents, fetchSharkFlow } from '../services/apiClient';

const VERDICT_LABEL = {
  TOT: { text: 'Lợi nhuận chất lượng tốt', cls: 'rd-good' },
  TRUNG_BINH: { text: 'Chất lượng trung bình', cls: 'rd-warn' },
  YEU: { text: 'Nguy cơ lãi trên giấy', cls: 'rd-bad' },
  KHONG_AP_DUNG: { text: 'Không áp dụng (DN tài chính)', cls: 'rd-muted' },
  KHONG_DU_DU_LIEU: { text: 'Chưa đủ 4 quý dữ liệu', cls: 'rd-muted' },
};

const STANCE_LABEL = {
  NE_TRUOC_CHOT: { text: 'Né trước chốt', cls: 'rd-bad' },
  BAT_SAU_CHIA: { text: 'Bắt sau chia', cls: 'rd-good' },
  CO_TUC_TIEN: { text: 'Cổ tức tiền mặt sắp GDKHQ', cls: 'rd-warn' },
  KHONG_CO_SU_KIEN: { text: 'Không có sự kiện quyền', cls: 'rd-muted' },
  KHONG_RO: { text: 'Không rõ', cls: 'rd-muted' },
};

const SIGNAL_CLS = {
  CA_MAP_GOM_CA_CON_BAN: 'rd-good',
  CA_MAP_MUA_RONG: 'rd-good',
  CA_MAP_XA_CA_CON_MUA: 'rd-bad',
  CA_MAP_BAN_RONG: 'rd-bad',
  TRUNG_TINH: 'rd-muted',
};

const fmt = (v, digits = 1) =>
  v === null || v === undefined ? '—' : Number(v).toLocaleString('vi-VN', { maximumFractionDigits: digits });
const signed = (v) => (v === null || v === undefined ? '—' : `${v > 0 ? '+' : ''}${fmt(v, 2)}`);

function useLoader(loader, symbol) {
  const [state, setState] = useState({ loading: true, data: null, error: null });
  const run = useCallback(
    (...args) => {
      let alive = true;
      setState((s) => ({ ...s, loading: true, error: null }));
      loader(symbol, ...args)
        .then((data) => alive && setState({ loading: false, data, error: null }))
        .catch((err) => alive && setState({ loading: false, data: null, error: err.message }));
      return () => {
        alive = false;
      };
    },
    [loader, symbol],
  );
  useEffect(() => run(), [run]);
  return [state, run];
}

function Card({ icon: Icon, title, badge, source, children, onRefresh, loading }) {
  return (
    <section className="rd-card">
      <header className="rd-card-head">
        <div className="rd-card-title">
          <Icon size={16} />
          <h3>{title}</h3>
          {badge}
        </div>
        {onRefresh && (
          <button type="button" className="rd-refresh" onClick={onRefresh} disabled={loading} aria-label="Tải lại">
            <RefreshCw size={13} className={loading ? 'ws-spin' : ''} />
          </button>
        )}
      </header>
      {children}
      {source && <footer className="rd-source">Nguồn: {source}</footer>}
    </section>
  );
}

function Status({ state, emptyText }) {
  if (state.loading) return <div className="rd-status">Đang tải dữ liệu thật…</div>;
  if (state.error) return <div className="rd-status rd-bad">Lỗi: {state.error}</div>;
  if (state.data && state.data.available === false)
    return <div className="rd-status rd-muted">{emptyText}{state.data.error ? ` (${state.data.error})` : ''}</div>;
  return null;
}

function CashflowCard({ symbol }) {
  const [state, reload] = useLoader(fetchCashflowQuality, symbol);
  const d = state.data;
  const ok = d?.available;
  const v = ok ? VERDICT_LABEL[d.verdict] || VERDICT_LABEL.KHONG_DU_DU_LIEU : null;
  return (
    <Card
      icon={FileSearch}
      title="Chất lượng lợi nhuận (CFO vs LNST)"
      badge={v && <span className={`rd-badge ${v.cls}`}>{v.text}</span>}
      source={ok ? `${d.source} · kỳ ${d.latest_period} · ${d.unit}` : null}
      onRefresh={() => reload()}
      loading={state.loading}
    >
      <Status state={state} emptyText="Chưa có BCTC quý cho mã này." />
      {ok && !state.loading && (
        <>
          <div className="rd-kpis">
            <div><span>CFO 4 quý</span><strong>{fmt(d.cfo_ttm_bn)} tỷ</strong></div>
            <div><span>LNST 4 quý</span><strong>{fmt(d.npat_ttm_bn)} tỷ</strong></div>
            <div><span>CFO / LNST</span><strong>{d.cfo_to_npat_ttm === null ? '—' : `${fmt(d.cfo_to_npat_ttm, 2)}x`}</strong></div>
            <div><span>Quý CFO âm (4Q)</span><strong>{d.negative_cfo_quarters_4q}/4</strong></div>
          </div>
          {d.flags?.length > 0 ? (
            <ul className="rd-flags">
              {d.flags.map((f) => (
                <li key={f}><AlertTriangle size={12} /> {f}</li>
              ))}
            </ul>
          ) : (
            <div className="rd-ok"><CheckCircle2 size={13} /> Không phát hiện cờ đỏ ở CFO, phải thu, tồn kho.</div>
          )}
          <div className="rd-table-wrap">
            <table className="rd-table">
              <thead>
                <tr><th>Kỳ</th><th>Doanh thu</th><th>LNST mẹ</th><th>CFO</th><th>Phải thu</th><th>Tồn kho</th></tr>
              </thead>
              <tbody>
                {d.quarters.map((q) => (
                  <tr key={q.period}>
                    <td>{q.period}</td>
                    <td>{fmt(q.revenue, 0)}</td>
                    <td>{fmt(q.npat_parent ?? q.npat, 0)}</td>
                    <td className={q.cfo < 0 ? 'rd-bad' : ''}>{fmt(q.cfo, 0)}</td>
                    <td>{fmt(q.receivables, 0)}</td>
                    <td>{fmt(q.inventory, 0)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </Card>
  );
}

function EventsCard({ symbol }) {
  const [state, reload] = useLoader(fetchCorporateEvents, symbol);
  const d = state.data;
  const ok = d?.available;
  const s = d ? STANCE_LABEL[d.stance] || STANCE_LABEL.KHONG_RO : null;
  const rows = ok ? [...(d.upcoming || []), ...(d.recent || [])] : [];
  return (
    <Card
      icon={CalendarClock}
      title="Lịch sự kiện quyền (GDKHQ)"
      badge={s && <span className={`rd-badge ${s.cls}`}>{s.text}</span>}
      source={ok ? `${d.source} · ±${d.window_days} ngày quanh ${d.as_of}` : null}
      onRefresh={() => reload()}
      loading={state.loading}
    >
      <Status state={state} emptyText="Không tải được lịch sự kiện quyền." />
      {d?.advice && !state.loading && <p className="rd-advice">{d.advice}</p>}
      {rows.length > 0 && !state.loading && (
        <ul className="rd-events">
          {rows.map((e) => (
            <li key={`${e.type}-${e.ex_date}-${e.note}`}>
              <span className="rd-ev-date">{e.ex_date}</span>
              <span className="rd-ev-type">{e.label}</span>
              <span className="rd-ev-note">{e.note}</span>
              <span className="rd-ev-days">{e.days_to_ex >= 0 ? `còn ${e.days_to_ex} ngày` : `${-e.days_to_ex} ngày trước`}</span>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

function SharkCard({ symbol }) {
  const [state, reload] = useLoader(fetchSharkFlow, symbol);
  const d = state.data;
  const ok = d?.available;
  return (
    <Card
      icon={Fish}
      title="Shark Tracker — khớp lệnh từng lô thật"
      badge={ok && <span className={`rd-badge ${SIGNAL_CLS[d.signal] || 'rd-muted'}`}>{d.signal_note}</span>}
      source={ok ? `${d.source} · phiên ${d.session_date} · ${fmt(d.tick_count, 0)} lệnh · phủ ${fmt(d.coverage_pct)}% KL phiên` : null}
      onRefresh={() => reload(true)}
      loading={state.loading}
    >
      {state.loading && <div className="rd-status">Đang tải khớp lệnh từng lô (mã thanh khoản cao có thể mất 30–45 giây)…</div>}
      {!state.loading && <Status state={state} emptyText="Không có dữ liệu khớp lệnh." />}
      {ok && !state.loading && (
        <>
          <div className="rd-tiers">
            {['shark', 'wolf', 'sheep'].map((k) => {
              const t = d.tiers[k];
              return (
                <div key={k} className="rd-tier">
                  <div className="rd-tier-name">{t.label} <small>({t.range})</small></div>
                  <div className={`rd-tier-net ${t.net_value_bn > 0 ? 'rd-good' : t.net_value_bn < 0 ? 'rd-bad' : ''}`}>
                    {signed(t.net_value_bn)} tỷ
                  </div>
                  <div className="rd-tier-sub">
                    Mua {fmt(t.buy_value_bn, 2)} · Bán {fmt(t.sell_value_bn, 2)} · ATO/ATC {fmt(t.unknown_value_bn, 2)} · {fmt(t.count, 0)} lệnh
                  </div>
                </div>
              );
            })}
          </div>
          {d.coverage_pct !== null && d.coverage_pct < 90 && (
            <div className="rd-status rd-warn">
              Chỉ phân tích {fmt(d.coverage_pct)}% khối lượng phiên (giới hạn số trang tải từ nguồn) — các lệnh sớm nhất trong phiên chưa được tính.
            </div>
          )}
          <p className="rd-caveat">{d.caveat}</p>
        </>
      )}
    </Card>
  );
}

export default function RealDataPanel({ symbol }) {
  return (
    <div className="rd-grid">
      <CashflowCard key={`cf-${symbol}`} symbol={symbol} />
      <EventsCard key={`ev-${symbol}`} symbol={symbol} />
      <SharkCard key={`sh-${symbol}`} symbol={symbol} />
    </div>
  );
}
