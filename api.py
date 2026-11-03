import os
import sys
import io
# anh yêu em nhiều lắm

# Ép hệ thống xuất Text tiếng Việt chuẩn UTF-8 để không bị lỗi Charmap trên Windows
try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
except:
    pass

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv
import pandas as pd
import json

from data_fetcher import get_historical_data, get_peers_performance
from news_fetcher import get_latest_news
from ai_analyzer import analyze_stock_data, MARKET_INDICES

load_dotenv()

# === FIX: yfinance/certifi bị lỗi Unicode do đường dẫn thư mục chứa tiếng Việt ===
import shutil
import ssl
import certifi
import tempfile
try:
    _cert_src = certifi.where()
    _cert_dst = os.path.join(tempfile.gettempdir(), 'cacert_ascii.pem')
    if not os.path.exists(_cert_dst):
        shutil.copy2(_cert_src, _cert_dst)
    os.environ['REQUESTS_CA_BUNDLE'] = _cert_dst
    os.environ['SSL_CERT_FILE'] = _cert_dst
    print(f"[+] SSL cert path fixed: {_cert_dst}")
except Exception as _e:
    print(f"[!] Could not fix SSL cert path: {_e}")
# =====================================================================

app = FastAPI(title="AI Stock Analyzer API")

# Setup CORS cho phép Frontend gọi API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AnalyzeRequest(BaseModel):
    symbol: str
    target_date: Optional[str] = None # Định dạng YYYY-MM-DD

@app.post("/api/analyze")
async def analyze_stock(req: AnalyzeRequest):
    symbol = req.symbol.upper()
    target_date = req.target_date
    
    if not os.getenv("GEMINI_API_KEY"):
        raise HTTPException(status_code=500, detail="Chưa cấu hình GEMINI_API_KEY trong file .env")
        
    try:
        # 1. Khởi chạy Đa luồng lấy dữ liệu (Giá cổ phiếu, Tin Tức, So sánh cùng ngành, Chỉ số thị trường)
        import concurrent.futures
        days = 365

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_df = executor.submit(get_historical_data, symbol, days, target_date)
            future_peers = executor.submit(get_peers_performance, symbol, target_date)
            future_news = executor.submit(get_latest_news, symbol)
            future_market = {idx: executor.submit(get_historical_data, idx, days, target_date) for idx in MARKET_INDICES}

            df = future_df.result()
            peers_info = future_peers.result()
            news_items = future_news.result()
            market_data = {idx: future.result() for idx, future in future_market.items()}

        if df.empty:
            raise HTTPException(status_code=404, detail=f"Không tìm thấy dữ liệu hoặc mã cổ phiếu {symbol} không hợp lệ.")
            
        # Format df để gửi về Frontend dưới dạng JSON
        df_reset = df.reset_index()
        df_reset['Date'] = df_reset['Date'].dt.strftime('%Y-%m-%d')
        historical_records = df_reset.to_dict(orient='records')
        
        # 4. Phân tích bằng AI
        print(f"[*] Đang gửi yêu cầu phân tích {symbol} tới Gemini AI...")
        analysis_json_str = analyze_stock_data(symbol, df, news_items, peers_info, market_data)
        
        # 5. Parse JSON từ AI (Lọc bỏ các khối markdown nếu có)
        try:
            clean_str = analysis_json_str.strip()
            if clean_str.startswith("```"):
                # Tìm vị trí bắt đầu và kết thúc của khối JSON
                start_idx = clean_str.find("{")
                end_idx = clean_str.rfind("}")
                if start_idx != -1 and end_idx != -1:
                    clean_str = clean_str[start_idx:end_idx+1]
            
            ai_data = json.loads(clean_str)
            print("[+] AI đã phản hồi dữ liệu JSON hợp lệ.")
        except Exception as e:
            print(f"[!] Lỗi phân tích JSON từ AI: {e}")
            # Xử lý trường hợp AI trả về text thay vì JSON hợp lệ
            ai_data = {
                "analysis": analysis_json_str,
                "predictions": []
            }
            
        return {
            "symbol": symbol,
            "target_date": target_date,
            "history": historical_records,
            "ai_report": ai_data
        }
        
    except Exception as e:
        print(f"[ERROR] Lỗi Backend: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # Mặc định chạy ở port 8000
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
