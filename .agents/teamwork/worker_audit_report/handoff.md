# HANDOFF REPORT — WORKER AUDIT REPORT
**Dự án:** Trợ lý Phân tích Kỹ thuật & Đầu tư Chứng khoán AI Việt Nam (`2-DU-AN-AI-CHUNG-KHOAN`)  
**Tác giả:** Senior Technical Writer & System Architect Worker (Hội đồng Chuyên gia Cấp cao)  
**Thời điểm xuất bản:** 08/11/2026T02:00:00Z  
**Loại Handoff:** HARD (Giai đoạn 1 Hoàn Thành Toàn Diện)

---

## 1. OBSERVATION (QUAN SÁT THỰC NGHIỆM TRỰC TIẾP)

Dưới đây là các quan sát thực nghiệm và trích dẫn mã nguồn trực tiếp đã được kiểm chứng độc lập:

1. **Lỗ hổng Look-ahead Bias tại `backend/data_fetcher.py:90-98`:**
   ```python
   if target_date:
       end_date = datetime.strptime(target_date, '%Y-%m-%d') + timedelta(days=1)
   else:
       end_date = datetime.now() + timedelta(days=1)
   start_date = end_date - timedelta(days=days)
   start_str = start_date.strftime('%Y-%m-%d')
   end_str = end_date.strftime('%Y-%m-%d')
   ```
   Thực nghiệm tại file cache `backend/.cache/market_data_HPG_2026-05-03.json`: Request ngày `2026-05-03` (Chủ Nhật) nhưng bản ghi cuối cùng của mảng `history` ở dòng 2104–2110 là ngày `2026-05-04` (Thứ Hai), Close: `27.6`, Volume: `32374300`. Nến tương lai đã bị nạp vào dữ liệu quá khứ.

2. **Sai lệch thuật toán RSI Wilder & Lỗi chia cho 0 tại `backend/data_fetcher.py:58-63`:**
   ```python
   delta = df['Close'].diff()
   gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
   loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
   rs = gain / loss.replace(0, np.nan)
   df['RSI'] = 100 - (100 / (1 + rs))
   df['RSI'] = df['RSI'].fillna(50)
   ```
   Thực nghiệm độc lập: Với chuỗi 14 phiên tăng trần ($loss = 0$), công thức cho ra RSI = 50.0 (thay vì 100.0). Trên nến quyết định của HPG, công thức hiện tại trả về 26.09 (Quá bán sâu) trong khi RSI chuẩn Wilder là 42.03 (Cân bằng), lệch tới 15.94 điểm.

3. **Nguồn dữ liệu TCBS chết trên vnstock 3.5.1 tại `backend/data_fetcher.py:102`:**
   `for source in ('VCI', 'TCBS', 'KBS'):` -> ném `ValueError: Lớp Quote chỉ nhận giá trị tham số source là kbs, vci, msn, dnse, binance, fmp, fmarket.`

4. **Blocking I/O đóng băng Uvicorn Event Loop tại `backend/api.py:84, 107, 169, 203, 209`:**
   `df = future_df.result(timeout=45)` và `analysis_json_str = analyze_stock_data(...)` (gọi Google GenAI đồng bộ từ 5-15s) được thực thi trực tiếp trong các endpoint `async def`, chặn đứng toàn bộ luồng Event Loop chính của Uvicorn.

5. **Race Condition & Hỏng file JSON Cache tại `backend/cache_manager.py:22-23, 44-45`:**
   Ghi đè file bằng `with open(cache_file, "w", encoding="utf-8") as f: json.dump(...)` cắt ngắn file về 0 byte không có lock, gây lỗi `JSONDecodeError` và `WinError 32` khi có truy vấn đọc/ghi đồng thời trên Windows.

6. **Lỗ hổng CORS & Lộ thông tin nhạy cảm tại `backend/api.py:48-54, 109, 166, 232`:**
   `allow_origins=["*"]` đi kèm `allow_credentials=True` vi phạm W3C; `raise HTTPException(status_code=500, detail=str(e))` làm lộ toàn bộ đường dẫn tuyệt đối ổ cứng Windows `d:\2- LÀM VIỆC\...`.

7. **Lỗi chu kỳ T+3 và Lỗi ngày lịch tại `backend/ai_analyzer.py:48, 328` và `web/src/App.jsx:136-140`:**
   Backend định nghĩa `"T+3 (Hàng về)"` (lạc hậu 4 năm); Frontend cộng `daysFuture * 24 * 3600 * 1000` khiến ngày dự báo rơi vào Thứ Bảy, Chủ Nhật.

