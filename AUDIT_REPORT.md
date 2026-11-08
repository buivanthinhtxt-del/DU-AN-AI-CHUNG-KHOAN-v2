# BÁO CÁO KIỂM TOÁN TOÀN DIỆN HỆ THỐNG & KẾ HOẠCH NÂNG CẤP KIẾN TRÚC THẾ HỆ MỚI
## (COMPREHENSIVE DEEP AUDIT REPORT & NEXT-GEN ARCHITECTURE ROADMAP)

**Dự án:** Trợ lý Phân tích Kỹ thuật & Đầu tư Chứng khoán AI Việt Nam (`2-DU-AN-AI-CHUNG-KHOAN`)  
**Cơ quan thực hiện:** Hội đồng Chuyên gia Cấp cao (Senior Expert Council)
- *CTO & Distributed Systems Architect*
- *Senior Quantitative Trader & Lead Financial Analyst*
- *Principal AI/LLM Engineer & Senior Frontend Specialist*
- *Senior Technical Writer & System Architect*

**Thời điểm hoàn thành kiểm toán:** 08/11/2026  
**Chế độ kiểm toán:** Forensic Codebase Deep Audit, Mathematical Proof Verification & Concurrency Stress-Test  
**Trạng thái hệ thống:** Prototype / Alpha Stage — **CHƯA ĐỦ ĐIỀU KIỆN SẴN SÀNG VẬN HÀNH (NOT PRODUCTION READY)**  

---

## MỤC LỤC BÁO CÁO

