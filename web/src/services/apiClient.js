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

export async function fetchCouncilDebate(symbolOrPayload, params = {}) {
  const payload =
    typeof symbolOrPayload === 'string'
      ? { symbol: symbolOrPayload, ...params }
      : { ...symbolOrPayload, ...params };

  const res = await fetch(`${API_BASE_URL}/api/council/debate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || 'Lỗi phiên họp Hội Đồng Quân Cơ hoặc máy chủ bận.');
  }
  return res.json();
}

/**
 * Phiên họp Hội Đồng Quân Cơ qua Server-Sent Events: gọi onProgress({stage, status, label})
 * cho từng chặng 0..5, trả về payload đầy đủ khi có event "result".
 * Nếu máy chủ cũ chưa có endpoint stream (404/405) hoặc trình duyệt không hỗ trợ đọc stream,
 * tự động quay về fetchCouncilDebate thông thường.
 */
export async function fetchCouncilDebateStream(symbolOrPayload, params = {}, onProgress = () => {}) {
  const payload =
    typeof symbolOrPayload === 'string'
      ? { symbol: symbolOrPayload, ...params }
      : { ...symbolOrPayload, ...params };

  let res;
  try {
    res = await fetch(`${API_BASE_URL}/api/council/debate/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
      body: JSON.stringify(payload),
    });
  } catch (err) {
    return fetchCouncilDebate(payload);
  }

  if (res.status === 404 || res.status === 405 || !res.body?.getReader) {
    return fetchCouncilDebate(payload);
  }
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || 'Lỗi phiên họp Hội Đồng Quân Cơ hoặc máy chủ bận.');
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder('utf-8');
  let buffer = '';

  const handleBlock = (block) => {
    let event = 'message';
    const dataLines = [];
    block.split('\n').forEach((line) => {
      if (line.startsWith('event:')) event = line.slice(6).trim();
      else if (line.startsWith('data:')) dataLines.push(line.slice(5).trimStart());
    });
    if (!dataLines.length) return null;
    const data = JSON.parse(dataLines.join('\n'));
    if (event === 'progress') {
      onProgress(data);
      return null;
    }
    if (event === 'error') {
      throw new Error(data.detail || 'Lỗi phiên họp Hội Đồng Quân Cơ.');
    }
    if (event === 'result') return { done: true, data };
    return null;
  };

  // eslint-disable-next-line no-constant-condition
  while (true) {
    const { value, done } = await reader.read();
    if (value) buffer += decoder.decode(value, { stream: true });
    let sep;
    while ((sep = buffer.indexOf('\n\n')) !== -1) {
      const block = buffer.slice(0, sep);
      buffer = buffer.slice(sep + 2);
      const out = handleBlock(block);
      if (out?.done) {
        reader.cancel().catch(() => {});
        return out.data;
      }
    }
    if (done) break;
  }
  throw new Error('Kết nối tới Hội Đồng Quân Cơ bị ngắt trước khi có Nghị quyết.');
}

export async function fetchCouncilAgents() {
  const res = await fetch(`${API_BASE_URL}/api/council/agents`);
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || 'Không thể tải thông tin Điểm Công Huân của các Agent.');
  }
  return res.json();
}



