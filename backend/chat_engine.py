import os
import sys
import re
import json
import logging
from typing import List, Dict, Optional
from datetime import datetime, timezone, timedelta

from dotenv import load_dotenv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from google.genai import types

import llm_client

from news_fetcher import get_latest_news_detailed
from data_fetcher import get_historical_data, calculate_indicators, get_stock_sector
from macro_fetcher import get_macro_data

logger = logging.getLogger("chat_engine")
load_dotenv(ROOT_DIR / ".env")
load_dotenv(BASE_DIR / ".env")

VN_TZ = timezone(timedelta(hours=7))

CHAT_SYSTEM_PROMPT = """Bạn là Antigravity WallStreet AI — Chuyên gia Phân tích & Tra cứu Thông tin Chứng khoán Việt Nam cao cấp.
Nhiệm vụ của bạn:
1. Giải đáp các câu hỏi về cổ phiếu, nhóm ngành, tin tức tài chính, báo cáo kết quả kinh doanh, vĩ mô, chu kỳ T+2.5, chính sách tiền tệ và chiến lược đầu tư.
2. Sử dụng thông tin tra cứu thực tế trên Internet (Google Search grounding) và dữ liệu thị trường trực tiếp được cung cấp.
3. Trả lời súc tích, chuyên nghiệp, cấu trúc rõ ràng với Markdown (tiêu đề, gạch đầu dòng, bảng biểu nếu cần).
4. Luôn giữ tinh thần khách quan, thực chiến, có cảnh báo quản trị rủi ro khi đề cập điểm mua/bán."""


def _extract_symbol_from_query(query: str, current_symbol: Optional[str] = None) -> Optional[str]:
    """Phát hiện mã cổ phiếu trong câu hỏi nếu có (3 chữ cái in hoa)."""
    # 1. Nếu có current_symbol và người dùng hỏi có nhắc đến current_symbol hoặc đại từ liên hệ
    if current_symbol:
        current_upper = current_symbol.strip().upper()
        if current_upper in query.upper() or any(w in query.lower() for w in ["mã này", "cổ phiếu này", "doanh nghiệp này", "nó", "target"]):
            return current_upper

    # 2. Tìm tất cả các từ 3 chữ cái
    words = re.findall(r"\b[A-Za-z]{3}\b", query)
    
    # Danh sách các từ tiếng Việt/từ thông dụng 3 ký tự cần loại trừ
    vietnamese_words = {
        "VND", "USD", "GDP", "CPI", "FED", "SBV", "WTO", "EPS", "ROE", "ROA", "RSI", "EMA", "SMA",
        "ATO", "ATC", "NAV", "ETF", "BCTC", "NAY", "GIA", "CHO", "KHI", "NEN", "SAU", "LAM", "DAN",
        "THE", "TIN", "MUA", "BAN", "DAU", "CON", "MAI", "LUC", "HOA", "NAM", "THI", "ROI", "GIO",
        "NHA", "NGU", "DAT", "TAP", "CAC", "XEM", "DUNG", "DIEM", "QUY", "BAI", "CAN", "HON", "BAO",
        "DAY", "MOT", "HAI", "VAN", "HOI", "DOC", "GAP", "TIEP", "VOI", "SANG", "CHIEU", "TRUA", "TOI"
    }
    
    for w in words:
        w_upper = w.upper()
        if w_upper not in vietnamese_words:
            # Kiểm tra xem mã có trong hệ thống phân loại ngành không
            sector = get_stock_sector(w_upper)
            if sector != "Chưa phân loại ngành":
                return w_upper
            # Hoặc nếu là từ viết hoa hoàn toàn trong câu
            if w.isupper():
                return w_upper

    return current_symbol.upper() if current_symbol else None


