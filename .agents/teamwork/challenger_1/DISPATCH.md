## 2026-11-08T02:20:35Z
Bạn là Senior Adversarial Verification Challenger (Challenger 1) thuộc Hội đồng Chuyên gia Cấp cao thực hiện kiểm chứng thực nghiệm độc lập và stress-test sau khi sửa 14 lỗi P0 cho dự án AI Chứng khoán (2-DU-AN-AI-CHUNG-KHOAN).

BẮT BUỘC ĐỌC:
1. File yêu cầu gốc: `d:\2- LÀM VIỆC\2- github du an 1\2-DU-AN-AI-CHUNG-KHOAN\.agents\teamwork\ORIGINAL_REQUEST.md`
2. File quy hoạch dự án: `d:\2- LÀM VIỆC\2- github du an 1\2-DU-AN-AI-CHUNG-KHOAN\.agents\teamwork\PROJECT.md`
3. Báo cáo kiểm toán: `d:\2- LÀM VIỆC\2- github du an 1\2-DU-AN-AI-CHUNG-KHOAN\AUDIT_REPORT.md`
4. Báo cáo khắc phục của Worker: `d:\2- LÀM VIỆC\2- github du an 1\2-DU-AN-AI-CHUNG-KHOAN\.agents\teamwork\worker_p0_remediation\remediation_report.md`

Working directory: `d:\2- LÀM VIỆC\2- github du an 1\2-DU-AN-AI-CHUNG-KHOAN`
State folder của bạn: `d:\2- LÀM VIỆC\2- github du an 1\2-DU-AN-AI-CHUNG-KHOAN\.agents\teamwork\challenger_1\`

NHIỆM VỤ THỰC NGHIỆM ĐỐI KHÁNG (STRESS-TEST & ORACLE VERIFICATION):
Viết kịch bản và thực thi các bài kiểm thử thực nghiệm để thách thức hệ thống:
1. **Kiểm thử Toán học & Biên Định lượng:**
   - Tạo chuỗi giá giả lập 14 phiên tăng trần liên tiếp: Xác minh `calculate_rsi_wilder` trả về chính xác 100.0 (không phải 50.0).
   - Tạo chuỗi giá đi ngang hoàn toàn: Xác minh trả về 50.0.
   - Thử nghiệm trên dữ liệu thực tế HPG: Đối chiếu RSI Wilder xem có bị nhảy vọt cliff-effect của SMA cũ không.
2. **Kiểm thử Look-ahead Bias:**
   - Gọi `get_historical_data('HPG', days=10, target_date='2026-05-03')` (ngày Chủ Nhật).
   - Kiểm tra ngày của nến cuối cùng trong DataFrame: Đảm bảo $\le$ 2026-05-03, TUYỆT ĐỐI KHÔNG chứa nến ngày 2026-05-04.
3. **Kiểm thử Race Condition Cache Đa luồng (Concurrent Concurrency Stress-Test):**
   - Viết test đa luồng (ví dụ 10-20 workers đồng thời đọc và ghi cùng một key cache qua `set_cache` và `get_cache`).
   - Xác minh 0% lỗi `JSONDecodeError` và 0% lỗi `WinError 32`.
4. **Kiểm thử FastAPI & Test Suite:**
   - Chạy `python backend/tests/test_api.py` và `python backend/tests/test_macro.py`.
   - Chạy `npm --prefix web run build`.
   - Xác minh toàn bộ các test pass với exit code 0.

YÊU CẦU ĐẦU RA:
- Xuất file `challenge_report.md` tại `d:\2- LÀM VIỆC\2- github du an 1\2-DU-AN-AI-CHUNG-KHOAN\.agents\teamwork\challenger_1\challenge_report.md`
- Xuất `handoff.md` theo Handoff Protocol với Verdict: **APPROVE** hoặc **REQUEST_CHANGES**.
- Gửi tin nhắn thông báo hoàn thành kèm Verdict cho orchestrator.
