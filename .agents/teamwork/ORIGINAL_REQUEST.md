# Original User Request

## Initial Request — 2026-11-08T01:42:14Z

Thực hiện đợt STRESS-TEST & TOÀN DIỆN KIỂM TOÁN (DEEP AUDIT) và trực tiếp sửa chữa các lỗ hổng nghiêm trọng trên toàn bộ mã nguồn của dự án AI Chứng khoán hiện tại (2-DU-AN-AI-CHUNG-KHOAN) bởi một Hội đồng Chuyên gia cấp cao gồm CTO & Distributed Systems Architect, Senior Quantitative Trader & Lead Financial Analyst, và Principal AI/LLM Engineer nhằm phục vụ mục đích sẵn sàng vận hành thực tế (production readiness). Quá trình thực hiện theo 2 giai đoạn: Giai đoạn 1 hoàn thành đợt Deep Audit và xuất bản AUDIT_REPORT.md; Giai đoạn 2 trực tiếp sửa chữa các lỗi P0 và chạy kiểm thử tự động xác minh toàn diện hệ thống.

Working directory: d:\2- LÀM VIỆC\2- github du an 1\2-DU-AN-AI-CHUNG-KHOAN
Integrity mode: development

## Requirements

### R1. Kiểm toán Trụ cột 1: Nghiệp vụ Chứng khoán Thực chiến tại Việt Nam (Financial & Market Domain)
Đánh giá chuyên sâu mức độ đáp ứng nghiệp vụ chứng khoán Việt Nam trong mã nguồn:
- Cơ chế thời gian giao dịch & trạng thái sàn: Xử lý các trạng thái ngoài giờ, cuối tuần, ngày nghỉ lễ, phiên định kỳ ATO (9h00-9h15), phiên định kỳ ATC (14h30-14h45), phiên liên tục; phản hồi của hệ thống khi người dùng truy vấn ngoài giờ hoặc ban đêm.
- Quy tắc T+2.5: Đánh giá xem các chỉ báo và mô hình dự báo đã tính đến chu kỳ hàng về tài khoản lúc 13h00 ngày T+2 chưa.
- Dữ liệu trọng yếu: Đánh giá việc tích hợp dữ liệu mua/bán ròng Khối ngoại & Tự doanh; Dữ liệu Sổ lệnh (Order Book / Bảng giá Depth 3 mức giá, tỷ lệ Active Buy vs Active Sell); Dữ liệu Tài chính Doanh nghiệp cơ bản (FA: P/E, P/B, ROE, Tăng trưởng Doanh thu/LN, Nợ/VCSH) kết hợp với Phân tích Kỹ thuật (TA); Khả năng tích hợp dữ liệu tin đồn và mạng xã hội tài chính (F247, Vietstock Forum).

### R2. Kiểm toán Trụ cột 2: Tính Tức thời & Hạ tầng Dữ liệu Đa nguồn (Real-time & Data Resilience)
Đánh giá độ trễ và khả năng chống chịu sự cố của tầng dữ liệu:
- Rủi ro phụ thuộc đơn nguồn & Rate-limit: Xử lý khi API nguồn (TCBS, VCI...) bị chặn IP, đổi cấu trúc JSON, dính Captcha, bảo trì; cơ chế fallback sang các nguồn dự phòng (SSI, DNSE, Vietstock, CafeF), thuật toán Exponential Backoff và Circuit Breaker.
- Tính toán chỉ báo kỹ thuật trong phiên (Intraday Realtime TA): Cơ chế ghép nến ngày hiện tại (giá biến động liên tục) vào chuỗi nến lịch sử để tính RSI, MACD, EMA mà không gây sai lệch thuật toán; kiểm tra và phát hiện Look-ahead Bias (rò rỉ dữ liệu tương lai vào dữ liệu quá khứ).

### R3. Kiểm toán Trụ cột 3: Trí tuệ Nhân tạo & Prompt Chuyên sâu (AI, LLM & Reasoning)
Đánh giá kiến trúc suy luận và tầng AI:
- Kiểm soát ảo giác (Hallucination) & Tính cập nhật: Ràng buộc prompt ngăn AI bịa đặt số liệu tài chính hoặc sai mốc thời gian; cơ chế Context Window Guard chống nhồi dữ liệu nến thô làm loãng sự tập trung của LLM.
- Định dạng đầu ra & Xử lý lỗi AI: Cơ chế Structured Outputs đảm bảo trả về đúng JSON schema; chiến lược xử lý khi Gemini gặp lỗi (429 Quota, 503 Overloaded, Content Safety Filter) kèm cơ chế retry hoặc fallback.

### R4. Kiểm toán Trụ cột 4: Hiệu năng, Kiến trúc Backend & An toàn Dữ liệu (Architecture & Backend)
Đánh giá hạ tầng kỹ thuật và bảo mật backend:
- Điểm nghẽn hiệu năng & Độ trễ: Đánh giá tính chất blocking/non-blocking của các tác vụ mạng/I/O; đo lường và đánh giá thời gian phản hồi; nguy cơ Race Condition khi ghi nhận cache file JSON cục bộ khi có truy vấn đồng thời.
- An toàn & Bảo mật: Kiểm tra nguy cơ rò rỉ API Key hoặc thông tin nhạy cảm qua log hoặc response lỗi; kiểm tra CORS và Rate-limiting chống lạm dụng/DDoS.

