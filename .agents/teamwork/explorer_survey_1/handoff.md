# HANDOFF REPORT — FINANCIAL & QUANT AUDIT (R1 & R2-TA)

- **Agent**: `explorer_survey_1`
- **Roles**: Senior Quantitative Trader & Lead Financial Analyst (Hội đồng Chuyên gia Cấp cao)
- **Handoff Type**: Hard Handoff (Hoàn thành kiểm toán Trụ cột 1 & Trụ cột 2-TA)
- **Target Deliverable**: `financial_quant_audit.md` (Báo cáo kiểm toán chuyên sâu nghiệp vụ & định lượng)

---

## 1. OBSERVATION (Quan sát Trực tiếp & Bằng chứng Cốt lõi)

1. **Look-ahead Bias rò rỉ nến tương lai vào quá khứ:**
   - **Vị trí**: `backend/data_fetcher.py:91`
     ```python
     if target_date:
         end_date = datetime.strptime(target_date, '%Y-%m-%d') + timedelta(days=1)
     ```
   - **Dữ liệu thực tế tại Cache**: `backend/.cache/market_data_HPG_2026-05-03.json`:
     + Dòng 5: `"target_date": "2026-05-03"`
     + Dòng 2104–2110: `"Date": "2026-05-04", "Open": 27.75, "High": 27.95, "Low": 27.4, "Close": 27.6, "Volume": 32374300`
     + Không có câu lệnh lọc `df = df[df.index <= target_date]` sau khi tải từ `Quote.history`.
2. **Lỗi công thức RSI: Dùng SMA thay vì Wilder's Smoothing và Lỗi chia cho 0:**
   - **Vị trí**: `backend/data_fetcher.py:58-63`:
     ```python
     delta = df['Close'].diff()
     gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
     loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
     rs = gain / loss.replace(0, np.nan)
     df['RSI'] = 100 - (100 / (1 + rs))
     df['RSI'] = df['RSI'].fillna(50)
     ```
   - **Thực nghiệm Python đối chiếu**:
     + Chuỗi 14 phiên tăng trần liên tiếp (`loss = 0`): Code trả về **RSI = 50.0**, trong khi chuẩn Wilder TA là **RSI = 100.0**.
     + Dữ liệu thực tế mã HPG: Độ lệch lớn nhất giữa code và Wilder là **50.0 điểm**, MAE là **6.36 điểm**. Tại phiên gần nhất (decision candle), code ra **RSI = 26.09** (quá bán < 30), trong khi Wilder RSI là **42.03** (trung tính).
3. **Lỗi sập nguồn dữ liệu khi fallback sang TCBS:**
   - **Vị trí**: `backend/data_fetcher.py:102`: `for source in ('VCI', 'TCBS', 'KBS'):`
   - **Lỗi thực thi**: Gọi `Quote(symbol='HPG', source='TCBS')` ném lỗi:
     `ValueError: Lớp Quote chỉ nhận giá trị tham số source là kbs, vci, msn, dnse, binance, fmp, fmarket.`
4. **Lỗi nghiệp vụ T+3 và Lỗi Ngày Lịch (Calendar Days):**
   - **Vị trí**: `backend/ai_analyzer.py:48, 328`, `web/src/App.jsx:136-140`, `web/src/components/PriceTargetsAndPeers.jsx:13-18`
   - Code ghi nhận `T+3 (Hàng về)` (chu kỳ đã bãi bỏ từ tháng 8/2022).
   - Hàm `formatPredictionDate` cộng `daysFuture * 24 * 3600 * 1000` (ngày lịch), khiến ngày dự báo rơi vào Thứ Bảy, Chủ Nhật.
5. **Dữ liệu Khối ngoại, Tự doanh, Sổ lệnh, Phân tích Cơ bản (FA) bị bỏ quên / giả định:**
   - **Vị trí**: `backend/ai_analyzer.py:180-210`, `backend/ai_analyzer.py:202, 257`.
   - Biến `foreign_net` có trong template prompt nhưng không được đưa vào dict `values` của `build_user_prompt()`, luôn trả về `N/A`.
   - `fundamentals` bị gán chuỗi giả định; ở chế độ fallback `fund_score` bị gán cứng = `62`.
   - Dữ liệu Tự doanh và Order Book depth 3 mức giá hoàn toàn vắng bóng trong toàn bộ mã nguồn.