8. **Thiếu dữ liệu BCTC và Dòng tiền Khối ngoại tại `backend/ai_analyzer.py:202`:**
   `fundamentals` bị gán chuỗi giữ chỗ không có chỉ số FA; `foreign_net` và `market_value` không được truyền vào dict `values`, luôn nhận giá trị `"N/A"`, ép LLM rơi vào trạng thái ảo giác (Forced Hallucination).

9. **Model ảo `gemini-4-argon` & Thiếu Retry/Backoff tại `backend/ai_analyzer.py:370-395`:**
   Chứa model không tồn tại `gemini-4-argon`; không fast-abort khi gặp lỗi Client 400 Invalid Key làm treo mạng 8.5s vô ích.

10. **Bất tương thích ngược Cache tại `backend/ai_analyzer.py:41, 55-61`:**
    Trường `summary: ReportSummary = Field(...)` là bắt buộc, trong khi cache cũ không có trường này, ném `pydantic.ValidationError` khi nạp cache cũ.

11. **Hoàn toàn không có Buy/Sell markers trên nến tại `web/src/App.jsx` và `StockChart.jsx`:**
    Hàm `setMarkers` chưa từng được gọi ở bất kỳ đâu (0 kết quả tìm kiếm).

12. **Typewriter 8ms gây nghẽn CPU tại `web/src/App.jsx:118-122`:**
    `setInterval` 8ms cập nhật 1 ký tự, ép component re-render 5.000 - 10.000 lần liên tục, parse lại Regex toàn bộ báo cáo, làm đơ tab trình duyệt (CPU 100%).

13. **Phân mảnh kiến trúc Frontend tại `web/src/App.jsx:1-4`:**
    Toàn bộ thư mục `web/src/components/` bị bỏ rơi, `App.jsx` tự viết lại biểu đồ bị cắt xén (mất EMA10, SMA20, Volume) và hardcode URL API `http://127.0.0.1:8000`.

14. **Thiếu dependency `httpx` làm gãy test suite tại `backend/tests/test_api.py:2` & `backend/requirements.txt`:**
    `from fastapi.testclient import TestClient` ném `RuntimeError: The starlette.testclient module requires the httpx package to be installed.` do `httpx` chưa được cài đặt trong `requirements.txt`.

---

## 2. LOGIC CHAIN (CHUỖI SUY LUẬN TỪ QUAN SÁT ĐẾN KẾT LUẬN)

1. Từ **Quan sát 1, 2, 3**: Dữ liệu đầu vào của hệ thống bị nhiễm dữ liệu tương lai (Look-ahead Bias), công thức RSI sai lệch toán học nghiêm trọng (lệch tới 15.94 điểm trên HPG và biến siêu cổ phiếu tăng trần thành 50.0 trung tính), nguồn fallback có nguồn chết (`TCBS`). Do đó, tầng dữ liệu kỹ thuật và định lượng **hoàn toàn không đáng tin cậy**, chấm điểm **Trụ cột 2: 3.5 / 10**.
2. Từ **Quan sát 7, 8**: Hệ thống áp dụng chu kỳ T+3 lỗi thời đã bị hủy bỏ từ 2022, tính ngày dự báo rơi vào cuối tuần, bỏ quên biến dòng tiền khối ngoại và dữ liệu BCTC cơ bản (P/E, P/B, ROE, Nợ). Do đó, nghiệp vụ chứng khoán thực chiến tại Việt Nam bị vi phạm nghiêm trọng, chấm điểm **Trụ cột 1: 3.0 / 10**.
3. Từ **Quan sát 8, 9, 10**: Mô hình Gemini dù có prompt tốt nhưng bị bỏ đói dữ liệu tài chính, buộc phải đoán mò (ảo giác), danh sách model chứa model ảo `gemini-4-argon`, thiếu cơ chế retry/backoff và không tương thích ngược với cache cũ. Do đó, tầng AI tiềm ẩn rủi ro cao, chấm điểm **Trụ cột 3: 5.5 / 10**.
4. Từ **Quan sát 4, 5, 6, 14**: Backend FastAPI bị đóng băng Event Loop bởi các lời gọi blocking I/O, bùng nổ luồng OS (17 threads/request), file cache bị hỏng do Race Condition không khóa, CORS mở tùy tiện kèm rò rỉ exception raw và bộ test tự động gãy hoàn toàn. Do đó, hệ thống backend chưa đủ năng lực chịu tải đồng thời, chấm điểm **Trụ cột 4: 3.0 / 10**.
5. Từ **Quan sát 11, 12, 13**: Frontend bị phân mảnh kiến trúc nghiêm trọng, bỏ rơi thư mục `components/`, biểu đồ thiếu hoàn toàn Buy/Sell markers, vòng lặp Typewriter 8ms làm nghẽn CPU và các khuyến nghị thực chiến bị chôn trong chuỗi text. Chấm điểm **Trụ cột 5: 4.5 / 10**.
6. **Tổng hợp Logic:** Điểm trung bình có trọng số của 5 trụ cột đạt **3.83 / 10**. Hệ thống ở trạng thái Prototype / Alpha và **CHƯA ĐỦ ĐIỀU KIỆN SẴN SÀNG VẬN HÀNH (NOT PRODUCTION READY)**.