1. [PHẦN 1: BẢNG ĐIỂM ĐÁNH GIÁ HIỆN TRẠNG (5 TRỤ CỘT CỐT LÕI)](#phần-1-bảng-điểm-đánh-giá-hiện-trạng-5-trụ-cột-cốt-lõi)
   - 1.1. Ma trận Điểm số & Đánh giá Tổng thể Hệ thống
   - 1.2. Đánh giá Trụ cột 1: Nghiệp vụ Chứng khoán Thực chiến tại Việt Nam (3.0 / 10)
   - 1.3. Đánh giá Trụ cột 2: Tính Tức thời & Hạ tầng Dữ liệu Đa nguồn (3.5 / 10)
   - 1.4. Đánh giá Trụ cột 3: Trí tuệ Nhân tạo & Prompt Chuyên sâu (5.5 / 10)
   - 1.5. Đánh giá Trụ cột 4: Hiệu năng, Kiến trúc Backend & An toàn Dữ liệu (3.0 / 10)
   - 1.6. Đánh giá Trụ cột 5: Trải nghiệm Người dùng & Tính Thực chiến (4.5 / 10)
   - 1.7. Kết luận Trạng thái Vận hành
2. [PHẦN 2: DANH SÁCH CÁC LỖ HỔNG CHẾT NGƯỜI (CRITICAL VULNERABILITIES & BOTTLENECKS - P0)](#phần-2-danh-sách-các-lỗ-hổng-chết-người-critical-vulnerabilities--bottlenecks---p0)
   - P0-DATA-01: Look-ahead Bias làm rò rỉ nến tương lai vào tập dữ liệu quá khứ
   - P0-TA-01: Sai lệch thuật toán RSI Wilder & Lỗi chia cho 0 biến siêu cổ phiếu thành trung tính
   - P0-RES-01: Nguồn dữ liệu TCBS chết hoàn toàn trên vnstock 3.5.1
   - P0-PERF-01: Blocking I/O mạng và AI làm đóng băng FastAPI Uvicorn Event Loop
   - P0-RES-02: Race Condition & Phá hủy file Cache JSON do ghi đồng thời không nguyên tử
   - P0-SEC-01: CORS Wildcard kèm Credentials & Rò rỉ Exception raw ra Client
   - P0-FIN-01: Lạc hậu chu kỳ thanh toán T+3 và Lỗi cộng ngày lịch thay vì ngày giao dịch
   - P0-AI-01: Thiếu dữ liệu BCTC và Dòng tiền Khối ngoại gây ảo giác bắt buộc (Forced Hallucination)
   - P0-AI-02: Mô hình ảo `gemini-4-argon`, thiếu Retry/Backoff và không Fast-Abort lỗi Client 4xx
   - P0-AI-03: Bất tương thích ngược Cache do thiếu trường `summary` bắt buộc
   - P0-FE-01: Hoàn toàn không có Buy/Sell Markers trên biểu đồ nến
   - P0-FE-02: Hiệu ứng Typewriter 8ms gây nghẽn CPU và Re-render DOM thảm khốc
   - P0-FE-03: Phân mảnh kiến trúc Frontend & Bỏ rơi toàn bộ thư mục `web/src/components/`
   - P0-TEST-01: Thiếu dependency `httpx` làm gãy hoàn toàn bộ kiểm thử tự động
   - Bảng tổng hợp các khiếm khuyết mức P1 (Major) và P2 (Minor)
3. [PHẦN 3: DANH SÁCH CÁC GÓC KHUẤT & EDGE CASES THỊ TRƯỜNG CHƯA TÍNH TỚI](#phần-3-danh-sách-các-góc-khuất--edge-cases-thị-trường-chưa-tính-tới)
   - 3.1. Cổ phiếu bị Đình chỉ / Tạm ngừng / Hủy niêm yết (Bị nhầm với lỗi gõ sai mã 404)
   - 3.2. Hiện tượng Bẫy sàn "Múa Bên Trăng" (Trắng bên mua / Floor Lock) làm vô hiệu lệnh cắt lỗ
   - 3.3. Điều chỉnh Giá Kỹ thuật do Cổ tức / Thưởng (Ngày GDKHQ) gây nhảy vọt giả chỉ báo
   - 3.4. Đặc thù Giá Tham chiếu Sàn UPCoM (Giá bình quân gia quyền thay vì Giá đóng cửa)
   - 3.5. Phiên ngoài giờ, ban đêm, cuối tuần, ngày nghỉ lễ (Thiếu Market Session State Machine)
   - 3.6. Lệch pha thời gian dữ liệu Tin tức và Vĩ mô khi tra cứu lịch sử (`target_date`)
4. [PHẦN 4: BẢN THIẾT KẾ ĐỀ XUẤT NÂNG CẤP KIẾN TRÚC THẾ HỆ MỚI (NEXT-GEN ARCHITECTURE ROADMAP)](#phần-4-bản-thiết-kế-đề-xuất-nâng-cấp-kiến-trúc-thế-hệ-mới-next-gen-architecture-roadmap)
   - 4.1. Sơ đồ Tổng thể Kiến trúc 4 Tầng Phân lớp (Next-Gen Architecture Diagram)
   - 4.2. Tầng 1: Resilient Vietnam Market Data Pipeline
   - 4.3. Tầng 2: High-Performance Backend & Hybrid Two-Tier Cache
   - 4.4. Tầng 3: Institutional AI Reasoning & Actionable Trade Engine
   - 4.5. Tầng 4: Actionable Frontend Trading Workstation
5. [KẾ HOẠCH HÀNH ĐỘNG GIAI ĐOẠN 2 (P0 REMEDIATION & VERIFICATION MATRIX)](#kế-hoạch-hành-động-giai-đoạn-2-p0-remediation--verification-matrix)

---

## PHẦN 1: BẢNG ĐIỂM ĐÁNH GIÁ HIỆN TRẠNG (5 TRỤ CỘT CỐT LÕI)

### 1.1. Ma trận Điểm số & Đánh giá Tổng thể Hệ thống

Dưới sự chủ trì của Hội đồng Chuyên gia Cấp cao, toàn bộ mã nguồn của dự án `2-DU-AN-AI-CHUNG-KHOAN` đã được kiểm toán pháp y (Forensic Audit), đối chiếu từng dòng mã nguồn với các nguyên tắc kiến trúc hệ thống phân tán, chuẩn mực định lượng tài chính và quy định thực tế của thị trường chứng khoán Việt Nam (VSDC, HOSE, HNX, UPCoM).

| STT | Trụ cột Đánh giá | Trọng số | Điểm số (1-10) | Điểm Trọng số | Trạng thái Chuyên môn |
| :---: | :--- | :---: | :---: | :---: | :--- |
| **1** | **Nghiệp vụ Chứng khoán Thực chiến tại Việt Nam (R1)** | 25% | **3.0 / 10** | 0.75 | 🔴 **Cực kỳ Nghiêm trọng (Critical Gaps)** |
| **2** | **Tính Tức thời & Hạ tầng Dữ liệu Đa nguồn (R2)** | 20% | **3.5 / 10** | 0.70 | 🔴 **Nghiêm trọng (Math & Bias Flaws)** |
| **3** | **Trí tuệ Nhân tạo & Prompt Chuyên sâu (R3)** | 20% | **5.5 / 10** | 1.10 | ⚠️ **Cảnh báo Rủi ro (Hallucination Risks)** |
| **4** | **Hiệu năng, Kiến trúc Backend & An toàn Dữ liệu (R4)** | 20% | **3.0 / 10** | 0.60 | 🔴 **Cực kỳ Nghiêm trọng (Deadlock & Race)** |
| **5** | **Trải nghiệm Người dùng & Tính Thực chiến (R5)** | 15% | **4.5 / 10** | 0.68 | 🔴 **Nghiêm trọng (Schism & Missing Markers)** |
| **TỔNG**| **HỆ THỐNG ĐÁNH GIÁ TỔNG HỢP** | **100%** | **3.83 / 10** | **3.83 / 10** | ⛔ **CHƯA ĐỦ ĐIỀU KIỆN SẴN SÀNG VẬN HÀNH** |

---

### 1.2. Đánh giá Trụ cột 1: Nghiệp vụ Chứng khoán Thực chiến tại Việt Nam (3.0 / 10)

- **Điểm số:** **3.0 / 10**
- **Nhận định của Hội đồng:** Hệ thống có ý tưởng nghiệp vụ và xây dựng tài liệu prompt (`backend/prompts/tro_ly_dau_tu_chung_khoan_vn.md`) tương đối chi tiết. Tuy nhiên, giữa tài liệu và mã nguồn thực thi thực tế có sự **đứt gãy hoàn toàn**.
- **Dẫn chứng cụ thể từ mã nguồn:**
  1. *Lạc hậu chu kỳ thanh toán:* Tại `backend/ai_analyzer.py:48` và `backend/ai_analyzer.py:328`, hệ thống vẫn định nghĩa `"T+3 (Hàng về)"` với `days_future = 3`. Quy định T+3 đã bị VSDC bãi bỏ từ ngày 29/08/2022 để chuyển sang T+2.5 (hàng về lúc 11:30 - 12:00 trưa và được giao dịch lúc 13:00 ngày T+2).
  2. *Lỗi lẫn lộn ngày lịch và ngày giao dịch:* Tại `web/src/App.jsx:136-140` và `web/src/components/PriceTargetsAndPeers.jsx:13-18`, hàm `formatPredictionDate` cộng trực tiếp số mili-giây của ngày lịch (`daysFuture * 24 * 3600 * 1000`). Nếu phiên gần nhất là Thứ Sáu, các điểm dự báo T+1 và T+2 sẽ rơi thẳng vào **Thứ Bảy và Chủ Nhật** — thời điểm thị trường hoàn toàn đóng cửa.
  3. *Bỏ rơi biến Dòng tiền Khối ngoại:* Mặc dù tài liệu prompt tại `backend/prompts/tro_ly_dau_tu_chung_khoan_vn.md:298` khai báo biến `{foreign_net}`, nhưng trong `backend/ai_analyzer.py:180-210` hàm `build_user_prompt()`, lập trình viên **quên đưa biến này vào dictionary `values`**. Do đó, AI luôn luôn nhận giá trị `"N/A"`, làm mất hoàn toàn dữ liệu dòng tiền khối ngoại — biến số dẫn dắt quan trọng nhất của thị trường VN.
  4. *Giả lập dữ liệu Phân tích Cơ bản (FA):* Tại `backend/ai_analyzer.py:202`, trường `fundamentals` bị gán chuỗi giữ chỗ: `"Nhóm ngành: {sector_name}. (Đánh giá nội lực kết hợp từ kiến thức tài chính và tin tức doanh nghiệp bên dưới)"`. Không hề có P/E, P/B, ROE, EPS, Nợ vay. Trong chế độ Fallback (`backend/ai_analyzer.py:257`), điểm cơ bản bị gán chết `62/100`.
  5. *Nhận diện phiên giao dịch mù quáng:* Tại `backend/ai_analyzer.py:93-100`, hàm `_session_label` chỉ kiểm tra `now.hour < 15`. Khi người dùng truy vấn lúc 2h sáng hoặc sáng Chủ Nhật, hệ thống vẫn gắn nhãn ngây ngô: `"(phiên đang giao dịch, số liệu chưa chốt)"`.

---

### 1.3. Đánh giá Trụ cột 2: Tính Tức thời & Hạ tầng Dữ liệu Đa nguồn (3.5 / 10)

- **Điểm số:** **3.5 / 10**
- **Nhận định của Hội đồng:** Phân hệ dữ liệu tồn tại lỗi nghiêm trọng phá hủy tính trung thực toán học và khả năng chống chịu sự cố của hệ thống.
- **Dẫn chứng cụ thể từ mã nguồn:**
  1. *Look-ahead Bias rò rỉ nến tương lai:* Tại `backend/data_fetcher.py:90-98`, mã nguồn cộng thêm 1 ngày vào `target_date`:
     ```python
     end_date = datetime.strptime(target_date, '%Y-%m-%d') + timedelta(days=1)
     ```
     Vì hàm `Quote.history` của thư viện `vnstock` coi tham số `end` là **inclusive (bao gồm cả ngày kết thúc)**, nên khi người dùng yêu cầu phân tích ngày `2026-05-03`, hệ thống lại lấy cả nến ngày `2026-05-04` (chứng thực tại `backend/.cache/market_data_HPG_2026-05-03.json:2104`). Dữ liệu ngày tương lai bị nạp vào chuỗi nến quá khứ, khiến mọi chỉ báo kỹ thuật và phân tích của AI bị "gian lận dữ liệu tương lai".
  2. *Sai lệch công thức RSI & Bug chia 0:* Tại `backend/data_fetcher.py:58-63`:
     ```python
     gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
     loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
     rs = gain / loss.replace(0, np.nan)
     df['RSI'] = 100 - (100 / (1 + rs))
     df['RSI'] = df['RSI'].fillna(50)
     ```
     Hệ thống sử dụng Rolling SMA thay vì phương pháp làm mượt hàm mũ của J. Welles Wilder (Wilder's RMA với $\alpha = 1/14$). Nghiêm trọng hơn, khi cổ phiếu tăng trần 14 phiên liên tiếp ($loss = 0$), dòng `loss.replace(0, np.nan)` kết hợp `fillna(50)` biến RSI của siêu cổ phiếu từ mức quá mua cực độ (100.0) về **50.0 (Trung tính)**! Thực nghiệm trên mã HPG cho thấy độ lệch RSI lên tới **15.94 điểm** ở nến quyết định.
  3. *Nguồn dữ liệu dự phòng có nguồn chết:* Tại `backend/data_fetcher.py:102`, danh sách `for source in ('VCI', 'TCBS', 'KBS'):` chứa nguồn `'TCBS'`. Trong phiên bản `vnstock 3.5.1`, lớp `Quote` ném ngay ngoại lệ `ValueError: Lớp Quote chỉ nhận giá trị tham số source là kbs, vci, msn, dnse...`. Nguồn này luôn luôn chết và làm chậm thời gian truy vấn.
  4. *Méo mó thanh khoản nến trong ngày:* Tại `backend/data_fetcher.py:77` và `backend/ai_analyzer.py:254`, khối lượng dở dang của phiên sáng (ví dụ mới chạy 1 tiếng) được so sánh trực tiếp với `VolMA20` của cả ngày, khiến hệ thống luôn báo động sai lầm rằng *"dòng tiền suy kiệt, thanh khoản biến mất"*.

---

### 1.4. Đánh giá Trụ cột 3: Trí tuệ Nhân tạo & Prompt Chuyên sâu (5.5 / 10)

- **Điểm số:** **5.5 / 10**
- **Nhận định của Hội đồng:** Điểm sáng của hệ thống là System Prompt được xây dựng công phu, có sử dụng Google GenAI SDK hiện đại (`client.interactions.create`) và Pydantic Structured Outputs. Tuy nhiên, hệ thống bị trừ điểm nặng do rủi ro ảo giác và cơ chế xử lý lỗi thiếu chuyên nghiệp.
- **Dẫn chứng cụ thể từ mã nguồn:**
  1. *Ảo giác bắt buộc (Forced Hallucination):* Do dữ liệu BCTC cơ bản và dòng tiền khối ngoại bị khuyết trắng tại `backend/ai_analyzer.py:202`, khi prompt yêu cầu chấm điểm Bước 2 (*Nội lực cơ bản & Chất xúc tác*), mô hình Gemini bắt buộc phải bịa đặt số liệu hoặc lấy kiến thức cũ từ dữ liệu tiền huấn luyện 2023-2024 (chứng thực tại `backend/.cache/ai_report_FPT_None.json:11`).
  2. *Model ảo không tồn tại:* Tại `backend/ai_analyzer.py:370`:
     ```python
     candidate_models = ["gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-4-argon"]
     ```
     Định danh `gemini-4-argon` không tồn tại trên các endpoint thương mại của Google Cloud GenAI API.
  3. *Thiếu Exponential Backoff & Fast-Abort:* Tại `backend/ai_analyzer.py:373-395`, vòng lặp failover qua các model bắt mọi ngoại lệ bằng `except Exception as e:`. Khi người dùng truyền sai API Key (lỗi HTTP 400 `API_KEY_INVALID`), hệ thống không dừng lại mà tiếp tục thử tiếp các model sau, làm request bị treo vô ích hơn 8.5 giây. Khi gặp lỗi 429 Quota Exceeded, hệ thống không áp dụng thuật toán Exponential Backoff kèm Jitter.
  4. *Bất tương thích ngược Schema:* Tại `backend/ai_analyzer.py:41, 55-61`, lớp `StockAIReportSchema` định nghĩa trường `summary: ReportSummary = Field(...)` là bắt buộc. Trong khi đó, các file cache cũ trong hệ thống hoàn toàn không có trường này, dẫn đến nguy cơ bắn ngoại lệ `ValidationError` làm sập endpoint `/api/ai_report`.

---

### 1.5. Đánh giá Trụ cột 4: Hiệu năng, Kiến trúc Backend & An toàn Dữ liệu (3.0 / 10)

- **Điểm số:** **3.0 / 10**
- **Nhận định của Hội đồng:** Kiến trúc backend vi phạm các nguyên tắc cốt lõi của xử lý bất đồng bộ trong Python/FastAPI, chứa đựng các rủi ro chết người về mặt an toàn dữ liệu và bảo mật thông tin.
- **Dẫn chứng cụ thể từ mã nguồn:**
  1. *Blocking I/O làm đóng băng Event Loop:* Tại `backend/api.py:84, 107, 169, 203, 209`, các endpoint được khai báo bất đồng bộ `async def` nhưng bên trong lại gọi các hàm chặn đồng bộ:
     - `future_df.result(timeout=45)` (chặn luồng chính Uvicorn tới 45s).
     - `analyze_stock_data(...)` (gọi HTTP đồng bộ tới Gemini từ 5 - 15 giây).
     - Kết nối SQLite đồng bộ `sqlite3.connect()` trong các hàm watchlist.
     Hậu quả: Chỉ cần 1 người dùng gửi request phân tích, toàn bộ Event Loop của Uvicorn bị phong tỏa; tất cả người dùng khác đều bị treo (Request Starvation/Freezing).
  2. *Bùng nổ luồng hệ điều hành (Thread Pool Explosion):* Mã nguồn khởi tạo `with ThreadPoolExecutor(...)` cục bộ liên tục trên từng request (`backend/api.py:97, 196`, `backend/data_fetcher.py:178`, `backend/macro_fetcher.py:53`, `backend/news_fetcher.py:62`). Một request đơn lẻ kích hoạt tới 17 luồng hệ điều hành. Dưới tải 20 người dùng đồng thời, hơn 340 luồng OS tranh chấp CPU, gây thrashing và suy kiệt bộ nhớ.
  3. *Race Condition phá hủy Cache File:* Tại `backend/cache_manager.py:22-23` và `44-45`:
     ```python
     with open(cache_file, "w", encoding="utf-8") as f:
         json.dump(data, f, ensure_ascii=False, indent=2)
     ```
     Thao tác mở file `"w"` cắt ngắn file về 0 byte (truncate) mà không có khóa file (file locking). Khi có truy vấn đọc đồng thời, `json.load(f)` đọc phải file rỗng và bắn ra ngoại lệ `json.decoder.JSONDecodeError`. Trên Windows, hai tiến trình cùng mở ghi sẽ ném `PermissionError: [WinError 32]`, làm crash request.
  4. *Lỗ hổng CORS & Lộ thông tin nhạy cảm:* Tại `backend/api.py:48-54`, cấu hình `allow_origins=["*"]` đi kèm `allow_credentials=True` vi phạm tiêu chuẩn bảo mật W3C/RFC 6454. Tại `backend/api.py:109, 166, 232`, mã nguồn trả về `raise HTTPException(status_code=500, detail=str(e))`, phơi bày toàn bộ đường dẫn tuyệt đối ổ đĩa Windows (`d:\2- LÀM VIỆC\...`) và cấu trúc mã nguồn nội bộ ra client.
  5. *Gãy bộ kiểm thử tự động:* Tại `backend/tests/test_api.py:2`, import `from fastapi.testclient import TestClient` thất bại ngay lập tức với `RuntimeError: The starlette.testclient module requires the httpx package to be installed` vì `httpx` bị bỏ quên trong `backend/requirements.txt`.

---

### 1.6. Đánh giá Trụ cột 5: Trải nghiệm Người dùng & Tính Thực chiến (4.5 / 10)

- **Điểm số:** **4.5 / 10**
- **Nhận định của Hội đồng:** Giao diện có thẩm mỹ Dark theme hiện đại, nhưng tồn tại sự phân mảnh kiến trúc nghiêm trọng, hiệu năng trình duyệt kém và thiếu hoàn toàn các tính năng thực chiến cốt lõi theo yêu cầu của dự án.
- **Dẫn chứng cụ thể từ mã nguồn:**
  1. *Phân mảnh kiến trúc Frontend:* Dự án có thư mục component mô-đun được xây dựng bài bản (`web/src/components/StockChart.jsx`, `AnalysisReport.jsx`, `PriceTargetsAndPeers.jsx`, `RadarScoreCard.jsx`, `apiClient.js`). Nhưng tại `web/src/App.jsx:1-4`, file `App.jsx` **hoàn toàn không import bất kỳ component nào trong số đó**. File `App.jsx` là một tệp đơn khối 581 dòng tự viết lại biểu đồ bị cắt xén (mất EMA10, SMA20, Volume), tự render SVG radar và hardcode URL API `http://127.0.0.1:8000`.
  2. *Hoàn toàn không có Buy/Sell Markers trên biểu đồ (0%):* Cả trong `App.jsx` và `StockChart.jsx`, hàm `setMarkers` của thư viện Lightweight Charts chưa từng được gọi. Biểu đồ nến không hề có mũi tên, nhãn hay đánh dấu điểm Mua (Buy), Điểm Chốt lời (Take Profit) hay Điểm Cắt lỗ (Stop Loss) trên nến.
  3. *Typewriter gây nghẽn CPU và giật lag DOM:* Tại `web/src/App.jsx:118-122`:
     ```javascript
     typewriterRef.current = setInterval(() => {
         setTypedAnalysis((prev) => prev + text.charAt(i));
         i++;
         if (i >= text.length) clearInterval(typewriterRef.current);
     }, 8);
     ```
     Với báo cáo dài 5.000 - 10.000 ký tự, `setInterval(..., 8)` kích hoạt 5.000 - 10.000 lần re-render component React liên tục. Mỗi lần re-render, hàm `formatReport` lại parse lại toàn bộ cú pháp Markdown và bảng biểu từ đầu, khiến tab trình duyệt bị đơ cứng, CPU nhảy vọt 100% và gây rò rỉ bộ nhớ khi chuyển mã cổ phiếu liên tục.
  4. *Khuyến nghị thực chiến bị giấu trong văn bản:* Điểm mua tối ưu, mục tiêu chốt lời, ngưỡng cắt lỗ bắt buộc và tỷ lệ R:R bị chôn vùi trong chuỗi Markdown `analysis`, không được bóc tách thành các thẻ trực quan (Actionable Trading HUD/Widgets) giúp trader ra quyết định tức thì.

---

### 1.7. Kết luận Trạng thái Vận hành

> **KẾT LUẬN CỦA HỘI ĐỒNG CHUYÊN GIA CẤP CAO:**  
> Hệ thống hiện tại đang ở trạng thái Prototype / Alpha Testing và **HOÀN TOÀN CHƯA ĐỦ ĐIỀU KIỆN SẴN SÀNG VẬN HÀNH THỰC TẾ (NOT PRODUCTION READY)**.  
> Các lỗi Look-ahead Bias, sai thuật toán RSI, đóng băng Event Loop, Race condition phá hỏng file cache, cùng sự phân mảnh frontend là những rào cản nghiêm trọng đe dọa trực tiếp đến tính an toàn tài chính và độ tin cậy của toàn hệ thống.  
> **Toàn bộ 14 lỗ hổng mức P0 dưới đây bắt buộc phải được khắc phục trực tiếp trong Giai đoạn 2.**

---

## PHẦN 2: DANH SÁCH CÁC LỖ HỔNG CHẾT NGƯỜI (CRITICAL VULNERABILITIES & BOTTLENECKS - P0)

Hội đồng Chuyên gia đã xác lập danh mục 14 lỗ hổng nghiêm trọng mức P0 (Blocker/Critical). Dưới đây là phân tích chi tiết nguyên nhân gốc rễ, trích dẫn mã nguồn và hậu quả của từng lỗ hổng:

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                DANH MỤC 14 LỖ HỔNG CHÍ MẠNG MỨC P0                              │
├─────────────────┬─────────────────────────────────────────────────┬─────────────────────────────┤
│ Mã Lỗ Hổng      │ Phân Hệ & Vị Trí Phát Hiện                      │ Bản Chất Khiếm Khuyết       │
├─────────────────┼─────────────────────────────────────────────────┼─────────────────────────────┤
│ P0-DATA-01      │ backend/data_fetcher.py:90-98                   │ Look-ahead Bias (Nến tương  │
│                 │                                                 │ lai lọt vào quá khứ)        │
│ P0-TA-01        │ backend/data_fetcher.py:58-63                   │ Sai thuật toán RSI Wilder & │
│                 │                                                 │ Bug chia 0 (Lệch 50 điểm)   │
│ P0-RES-01       │ backend/data_fetcher.py:102                     │ Nguồn TCBS chết trên        │
│                 │                                                 │ vnstock 3.5.1               │
│ P0-PERF-01      │ backend/api.py:84,107,169,203,209               │ Blocking I/O làm đóng băng  │
│                 │                                                 │ FastAPI Event Loop          │
│ P0-RES-02       │ backend/cache_manager.py:22-23,44-45            │ Race Condition & Hỏng file  │
│                 │                                                 │ JSON Cache                  │
│ P0-SEC-01       │ backend/api.py:48-54,109,166,232                │ CORS Wildcard & Lộ lọt      │
│                 │                                                 │ Exception raw               │
│ P0-FIN-01       │ backend/ai_analyzer.py:48,328; App.jsx:136-140  │ Lạc hậu T+3 & Nhầm ngày     │
│                 │                                                 │ lịch với ngày giao dịch     │
│ P0-AI-01        │ backend/ai_analyzer.py:202                      │ Thiếu dữ liệu BCTC & Dòng   │
│                 │                                                 │ tiền khối ngoại             │
│ P0-AI-02        │ backend/ai_analyzer.py:370-395                  │ Model ảo `gemini-4-argon`,  │
│                 │                                                 │ thiếu Retry & Fast-Abort    │
│ P0-AI-03        │ backend/ai_analyzer.py:41,55-61                 │ Bất tương thích ngược cache │
│                 │                                                 │ do thiếu trường `summary`   │
│ P0-FE-01        │ web/src/App.jsx & StockChart.jsx                │ Hoàn toàn không có Buy/Sell │
│                 │                                                 │ markers trên nến (0%)       │
│ P0-FE-02        │ web/src/App.jsx:118-122                         │ Typewriter 8ms gây nghẽn    │
│                 │                                                 │ CPU & DOM Re-render         │
│ P0-FE-03        │ web/src/App.jsx:1-4                             │ Phân mảnh kiến trúc, bỏ rơi │
│                 │                                                 │ components/                 │
│ P0-TEST-01      │ backend/tests/test_api.py:2; requirements.txt   │ Thiếu dependency `httpx`    │
│                 │                                                 │ làm gãy bộ test             │
└─────────────────┴─────────────────────────────────────────────────┴─────────────────────────────┘
```

---

### Lỗ hổng 1: P0-DATA-01 — Look-ahead Bias làm rò rỉ nến tương lai vào tập dữ liệu quá khứ
- **Phân loại:** P0 (Critical Financial Blocker)
- **Vị trí chính xác:** `backend/data_fetcher.py`, dòng 90–98.
- **Hiện tượng quan sát được:**
  Khi người dùng hoặc hệ thống backtest yêu cầu phân tích dữ liệu tại một mốc lịch sử cụ thể, ví dụ `target_date = '2026-05-03'` (ngày Chủ Nhật), tập dữ liệu DataFrame trả về lại chứa nến giao dịch của ngày hôm sau (`2026-05-04` - ngày Thứ Hai) với giá đóng cửa 27.60 và khối lượng 32.374.300 cổ phiếu (chứng thực tại `backend/.cache/market_data_HPG_2026-05-03.json:2104-2110`).
- **Nguyên nhân gốc rễ:**
  Lập trình viên cộng thêm 1 ngày vào `target_date`:
  ```python
  if target_date:
      end_date = datetime.strptime(target_date, '%Y-%m-%d') + timedelta(days=1)
  ```
  Trong khi đó, API của `vnstock` xử lý tham số `end` theo dạng **INCLUSIVE (bao gồm cả ngày kết thúc)**. Do mã nguồn hoàn toàn không có bộ lọc hậu kỳ `df = df[df.index <= target_date]`, toàn bộ phiên giao dịch của ngày hôm sau đã bị hấp thụ vào chuỗi dữ liệu lịch sử.
- **Hậu quả nếu không xử lý:**
  Các chỉ báo EMA, RSI, MACD bị bóp méo do hấp thụ trước giá của tương lai. Nến cuối cùng chuyển cho AI phân tích (`latest = df.iloc[-1]`) là giá của ngày mai. Mọi quyết định khuyến nghị và kết quả kiểm thử quá khứ (Backtest) đều trở thành gian lận định lượng (Data Leakage), hoàn toàn vô giá trị trong thực tế.

---

### Lỗ hổng 2: P0-TA-01 — Sai thuật toán RSI Wilder & Lỗi chia cho 0 biến siêu cổ phiếu thành trung tính
- **Phân loại:** P0 (Critical Quantitative Math Blocker)
- **Vị trí chính xác:** `backend/data_fetcher.py`, dòng 58–63.
- **Hiện tượng quan sát được:**
  Chỉ số RSI của hệ thống bị lệch nghiêm trọng so với biểu đồ chuẩn của TradingView và các CTCK. Khi một cổ phiếu tăng trần liên tiếp 14 phiên, hệ thống tính ra RSI = **50.0 (Trung tính)** thay vì 100.0 (Quá mua cực độ). Trên mã HPG thực tế, độ lệch RSI lên tới **15.94 điểm** ở nến quyết định (Hệ thống tính 26.09 trong khi RSI Wilder chuẩn là 42.03).
- **Nguyên nhân gốc rễ:**
  ```python
  gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
  loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
  rs = gain / loss.replace(0, np.nan)
  df['RSI'] = 100 - (100 / (1 + rs))
  df['RSI'] = df['RSI'].fillna(50)
  ```
  1. Dùng Rolling SMA thay vì phương pháp làm mượt hàm mũ chuẩn quốc tế của J. Welles Wilder Jr. (1978): $\text{RMA} = \text{EMA}(\alpha = 1/14)$. Rolling SMA gây ra hiện tượng "vách đá" (cliff effect) khi một phiên biến động mạnh 14 ngày trước rơi ra khỏi cửa sổ trượt.
  2. Lỗi chia cho 0: Khi chuỗi nến không có phiên giảm ($loss = 0$), dòng `loss.replace(0, np.nan)` biến mẫu số thành NaN, phép chia `gain / NaN` ra NaN, và `fillna(50)` ép chỉ số về 50.0!
- **Hậu quả nếu không xử lý:**
  Hệ thống phát tín hiệu bắt đáy giả (False Oversold Alert) khi RSI rớt về 26.09 trong khi thị trường thực tế vẫn ở mức cân bằng 42.03, hoặc báo cổ phiếu siêu nóng tăng trần là "trung tính 50", dẫn dụ nhà đầu tư vào bẫy rủi ro tài chính cực lớn.

---

### Lỗ hổng 3: P0-RES-01 — Nguồn dữ liệu TCBS chết hoàn toàn trên vnstock 3.5.1
- **Phân loại:** P0 (Critical Data Pipeline Blocker)
- **Vị trí chính xác:** `backend/data_fetcher.py`, dòng 102.
- **Hiện tượng quan sát được:**
  Mỗi lần hàm `get_historical_data` fallback sang nguồn TCBS, console lập tức xuất hiện lỗi:
  `ValueError: Lớp Quote chỉ nhận giá trị tham số source là kbs, vci, msn, dnse, binance, fmp, fmarket.`
- **Nguyên nhân gốc rễ:**
  Thư viện `vnstock` phiên bản `3.5.1` cài đặt trong dự án đã loại bỏ hoàn toàn tham số `source='TCBS'` trong class `Quote`. Lập trình viên hardcode danh sách `('VCI', 'TCBS', 'KBS')` mà không kiểm tra tính tương thích của thư viện.
- **Hậu quả nếu không xử lý:**
  Khi nguồn VCI gặp sự cố mạng hoặc rate-limit, hệ thống chuyển sang TCBS và văng ngoại lệ ngay lập tức, làm mất một nguồn dữ liệu dự phòng quan trọng, kéo dài thời gian phản hồi và làm tăng tỷ lệ request thất bại về 0%.

---

### Lỗ hổng 4: P0-PERF-01 — Blocking I/O làm đóng băng FastAPI Uvicorn Event Loop
- **Phân loại:** P0 (Critical Architecture & Concurrency Blocker)
- **Vị trí chính xác:** `backend/api.py`, dòng 84, 107, 169, 203, 209; `backend/api.py:236-252`.
- **Hiện tượng quan sát được:**
  Khi một người dùng gửi request phân tích mã cổ phiếu (mất khoảng 10-15 giây để gọi AI và tải mạng), toàn bộ ứng dụng web bị đơ. Các người dùng khác truy cập trang chủ hoặc tải Watchlist đều bị quay vòng tròn (hanging) và không nhận được phản hồi.
- **Nguyên nhân gốc rễ:**
  Trong kiến trúc bất đồng bộ FastAPI, hàm `async def` chạy trực tiếp trên luồng chính của Event Loop. Tuy nhiên, mã nguồn lại thực thi các lệnh đồng bộ nặng nề trực tiếp trong thân hàm:
  - `df = future_df.result(timeout=45)`: Chặn đứng Event Loop để đợi luồng con.
  - `analysis_json_str = analyze_stock_data(...)`: Lệnh gọi HTTP đồng bộ tới Gemini SDK kéo dài từ 5 - 15 giây.
  - `sqlite3.connect()` và `conn.commit()` trong các endpoint Watchlist: Chặn I/O đĩa đồng bộ.
- **Hậu quả nếu không xử lý:**
  Hệ thống hoàn toàn mất khả năng phục vụ đồng thời. Chỉ cần 2-3 người dùng bấm phân tích cùng lúc, hàng đợi Uvicorn sẽ bị quá tải, gây nghẽn tắc hoàn toàn (Request Starvation/Denial of Service).

---

### Lỗ hổng 5: P0-RES-02 — Race Condition & Hỏng file JSON Cache do ghi đồng thời không nguyên tử
- **Phân loại:** P0 (Critical Concurrency & Data Integrity Blocker)
- **Vị trí chính xác:** `backend/cache_manager.py`, dòng 22–23 và 44–45.
- **Hiện tượng quan sát được:**
  Khi có nhiều truy vấn đồng thời cùng truy cập vào một mã cổ phiếu, hệ thống bắn ra lỗi crash:
  `json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)`  
  Hoặc trên hệ điều hành Windows:
  `PermissionError: [WinError 32] The process cannot access the file because it is being used by another process`
- **Nguyên nhân gốc rễ:**
  ```python
  with open(cache_file, "w", encoding="utf-8") as f:
      json.dump(data, f, ensure_ascii=False, indent=2)
  ```
  1. Thao tác `open(..., "w")` lập tức truncate file về 0 byte. Nếu đúng tích tắc đó luồng khác đọc file, nó sẽ nhận file rỗng 0 byte, gây sập bộ giải mã JSON.
  2. Không có cơ chế khóa tệp (File Lock) và không sử dụng cơ chế ghi tệp tạm thời rồi đổi tên nguyên tử (`tempfile` + `os.replace`).
- **Hậu quả nếu không xử lý:**
  Các file cache JSON trong thư mục `.cache/` bị hỏng thành file rỗng 0 byte. Mọi truy vấn tiếp theo tới file đó đều ném lỗi HTTP 500 cho client, làm tê liệt tính năng bộ nhớ đệm của toàn bộ hệ thống.

---

### Lỗ hổng 6: P0-SEC-01 — CORS Wildcard kèm Credentials & Rò rỉ Exception raw ra Client
- **Phân loại:** P0 (Critical Security & Information Leakage Blocker)
- **Vị trí chính xác:** `backend/api.py`, dòng 48–54 và các dòng 109, 166, 232.
- **Hiện tượng quan sát được:**
  Trình duyệt web hiện đại chặn các kết nối API có credentials do xung đột chính sách bảo mật CORS. Khi server gặp lỗi nội bộ, giao diện client hiển thị nguyên văn chuỗi lỗi chứa đường dẫn tuyệt đối ổ cứng Windows trên máy chủ phát triển.
- **Nguyên nhân gốc rễ:**
  1. Cấu hình CORS sai chuẩn W3C/RFC 6454:
     ```python
     app.add_middleware(
         CORSMiddleware,
         allow_origins=["*"],
         allow_credentials=True,
         ...
     )
     ```
  2. Bắt lỗi cẩu thả và ném thẳng chuỗi Exception nội bộ ra ngoài:
     `raise HTTPException(status_code=500, detail=str(e))`
- **Hậu quả nếu không xử lý:**
  Lỗ hổng bảo mật nghiêm trọng: kẻ tấn công có thể khai thác tấn công CSRF thông qua trình duyệt người dùng; đồng thời cấu trúc thư mục, tên tài khoản hệ điều hành và thông tin SDK nhạy cảm bị phơi bày hoàn toàn qua thông báo lỗi HTTP 500.

---

### Lỗ hổng 7: P0-FIN-01 — Lạc hậu chu kỳ T+3 và Lỗi cộng ngày lịch thay vì ngày giao dịch
- **Phân loại:** P0 (Critical Financial Domain Blocker)
- **Vị trí chính xác:** `backend/ai_analyzer.py:48, 328`; `web/src/App.jsx:136-140`; `web/src/components/PriceTargetsAndPeers.jsx:13-18`.
- **Hiện tượng quan sát được:**
  Hệ thống hiển thị khung dự báo `"T+3 (Hàng về)"`. Trên biểu đồ dự báo giá tương lai, các điểm mục tiêu giá hiển thị ngày rơi vào **Thứ Bảy và Chủ Nhật**.
- **Nguyên nhân gốc rễ:**
  1. Backend dùng chu kỳ T+3 đã bãi bỏ từ năm 2022 thay vì chu kỳ T+2.5 hiện hành.
  2. Frontend tính ngày dự báo bằng cách cộng ngày lịch:
     `new Date(lastDate.getTime() + (daysFuture * 24 * 3600 * 1000))`
     Thay vì phải duyệt qua lịch ngày giao dịch (Trading Days Calendar - loại bỏ Thứ Bảy, Chủ Nhật và ngày nghỉ lễ).
- **Hậu quả nếu không xử lý:**
  Làm sai lệch thời điểm quản trị rủi ro hàng về của nhà đầu tư (thực tế hàng về lúc 13h00 T+2 để bán ngay phiên chiều). Hiển thị ngày dự báo vào ngày nghỉ lễ/cuối tuần phá hủy hoàn toàn uy tín chuyên môn của một sản phẩm tư vấn tài chính.

---

### Lỗ hổng 8: P0-AI-01 — Thiếu dữ liệu BCTC và Dòng tiền Khối ngoại gây ảo giác bắt buộc
- **Phân loại:** P0 (Critical AI Domain Blocker)
- **Vị trí chính xác:** `backend/ai_analyzer.py`, dòng 180–210.
- **Hiện tượng quan sát được:**
  Mô hình AI Gemini đưa ra các nhận định chung chung, tự nhận *"không có dữ liệu chất xúc tác cụ thể"* hoặc bịa đặt các chỉ số tài chính cơ bản trong bài phân tích (chứng thực tại `backend/.cache/ai_report_FPT_None.json:11-13`).
- **Nguyên nhân gốc rễ:**
  1. Biến `{fundamentals}` bị gán cứng chuỗi placeholder rỗng không chứa P/E, P/B, ROE, EPS hay Nợ/VCSH.
  2. Biến `{foreign_net}` và `{market_value}` trong System Prompt hoàn toàn bị bỏ quên trong dict `values` của `build_user_prompt()`, luôn luôn nhận giá trị `"N/A"`.
- **Hậu quả nếu không xử lý:**
  Vi phạm trực tiếp nguyên tắc *"Dữ liệu là gốc - Grounding"* của hệ thống AI. LLM rơi vào trạng thái ảo giác bắt buộc (Forced Hallucination), làm sai lệch toàn bộ điểm số nội lực doanh nghiệp và phán đoán sai xu hướng dòng tiền lớn.

---

### Lỗ hổng 9: P0-AI-02 — Mô hình ảo `gemini-4-argon`, thiếu Retry/Backoff và không Fast-Abort lỗi Client 4xx
- **Phân loại:** P0 (Critical AI Resilience Blocker)
- **Vị trí chính xác:** `backend/ai_analyzer.py`, dòng 370–395.
- **Hiện tượng quan sát được:**
  Khi người dùng nhập sai API Key hoặc API Key hết hạn, request bị treo cứng hơn 8.5 giây. Console in ra hàng loạt thông báo lỗi lặp lại trên các model.
- **Nguyên nhân gốc rễ:**
  1. Danh sách `candidate_models` chứa định danh `gemini-4-argon` không tồn tại trên endpoint Google Cloud thương mại.
  2. Vòng lặp `for model_name in candidate_models` không phân biệt giữa lỗi Client (HTTP 400 Invalid Key, 403 Forbidden) và lỗi Server/Quota (HTTP 429, 503). Khi gặp lỗi 400, hệ thống vẫn tiếp tục gửi thêm 2 request qua mạng tới các model tiếp theo.
  3. Hoàn toàn thiếu vắng cơ chế Exponential Backoff có Jitter và Circuit Breaker.
- **Hậu quả nếu không xử lý:**
  Lãng phí băng thông mạng, làm chậm thời gian phản hồi của backend một cách vô nghĩa; dễ dàng bị Google đưa địa chỉ IP vào danh sách đen do gửi request sai liên tục khi gặp lỗi xác thực.

---

### Lỗ hổng 10: P0-AI-03 — Bất tương thích ngược Cache do thiếu trường `summary` bắt buộc
- **Phân loại:** P0 (Critical Schema Integrity Blocker)
- **Vị trí chính xác:** `backend/ai_analyzer.py`, dòng 41, 55–61 và `backend/api.py:176`.
- **Hiện tượng quan sát được:**
  Khi đọc lại các file cache phân tích cũ được tạo trước đó (`backend/.cache/ai_report_FPT_None.json`, `ai_report_HPG_None.json`), ứng dụng có nguy cơ sập với ngoại lệ `pydantic.ValidationError: Field required: summary`.
- **Nguyên nhân gốc rễ:**
  Lớp `StockAIReportSchema` được cập nhật thêm trường `summary: ReportSummary = Field(...)` là trường bắt buộc (không có default value). Các bản ghi cache cũ trong thư mục `.cache/` không hề có trường này.
- **Hậu quả nếu không xử lý:**
  Toàn bộ dữ liệu cache phân tích AI trước đó bị vô hiệu hóa, gây sập endpoint `/api/ai_report` khi người dùng tra cứu các mã cổ phiếu đã có cache.

---

### Lỗ hổng 11: P0-FE-01 — Hoàn toàn không có Buy/Sell Markers trên biểu đồ nến
- **Phân loại:** P0 (Critical UI/UX & Functional Blocker)
- **Vị trí chính xác:** `web/src/App.jsx:196-255` và `web/src/components/StockChart.jsx`.
- **Hiện tượng quan sát được:**
  Người dùng mở biểu đồ chỉ nhìn thấy chuỗi nến lịch sử và một dải mờ dự báo tương lai. Hoàn toàn không có bất kỳ mũi tên MUA (xanh lá), CẮT LỖ (đỏ) hay CHỐT LỜI nào trên thân nến.
- **Nguyên nhân gốc rễ:**
  Hàm `setMarkers` của thư viện Lightweight Charts chưa từng được gọi ở bất kỳ đâu trong toàn bộ codebase.
- **Hậu quả nếu không xử lý:**
  Vi phạm trực tiếp yêu cầu nghiệm thu cốt lõi của R5 (*"đánh dấu điểm Mua/Bán Buy/Sell markers trên nến"*), tước bỏ công cụ trực quan hóa quan trọng nhất của nhà đầu tư kỹ thuật.

---

### Lỗ hổng 12: P0-FE-02 — Hiệu ứng Typewriter 8ms gây nghẽn CPU và Re-render DOM thảm khốc
- **Phân loại:** P0 (Critical Frontend Performance Blocker)
- **Vị trí chính xác:** `web/src/App.jsx`, dòng 118–122 và dòng 561.
- **Hiện tượng quan sát được:**
  Mỗi khi nhận báo cáo AI, tab trình duyệt bị đơ lag dữ dội, quạt tản nhiệt máy tính quay mạnh, thanh cuộn giật khựng, không thể click chuyển tab hay thao tác trên trang web.
- **Nguyên nhân gốc rễ:**
  `setInterval` được đặt chu kỳ **8 mili-giây**, mỗi nhịp chỉ nối thêm **1 ký tự đơn lẻ**. Với báo cáo dài 8.000 ký tự, component React bị ép re-render 8.000 lần liên tục! Mỗi lần re-render, hàm `formatReport` lại chạy lại toàn bộ biểu thức chính quy (Regex) để parse lại bảng Markdown từ đầu.
- **Hậu quả nếu không xử lý:**
  Làm suy kiệt tài nguyên CPU của máy người dùng (CPU spike 100%), gây trải nghiệm tồi tệ và nguy cơ sập trình duyệt trên các thiết bị di động hoặc máy tính văn phòng.

---

### Lỗ hổng 13: P0-FE-03 — Phân mảnh kiến trúc Frontend & Bỏ rơi toàn bộ thư mục `components/`
- **Phân loại:** P0 (Critical Frontend Architectural Blocker)
- **Vị trí chính xác:** `web/src/App.jsx`, dòng 1–4.
- **Hiện tượng quan sát được:**
  Các component được viết rất tốt trong `web/src/components/` (như `StockChart.jsx` có đủ EMA10, SMA20, Volume; `apiClient.js` có cấu hình biến môi trường) hoàn toàn không có tác dụng gì trong ứng dụng.
- **Nguyên nhân gốc rễ:**
  `App.jsx` hoàn toàn không import thư mục `components/`. Thay vào đó, nó ôm đồm toàn bộ 581 dòng code đơn khối, tự viết lại biểu đồ bị cắt xén tính năng và gọi cứng URL API `http://127.0.0.1:8000`.
- **Hậu quả nếu không xử lý:**
  Gây phân mảnh mã nguồn, nợ kỹ thuật trầm trọng, không thể triển khai ứng dụng lên môi trường Production có domain/port khác `localhost:8000`.

---

### Lỗ hổng 14: P0-TEST-01 — Thiếu dependency `httpx` làm gãy hoàn toàn bộ kiểm thử tự động
- **Phân loại:** P0 (Critical Testing & CI/CD Blocker)
- **Vị trí chính xác:** `backend/tests/test_api.py:2` và `backend/requirements.txt`.
- **Hiện tượng quan sát được:**
  Chạy lệnh `python backend/tests/test_api.py` lập tức bị dừng với ngoại lệ:
  `RuntimeError: The starlette.testclient module requires the httpx package to be installed.`
- **Nguyên nhân gốc rễ:**
  FastAPI TestClient phụ thuộc vào gói `httpx`, nhưng gói này hoàn toàn không được liệt kê trong `backend/requirements.txt`.
- **Hậu quả nếu không xử lý:**
  Không thể thực hiện bất kỳ bài kiểm tra tích hợp tự động nào để xác minh tính ổn định của hệ thống trước và sau khi sửa lỗi.

---

### Bảng tổng hợp các khiếm khuyết mức P1 (Major) và P2 (Minor)

| Mã lỗi | Mức độ | Phân hệ | Tệp tin & Dòng mã | Tóm tắt Hiện tượng |
| :--- | :---: | :---: | :--- | :--- |
| **P1-ARCH-01** | **P1** | Backend | `api.py:97,196`; `data_fetcher.py:178` | Bùng nổ luồng hệ điều hành do liên tục tạo ThreadPool mới trên từng request (17 threads/req). |
| **P1-RES-03** | **P1** | Pipeline | `data_fetcher.py:102-127` | Thiếu Circuit Breaker và Exponential Backoff khi API nguồn bị nghẽn mạng hoặc quá tải. |
| **P1-CACHE-01**| **P1** | Cache | `api.py:91,103,176` | Cache tĩnh theo giây (1800s), không nhận biết các thời khắc đóng/mở phiên then chốt (ATO, ATC). |
| **P1-SEC-02** | **P1** | Security | `api.py:46-56` | Hoàn toàn không có Rate Limiting (chống DDoS hoặc cạn kiệt Quota Gemini). |
| **P1-TA-02** | **P1** | Quant | `data_fetcher.py:77`; `ai_analyzer.py:254` | Méo mó thanh khoản nến trong ngày (so sánh Volume dở dang với VolMA20 cả ngày). |
| **P1-FIN-02** | **P1** | Market | `ai_analyzer.py:93-100` | Thiếu Market Session State Machine (không phân biệt giờ giao dịch, trưa, đêm, cuối tuần). |
| **P1-DATA-02**| **P1** | Pipeline | `data_fetcher.py:85-129` | Thiếu cơ chế ghép nến Intraday Realtime (Synthetic Candle). |
| **P1-UI-01** | **P1** | Frontend | `App.jsx:183-222` | Thiếu khung chỉ báo phụ riêng cho RSI và MACD Histogram. |
| **P2-DB-01** | **P2** | Database | `database.py:9-46` | SQLite chưa bật chế độ Write-Ahead Logging (`PRAGMA journal_mode=WAL;`). |
| **P2-CACHE-02**| **P2** | Cache | `cache_manager.py:9-47` | Tích tụ rác ổ cứng (Disk space leak do file cache hết hạn không bao giờ bị xóa). |
| **P2-WEB-01** | **P2** | Frontend | `App.jsx:47, 234, 262` | Các lỗi cảnh báo ESLint (unused variables, exhaustive-deps). |

---

## PHẦN 3: DANH SÁCH CÁC GÓC KHUẤT & EDGE CASES THỊ TRƯỜNG CHƯA TÍNH TỚI

Một hệ thống phân tích chứng khoán chuyên nghiệp không thể chỉ hoạt động trong điều kiện thị trường lý tưởng. Dưới đây là 6 góc khuất và ca biên (Edge Cases) thị trường Việt Nam mà hệ thống hiện tại chưa tính tới:

### 3.1. Cổ phiếu bị Đình chỉ / Tạm ngừng / Hủy niêm yết (Suspension & Delisting)
- **Bản chất nghiệp vụ:** Trên thị trường chứng khoán Việt Nam, các cổ phiếu dính sai phạm báo cáo tài chính hoặc vi phạm pháp luật nghiêm trọng (như FLC, ROS, TGG, IBC, POM, SJF...) sẽ bị Sở GDCK đình chỉ giao dịch từng phần (chỉ cho giao dịch phiên chiều), tạm ngừng giao dịch hoặc hủy niêm yết bắt buộc.
- **Hành vi hiện tại của hệ thống:**
  Hàm `get_historical_data` tải dữ liệu 365 ngày qua. Nếu cổ phiếu đã bị đình chỉ hơn 1 năm, hàm trả về DataFrame rỗng. Tại `backend/api.py:130` hoặc `188`, hệ thống ném ra lỗi:
  `HTTPException(404, "Không tìm thấy dữ liệu lịch sử hoặc mã cổ phiếu không hợp lệ")`
- **Hậu quả & Rủi ro:**
  Hệ thống đánh đồng một cổ phiếu bị đình chỉ (rủi ro pháp lý/mất trắng vốn cực lớn) với việc người dùng gõ sai chính tả mã cổ phiếu. Nguy hiểm hơn, nếu cổ phiếu mới bị tạm ngừng giao dịch 2 tuần trước, hệ thống vẫn hiển thị nến cũ nhất như thể cổ phiếu đang hoạt động bình thường, đưa ra khuyến nghị kỹ thuật vô nghĩa và đẩy nhà đầu tư vào rủi ro chôn vốn vĩnh viễn.

---

### 3.2. Hiện tượng Bẫy sàn "Múa Bên Trăng" (Trắng bên mua / Floor Lock) làm vô hiệu lệnh cắt lỗ
- **Bản chất nghiệp vụ:**
  Biên độ dao động trần/sàn tại Việt Nam được kiểm soát nghiêm ngặt: $\pm 7\%$ (HOSE), $\pm 10\%$ (HNX), và $\pm 15\%$ (UPCoM). Khi thị trường hoảng loạn hoặc cổ phiếu có thông tin tiêu cực đột ngột, xuất hiện hiện tượng **"Trắng bên mua"** (dân gian gọi là *"Múa bên trăng"*): hàng triệu cổ phiếu bị chất bán ở mức giá sàn mà hoàn toàn không có lệnh mua đối ứng (Dư mua = 0).
- **Hành vi hiện tại của hệ thống:**
  Hệ thống chỉ theo dõi giá đóng cửa và khối lượng khớp lệnh. Khi trắng bên mua, khối lượng khớp lệnh teo tóp về gần bằng 0. Hệ thống nhận thấy khối lượng sụt giảm và kết luận sai lầm: *"Áp lực bán cạn kiệt, cổ phiếu đang tạo đáy"* hoặc đưa ra khuyến nghị *"Cắt lỗ tại vùng hỗ trợ -7%"*.
- **Hậu quả & Rủi ro:**
  Khuyến nghị cắt lỗ của hệ thống trở nên **hoàn toàn vô nghĩa và sáo rỗng** vì trên bảng điện tử không có bất kỳ ai mua để khớp lệnh! Nhà đầu tư không thể thoát hàng dù muốn. Hệ thống bắt buộc phải có cơ chế kiểm tra cờ cảnh báo `Floor_Lock` (Giá = Giá sàn & Dư mua = 0) để cảnh báo khẩn cấp hiện tượng kẹp hàng thanh khoản.

---

### 3.3. Điều chỉnh Giá Kỹ thuật do Cổ tức / Thưởng (Ngày GDKHQ) gây nhảy vọt giả chỉ báo
- **Bản chất nghiệp vụ:**
  Vào Ngày Giao dịch Không Hưởng Quyền (GDKHQ), Sở GDCK tự động điều chỉnh giá tham chiếu giảm tương ứng với tỷ lệ cổ tức bằng tiền mặt hoặc tỷ lệ chia thưởng cổ phiếu / phát hành thêm (ví dụ trả cổ tức 30% thì giá thị giá giảm khoảng 23%).
- **Hành vi hiện tại của hệ thống:**
  Hệ thống hiện tại không tích hợp lịch sự kiện doanh nghiệp (Corporate Actions). Nếu API nguồn trả về dữ liệu giá chưa điều chỉnh hoặc điều chỉnh lệch ngày, công thức `df['Close'].diff()` sẽ ghi nhận một phiên sập giá giả định (-15% đến -30%).
- **Hậu quả & Rủi ro:**
  Đường RSI bị kéo cắm đầu xuống vùng quá bán sâu giả tạo, độ biến động Volatility nhảy vọt bất thường và AI đưa ra phân tích hoảng loạn về việc doanh nghiệp bị bán tháo, trong khi thực tế đó chỉ là một đợt chia cổ tức bình thường.

---

### 3.4. Đặc thù Giá Tham chiếu Sàn UPCoM (Giá bình quân gia quyền thay vì Giá đóng cửa)
- **Bản chất nghiệp vụ:**
  Khác với sàn HOSE và HNX (lấy giá khớp lệnh phiên ATC làm giá tham chiếu cho phiên hôm sau), sàn UPCoM xác định giá tham chiếu là **Giá bình quân gia quyền (Weighted Average Price)** của toàn bộ các lệnh khớp trong phiên giao dịch trước đó.
- **Hành vi hiện tại của hệ thống:**
  Hệ thống áp dụng công thức tính phần trăm thay đổi giá thống nhất cho mọi mã cổ phiếu:
  `pct_change = ((last_close - prev_close) / prev_close) * 100`
- **Hậu quả & Rủi ro:**
  Đối với các cổ phiếu giao dịch trên UPCoM (như BSR, OIL, MCH, ACV, VEA, QNS...), giá tham chiếu bị tính sai lệch so với bảng điện tử của các công ty chứng khoán, dẫn tới việc tính toán sai biên độ dao động trong phiên và sai giá trần/sàn.

---

### 3.5. Phiên ngoài giờ, ban đêm, cuối tuần, ngày nghỉ lễ (Thiếu Market Session State Machine)
- **Bản chất nghiệp vụ:**
  Thị trường chứng khoán Việt Nam vận hành theo các khung giờ nghiêm ngặt và nghỉ giao dịch vào Thứ Bảy, Chủ Nhật cũng như các dịp lễ Tết (Tết Nguyên Đán, Giỗ Tổ Hùng Vương, 30/4 - 1/5, Quốc khánh 2/9).
- **Hành vi hiện tại của hệ thống:**
  Hệ thống chỉ dựa vào dòng code sơ sài `now.hour < 15`. Không hề có bộ máy trạng thái thị trường (Market Session State Machine).
- **Hậu quả & Rủi ro:**
  Khi người dùng truy vấn lúc 3h sáng Thứ Bảy, hệ thống vẫn hiển thị nến của ngày Thứ Sáu và ghi nhãn `"phiên đang giao dịch, số liệu chưa chốt"`. Người dùng không biết bao giờ thị trường mở cửa trở lại, không có đồng hồ đếm ngược và không có thông báo trạng thái sàn (ATO / Liên tục / Nghỉ trưa / ATC / Đóng cửa).

---

### 3.6. Lệch pha thời gian dữ liệu Tin tức và Vĩ mô khi tra cứu lịch sử (`target_date`)
- **Bản chất nghiệp vụ:**
  Khi một nhà đầu tư hoặc chuyên gia định lượng muốn quay ngược thời gian về một ngày trong quá khứ (ví dụ ngày 14/04/2026) để kiểm tra xem hệ thống phân tích ra sao trước một phiên sập gãy thị trường:
- **Hành vi hiện tại của hệ thống:**
  Hàm `get_historical_data` lấy nến giá quá khứ (dù bị lỗi Look-ahead). Nhưng tại `backend/api.py:100` và `backend/macro_fetcher.py:7-19`, hàm `get_latest_news` và `get_macro_data` lại **cào tin tức RSS CafeF/VnExpress của ngày hôm nay và lấy giá Dầu/Vàng của ngày hôm nay**!
- **Hậu quả & Rủi ro:**
  Hiện tượng **Lệch pha thời gian (Temporal Inconsistency)** nghiêm trọng: Nến giá là của năm 2024 hoặc tháng trước, nhưng tin tức và bối cảnh vĩ mô lại là chiến sự hoặc giá vàng của ngày hôm nay. AI bị đặt vào một bối cảnh hỗn loạn, đưa ra những suy luận chắp vá và hoàn toàn phi thực tế.

---

## PHẦN 4: BẢN THIẾT KẾ ĐỀ XUẤT NÂNG CẤP KIẾN TRÚC THẾ HỆ MỚI (NEXT-GEN ARCHITECTURE ROADMAP)

Để giải quyết triệt để 14 lỗ hổng P0, bao quát toàn bộ các Edge Cases và đưa hệ thống đạt tiêu chuẩn vận hành thương mại chuyên nghiệp, Hội đồng Chuyên gia đề xuất Bản Thiết kế Kiến trúc Thế hệ Mới theo mô hình 4 tầng phân lớp độc lập:

### 4.1. Sơ đồ Tổng thể Kiến trúc 4 Tầng Phân lớp

```
+===================================================================================================+
|                                    NEXT-GEN AI TRADING WORKSTATION                                |
+===================================================================================================+
                                                  │
                                                  ▼
┌───────────────────────────────────────────────────────────────────────────────────────────────────┐
│                    TẦNG 4: ACTIONABLE FRONTEND TRADING WORKSTATION (REACT 18 + VITE)              │
│  - Hợp nhất Kiến trúc Component Sạch (Sidebar, MacroTicker, StockChart, ActionableTradePlan)      │
│  - Trading View Engine: Nến + EMA10/20 + SMA50 + Volume + RSI(14) Sub-pane + MACD Sub-pane        │
│  - Trực quan hóa Điểm Mua / Cắt Lỗ / Chốt Lời trực tiếp trên nến qua Lightweight Charts Markers    │
│  - Actionable Trading HUD: Entry Zone, Target Price 1/2, Stop Loss Guard, Tỷ lệ R:R, Position Size │
│  - Thuật toán Trading Days Date-Math: Miễn dịch hoàn toàn với Thứ Bảy, Chủ Nhật và ngày lễ       │
│  - Batch Typewriter Renderer: Tối ưu 50 chars / 16ms, triệt tiêu 100% hiện tượng nghẽn DOM        │
└─────────────────────────────────────────────────┬─────────────────────────────────────────────────┘
                                                  │ HTTPS / Non-blocking JSON
                                                  ▼
┌───────────────────────────────────────────────────────────────────────────────────────────────────┐
│                    TẦNG 2: HIGH-PERFORMANCE BACKEND & HYBRID TWO-TIER CACHE (FASTAPI)             │
│  - FastAPI Fully Non-Blocking Core: Triệt tiêu hoàn toàn Blocking I/O trên Uvicorn Event Loop     │
│  - Singleton Global Thread Pool: Điều phối tác vụ nặng qua `asyncio.to_thread` / `run_in_executor`│
│  - Hybrid Two-Tier Cache: L1 In-Memory TTLCache (<1ms) + L2 Atomic File Replace (Anti-Corruption) │
│  - Market Session-Aware Cache Invalidation: Tự động dọn cache tại các mốc then chốt 09:15, 14:45 │
│  - SQLite WAL Mode (`PRAGMA journal_mode=WAL;`): Đọc ghi đồng thời không khóa Watchlist           │
│  - Security Shield: Restricted CORS Policy, Error Sanitizer Shield, SlowAPI Rate Limiter          │
└────────────────────────┬─────────────────────────────────────────────────┬────────────────────────┘
                         │                                                 │
                         ▼                                                 ▼
┌──────────────────────────────────────────────────┐ ┌──────────────────────────────────────────────┐
│       TẦNG 1: RESILIENT DATA PIPELINE            │ │    TẦNG 3: INSTITUTIONAL AI REASONING        │
│  - Source Adapter Pattern: VCI, KBS, DNSE        │ │  - Financial Grounding: P/E, P/B, ROE, EPS   │
│  - Loại bỏ hoàn toàn nguồn lỗi TCBS              │ │  - Dòng tiền Khối ngoại & Tự doanh thực tế   │
│  - Circuit Breaker Mesh: CLOSED -> OPEN -> HALF  │ │  - Pydantic Actionable Trade Plan Schema     │
│  - Exponential Backoff with Jitter               │ │  - Smart AI Resilience Manager: Fast-abort   │
│  - Zero Look-ahead Bias Filter (Strict <= target)│ │    4xx, Retry 5xx/429, Fallback an toàn      │
│  - Wilder's Smoothing RSI RMA (Fix chia cho 0)   │ │  - Standard Models: gemini-2.5-flash / 2.0   │
│  - Intraday Volume Pacing Normalization          │ │  - Backward-compatible Schema (Default fields)│
└──────────────────────────────────────────────────┘ └──────────────────────────────────────────────┘
```

---

### 4.2. Tầng 1: Resilient Vietnam Market Data Pipeline

#### 1. Kiến trúc Adapter Đa nguồn (Multi-Source Adapter Pattern)
Xây dựng lớp cơ sở trừu tượng `BaseMarketAdapter` độc lập hoàn toàn với các thay đổi thư viện bên ngoài:
```python
from abc import ABC, abstractmethod
import pandas as pd

class BaseMarketAdapter(ABC):
    @abstractmethod
    def fetch_history(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Trả về DataFrame chuẩn hóa: ['Open', 'High', 'Low', 'Close', 'Volume']"""
        pass

    @abstractmethod
    def fetch_live_quote(self, symbol: str) -> dict:
        """Lấy giá tức thời và độ sâu giá Bid/Ask trong phiên"""
        pass
```
- Triển khai cụ thể:
  - `VciAdapter`: Nguồn dữ liệu lịch sử nến ngày chính.
  - `KbsAdapter`: Nguồn dự phòng cấp 1.
  - `DnseAdapter`: Nguồn dự phòng cấp 2.
  - **Loại bỏ vĩnh viễn** nguồn `'TCBS'` vốn đã bị khai tử trên vnstock 3.5.1.

#### 2. Cơ chế Circuit Breaker & Exponential Backoff with Jitter
- **Circuit Breaker:**
  - `CLOSED`: Hoạt động bình thường. Nếu tỷ lệ lỗi vượt quá 50% trong 5 lần gọi gần nhất, lập tức ngắt mạch sang `OPEN`.
  - `OPEN`: Từ chối kết nối tới nguồn lỗi trong 60 giây (Cool-down Period). Mọi request lập tức chuyển thẳng sang adapter dự phòng mà không cần chờ timeout 45 giây.
  - `HALF-OPEN`: Sau 60 giây, cho phép 1 request đi qua để thăm dò. Nếu thành công -> chuyển về `CLOSED`; nếu thất bại -> quay lại `OPEN`.
- **Exponential Backoff có Jitter:**
  $$T_{wait} = \min\left(T_{max}, T_{base} \times 2^{retry\_count}\right) \times \text{Uniform}(0.5, 1.5)$$
  Dàn đều tải và chống hiện tượng nghẽn thác lũ (Cascading Failure).

#### 3. Loại bỏ hoàn toàn Look-ahead Bias & Chuẩn hóa RSI Wilder
- **Bộ lọc thời gian nghiêm ngặt (Zero Look-ahead Filter):**
  ```python
  # Chuẩn hóa ngày kết thúc: Tuyệt đối không cộng thêm ngày!
  end_str = target_date if target_date else datetime.now(VN_TZ).strftime('%Y-%m-%d')
  # Lọc chặt chẽ sau khi lấy dữ liệu:
  if target_date:
      df = df[df.index <= pd.to_datetime(target_date)]
  ```
- **Công thức RSI Wilder chuẩn quốc tế:**
  ```python
  def calculate_rsi_wilder(series: pd.Series, period: int = 14) -> pd.Series:
      delta = series.diff()
      gain = delta.where(delta > 0, 0.0)
      loss = -delta.where(delta < 0, 0.0)
      # Wilder's Smoothing: alpha = 1 / period (RMA)
      avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
      avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
      
      # Xử lý điều kiện biên chống chia cho 0
      rs = avg_gain / avg_loss.replace(0, np.nan)
      rsi = 100.0 - (100.0 / (1.0 + rs))
      
      # Trường hợp chuỗi nến toàn tăng trần -> RSI = 100.0
      rsi = rsi.where(avg_loss != 0, 100.0)
      # Trường hợp chuỗi nến toàn giảm sàn -> RSI = 0.0
      rsi = rsi.where(avg_gain != 0, 0.0)
      return rsi.fillna(50.0).round(2)
  ```

#### 4. Chuẩn hóa Khối lượng trong phiên (Intraday Volume Pacing)
Khi phiên đang diễn ra, chuẩn hóa khối lượng dở dang trước khi so sánh với `VolMA20`:
$$\text{Projected\_Volume} = \text{Current\_Volume} \times \left( \frac{270 \text{ phút}}{\text{Số phút đã giao dịch}} \right)$$

---

### 4.3. Tầng 2: High-Performance Backend & Hybrid Two-Tier Cache

#### 1. Triệt tiêu Blocking I/O — Chuyển dịch toàn diện sang Non-Blocking
- **Nguyên tắc vàng:** Event Loop của FastAPI không bao giờ được phép thực thi bất kỳ tác vụ mạng hay tính toán đồng bộ nào.
- Sử dụng **Singleton Global Thread Pool** kết hợp `asyncio.to_thread` / `run_in_executor`:
  ```python
  GLOBAL_EXECUTOR = ThreadPoolExecutor(max_workers=min(32, (os.cpu_count() or 4) * 4))

  @app.post("/api/market_data")
  async def fetch_market_data(req: AnalyzeRequest):
      loop = asyncio.get_running_loop()
      df = await loop.run_in_executor(GLOBAL_EXECUTOR, get_historical_data, req.symbol, 365, req.target_date)
  ```

#### 2. Kiến trúc Cache Hai Tầng (Hybrid Two-Tier Cache) & Atomic File Replace
- **L1 In-Memory Cache:** `cachetools.TTLCache` (dung lượng 200 items, phản hồi <1ms trong RAM).
- **L2 Atomic Disk Cache:** Áp dụng kỹ thuật ghi file tạm và đổi tên nguyên tử:
  ```python
  def set_cache_atomic(cache_file: Path, data: dict):
      cache_file.parent.mkdir(parents=True, exist_ok=True)
      temp_file = tempfile.NamedTemporaryFile(
          mode="w", encoding="utf-8", dir=cache_file.parent, delete=False, suffix=".tmp"
      )
      try:
          json.dump(data, temp_file, ensure_ascii=False, indent=2)
          temp_file.flush()
          os.fsync(temp_file.fileno())
          temp_file.close()
          # Đổi tên nguyên tử (Atomic Replace) — miễn nhiễm 100% với Race Condition
          os.replace(temp_file.name, cache_file)
      except Exception:
          if os.path.exists(temp_file.name):
              os.remove(temp_file.name)
          raise
  ```
- **Market Session-Aware Invalidation:** Tính toán TTL động. Tự động xóa cache vào các mốc chốt phiên 09:15 (ATO), 11:30 (Trưa), 14:45 (ATC) để người dùng luôn nhận được giá đóng cửa và thanh khoản chính xác nhất.

#### 3. Tối ưu hóa SQLite Concurrency & An toàn Bảo mật
- **SQLite WAL Mode:** Kích hoạt ngay khi mở kết nối:
  ```python
  conn.execute("PRAGMA journal_mode=WAL;")
  conn.execute("PRAGMA busy_timeout=5000;")
  ```
- **Bảo mật CORS & Error Shield:**
  - Khóa chặt `allow_origins` theo danh sách domain chỉ định (ví dụ `http://localhost:5173`).
  - Toàn bộ lỗi nội bộ được lọc qua Exception Handler tập trung, không bao giờ lộ chuỗi `str(e)` thô chứa đường dẫn đĩa cứng.
  - Tích hợp `slowapi` giới hạn tốc độ truy vấn: 60 req/phút cho Data và 10 req/phút cho AI.

---

### 4.4. Tầng 3: Institutional AI Reasoning & Actionable Trade Engine

#### 1. Bổ sung Tầng Neo Dữ liệu Cơ bản Thực tế (Financial Grounding)
- Tích hợp module thu thập dữ liệu báo cáo tài chính thực tế:
  - Chỉ số cơ bản: **P/E, P/B, ROE, ROA, EPS, Nợ vay / VCSH (D/E)**.
  - Tăng trưởng Doanh thu & Lợi nhuận sau thuế quý gần nhất.
- Bơm số liệu giao dịch thực tế của **Khối ngoại mua/bán ròng** và **Tự doanh** vào biến `{foreign_net}` và `{market_value}` trong prompt.

#### 2. Nâng cấp Pydantic Actionable Trade Schema
Mở rộng cấu trúc dữ liệu trả về của AI để phục vụ giao dịch thực chiến:
```python
class ActionableTradePlan(BaseModel):
    entry_min: float = Field(description="Vùng giá mua tối ưu thấp nhất")
    entry_max: float = Field(description="Vùng giá mua tối ưu cao nhất")
    take_profit_1: float = Field(description="Mục tiêu chốt lời ngắn hạn 1")
    take_profit_2: float = Field(description="Mục tiêu chốt lời kỳ vọng 2")
    stop_loss: float = Field(description="Mức giá cắt lỗ bắt buộc")
    risk_reward_ratio: float = Field(description="Tỷ lệ Lợi nhuận/Rủi ro (R:R, ví dụ: 2.2)")
    position_size_pct: int = Field(description="Tỷ trọng danh mục khuyến nghị (ví dụ: 15%)")
    execution_strategy: str = Field(description="Chiến lược giải ngân cụ thể")

class StockAIReportSchema(BaseModel):
    overall_score: int = Field(ge=0, le=100)
    summary: Optional[ReportSummary] = Field(default_factory=...) # Tương thích ngược cache cũ
    scores: FiveDimensionScores
    trade_plan: Optional[ActionableTradePlan] = None
    analysis: str
    predictions: List[PricePredictionItem]
```

#### 3. Bộ Quản lý Khả năng Chống chịu AI (Smart AI Resilience Manager)
- Sử dụng danh sách model chuẩn: `["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]`.
- Cơ chế **Fast-Abort**: Khi nhận mã lỗi Client HTTP 400 (Invalid Key) hoặc 403, lập tức dừng vòng lặp và kích hoạt Fallback kỹ thuật, không lặp gọi tiếp các model sau.
- Cơ chế **Retry có Backoff**: Khi gặp lỗi HTTP 429 hoặc 503, retry tối đa 2 lần với Exponential Backoff kèm Jitter.
- Tự động lưu cache cho cả chế độ Fallback định lượng khi offline để giảm tải tính toán.

---

### 4.5. Tầng 4: Actionable Frontend Trading Workstation

#### 1. Hợp nhất Kiến trúc Frontend Sạch
- Tái cấu trúc triệt để `App.jsx`: Chuyển đổi từ tệp đơn khối thành Orchestrator Container mỏng, import và kết nối trực tiếp các component:
  - `<Sidebar />`: Quản lý danh mục theo dõi (Watchlist).
  - `<MacroTicker />`: Hiển thị chỉ số vĩ mô thị trường.
  - `<StockChart />`: Biểu đồ kỹ thuật tương tác cao.
  - `<ActionableTradeHUD />`: Bảng điều khiển kế hoạch giao dịch thực chiến.
  - `<PriceTargetsAndPeers />`: Mục tiêu giá theo ngày giao dịch và so sánh cùng ngành.
  - `<RadarScoreCard />`: Biểu đồ mạng nhện đánh giá 5 chiều.
  - `<AnalysisReport />`: Báo cáo phân tích chuyên sâu.
- Mọi kết nối API được tập trung qua `apiClient.js` đọc biến môi trường `VITE_API_BASE_URL`.

#### 2. Trực quan hóa Điểm Mua / Bán trên Biểu đồ Lightweight Charts
Triển khai hàm gắn markers trực tiếp trên series nến:
```javascript
if (tradePlan && historyData.length > 0) {
    const lastBar = historyData[historyData.length - 1];
    const markers = [];
    if (tradePlan.entry_max) {
        markers.push({
            time: lastBar.time,
            position: 'belowBar',
            color: '#22c55e',
            shape: 'arrowUp',
            text: `MUA (${tradePlan.entry_min} - ${tradePlan.entry_max})`,
        });
    }
    if (tradePlan.stop_loss) {
        markers.push({
            time: lastBar.time,
            position: 'aboveBar',
            color: '#ef4444',
            shape: 'arrowDown',
            text: `CẮT LỖ (${tradePlan.stop_loss})`,
        });
    }
    candlestickSeries.setMarkers(markers);
}
```

#### 3. Bổ sung Chỉ báo Phụ & Actionable Trading HUD
- **Khung chỉ báo phụ (Sub-panes):** Tạo 2 pane phụ phía dưới biểu đồ chính hiển thị:
  - Chỉ báo RSI(14) với 2 đường giới hạn 30 (quá bán) và 70 (quá mua).
  - Chỉ báo MACD Histogram đổi màu theo động lượng dòng tiền.
- **Actionable Trading HUD:** Thẻ thông số giao dịch nổi bật đặt trên đầu báo cáo:
  - 🟢 **Vùng Giải Ngân:** `27.20 - 27.60`
  - 🎯 **Mục Tiêu Chốt Lời (TP1 / TP2):** `29.50 (+7.8%) / 31.00 (+13.3%)`
  - 🛑 **Ngưỡng Cắt Lỗ Bắt Buộc:** `26.20 (-4.2%)`
  - ⚖️ **Tỷ Lệ R:R:** `1 : 2.1` (Đạt chuẩn)
  - 💼 **Tỷ Trọng Khuyến Nghị:** `15% danh mục`
- **Thuật toán Trading Days Date-Math:** Loại bỏ hoàn toàn Thứ Bảy, Chủ Nhật và ngày nghỉ lễ khi tính toán các mốc ngày tương lai.
- **Tối ưu Typewriter:** Áp dụng kỹ thuật Batch Rendering (cập nhật 50 ký tự mỗi 16ms) và tự động dừng khi người dùng cuộn xem báo cáo.

---

## KẾ HOẠCH HÀNH ĐỘNG GIAI ĐOẠN 2 (P0 REMEDIATION & VERIFICATION MATRIX)

Để chuyển giao sang **Giai đoạn 2 (P0 Remediation)** một cách chuẩn xác và an toàn, Hội đồng Chuyên gia lập bảng ma trận phân công nhiệm vụ khắc phục trực tiếp trên mã nguồn:

| Thứ tự | Mã Lỗ hổng | Tập tin Cần Sửa Đổi | Hành Động Kỹ Thuật Chi Tiết | Tiêu Chí Nghiệm Thu (Acceptance Criteria) |
| :---: | :--- | :--- | :--- | :--- |
| **1** | **P0-DATA-01** | `backend/data_fetcher.py` | Bỏ `+ timedelta(days=1)`; bổ sung bộ lọc cắt `df = df[df.index <= pd.to_datetime(target_date)]`. | Truy vấn lịch sử `2026-04-14` trả về nến cuối cùng đúng ngày `2026-04-14`, không lọt nến ngày mai. |
| **2** | **P0-TA-01** | `backend/data_fetcher.py` | Viết lại hàm `calculate_rsi_wilder` dùng `ewm(alpha=1/14)`; xử lý an toàn biên khi $loss = 0 \rightarrow \text{RSI} = 100.0$. | RSI khớp chuẩn Wilder; chuỗi nến tăng trần trả về RSI = 100.0; trên HPG nến cuối đạt 42.03. |
| **3** | **P0-RES-01** | `backend/data_fetcher.py` | Loại bỏ `'TCBS'` khỏi danh sách nguồn; thay bằng `('VCI', 'KBS', 'DNSE')`; bao bọc try-except an toàn. | Không phát sinh lỗi `ValueError` của vnstock; tự động fallback mượt mà khi đổi nguồn. |
| **4** | **P0-PERF-01** | `backend/api.py` | Chuyển đổi các lời gọi chặn mạng và AI sang `asyncio.to_thread` / Singleton ThreadPool; giải phóng Event Loop. | Các endpoint API không còn chặn Event Loop; Watchlist phản hồi tức thì trong khi đang phân tích AI. |
| **5** | **P0-RES-02** | `backend/cache_manager.py` | Áp dụng ghi tệp tạm thời rồi đổi tên nguyên tử (`tempfile` + `os.replace`). | Chạy stress-test 20 luồng đọc/ghi đồng thời không phát sinh lỗi `JSONDecodeError` hay `WinError 32`. |
| **6** | **P0-SEC-01** | `backend/api.py` | Cấu hình danh sách `allow_origins` chỉ định; xây dựng Exception Handler tập trung che giấu lỗi raw. | Trình duyệt không chặn CORS; phản hồi HTTP 500 trả về thông điệp sạch sẽ, không lộ đường dẫn ổ đĩa. |
| **7** | **P0-FIN-01** | `backend/ai_analyzer.py`<br>`web/src/App.jsx` | Cập nhật mốc T+2.5; viết hàm cộng ngày giao dịch (Trading Days adder) bỏ qua Thứ Bảy, Chủ Nhật. | Các mốc dự báo T+1, T+2.5, T+5 luôn hiển thị đúng ngày làm việc, không rơi vào cuối tuần. |
| **8** | **P0-AI-01** | `backend/ai_analyzer.py` | Bổ sung lấy chỉ số BCTC cơ bản (P/E, P/B, ROE) và bơm dữ liệu Khối ngoại mua/bán ròng vào prompt. | Biến `{foreign_net}` nhận giá trị số thực; AI không còn bịa đặt số liệu BCTC cơ bản. |
| **9** | **P0-AI-02** | `backend/ai_analyzer.py` | Loại bỏ `gemini-4-argon`; thêm fast-abort khi gặp lỗi Client 400/401; thêm retry backoff cho lỗi 429/503. | Nhập API key sai dừng ngay lập tức (<1s); không gọi mù quáng qua các model tiếp theo. |
| **10**| **P0-AI-03** | `backend/ai_analyzer.py` | Đặt giá trị mặc định cho trường `summary` trong `StockAIReportSchema`; thêm validator `high >= low`. | Đọc thành công 100% các file cache cũ trong thư mục `.cache/` mà không văng `ValidationError`. |
| **11**| **P0-FE-01** | `web/src/components/StockChart.jsx`<br>`web/src/App.jsx` | Kích hoạt `setMarkers` trên CandlestickSeries để vẽ các nhãn MUA, CẮT LỖ trực quan trên nến. | Biểu đồ nến hiển thị rõ ràng mũi tên xanh MUA và mũi tên đỏ CẮT LỖ tương ứng kế hoạch giao dịch. |
| **12**| **P0-FE-02** | `web/src/App.jsx` | Thay thế `setInterval` 8ms bằng cơ chế batch update (50 ký tự / 16ms) có dọn dẹp cleanup khi unmount. | CPU trình duyệt duy trì dưới 15%; giao diện mượt mà, không còn giật lag khi hiển thị báo cáo dài. |
| **13**| **P0-FE-03** | `web/src/App.jsx` | Tái cấu trúc `App.jsx`, import và kết nối toàn bộ các component trong `web/src/components/`. | Mã nguồn rõ ràng, biểu đồ khôi phục đầy đủ EMA10, SMA20, Volume; API gọi qua `apiClient.js`. |
| **14**| **P0-TEST-01**| `backend/requirements.txt`<br>`backend/tests/test_api.py` | Bổ sung `httpx` vào `requirements.txt`; cấu hình biến môi trường SSL Windows an toàn. | Lệnh `python backend/tests/test_api.py` thực thi thành công 100%, trả về Status Code 200. |

---

## LỜI KẾT & CHỮ KÝ HỘI ĐỒNG KIỂM TOÁN

Bản **Báo cáo Kiểm toán Toàn diện (AUDIT_REPORT.md)** này là kết tinh của quá trình rà soát pháp y nghiêm ngặt, độc lập và trung thực bởi Hội đồng Chuyên gia Cấp cao. Mọi khiếm khuyết được chỉ ra đều có căn cứ mã nguồn chính xác, số liệu đối chuẩn thực nghiệm và phương án khắc phục khả thi.

Hội đồng Chuyên gia trân trọng đệ trình báo cáo lên Ban Điều phối Dự án (Orchestrator) và khuyến nghị **lập tức phê duyệt kích hoạt Giai đoạn 2 (P0 Remediation)** để đưa hệ thống AI Chứng Khoán Việt Nam đạt chuẩn mực vận hành thương mại chuyên nghiệp.

**ĐẠI DIỆN HỘI ĐỒNG CHUYÊN GIA CẤP CAO:**
- *CTO & Distributed Systems Architect*
- *Senior Quantitative Trader & Lead Financial Analyst*
- *Principal AI/LLM Engineer & Senior Frontend Specialist*
- *Senior Technical Writer & System Architect Worker*