### R5. Kiểm toán Trụ cột 5: Trải nghiệm Người dùng & Tính Trực quan (Frontend & Actionable Insights)
Đánh giá giao diện và tính thực chiến của thông tin trả về:
- Tính tương tác của biểu đồ: Đánh giá khả năng zoom/pan mượt mà, công cụ vẽ, chỉ báo kỹ thuật kèm theo, đánh dấu điểm Mua/Bán (Buy/Sell markers) trên nến.
- Tính thực chiến của khuyến nghị (Actionable Insights): Kiểm tra khuyến nghị có cung cấp cụ thể Vùng giải ngân (Entry Zone), Điểm chốt lời từng phần (Take Profit 1, 2), Ngưỡng cắt lỗ (Stoploss), và Tỷ trọng danh mục (Position Sizing) thay vì nhận định chung chung.

### R6. Giai đoạn 1: Xuất bản Báo cáo Kiểm toán Toàn diện & Bản thiết kế Kiến trúc Thế hệ Mới
Tổng hợp toàn bộ kết quả kiểm toán từ R1 đến R5 thành báo cáo hoàn chỉnh lưu tại `AUDIT_REPORT.md` ở thư mục gốc của dự án với 4 phần bắt buộc:
1. Bảng điểm đánh giá hiện trạng (Thang điểm 1-10 cho từng trụ cột kèm dẫn chứng cụ thể).
2. Danh sách các lỗ hổng chết người (Critical Vulnerabilities & Bottlenecks): Mô tả hiện tượng, nguyên nhân gốc rễ và hậu quả nếu không xử lý.
3. Danh sách các góc khuất & Edge Cases chưa tính tới (Cổ phiếu đình chỉ/hủy giao dịch, điều chỉnh giá do chia cổ tức/thưởng, hiện tượng trắng bên mua/bán...).
4. Bản thiết kế đề xuất nâng cấp hệ thống thế hệ mới (Next-Gen Architecture Roadmap): Chi tiết từng tầng Data Pipeline -> Backend & Cache -> AI Engine -> Frontend.

### R7. Giai đoạn 2: Khắc phục Trực tiếp các Lỗ hổng Nghiêm trọng (P0 Remediation)
Dựa trên kết quả kiểm toán từ Giai đoạn 1, trực tiếp khắc phục các lỗ hổng nghiêm trọng nhất (mức P0) trong mã nguồn dự án:
- Bảo mật: Loại bỏ việc hardcode API key, chống rò rỉ thông tin nhạy cảm qua log hoặc error response.
- Ổn định & Hiệu năng: Xử lý các tác vụ Blocking I/O mạng, giải quyết rủi ro Race Condition khi đọc/ghi cache file JSON cục bộ, xử lý các lỗi tiềm ẩn gây crash ứng dụng.
- Logic tính toán & AI: Sửa chữa sai lệch thuật toán tính chỉ báo kỹ thuật (RSI, MACD, EMA), khắc phục nguy cơ Look-ahead Bias; bổ sung cơ chế xử lý lỗi/quota Gemini (429, 503, safety filter) và bảo đảm Structured Outputs JSON.
- Đảm bảo việc sửa chữa không làm phá vỡ các tính năng hiện có của hệ thống.

### R8. Kiểm thử Tự động Xác minh Sau Sửa chữa (Automated Verification)
Thực hiện kịch bản kiểm thử tự động để xác minh toàn diện hệ thống sau khi hoàn thành sửa chữa:
- Kiểm tra toàn bộ các module và tệp mã nguồn import thành công, không phát sinh lỗi cú pháp hay runtime error cơ bản.
- Kiểm tra các endpoint API phản hồi đúng chuẩn schema và hoạt động bình thường.

## Acceptance Criteria

### Giai đoạn 1: Báo cáo Kiểm toán Toàn diện
- [ ] Tệp `AUDIT_REPORT.md` được tạo tại thư mục gốc của dự án và chứa đầy đủ 4 phần theo yêu cầu: Bảng điểm (1-10), Danh sách lỗ hổng chết người, Danh sách góc khuất & Edge Cases, Bản thiết kế kiến trúc thế hệ mới.
- [ ] Bảng điểm đánh giá đầy đủ 5 trụ cột với thang điểm 1-10 kèm dẫn chứng cụ thể cho từng điểm số.
- [ ] Tất cả các lỗ hổng phát hiện được phân loại mức độ nghiêm trọng và trích dẫn chính xác đường dẫn tệp (file path) cùng số dòng liên quan trong dự án.
- [ ] Danh sách góc khuất & Edge Cases bao quát ít nhất các kịch bản: phiên ngoài giờ/nghỉ lễ, cổ phiếu bị hủy/đình chỉ, điều chỉnh giá kỹ thuật do cổ tức, và nghẽn/lỗi API nguồn dữ liệu.
- [ ] Bản thiết kế kiến trúc thế hệ mới đề xuất giải pháp kỹ thuật chi tiết cho cả 5 trụ cột theo mô hình 4 tầng: Dữ liệu -> Backend & Cache -> AI Engine -> Frontend.

### Giai đoạn 2: Khắc phục Lỗ hổng Nghiêm trọng & Kiểm thử Tự động
- [ ] Các lỗi nghiêm trọng thuộc nhóm P0 (bảo mật, crash, blocking I/O, sai lệch công thức RSI/MACD, quota Gemini, race condition cache) được sửa chữa trực tiếp trong mã nguồn.
- [ ] Không có API key hay thông tin nhạy cảm nào bị hardcode hoặc lộ qua log/error response.
- [ ] Kịch bản kiểm thử tự động được thực thi thành công, xác minh toàn bộ mã nguồn import hợp lệ, không có lỗi cú pháp và các API cốt lõi phản hồi đúng chuẩn.
