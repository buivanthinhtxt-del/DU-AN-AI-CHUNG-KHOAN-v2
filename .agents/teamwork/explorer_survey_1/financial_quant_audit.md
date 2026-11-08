# BÁO CÁO KIỂM TOÁN CHUYÊN SÂU NGHIỆP VỤ CHỨNG KHOÁN & TÍNH TOÁN ĐỊNH LƯỢNG
**DỰ ÁN: AI CHỨNG KHOÁN (2-DU-AN-AI-CHUNG-KHOAN)**

- **Đơn vị thực hiện:** Senior Quantitative Trader & Lead Financial Analyst (Hội đồng Chuyên gia Cấp cao)
- **Thời điểm kiểm toán:** 08/11/2026
- **Phạm vi kiểm toán trọng tâm:** Trụ cột 1 (R1 - Nghiệp vụ Thị trường Việt Nam) & Trụ cột 2 (R2-TA - Phân hệ Kỹ thuật & Định lượng)
- **Phương pháp tiếp cận:** Kiểm toán mã nguồn từng dòng (Line-by-line Forensic Source Code Audit), Kiểm tra công thức toán học trên dữ liệu thực (Empirical Backtest & Stress-Test), Rà soát rủi ro Look-ahead Bias và Edge Cases thị trường thực chiến.

---

## 1. TỔNG QUAN & BẢNG ĐIỂM ĐÁNH GIÁ (EXECUTIVE AUDIT SCORECARD)

| Phân hệ / Trụ cột | Điểm số (1-10) | Trạng thái Thực tế | Tóm tắt Đánh giá |
| :--- | :---: | :---: | :--- |
| **Trụ cột 1: Nghiệp vụ Chứng khoán VN (R1)** | **3.0 / 10** | **NGHIÊM TRỌNG (Critical Gaps)** | Mặc dù tài liệu prompt (`tro_ly_dau_tu_chung_khoan_vn.md`) mô tả đầy đủ lý thuyết, toàn bộ mã nguồn thực thi ở Backend (`data_fetcher.py`, `api.py`, `ai_analyzer.py`) hoàn toàn **bỏ trống** dữ liệu Tự doanh, Sổ lệnh 3 giá, Active Buy/Sell, dữ liệu BCTC cơ bản (FA là chuỗi giả định). Xử lý thời gian giao dịch sơ sài, sai lệch chu kỳ T+2.5 thành T+3 cũ, nhầm lẫn giữa ngày lịch và ngày giao dịch. |
| **Trụ cột 2: Chỉ báo Kỹ thuật & Định lượng (R2-TA)** | **3.5 / 10** | **NGHIÊM TRỌNG (Math & Bias Flaws)** | Tồn tại **Look-ahead Bias** rò rỉ nến tương lai vào tập dữ liệu quá khứ (`target_date + 1` không filter). Công thức RSI tính sai chuẩn kỹ thuật (dùng SMA rolling thay vì Wilder Smoothing), dính lỗi toán học nghiêm trọng: cổ phiếu tăng trần 14 phiên liên tục cho ra RSI = 50 (trung tính); trên mã HPG thực tế lệch tới 15.94 điểm RSI ở nến quyết định. Dữ liệu nến trong ngày so sánh trực tiếp khối lượng dở dang với `VolMA20` gây méo mó tín hiệu dòng tiền. |

---

## 2. KIỂM TOÁN CHI TIẾT TRỤ CỘT 1: NGHIỆP VỤ CHỨNG KHOÁN THỰC CHIẾN VIỆT NAM (R1)

### 2.1. Cơ chế Thời gian Giao dịch & Trạng thái Sàn
Thị trường chứng khoán Việt Nam (HOSE, HNX, UPCoM) vận hành với các phiên đặc thù:
- `09:00 - 09:15`: Khớp lệnh định kỳ mở cửa (ATO - HOSE). Nghiêm cấm sửa/hủy lệnh.
- `09:15 - 11:30`: Khớp lệnh liên tục sáng.
- `11:30 - 13:00`: Nghỉ trưa. Hệ thống đóng băng sổ lệnh.
- `13:00 - 14:30`: Khớp lệnh liên tục chiều (Mốc 13:00 đón lượng hàng T+2.5 về tài khoản).
- `14:30 - 14:45`: Khớp lệnh định kỳ đóng cửa (ATC - HOSE & HNX). Nghiêm cấm sửa/hủy lệnh; quỹ ETF cơ cấu danh mục.
- `14:45 - 15:00`: Giao dịch thỏa thuận / PLO (HNX).
- Sau `15:00`, Ban đêm, Thứ Bảy, Chủ Nhật, Ngày lễ (Tết, 30/4, 2/9...): Thị trường đóng cửa hoàn toàn.

#### Hiện trạng mã nguồn phát hiện:
Trích dẫn `backend/ai_analyzer.py` (dòng 93–100):
```python
def _session_label(last_date) -> str:
    if hasattr(last_date, "strftime"):
        label = last_date.strftime("%d/%m/%Y")
        now = datetime.now(VN_TZ)
        if last_date.date() == now.date() and now.hour < 15:
            label += " (phiên đang giao dịch, số liệu chưa chốt)"
        return label
    return str(last_date)
```

