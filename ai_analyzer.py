import os
import re
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from dotenv import load_dotenv
import google.generativeai as genai
import pandas as pd
import json
import numpy as np

load_dotenv()

# File prompt trợ lý đầu tư (Phần A: System prompt, Phần B: mẫu dữ liệu, Phần C: chế độ JSON)
PROMPT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompts", "tro_ly_dau_tu_chung_khoan_vn.md")

# Các chỉ số dùng cho bước "Thời tiết" thị trường
MARKET_INDICES = ("VNINDEX", "VN30")

# Giờ Việt Nam (UTC+7, không đổi giờ theo mùa) — dùng để nhận biết phiên đang giao dịch
VN_TZ = timezone(timedelta(hours=7))

# Cấu hình API key của Google Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY and GEMINI_API_KEY != "your_gemini_api_key_here":
    genai.configure(api_key=GEMINI_API_KEY)
else:
    print("[!] Chú ý: Chưa cấu hình GEMINI_API_KEY trong file .env")

def calculate_indicators(df: pd.DataFrame):
    """Tính toán các chỉ số kỹ thuật chuyên sâu (Step 2: Móng)."""
    try:
        # 1. EMA 10 & SMA 20
        df['EMA10'] = df['Close'].ewm(span=10, adjust=False).mean()
        df['SMA20'] = df['Close'].rolling(window=20).mean()
        
        # 2. RSI (14)
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # 3. MACD (12, 26, 9)
        exp1 = df['Close'].ewm(span=12, adjust=False).mean()
        exp2 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp1 - exp2
        df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['Histogram'] = df['MACD'] - df['Signal']
        
        # 4. Volatility
        df['Volatility'] = df['Close'].pct_change().rolling(window=20).std() * 100

        # 5. Khối lượng trung bình 20 phiên
        if 'Volume' in df.columns:
            df['VolMA20'] = df['Volume'].rolling(window=20).mean()

        return df
    except Exception as e:
        print(f"[!] Loi tinh toan chi so: {e}")
        return df

@lru_cache(maxsize=1)
def load_prompt_parts() -> dict:
    """Tách System prompt (Phần A), mẫu dữ liệu (Phần B) và chế độ JSON (Phần C) từ file prompt."""
    with open(PROMPT_FILE, encoding="utf-8") as f:
        text = f.read()

    system = re.search(r"## PHẦN A[^\n]*\n(.*?)\n---\s*\n## PHẦN B", text, re.S)
    user_template = re.search(r"## PHẦN B.*?```text\n(.*?)\n```", text, re.S)
    json_mode = re.search(r"## PHẦN C.*?````text\n(.*?)\n````", text, re.S)

    if not (system and user_template and json_mode):
        raise ValueError(f"File prompt không đúng cấu trúc Phần A/B/C: {PROMPT_FILE}")

    return {
        "system": system.group(1).strip(),
        "user": user_template.group(1),
        "json": json_mode.group(1),
    }

class _MissingAsNA(dict):
    """Biến nào không có dữ liệu thì điền N/A để trợ lý tự ghi nhận là thiếu."""
    def __missing__(self, key):
        return "N/A"

def _fmt(value, spec=".2f") -> str:
    """Định dạng số; trả về N/A nếu giá trị trống (VD: chưa đủ 20 phiên để tính SMA20)."""
    try:
        if value is None or pd.isna(value):
            return "N/A"
        return format(value, spec)
    except (TypeError, ValueError):
        return "N/A"

def _session_label(last_date) -> str:
    """Ngày của phiên cuối; đánh dấu nếu phiên đó chưa kết thúc (chạy trong giờ giao dịch)."""
    if not hasattr(last_date, 'strftime'):
        return str(last_date)
    label = last_date.strftime('%d/%m/%Y')
    now = datetime.now(VN_TZ)
    if last_date.date() == now.date() and now.hour < 15:
        label += " (phiên đang giao dịch, số liệu chưa chốt)"
    return label

