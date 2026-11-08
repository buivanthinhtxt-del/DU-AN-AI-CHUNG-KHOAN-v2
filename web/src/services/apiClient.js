function resolveApiBaseUrl() {
  if (import.meta.env.VITE_API_BASE_URL) {
    return import.meta.env.VITE_API_BASE_URL.replace(/\/+$/, '');
  }
  if (typeof window !== 'undefined') {
    const { hostname, port } = window.location;
    // Khi chạy Vite dev server ở máy cá nhân (port 5173/5174), trỏ về cổng 8000 của FastAPI
    if ((hostname === 'localhost' || hostname === '127.0.0.1') && port && port !== '8000' && port !== '7860') {
      return 'http://127.0.0.1:8000';
    }
    // Khi chạy trên Cloud (Render / Hugging Face / Railway) hoặc chung cổng với FastAPI: gọi đường dẫn tương đối cùng domain
    return '';
  }
  return 'http://127.0.0.1:8000';
}

const API_BASE_URL = resolveApiBaseUrl();

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

export async function fetchRealtimeQuoteApi(symbols) {
  const list = Array.isArray(symbols) ? symbols.join(',') : symbols;
  const res = await fetch(`${API_BASE_URL}/api/realtime/quote?symbols=${encodeURIComponent(list)}`);
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || 'Không lấy được bảng giá trực tiếp.');
  }
  return res.json();
}

export async function fetchIntradayApi(symbol, resolution = '1') {
  const res = await fetch(
    `${API_BASE_URL}/api/realtime/intraday/${encodeURIComponent(symbol)}?resolution=${encodeURIComponent(resolution)}`,
  );
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || 'Không lấy được nến trong phiên.');
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


