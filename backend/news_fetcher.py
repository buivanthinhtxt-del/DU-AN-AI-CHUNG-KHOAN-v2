import re
import html
import urllib.parse
import concurrent.futures
from email.utils import parsedate_to_datetime

import requests
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import ParseError

RSS_URLS = [
    ("CafeF", "https://cafef.vn/thi-truong-chung-khoan.rss"),
    ("CafeF Doanh nghiệp", "https://cafef.vn/doanh-nghiep.rss"),
    ("VnExpress", "https://vnexpress.net/rss/kinh-doanh/chung-khoan.rss"),
    ("VnExpress Kinh doanh", "https://vnexpress.net/rss/kinh-doanh.rss"),
]

# Tìm kiếm tin RIÊNG theo mã (Google News RSS gom bài từ CafeF, VnEconomy, Vietstock, NDH...)
TICKER_NEWS_URL = "https://news.google.com/rss/search?q={query}&hl=vi&gl=VN&ceid=VN:vi"
TICKER_NEWS_WINDOW = "30d"

_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def _clean_html(raw_text: str) -> str:
    """Loại bỏ thẻ HTML và giải mã HTML entities trong RSS description."""
    if not raw_text:
        return ""
    text = re.sub(r"<[^>]+>", " ", raw_text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _pub_ts(pub_date: str) -> float:
    try:
        return parsedate_to_datetime(pub_date).timestamp()
    except Exception:
        return 0.0


def _fetch_single_rss(source_name: str, url: str) -> list[dict]:
    """Tải và phân tích toàn bộ danh sách item từ 1 nguồn RSS."""
    items = []
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=8)
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


def _fetch_ticker_news(symbol: str) -> list[dict]:
    """
    Tin tức chuyên biệt theo mã cổ phiếu (ticker-specific).
    Google News trả về tiêu đề dạng "<tiêu đề> - <tên báo>", tên báo nằm trong thẻ <source>.
    Phần description chỉ là liên kết HTML nên bỏ qua (summary rỗng).
    """
    query = urllib.parse.quote(f'"{symbol}" cổ phiếu when:{TICKER_NEWS_WINDOW}')
    url = TICKER_NEWS_URL.format(query=query)
    items = []
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=8)
        if resp.status_code != 200:
            return []
        root = ET.fromstring(resp.content)
        for item in root.findall(".//item"):
            title = _clean_html(item.findtext("title") or "")
            publisher = _clean_html(item.findtext("source") or "") or "Google News"
            suffix = f" - {publisher}"
            if title.endswith(suffix):
                title = title[: -len(suffix)].strip()
            if not title:
                continue
            items.append({
                "title": title,
                "summary": "",
                "source": publisher,
                "pub_date": (item.findtext("pubDate") or "").strip(),
                "url": (item.findtext("link") or "").strip(),
                "ticker_specific": True,
            })
    except (requests.RequestException, ParseError) as e:
        print(f"[!] Lỗi tải tin riêng theo mã {symbol}: {e}")
    return items


def _collect_news(symbol: str = None) -> tuple[list[dict], list[dict]]:
    """
    Trả về (tin riêng của mã, tin thị trường chung).
    - Tin riêng = tin Google News theo mã + tin RSS chung có nhắc đến mã, sắp xếp mới nhất trước.
    - Chỉ giữ tin có mã xuất hiện trong tiêu đề/tóm tắt để tránh nhiễu (vd: "FPT" trong tin không liên quan).
    """
    clean_sym = symbol.upper().strip().replace(".VN", "") if symbol else None
    sym_pattern = re.compile(rf"\b{re.escape(clean_sym)}\b", re.IGNORECASE) if clean_sym else None

    all_articles: list[dict] = []
    ticker_articles: list[dict] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(_fetch_single_rss, name, url): "rss" for name, url in RSS_URLS}
        if clean_sym:
            futures[executor.submit(_fetch_ticker_news, clean_sym)] = "ticker"
        try:
            for future in concurrent.futures.as_completed(futures, timeout=12):
                try:
                    res = future.result()
                except Exception:
                    continue
                (ticker_articles if futures[future] == "ticker" else all_articles).extend(res)
        except concurrent.futures.TimeoutError:
            pass

    matched: list[dict] = []
    general: list[dict] = []
    seen: set[str] = set()

    def _key(title: str) -> str:
        return re.sub(r"\W+", "", title.lower())[:80]

    for art in ticker_articles + all_articles:
        title = art.get("title", "")
        k = _key(title)
        if not title or k in seen:
            continue
        seen.add(k)
        if sym_pattern and (sym_pattern.search(title) or sym_pattern.search(art.get("summary", ""))):
            matched.append(art)
        else:
            general.append(art)

    matched.sort(key=lambda a: _pub_ts(a.get("pub_date", "")), reverse=True)
    return matched, general


def get_latest_news(symbol: str = None) -> list[str]:
    """
    Lấy tin tức mới nhất: ưu tiên tin riêng theo mã (Google News + RSS CafeF/VnExpress có nhắc mã),
    bổ sung tin vĩ mô thị trường cho đủ bức tranh.
    """
    print(f"[*] Đang tổng hợp bản tin tài chính mới nhất cho {symbol or 'Thị trường chung'}...")
    matched, general = _collect_news(symbol)
    fmt = lambda a: f"- {a['title']} (Nguồn: {a['source']})"  # noqa: E731
    if symbol and matched:
        return [fmt(a) for a in (matched[:7] + general[:3])][:10]
    return [fmt(a) for a in general[:10]]


def get_latest_news_detailed(symbol: str = None) -> list[dict]:
    """
    Lấy danh sách tin tức chi tiết gồm: title, summary, source, pub_date, url (+ ticker_specific)
    để hỗ trợ hiển thị citation / liên kết đọc bài gốc.
    """
    matched, general = _collect_news(symbol)
    if symbol and matched:
        return (matched[:7] + general[:3])[:10]
    return general[:10]


if __name__ == "__main__":
    for n in get_latest_news("FPT"):
        print(n)