def _market_values(market_data: dict) -> dict:
    """Tính bối cảnh "Thời tiết" (Bước 1) từ dữ liệu VN-Index và VN30."""
    values = {}

    vnindex = market_data.get("VNINDEX")
    if vnindex is not None and len(vnindex) >= 2:
        idx = calculate_indicators(vnindex.copy())
        close = idx['Close']
        change = close.pct_change() * 100
        latest = idx.iloc[-1]
        recent = zip(idx.index[-5:], close.iloc[-5:], change.iloc[-5:], idx['Volume'].iloc[-5:])
        values.update({
            "market_date": _session_label(idx.index[-1]),
            "vnindex": _fmt(latest['Close']),
            "vnindex_change": _fmt(change.iloc[-1], "+.2f"),
            "vnindex_ma20": _fmt(latest.get('SMA20')),
            "vnindex_ma50": _fmt(close.rolling(window=50).mean().iloc[-1]),
            "vnindex_ma200": _fmt(close.rolling(window=200).mean().iloc[-1]),
            "vnindex_rsi": _fmt(latest.get('RSI')),
            "vnindex_volume": _fmt(latest.get('Volume'), ",.0f"),
            "vnindex_volume_ma20": _fmt(latest.get('VolMA20'), ",.0f"),
            "vnindex_recent": "\n".join(
                f"  {d.strftime('%d/%m')}: {_fmt(c)} điểm ({_fmt(p, '+.2f')}%) | KL {_fmt(v, ',.0f')}"
                for d, c, p, v in recent
            ),
        })

    vn30 = market_data.get("VN30")
    if vn30 is not None and len(vn30) >= 2:
        values["vn30"] = _fmt(vn30['Close'].iloc[-1])
        values["vn30_change"] = _fmt(vn30['Close'].pct_change().iloc[-1] * 100, "+.2f")

    return values

def build_user_prompt(symbol: str, df: pd.DataFrame, news_items: list = None, peers_info: dict = None, market_data: dict = None) -> str:
    """Điền dữ liệu đã tính toán vào mẫu tin nhắn Phần B."""
    latest = df.iloc[-1]

    values = {
        "symbol": symbol,
        # Giá cổ phiếu VN không dưới 1.000 đ, nên giá < 1.000 nghĩa là nguồn trả về theo nghìn đồng
        "price_unit": "nghìn đồng/cp" if latest['Close'] < 1000 else "đồng/cp",
        "price_table": df.tail(15).round(3).to_string(),
        "last_date": _session_label(df.index[-1]),
        "close": _fmt(latest['Close']),
        "ema10": _fmt(latest.get('EMA10')),
        "sma20": _fmt(latest.get('SMA20')),
        "rsi": _fmt(latest.get('RSI')),
        "macd": _fmt(latest.get('MACD'), ".3f"),
        "signal": _fmt(latest.get('Signal'), ".3f"),
        "histogram": _fmt(latest.get('Histogram'), ".3f"),
        "volatility": _fmt(latest.get('Volatility')),
        "volume": _fmt(latest.get('Volume'), ",.0f"),
        "volume_ma20": _fmt(latest.get('VolMA20'), ",.0f"),
    }

    if peers_info:
        values["peers"] = "\n".join(
            f"- {p}: {data['Price']} ({data['Change']:+.2f}%)" for p, data in peers_info.items()
        )

    if news_items:
        values["news"] = "\n".join(news_items[:8])

    if market_data:
        values.update(_market_values(market_data))

    return load_prompt_parts()["user"].format_map(_MissingAsNA(values))

def analyze_stock_data(symbol: str, df: pd.DataFrame, news_items: list = None, peers_info: dict = None, market_data: dict = None) -> str:
    """
    Sử dụng Gemini để phân tích theo quy trình 6 bước của Trợ lý Đầu tư VN
    (Thời tiết, Khu phố, Nội lực, Móng, Bản vẽ, Kịch bản) — xem prompts/tro_ly_dau_tu_chung_khoan_vn.md.
    """
    if df.empty:
        return json.dumps({"analysis": "Không có dữ liệu.", "predictions": []})

    if not GEMINI_API_KEY or GEMINI_API_KEY == "your_gemini_api_key_here":
        return json.dumps({"analysis": "Vui lòng cấu hình API Key.", "predictions": []})

    df = calculate_indicators(df)

    try:
        prompt_parts = load_prompt_parts()
        prompt = build_user_prompt(symbol, df, news_items, peers_info, market_data) + "\n\n" + prompt_parts["json"]
    except Exception as e:
        print(f"[!] Prompt Error: {e}")
        return json.dumps({
            "analysis": f"Lỗi đọc file prompt: {e}",
            "predictions": []
        })

    try:
        model_name = 'gemini-flash-latest'
        model = genai.GenerativeModel(
            model_name,
            system_instruction=prompt_parts["system"]
        )

        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        
        return response.text.strip()
    except Exception as e:
        print(f"[!] AI Error: {e}")
        return json.dumps({
            "analysis": f"Lỗi gọi AI: {e}",
            "predictions": []
        })

if __name__ == "__main__":
    pass
