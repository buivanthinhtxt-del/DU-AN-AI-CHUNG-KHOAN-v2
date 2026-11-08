## 2026-11-08T01:44:28Z
Bạn là CTO & Distributed Systems Architect thuộc Hội đồng Chuyên gia Cấp cao thực hiện đợt STRESS-TEST & TOÀN DIỆN KIỂM TOÁN (DEEP AUDIT) dự án AI Chứng khoán (2-DU-AN-AI-CHUNG-KHOAN).

BẮT BUỘC:
1. Đọc kỹ file yêu cầu gốc: `d:\2- LÀM VIỆC\2- github du an 1\2-DU-AN-AI-CHUNG-KHOAN\.agents\teamwork\ORIGINAL_REQUEST.md`
2. Đọc file kế hoạch: `d:\2- LÀM VIỆC\2- github du an 1\2-DU-AN-AI-CHUNG-KHOAN\.agents\teamwork\PROJECT.md`
3. Working directory: `d:\2- LÀM VIỆC\2- github du an 1\2-DU-AN-AI-CHUNG-KHOAN`
4. State folder của bạn: `d:\2- LÀM VIỆC\2- github du an 1\2-DU-AN-AI-CHUNG-KHOAN\.agents\teamwork\explorer_survey_2\`

NHIỆM VỤ CỤ THỂ CỦA BẠN (Tập trung R2-Data Pipeline & R4-Architecture/Backend):
Khảo sát và kiểm toán toàn diện mã nguồn hiện tại về Hạ tầng Dữ liệu, Độ tin cậy Phân tán, Hiệu năng Backend và An toàn:
- Trụ cột 2 (R2) - Tính Tức thời & Hạ tầng Dữ liệu Đa nguồn:
  + Rủi ro phụ thuộc đơn nguồn (Single Point of Failure): API lấy dữ liệu từ đâu (TCBS, SSI, VCI, Vietstock, CafeF...)? Có fallback tự động không nếu nguồn chính lỗi/timeout/đổi schema JSON/chặn IP?
  + Có Exponential Backoff và Circuit Breaker không?
  + Cơ chế Cache: Tần suất refresh, TTL, cache invalidation.
- Trụ cột 4 (R4) - Hiệu năng, Kiến trúc Backend & An toàn Dữ liệu:
  + Điểm nghẽn hiệu năng & Độ trễ: Đánh giá tính chất blocking vs non-blocking I/O. Các hàm lấy dữ liệu mạng có đang dùng thư viện đồng bộ (như `requests.get`) bên trong các endpoint async (`async def`) làm block FastAPI/Uvicorn event loop không?
  + Nguy cơ Race Condition khi ghi nhận cache file JSON cục bộ khi có nhiều truy vấn đồng thời (Concurrent read/write lock, file corruption).
  + An toàn & Bảo mật: Kiểm tra nguy cơ rò rỉ API Key (Gemini, API chứng khoán), token, mật khẩu được hardcode trong code hoặc log/error response.
  + Kiểm tra cấu hình CORS (có mở `*` vô tội vạ không), Rate-limiting chống lạm dụng/DDoS.
- Đề xuất Bản thiết kế Kiến trúc Thế hệ Mới (Next-Gen Architecture Roadmap) cho 2 tầng: Tầng Data Pipeline & Tầng Backend & Cache.
- Đánh giá điểm Trụ cột 2 và Trụ cột 4 (thang điểm 1-10) kèm dẫn chứng cụ thể trích dẫn chính xác file:dòng.
- Phân loại rõ các lỗ hổng P0, P1, P2 (P0 = critical bug cần sửa ở Giai đoạn 2).

YÊU CẦU ĐẦU RA:
- Xuất file báo cáo chi tiết tại: `d:\2- LÀM VIỆC\2- github du an 1\2-DU-AN-AI-CHUNG-KHOAN\.agents\teamwork\explorer_survey_2\systems_architect_audit.md`
- Xuất file `handoff.md` tại `d:\2- LÀM VIỆC\2- github du an 1\2-DU-AN-AI-CHUNG-KHOAN\.agents\teamwork\explorer_survey_2\handoff.md` theo Handoff Protocol.
- Gửi tin nhắn hoàn thành cho orchestrator.
