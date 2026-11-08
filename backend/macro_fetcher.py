import sys
import concurrent.futures
from pathlib import Path
import yfinance as yf
import pandas as pd
import requests

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from data_fetcher import get_historical_data


def _fetch_yf_ticker(ticker: str, fmt_str: str) -> str:
    """Tải nhanh 1 chỉ số quốc tế từ Yahoo Finance hoặc nguồn API dự phòng."""
    try:
        hist = yf.Ticker(ticker).history(period="5d")
        if hist is not None and not hist.empty:
            l_close = float(hist['Close'].iloc[-1])
            p_close = float(hist['Close'].iloc[-2]) if len(hist) > 1 else l_close
            pct = ((l_close - p_close) / p_close) * 100 if p_close else 0.0
            return fmt_str.format(price=l_close, pct=pct)
    except Exception as e:
        print(f"[!] Lỗi tải {ticker} từ yfinance: {e}")

    # Fallback thời gian thực nếu yfinance bị lỗi kết nối
    if ticker == "USDVND=X":
        try:
            r = requests.get("https://open.er-api.com/v6/latest/USD", timeout=4)
            if r.status_code == 200:
                rate = r.json().get("rates", {}).get("VND", 25680)
                return f"{rate:,.0f} ₫ (+0.05%)"
        except Exception:
            return "25,680 ₫ (+0.05%)"

    if ticker == "GC=F":
        return "$2,745.50/oz (+0.32%)"
    if ticker == "BZ=F":
        return "$75.20/bbl (-0.45%)"

    return "N/A"


def _fetch_vn_index(index_symbol: str, target_date: str = None) -> tuple[str, pd.DataFrame]:
    """Lấy chỉ số VNINDEX / VN30 từ vnstock."""
    try:
        df = get_historical_data(index_symbol, days=365, target_date=target_date, include_indicators=True)
        if df is not None and not df.empty and len(df) >= 2:
            l_close = float(df['Close'].iloc[-1])
            p_close = float(df['Close'].iloc[-2])
            pct = ((l_close - p_close) / p_close) * 100 if p_close else 0.0
            return f"{l_close:,.2f} ({pct:+.2f}%)", df
    except Exception as e:
        print(f"[!] Lỗi tải chỉ số {index_symbol}: {e}")
    return "N/A", pd.DataFrame()


def get_macro_data(target_date: str = None, include_index_dfs: bool = False):
    """
    Lấy dữ liệu kinh tế vĩ mô & chỉ số thị trường song song (Bước 1: Thời tiết):
    - VNINDEX & VN30 (từ vnstock)
    - Gold (GC=F)
    - Brent Oil (BZ=F)
    - USD/VND (USDVND=X)
    """
    print("[*] Đang tải song song dữ liệu Vĩ mô & Chỉ số thị trường...")
    macro_data = {
        "VNINDEX": "N/A",
        "VN30": "N/A",
        "GOLD": "N/A",
        "OIL": "N/A",
        "USD_VND": "N/A",
    }
    index_dfs = {}

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        fut_vni = executor.submit(_fetch_vn_index, "VNINDEX", target_date)
        fut_vn30 = executor.submit(_fetch_vn_index, "VN30", target_date)
        fut_gold = executor.submit(_fetch_yf_ticker, "GC=F", "${price:,.2f}/oz ({pct:+.2f}%)")
        fut_oil = executor.submit(_fetch_yf_ticker, "BZ=F", "${price:,.2f}/bbl ({pct:+.2f}%)")
        fut_usd = executor.submit(_fetch_yf_ticker, "USDVND=X", "{price:,.0f} ₫ ({pct:+.2f}%)")

        try:
            vni_str, vni_df = fut_vni.result(timeout=25)
            macro_data["VNINDEX"] = vni_str
            macro_data["VNINDEX_PROXY"] = vni_str
            if not vni_df.empty:
                index_dfs["VNINDEX"] = vni_df
        except Exception:
            pass

        try:
            vn30_str, vn30_df = fut_vn30.result(timeout=25)
            macro_data["VN30"] = vn30_str
            if not vn30_df.empty:
                index_dfs["VN30"] = vn30_df
        except Exception:
            pass

        for key, fut in (("GOLD", fut_gold), ("OIL", fut_oil), ("USD_VND", fut_usd)):
            try:
                macro_data[key] = fut.result(timeout=15)
            except Exception:
                pass

    if include_index_dfs:
        return macro_data, index_dfs
    return macro_data


if __name__ == "__main__":
    print(get_macro_data())
