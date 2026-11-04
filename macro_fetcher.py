import yfinance as yf
import pandas as pd

def get_macro_data() -> dict:
    """
    Lấy dữ liệu kinh tế vĩ mô (Step 1: Thời tiết)
    - VNINDEX.VMI, VNI.VMI, hoặc lấy tạm từ cổ phiếu VCB làm thước đo index (nếu lỗi).
    - Gold (GC=F)
    - Brent Oil (BZ=F)
    - USD/VND (USDVND=X)
    """
    print("[*] Đang tải dữ liệu Vĩ mô (Macro)...")
    macro_data = {
        "GOLD": "N/A",
        "OIL": "N/A",
        "USD_VND": "N/A",
        "VNINDEX_PROXY": "N/A"
    }
    
    try:
        # Vàng
        gold = yf.Ticker("GC=F").history(period="5d")
        if not gold.empty:
            l_close = gold['Close'].iloc[-1]
            p_close = gold['Close'].iloc[-2] if len(gold) > 1 else l_close
            pct = ((l_close - p_close) / p_close) * 100
            macro_data['GOLD'] = f"${l_close:.2f}/oz ({pct:+.2f}%)"
            
        # Dầu Brent
        oil = yf.Ticker("BZ=F").history(period="5d")
        if not oil.empty:
            l_close = oil['Close'].iloc[-1]
            p_close = oil['Close'].iloc[-2] if len(oil) > 1 else l_close
            pct = ((l_close - p_close) / p_close) * 100
            macro_data['OIL'] = f"${l_close:.2f}/bbl ({pct:+.2f}%)"
            
        # Tỷ giá USD/VND
        usd = yf.Ticker("USDVND=X").history(period="5d")
        if not usd.empty:
            l_close = usd['Close'].iloc[-1]
            p_close = usd['Close'].iloc[-2] if len(usd) > 1 else l_close
            pct = ((l_close - p_close) / p_close) * 100
            macro_data['USD_VND'] = f"{l_close:,.0f} ₫ ({pct:+.2f}%)"
            
    except Exception as e:
        print(f"[!] Lỗi khi lấy dữ liệu Vĩ mô: {e}")
        
    return macro_data

if __name__ == "__main__":
    print(get_macro_data())