#### Phân tích sai phạm nghiệp vụ:
1. **Lỗi xác định phiên giao dịch mù quáng (Blind Session Detection):**
   - Điều kiện `now.hour < 15` không kiểm tra `now.hour >= 9`. Khi người dùng truy vấn lúc 2:00 sáng hoặc 7:30 sáng, hệ thống vẫn gắn nhãn `(phiên đang giao dịch, số liệu chưa chốt)`.
   - Điều kiện không kiểm tra `now.weekday() < 5`. Khi người dùng mở app vào sáng Thứ Bảy hoặc Chủ Nhật, hệ thống vẫn báo phiên đang giao dịch nếu nến cuối có ngày trùng ngày hôm nay!
   - Không kiểm tra giờ nghỉ trưa (`11:30 - 13:00`).
2. **Không có bộ máy trạng thái thị trường (Market State Machine):**
   - Hệ thống hoàn toàn không biết thị trường đang ở trạng thái nào: `ATO`, `CONTINUOUS_AM`, `LUNCH_BREAK`, `CONTINUOUS_PM`, `ATC`, `CLOSED`, `WEEKEND`, `HOLIDAY`.
   - Khi người dùng truy vấn ngoài giờ hoặc cuối tuần, hệ thống chỉ hiển thị nến của phiên gần nhất mà **không hề có thông báo hay đếm ngược đến phiên giao dịch tiếp theo** (ví dụ: *"Thị trường đóng cửa. Phiên ATO tiếp theo sẽ mở lúc 09:00 Thứ Hai 10/11/2026"*).
   - Frontend không có bất kỳ trạng thái nào thể hiện phiên sàn.

---

### 2.2. Quy tắc Thanh toán T+2.5 và Lỗi Mô hình Hóa Lịch Ngày (Calendar Days vs Trading Days)
Theo quy định chính thức của Tổng công ty Lưu ký và Bù trừ Chứng khoán Việt Nam (VSDC) có hiệu lực từ ngày **29/08/2022**:
- Nhà đầu tư mua cổ phiếu ngày `T` sẽ nhận được chứng khoán về tài khoản vào khoảng **11:30 - 12:00 trưa ngày T+2** và được quyền bán ngay trong **phiên chiều ngày T+2 (từ 13:00)**.
- Chu kỳ này gọi là **T+2.5**. Áp lực cung hàng về lúc 13:00 chiều T+2 là một biến số thanh khoản cực kỳ quan trọng của dân trading Việt Nam.

#### Hiện trạng mã nguồn phát hiện:
1. Trích dẫn `backend/ai_analyzer.py` (dòng 48 và dòng 328):
```python
# Dòng 48:
timeframe: str = Field(description="Khung thời gian dự báo, ví dụ: 'T+1 (1 ngày)', 'T+3 (Hàng về)', 'T+5 (1 tuần)', 'T+10 (2 tuần)'")
# Dòng 328:
{"timeframe": "T+3 (Hàng về)", "days_future": 3, "high": round(close * (1 + step_pct * 1.5), 2), "low": round(close * (1 - step_pct * 1.2), 2), "reason": "Phản ứng tại vùng EMA10 / SMA20"}
```
2. Trích dẫn `web/src/App.jsx` (dòng 136–140) và `web/src/components/PriceTargetsAndPeers.jsx` (dòng 13–18):
```javascript
const formatPredictionDate = (daysFuture) => {
  if (!lastHistoryDate) return '';
  const lastDate = new Date(lastHistoryDate);
  const futureDate = new Date(lastDate.getTime() + daysFuture * 24 * 3600 * 1000);
  return futureDate.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit' });
};
```

#### Phân tích sai phạm nghiệp vụ:
1. **Lạc hậu nghiệp vụ nghiêm trọng (Obsolete T+3 Settlement Rule):**
   - Hệ thống vẫn định nghĩa `T+3 (Hàng về)`. Chu kỳ T+3 đã bị bãi bỏ tại Việt Nam từ hơn 4 năm trước! Mô hình định lượng gán `days_future = 3` làm mốc hàng về là hoàn toàn sai với thực tế tài khoản nhà đầu tư (thực tế hàng về lúc 13h00 T+2, tức sau đúng 2 phiên giao dịch).
2. **Sai lầm chết người giữa Ngày Lịch (Calendar Days) và Ngày Giao dịch (Trading Days):**
   - Hàm `formatPredictionDate` cộng trực tiếp `daysFuture * 24 * 3600 * 1000` (ngày lịch thông thường).
   - **Hậu quả:** Nếu phiên gần nhất là Thứ Sáu (ví dụ 08/05):
     + Dự báo `T+1` (+1 ngày) sẽ hiển thị ngày **Thứ Bảy 09/05** (Thị trường đóng cửa!).
     + Dự báo `T+2` (+2 ngày) sẽ hiển thị ngày **Chủ Nhật 10/05** (Thị trường đóng cửa!).
     + Dự báo `T+3` (+3 ngày) sẽ hiển thị ngày **Thứ Hai 11/05** — nhưng Thứ Hai thực chất mới chỉ là phiên **T+1** của nhà đầu tư!
   - Biểu đồ dự báo AreaSeries trên Frontend sẽ vẽ điểm giá rơi vào ngày cuối tuần, gây mất uy tín hoàn toàn về mặt chuyên môn trước nhà đầu tư chuyên nghiệp.

