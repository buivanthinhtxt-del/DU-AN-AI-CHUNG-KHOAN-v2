# HỆ THỐNG PROMPT & BỘ QUY TẮC THỰC CHIẾN T+2,5 — HỘI ĐỒNG ĐẦU TƯ AI (VERSION 5.0)
**Cấp độ:** Định chế Quản lý Quỹ × Thực chiến Đọc vị Tạo lập (CFA Dual-Funnel Verification & Tactical T+2,5 Institutional Edition)  
**Thị trường:** Cổ phiếu niêm yết Việt Nam (HOSE, HNX, UPCoM)  
**Phiên bản:** 5.0 — Hợp nhất Kiến trúc Phễu Kiểm Chứng 2 Tầng, Ma trận 6 Giả thuyết, Bộ 3 Chốt Chặn Thoát Lệnh và Đối Chiếu Dự Báo Cũ

---

## MỤC LỤC
1. [Đối chiếu & So sánh các Phương án Tư duy (Kiến trúc Phễu Kiểm Chứng 2 Tầng)](#1-đối-chiếu--so-sánh-các-phương-án-tư-duy-kiến-trúc-phễu-kiểm-chứng-2-tầng)
2. [Chi tiết Bộ Quy Tắc Thực Chiến Nâng Cấp Version 5.0](#2-chi-tiết-bộ-quy-tắc-thực-chiến-nâng-cấp-version-50)
3. [Cách Hệ thống Định lượng (`quant_engine.py` & `forecast_audit.py`) Tự động hóa Version 5.0](#3-cách-hệ-thống-định-lượng-quant_enginepy--forecast_auditpy-tự-động-hóa-version-50)
4. [Master System Prompt Hoàn chỉnh (Phần A, Phần B & Phần C)](#4-master-system-prompt-hoàn-chỉnh-phần-a-phần-b--phần-c)

---

## 1. ĐỐI CHIẾU & SO SÁNH CÁC PHƯƠNG ÁN TƯ DUY (KIẾN TRÚC PHỄU KIỂM CHỨNG 2 TẦNG)

Để đưa ra **lời khuyên đầu tư có giá trị kiếm tiền và giữ tiền thật** trên thị trường chứng khoán Việt Nam, chúng ta đặt lên bàn cân 3 phương án tư duy:

| Tiêu chí đối chiếu | Phương án 1: Thuần Học thuật Định chế (Pure FA/TA cổ điển) | Phương án 2: Thuần Lướt sóng Bảng điện (Pure Tape Reading T+) | Phương án 3 (VERSION 5.0 — TỐI ƯU NHẤT): Kiến trúc Phễu Kiểm Chứng 2 Tầng (CFA Standard × Thực chiến T+2,5) |
| :--- | :--- | :--- | :--- |
| **Cách tiếp cận** | Đánh giá mọi cổ phiếu bằng cùng một bộ tiêu chuẩn P/E, P/B, ROE, DCF và MA50/MA200. | Chỉ nhìn bảng điện, khớp lệnh trong phiên, bất chấp nội tại doanh nghiệp và định giá; dễ sa đà vào thuyết âm mưu. | **Hợp nhất 2 tầng kiểm chứng:**<br>- **Tầng 1 (Bộ lọc thực chiến):** Định danh bản chất cổ phiếu trên bàn cờ Tạo lập (5 nhóm) và đọc vị vi cấu trúc sổ lệnh.<br>- **Tầng 2 (Bộ lọc định chế CFA):** Đánh giá Ma trận 6 giả thuyết nguyên nhân, xác suất nền thống kê, bóc tách BCTC và bộ 3 chốt chặn. |
| **Điểm mù chí mạng** | - Ngây thơ trước các đòn tâm lý của Tạo lập.<br>- Dùng BCTC tĩnh để phân tích nhóm Đầu cơ Hệ sinh thái (VIX, GEX, EIB, VSC) là sai bản chất.<br>- Dễ bị lừa bởi chỉ số VN-Index "Xanh vỏ đỏ lòng" khi VIC/VHM kéo điểm Phái sinh.<br>- Hay khuyên "mua đuổi Breakout" buổi sáng dẫn đến kẹp T+2,5. | - Dễ bán non cổ phiếu Sản xuất nội tại thật (HPG, CTD) ngay chân sóng lớn.<br>- Không phân biệt được nhịp đè gom trước mùa BCTC quý với nhịp gãy xu hướng thật.<br>- Quy chụp mọi biến động cho "đội lái", thiếu kiểm chứng khách quan. | **Khắc phục hoàn toàn điểm mù của cả 2 phương án:**<br>- Giữ lại "Tạo lập" làm ngôi danh xưng chuyên môn chính thức dựa trên bằng chứng sổ lệnh (Bid Wall, Iceberg, ATC).<br>- Luôn bắt buộc đối chiếu 3 giả thuyết thay thế: Quỹ cơ cấu, luân chuyển ngành, định giá lại.<br>- Gắn 6 nhãn kiểm chứng chọn lọc (`[Nguồn]`, `[Tính toán]`, `[Suy luận]`, `[Giả định]`, `[Chưa xác định]`, `[Mâu thuẫn nguồn]`) ở các câu kết luận then chốt. |
| **Quản trị Thoát lệnh & Đi vốn** | Đặt 1 mức Target và 1 mức Stop-loss tĩnh cố định. | Cắt lỗ quá sát (<1×ATR) dễ bị cú "Rút ván rũ hàng (Spring)" quét mất hàng ngay trước giờ chạy. | - **Bộ 3 Chốt Chặn Thoát Lệnh (Exit Stops Triad):**<br>  1. `Price-Stop`: Đệm an toàn $\ge 1,5\times\text{ATR}$ và $\le 12\%$.<br>  2. `Thesis-Stop`: Thoát ngay khi luận điểm sai, không chờ giá.<br>  3. `Time-Stop`: Quá 10–15 phiên không chạy thì cơ cấu thu hồi vốn.<br>- **Chốt lời 3 nhịp:** 30% khóa lãi cơ bản + 50% Trailing Stop trượt 1,5%–2% + 20% ăn Gap FOMO sáng hôm sau. |
| **Cơ chế Tự hoàn thiện** | Không đối chiếu lại các dự báo quá khứ. | Nhớ nhớ quên quên, đổi lỗi cho thị trường. | **Hệ thống Đối Chiếu Dự Báo Cũ (Forecast Audit Engine):** Tự động chấm điểm 4 chiều (Hướng, Biên độ, Thời điểm, Điều kiện), AI tự nhìn nhận sai số khách quan và tự điều chỉnh kịch bản. |

👉 **KẾT LUẬN LỰA CHỌN:** **Version 5.0 (Kiến trúc Phễu Kiểm Chứng 2 Tầng)** là bước nhảy vọt toàn diện, dung hòa hoàn hảo giữa tính phản biện khoa học của Quỹ đầu tư định chế và tính thực chiến sát ván của thị trường Việt Nam.

---

## 2. CHI TIẾT BỘ QUY TẮC THỰC CHIẾN NÂNG CẤP VERSION 5.0

### PHẦN I: ĐỊNH DANH BẢN CHẤT CỔ PHIẾU (5 NHÓM BÀN CỜ TẠO LẬP) & 3 GIẢ THUYẾT THAY THẾ
Trước khi nhìn đồ thị kỹ thuật, hệ thống phân loại chính xác cổ phiếu phục vụ mục đích gì trên bàn cờ của Tạo lập:

| Phân nhóm | Đại diện điển hình | Bản chất vận động & Quy luật điều phối | Nguyên tắc giao dịch cốt lõi |
| :--- | :--- | :--- | :--- |
| **1. Nhóm Trụ điều tiết chỉ số (Cô đặc)** | `VIC`, `VHM`, `VRE`, `VNM`, `SAB`, `MSN`, `BVH`, `VJC` | Dùng lượng vốn nhỏ để kéo/đè điểm số VN-Index và VN30 phục vụ Phái sinh hoặc giữ nhịp thị trường. | Phân biệt rõ **"Tiết cung"** với **"Kéo xả"**. Khi đã có vị thế tốt, tuyệt đối không bán hết 1 lệnh mà phải dùng **Chặn lãi trượt (Trailing Stop 1,5%–2%)**. |
| **2. Nhóm Đầu cơ Hệ sinh thái (High-Beta)** | `VIX`, `GEX`, `VSC`, `EIB`, `NVL`, `DIG`, `PDR`, `SHS`, `VND` | Vận hành bằng kỹ thuật tài chính: sở hữu chéo, cầm cố cổ phiếu làm tài sản đảm bảo ngân hàng và kéo giá ngày chốt quý để hạch toán lãi tự doanh FVTPL. | **Bỏ qua BCTC tĩnh, chỉ đánh theo dòng tiền.** Biên độ cực lớn (trần/sàn nhanh). Chỉ mua sau khi rũ xong hàng T+ và **thoát dứt khoát khi cả hệ sinh thái bị bán ròng**. |
| **3. Nhóm Sản xuất cơ bản & Nội tại thật** | `HPG`, `CTD`, `FPT`, `DGC`, `MWG`, `PNJ`, `GMD`, `ACV`, `REE` | Có dòng tiền tổ chức và khối ngoại bảo kê tại vùng giá vốn. Đi lên theo bậc thang hoặc cô đặc theo đơn hàng thực tế, giữ giá rất khỏe khi thị trường chỉnh. | **Mua gom tại nền cạn cung (No Supply).** Không sợ các nhịp rũ bỏ thanh khoản thấp. Nhịp đè giá trước ngày công bố BCTC hợp nhất là cơ hội gom hàng của tổ chức. |
| **4. Nhóm Ngân hàng (Vua thanh khoản)** | `TCB`, `MBB`, `VCB`, `BID`, `CTG`, `ACB`, `VPB`, `STB`, `HDB` | Nhạy cảm với điểm số VN30, tỷ giá, biên lãi ròng (NIM) và đặc biệt là các sự kiện chia tách tăng vốn / GDKHQ. | Soi kỹ dòng tiền mua/bán ròng tổ chức và **tường lệnh đỡ ở bước giá dưới** trước khi giải ngân. Áp dụng triệt để **"Né trước chốt – Bắt sau chia"**. |
| **5. Nhóm Phòng thủ Địa chính trị** | `OIL`, `PVD`, `PVS`, `PVT`, `GAS`, `PLX`, `BSR`, `DPM`, `DCM` | Hút dòng tiền trú ẩn ngắn hạn khi thị trường chung đỏ lửa hoặc căng thẳng địa chính trị leo thang. | Sóng ngắn, hay tạo **nến cụt đầu (râu trên dài)** khi kéo buổi sáng. **Tuyệt đối không mua đuổi khi đã kéo xanh.** |

*Yêu cầu bắt buộc:* Khi phân tích động thái của Tạo lập, phải luôn đối chiếu với **3 Giả thuyết Thay thế Không-Thao-túng**:
1. *Quỹ tái cơ cấu danh mục (Fund Rebalancing):* Các quỹ ETF ngoại (VNM ETF, FTSE ETF) hoặc quỹ nội (DCVFM Diamond, VNFinLead) cơ cấu định kỳ hoặc chốt NAV cuối quý.
2. *Luân chuyển dòng tiền ngành tự nhiên (Sector Rotation):* Phản ứng tự nhiên của dòng tiền trước biến động vĩ mô (tỷ giá, lãi suất liên ngân hàng, giá hàng hóa).
3. *Tái định giá theo nội tại (Fundamental Re-rating):* Thị trường điều chỉnh định giá trước hoặc sau kỳ công bố KQKD có kết quả đột biến.

---

### PHẦN II: KỸ THUẬT TAPE READING, MA TRẬN 6 GIẢ THUYẾT & PHÂN TÍCH PHIÊN ATC
1. **Nhận diện bẫy "Xanh vỏ đỏ lòng" và "Neo giá xả ngầm" (Churning Trap):**
   - *Biểu hiện:* VN-Index kéo xanh nhờ trụ lớn cô đặc, nhưng phần lớn danh mục cơ bản bị đè đỏ dưới tham chiếu.
   - *Bẫy thanh khoản tại cổ phiếu đầu cơ:* Giữ giá xanh nhẹ hoặc tham chiếu với khối lượng khớp lệnh nổ vọt kỷ lục ($>1,5\times \text{TB20}$) mà giá không bứt lên nổi, đồng thời lệnh lớn bán ròng cả cụm hệ sinh thái → Hành vi **neo giá dụ cầu FOMO để tay to thoát hàng**.
2. **Giải mã Chu kỳ Khối ngoại theo "Bất đối xứng khối lượng":**
   - Thống kê chuỗi 10–20 phiên liên tiếp để tính vùng giá vốn và tổng lượng tồn kho của Khối ngoại.
   - *Quy tắc "Bất đối xứng khối lượng":* Sau các phiên mua ròng quy mô đột biến, nhịp điều chỉnh chỉ kết thúc khi lượng bán của khối ngoại thu hẹp dần về mức cân bằng và **đảo chiều sang mua ròng dương trở lại** → Điểm xác nhận đáy ngắn hạn có độ tin cậy cao nhất.
3. **Độ sâu thị trường (Order Book), Cú rũ bỏ Spring & Phân tích ATC:**
   - *Tường đỡ tổ chức (Bid Wall):* Cổ phiếu chỉnh đỏ nhưng bên Mua xuất hiện cục lệnh chặn đỡ gấp đôi bên Bán ngay tại hỗ trợ → Tay to há miệng gom hàng cắt lỗ của nhỏ lẻ.
   - *Phân biệt Gãy thật vs. Rũ giả (Spring):* Rũ giả có biên độ lệch nền chỉ **1%–2,5%**, không phá vỡ đáy cây nến gom hàng lớn nhất của tổ chức và được kéo lấy lại nền ngay trong 1–2 phiên kế tiếp kèm thanh khoản tăng vọt.
   - *Chỉ số Close Location Value ($CLV = \frac{Close - Low}{High - Low}$):* Đo lường vị thế nến đóng cửa phiên ATC. $CLV \ge 0,7$ xác nhận lực kéo dứt khoát; $CLV \le 0,3$ cảnh báo nến cụt đầu bị đè đạp ATC. Lưu ý tuần đáo hạn phái sinh VN30F.
4. **Ma trận 6 Giả thuyết Biến động Giá (`causal_hypotheses`):**
   - **H1 (Gom hàng/Hấp thụ):** Tạo lập gom ngầm vùng hỗ trợ, cạn cung No Supply.
   - **H2 (Phân phối/Xả ngầm):** Kéo trụ xả midcap, Upthrust, râu nến trên dài.
   - **H3 (Quỹ tái cơ cấu):** ETF rebalancing, khớp lệnh đột biến ATC thứ 6.
   - **H4 (Luân chuyển ngành):** Dòng tiền xoay vòng tự nhiên giữa các nhóm ngành.
   - **H5 (Tái định giá căn bản):** KQKD quý vượt kỳ vọng, lợi nhuận ròng tăng trưởng > 20%.
   - **H6 (Bán tháo kỹ thuật/Call margin):** Giải chấp chéo, lệnh bán MP sàn áp đảo.

---

### PHẦN III: QUY LUẬT T+2,5 & 3 KHUNG GIỜ TÁC CHIẾN CHUẨN TRONG NGÀY
Dành riêng cho nhà đầu tư bận rộn ngoài công trường không thể canh bảng điện từng phút:
- **Khung `09h00 – 10h00` (Khung giờ Bẫy hưng phấn / Mở Gap sáng):** Tạo lập mượn đà tăng chiều hôm trước để mở Gap Up đầu phiên với thanh khoản thấp. **Tuyệt đối không mua đuổi giá xanh đầu phiên** để tránh kẹp T+ khi thị trường quay đầu lấp Gap giữa trưa.
- **Khung `11h00 – 11h30` (Khung giờ Biến động trưa / Kiểm định lực cầu sáng):** Kiểm tra độ bền của dòng tiền sáng. Cổ phiếu yếu bắt đầu đuối sức và chịu áp lực xả trước giờ nghỉ trưa. Đánh giá tỷ lệ giữ giá để nhận diện mã khỏe.
- **Khung `13h45 – 14h30 / ATC` (Khung giờ Phán quyết & Chốt chặn ATC):** Sau `13h00`, hàng nổ vol T+2,5 chính thức về tài khoản. Đến `13h45`, thị trường đã hấp thụ xong toàn bộ áp lực bán chốt lời/cắt lỗ. **Mọi lệnh Mua mở vị thế hoặc Bán thoát lệnh đều được quyết định trong khung giờ này** dựa trên hình thái nến đóng cửa ngày và ý chí cân lệnh ATC.

---

### PHẦN IV: BỘ LỌC SỰ KIỆN DOANH NGHIỆP & VĨ MÔ (TRÁNH BẪY CHÔN VỐN)
- **Quy tắc 1:** Kiểm tra ký hiệu Sự kiện Quyền (`•`) trước mọi lệnh mua.
- **Quy tắc 2:** Tuyệt đối không mua trong 2 phiên (`T-1`, `T-2`) trước ngày GDKHQ chia cổ tức bằng cổ phiếu / phát hành thêm (tránh bị ép "lăn chốt", giam cứng 1/3–1/2 vốn lưu động trong 2–3 tháng và chịu thiệt 5% thuế TNCN).
- **Quy tắc 3 (Chiến thuật "Né trước chốt – Bắt sau chia"):** Đứng ngoài trong 2 ngày cuối trước chốt quyền (khi dân T+ xả rát né cổ tức), chờ qua ngày GDKHQ khi giá đã điều chỉnh kỹ thuật về mức thấp và sạch áp lực bán mới giải ngân mua 100% cổ phiếu tươi.
- **Quy tắc 4 (Đón điểm rơi BCTC Quý):** Ở các cổ phiếu sản xuất đầu ngành tăng trưởng thật (`HPG`, `CTD`...), nhịp đè giá ngay trước ngày công bố BCTC hợp nhất là cơ hội gom hàng của tổ chức.

---

### PHẦN V: KỶ LUẬT QUẢN TRỊ VỊ THẾ, BỘ 3 CHỐT CHẶN THOÁT LỆNH & CHỐT LỜI 3 NHỊP
1. **Nguyên tắc Dịch chuyển Kịch bản linh hoạt:** Khi thanh khoản thị trường thấp (<15.000 tỷ/phiên), áp lực Margin không lớn, thị trường chỉnh kiểu "Cưa chân bàn" hoặc "Đi ngang hấp thụ". Ngay khi cổ phiếu giữ vững nền hỗ trợ qua 3–4 phiên thử lửa, lập tức nâng điểm mua lên **"Mua gom tại nền tích lũy" tối thiểu 30%–40% vốn** để có sẵn lợi thế T+.
2. **Bộ 3 Chốt Chặn Thoát Lệnh (Exit Stops Triad):**
   - **`Price-Stop` (Chốt chặn Giá):** Mức giá cắt lỗ kỹ thuật. Phải đảm bảo **khoảng cách $\ge 1,5\times\text{ATR}(14)$** và mức lỗ $\le 12\%$ NAV để chống bẫy rung lắc T+2,5.
   - **`Thesis-Stop` (Chốt chặn Luận điểm):** Điều kiện mà nếu xảy ra, luận điểm đầu tư ban đầu bị bác bỏ hoàn toàn. **Thoát lệnh ngay lập tức khi Thesis-Stop kích hoạt mà KHÔNG cần đợi giá chạm Price-Stop**.
   - **`Time-Stop` (Chốt chặn Thời gian):** Giới hạn tối đa 10–15 phiên giao dịch. Nếu sau thời gian này giá vẫn không bứt phá khỏi vùng nền, chủ động hạ 50% tỷ trọng để giải phóng vốn.
3. **Công thức Chốt lời 3 Nhịp & Chặn lãi trượt (Trailing Stop):**
   - **Nhịp 1 (Khóa lợi nhuận cơ bản – Bán 30%):** Chạm kháng cự kỹ thuật đầu tiên hoặc đạt lãi kỳ vọng **+5% đến +7%** (cơ bản) / **+10% đến +12%** (đầu cơ).
   - **Nhịp 2 (Cưỡi sóng bằng Lệnh điều kiện – Giữ 50%):** Cài đặt **Stop Order / Trailing Stop trượt lùi 1,5% – 2,0%** tính từ mức giá đỉnh cao nhất đạt được trong phiên.
   - **Nhịp 3 (Ăn trọn quán tính FOMO – Giữ 20% cuối cùng):** Nếu đóng nến xanh đặc gần đỉnh ngày hoặc dư mua trần, giữ 20% qua đêm để bán vào nhịp mở Gap hưng phấn lúc **`09h15 – 09h30` sáng hôm sau**.

---

### PHẦN VI: BẢNG CHECKLIST 5 PHÚT & BỘ 3 CÂU HỎI TỰ KIỂM TRA (SELF-REFLECTION)
#### Bảng Checklist 5 Phút Trước Khi Bấm Lệnh:
1. `[ ]` **1. Kiểm tra Sự kiện Quyền:** Mã này có dấu chấm cảnh báo sự kiện (`•`) hay lịch chốt cổ tức/phát hành thêm trong 3 ngày tới không? *(Nếu có chia cổ phiếu → Dừng mua ngay).*
2. `[ ]` **2. Kiểm tra Thời gian & Giá mua:** Đã qua `13h45` chiều chưa hay đang là nhịp kéo xanh mở Gap trước `10h00` sáng? Giá định mua đang nằm sát nền hỗ trợ hay đã kéo xa?
3. `[ ]` **3. Kiểm tra Dòng tiền Tổ chức/Khối ngoại:** Mã này (và hệ sinh thái của nó) đang được gom ròng hay nằm trong Top bán ròng ẩn? Khối ngoại đã ngưng xả chưa?
4. `[ ]` **4. Kiểm tra Chu kỳ T+2,5:** Chiều nay hoặc chiều mai có phải là ngày hàng của một cây nến nổ thanh khoản kỷ lục về tài khoản không? *(Nếu mai hàng lớn về → Chờ qua 13h45 ngày mai mới nhặt).*
5. `[ ]` **5. Thiết lập Chốt chặn tự động:** Sau khi khớp lệnh xong, đã cài sẵn Chuông cảnh báo giá (Price Alert) và Lệnh điều kiện cắt lỗ/chặn lãi (Stop Order) trên app để yên tâm đóng điện thoại làm việc chưa?

#### Bộ 3 Câu Hỏi Tự Kiểm Tra (Self-Reflection) Trước Khi Phê Duyệt:
1. `[ ]` **Kiểm tra Thiên kiến & Giả định ngầm:** Luận điểm này có đang phụ thuộc vào một giả định chưa được kiểm chứng không?
2. `[ ]` **Kiểm tra Kế hoạch Thoát hiểm & Thesis-Stop:** Nếu thị trường chung sập hoặc Thesis-Stop bị kích hoạt, kế hoạch thoát hiểm và mức lỗ tối đa đã sẵn sàng chưa?
3. `[ ]` **Kiểm tra Kỷ luật Khung giờ & Bẫy T+2,5:** Lệnh có tuân thủ đúng khung giờ sau 13h45 và tránh được ngày hàng nổ vol về tài khoản chưa?

---

### PHẦN VII: CƠ CHẾ ĐỐI CHIẾU DỰ BÁO CŨ (FORECAST AUDIT ENGINE)
Hệ thống lưu trữ lịch sử dự báo tại `backend/cache/forecast_audit/{symbol}.json`. Khi phân tích lại một mã đã có dữ liệu dự báo, hệ thống tự động chấm điểm theo 4 chiều:
1. **Hướng (Direction):** Đúng / Sai hướng kỳ vọng (UP/DOWN).
2. **Biên độ (Amplitude):** Tỷ lệ đạt được mục tiêu Target 1 (0.0 đến 1.0).
3. **Thời điểm (Timing):** Đạt trong khung thời gian T+ (T+2.5, T+5, T+10).
4. **Điều kiện (Condition):** Luận điểm bảo toàn hay vi phạm ngưỡng cắt lỗ Stop-loss.

AI tiếp nhận kết quả đối chiếu qua biến `{forecast_audit}` và có trách nhiệm tự nhìn nhận sai số, tự sửa sai và giải trình nguyên nhân khách quan, không dùng lời nói cũ của mình làm chân lý.

---

## 3. CÁCH HỆ THỐNG ĐỊNH LƯỢNG (`quant_engine.py` & `forecast_audit.py`) TỰ ĐỘNG HÓA VERSION 5.0

Hệ thống mã nguồn tự động tính toán các trường dữ liệu và bơm thẳng vào Prompt cho AI:
- `archetype`: Tự động định danh mã cổ phiếu vào đúng 1 trong 5 nhóm của Tạo lập.
- `SECTOR_FORENSIC_GUIDE` & `ENTITY_DISAMBIGUATION`: Cung cấp cẩm nang điều tra đặc thù theo mã/ngành và luật phân biệt thực thể (tránh nhầm OIL với dầu thế giới, VIX với chỉ số CBOE Mỹ).
- `_analyze_atc()`: Tính toán chỉ số CLV, nhận diện kéo dứt khoát, đè đạp ATC, rút chân mạnh, và cảnh báo tuần đáo hạn phái sinh VN30F.
- `exit_stops`: Tự động tính toán bộ 3 chốt chặn `price_stop` ($\ge 1,5\times\text{ATR}$ và $\le 12\%$), `thesis_stop`, `time_stop`.
- `causal_hypotheses`: Đánh giá ma trận 6 giả thuyết nguyên nhân với xác suất chuẩn hóa $\sum prob = 1,0$.
- `market_layers`: Xây dựng 4 lớp thị trường Top-down (Vĩ mô/Lãi suất $\to$ VN-Index/VN30 $\to$ Ngành/Dòng tiền $\to$ Cổ phiếu).
- `audit_historical_forecast()`: Tự động nạp, đối chiếu và chấm điểm các bản ghi dự báo lịch sử.

---

## 4. MASTER SYSTEM PROMPT HOÀN CHỈNH (PHẦN A, PHẦN B & PHẦN C)

*(Đã được đồng bộ trực tiếp vào [`backend/prompts/tro_ly_dau_tu_chung_khoan_vn.md`](file:///d:/2-%20L%C3%80M%20VI%E1%BB%86C/2-%20github%20du%20an%201/2-DU-AN-AI-CHUNG-KHOAN/backend/prompts/tro_ly_dau_tu_chung_khoan_vn.md) để `ai_analyzer.py` sử dụng ngay khi phân tích trên web).*
