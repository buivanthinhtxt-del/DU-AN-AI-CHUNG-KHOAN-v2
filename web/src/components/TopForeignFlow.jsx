import React, { useEffect, useState } from 'react';
import { Globe, TrendingUp, TrendingDown, RefreshCw } from 'lucide-react';

const vn = (x, nd = 2) => {
  const n = Number(x);
  if (x === null || x === undefined || Number.isNaN(n)) return '—';
  return n.toLocaleString('vi-VN', { minimumFractionDigits: nd, maximumFractionDigits: nd });
};

export default function TopForeignFlow({ onSelectSymbol }) {
  const [data, setData] = useState({ top_buy: [], top_sell: [], updated_at: '' });
  const [loading, setLoading] = useState(false);

  const fetchTopForeign = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/realtime/top-foreign');
      if (res.ok) {
        const json = await res.json();
        setData(json);
      }
    } catch (e) {
      console.error('Lỗi tải Top Khối Ngoại:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTopForeign();
    const timer = setInterval(fetchTopForeign, 30000);
    return () => clearInterval(timer);
  }, []);

  const hasData = (data.top_buy && data.top_buy.length > 0) || (data.top_sell && data.top_sell.length > 0);

  return (
    <div className="glass-panel" style={{ padding: '0.85rem 1rem', marginBottom: '1rem', border: '1px solid rgba(255,255,255,0.08)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem', flexWrap: 'wrap', gap: '0.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Globe size={18} color="var(--accent-blue)" />
          <span style={{ fontWeight: 700, fontSize: '0.92rem', letterSpacing: '0.5px', textTransform: 'uppercase' }}>
            Top Khối Ngoại Giao Dịch Toàn Sàn (Real-time)
          </span>
          <span className="thesis-chip" style={{ fontSize: '0.72rem', padding: '0.15rem 0.45rem' }}>
            Nguồn: Vietcap Data
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          {data.updated_at && (
            <span className="muted small" style={{ fontSize: '0.75rem' }}>
              Cập nhật: {data.updated_at}
            </span>
          )}
          <button
            onClick={fetchTopForeign}
            disabled={loading}
            className="btn-icon"
            title="Làm mới dòng tiền ngoại"
            style={{ padding: '0.2rem 0.4rem', background: 'transparent', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '4px', cursor: 'pointer', color: 'var(--text-secondary)' }}
          >
            <RefreshCw size={13} className={loading ? 'spin' : ''} />
          </button>
        </div>
      </div>

      {!hasData ? (
        <div className="muted small" style={{ textAlign: 'center', padding: '1rem' }}>
          {loading ? 'Đang nạp luồng giao dịch khối ngoại từ Vietcap...' : 'Chưa có giao dịch khối ngoại trong phiên hôm nay'}
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
          {/* CỘT TOP MUA RÒNG */}
          <div style={{ background: 'rgba(34, 197, 94, 0.04)', borderRadius: '6px', border: '1px solid rgba(34, 197, 94, 0.2)', padding: '0.6rem 0.8rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--up-color)', fontWeight: 700, fontSize: '0.82rem', marginBottom: '0.5rem' }}>
              <TrendingUp size={15} />
              <span>TOP 5 MUA RÒNG NHẤT (TỶ ĐỒNG)</span>
            </div>
            <table className="fiin-table" style={{ fontSize: '0.78rem', width: '100%' }}>
              <thead>
                <tr>
                  <th>MÃ</th>
                  <th style={{ textAlign: 'right' }}>GIÁ</th>
                  <th style={{ textAlign: 'right' }}>KL RÒNG</th>
                  <th style={{ textAlign: 'right' }}>GT RÒNG</th>
                </tr>
              </thead>
              <tbody>
                {(data.top_buy || []).map((row, i) => (
                  <tr key={i} onClick={() => onSelectSymbol && onSelectSymbol(row.symbol)} style={{ cursor: onSelectSymbol ? 'pointer' : 'default' }}>
                    <td style={{ fontWeight: 700, color: 'var(--text-active)' }}>
                      <span className="mono">{row.symbol}</span>
                    </td>
                    <td style={{ textAlign: 'right' }} className="mono">{vn(row.price)}</td>
                    <td style={{ textAlign: 'right', color: 'var(--up-color)' }} className="mono">
                      +{vn(row.net_vol, 0)}
                    </td>
                    <td style={{ textAlign: 'right', fontWeight: 700, color: 'var(--up-color)' }} className="mono">
                      +{vn(row.net_val_bn)} tỷ
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* CỘT TOP BÁN RÒNG */}
          <div style={{ background: 'rgba(239, 68, 68, 0.04)', borderRadius: '6px', border: '1px solid rgba(239, 68, 68, 0.2)', padding: '0.6rem 0.8rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--down-color)', fontWeight: 700, fontSize: '0.82rem', marginBottom: '0.5rem' }}>
              <TrendingDown size={15} />
              <span>TOP 5 BÁN RÒNG NHẤT (TỶ ĐỒNG)</span>
            </div>
            <table className="fiin-table" style={{ fontSize: '0.78rem', width: '100%' }}>
              <thead>
                <tr>
                  <th>MÃ</th>
                  <th style={{ textAlign: 'right' }}>GIÁ</th>
                  <th style={{ textAlign: 'right' }}>KL RÒNG</th>
                  <th style={{ textAlign: 'right' }}>GT RÒNG</th>
                </tr>
              </thead>
              <tbody>
                {(data.top_sell || []).map((row, i) => (
                  <tr key={i} onClick={() => onSelectSymbol && onSelectSymbol(row.symbol)} style={{ cursor: onSelectSymbol ? 'pointer' : 'default' }}>
                    <td style={{ fontWeight: 700, color: 'var(--text-active)' }}>
                      <span className="mono">{row.symbol}</span>
                    </td>
                    <td style={{ textAlign: 'right' }} className="mono">{vn(row.price)}</td>
                    <td style={{ textAlign: 'right', color: 'var(--down-color)' }} className="mono">
                      {vn(row.net_vol, 0)}
                    </td>
                    <td style={{ textAlign: 'right', fontWeight: 700, color: 'var(--down-color)' }} className="mono">
                      {vn(row.net_val_bn)} tỷ
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
