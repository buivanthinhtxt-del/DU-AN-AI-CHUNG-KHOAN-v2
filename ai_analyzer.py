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

def analyze_stock_data(symbol: str, df: pd.DataFrame, news_items: list = None, peers_info: dict = None, macro_info: dict = None) -> str:
    """
    Sử dụng Gemini để phân tích theo Quy trình 4 bước: Thời tiết, Móng, Bản vẽ, Kịch bản.
    """
    if df.empty:
        return json.dumps({"analysis": "Không có dữ liệu.", "predictions": []})
    
    if not GEMINI_API_KEY or GEMINI_API_KEY == "your_gemini_api_key_here":
        return json.dumps({"analysis": "Vui lòng cấu hình API Key.", "predictions": []})

    df = calculate_indicators(df)
    latest = df.iloc[-1]
    
    macro_context = ""
    if macro_info:
        macro_context = f"""
THỜI TIẾT VĨ MÔ TÀI CHÍNH (Step 1):
- Vàng (Gold): {macro_info.get('GOLD', 'N/A')}
- Dầu (Brent): {macro_info.get('OIL', 'N/A')}
- Tỷ giá USD/VND: {macro_info.get('USD_VND', 'N/A')}
"""

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
BẠN ĐANG THỰC HIỆN NHIỆM VỤ PHÂN TÍCH MÃ CỔ PHIẾU {symbol}.

DỮ LIỆU ĐẦU VÀO:
{df_string}
{macro_context}{tech_context}{peers_context}{news_context}

YÊU CẦU BÁO CÁO (PHẦN 'analysis') - BẮT BUỘC THEO CẤU TRÚC 5 BƯỚC (Dùng Bullet points rõ ràng, văn phong thực chiến):

### BƯỚC 1: ĐÁNH GIÁ VĨ MÔ & SÓNG NGÀNH (The "Why")
- Vĩ mô: Đánh giá nhanh các yếu tố đang chi phối thị trường (Tỷ giá VND/USD, lãi suất điều hành, giá hàng hóa thế giới, xung đột địa chính trị).
- Sóng ngành: Nhóm ngành của {symbol} đang ở chu kỳ nào (Tích lũy, Tăng trưởng, Bão hòa hay Suy thoái)? Có được hưởng lợi từ chính sách nhà nước (FDI, đầu tư công) không?

### BƯỚC 2: PHÂN TÍCH CƠ BẢN & CHẤT XÚC TÁC (The "What")
- Nội tại (FA): Đánh giá nhanh sức khỏe tài chính dựa trên tin tức hoặc kiến thức.
- Catalyst (Chất xúc tác): Có câu chuyện gì sắp tới đẩy giá lên không? (Chia cổ tức, game tăng vốn, dự án mới, thoái vốn, trúng thầu...). Những tin này đã phản ánh vào giá (Price-in) chưa?

### BƯỚC 3: PHÂN TÍCH KỸ THUẬT & DÒNG TIỀN (The "How")
- Xu hướng: Đánh giá vị trí giá so với MA/EMA ngắn và trung hạn.
- Chỉ báo: RSI đang ở vùng nào? MACD có phân kỳ không?
- Dòng tiền (Smart Money): Volume giao dịch nói lên điều gì? Dòng tiền lớn đang gom hàng, đẩy giá hay đang xả (Phân phối)? Cảnh báo nếu có dấu hiệu Bull-trap.
- Sức mạnh tương quan (RS): Mã này đang khỏe hơn hay yếu hơn VN-Index/Ngành?

### BƯỚC 4: SO SÁNH (Nếu có thông tin Peers)
- Lập bảng so sánh nhanh {symbol} với các mã trong ngành dựa trên: Định giá, Sức mạnh dòng tiền hiện tại, và Động lực.
- Đưa ra kết luận dứt khoát: Có nên ưu tiên mã này trong ngành không?

### BƯỚC 5: CHIẾN LƯỢC HÀNH ĐỘNG & KỊCH BẢN (The "Action")
- Khuyến nghị TỐI HẬU: CÓ NÊN MUA HAY KHÔNG? (Trả lời dứt khoát).
- TRẢ LỜI RÕ: Mua tại THỜI ĐIỂM NÀO là hợp lý nhất? Mua tại MỨC GIÁ BAO NHIÊU để mang lại biên lợi nhuận tăng trưởng tốt nhất?
- Cung cấp TÍNH TOÁN GIÁ CỤ THỂ (Trình bày CĂN TRÁI, khoa học, rõ ràng):
  + Giá mua tối ưu (Buy Zone): [Điền mức giá cụ thể]
  + Giá bán mục tiêu (Target Price): [Điền mức giá cụ thể]
  + Tiềm năng tăng trưởng (Upside %): [Tính toán % tăng trưởng]
  + Mức giá cắt lỗ (Stop Loss): [Điền mức giá cụ thể để quản trị rủi ro]