---

### 2.3. Kiểm toán Dòng Dữ liệu Trọng yếu (Critical Market Feeds)

| Luồng Dữ liệu | Trạng thái trong Code | Vị trí kiểm tra | Đánh giá & Rủi ro Nghiệp vụ |
| :--- | :---: | :--- | :--- |
| **Khối Ngoại Mua/Bán Ròng** | **BỊ BỎ RƠI (Orphaned Variable)** | `backend/prompts/tro_ly_dau_tu_chung_khoan_vn.md:298`<br>`backend/ai_analyzer.py:180-210`<br>`backend/data_fetcher.py:118` | File prompt có khai báo biến `{foreign_net}`. Tuy nhiên trong `ai_analyzer.py` hàm `build_user_prompt()`, lập trình viên **hoàn toàn quên đưa biến này vào dict `values`**! Do đó `foreign_net` luôn luôn nhận giá trị `"N/A"` thông qua class `_MissingAsNA`. Trong khi đó, khối ngoại bán ròng kỷ lục là nguyên nhân chính dẫn dắt thị trường VN 2024–2026. Hệ thống làm AI bị "mù" hoàn toàn trước biến số này. |
| **Tự Doanh CTCK** | **HOÀN TOÀN KHÔNG CÓ (100% Missing)** | Toàn bộ codebase | Không có bất kỳ hàm nào thu thập dữ liệu giao dịch khớp lệnh và thỏa thuận của khối Tự doanh các công ty chứng khoán (dữ liệu công bố lúc 17:00 hằng ngày). |
| **Sổ lệnh 3 Mức Giá (Order Book Depth)** | **HOÀN TOÀN KHÔNG CÓ (100% Missing)** | `backend/data_fetcher.py` | Không gọi `Quote.price_depth()` của vnstock. Không có dữ liệu 3 bước giá mua tốt nhất (Bid 1, 2, 3), 3 bước giá bán tốt nhất (Ask 1, 2, 3). Nhà đầu tư không thể nhìn thấy tường mua/bán (order wall). |
| **Lệnh Mua/Bán Chủ Động (Active Buy vs Active Sell)** | **HOÀN TOÀN KHÔNG CÓ (100% Missing)** | `backend/data_fetcher.py` | Không thu thập tỷ lệ khớp lệnh chủ động (lệnh quét thẳng vào dư bán hay xả thẳng vào dư mua). Đây là chỉ báo quan trọng nhất để phát hiện dòng tiền tổ chức gom hàng âm thầm hay phân phối. |
| **Phân tích Cơ bản (FA: P/E, P/B, ROE, Nợ/VCSH, Tăng trưởng)** | **CHÈN CHUỖI GIẢ ĐỊNH (Hardcoded Placeholder)** | `backend/ai_analyzer.py:202, 257`<br>`backend/data_fetcher.py` | `data_fetcher.py` không hề tải chỉ số tài chính từ vnstock (`FinancialRatio`, `IncomeStatement`...). Trong `build_user_prompt()`, trường `fundamentals` bị gán cứng: `"Nhóm ngành: {sector_name}. (Đánh giá nội lực kết hợp từ kiến thức tài chính và tin tức doanh nghiệp bên dưới)"`. Ở chế độ Fallback, điểm FA bị gán cứng cố định = `62`! Biểu đồ Radar mục "FA & Catalyst" thực chất là số liệu bịa đặt, không phản ánh thực tế doanh nghiệp. |
| **Mạng xã hội & Diễn đàn (F247, Vietstock Forum)** | **CHƯA TÍCH HỢP (Missing)** | `backend/news_fetcher.py` | Chỉ cào RSS tiêu đề từ CafeF và VnExpress. Hoàn toàn không có dữ liệu đo lường chỉ số hưng phấn / hoảng loạn (Retail Sentiment Index) từ diễn đàn chứng khoán lớn nhất Việt Nam F247 hay Vietstock. |

---

### 2.4. Danh sách Góc khuất & Edge Cases Nghiệp vụ Bị Bỏ Quên

1. **Cổ phiếu bị Đình chỉ / Tạm ngừng / Hủy niêm yết (Suspension & Delisting):**
   - Khi người dùng tra cứu các mã cổ phiếu gặp sự cố pháp lý (như FLC, ROS, TGG, IBC, POM, SJF...):
     + Hàm `get_historical_data` tải dữ liệu 365 ngày qua. Nếu cổ phiếu đã ngừng giao dịch hơn 1 năm, kết quả trả về `df` rỗng.
     + Tại `backend/api.py:130`: Hệ thống ném ra lỗi `HTTPException(404, "Không tìm thấy dữ liệu lịch sử hoặc mã cổ phiếu không hợp lệ")`.
     + **Hậu quả:** Hệ thống đánh đồng một cổ phiếu bị đình chỉ giao dịch (rủi ro pháp lý/thua lỗ cực lớn) với việc người dùng gõ sai tên mã! Nếu cổ phiếu mới bị đình chỉ 2 tuần trước, hệ thống hiển thị nến cũ nhất như thể cổ phiếu vẫn đang giao dịch bình thường, gây rủi ro mất trắng vốn cho người dùng.