def _build_context_summary(symbol: Optional[str]) -> tuple[str, list[dict]]:
    """Tổng hợp bối cảnh dữ liệu thị trường và tin tức mới nhất cho câu hỏi."""
    context_lines = []
    sources = []
    
    # 1. Bối cảnh Vĩ mô
    try:
        macro = get_macro_data()
        if macro:
            context_lines.append("[DỮ LIỆU THỜI TIẾT THỊ TRƯỜNG & VĨ MÔ]")
            for k, v in macro.items():
                context_lines.append(f"- {k}: {v}")
    except Exception as e:
        logger.warning(f"Không thể lấy dữ liệu vĩ mô cho chat: {e}")

    # 2. Bối cảnh Cổ phiếu & Kỹ thuật
    if symbol:
        try:
            sector = get_stock_sector(symbol)
            context_lines.append(f"\n[DỮ LIỆU CỔ PHIẾU {symbol} - NGÀNH: {sector}]")
            df = get_historical_data(symbol)
            if df is not None and not df.empty:
                df = calculate_indicators(df)
                latest = df.iloc[-1]
                close = float(latest["Close"])
                prev_close = float(df.iloc[-2]["Close"]) if len(df) > 1 else close
                pct_change = ((close - prev_close) / prev_close) * 100 if prev_close else 0.0
                ema10 = float(latest.get("EMA10", close))
                sma20 = float(latest.get("SMA20", close))
                rsi = float(latest.get("RSI", 50.0))
                macd = float(latest.get("MACD", 0.0))
                vol = float(latest.get("Volume", 0.0))
                
                context_lines.append(f"- Giá đóng cửa gần nhất: {close:,.2f} ({pct_change:+.2f}%)")
                context_lines.append(f"- Đường EMA10: {ema10:.2f} | Đường SMA20: {sma20:.2f}")
                context_lines.append(f"- Chỉ báo RSI(14): {rsi:.2f} | MACD: {macd:.3f}")
                context_lines.append(f"- Khối lượng khớp lệnh phiên cuối: {vol:,.0f} cp")
        except Exception as e:
            logger.warning(f"Không thể lấy dữ liệu kỹ thuật {symbol}: {e}")

    # 3. Tin tức tài chính thực tế từ Internet (RSS CafeF & VnExpress)
    try:
        news_items = get_latest_news_detailed(symbol)
        if news_items:
            context_lines.append("\n[TIN TỨC BÁO CHÍ TÀI CHÍNH MỚI NHẤT TRÊN INTERNET]")
            for idx, item in enumerate(news_items[:6]):
                context_lines.append(f"{idx+1}. {item['title']} ({item['source']})")
                if item.get("summary"):
                    context_lines.append(f"   Trích dẫn: {item['summary'][:160]}...")
                if item.get("url"):
                    sources.append({"title": item["title"], "url": item["url"], "source": item["source"]})
    except Exception as e:
        logger.warning(f"Không thể lấy tin tức cho chat: {e}")

    return "\n".join(context_lines), sources


def _offline_synthesize_answer(message: str, symbol: Optional[str], context_text: str, sources: list[dict]) -> str:
    """Fallback tự động tổng hợp câu trả lời dựa trên dữ liệu thực tế khi không có GEMINI_API_KEY hoặc dính Quota."""
    sym_header = f" cổ phiếu **{symbol}**" if symbol else " thị trường chứng khoán"
    
    reply = f"### 💡 Thông tin tra cứu & phân tích thực tế về{sym_header}\n\n"
    reply += f"*Cập nhật lúc: {datetime.now(VN_TZ).strftime('%H:%M - %d/%m/%Y')}*\n\n"
    
    if symbol:
        sector = get_stock_sector(symbol)
        reply += f"- **Mã chứng khoán:** `{symbol}` (Nhóm ngành: {sector})\n"
    
    reply += "\n#### 1. Bối cảnh Dữ liệu & Thị trường Trực tiếp:\n"
    if "[DỮ LIỆU CỔ PHIẾU" in context_text:
        stock_part = context_text.split("[DỮ LIỆU CỔ PHIẾU")[1].split("[TIN TỨC")[0].strip()
        lines = [line.strip() for line in stock_part.split("\n") if line.strip().startswith("-")]
        for l in lines[:5]:
            reply += f"{l}\n"
    else:
        reply += "- Dữ liệu giao dịch đang được cập nhật từ hệ thống dữ liệu thị trường.\n"

    if "[DỮ LIỆU THỜI TIẾT THỊ TRƯỜNG & VĨ MÔ]" in context_text:
        macro_part = context_text.split("[DỮ LIỆU THỜI TIẾT THỊ TRƯỜNG & VĨ MÔ]")[1].split("\n\n")[0].strip()
        reply += "\n**Chỉ số vĩ mô tham chiếu:**\n"
        for m in macro_part.split("\n")[:4]:
            if m.strip().startswith("-"):
                reply += f"{m}\n"

    reply += "\n#### 2. Tin tức & Sự kiện Báo chí mới nhất trên mạng:\n"
    if sources:
        for idx, s in enumerate(sources[:4]):
            url_str = f" ([Đọc bài gốc]({s['url']}))" if s.get("url") else ""
            reply += f"- **{s.get('source', 'Tin tức')}:** {s['title']}{url_str}\n"
    else:
        reply += "- Chưa ghi nhận tin tức đột biến trong 24 giờ qua trên các kênh chính thống.\n"

    reply += "\n#### 3. Nhận định & Khuyến nghị thực chiến:\n"
    reply += "- **Theo dõi chu kỳ T+2.5:** Khi mở vị thế mới, cần lưu ý áp lực cung hàng về vào đầu phiên chiều ngày T+2 (khoảng 13h00 - 14h00).\n"
    reply += "- **Chiến lược:** Luôn xác định ngưỡng cắt lỗ (Stop Loss) tối đa 5-7% và giải ngân từng phần (20-30% vị thế) quanh các ngưỡng hỗ trợ mạnh.\n"

    return reply


