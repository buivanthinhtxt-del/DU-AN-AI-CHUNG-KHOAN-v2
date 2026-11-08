const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

export async function getWatchlist() {
  try {
    const res = await fetch(`${API_BASE_URL}/api/watchlist`);
    if (!res.ok) return [];
    const data = await res.json();
    return Array.isArray(data) ? data : [];
  } catch {
    return [];
  }
}

export async function addToWatchlistApi(symbol) {
  const res = await fetch(`${API_BASE_URL}/api/watchlist`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ symbol }),
  });
  return res.json();
}

export async function removeFromWatchlistApi(symbol) {
  const res = await fetch(`${API_BASE_URL}/api/watchlist/${encodeURIComponent(symbol)}`, {
    method: 'DELETE',
  });
  return res.json();
}

export async function fetchMarketDataApi(payload) {
  const res = await fetch(`${API_BASE_URL}/api/market_data`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || 'Lỗi kết nối máy chủ API khi tải dữ liệu thị trường.');
  }
  return res.json();
}

export async function fetchAiReportApi(payload) {
  const res = await fetch(`${API_BASE_URL}/api/ai_report`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || 'Lỗi phân tích AI hoặc vượt quá giới hạn truy vấn.');
  }
  return res.json();
}

export async function sendChatQueryApi(message, history = [], symbol = null) {
  const res = await fetch(`${API_BASE_URL}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, history, symbol }),
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || 'Không thể kết nối đến máy chủ tra cứu AI.');
  }
  return res.json();
}


