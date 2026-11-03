import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from data_fetcher import get_historical_data, get_peers_performance
from ai_analyzer import analyze_stock_data, MARKET_INDICES
from news_fetcher import get_latest_news
from tabulate import tabulate
import warnings

# Tắt các cảnh báo không quan trọng của pandas
warnings.filterwarnings('ignore')

def print_header(title):
    print("\n" + "="*60)
    print(title.center(60))
    print("="*60 + "\n")

def main():
    print_header("HỆ THỐNG AI PHÂN TÍCH CHỨNG KHOÁN (VNSTOCK)")
    
    symbol = input("Nhập mã cổ phiếu VN muốn phân tích (VD: FPT, VCB, HPG): ").strip().upper()
    if not symbol:
        symbol = "FPT"
        
    days = 1095 # ~3 năm để quan sát chu kỳ dài hạn
    
    print(f"\n[*] Đang tải tệp dữ liệu khổng lồ (3 năm qua) của {symbol} để phân tích chu kỳ...")
    df = get_historical_data(symbol, days)
    
    if df.empty:
        print("[!] Không tìm thấy dữ liệu. Vui lòng kiểm tra lại mã cổ phiếu.")
        return
        
    # In ra 5 ngày gần nhất cho người dùng xem
    print(f"\n[Dữ liệu 5 ngày giao dịch gần nhất của {symbol}]:")
    print(tabulate(df.tail(5), headers='keys', tablefmt='psql'))
    
    print("\n[*] Đang tổng hợp các tin tức kinh tế / chứng khoán nóng nhất từ báo chính thống...")
    news_items = get_latest_news(symbol)
    if news_items:
        print("  -> Đã tìm thấy tin bài có thể ảnh hưởng đến kết quả.")
    else:
        print("  -> Không tìm thấy trang tin có sẵn. (Có thể phân tích thuần số liệu).")
        
    peers_info = get_peers_performance(symbol)

    print("\n[*] Đang tải VN-Index & VN30 để đánh giá 'thời tiết' thị trường...")
    market_data = {idx: get_historical_data(idx, 365) for idx in MARKET_INDICES}

    print("\n[*] Đang chuyển Cổ Phiếu Vua, số liệu Ngành, và Tin thời sự cho AI AI... Hãy chờ trong vài giây!")
    analysis = analyze_stock_data(symbol, df, news_items, peers_info, market_data)
    
    print_header("BÁO CÁO PHÂN TÍCH TỪ CHUYÊN GIA AI")
    print(analysis)
    print("\n" + "="*60)

if __name__ == "__main__":
    main()