def query_gemini_chat(
    message: str,
    history: Optional[List[Dict[str, str]]] = None,
    current_symbol: Optional[str] = None
) -> dict:
    """
    Xử lý truy vấn chatbox thông minh:
    1. Trích xuất bối cảnh mã cổ phiếu & vĩ mô.
    2. Gọi Gemini 2.5 Flash với Google Search Grounding để tra cứu Internet thời gian thực.
    3. Trả về câu trả lời kèm danh sách nguồn trích dẫn (citations) có thể bấm được.
    4. Tự động fallback linh hoạt sang công cụ tổng hợp định lượng khi không có khóa API.
    """
    clean_msg = message.strip()
    detected_symbol = _extract_symbol_from_query(clean_msg, current_symbol)
    context_text, pre_sources = _build_context_summary(detected_symbol)
    
    if llm_client.get_api_key():
        # Chuẩn bị lịch sử hội thoại
        formatted_contents = []
        if history:
            for h in history[-4:]:
                role = "user" if h.get("role") == "user" else "model"
                formatted_contents.append(types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=h.get("content", ""))]
                ))
        user_content_prompt = f"{clean_msg}\n\n---\n[THÔNG TIN THỰC TẾ & BỐI CẢNH THỊ TRƯỜNG HIỆN HÀNH]\n{context_text}"
        formatted_contents.append(types.Content(role="user", parts=[types.Part.from_text(text=user_content_prompt)]))

        try:
            # Failover nhiều model (429/quá tải → model kế tiếp; chỉ dừng khi khóa API sai)
            reply_text, model_name, response = llm_client.generate(
                formatted_contents, system=CHAT_SYSTEM_PROMPT, use_search=True, temperature=0.3, label="Chat",
            )
            extracted_sources = [
                {"title": s["title"], "url": s["url"], "source": "Google Live Search"}
                for s in llm_client.grounding_sources(response)
            ]
            # Nếu Gemini không trả về sources riêng thì bổ sung sources từ RSS đã thu thập
            final_sources = extracted_sources if extracted_sources else pre_sources[:4]
            if reply_text:
                return {
                    "reply": reply_text,
                    "sources": final_sources,
                    "grounded": bool(extracted_sources),
                    "symbol": detected_symbol,
                    "engine": f"Gemini ({model_name}) + Real-time Web Search"
                }
        except (llm_client.LLMAuthError, llm_client.LLMUnavailable) as e:
            logger.warning(f"Chat Gemini không khả dụng: {e}")

    # Fallback tự động khi không có API Key hoặc gặp lỗi kết nối
    fallback_text = _offline_synthesize_answer(clean_msg, detected_symbol, context_text, pre_sources)
    return {
        "reply": fallback_text,
        "sources": pre_sources[:4],
        "grounded": bool(pre_sources),
        "symbol": detected_symbol,
        "engine": "Financial Research Engine (Live Market & News RSS)"
    }
