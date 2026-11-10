import sys
import io
import json
import concurrent.futures
import warnings

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from tabulate import tabulate
from data_fetcher import get_historical_data, get_peers_performance
from ai_analyzer import analyze_stock_data, MARKET_INDICES
from macro_fetcher import get_macro_data
from news_fetcher import get_latest_news

warnings.filterwarnings("ignore")


def print_header(title: str):
    print("\n" + "=" * 70)
    print(title.center(70))
    print("=" * 70 + "\n")


def main():
    print_header("HỆ THỐNG AI PHÂN TÍCH CHỨNG KHOÁN VIỆT NAM (VNSTOCK + GEMINI)")

    symbol = input("Nhập mã cổ phiếu VN muốn phân tích (VD: FPT, VCB, HPG): ").strip().upper()
    if not symbol:
        symbol = "FPT"

    days = 365
    print(f"\n[*] Đang tải song song dữ liệu lịch sử, vĩ mô, cùng ngành và tin tức cho {symbol}...")

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_df = executor.submit(get_historical_data, symbol, days)
        future_peers = executor.submit(get_peers_performance, symbol)
        future_news = executor.submit(get_latest_news, symbol)
        future_macro = executor.submit(get_macro_data)
        future_indices = {idx: executor.submit(get_historical_data, idx, days) for idx in MARKET_INDICES}

        df = future_df.result()
        peers_info = future_peers.result()
        news_items = future_news.result()
        macro_info = future_macro.result()
        market_data = {idx: fut.result() for idx, fut in future_indices.items()}

    if df.empty:
        print("[!] Không tìm thấy dữ liệu. Vui lòng kiểm tra lại mã cổ phiếu.")
        return

    display_cols = [c for c in ["Open", "High", "Low", "Close", "Volume", "EMA10", "SMA20", "RSI"] if c in df.columns]
    print(f"\n[Dữ liệu 5 phiên giao dịch gần nhất của {symbol}]:")
    print(tabulate(df[display_cols].tail(5).round(2), headers="keys", tablefmt="psql"))

    print("\n[*] Đang gửi dữ liệu tới Trợ lý Đầu tư AI... Vui lòng chờ trong giây lát!")
    raw_json = analyze_stock_data(symbol, df, news_items, peers_info, macro_info, market_data)

    try:
        report = json.loads(raw_json)
        print_header(f"BÁO CÁO PHÂN TÍCH CHUYÊN SÂU — {symbol} (Điểm: {report.get('overall_score', 'N/A')}/100)")
        print(report.get("analysis", raw_json))
    except Exception:
        print_header("BÁO CÁO PHÂN TÍCH TỪ CHUYÊN GIA AI")
        print(raw_json)
    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