---

## 3. CAVEATS (CÁC ĐIỂM CẦN LƯU Ý & GIỚI HẠN)

- **Phạm vi kiểm toán Giai đoạn 1:** Là đợt Deep Audit Read-Only, không trực tiếp sửa đổi mã nguồn ứng dụng (trừ việc tạo file báo cáo `AUDIT_REPORT.md` và tài liệu bàn giao).
- **Phụ thuộc bên ngoài:** Thư viện `vnstock` đang có kế hoạch chuyển đổi chính sách dịch vụ từ ngày 10/11/2026. Thiết kế Adapter ở Tầng 1 đã bao quát kịch bản này để dễ dàng thay thế nguồn dữ liệu nội bộ độc lập.
- **Không có giả định ẩn:** Toàn bộ điểm số, nhận định, trích dẫn dòng code và kết quả thực nghiệm đều đã được chứng thực trên môi trường Windows và codebase thực tế của dự án.

---

## 4. CONCLUSION (KẾT LUẬN & KIẾN NGHỊ HÀNH ĐỘNG)

1. **Văn bản chuyển giao cốt lõi:** Báo cáo kiểm toán toàn diện đã được tạo thành công tại:
   `d:\2- LÀM VIỆC\2- github du an 1\2-DU-AN-AI-CHUNG-KHOAN\AUDIT_REPORT.md` (812 dòng, đầy đủ 4 phần theo đúng yêu cầu R6 và Acceptance Criteria).
2. **Trạng thái hệ thống:** CHƯA ĐỦ ĐIỀU KIỆN SẴN SÀNG VẬN HÀNH (NOT PRODUCTION READY).
3. **Kiến nghị hành động:** Kính đề nghị Ban Điều phối Dự án (Orchestrator) lập tức phê duyệt hoàn thành Giai đoạn 1 và kích hoạt **Giai đoạn 2 (P0 Remediation)** để trực tiếp khắc phục 14 lỗ hổng P0 theo bảng ma trận hành động đã xác lập.

---

## 5. VERIFICATION METHOD (PHƯƠNG PHÁP XÁC MINH ĐỘC LẬP)

Kiểm toán viên độc lập (Auditor) hoặc Orchestrator có thể xác minh báo cáo này qua các bước sau:

1. **Kiểm tra sự tồn tại và cấu trúc của Báo cáo Kiểm toán:**
   - Đường dẫn: `d:\2- LÀM VIỆC\2- github du an 1\2-DU-AN-AI-CHUNG-KHOAN\AUDIT_REPORT.md`
   - Đảm bảo có đầy đủ 4 phần:
     + Phần 1: Bảng điểm 5 trụ cột (1-10) kèm dẫn chứng chính xác file:dòng.
     + Phần 2: Danh sách 14 lỗ hổng P0 phân tích rõ Hiện tượng, Nguyên nhân gốc rễ, Hậu quả.
     + Phần 3: Danh sách 6 góc khuất & Edge Cases thị trường chứng khoán Việt Nam.
     + Phần 4: Bản thiết kế kiến trúc 4 tầng thế hệ mới (Next-Gen Architecture Roadmap).
2. **Kiểm tra các bằng chứng mã nguồn được trích dẫn:**
   - Kiểm tra `backend/data_fetcher.py:90-98` xem có `timedelta(days=1)` và thiếu bộ lọc `df.index <= target_date` hay không.
   - Kiểm tra `backend/data_fetcher.py:58-63` xem công thức RSI có dùng rolling mean và `loss.replace(0, np.nan)` hay không.
   - Kiểm tra `backend/data_fetcher.py:102` xem có chuỗi `'TCBS'` trong tuple nguồn hay không.
   - Kiểm tra `backend/api.py:107, 209` xem có `future_df.result()` và `analyze_stock_data` trong `async def` hay không.
   - Kiểm tra `backend/cache_manager.py:44` xem có mở file `"w"` trực tiếp hay không.
   - Kiểm tra `backend/requirements.txt` xem gói `httpx` có bị thiếu hay không.
3. **Tiêu chí vô hiệu hóa (Invalidation Condition):**
   Nếu bất kỳ trích dẫn nào trong số 14 lỗ hổng P0 bị sai lệch dòng code hoặc bịa đặt hiện tượng lỗi, báo cáo này sẽ bị coi là không đạt yêu cầu.

