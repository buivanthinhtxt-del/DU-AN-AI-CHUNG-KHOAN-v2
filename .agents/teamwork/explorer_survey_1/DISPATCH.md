## 2026-11-08T01:44:17Z
Sender: 561bec3b-3da6-43f1-a97b-5a4ed73cc1c8
Content:
Bạn là Senior Quantitative Trader & Lead Financial Analyst thuộc Hội đồng Chuyên gia Cấp cao thực hiện đợt STRESS-TEST & TOÀN DIỆN KIỂM TOÁN (DEEP AUDIT) dự án AI Chứng khoán (2-DU-AN-AI-CHUNG-KHOAN).

BẮT BUỘC:
1. Đọc kỹ file yêu cầu gốc: `d:\2- LÀM VIỆC\2- github du an 1\2-DU-AN-AI-CHUNG-KHOAN\.agents\teamwork\ORIGINAL_REQUEST.md`
2. Đọc file kế hoạch: `d:\2- LÀM VIỆC\2- github du an 1\2-DU-AN-AI-CHUNG-KHOAN\.agents\teamwork\PROJECT.md`
3. Working directory: `d:\2- LÀM VIỆC\2- github du an 1\2-DU-AN-AI-CHUNG-KHOAN`
4. State folder của bạn: `d:\2- LÀM VIỆC\2- github du an 1\2-DU-AN-AI-CHUNG-KHOAN\.agents\teamwork\explorer_survey_1\`

NHIỆM VỤ CỤ THỂ CỦA BẠN (Tập trung R1 và R2-TA):
Khảo sát và kiểm toán toàn diện mã nguồn hiện tại về khía cạnh Nghiệp vụ Tài chính Chứng khoán Việt Nam & Tính toán Định lượng:
- Trụ cột 1 (R1):
  + Cơ chế thời gian giao dịch & trạng thái sàn: ATO (9h00-9h15), ATC (14h30-14h45), phiên liên tục, phiên ngoài giờ, cuối tuần, ngày lễ. Hệ thống phản hồi thế nào khi người dùng truy vấn ban đêm/cuối tuần?
  + Quy tắc T+2.5: Các chỉ báo và mô hình dự báo đã tính đến chu kỳ hàng về tài khoản lúc 13h00 ngày T+2 chưa?
  + Dữ liệu trọng yếu: Khối ngoại mua/bán ròng, Tự doanh, Sổ lệnh (Order Book depth 3 mức giá, Active Buy vs Active Sell volume), Dữ liệu FA (P/E, P/B, ROE, Tăng trưởng LN/Doanh thu, Nợ/VCSH) kết hợp với TA, dữ liệu tâm lý F247/Vietstock.
- Trụ cột 2 - Phân hệ Tính toán Chỉ báo Kỹ thuật & Look-ahead Bias:
  + Cơ chế ghép nến ngày hiện tại (intraday realtime candle) vào chuỗi nến lịch sử để tính RSI, MACD, EMA. Có gây sai lệch thuật toán không?
  + Kiểm tra công thức toán học thực tế: RSI dùng Wilder Smoothing (chuẩn TA) hay SMA đơn giản? EMA tính hệ số multiplier 2/(N+1) thế nào? MACD tính đúng EMA12 - EMA26 và Signal EMA9 không?
  + Kiểm tra nguy cơ Look-ahead Bias: có bị shift dữ liệu sai, rò rỉ nến tương lai vào quá khứ không?
- Danh sách các góc khuất & Edge Cases nghiệp vụ: Cổ phiếu đình chỉ/hủy niêm yết, điều chỉnh giá kỹ thuật do cổ tức/thưởng, hiện tượng múa bên trăng (trắng bên mua/bán).
- Đánh giá điểm Trụ cột 1 (thang điểm 1-10) kèm dẫn chứng và trích dẫn file:dòng chính xác.

YÊU CẦU ĐẦU RA:
- Xuất file báo cáo chi tiết tại: `d:\2- LÀM VIỆC\2- github du an 1\2-DU-AN-AI-CHUNG-KHOAN\.agents\teamwork\explorer_survey_1\financial_quant_audit.md`
- Xuất file `handoff.md` tại `d:\2- LÀM VIỆC\2- github du an 1\2-DU-AN-AI-CHUNG-KHOAN\.agents\teamwork\explorer_survey_1\handoff.md` theo Handoff Protocol (Observation, Logic Chain, Caveats, Conclusion, Verification Method).
- Phân loại rõ các lỗi P0, P1, P2 (P0 = critical bug/sai logic nghiêm trọng cần sửa ngay ở Giai đoạn 2).
- Gửi tin nhắn hoàn thành cho orchestrator.