---

## 2. LOGIC CHAIN (Chuỗi Suy luận Logic từ Quan sát đến Kết luận)

1. **Từ Quan sát 1 $\rightarrow$ Suy luận về Look-ahead Bias:**
   Khi người dùng chạy giả lập tại ngày `target_date = 2026-05-03`, `end_date` bị cộng 1 ngày thành `2026-05-04`. Do vnstock xử lý `end_str` dạng inclusive và code thiếu bước lọc `df.index <= target_date`, nến giao dịch của Thứ Hai `2026-05-04` đã lọt vào dữ liệu. Kết quả là mọi tính toán chỉ báo và prompt gửi tới LLM đều biết trước giá đóng cửa của ngày hôm sau. Đây là lỗi Look-ahead Bias trực tiếp phá hủy tính giá trị của phân hệ định lượng.
2. **Từ Quan sát 2 $\rightarrow$ Suy luận về Sai lệch Chỉ báo Kỹ thuật:**
   Công thức RSI chuẩn của Welles Wilder dựa trên trung bình động làm mượt theo hàm mũ (RMA). Việc dùng `.rolling(window=14).mean()` tạo ra hiệu ứng vách đá (cliff effect) khi dữ liệu cũ bị loại bỏ. Nghiêm trọng hơn, khi cổ phiếu tăng trần liên tục không có phiên giảm, mẫu số `loss` bằng 0 bị ép thành `NaN`, khiến RSI bị gán mặc định thành 50.0 thay vì 100.0. Trên dữ liệu thực tế HPG, nến quyết định bị lệch tới -15.94 điểm RSI (tạo tín hiệu bắt đáy giả 26.09).
3. **Từ Quan sát 3 $\rightarrow$ Suy luận về Rủi ro Đứt gãy Pipeline Dữ liệu:**
   Việc hardcode danh sách nguồn `('VCI', 'TCBS', 'KBS')` trong đó có `TCBS` không tương thích với class `Quote` khiến tiến trình fallback bị chặn đứng bởi exception `ValueError`, làm tăng độ trễ và có nguy cơ làm rỗng dữ liệu khi VCI bị nghẽn mạng.
4. **Từ Quan sát 4 & 5 $\rightarrow$ Suy luận về Lỗ hổng Nghiệp vụ Thị trường Việt Nam:**
   Hệ thống thiếu các dòng dữ liệu cốt lõi chi phối thị trường Việt Nam (Khối ngoại, Tự doanh, Sổ lệnh chủ động, chỉ số tài chính P/E, P/B, ROE). Việc tính ngày dự báo theo ngày lịch thay vì ngày giao dịch chứng khoán khiến người dùng nhận được dự báo vào các ngày thị trường đóng cửa.

---

## 3. CAVEATS (Vùng Giới hạn & Giả định)

1. **Phạm vi kiểm toán:** Báo cáo tập trung chuyên sâu vào Trụ cột 1 (Nghiệp vụ Thị trường VN) và Trụ cột 2 (Chỉ báo Kỹ thuật & Định lượng). Các khía cạnh về Quota/Latency của Gemini API, Blocking I/O backend và Concurrency Cache được các chuyên gia kiến trúc hệ thống và AI đồng thời rà soát trong các báo cáo song song.
2. **Dữ liệu nguồn:** Đánh giá dựa trên mã nguồn hiện tại của dự án và hành vi của thư viện `vnstock` phiên bản đang được cài đặt trong môi trường `.venv`.
3. **Không chỉnh sửa trực tiếp mã nguồn:** Tuân thủ nguyên tắc Read-Only Investigation của Explorer; toàn bộ đề xuất sửa đổi mã nguồn đã được định dạng và phân loại rõ ràng (P0, P1, P2) sẵn sàng cho Giai đoạn 2.

