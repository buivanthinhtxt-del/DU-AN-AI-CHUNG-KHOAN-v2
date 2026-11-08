## 2026-11-08T02:01:22Z
Bạn là Senior Fullstack Remediation Worker thuộc Hội đồng Chuyên gia Cấp cao thực hiện Giai đoạn 2 (P0 Remediation) cho dự án AI Chứng khoán (2-DU-AN-AI-CHUNG-KHOAN).

BẮT BUỘC ĐỌC:
1. File yêu cầu gốc: `d:\2- LÀM VIỆC\2- github du an 1\2-DU-AN-AI-CHUNG-KHOAN\.agents\teamwork\ORIGINAL_REQUEST.md`
2. File quy hoạch dự án: `d:\2- LÀM VIỆC\2- github du an 1\2-DU-AN-AI-CHUNG-KHOAN\.agents\teamwork\PROJECT.md`
3. Báo cáo kiểm toán toàn diện: `d:\2- LÀM VIỆC\2- github du an 1\2-DU-AN-AI-CHUNG-KHOAN\AUDIT_REPORT.md` (Đặc biệt xem kỹ Phần 2 và Bảng ma trận Phần 5).

Working directory: `d:\2- LÀM VIỆC\2- github du an 1\2-DU-AN-AI-CHUNG-KHOAN`
State folder của bạn: `d:\2- LÀM VIỆC\2- github du an 1\2-DU-AN-AI-CHUNG-KHOAN\.agents\teamwork\worker_p0_remediation\`

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

NHIỆM VỤ CỤ THỂ CỦA BẠN (GIAI ĐOẠN 2 - SỬA CHỮA TOÀN BỘ CÁC LỖ HỔNG P0):
Trực tiếp sửa chữa triệt để 14 lỗ hổng P0 trong mã nguồn dự án:

1. `backend/data_fetcher.py`:
   - [P0-DATA-01] Loại bỏ Look-ahead Bias: Trong `get_historical_data()`, khi có `target_date`, không cộng thêm ngày hoặc phải thêm bộ lọc chặt chẽ `df = df[df.index <= pd.to_datetime(target_date)]` sau khi nhận kết quả từ `vnstock`. Đảm bảo ngày cuối cùng của DataFrame không bao giờ vượt quá `target_date`.
   - [P0-TA-01] Sửa chuẩn công thức RSI theo J. Welles Wilder: Dùng RMA/Wilder smoothing với $\alpha = 1/14$ (`gain.ewm(alpha=1/14, adjust=False).mean()`). Xử lý an toàn mẫu số khi chuỗi nến toàn tăng ($loss = 0 \rightarrow \text{RSI} = 100.0$, nếu cả gain và loss = 0 thì RSI = 50.0). Không dùng `rolling(14).mean()`.
   - [P0-RES-01] Sửa nguồn dữ liệu TCBS chết: Thay `('VCI', 'TCBS', 'KBS')` bằng các nguồn hợp lệ của `vnstock 3.5.1` (như `'vci'`, `'kbs'`, `'msn'`, `'dnse'`), bao bọc try-except riêng biệt cho từng nguồn để tự động fallback mượt mà.

2. `backend/cache_manager.py`:
   - [P0-RES-02] Loại bỏ Race Condition & File Corruption: Viết lại hàm `set_cache` sử dụng cơ chế ghi tệp tạm thời rồi đổi tên nguyên tử (`tempfile.NamedTemporaryFile` trong cùng thư mục cache + `os.replace`), đồng thời bắt `json.decoder.JSONDecodeError` trong `get_cache` để tự động xóa file lỗi và trả về None an toàn thay vì crash.

3. `backend/api.py`:
   - [P0-PERF-01] Loại bỏ Blocking I/O trên Uvicorn Event Loop: Chuyển các tác vụ nặng (gọi `get_historical_data`, gọi Gemini `analyze_stock_data`, SQLite) sang `asyncio.to_thread` để Event Loop của FastAPI luôn hoàn toàn non-blocking.
   - [P0-SEC-01] Sửa lỗi bảo mật CORS & Rò rỉ Exception: Cấu hình `allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"]` (kèm env fallback) thay vì wildcard `*` với credentials. Thay thế các lệnh `raise HTTPException(status_code=500, detail=str(e))` bằng xử lý chuẩn hóa, ghi log lỗi nội bộ và trả về message an toàn cho người dùng, không lộ đường dẫn ổ đĩa tuyệt đối Windows.

