import os
import sys
import io
import json
import concurrent.futures

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

from data_fetcher import get_historical_data, get_peers_performance
from news_fetcher import get_latest_news
from ai_analyzer import analyze_stock_data
from macro_fetcher import get_macro_data

from cache_manager import get_cache, set_cache
from database import init_db, get_watchlist, add_watchlist, remove_watchlist

# === FIX: yfinance/certifi ===
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
except Exception as _e:
    pass

load_dotenv()

app = FastAPI(title="Antigravity Workstation API V2")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    init_db()

class AnalyzeRequest(BaseModel):
    symbol: str
    target_date: Optional[str] = None

class WatchlistRequest(BaseModel):
    symbol: str

@app.post("/api/market_data")
async def fetch_market_data(req: AnalyzeRequest):
    symbol = req.symbol.upper()
    target_date = req.target_date
    
    cache_key = f"market_data_{symbol}_{target_date}"
    cached_data = get_cache(cache_key, 1800) # 30 mins
    if cached_data:
        return cached_data

    try:
        days = 365
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            future_df = executor.submit(get_historical_data, symbol, days, target_date)
            future_peers = executor.submit(get_peers_performance, symbol, target_date)
            future_news = executor.submit(get_latest_news, symbol)
            
            macro_cached = get_cache("macro_data", 900) # 15 mins
            if macro_cached:
                macro_info = macro_cached
            else:
                macro_info = get_macro_data()
                set_cache("macro_data", macro_info)
            
            try:
                df = future_df.result(timeout=60)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Lỗi tải dữ liệu lịch sử ({type(e).__name__}): {e}")
                
            try:
                peers_info = future_peers.result(timeout=45)
            except Exception:
                peers_info = {}
                
            try:
                news_items = future_news.result(timeout=30)
            except Exception:
                news_items = []

        if df.empty:
            raise HTTPException(status_code=404, detail=f"Không tìm thấy dữ liệu hoặc mã cổ phiếu {symbol} không hợp lệ.")
            
        df_reset = df.reset_index()
        # Clean NaN/NaT ONLY on numeric columns, leaving Date unaffected
        num_cols = df_reset.select_dtypes(include=['number']).columns
        df_reset[num_cols] = df_reset[num_cols].fillna(0)
        df_reset['Date'] = df_reset['Date'].dt.strftime('%Y-%m-%d')
        historical_records = df_reset.to_dict(orient='records')
        
        payload = {
            "symbol": symbol,
            "target_date": target_date,
            "history": historical_records,
            "macro": macro_info,
            "peers": peers_info,
            "news": news_items
        }
        
        set_cache(cache_key, payload)
        return payload
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ai_report")
async def fetch_ai_report(req: AnalyzeRequest):
    symbol = req.symbol.upper()
    target_date = req.target_date
    
    if not os.getenv("GEMINI_API_KEY"):
        raise HTTPException(status_code=500, detail="Chưa cấu hình GEMINI_API_KEY")

    cache_key = f"ai_report_{symbol}_{target_date}"
    cached_report = get_cache(cache_key, 86400) # 24 hours ! Reduce 429 quota limits
    if cached_report:
        return cached_report

    try:
        mk_cache_key = f"market_data_{symbol}_{target_date}"
        mk_data = get_cache(mk_cache_key, 3600)
        
        if not mk_data:
            raise HTTPException(status_code=400, detail="Missing market data. Call /api/market_data first.")
            
        # Reconstruct df for analysis
        df_records = mk_data['history']
        if not df_records:
            raise HTTPException(status_code=404, detail="Empty history.")
        df = pd.DataFrame(df_records)
        df['Date'] = pd.to_datetime(df['Date'])
        # Set index back if needed, though ai_analyzer currently might just use Close, Open etc.
        # But wait, ai_analyzer calculate_indicators expects a DataFrame.
        # Actually calculate_indicators works with or without Date index as long as 'Close' is there.
        
        analysis_json_str = analyze_stock_data(
            symbol, df, mk_data['news'], mk_data['peers'], mk_data['macro']
        )
        
        try:
            clean_str = analysis_json_str.strip()
            if clean_str.startswith("```"):
                start_idx = clean_str.find("{")
                end_idx = clean_str.rfind("}")
                if start_idx != -1 and end_idx != -1:
                    clean_str = clean_str[start_idx:end_idx+1]
            
            ai_data = json.loads(clean_str)
        except Exception as e:
            ai_data = {
                "overall_score": 0,
                "scores": {
                    "macro_industry": { "score": 0, "reason": "Lỗi phân tích JSON" },
                    "fundamentals_catalyst": { "score": 0, "reason": "Lỗi phân tích JSON" },
                    "technical_momentum": { "score": 0, "reason": "Lỗi phân tích JSON" },
                    "comparative_strength": { "score": 0, "reason": "Lỗi phân tích JSON" },
                    "action_strategy": { "score": 0, "reason": "Lỗi phân tích JSON" }
                },
                "analysis": analysis_json_str if analysis_json_str else "Nội dung phản hồi bị rỗng hoặc lỗi.",
                "predictions": []
            }
            
        payload = {"ai_report": ai_data}
        # Nếu AI trả lỗi Quota Exceeded/RateLimit, ta không lưu cache dài hạn để có thể gọi lại mượt mà khi hết giới hạn.
        if ai_data.get("overall_score") != 0:
            set_cache(cache_key, payload)
        return payload
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Watchlist APIs ---
@app.get("/api/watchlist")
async def api_get_watchlist():
    return get_watchlist()

@app.post("/api/watchlist")
async def api_add_watchlist(req: WatchlistRequest):
    add_watchlist(req.symbol)
    return {"status": "success"}

@app.delete("/api/watchlist/{symbol}")
async def api_remove_watchlist(symbol: str):
    remove_watchlist(symbol)
    return {"status": "success"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
