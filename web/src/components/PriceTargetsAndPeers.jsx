import React from 'react';
import { Target, Users } from 'lucide-react';
import { addTradingDays } from '../services/tradingDays';

export default function PriceTargetsAndPeers({
  predictions,
  lastHistoryDate,
  loadingAI,
  peers,
  symbol,
  sector,
  onSelectSymbol,
}) {
  const formatPredictionDate = (daysFuture) => {
    if (!lastHistoryDate) return '';
    return addTradingDays(lastHistoryDate, daysFuture).formatted;
  };

  const peerEntries = peers ? Object.entries(peers) : [];

  return (
    <div className="glass-panel predictions-card" style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      <div>
        <div className="section-title">
          <Target size={18} color="var(--accent-gold)" />
          <h2>Vùng Giá Dự Báo (Price Targets)</h2>
        </div>
        <div className="predictions-table-container">
          <table className="predictions-table">
            <thead>
              <tr>
                <th>Khung Thời Gian</th>
                <th>Kháng Cự (High)</th>
                <th>Hỗ Trợ (Low)</th>
                <th>Động Lực / Ghi Chú</th>
              </tr>
            </thead>
            <tbody>
              {predictions.map((p, i) => (
                <tr key={i}>
                  <td>
                    <span className="date-label">Ngày {formatPredictionDate(p.days_future)}</span>
                    <span className="tf-label">{p.timeframe || `T+${p.days_future}`}</span>
                  </td>
                  <td className="high-val">{p.high}</td>
                  <td className="low-val">{p.low}</td>
                  <td
                    style={{
                      fontSize: '0.75rem',
                      color: 'var(--text-secondary)',
                      fontStyle: 'italic',
                      lineHeight: '1.4',
                      maxWidth: '180px',
                    }}
                  >
                    {p.reason || '-'}
                  </td>
                </tr>
              ))}
              {predictions.length === 0 && !loadingAI && (
                <tr>
                  <td colSpan="4" style={{ textAlign: 'center', color: 'var(--text-secondary)' }}>
                    Chưa có dữ liệu dự báo
                  </td>
                </tr>
              )}
              {loadingAI && (
                <tr>
                  <td colSpan="4" style={{ textAlign: 'center' }}>
                    <span className="typewriter-cursor" style={{ margin: '0 auto' }}></span>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {peerEntries.length > 0 && (
        <div>
          <div className="section-title" style={{ marginBottom: '0.75rem' }}>
            <Users size={18} color="var(--accent-blue)" />
            <h2>So Sánh Cùng Ngành ({sector || symbol})</h2>
          </div>
          <div className="peers-grid">
            {peerEntries.map(([peerSym, info]) => {
              const isUp = (info.Change || 0) >= 0;
              return (
                <div
                  key={peerSym}
                  className="peer-chip"
                  onClick={() => onSelectSymbol && onSelectSymbol(peerSym)}
                  title={`Nhấn để phân tích ${peerSym}`}
                >
                  <div className="peer-chip-top">
                    <span className="peer-sym">{peerSym}</span>
                    <span className={isUp ? 'up-color' : 'down-color'} style={{ fontWeight: '700', fontSize: '0.8rem' }}>
                      {isUp ? '+' : ''}
                      {Number(info.Change || 0).toFixed(2)}%
                    </span>
                  </div>
                  <div className="peer-chip-bottom">
                    <span>Giá: {info.Price}</span>
                    {info.Volume ? <span>KL: {(info.Volume / 1000000).toFixed(1)}M</span> : null}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

