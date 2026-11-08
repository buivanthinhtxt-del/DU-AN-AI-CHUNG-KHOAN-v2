import React from 'react';
import { Plus, Globe } from 'lucide-react';

export default function MacroTicker({ macro, symbol, sector, onAddWatchlist }) {
  if (!macro) return null;

  const getColorClass = (val) => {
    if (!val || typeof val !== 'string') return '';
    if (val.includes('+')) return 'up-color';
    if (val.includes('-')) return 'down-color';
    return '';
  };

  return (
    <div className="macro-header-row">
      <div className="macro-ticker">
        <div className="macro-item">
          <Globe size={14} color="var(--accent-blue)" />
          <span className="macro-label">VN-Index:</span>
          <span className={getColorClass(macro.VNINDEX)}>{macro.VNINDEX || 'N/A'}</span>
        </div>
        {macro.VN30 && macro.VN30 !== 'N/A' && (
          <div className="macro-item">
            <span className="macro-label">VN30:</span>
            <span className={getColorClass(macro.VN30)}>{macro.VN30}</span>
          </div>
        )}
        <div className="macro-item">
          <span className="macro-label">Vàng (GC=F):</span>
          <span className={getColorClass(macro.GOLD)}>{macro.GOLD || 'N/A'}</span>
        </div>
        <div className="macro-item">
          <span className="macro-label">Dầu Brent:</span>
          <span className={getColorClass(macro.OIL)}>{macro.OIL || 'N/A'}</span>
        </div>
        <div className="macro-item">
          <span className="macro-label">USD/VND:</span>
          <span className={getColorClass(macro.USD_VND)}>{macro.USD_VND || 'N/A'}</span>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexShrink: 0 }}>
        {sector && <span className="sector-badge">{sector}</span>}
        <button className="add-watchlist-btn" onClick={() => onAddWatchlist(symbol)}>
          <Plus size={14} /> Lưu mã {symbol}
        </button>
      </div>
    </div>
  );
}

