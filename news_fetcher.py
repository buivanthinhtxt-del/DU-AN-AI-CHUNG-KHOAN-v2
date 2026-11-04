import requests
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import ParseError

def get_latest_news(symbol: str = None) -> list:
    """
    Lấy tin tức mới nhất từ các trang báo tài chính chính thống (CafeF, VnExpress).
    Sử dụng requests và ElementTree để không phụ thuộc feedparser.
    """
    news_items = []
    
    rss_urls = [
        "https://cafef.vn/thi-truong-chung-khoan.rss",  # CafeF Chứng khoán
        "https://vnexpress.net/rss/kinh-doanh/chung-khoan.rss" # VnExpress Chứng khoán
    ]
    
    print("[*] Đang tổng hợp bản tin tài chính mới nhất...")
    
    try:
        for url in rss_urls:
            try:
                resp = requests.get(url, timeout=10)
                if resp.status_code == 200:
                    root = ET.fromstring(resp.content)
                    count = 0
                    for item in root.findall('.//item'):
                        if count >= 5:
                            break
                        title_elem = item.find('title')
                        desc_elem = item.find('description')
                        
                        if title_elem is not None:
                            title = title_elem.text or ""
                            summary = ""
                            if desc_elem is not None and desc_elem.text is not None:
                                summary = desc_elem.text
                                
                            if symbol:
                                if symbol.upper() in title.upper() or symbol.upper() in summary.upper():
                                    news_items.append(f"- {title} (Nguồn: {url.split('/')[2]})")
                            else:
                                news_items.append(f"- {title} (Nguồn: {url.split('/')[2]})")
                            count += 1
            except (requests.RequestException, ParseError) as e:
                print(f"[!] Lỗi kết nối hoặc parse XML từ {url}: {e}")
                continue
                
        if symbol and not news_items:
            print(f"[-] Không có tin tức nóng về riêng lẻ '{symbol}'. Lấy tin vĩ mô thị trường chung...")
            return get_latest_news(symbol=None)
            
        return news_items[:10]
        
    except Exception as e:
        print(f"[!] Lỗi chung khi lấy tin tức: {e}")
        return []

if __name__ == "__main__":
    news = get_latest_news("FPT")
    for n in news:
        print(n)