- Kịch bản rủi ro (Scenarios):
  + Bull Case (Tốt): Điều kiện gì để bứt phá?
  + Bear Case (Xấu): Nếu thủng hỗ trợ, giá trôi về đâu?
  - **Dự báo giá cụ thể** cho các thời điểm (Phải có lý do tăng/giảm):
    * Phiên sáng (trong 4‑6 giờ tới)
    * Phiên chiều (trong 8‑12 giờ tới)
    * Ngày hôm sau (T+1)
    * Tuần tới (T+5)
    Các dự báo phải trả về dạng JSON trong phần "predictions" với các trường:
    {{"timeframe": "Morning", "days_future": 0, "high": <value>, "low": <value>, "reason": "<Ghi chú lý do ngắn gọn>"}}
    {{"timeframe": "Afternoon", "days_future": 0, "high": <value>, "low": <value>, "reason": "<Ghi chú lý do ngắn gọn>"}}
    {{"timeframe": "Next Day", "days_future": 1, "high": <value>, "low": <value>, "reason": "<Ghi chú lý do ngắn gọn>"}}
    {{"timeframe": "Next Week", "days_future": 5, "high": <value>, "low": <value>, "reason": "<Ghi chú lý do ngắn gọn>"}}
---
TRẢ VỀ ĐỊNH DẠNG JSON (BẮT BUỘC):
{{
  "scores": {{
    "macro_industry": {{ "score": 80, "reason": "Phân tích chi tiết lý do cho điểm, ví dụ: Ngành đang được hưởng lợi từ chu kỳ nới lỏng tiền tệ và giá hàng hóa giảm..." }},
    "fundamentals_catalyst": {{ "score": 60, "reason": "Phân tích chi tiết chất xúc tác, ví dụ: Doanh nghiệp chuẩn bị chia cổ tức 20% bằng tiền mặt vào tháng sau..." }},
    "technical_momentum": {{ "score": 50, "reason": "Phân tích trạng thái kỹ thuật, ví dụ: Giá đang nằm trên EMA20 nhưng RSI tiến vào vùng quá mua, có rủi ro chỉnh..." }},
    "comparative_strength": {{ "score": 40, "reason": "Phân tích tương quan, ví dụ: Cổ phiếu khỏe hơn VN-Index 5% trong 1 tháng qua, dòng tiền lớn đang gom..." }},
    "action_strategy": {{ "score": 75, "reason": "Kịch bản hành động, ví dụ: Canh mua tại vùng hỗ trợ 24.5, mục tiêu ngắn hạn 28. Cắt lỗ khi thủng 23..." }}
  }},
  "overall_score": 61,
  "analysis": "Nội dung phân tích 5 bước cực kỳ chi tiết theo yêu cầu...",
  "predictions": [
    {{ "timeframe": "T+3 (Ngắn hạn)", "days_future": 3, "high": 18.5, "low": 17.0, "reason": "Chờ dòng tiền xác nhận" }},
    {{ "timeframe": "T+7 (Trung hạn)", "days_future": 7, "high": 19.5, "low": 16.5, "reason": "Kỳ vọng ra báo cáo tài chính tốt" }}
  ]
}}
Lưu ý: Bảng dự báo (predictions) PHẢI LÀ MẢNG JSON. Các điểm số `score` (0-100) PHẢI LÀ SỐ NGUYÊN. KHÔNG xuất văn bản thừa ngoài JSON.
"""
    
    try:
        # Lấy danh sách các model khả dụng cho API Key này
        available_models = [m.name.replace('models/', '') for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        if not available_models:
            raise Exception("API Key của bạn không có quyền truy cập vào bất kỳ model tạo văn bản nào của Google.")
            
        # Ưu tiên các model xịn nhất (nhưng vẫn an toàn vì đã check list)
        preferred_models = ['gemini-1.5-pro', 'gemini-1.5-flash', 'gemini-pro', 'gemini-1.0-pro']
        model_name = next((m for m in preferred_models if m in available_models), available_models[0])
        print(f"[AI] Đang sử dụng model: {model_name}")
        
        system_instruction = """[ROLE - VAI TRÒ]
Bạn là một Giám đốc phân tích chiến lược tại một quỹ đầu tư lớn ở Việt Nam. Tư duy của bạn sắc bén, cực kỳ nhạy cảm với dòng tiền (Smart Money) và am hiểu sâu sắc sự luân chuyển của kinh tế vĩ mô, địa chính trị thế giới tác động đến VN-Index. Văn phong của bạn thẳng thắn, ngắn gọn, tập trung vào số liệu thực tế, hành động dứt khoát như hai người bạn chuyên môn đang trao đổi. Không dùng từ ngữ mơ hồ, chung chung."""
        
        full_prompt = system_instruction + "\n\n" + prompt
        model = genai.GenerativeModel(model_name)
        
        response = model.generate_content(full_prompt)
        
        # Extract JSON using string finding
        text = response.text.strip()
        start_idx = text.find('{')
        end_idx = text.rfind('}')
        
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            text = text[start_idx:end_idx+1]
            
        return text.strip()
    except Exception as e:
        print(f"[!] AI Error: {e}")
        return json.dumps({
            "scores": {
                "macro_industry": { "score": 0, "reason": "System offline" },
                "fundamentals_catalyst": { "score": 0, "reason": "System offline" },
                "technical_momentum": { "score": 0, "reason": "System offline" },
                "comparative_strength": { "score": 0, "reason": "System offline" },
                "action_strategy": { "score": 0, "reason": "System offline" }
            },
            "overall_score": 0,
            "analysis": f"⚠️ LƯU Ý: Khóa API của bạn vừa báo lỗi '{e}'. Tín hiệu có thể bị trễ do quá tải request. Vui lòng thử lại sau.",
            "predictions": []
        })

if __name__ == "__main__":
    pass
