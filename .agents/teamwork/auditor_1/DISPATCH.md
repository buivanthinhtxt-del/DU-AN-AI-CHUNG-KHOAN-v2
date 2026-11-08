## 2026-11-08T02:20:49Z

Bạn là Forensic Integrity Auditor (Kiểm toán viên Pháp y Độc lập) thuộc Hội đồng Chuyên gia Cấp cao thực hiện kiểm toán tính trung thực và toàn vẹn mã nguồn sau khi khắc phục 14 lỗi P0 cho dự án AI Chứng khoán (2-DU-AN-AI-CHUNG-KHOAN).

BẮT BUỘC ĐỌC:
1. File yêu cầu gốc: `d:\2- LÀM VIỆC\2- github du an 1\2-DU-AN-AI-CHUNG-KHOAN\.agents\teamwork\ORIGINAL_REQUEST.md`
2. File quy hoạch dự án: `d:\2- LÀM VIỆC\2- github du an 1\2-DU-AN-AI-CHUNG-KHOAN\.agents\teamwork\PROJECT.md`
3. Báo cáo kiểm toán ban đầu: `d:\2- LÀM VIỆC\2- github du an 1\2-DU-AN-AI-CHUNG-KHOAN\AUDIT_REPORT.md`
4. Báo cáo khắc phục của Worker: `d:\2- LÀM VIỆC\2- github du an 1\2-DU-AN-AI-CHUNG-KHOAN\.agents\teamwork\worker_p0_remediation\remediation_report.md`

Working directory: `d:\2- LÀM VIỆC\2- github du an 1\2-DU-AN-AI-CHUNG-KHOAN`
State folder của bạn: `d:\2- LÀM VIỆC\2- github du an 1\2-DU-AN-AI-CHUNG-KHOAN\.agents\teamwork\auditor_1\`

NHIỆM VỤ PHÁP Y ĐỘC LẬP (FORENSIC INTEGRITY AUDIT):
Kiểm tra nghiêm ngặt xem có bất kỳ hành vi GIAN LẬN (CHEATING), LÀM GIẢ (FACADE/DUMMY), HARDCODE KẾT QUẢ hoặc RÒ RỈ THÔNG TIN NHẠY CẢM nào trong mã nguồn dự án hay không:
1. **Kiểm tra Hardcoding & Facade Implementation:**
   - Kiểm tra xem Worker có hardcode kết quả test để đối phó (ví dụ: hardcode output RSI, hardcode phản hồi API, hardcode kết quả test trong `test_api.py`) hay các thuật toán (Wilder's RSI RMA, Look-ahead filter, Atomic cache, FastAPI non-blocking async) là logic toán học và hệ thống thực thụ?
2. **Kiểm tra Tính Toàn vẹn Dữ liệu & Xử lý An toàn:**
   - Kiểm tra xem có bất kỳ API key bí mật, token hay thông tin đăng nhập nào bị hardcode trực tiếp vào mã nguồn hoặc bị in ra log/error response không?
   - Kiểm tra xem file cache `.cache/` có dữ liệu giả mạo hay được sinh ra từ logic hệ thống?
3. **Kiểm tra Runtime Execution & Syntax:**
   - Chạy các lệnh kiểm tra cú pháp và thực thi:
     `python -m py_compile backend/data_fetcher.py backend/cache_manager.py backend/api.py backend/ai_analyzer.py`
     `python backend/tests/test_api.py`
     `npm --prefix web run build`
   - Xác minh mã nguồn hoàn toàn hợp lệ, không có backdoor, stub rỗng hay bypass kiểm tra.

TIÊU CHÍ PHÁN QUYẾT (BINARY VERDICT):
- Nếu phát hiện bất kỳ hành vi gian lận, hardcode giả mạo kết quả, dummy facade hoặc vi phạm an toàn bí mật: Phán quyết bắt buộc là **INTEGRITY VIOLATION** kèm bằng chứng chi tiết.
- Nếu toàn bộ mã nguồn được triển khai chân thực, đầy đủ, chuẩn mực và an toàn: Phán quyết là **CLEAN**.

YÊU CẦU ĐẦU RA:
- Xuất file `forensic_audit_report.md` tại `d:\2- LÀM VIỆC\2- github du an 1\2-DU-AN-AI-CHUNG-KHOAN\.agents\teamwork\auditor_1\forensic_audit_report.md`
- Xuất `handoff.md` theo Handoff Protocol với Verdict rõ ràng: **CLEAN** hoặc **INTEGRITY VIOLATION**.
- Gửi tin nhắn thông báo hoàn thành kèm Verdict cho orchestrator.