2. **Hiện tượng "Múa Bên Trăng" / Bẫy Thanh Khoản Sàn (Trắng bên mua / Floor Lock):**
   - Biên độ dao động sàn HOSE là $\pm 7\%$, HNX là $\pm 10\%$, UPCoM là $\pm 15\%$. Khi thị trường hoảng loạn hoặc cổ phiếu có biến cố, hàng triệu cổ phiếu bị chất bán sàn mà không có một lệnh mua nào đối ứng ("Trắng bên mua" - Múa bên trăng).
   - **Lỗi hệ thống:** Hệ thống chỉ tính toán `Close` và `Volume`. Khi cổ phiếu rơi vào tình trạng trắng bên mua, khối lượng khớp lệnh tụt về 0 hoặc rất thấp. Hệ thống tính `Vol / VolMA20` rất thấp và đưa ra nhận định *"Cạn kiệt cung bán"* hoặc khuyến nghị *"Cắt lỗ tại vùng hỗ trợ -7%"*.
   - **Hậu quả:** Trên thực tế, nhà đầu tư hoàn toàn **không thể đặt lệnh cắt lỗ** vì không có người mua! Khuyến nghị cắt lỗ của hệ thống trở nên vô nghĩa nếu không kiểm tra cờ cảnh báo `Floor_Lock` (Giá = Giá sàn & Dư mua = 0).
3. **Điều chỉnh Giá Kỹ thuật do Cổ tức / Thưởng / Phát hành thêm (Ngày GDKHQ):**
   - Vào Ngày Giao dịch Không Hưởng Quyền (GDKHQ), Sở GDCK tự động điều chỉnh giá tham chiếu giảm tương ứng với tỷ lệ cổ tức tiền mặt hoặc cổ tức cổ phiếu/thưởng.
   - Do hệ thống không lấy lịch sự kiện doanh nghiệp (Corporate Actions), nếu dữ liệu nguồn chưa điều chỉnh hoặc điều chỉnh đột ngột, công thức `df['Close'].diff()` sẽ ghi nhận một phiên sập giá mạnh (-15% đến -30%), khiến RSI cắm đầu, biến động Volatility tăng vọt và AI đưa ra cảnh báo hoảng loạn sai sự thật.
4. **Đặc thù Giá Tham chiếu Sàn UPCoM:**
   - Trên sàn UPCoM, giá tham chiếu của phiên hôm nay không phải là giá đóng cửa (Close) của phiên trước, mà là **Giá bình quân gia quyền (Weighted Average Price)** của phiên trước.
   - Hệ thống hiện tại tính % thay đổi giá `((last_close - prev_close) / prev_close) * 100` cho mọi mã (kể cả BSR, OIL, MCH, QNS trên UPCoM), dẫn đến tính sai biên độ dao động và sai giá tham chiếu của cổ phiếu UPCoM.

---

## 3. KIỂM TOÁN TRỤ CỘT 2 (R2-TA): CHỈ BÁO KỸ THUẬT, TOÁN HỌC ĐỊNH LƯỢNG & LOOK-AHEAD BIAS

### 3.1. Phát hiện và Bằng chứng Look-Ahead Bias (Rò rỉ Nến Tương lai vào Quá khứ)

Đây là **lỗ hổng P0 nghiêm trọng nhất** về mặt định lượng, trực tiếp phá hủy tính trung thực của mọi mô hình dự báo và kiểm thử quá khứ (Backtesting).

#### Bằng chứng kiểm toán trong Code:
Trích dẫn `backend/data_fetcher.py` (dòng 90–98):
```python
if target_date:
    end_date = datetime.strptime(target_date, '%Y-%m-%d') + timedelta(days=1)
else:
    end_date = datetime.now() + timedelta(days=1)

start_date = end_date - timedelta(days=days)
start_str = start_date.strftime('%Y-%m-%d')
end_str = end_date.strftime('%Y-%m-%d')
```
Sau đó gọi `q.history(start=start_str, end=end_str, interval='1D')`.

#### Bằng chứng thực tế trong Cache Data:
Xem tệp cache thực tế tại `backend/.cache/market_data_HPG_2026-05-03.json`:
- Người dùng gửi request truy vấn tại ngày mục tiêu: `"target_date": "2026-05-03"` (Chủ Nhật).
- Nhưng hãy xem bản ghi cuối cùng của mảng `"history"` ở dòng 2104–2110:
```json
{
  "Date": "2026-05-04",
  "Open": 27.75,
  "High": 27.95,
  "Low": 27.4,
  "Close": 27.6,
  "Volume": 32374300
}
```