---

## 4. CONCLUSION (Kết luận & Đánh giá)

- **Điểm số Trụ cột 1 (Nghiệp vụ Chứng khoán Việt Nam - R1):** **3.0 / 10**
- **Điểm số Trụ cột 2 (Chỉ báo Kỹ thuật & Định lượng - R2-TA):** **3.5 / 10**
- **Tổng số lỗ hổng phát hiện:** 10 lỗ hổng.
  + **4 lỗi P0 (Bắt buộc sửa ngay tại Giai đoạn 2):**
    * `P0-TA01`: Look-ahead Bias rò rỉ nến ngày tương lai vào dữ liệu lịch sử (`data_fetcher.py:91`).
    * `P0-TA02`: Công thức RSI sai chuẩn Wilder và dính lỗi chia 0 làm méo mó 50 điểm RSI (`data_fetcher.py:58-63`).
    * `P0-DATA01`: Nguồn `'TCBS'` trong `Quote` gây sập ngoại lệ `ValueError` làm đứt chuỗi fallback (`data_fetcher.py:102`).
    * `P0-FIN01`: Chu kỳ T+3 lạc hậu và lỗi cộng ngày lịch khiến dự báo rơi vào cuối tuần (`ai_analyzer.py:48`, `web/src/App.jsx:136-140`).
  + **5 lỗi P1 (Cần khắc phục để hoàn thiện tính năng):** `P1-FIN01` (Thiếu Market Session State), `P1-DATA02` (Bỏ quên Khối ngoại), `P1-FIN02` (FA bị gán tĩnh), `P1-TA03` (Méo mó Volume Intraday), `P1-DATA03` (Lệch pha tin tức/macro khi xem lịch sử).
  + **1 lỗi P2 (Cải thiện giao diện & cấu trúc):** `P2-UI01` (Thiếu sub-pane RSI/MACD và buy/sell markers trên chart).

---

## 5. VERIFICATION METHOD (Phương pháp Xác minh Độc lập)

Người nhận bàn giao hoặc kiểm toán viên độc lập có thể xác minh các phát hiện trên bằng các lệnh sau trong môi trường dự án:

1. **Xác minh Look-ahead Bias:**
   Kiểm tra tệp cache đã lưu:
   ```powershell
   Get-Content "backend\.cache\market_data_HPG_2026-05-03.json" | Select-String -Pattern "target_date|2026-05-04" -Context 2
   ```
   *Kết quả mong đợi:* Tìm thấy `"target_date": "2026-05-03"` nhưng dòng cuối cùng của nến lại là `"Date": "2026-05-04"`.

2. **Xác minh lỗi chia 0 và độ lệch RSI Wilder:**
   Chạy script Python kiểm thử:
   ```powershell
   .venv\Scripts\python.exe -c "
   import pandas as pd, numpy as np
   def cur_rsi(p):
       d = p.diff()
       g = (d.where(d > 0, 0)).rolling(14).mean()
       l = (-d.where(d < 0, 0)).rolling(14).mean()
       return (100 - (100 / (1 + (g / l.replace(0, np.nan)))))).fillna(50)
   p = pd.Series([10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0, 19.0, 20.0, 21.0, 22.0, 23.0, 24.0])
   print('Ceiling RSI:', cur_rsi(p).iloc[-1])
   "
   ```
   *Kết quả mong đợi:* In ra `Ceiling RSI: 50.0` (chứng minh lỗi 14 phiên tăng trần ra 50.0).

3. **Xác minh lỗi Quote với nguồn TCBS:**
   Chạy lệnh:
   ```powershell
   .venv\Scripts\python.exe -c "from vnstock.api.quote import Quote; q = Quote(symbol='HPG', source='TCBS')"
   ```
   *Kết quả mong đợi:* Ném `ValueError: Lớp Quote chỉ nhận giá trị tham số source là kbs, vci, msn, dnse, binance, fmp, fmarket.`
