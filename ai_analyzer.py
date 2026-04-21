import os
from dotenv import load_dotenv
import google.generativeai as genai
import pandas as pd
import json
import numpy as np

load_dotenv()

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
        
        return df
    except Exception as e:
        print(f"[!] Loi tinh toan chi so: {e}")
        return df

def analyze_stock_data(symbol: str, df: pd.DataFrame, news_items: list = None, peers_info: dict = None) -> str:
    """
    Sử dụng Gemini để phân tích theo Quy trình 4 bước: Thời tiết, Móng, Bản vẽ, Kịch bản.
    """
    if df.empty:
        return json.dumps({"analysis": "Không có dữ liệu.", "predictions": []})
    
    if not GEMINI_API_KEY or GEMINI_API_KEY == "your_gemini_api_key_here":
        return json.dumps({"analysis": "Vui lòng cấu hình API Key.", "predictions": []})

    df = calculate_indicators(df)
    latest = df.iloc[-1]
    
    tech_context = f"""
DỮ LIỆU KỸ THUẬT HIỆN TẠI (Step 2):
- Giá hiện hành: {latest['Close']:.2f}
- EMA10: {latest['EMA10']:.2f} | SMA20: {latest['SMA20']:.2f}
- RSI: {latest['RSI']:.2f}
- MACD Line: {latest['MACD']:.3f} | Signal Line: {latest['Signal']:.3f}
- Trạng thái MACD: {'Cắt lên' if latest['MACD'] > latest['Signal'] else 'Cắt xuống'}
- Biến động Vol: {latest['Volatility']:.2f}%
"""

    peers_context = ""
    if peers_info:
        peers_str_list = [f"- {p}: {data['Price']} đ ({data['Change']:.2f}%)" for p, data in peers_info.items()]
        peers_context = "\nDIỄN BIẾN NGÀNH (Peers):\n" + "\n".join(peers_str_list) + "\n"

    news_context = ""
    if news_items:
        news_list_str = "\n".join(news_items[:8])
        news_context = f"\nTIN TỨC & SỰ KIỆN (Step 3):\n{news_list_str}\n"

    df_string = df.tail(15).to_string()
    
    prompt = f"""
BẠN LÀ SIÊU AI CHUYÊN GIA PHÂN TÍCH CHỨNG KHOÁN (QUANTS).
Nhiệm vụ: Phân tích mã {symbol} theo QUY TRÌNH 4 BƯỚC NGHIÊM NGẶT.

DỮ LIỆU ĐẦU VÀO:
{df_string}
{tech_context}{peers_context}{news_context}

YÊU CẦU BÁO CÁO (PHẦN 'analysis') - BẮT BUỘC THEO CẤU TRÚC:

### BƯỚC 1: XEM "THỜI TIẾT" (VN-INDEX & VĨ MÔ)
- Đánh giá thị trường chung. Chú ý mốc 1.800 - 1.820.
- Kiểm tra thanh khoản (Vol) và hiện tượng "xanh vỏ đỏ lòng" (kéo trụ hay tăng đều).
- Đánh giá tác động Địa chính trị (Giá dầu, xung đột) đến nhóm ngành.

### BƯỚC 2: KIỂM TRA "MÓNG" (KỸ THUẬT NGẮN HẠN T+)
- Đánh giá "3 đường chỉ": MA10/MA20, RSI (có nóng > 75 không?), MACD (có cắt Signal không?).
- Phân tích Dòng tiền (Vol): Phiên tăng có Vol cao không? Hay tăng Vol "héo".

### BƯỚC 3: SOI "BẢN VẼ" (TIN TỨC & SỰ KIỆN)
- Phân tích các tin ĐHĐCĐ, lịch họp, lấp Gap.
- Áp dụng quy tắc: Mua kỳ vọng, bán sự thật.

### BƯỚC 4: CHỐT "KỊCH BẢN" (ACTION PLAN)
Xuất một bảng Markdown với kịch bản chi tiết:
| Kịch bản | Dấu hiệu nhận biết | Hành động cụ thể |
| :--- | :--- | :--- |
| **Kịch bản Tốt (Bullish)** | Index vượt 1.830, Vol bùng nổ... | Tấn công: Múc thêm, nắm giữ... |
| **Kịch bản Đi ngang (Sideway)** | Giá biến động hẹp, Vol thấp... | Thăm dò: Mua nhịp nhúng, không đu xanh |
| **Kịch bản Xấu (Bearish)** | Trụ bị bán rát, Index thủng 1.800... | Phòng thủ: Bán giảm tỷ trọng, giữ tiền mặt |

---
**Ví dụ chi tiết cho 1-2 tuần tới:**
(Dựa trên lịch Thứ 6 "thay máu", Đầu tuần "thử lửa", Cuối tuần "nghiệm thu")

TRẢ VỀ ĐỊNH DẠNG JSON:
{{
  "analysis": "Nội dung phân tích 4 bước cực kỳ chi tiết...",
  "predictions": [
    ... (Dự báo giá phi tuyến tính)
  ]
}}
Lưu ý: Không xuất văn bản thừa ngoài JSON.
"""
    
    try:
        model_name = 'gemini-flash-latest'
        model = genai.GenerativeModel(
            model_name,
            system_instruction="Ban la tro ly AI chuyen gia. Tra ve JSON duy nhat, trinh bay bao cao khoa hoc, dung quy trinh 4 buoc."
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
