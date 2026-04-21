import feedparser
from datetime import datetime

def get_latest_news(symbol: str = None) -> list:
    """
    Lấy tin tức mới nhất từ các trang báo tài chính chính thống (CafeF, VnExpress).
    Nếu không có symbol, lấy tin chung thị trường.
    """
    news_items = []
    
    # Nguồn RSS (Luôn cập nhật realtime)
    rss_urls = [
        "https://cafef.vn/thi-truong-chung-khoan.rss",  # CafeF Chứng khoán
        "https://vnexpress.net/rss/kinh-doanh/chung-khoan.rss" # VnExpress Chứng khoán
    ]
    
    print("[*] Đang tổng hợp bản tin tài chính mới nhất...")
    
    try:
        for url in rss_urls:
            feed = feedparser.parse(url)
            for entry in feed.entries[:5]:  # Lấy 5 tin mới nhất mỗi báo
                title = entry.title
                link = entry.link
                # Chỉ xử lý nhanh text tóm tắt
                summary = entry.description if hasattr(entry, 'description') else ""
                
                # Nếu có tìm một mã cụ thể, lọc tin theo mã đó (tuỳ chọn)
                if symbol:
                    if symbol.upper() in title.upper() or symbol.upper() in summary.upper():
                        news_items.append(f"- {title} (Nguồn: {url.split('/')[2]})")
                else:
                    news_items.append(f"- {title}")
                    
        # Nếu đã lọc mã mà không có tin nào, ta trả về tin chung thị trường để AI lấy làm bối cảnh vĩ mô
        if symbol and not news_items:
            print(f"[-] Không có tin tức nóng về riêng lẻ '{symbol}'. Lấy tin vĩ mô thị trường chung...")
            return get_latest_news(symbol=None)
            
        return news_items[:10]  # Giới hạn 10 tin để không làm tràn context
        
    except Exception as e:
        print(f"[!] Lỗi khi lấy tin tức: {e}")
        return []

if __name__ == "__main__":
    news = get_latest_news("FPT")
    for n in news:
        print(n)
