# BÁO CÁO KIỂM TOÁN CHUYÊN SÂU & STRESS-TEST (DEEP AUDIT)
## TRỤ CỘT 3 (R3): KIẾN TRÚC TRÍ TUỆ NHÂN TẠO & PROMPT REASONING
## TRỤ CỘT 5 (R5): TRẢI NGHIỆM GIAO DIỆN & TÍNH THỰC CHIẾN (ACTIONABLE INSIGHTS)

**Hội đồng Chuyên gia Cấp cao:** Principal AI/LLM Engineer & Senior Frontend Specialist  
**Mã dự án:** `2-DU-AN-AI-CHUNG-KHOAN`  
**Ngày kiểm toán:** 08/11/2026  
**Chế độ kiểm toán:** Forensic Codebase Deep Audit & Stress-Test (Read-Only)  
**Tập tin mục tiêu:** `ai_analyzer.py`, `tro_ly_dau_tu_chung_khoan_vn.md`, `api.py`, `App.jsx`, `web/src/components/*`, `web/src/services/*`

---

## MỤC LỤC
1. [TỔNG QUAN ĐÁNH GIÁ & BẢNG ĐIỂM CHUYÊN GIA](#1-tổng-quan-đánh-giá--bảng-điểm-chuyên-gia)
2. [KIỂM TOÁN CHI TIẾT TRỤ CỘT 3 (R3) - AI, LLM & REASONING](#2-kiểm-toán-chi-tiết-trụ-cột-3-r3---ai-llm--reasoning)
   - 2.1. Kiểm soát Ảo giác (Hallucination) & Tính Cập nhật Dữ liệu
   - 2.2. Định dạng Đầu ra (Structured Outputs) & Schema Integrity
   - 2.3. Khả năng Chống chịu (Resilience), Quota & Xử lý Lỗi Gemini
3. [KIỂM TOÁN CHI TIẾT TRỤ CỘT 5 (R5) - FRONTEND & ACTIONABLE INSIGHTS](#3-kiểm-toán-chi-tiết-trụ-cột-5-r5---frontend--actionable-insights)
   - 3.1. Khảo sát Mã nguồn Giao diện & Kiến trúc Phân mảnh (Architectural Schism)
   - 3.2. Tính Năng Biểu Đồ & Tương Tác (Lightweight Charts, Markers, Sub-panes)
   - 3.3. Tính Thực Chiến của Khuyến Nghị (Actionable Insights)
   - 3.4. Hiệu năng & Rò rỉ Tài nguyên (Memory Leaks, Re-renders, ESLint Errors)
4. [BẢNG TỔNG HỢP PHÂN LOẠI LỖ HỔNG (P0 - P1 - P2)](#4-bảng-tổng-hợp-phân-loại-lỗ-hổng-p0---p1---p2)
5. [BẢN THIẾT KẾ KIẾN TRÚC THẾ HỆ MỚI (NEXT-GEN ARCHITECTURE ROADMAP)](#5-bản-thiết-kế-kiến-trúc-thế-hệ-mới-next-gen-architecture-roadmap)
   - 5.1. Tầng AI Engine Thế hệ Mới (Next-Gen AI Engine)
   - 5.2. Tầng Frontend Thế hệ Mới (Next-Gen Interactive Trading Frontend)
6. [KẾT LUẬN & KIẾN NGHỊ TRIỂN KHAI GIAI ĐOẠN 2](#6-kết-luận--kiến-nghị-triển-khai-giai-đoạn-2)

---

## 1. TỔNG QUAN ĐÁNH GIÁ & BẢNG ĐIỂM CHUYÊN GIA

Hội đồng Chuyên gia đã tiến hành rà soát từng dòng mã nguồn (line-by-line inspection), chạy thử nghiệm kịch bản lỗi biên (edge cases) và kiểm thử đối chuẩn với các tiêu chuẩn công nghiệp tài chính khắt khe nhất (Production-grade Financial Systems).

### Bảng Điểm Đánh Giá Hiện Trạng

| Trụ cột | Điểm số (1-10) | Trạng thái | Đánh giá tổng quan |
| :--- | :---: | :---: | :--- |
| **Trụ cột 3 (R3): Trí tuệ Nhân tạo & Prompt Chuyên sâu** | **5.5 / 10** | ⚠️ Nguy cơ Cao | Prompt Markdown công phu, đã áp dụng Pydantic Structured Output và Google GenAI SDK hiện đại. Tuy nhiên, **tầng dữ liệu đầu vào bị thiếu trắng dữ liệu BCTC cơ bản (FA) và dòng tiền khối ngoại**, buộc AI phải đoán mò/ảo giác; danh sách model dự phòng có model không tồn tại (`gemini-4-argon`); không có retry/backoff phân biệt lỗi client/server; schema thiếu ràng buộc logic giá. |
| **Trụ cột 5 (R5): Trải nghiệm Người dùng & Tính Thực chiến** | **4.5 / 10** | 🔴 Nghiêm trọng | Giao diện Dark theme có tính thẩm mỹ khá. Tuy nhiên, **tồn tại sự phân mảnh kiến trúc nghiêm trọng: toàn bộ thư mục `web/src/components/` bị bỏ rơi**, `App.jsx` đơn khối (monolithic) tự viết lại biểu đồ bị cắt cụt EMA/SMA/Volume; **hoàn toàn không có Buy/Sell markers trên nến (0%)**; hiệu ứng máy đánh chữ (Typewriter) gây nghẽn DOM cực độ (8ms/ký tự re-render 10.000 lần); khuyến nghị thực chiến bị giấu trong văn bản Markdown thô thay vì hiển thị trực quan dạng thẻ/badge. |

---

## 2. KIỂM TOÁN CHI TIẾT TRỤ CỘT 3 (R3) - AI, LLM & REASONING

### 2.1. Kiểm soát Ảo giác (Hallucination) & Tính Cập nhật Dữ liệu

#### Ưu điểm đã ghi nhận:
1. **Thiết kế System Prompt chuẩn mực:** Tệp `backend/prompts/tro_ly_dau_tu_chung_khoan_vn.md` (dòng 15-264) được xây dựng rất bài bản:
   - Quy định rõ vai trò "Trợ lý Đầu tư VN" đa chiều (Vĩ mô, Phân tích cơ bản, Kỹ thuật, Quản trị rủi ro - dòng 19-24).
   - Nguyên tắc cốt lõi: *"Dữ liệu là gốc. Chỉ dùng số liệu được cung cấp... Tuyệt đối không bịa giá, chỉ số, số liệu BCTC... Thiếu dữ liệu -> nói rõ 'Chưa có dữ liệu về...' "* (dòng 32).
   - Cấm ngôn ngữ kích động, cam kết lợi nhuận, cấm đoán mò giá tương lai không căn cứ (dòng 37-39).
   - Tách biệt rõ trạng thái phiên giao dịch đang diễn ra (*"phiên đang giao dịch, số liệu chưa chốt"*, dòng 93-100 `ai_analyzer.py`).
2. **Context Window Guard (Chống nhồi dữ liệu thô):**
   - Tại `backend/ai_analyzer.py:178`: `price_table_str = df[display_cols].tail(15).round(2).to_string()`. Hệ thống chỉ gửi bảng giá 15 phiên gần nhất thay vì nhồi 365 phiên nến thô, giúp bảo vệ Attention Mechanism của LLM, tránh hiện tượng *Lost-in-the-Middle*.

#### Lỗ hổng & Điểm yếu chí mạng:
1. **Ảo giác bắt buộc do thiếu hụt dữ liệu đầu vào (Forced Hallucination) [P0]:**
   - **Bằng chứng:** Tại `backend/ai_analyzer.py:202`:
     ```python
     "fundamentals": f"Nhóm ngành: {sector_name}. (Đánh giá nội lực kết hợp từ kiến thức tài chính và tin tức doanh nghiệp bên dưới)",
     ```
   - **Phân tích:** Biến `{fundamentals}` không hề chứa bất kỳ chỉ số tài chính cơ bản nào: **Không có P/E, không có P/B, không có ROE, không có Doanh thu, Lợi nhuận sau thuế, Nợ vay/VCSH hay EPS**.
   - **Hậu quả:** Khi prompt yêu cầu Gemini chấm điểm Bước 2 (*"Điểm Nội lực cơ bản & Chất xúc tác"*, thang điểm 0-100), Gemini không có dữ liệu thực tế tại thời điểm phân tích, buộc phải:
     - Hoặc bịa ra số liệu BCTC.
     - Hoặc lục tìm trong trọng số tiền huấn luyện (Pre-trained weights) vốn đã lỗi thời (outdated từ 2023 - 2024).
     - Bằng chứng thực tế trong file cache `backend/.cache/ai_report_FPT_None.json:11-13`: Gemini phải tự biện hộ: *"Tuy nhiên, dữ liệu đầu vào không cung cấp chất xúc tác cụ thể, rõ ràng cho FPT trong ngắn hạn..."* và chấm điểm cảm tính 60/100.
2. **Thiếu trắng dữ liệu Dòng tiền Khối ngoại & Giá trị giao dịch thị trường [P1]:**
   - **Bằng chứng:** Trong prompt mẫu `backend/prompts/tro_ly_dau_tu_chung_khoan_vn.md:297-298`:
     ```text
     - Giá trị giao dịch HOSE: {market_value} tỷ đồng
     - Khối ngoại mua/bán ròng: {foreign_net} tỷ đồng
     ```
   - Tuy nhiên, trong `backend/ai_analyzer.py:180-219`, `values` dictionary **hoàn toàn không định nghĩa 2 biến `market_value` và `foreign_net`**. Nhờ lớp bọc `_MissingAsNA`, chúng luôn luôn bị thay thế bằng `"N/A"`.
   - **Hậu quả:** Trí tuệ nhân tạo không nắm được hành vi của khối ngoại (mua/bán ròng trăm tỷ) và độ thanh khoản toàn sàn HOSE, làm tê liệt khả năng đánh giá dòng tiền tổ chức (Smart Money).

---

### 2.2. Định dạng Đầu ra (Structured Outputs) & Schema Integrity

#### Ưu điểm đã ghi nhận:
1. **Sử dụng Pydantic Schema chính thức với Google GenAI SDK:**
   - Tại `backend/ai_analyzer.py:28-61`, các lớp `ScoreDimension`, `FiveDimensionScores`, `ReportSummary`, `PricePredictionItem`, `StockAIReportSchema` được định nghĩa rõ ràng.
   - Tại `backend/ai_analyzer.py:380-384`, hệ thống áp dụng cơ chế native structured output:
     ```python
     response_format={
         "type": "text",
         "mime_type": "application/json",
         "schema": StockAIReportSchema.model_json_schema(),
     }
     ```
   - Tại `ai_analyzer.py:389`: Sử dụng `StockAIReportSchema.model_validate_json(output_text)` để xác thực cấu trúc trước khi trả về.

#### Lỗ hổng & Điểm yếu chí mạng:
1. **Lệch pha (Schema Drift) giữa System Prompt và Pydantic Schema [P0]:**
   - **Bằng chứng:** Trong file `tro_ly_dau_tu_chung_khoan_vn.md` PHẦN C (dòng 324-337), mẫu JSON chỉ có `analysis`, `summary`, và `predictions`. Nó **không hề mô tả cấu trúc `scores` gồm 5 chiều**.
   - Cấu trúc `scores` chỉ được nhắc đến thoáng qua ở câu hỏi trong `values["question"]` (`ai_analyzer.py:205`). Việc Pydantic schema bắt buộc có `scores` trong khi Prompt không định nghĩa tiêu chí chấm điểm 5 chiều khiến mô hình LLM phải tự suy diễn ý nghĩa các trường.
2. **Nguy cơ Crash do Không Tương thích Ngược Cache (Cache Backward-Incompatibility) [P0]:**
   - **Bằng chứng:** File cache cũ `backend/.cache/ai_report_FPT_None.json` và `ai_report_HPG_None.json` được tạo từ phiên bản trước **hoàn toàn không có trường `"summary"`** (stance, confidence, action).
   - Vì `StockAIReportSchema` định nghĩa `summary: ReportSummary = Field(...)` là trường bắt buộc (required, không có default), bất kỳ luồng nào deserialze cache cũ bằng schema mới sẽ lập tức bắn ra ngoại lệ `pydantic.ValidationError`, làm crash endpoint `/api/ai_report`.
3. **Thiếu Ràng buộc Logic Toán học trong Pydantic Validator [P1]:**
   - Trong `PricePredictionItem` (`ai_analyzer.py:47-53`):
     - Không có `@field_validator` hoặc `@model_validator` kiểm tra `high >= low`. LLM có thể trả về `high: 22.0, low: 23.5`.
     - Không kiểm tra `days_future > 0`. Bằng chứng thực tế trong file cache `ai_report_FPT_None.json:32, 38`: Gemini trả về `days_future: 0` cho cả 2 mốc "Morning" và "Afternoon", làm rối loạn thuật toán vẽ trục thời gian của frontend.
     - `overall_score` không có validator kiểm tra có nằm trong dải `[0, 100]` hay không.

---

### 2.3. Khả năng Chống chịu (Resilience), Quota & Xử lý Lỗi Gemini

#### Lỗ hổng & Điểm yếu chí mạng:
1. **Danh sách Candidate Models chứa Tên Mô hình Ảo / Không Hợp Lệ [P0]:**
   - **Bằng chứng:** Tại `backend/ai_analyzer.py:370`:
     ```python
     candidate_models = ["gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-4-argon"]
     ```
   - **Phân tích:** `gemini-4-argon` là định danh thử nghiệm nội bộ hoặc không tồn tại trên endpoint thương mại của Google GenAI.
   - Nếu tài khoản API của người dùng thuộc gói Free hoặc thông thường chỉ hỗ trợ `gemini-2.5-flash` hoặc `gemini-2.0-flash`, toàn bộ danh sách trên sẽ thất bại.
2. **Không phân biệt Lỗi Client (4xx) và Lỗi Server/Quota (5xx/429), Vòng lặp Failover Mù Quáng [P0]:**
   - **Bằng chứng:** Tại `backend/ai_analyzer.py:373-395`:
     ```python
     for model_name in candidate_models:
         try:
             ...
         except Exception as e:
             last_error = e
             print(f"[!] Model {model_name} gặp lỗi: {e}")
             continue
     ```
   - **Thử nghiệm thực tế:** Khi chạy thử với API Key không hợp lệ (`dummy_key_12345`), mã nguồn nhận lỗi `400 API_KEY_INVALID`. Thay vì dừng ngay lập tức, vòng lặp vẫn tiếp tục gửi thêm 2 request qua mạng tới `gemini-3.5-flash-lite` và `gemini-4-argon`.
   - Kết quả: Request bị treo hơn **8.5 giây** chỉ để nhận 3 lỗi giống hệt nhau!
   - Không có **Exponential Backoff** và **Jitter**: Khi gặp lỗi `429 Quota Exceeded` hoặc `503 Service Unavailable`, hệ thống không có độ trễ nghỉ (sleep) mà lập tức bắn tiếp, khiến IP dễ bị Google đưa vào blacklist rate-limit tạm thời.
   - Không có **Circuit Breaker**: Khi mạng mất kết nối hoặc API sập, 100 người dùng truy cập đồng thời sẽ tạo ra 300 cuộc gọi mạng vô vọng, làm tê liệt toàn bộ worker FastAPI.
3. **Chế độ Fallback Định lượng chưa được Cache Khi Offline [P1]:**
   - **Bằng chứng:** Tại `backend/api.py:222-225`:
     ```python
     is_fallback = "Chế độ Phân tích Định lượng Tự động" in ai_data.get("analysis", "")
     if api_key and api_key != "your_gemini_api_key_here" and not is_fallback:
         set_cache(cache_key, payload)
     ```
   - Nếu chạy ở chế độ offline (hoặc khi chưa nhập key), hệ thống **từ chối lưu cache bản fallback định lượng**. Mỗi lần người dùng click lại mã HPG, FPT..., backend lại phải tính toán lại từ đầu toàn bộ các chỉ báo và gọi lại các nguồn tin tức.

---

## 3. KIỂM TOÁN CHI TIẾT TRỤ CỘT 5 (R5) - FRONTEND & ACTIONABLE INSIGHTS

### 3.1. Khảo sát Mã nguồn Giao diện & Kiến trúc Phân mảnh (Architectural Schism)

#### Lỗ hổng Chí Mạng (P0): Phân mảnh Kiến trúc & Thư mục Component Bị Bỏ Rơi
Trong dự án hiện có 2 hệ thống mã nguồn Frontend song song:
1. **Hệ thống Modular Components (Được thiết kế rất chuẩn):**
   - `web/src/components/StockChart.jsx` (196 dòng - hỗ trợ nến, EMA10, SMA20, Volume histogram).
   - `web/src/components/AnalysisReport.jsx` (199 dòng - render Markdown, bảng biểu, điểm tin).
   - `web/src/components/PriceTargetsAndPeers.jsx` (116 dòng - bảng mục tiêu giá & so sánh cùng ngành).
   - `web/src/components/RadarScoreCard.jsx` (167 dòng - biểu đồ mạng nhện SVG 5 chiều & thanh tiến độ).
   - `web/src/components/Sidebar.jsx` (41 dòng - quản lý Watchlist).
   - `web/src/components/MacroTicker.jsx` (51 dòng - chỉ số vĩ mô VN-Index, VN30, Gold, Oil, USD/VND).
   - `web/src/services/apiClient.js` (55 dòng - cấu hình `API_BASE_URL` qua biến môi trường `VITE_API_BASE_URL`).
2. **Hệ thống Thực thi Thực tế (`web/src/App.jsx` - 581 dòng):**
   - **Sự thật kiểm toán:** File `App.jsx` **HOÀN TOÀN KHÔNG IMPORT BẤT KỲ COMPONENT NÀO Ở TRÊN** (xem dòng 1-4 `App.jsx`).
   - `App.jsx` là một tệp đơn khối khổng lồ (monolithic), tự viết lại toàn bộ giao diện:
     - Tự fetch trực tiếp URL cứng `http://127.0.0.1:8000/api/...` thay vì qua `apiClient.js` (dòng 40, 55, 63, 84, 99).
     - Tự khởi tạo biểu đồ Lightweight Charts nhưng **cắt bỏ hoàn toàn đường EMA10, SMA20 và Volume Histogram** (chỉ còn CandlestickSeries và AreaSeries).
     - Tự render lại mã SVG biểu đồ Radar và thanh tiến độ.
     - Tự parse chuỗi bảng Markdown một cách sơ sài.
   - **Hậu quả:** Nợ kỹ thuật (Technical Debt) nghiêm trọng. Mọi cải tiến, sửa lỗi trong thư mục `components/` đều không có tác dụng trên giao diện người dùng thực tế!

---

### 3.2. Tính Năng Biểu Đồ & Tương Tác (Lightweight Charts, Markers, Sub-panes)

#### Lỗ hổng Chí Mạng (P0): Hoàn Toàn Thiếu Vắng Điểm Mua/Bán (Buy/Sell Markers) Trên Biểu Đồ
- **Yêu cầu tại R5:** *"đánh dấu điểm Mua/Bán Buy/Sell markers trên nến"*.
- **Kết quả kiểm toán:** Kiểm tra toàn bộ mã nguồn frontend (`App.jsx`, `StockChart.jsx`), kết quả tìm kiếm hàm `setMarkers` hoặc `markers` là **HOÀN TOÀN BẰNG KHÔNG (0 kết quả)**.
- Người dùng khi nhìn vào biểu đồ nến chỉ thấy các cây nến lịch sử và một dải màu xanh `AreaSeries` vẽ trung bình giá dự báo trong tương lai. **Không hề có bất kỳ mũi tên, nhãn (label) hay marker đánh dấu điểm Vào lệnh (Buy), Điểm Chốt lời (Take Profit) hay Cắt lỗ (Stop Loss) trên trục giá/nến!**

#### Các điểm nghẽn tương tác biểu đồ khác [P1]:
1. **Thiếu hoàn toàn thanh công cụ biểu đồ (Chart Toolbar):**
   - Không có nút chọn khung thời gian (Timeframe selector): 1D, 1W, 1M, 3M, 6M, 1Y, All. Mặc định luôn load 365 phiên và fit content.
   - Không có công cụ vẽ kỹ thuật (Drawing Tools): Trendline, Support/Resistance horizontal lines, Fibonacci Retracement.
   - Không có nút Reset Zoom hoặc Fullscreen.
2. **Thiếu các khung chỉ báo phụ (Indicator Sub-panes):**
   - Dù backend tính toán đầy đủ `RSI`, `MACD`, `Signal`, `Histogram`, trên giao diện biểu đồ không hề có khung phụ (sub-pane) nào cho RSI hay MACD. Người dùng buộc phải nhìn số liệu chết dạng văn bản trong bảng Markdown.

---

### 3.3. Tính Thực Chiến của Khuyến Nghị (Actionable Insights)

#### Đánh giá tính thực chiến:
1. **Khuyến nghị bị chôn vùi trong văn bản Markdown thô [P1]:**
   - Mặc dù trong nội dung sinh ra của AI (hoặc bản fallback) có đề cập đến:
     - Giá mua tối ưu (Buy Zone)
     - Giá bán mục tiêu (Target Price 1, 2)
     - Mức giá cắt lỗ (Stop Loss)
     - Tỷ lệ Lợi nhuận / Rủi ro (R:R)
   - Nhưng tất cả những tham số sinh tử này **chỉ nằm trong chuỗi văn bản Markdown `analysis`** (dòng 304-307 `ai_analyzer.py` hoặc bảng mục 6 `tro_ly_dau_tu_chung_khoan_vn.md`).
2. **Thiếu các Widget hành động trực quan (Actionable Trading Widgets):**
   - Frontend không có các thẻ trực quan như:
     - **Thẻ Vùng Mua (Entry Box):** Kèm mức giá hiện tại đang cách vùng mua bao nhiêu %.
     - **Thẻ Chốt lời (Take Profit Targets):** Kèm tỷ lệ Upside % dự kiến.
     - **Thẻ Cắt lỗ Cảnh báo (Stop Loss Guard):** Hiển thị rõ ràng bằng màu đỏ với tỷ lệ rủi ro tối đa cho phép (ví dụ: `-7.0%`).
     - **Thẻ Tỷ trọng Khuyến nghị (Position Sizing):** Khuyến nghị giải ngân cụ thể bao nhiêu % tổng tài sản (ví dụ: `15% danh mục, chia làm 2 đợt giải ngân`).
   - Nhà đầu tư giao dịch thực chiến cần ra quyết định trong vài giây; việc bắt họ phải đọc qua 1.500 từ văn bản Markdown để tìm xem điểm cắt lỗ ở đâu là một rủi ro vận hành nghiêm trọng.

---

### 3.4. Hiệu năng & Rò rỉ Tài nguyên (Memory Leaks, Re-renders, ESLint Errors)

#### Lỗ hổng Chí Mạng (P0): Hiệu ứng Máy đánh chữ (Typewriter) Gây Đơ Nghẽn CPU Trình Duyệt
- **Bằng chứng:** Tại `web/src/App.jsx:118-122`:
  ```javascript
  typewriterRef.current = setInterval(() => {
      setTypedAnalysis((prev) => prev + text.charAt(i));
      i++;
      if (i >= text.length) clearInterval(typewriterRef.current);
  }, 8);
  ```
- **Phân tích cơ chế nghẽn:**
  - Báo cáo phân tích của Gemini thường dài từ **5.000 đến 10.000 ký tự**.
  - Hàm `setInterval` được cấu hình chạy mỗi **8 mili-giây**, mỗi nhịp chỉ nối thêm **1 ký tự đơn lẻ** (`text.charAt(i)`).
  - Điều này kích hoạt **5.000 đến 10.000 lần re-render component React liên tục** trong suốt 40 - 80 giây!
  - Trong mỗi lần re-render, tại dòng 561 `App.jsx`, hàm `formatReport(typedAnalysis)` lại được gọi: nó duyệt từng dòng, tách regex, tạo các thẻ `<h3>`, `<p>`, `<table>`, re-parse DOM từ đầu.
  - Trên các máy tính văn phòng hoặc thiết bị cấu hình trung bình, tab trình duyệt lập tức bị treo đơ (CPU spike 100%), thanh cuộn giật lag không thể tương tác.
  - **Memory Leak:** `typewriterRef.current` không có cơ chế dọn dẹp (cleanup) trong hook `useEffect` unmount. Nếu người dùng chuyển mã cổ phiếu liên tục, các interval cũ vẫn chạy ngầm trong bộ nhớ.
  - *Lưu ý:* File bị bỏ rơi `AnalysisReport.jsx:142-150` đã xử lý việc này thông minh hơn rất nhiều (tăng cụm 45 ký tự mỗi 18ms), nhưng đáng tiếc lại không được `App.jsx` sử dụng!

#### Lỗi Linting (ESLint Errors) trong Mã nguồn [P2]:
- Khi chạy `npm run lint` tại thư mục `web/`:
  - `web/src/App.jsx:47`: Lỗi `no-unused-vars` (biến `e` không sử dụng trong `fetchWatchlist`).
  - `web/src/App.jsx:234`: Lỗi `no-unused-vars` (biến `e` không sử dụng trong hàm xử lý ngày tháng).
  - `web/src/App.jsx:262`: Cảnh báo `react-hooks/exhaustive-deps` (thiếu `getSanitizedPredictions` trong dependency array của `useEffect` vẽ biểu đồ).
  - `web/src/components/AnalysisReport.jsx:135`: Lỗi React 19 `react-hooks/set-state-in-effect` (gọi `setState` đồng bộ ngay trong thân `useEffect` gây cascading render).

---

## 4. BẢNG TỔNG HỢP PHÂN LOẠI LỖ HỔNG (P0 - P1 - P2)

| Mã lỗi | Mức độ | Trụ cột | Vị trí (File:Dòng) | Tóm tắt Hiện tượng & Nguyên nhân Gốc rễ | Hậu quả Vận hành |
| :--- | :---: | :---: | :--- | :--- | :--- |
| **BUG-R3-01** | **P0** | R3 | `backend/ai_analyzer.py:202` | **Thiếu dữ liệu BCTC & Dòng tiền Khối ngoại:** `{fundamentals}` chỉ là chuỗi string giữ chỗ, không có P/E, P/B, ROE, Nợ; `{market_value}`, `{foreign_net}` bị bỏ quên luôn trả về `"N/A"`. | AI bắt buộc phải đoán mò (hallucinate) hoặc dùng kiến thức cũ 2-3 năm trước để chấm điểm cơ bản. |
| **BUG-R3-02** | **P0** | R3 | `backend/ai_analyzer.py:370-395` | **Model không hợp lệ & Không phân biệt lỗi 4xx/5xx:** `candidate_models` chứa `gemini-4-argon`; khi dính lỗi 400 API key không hợp lệ vẫn lặp gọi tiếp 3 model, không có retry backoff hay circuit breaker. | Treo mạng 8-15 giây vô nghĩa; dễ bị Google khóa rate-limit; nguy cơ crash hoặc nghẽn thread backend. |
| **BUG-R3-03** | **P0** | R3 | `backend/ai_analyzer.py:41, 55-61`<br>`backend/.cache/ai_report_*.json` | **Bất tương thích Cache & Thiếu Validator:** `StockAIReportSchema` bắt buộc có `summary`, trong khi các file cache thực tế không có trường này; thiếu validator kiểm tra `high >= low` và `days_future > 0`. | Ném ngoại lệ `ValidationError` làm sập endpoint `/api/ai_report` khi đọc cache; dự báo giá bị âm hoặc ngày trùng lặp (`days_future: 0`). |
| **BUG-R5-01** | **P0** | R5 | `web/src/App.jsx:196-255`<br>`web/src/components/StockChart.jsx` | **Hoàn toàn không có Buy/Sell Markers trên nến:** `setMarkers` chưa bao giờ được gọi trong toàn bộ codebase; biểu đồ chỉ có nến trần và vùng nón mờ. | Vi phạm nghiêm trọng yêu cầu trực quan hóa điểm mua/bán thực chiến của dự án. |
| **BUG-R5-02** | **P0** | R5 | `web/src/App.jsx:118-122, 351-405` | **Typewriter gây nghẽn CPU & DOM Re-render Catastrophic:** `setInterval(..., 8)` kích hoạt 5.000 - 10.000 lần re-render, mỗi lần đều parse lại toàn bộ bảng Markdown; không có cleanup khi unmount. | Làm đơ tab trình duyệt, giật lag giao diện, tiêu tốn 100% CPU trên máy người dùng, rò rỉ bộ nhớ. |
| **BUG-R5-03** | **P0** | R5 | `web/src/App.jsx:1-4`<br>`web/src/components/*` | **Phân mảnh Kiến trúc (Architectural Schism):** Toàn bộ thư mục `components/*` và `apiClient.js` bị bỏ rơi; `App.jsx` ôm đồm 581 dòng đơn khối, cắt bỏ chỉ báo EMA/SMA/Volume trên chart và hardcode URL API. | Mất khả năng bảo trì; tính năng biểu đồ bị thụt lùi so với code có sẵn; không thể cấu hình môi trường production. |
| **BUG-R3-04** | **P1** | R3 | `backend/ai_analyzer.py:386-388` | **Không bắt trạng thái Safety Filter:** Bỏ qua `finish_reason` khi Gemini chặn phản hồi vì bộ lọc an toàn, chỉ check `output_text` rỗng rồi failover. | Không thông báo được nguyên nhân bị chặn cho người dùng. |
| **BUG-R3-05** | **P1** | R3 | `backend/api.py:222-225` | **Không Cache Chế độ Fallback Định lượng:** Khi chạy offline hoặc chưa có API key, backend từ chối lưu cache, ép mọi request tính toán lại từ đầu. | Tăng thời gian phản hồi và gây tải thừa lên CPU backend khi offline. |
| **BUG-R5-04** | **P1** | R5 | `backend/ai_analyzer.py:55-61`<br>`web/src/App.jsx:530-568` | **Khuyến nghị Thực chiến bị chôn trong văn bản:** Entry Zone, TP1, TP2, Stop Loss, Position Sizing, R:R không có trường JSON có cấu trúc riêng mà chỉ là chuỗi Markdown dài. | Người dùng khó nắm bắt nhanh điểm cắt lỗ và vùng giải ngân trong phiên giao dịch biến động nhanh. |
| **BUG-R5-05** | **P1** | R5 | `web/src/App.jsx:183-222` | **Thiếu Thanh công cụ Biểu đồ & Chỉ báo Phụ:** Không có nút chọn khung thời gian (1D, 1W, 1M...), không có thanh công cụ vẽ kỹ thuật, không có pane riêng cho RSI/MACD. | Trải nghiệm phân tích kỹ thuật nghèo nàn, chưa đạt chuẩn trading workstation. |
| **BUG-R5-06** | **P2** | R5 | `web/src/App.jsx:47, 234, 262`<br>`web/src/components/AnalysisReport.jsx:135` | **Lỗi ESLint & Vi phạm React 19:** Biến không sử dụng, thiếu dependency trong `useEffect`, gọi `setState` đồng bộ trong effect body. | Nguy cơ cascading re-render và cảnh báo linting thất bại khi build CI/CD. |

---

## 5. BẢN THIẾT KẾ KIẾN TRÚC THẾ HỆ MỚI (NEXT-GEN ARCHITECTURE ROADMAP)

Để đưa hệ thống đạt chuẩn vận hành thương mại (Production Readiness), Hội đồng Chuyên gia đề xuất bản thiết kế kiến trúc nâng cấp thế hệ mới cho 2 tầng: **AI Engine** và **Frontend**.

```
+---------------------------------------------------------------------------------------------------+
|                                  NEXT-GEN AI TRADING WORKSTATION                                  |
+---------------------------------------------------------------------------------------------------+
                                                  |
                    +-----------------------------+-----------------------------+
                    |                                                           |
                    v                                                           v
+---------------------------------------+                   +---------------------------------------+
|          TẦNG AI ENGINE MỚI           |                   |          TẦNG FRONTEND MỚI            |
+---------------------------------------+                   +---------------------------------------+
| 1. Financial Context Engine:          |                   | 1. Unified Modular Architecture:      |
|    - Bơm FA thật: P/E, P/B, ROE, EPS  |                   |    - Tái cấu trúc App.jsx gọn nhẹ     |
|    - Bơm Khối ngoại, Tự doanh, Khớp   |                   |    - Tái sử dụng components/ hoàn toàn|
|                                       |                   |    - apiClient.js hỗ trợ env & retry  |
| 2. Pydantic Actionable Schema:        |                   |                                       |
|    - entry_zone: {min, max}           |                   | 2. Professional Charting Engine:      |
|    - take_profit_1, take_profit_2     |                   |    - Nến + EMA10/20 + SMA50 + Vol     |
|    - stop_loss, risk_reward_ratio     |                   |    - RSI & MACD Sub-panes riêng       |
|    - position_size_pct                |                   |    - Buy/Sell Markers trực tiếp nến   |
|    - Validators: high >= low, days>0  |                   |    - Timeframe bar: 1M, 3M, 6M, 1Y    |
|                                       |                   |                                       |
| 3. Smart Resilience & Failover:       |                   | 3. Actionable Insights HUD:           |
|    - Models chuẩn: 2.5-flash, 2.0     |                   |    - Trading Card: Buy, TP, SL, R:R   |
|    - Exponential Backoff + Jitter     |                   |    - Badges tỷ trọng giải ngân        |
|    - Fast-abort on 4xx Client Errors  |                   |    - Typewriter tối ưu (batch render) |
|    - Circuit Breaker pattern          |                   |                                       |
+---------------------------------------+                   +---------------------------------------+
```

### 5.1. Tầng AI Engine Thế hệ Mới (Next-Gen AI Engine)

#### 1. Bổ sung Tầng Thu thập Dữ liệu Cơ bản Thực tế (Financial Context Grounding):
- Tích hợp hàm `get_financial_ratios(symbol)` lấy từ nguồn tin cậy (`vnstock.stock(symbol).finance` hoặc API chứng khoán chính thống):
  - **P/E, P/B, ROE, ROA, EPS.**
  - **Tăng trưởng Doanh thu, Lợi nhuận ròng 4 quý gần nhất.**
  - **Nợ vay / Vốn chủ sở hữu (D/E).**
- Lấy số liệu mua/bán ròng của Khối ngoại và Tự doanh phiên gần nhất để bơm trực tiếp vào `{foreign_net}` và `{market_value}`.
- Khi có đủ số liệu thực tế, prompt của Gemini sẽ được neo vững chắc vào dữ kiện (Grounding), loại bỏ hoàn toàn hiện tượng bịa đặt số liệu.

#### 2. Nâng cấp Pydantic Schema Hỗ trợ Khuyến Nghị Thực Chiến (Actionable Schema):
Mở rộng `StockAIReportSchema` bổ sung cấu trúc giao dịch định lượng:
```python
class ActionableTradePlan(BaseModel):
    entry_min: float = Field(description="Vùng giá mua tối ưu thấp nhất")
    entry_max: float = Field(description="Vùng giá mua tối ưu cao nhất")
    take_profit_1: float = Field(description="Mục tiêu chốt lời ngắn hạn 1")
    take_profit_2: float = Field(description="Mục tiêu chốt lời kỳ vọng 2")
    stop_loss: float = Field(description="Mức giá cắt lỗ bắt buộc")
    risk_reward_ratio: float = Field(description="Tỷ lệ Lợi nhuận/Rủi ro (R:R, ví dụ: 2.5)")
    position_size_pct: int = Field(description="Tỷ trọng danh mục khuyến nghị (ví dụ: 15)")
    execution_strategy: str = Field(description="Kế hoạch giải ngân cụ thể (ví dụ: Chia 2 lần)")

class PricePredictionItem(BaseModel):
    timeframe: str
    days_future: int = Field(gt=0, description="Số ngày tương lai bắt buộc > 0")
    high: float
    low: float
    reason: str

    @model_validator(mode="after")
    def validate_price_bounds(self):
        if self.high < self.low:
            self.high, self.low = self.low, self.high
        return self

class StockAIReportSchema(BaseModel):
    overall_score: int = Field(ge=0, le=100)
    summary: Optional[ReportSummary] = Field(default_factory=...) # Backward-compatible
    scores: FiveDimensionScores
    trade_plan: Optional[ActionableTradePlan] = None # Dữ liệu thực chiến trực tiếp
    analysis: str
    predictions: List[PricePredictionItem]
```

#### 3. Bộ Quản Lý Khả Năng Chống Chịu (Smart AI Resilience Manager):
- **Phân loại mã lỗi:**
  - Nếu gặp lỗi Client `400 (API_KEY_INVALID)`, `401`, `403`: Lập tức dừng vòng lặp, chuyển sang `_build_technical_fallback` và cảnh báo rõ trên giao diện.
  - Nếu gặp lỗi Server `429 (Rate Limit)` hoặc `503`: Áp dụng thư viện `tenacity` retry tối đa 2 lần với Exponential Backoff kèm Jitter: `wait = min(4, 1.5 ** attempt + uniform(0, 0.5))`.
- **Danh sách mô hình thực tế:** Ưu tiên `["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]` theo đúng chính sách mô hình của Google Cloud API.
- **Safety Handling:** Đọc `interaction.finish_reason`. Nếu bị chặn, tự động kích hoạt fallback giải thích rõ do chính sách kiểm duyệt nội dung.

---

### 5.2. Tầng Frontend Thế hệ Mới (Next-Gen Interactive Trading Frontend)

#### 1. Hợp nhất Kiến trúc Frontend (Component Unification):
- Tái cấu trúc triệt để `App.jsx`: Loại bỏ toàn bộ 400 dòng code inline trùng lặp.
- Biến `App.jsx` thành tầng điều phối trạng thái (Orchestrator Container), nhập và sử dụng toàn bộ thư viện component sạch:
  - `<Sidebar />`
  - `<MacroTicker />`
  - `<StockChart />`
  - `<PriceTargetsAndPeers />`
  - `<RadarScoreCard />`
  - `<AnalysisReport />`
- Mọi cuộc gọi API chuyển sang dùng `apiClient.js` để đọc URL từ cấu hình môi trường `.env`.

#### 2. Tích hợp Điểm Mua/Bán (Buy/Sell Markers) Trên Biểu Đồ Lightweight Charts:
Trong `StockChart.jsx`, bổ sung hàm gắn markers tự động từ kế hoạch giao dịch của AI:
```javascript
// Tạo Markers trên nến
if (tradePlan && uniqueHistory.length > 0) {
    const lastSession = uniqueHistory[uniqueHistory.length - 1];
    const markers = [];
    
    if (tradePlan.entry_max) {
        markers.push({
            time: lastSession.time,
            position: 'belowBar',
            color: '#3fb950',
            shape: 'arrowUp',
            text: `MUA (${tradePlan.entry_min}-${tradePlan.entry_max})`,
        });
    }
    if (tradePlan.stop_loss) {
        markers.push({
            time: lastSession.time,
            position: 'aboveBar',
            color: '#f85149',
            shape: 'arrowDown',
            text: `CẮT LỖ (${tradePlan.stop_loss})`,
        });
    }
    candlestickSeries.setMarkers(markers);
}
```

#### 3. Bổ sung Chỉ báo Phụ & Bảng Điều Khiển Khuyến Nghị Thực Chiến (Actionable Insights HUD):
- **Khung phụ biểu đồ:** Thêm 1 panel nhỏ phía dưới biểu đồ chính hiển thị đường RSI(14) với 2 mốc biên 30 (quá bán) và 70 (quá mua).
- **Thanh HUD Hành Động (Actionable Trading HUD):** Đặt ngay trên đầu báo cáo với các thẻ chỉ số nổi bật:
  - 🟢 **Vùng Giải Ngân:** `23.00 - 23.40`
  - 🎯 **Mục Tiêu 1 / 2:** `25.50 (+9.4%) / 27.00 (+15.8%)`
  - 🛑 **Ngưỡng Cắt Lỗ:** `22.10 (-4.7%)`
  - ⚖️ **Tỷ Lệ R:R:** `1 : 2.0` (Đạt chuẩn)
  - 💼 **Tỷ Trọng Khuyến Nghị:** `15% danh mục`
- **Tối ưu hóa Typewriter:** Thay vì tick mỗi 8ms cho 1 ký tự đơn lẻ, áp dụng kỹ thuật batch rendering (40-50 ký tự mỗi 16ms) và tự động dừng khi người dùng cuộn xem báo cáo.

---

## 6. KẾT LUẬN & KIẾN NGHỊ TRIỂN KHAI GIAI ĐOẠN 2

Kết quả kiểm toán cho thấy hệ thống đã có nền móng khung sườn (skeleton) rất tốt về mặt ý tưởng và công nghệ hiện đại (FastAPI, Google GenAI SDK, Lightweight Charts, React 19). Tuy nhiên, những khiếm khuyết trong **tính toàn vẹn dữ liệu (BCTC/Dòng tiền)**, **resilience của API Gemini**, **sự phân mảnh mã nguồn giao diện** và **sự thiếu vắng Buy/Sell markers** đang ngăn cản dự án đạt tiêu chuẩn vận hành thực chiến.

### Danh mục Khắc phục Trọng tâm cho Giai đoạn 2 (P0 Remediation):
1. **[Backend AI]** Sửa `ai_analyzer.py` loại bỏ model ảo `gemini-4-argon`, thay bằng các model chuẩn (`gemini-2.5-flash`, `gemini-2.0-flash`). Bổ sung cơ chế dừng ngay lập tức khi gặp lỗi Client 400/401 và thêm xử lý fallback an toàn.
2. **[Backend AI]** Cập nhật `StockAIReportSchema` cho phép `summary` là trường tùy chọn (optional) có giá trị mặc định để tương thích 100% với các file cache hiện có. Thêm Pydantic validators cho `days_future > 0` và `high >= low`.
3. **[Frontend]** Tái cấu trúc `App.jsx`, kết nối hoàn toàn với các component trong `web/src/components/`, kích hoạt lại đường EMA10, SMA20 và Volume histogram trên biểu đồ.
4. **[Frontend]** Triển khai hàm `setMarkers` trên `CandlestickSeries` để trực quan hóa điểm Mua / Cắt lỗ / Chốt lời trực tiếp trên nến.
5. **[Frontend]** Thay thế triệt để vòng lặp Typewriter 8ms gây nghẽn CPU bằng cơ chế render tối ưu hoặc hiển thị trực tiếp an toàn.
6. **[Testing]** Bổ sung dependency `httpx` vào `backend/requirements.txt` để bộ kiểm thử tự động `test_api.py` có thể thực thi thành công.

---
*Báo cáo được hoàn thành và phê duyệt bởi Hội đồng Chuyên gia Cấp cao (Principal AI/LLM Engineer & Senior Frontend Specialist).*
