import React from 'react';
import { Bookmark, Trash2 } from 'lucide-react';

export default function Sidebar({ watchlist, currentSymbol, onSelectSymbol, onRemoveSymbol }) {
  return (
    <aside className="sidebar glass-panel">
      <div className="sidebar-header">
        <Bookmark size={18} />
        <span>Danh Mục Theo Dõi</span>
      </div>
      <div className="watchlist-items">
        {Array.isArray(watchlist) &&
          watchlist.map((item, idx) => {
            const isActive = item.symbol === currentSymbol;
            return (
              <div
                className={`watchlist-item ${isActive ? 'active' : ''}`}
                key={item.symbol || idx}
                onClick={() => onSelectSymbol(item.symbol)}
              >
                <span className="watchlist-item-symbol">{item.symbol}</span>
                <button
                  className="watchlist-item-delete"
                  title="Xóa khỏi danh mục"
                  onClick={(e) => onRemoveSymbol(item.symbol, e)}
                >
                  <Trash2 size={14} />
                </button>
              </div>
            );
          })}
        {(!Array.isArray(watchlist) || watchlist.length === 0) && (
          <div style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', fontStyle: 'italic' }}>
            Chưa có mã theo dõi.
          </div>
        )}
      </div>
    </aside>
  );
}

