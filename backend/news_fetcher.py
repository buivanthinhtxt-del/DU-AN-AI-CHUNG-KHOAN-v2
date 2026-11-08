import re
import html
import concurrent.futures
import requests
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import ParseError

RSS_URLS = [
    ("CafeF", "https://cafef.vn/thi-truong-chung-khoan.rss"),
    ("CafeF Doanh nghiệp", "https://cafef.vn/doanh-nghiep.rss"),
    ("VnExpress", "https://vnexpress.net/rss/kinh-doanh/chung-khoan.rss"),
    ("VnExpress Kinh doanh", "https://vnexpress.net/rss/kinh-doanh.rss"),
]


def _clean_html(raw_text: str) -> str:
    """Loại bỏ thẻ HTML và giải mã HTML entities trong RSS description."""
    if not raw_text:
        return ""
    text = re.sub(r"<[^>]+>", " ", raw_text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _fetch_single_rss(source_name: str, url: str) -> list[dict]:
    """Tải và phân tích toàn bộ danh sách item từ 1 nguồn RSS."""
    items = []
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        resp = requests.get(url, headers=headers, timeout=8)
        if resp.status_code == 200:
            root = ET.fromstring(resp.content)
            for item in root.findall(".//item"):
                title_elem = item.find("title")
                desc_elem = item.find("description")
                pub_elem = item.find("pubDate")
                link_elem = item.find("link")

                title = _clean_html(title_elem.text if title_elem is not None else "")
                summary = _clean_html(desc_elem.text if desc_elem is not None else "")
                pub_date = (pub_elem.text or "").strip() if pub_elem is not None else ""
                link_url = (link_elem.text or "").strip() if link_elem is not None else ""

                if title:
                    items.append({
                        "title": title,
                        "summary": summary,
                        "source": source_name,
                        "pub_date": pub_date,
                        "url": link_url,
                    })
    except (requests.RequestException, ParseError) as e:
        print(f"[!] Lỗi kết nối hoặc parse XML từ {url}: {e}")
    return items


def get_latest_news(symbol: str = None) -> list[str]:
    """
    Lấy tin tức mới nhất từ các trang báo tài chính chính thống (CafeF, VnExpress).
    Duyệt toàn bộ các bản tin trong RSS để tìm tin khớp với mã cổ phiếu trước khi giới hạn số lượng.
    """
    print(f"[*] Đang tổng hợp bản tin tài chính mới nhất cho {symbol or 'Thị trường chung'}...")

    all_articles = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(_fetch_single_rss, name, url) for name, url in RSS_URLS]
        for future in concurrent.futures.as_completed(futures, timeout=12):
            try:
                all_articles.extend(future.result())
            except Exception:
                continue

    matched_news = []
    general_news = []
    seen_titles = set()

    clean_sym = symbol.upper().strip().replace(".VN", "") if symbol else None
    sym_pattern = re.compile(rf"\b{re.escape(clean_sym)}\b", re.IGNORECASE) if clean_sym else None

    for art in all_articles:
        title = art["title"]
        if title in seen_titles:
            continue
        seen_titles.add(title)

        summary = art["summary"]
        source = art["source"]
        formatted = f"- {title} (Nguồn: {source})"

        if sym_pattern and (sym_pattern.search(title) or sym_pattern.search(summary)):
            matched_news.append(formatted)
        else:
            general_news.append(formatted)

    if clean_sym and matched_news:
        # Ưu tiên tin riêng của mã cổ phiếu, bổ sung thêm tin vĩ mô thị trường cho đủ bức tranh
        combined = matched_news[:7] + general_news[:3]
        return combined[:10]

    return general_news[:10]


def get_latest_news_detailed(symbol: str = None) -> list[dict]:
    """
    Lấy danh sách tin tức chi tiết gồm: title, summary, source, pub_date, url
    để hỗ trợ hiển thị citation / liên kết đọc bài gốc.
    """
    all_articles = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(_fetch_single_rss, name, url) for name, url in RSS_URLS]
        for future in concurrent.futures.as_completed(futures, timeout=12):
            try:
                all_articles.extend(future.result())
            except Exception:
                continue

    matched = []
    general = []
    seen = set()

    clean_sym = symbol.upper().strip().replace(".VN", "") if symbol else None
    sym_pattern = re.compile(rf"\b{re.escape(clean_sym)}\b", re.IGNORECASE) if clean_sym else None

    for art in all_articles:
        title = art.get("title", "")
        if not title or title in seen:
            continue
        seen.add(title)

        summary = art.get("summary", "")
        if sym_pattern and (sym_pattern.search(title) or sym_pattern.search(summary)):
            matched.append(art)
        else:
            general.append(art)

    if clean_sym and matched:
        combined = matched[:7] + general[:3]
        return combined[:10]

    return general[:10]


if __name__ == "__main__":
    for n in get_latest_news("FPT"):
        print(n)