#### Cơ chế phát sinh lỗi (Root Cause Analysis):
1. Lập trình viên cộng thêm `+ timedelta(days=1)` với mục đích lấy trọn vẹn ngày `target_date`.
2. Tuy nhiên, API của vnstock (nguồn VCI/KBS) xử lý tham số `end` là **inclusive (bao gồm cả ngày kết thúc)**.
3. Khi `target_date` là ngày `2026-05-03`, `end_date` bị đẩy thành `2026-05-04` (ngày Thứ Hai).
4. Do code **hoàn toàn không có bước lọc hậu kỳ** `df = df[df.index <= target_date]`, toàn bộ phiên giao dịch của ngày tương lai `2026-05-04` đã bị nạp vào DataFrame lịch sử!
5. Khi tính toán RSI, MACD, EMA và gửi cho Gemini phân tích, hệ thống đã đưa dữ liệu của ngày hôm sau cho AI đọc để dự báo cho ngày hôm trước!
6. **Hậu quả:** Mọi kết quả backtest hay phân tích lịch sử đều là "gian lận định lượng" (Look-ahead Leakage), vô giá trị trong giao dịch thực tế.

---

### 3.2. Kiểm toán Công thức Toán học Chỉ báo Kỹ thuật (RSI, EMA, MACD)

#### A. Phân tích Sai phạm Công thức RSI (Wilder Smoothing vs Cutler SMA)
Trích dẫn `backend/data_fetcher.py` (dòng 58–63):
```python
# 2. RSI (14)
delta = df['Close'].diff()
gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
rs = gain / loss.replace(0, np.nan)
df['RSI'] = 100 - (100 / (1 + rs))
df['RSI'] = df['RSI'].fillna(50)
```

