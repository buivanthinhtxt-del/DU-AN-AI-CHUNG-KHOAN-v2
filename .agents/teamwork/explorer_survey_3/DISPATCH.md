## 2026-11-08T01:44:39Z
[Message] timestamp=2026-11-08T01:44:39Z sender=561bec3b-3da6-43f1-a97b-5a4ed73cc1c8 priority=MESSAGE_PRIORITY_HIGH content=Bạn là Principal AI/LLM Engineer & Senior Frontend Specialist thuộc Hội đồng Chuyên gia Cấp cao thực hiện đợt STRESS-TEST & TOÀN DIỆN KIỂM TOÁN (DEEP AUDIT) dự án AI Chứng khoán (2-DU-AN-AI-CHUNG-KHOAN).

BẮT BUỘC:
1. Đọc kỹ file yêu cầu gốc: `d:\2- LÀM VIỆC\2- github du an 1\2-DU-AN-AI-CHUNG-KHOAN\.agents\teamwork\ORIGINAL_REQUEST.md`
2. Đọc file kế hoạch: `d:\2- LÀM VIỆC\2- github du an 1\2-DU-AN-AI-CHUNG-KHOAN\.agents\teamwork\PROJECT.md`
3. Working directory: `d:\2- LÀM VIỆC\2- github du an 1\2-DU-AN-AI-CHUNG-KHOAN`
4. State folder của bạn: `d:\2- LÀM VIỆC\2- github du an 1\2-DU-AN-AI-CHUNG-KHOAN\.agents\teamwork\explorer_survey_3\`

NHIỆM VỤ CỤ THỂ CỦA BẠN (Tập trung R3-AI/LLM & R5-Frontend/Actionable Insights):
Khảo sát và kiểm toán toàn diện mã nguồn hiện tại về Kiến trúc AI, Prompt Reasoning, Độ tin cậy mô hình và Trải nghiệm Giao diện:
- Trụ cột 3 (R3) - Trí tuệ Nhân tạo & Prompt Chuyên sâu:
  + Kiểm soát ảo giác (Hallucination) & Tính cập nhật: Prompt có các ràng buộc nghiêm ngặt ngăn AI bịa số liệu tài chính không? Có Context Window Guard chống nhồi dữ liệu nến thô quá dài làm loãng sự chú ý của LLM không?
  + Định dạng đầu ra (Structured Outputs): Có dùng JSON Schema enforcement, response_mime_type="application/json", Pydantic models hay chỉ parse text regex/strip markdown `json...` dễ gãy?
  + Xử lý lỗi AI & Resilience: Khi Gemini trả về lỗi 429 Quota Exceeded, 503 Overloaded, hoặc bị chặn bởi Content Safety Filter, hệ thống xử lý thế nào? Có fallback sang model khác, retry với jitter hay throw exception làm crash endpoint?
- Trụ cột 5 (R5) - Trải nghiệm Người dùng & Tính Trực quan:
  + Khảo sát mã nguồn giao diện (HTML/JS/React/Vue/Streamlit...): Tính tương tác của biểu đồ (zoom/pan, công cụ vẽ, chỉ báo kỹ thuật kèm theo, đánh dấu điểm Mua/Bán Buy/Sell markers trên nến).
  + Tính thực chiến của khuyến nghị (Actionable Insights): Khuyến nghị AI có cung cấp cụ thể Vùng giải ngân (Entry Zone), Điểm chốt lời từng phần (Take Profit 1, 2), Ngưỡng cắt lỗ (Stoploss), và Tỷ trọng danh mục (Position Sizing) hay chỉ nói chung chung "nên theo dõi / khả năng tăng"?
- Đề xuất Bản thiết kế Kiến trúc Thế hệ Mới (Next-Gen Architecture Roadmap) cho 2 tầng: Tầng AI Engine & Tầng Frontend.
- Đánh giá điểm Trụ cột 3 và Trụ cột 5 (thang điểm 1-10) kèm dẫn chứng cụ thể trích dẫn chính xác file:dòng.
- Phân loại rõ các lỗ hổng P0, P1, P2 (P0 = critical bug cần sửa ở Giai đoạn 2).

YÊU CẦU ĐẦU RA:
- Xuất file báo cáo chi tiết tại: `d:\2- LÀM VIỆC\2- github du an 1\2-DU-AN-AI-CHUNG-KHOAN\.agents\teamwork\explorer_survey_3\ai_frontend_audit.md`
- Xuất file `handoff.md` tại `d:\2- LÀM VIỆC\2- github du an 1\2-DU-AN-AI-CHUNG-KHOAN\.agents\teamwork\explorer_survey_3\handoff.md` theo Handoff Protocol.
- Gửi tin nhắn hoàn thành cho orchestrator.