4. `backend/ai_analyzer.py`:
   - [P0-FIN-01] Sửa chu kỳ T+3 thành T+2.5: Cập nhật prompt và mốc dự báo thành `T+2.5 (Hàng về chiều T+2)` với `days_future = 2`.
   - [P0-AI-01] Bơm dữ liệu Khối ngoại & FA: Đảm bảo biến `foreign_net` được truyền vào dict `values` trong `build_user_prompt()`. Thêm thông tin FA cơ bản thực tế hoặc chuẩn hóa để AI không bịa đặt số liệu.
   - [P0-AI-02] Loại bỏ model ảo & Xử lý lỗi thông minh: Bỏ `gemini-4-argon`, dùng các model hợp lệ `["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]`. Khi gặp lỗi Client HTTP 400/401/403 (Invalid API key), Fast-abort ngay lập tức chuyển sang fallback định lượng thay vì lặp qua 3 model. Thêm backoff cho 429/503.
   - [P0-AI-03] Tương thích ngược Cache & Validator: Trong `StockAIReportSchema`, đặt giá trị mặc định cho `summary = None` hoặc `Field(default_factory=...)` để đọc thành công các file cache cũ; thêm validator kiểm tra `days_future > 0` và `high >= low`.

5. `backend/requirements.txt` & `backend/tests/`:
   - [P0-TEST-01] Bổ sung `httpx` vào `backend/requirements.txt`.
   - Cài đặt / xác minh trong môi trường `.venv` để chạy thành công `test_api.py`.
   - Đảm bảo `backend/tests/test_api.py` và `test_macro.py` chạy thành công (exit code 0).

6. Frontend (`web/src/App.jsx` và `web/src/components/StockChart.jsx`):
   - [P0-FE-01] Kích hoạt Buy/Sell Markers trên biểu đồ Candlestick: Gọi `candlestickSeries.setMarkers(...)` để hiển thị mũi tên MUA (xanh) và CẮT LỖ (đỏ) trực quan trên nến.
   - [P0-FE-02] Tối ưu hóa Typewriter: Thay thế `setInterval(..., 8)` 1 ký tự bằng cơ chế cập nhật cụm (batch update 40-50 ký tự mỗi 16ms) có dọn dẹp interval khi unmount, chấm dứt tình trạng đơ nghẽn CPU 100%.
   - [P0-FE-03] Khôi phục chỉ báo kỹ thuật trên biểu đồ: Đảm bảo Candlestick đi kèm EMA10, SMA20 và Volume histogram đầy đủ.
   - [P0-FIN-01 Frontend] Sửa hàm `formatPredictionDate` cộng ngày giao dịch (Trading Days adder): bỏ qua Thứ Bảy, Chủ Nhật khi tính ngày dự báo tương lai.

YÊU CẦU ĐẦU RA:
- Chạy các lệnh kiểm thử và build để xác minh sau khi sửa đổi.
- Xuất file `remediation_report.md` tại `d:\2- LÀM VIỆC\2- github du an 1\2-DU-AN-AI-CHUNG-KHOAN\.agents\teamwork\worker_p0_remediation\remediation_report.md` chi tiết các tệp đã sửa, các hàm đã cập nhật và kết quả kiểm thử.
- Xuất `handoff.md` theo Handoff Protocol.
- Gửi tin nhắn thông báo hoàn thành cho orchestrator.


## 2026-11-08T02:16:43Z
**Context**: Kiểm tra tiến độ Giai đoạn 2 (P0 Remediation)
**Content**: Đã 15 phút trôi qua kể từ khi bạn nhận nhiệm vụ sửa chữa 14 lỗi P0. Bạn đã hoàn thành những tệp nào rồi và hiện đang thực hiện đến bước nào?
**Action**: Cập nhật tóm tắt tiến độ hoặc báo cáo hoàn thành nếu đã xong.