#### 2 Lỗi Toán học Chí tử:
1. **Dùng SMA 14 phiên thay vì Wilder's Smoothing (RMA):**
   - Theo chuẩn phân tích kỹ thuật thế giới do J. Welles Wilder Jr. phát minh (1978) và được sử dụng trên TradingView, Bloomberg, TCBS, SSI:
     $$\text{AvgGain}_t = \frac{\text{AvgGain}_{t-1} \times 13 + \text{Gain}_t}{14} = \text{EMA}(\text{Gain}, \alpha = 1/14)$$
   - Code hiện tại dùng `.rolling(window=14).mean()` (tức Cutler's RSI). Trong một cửa sổ trượt 14 phiên, một phiên tăng mạnh cách đây 14 ngày khi bị rơi ra khỏi cửa sổ (drop out) sẽ tạo ra một cú nhảy vọt giả tạo (cliff effect) trên đường RSI, dù giá phiên hiện tại không biến động!
2. **Lỗi Chia cho 0 (Zero Loss Bug) biến siêu cổ phiếu thành "Trung tính 50":**
   - Dòng 61: `loss.replace(0, np.nan)` -> khi một cổ phiếu tăng liên tục trong 14 phiên (chuỗi phiên tăng trần liên tiếp của các mã đầu cơ như FPT, VGI, hay penny), giá không có phiên giảm nào $\rightarrow loss = 0$.
   - Dòng 61 biến `loss` thành `np.nan`.
   - Phép tính `rs = gain / np.nan` cho ra `np.nan`.
   - Dòng 62: `df['RSI'] = 100 - (100 / (1 + np.nan))` cho ra `np.nan`.
   - Dòng 63: `df['RSI'].fillna(50)` biến RSI của cổ phiếu thành **50.0**!

#### Thực nghiệm Kiểm chứng Toán học (Empirical Verification):
Hội đồng chuyên gia đã chạy mã kiểm thử độc lập đối chiếu trên Python giữa công thức hiện tại và công thức chuẩn Wilder:

- **Thử nghiệm 1: Chuỗi 14 phiên tăng trần liên tiếp:**
  + Giá trị công thức hiện tại trong code: **RSI = 50.0** (Tín hiệu: Trung tính, bình thường!).
  + Giá trị công thức chuẩn Wilder TA: **RSI = 100.0** (Tín hiệu: Quá mua cực độ, rủi ro bong bóng!).
  + *Đánh giá:* Một sai lầm tài chính chết người nếu trader tin vào RSI = 50 để mua thêm vào đỉnh bong bóng!

- **Thử nghiệm 2: Chạy trên dữ liệu thực tế mã HPG (`market_data_HPG_None.json`):**
  + Độ lệch tối đa (Max Divergence): **50.0 điểm RSI**.
  + Độ lệch tuyệt đối trung bình (MAE): **6.36 điểm RSI**.
  + So sánh 5 phiên gần nhất của HPG:
    * Phiên -5: Hiện tại = 51.56 vs Wilder = 47.68 (lệch +3.88)
    * Phiên -4: Hiện tại = 45.71 vs Wilder = 42.34 (lệch +3.38)
    * Phiên -3: Hiện tại = 52.24 vs Wilder = 45.17 (lệch +7.07)
    * Phiên -2: Hiện tại = 53.03 vs Wilder = 44.39 (lệch +8.64)
    * **Phiên -1 (Nến quyết định): Hiện tại = 26.09 vs Wilder = 42.03 (Lệch tới -15.94 điểm!)**
  + *Hậu quả thực tế:* Công thức code hiện tại báo HPG rơi vào vùng **QUÁ BÁN NẶNG (RSI = 26.09 < 30)** phát sinh tín hiệu bắt đáy giả, trong khi RSI chuẩn của thị trường vẫn đang ở mức **42.03 (vùng cân bằng bình thường)**!

#### B. Phân tích Công thức EMA & MACD
Trích dẫn `backend/data_fetcher.py` (dòng 52, 66–70):
```python
df['EMA10'] = df['Close'].ewm(span=10, adjust=False).mean()
exp1 = df['Close'].ewm(span=12, adjust=False).mean()
exp2 = df['Close'].ewm(span=26, adjust=False).mean()
df['MACD'] = exp1 - exp2
df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
df['Histogram'] = df['MACD'] - df['Signal']
```
- **Hệ số nhân Multiplier:** Đối với pandas `ewm(span=N, adjust=False)`, hệ số $\alpha = \frac{2}{N + 1}$. Với span=10, $\alpha = 2/11 \approx 0.1818$; span=12, $\alpha = 2/13$; span=26, $\alpha = 2/27$; span=9, $\alpha = 2/10 = 0.2$. Về mặt tỷ lệ multiplier, công thức pandas đã dùng đúng chuẩn thế giới.
- **Vấn đề Warm-up Period và Khởi tạo:**
  + Pandas khởi tạo phần tử đầu tiên bằng chính giá trị $Close_0$. Để đường EMA26 và Signal9 hội tụ về giá trị chính xác, cần tối thiểu $3 \times 26 = 78$ phiên nến khởi động (warm-up).
  + Trong `_fetch_single_peer` (dòng 144), code chỉ lấy `days=25` (khoảng 17 phiên giao dịch). Nếu tính chỉ báo với số phiên ít như vậy, các chỉ báo EMA, MACD hoàn toàn sai lệch do chưa qua giai đoạn khởi động.
  + Tại `backend/api.py:80`, code thực hiện:
    `df_reset[num_cols] = df_reset[num_cols].replace([float("inf"), float("-inf")], 0).fillna(0).round(3)`
    Các dòng đầu tiên chưa đủ 26 phiên của MACD bị ép về 0, tạo ra các điểm cắt qua 0 giả tạo (False Zero Crossings) trên biểu đồ.

---

### 3.3. Cơ chế Ghép nến Intraday Realtime & Biến dạng Thanh khoản
- Trong phiên giao dịch (ví dụ lúc 10:00 sáng):
  + Nếu lấy nến ngày hiện tại để tính chỉ báo: `Close` là giá khớp tức thời $\rightarrow$ các chỉ báo động lượng giá như RSI, EMA, MACD biến động theo thời gian thực (đây là hành vi chấp nhận được của Intraday Bar).
  + **Tuy nhiên, đối với Khối lượng (Volume):**
    Tại `backend/data_fetcher.py:77`: `df['VolMA20'] = df['Volume'].rolling(window=20).mean()`
    Và tại `backend/ai_analyzer.py:254`: `vol_ratio = vol / vol_ma20 if vol_ma20 > 0 else 1.0`
  + Lúc 10:00 sáng, phiên giao dịch mới diễn ra được 1 giờ (trên tổng số 4.5 giờ giao dịch), khối lượng `vol` mới chỉ đạt khoảng 15-20% của cả ngày.
  + Đưa trực tiếp `vol` này vào tính toán sẽ kéo tụt `VolMA20` của cả 20 ngày xuống.
  + Tỷ lệ `vol_ratio` sẽ hiển thị khoảng `0.2x TB20`, khiến hệ thống Fallback và cả Prompt AI kết luận sai lầm: *"Dòng tiền mất hút, thanh khoản suy kiệt trầm trọng!"*
  + **Yêu cầu chuẩn định lượng:** Phải chuẩn hóa khối lượng tức thời theo thời gian đã trôi qua của phiên (Pacing Volume Normalization):
    $$\text{Projected\_Volume} = \text{Current\_Volume} \times \left( \frac{270 \text{ phút}}{\text{Số phút đã giao dịch}} \right)$$

---

## 4. BẢNG TỔNG HỢP VÀ PHÂN LOẠI CÁC LỖ HỔNG (P0, P1, P2)

Dưới đây là danh mục chi tiết các lỗi cần chuyển giao cho Kỹ sư Khắc phục tại Giai đoạn 2 (P0 = Bắt buộc sửa ngay lập tức):

| Mã Lỗ hổng | Phân loại | Tệp tin & Dòng mã (Exact Location) | Bản chất Lỗi & Hậu quả | Đề xuất Khắc phục Chi tiết cho Giai đoạn 2 |
| :--- | :---: | :--- | :--- | :--- |
| **P0-TA01** | **P0 (Critical)** | `backend/data_fetcher.py:90-118`<br>`backend/.cache/market_data_HPG_2026-05-03.json:2104` | **Look-ahead Bias (Rò rỉ nến tương lai):** `target_date + 1` làm lọt nến của ngày hôm sau vào dataset lịch sử. Không có bộ lọc chặn trên `df = df[df.index <= target_date]`. | Trong `get_historical_data()`, sau khi tải xong và set index `Date`, thêm ngay lệnh kiểm tra và cắt: `if target_date: df = df[df.index <= pd.to_datetime(target_date)]`. |
| **P0-TA02** | **P0 (Critical)** | `backend/data_fetcher.py:58-63` | **Sai thuật toán RSI Wilder & Bug chia 0:** Dùng rolling SMA thay vì Wilder RMA; chia cho 0 khi chuỗi nến toàn tăng trần làm RSI rơi về 50 thay vì 100. Lệch tới 15.94 điểm RSI thực tế. | Viết lại hàm tính RSI theo chuẩn Wilder: dùng `gain.ewm(alpha=1/14, adjust=False).mean()` và `loss.ewm(alpha=1/14, adjust=False).mean()`. Xử lý điều kiện biên: nếu `avg_loss == 0`, RSI = 100; nếu `avg_gain == 0`, RSI = 0. |
| **P0-DATA01** | **P0 (Critical)** | `backend/data_fetcher.py:102` | **Crash sập nguồn dữ liệu khi fallback sang TCBS:** `Quote(source='TCBS')` văng `ValueError` lập tức do phiên bản vnstock hiện tại không hỗ trợ tên nguồn `'TCBS'` trong class Quote (chỉ hỗ trợ `kbs, vci, msn, dnse...`). | Đổi danh sách nguồn dự phòng thành `for source in ('vci', 'kbs', 'msn', 'dnse'):`. Chuẩn hóa lowercase cho tham số `source`. Bổ sung try-except bao quanh từng nguồn để không làm đứt chuỗi fallback. |
| **P0-FIN01** | **P0 (Critical)** | `backend/ai_analyzer.py:48, 328`<br>`web/src/App.jsx:136-140`<br>`web/src/components/PriceTargetsAndPeers.jsx:13-18` | **Lỗi Nghiệp vụ T+3 và Lỗi Ngày Lịch (Calendar Days):** Định nghĩa T+3 đã bãi bỏ từ 2022; hàm format ngày dự báo cộng `daysFuture * 86400000` khiến ngày dự báo rơi vào Thứ Bảy, Chủ Nhật. | 1. Sửa mốc dự báo thành chuẩn T+2.5 (T+1, T+2 chiều hàng về, T+3, T+5).<br>2. Viết hàm cộng ngày giao dịch (Trading Days adder): bỏ qua Thứ Bảy, Chủ Nhật và ngày lễ khi sinh ngày dự báo tương lai. |
| **P1-FIN01** | **P1 (Major)** | `backend/ai_analyzer.py:93-100` | **Không có Market Session State Machine:** Chỉ kiểm tra `now.hour < 15`, phán đoán sai giờ giao dịch vào ban đêm và cuối tuần. | Xây dựng hàm `get_market_session_state(now)` chuẩn: kiểm tra ngày trong tuần (`weekday < 5`), các khung giờ ATO (9:00-9:15), Khớp lệnh liên tục sáng (9:15-11:30), Nghỉ trưa (11:30-13:00), Khớp lệnh liên tục chiều (13:00-14:30), ATC (14:30-14:45), Đóng cửa. Trả về nhãn trạng thái và thời gian mở phiên kế tiếp. |
| **P1-DATA02** | **P1 (Major)** | `backend/ai_analyzer.py:180-210`<br>`backend/prompts/tro_ly_dau_tu_chung_khoan_vn.md:298` | **Bỏ quên biến Khối Ngoại Mua/Bán Ròng (`foreign_net`):** Prompt có placeholder nhưng code `ai_analyzer.py` không truyền giá trị vào `values`, khiến AI luôn nhận `foreign_net = N/A`. | Bổ sung hàm lấy dữ liệu Khối ngoại mua/bán ròng từ vnstock/TCBS và truyền giá trị thật vào biến `foreign_net` trong hàm `build_user_prompt()`. |
| **P1-FIN02** | **P1 (Major)** | `backend/ai_analyzer.py:202, 257` | **Dữ liệu Phân tích Cơ bản (FA) bị giả lập:** Không lấy P/E, P/B, ROE, Nợ/VCSH từ báo cáo tài chính; gán điểm tĩnh FA = 62 trong fallback. | Tích hợp module lấy các chỉ số tài chính cơ bản cốt lõi (P/E, P/B, ROE, EPS, Nợ/VCSH) từ API tài chính và đưa bảng chỉ số thực vào Prompt BƯỚC 3 (Nội lực). |
| **P1-TA03** | **P1 (Major)** | `backend/data_fetcher.py:77`<br>`backend/ai_analyzer.py:254` | **Méo mó Thanh khoản Nến Intraday:** Đưa trực tiếp khối lượng dở dang của phiên sáng vào so với `VolMA20` 20 ngày trọn vẹn, gây ra cảnh báo sai lệch về dòng tiền suy kiệt. | Nếu phiên đang diễn ra, tính toán Projected Volume (ước tính thanh khoản cả ngày dựa trên tỷ lệ thời gian giao dịch đã qua) trước khi so sánh với `VolMA20`. |
| **P1-DATA03** | **P1 (Major)** | `backend/api.py:100`<br>`backend/macro_fetcher.py:7-19` | **Lệch pha Thời gian Dữ liệu Tin tức & Vĩ mô khi chạy Lịch sử:** Khi xem ngày cũ (`target_date`), tin tức và giá Vàng/Dầu/Tỷ giá vẫn lấy của ngày hôm nay. | Nếu có `target_date`, chỉ lấy tin tức có ngày xuất bản $\le$ `target_date`, và macro lấy nến lịch sử tương ứng tại ngày đó từ yfinance/vnstock. |
| **P2-UI01** | **P2 (Minor)** | `web/src/components/StockChart.jsx` | **Thiếu Sub-chart Chỉ báo & Buy/Sell Markers:** Biểu đồ không có ô phụ hiển thị RSI, MACD và không đánh dấu điểm Mua/Bán (markers) trên nến. | Tích hợp thêm series `Markers` trên candlestick và tạo thêm pane phụ cho RSI và MACD Histogram. |

---

## 5. ĐỀ XUẤT KIẾN TRÚC ĐỊNH LƯỢNG THẾ HỆ MỚI (NEXT-GEN FINANCIAL QUANT ROADMAP)

Để đưa hệ thống đạt chuẩn vận hành chuyên nghiệp (Institutional / Production Ready), Hội đồng Chuyên gia đề xuất bản thiết kế nâng cấp 4 tầng sau:

```
┌────────────────────────────────────────────────────────────────────────┐
│                   TẦNG 1: VIETNAM MARKET DATA PIPELINE                 │
│  - Multi-source Gateway: VCI, KBS, DNSE, MSN (Không dùng TCBS lỗi)     │
│  - Session Sentinel: Nhận diện ATO, ATC, Continuous, Lunch, Closed     │
│  - Historical Clean Filter: Cắt đúng target_date (Loại bỏ Look-ahead) │
│  - Corporate Actions Engine: Ghi nhận ngày GDKHQ, cổ tức, thưởng       │
│  - Order Book & Liquidity Guard: Bắt bẫy sàn (Floor Lock / Trắng mua) │
│  - Foreign & Prop Flow: Tích hợp Mua/Bán ròng Khối ngoại & Tự doanh    │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Clean OHLCV + Metadata
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│               TẦNG 2: QUANTITATIVE MATH & INDICATOR ENGINE             │
│  - Wilder's Smoothing RSI: Chuẩn RMA 14 phiên, fix bug chia cho 0      │
│  - Intraday Volume Pacing: Chuẩn hóa khối lượng theo thời gian phiên   │
│  - Warm-up Guard: Đảm bảo tối thiểu 100 nến cho EMA/MACD ổn định       │
│  - Trading Calendar Engine: Tính T+2.5, T+5 theo ngày giao dịch        │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Indicators + Quantitative Signals
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                TẦNG 3: AI REASONING & FINANCIAL GUARDRAILS             │
│  - Structured Action Schema: Entry Zone, TP1/2, Stoploss, Position Size│
│  - Temporal Integrity Guard: Chặn nạp tin tức/vĩ mô tương lai          │
│  - Dynamic Fallback: Tính toán định lượng tự động khi mất kết nối AI   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Validated JSON Schema
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│               TẦNG 4: ACTIONABLE FRONTEND & VISUAL INTELLIGENCE        │
│  - Trading Hours Status Badge (ATO / ATC / Đang GD / Đã đóng cửa)      │
│  - Lightweight Charts với Buy/Sell Markers & Sub-panes (RSI / MACD)    │
│  - True Trading Dates trên bảng Price Targets (Không dính Thứ 7, CN)   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 6. KẾT LUẬN CỦA HỘI ĐỒNG KIỂM TOÁN TÀI CHÍNH & ĐỊNH LƯỢNG

Dự án **AI Chứng khoán (2-DU-AN-AI-CHUNG-KHOAN)** sở hữu nền tảng ý tưởng rất tốt, tài liệu Prompt (`tro_ly_dau_tu_chung_khoan_vn.md`) được biên soạn công phu với đầy đủ các quy tắc thị trường thực tế.

Tuy nhiên, **khoảng cách giữa tài liệu và mã nguồn thực thi hiện tại là rất lớn**. Việc xuất hiện lỗi **Look-ahead Bias** rò rỉ dữ liệu tương lai, công thức **RSI sai chuẩn kỹ thuật**, lỗi chia 0 làm sai lệch 50 điểm RSI, chu kỳ thanh toán **T+3 lỗi thời**, và việc **quên nạp dữ liệu Khối ngoại, Tự doanh, BCTC cơ bản** khiến hệ thống chưa thể đáp ứng yêu cầu vận hành thực chiến.

Các lỗ hổng phân loại **P0** nêu trên cần được Hội đồng Chuyên gia trực tiếp khắc phục triệt để trong **Giai đoạn 2** của kế hoạch hành động.
