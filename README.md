# 📈 Antigravity WallStreet AI (`2-DU-AN-AI-CHUNG-KHOAN`)

Hệ thống phân tích chứng khoán Việt Nam chuyên sâu và dự báo thông minh sử dụng AI (Google Gemini), kết hợp dữ liệu lịch sử giá (`vnstock`), kinh tế vĩ mô quốc tế (`yfinance`) và tin tức tài chính thời gian thực.

---

## 1. Tổng quan Kiến trúc Hiện tại

### 🖥️ Backend (Python / FastAPI - Cổng `8000`)
* **`api.py`**: Cung cấp 2 endpoint phân tích chính là `POST /api/market_data` (tải lịch sử giá, vĩ mô, cùng ngành, tin tức) và `POST /api/ai_report` (gửi dữ liệu sang Gemini phân tích), cùng cụm CRUD `/api/watchlist`.
* **`data_fetcher.py`**: Dùng thư viện `vnstock` (nguồn `VCI`) để lấy lịch sử giá OHLCV 365 ngày và so sánh hiệu suất 3 mã cùng ngành (`SECTOR_MAP` đang gán cứng cho 9 nhóm ngành).
* **`macro_fetcher.py`**: Dùng `yfinance` lấy giá Vàng (`GC=F`), Dầu Brent (`BZ=F`), và tỷ giá `USDVND=X`.
* **`news_fetcher.py`**: Quét RSS từ CafeF và VnExpress bằng `xml.etree.ElementTree`.
* **`ai_analyzer.py`** (v3 – 08/11/2026): Dựng hồ sơ dữ liệu thật → gọi Gemini với prompt "Hội đồng đầu tư" (`prompts/tro_ly_dau_tu_chung_khoan_vn.md` v2.0) và JSON schema mở rộng (`verdict`, `thesis`, `trade_plan`, `scenarios`, `risks`, `monitoring`…) → hậu kiểm nhất quán (cắt lỗ ≥ 1,5×ATR và ≤ 12%, R:R tính lại từ số, xác suất kịch bản = 100, dự báo trong dải 95%, độ tin cậy ≤ trần chất lượng dữ liệu, phủ quyết "Mua" khi R:R < 1,5 hoặc cổ phiếu ở giai đoạn 4). Không gọi được AI → báo cáo định lượng đầy đủ thay vì bản sơ sài.
* **`quant_engine.py`**: Tính xác định giai đoạn xu hướng (Weinstein), sức mạnh tương đối & beta so với VN-Index, xếp hạng trong ngành, dòng tiền tích lũy/phân phối, vùng hỗ trợ/kháng cự có cơ sở (pivot + MA + volume profile), xác suất nền lịch sử, dải giá thống kê 68%/95%, kế hoạch giao dịch cơ sở có tỷ trọng theo rủi ro % NAV, "thời tiết" thị trường (ngày phân phối).
* **`fundamental_fetcher.py`**: Bảng giá phiên gần nhất (khối ngoại mua/bán ròng thật, room ngoại, trần/sàn, cờ trắng bên mua), hồ sơ công ty (vốn hóa), BCTC qua vnstock (best-effort) và tra cứu web có trích dẫn nguồn (Gemini + Google Search).
* **`data_sources.py`** (nguồn dữ liệu giá đa nhà cung cấp): chuỗi `ssi → vnstock → local` (đổi bằng `DATA_SOURCES`).
  * **SSI FastConnect Data** — API chính thức, miễn phí cho chủ tài khoản SSI; điền `SSI_CONSUMER_ID`/`SSI_CONSUMER_SECRET` (lấy trên iBoard → Dịch vụ API). Cho cả OHLCV cổ phiếu/chỉ số và **khối ngoại nhiều phiên**.
  * **vnstock** — các lớp đang dùng (`Quote`, `Company`, `Finance`, `Trading`) thuộc "thế hệ 4", vnstock thông báo ngừng từ **10/11/2026**; có cầu dao tự ngắt 30 phút sau 3 lỗi liên tiếp, hoặc tắt hẳn bằng `DISABLE_VNSTOCK=1`.
  * **Kho cục bộ** `backend/data/ohlcv/<MÃ>.csv` — mọi lần tải thành công được tự lưu; khi các nguồn trực tuyến hỏng, hệ thống dùng kho này và **cảnh báo số phiên bị cũ** (giao diện + giảm điểm chất lượng dữ liệu). Có thể tự thả file CSV `Date,Open,High,Low,Close,Volume` (giá nghìn đồng).
  * Tải trước kho: `.venv/Scripts/python.exe backend/tools/backfill_local_store.py --years 5 --skip-existing` · Kiểm tra nguồn: `backend/tools/check_data_sources.py HPG` hoặc `GET /api/data_sources/health?symbol=HPG`.
* **`llm_client.py`**: Failover nhiều model Gemini — 429/quá tải/404 → chuyển model kế tiếp (chỉ dừng khi khóa API sai); đổi danh sách model bằng biến môi trường `GEMINI_MODELS="m1,m2"`.
* **`cache_manager.py` & `database.py`**: Lưu cache ra file JSON trong `.cache/` (giảm tải request lặp lại) và lưu danh sách theo dõi (Watchlist) vào SQLite (`antigravity.db`).
* **`main.py`**: Bản chạy giao diện dòng lệnh (CLI) cũ.

### 🌐 Frontend (React 19 + Vite 8 - Cổng `5173`)
* **`web/src/App.jsx` & `web/src/App.css`**: Giao diện Dashboard 1 trang với Sidebar Watchlist, thanh chỉ số vĩ mô, biểu đồ nến (`lightweight-charts` v5) nối liền vùng dự báo (`AreaSeries`), biểu đồ Radar 5 chiều (SVG), bảng mục tiêu giá và báo cáo phân tích hiệu ứng gõ chữ (typewriter).

---

## 2. Báo cáo Hiện trạng: Các Vấn đề & Điểm nghẽn Cần Fix

### A. Nhóm AI & Gemini SDK (Ưu tiên số 1)
1. **Thư viện và Model đã cũ, gây lỗi Quota (`429`)**:
   * Dự án đang dùng package `google-generativeai` cũ (cần chuyển sang SDK chuẩn mới `google-genai`).
   * Trong `analyze_stock_data`, mỗi lần phân tích lại gọi `genai.list_models()` làm tốn thêm 1 vòng request mạng, và danh sách ưu tiên đang chọn `gemini-1.5-pro` đầu tiên — model này có giới hạn miễn phí (RPM) rất thấp nên thường xuyên văng lỗi `429 Quota Exceeded` (như ghi nhận trong `debug_output.txt`).
2. **Xử lý JSON từ AI còn thủ công và xung đột trong Prompt**:
   * Chưa bật **Structured Outputs** (`response_mime_type="application/json"` kèm `response_schema`), mà đang cắt chuỗi thủ công bằng `find('{')` và `rfind('}')`.
   * Trong `ai_analyzer.py`, phần hướng dẫn yêu cầu dự báo 4 mốc (`days_future`: `0, 0, 1, 5` cho Sáng, Chiều, Ngày mai, Tuần tới), nhưng mẫu JSON bên dưới lại ghi `T+3` và `T+7`. Khi AI trả về hai mốc có cùng `days_future: 0`, biểu đồ `lightweight-charts` ở Frontend phải tự cộng lùi ngày giả định (`+1 ngày`), làm lệch ngày thực tế trên đồ thị.

### B. Nhóm Dữ liệu Thị trường, Vĩ mô & Tin tức
1. **Dữ liệu Vĩ mô & VN-Index thiếu hụt**:
   * Trong `get_macro_data`, trường `VNINDEX_PROXY` được khởi tạo là `"N/A"` nhưng chưa có code lấy điểm số VN-Index thực tế.
   * Các lệnh gọi `yfinance` (Vàng, Dầu, Tỷ giá) chạy tuần tự trên luồng chính trong `fetch_market_data` thay vì đưa vào `ThreadPoolExecutor`, gây chậm lần tải đầu tiên.
2. **So sánh cùng ngành (`Peers`) chậm và thiếu linh hoạt**:
   * `get_peers_performance` gọi `vnstock` tuần tự cho từng mã cùng ngành. Những mã ngoài danh sách cứng `SECTOR_MAP` (như VNM, SAB, CTD, GVR...) chưa có dữ liệu so sánh ngành.
3. **Bộ lọc Tin tức RSS quá hẹp**:
   * `get_latest_news` chỉ duyệt đúng 5 tin đầu tiên trên trang chủ RSS chung rồi mới kiểm tra tên mã cổ phiếu (`if count >= 5: break` đặt ngoài điều kiện khớp mã). Do đó hầu như không bắt được tin riêng của doanh nghiệp, và phần `description` của RSS thường dính thẻ HTML (`<a>`, `<img>`).
4. **Tính toán kỹ thuật (TA) chưa xuất ra API**:
   * `calculate_indicators` chỉ được gọi nội bộ trong `ai_analyzer.py` mà không trả ra ở `/api/market_data`, nên Frontend chưa vẽ được các đường `EMA10`, `SMA20`, `RSI`, `MACD` hay cột `Volume` lên biểu đồ.

### C. Nhóm Frontend & Trải nghiệm người dùng (UI/UX)
1. **Monolithic Component & Hardcoded URL**:
   * Toàn bộ logic, state, biểu đồ và bộ đọc Markdown đều nằm chung trong 1 file `App.jsx` dài gần 600 dòng.
   * Địa chỉ API đang gắn cứng `http://127.0.0.1:8000` ở 4 nơi khác nhau.
   * Nhãn ô chọn ngày đang ghi là `"Start Date"` nhưng thực chất ở Backend biến `target_date` hoạt động như **ngày kết thúc (End Date / Ngày chốt dữ liệu quá khứ)** để phục vụ Backtest.
2. **Hiệu ứng Typewriter & Render Markdown**:
   * Bộ gõ chữ `setInterval(..., 8)` gọi `setTypedAnalysis` liên tục mỗi 8ms cho bài viết dài hàng nghìn ký tự, khiến React phải chạy lại hàm `formatReport` hàng trăm lần mỗi giây.

### D. Cấu trúc Thư mục & Vệ sinh Dự án (Housekeeping)
* **File rác / File test rải rác ở thư mục gốc**: Có 6 file test rời rạc (`diagnose_api.py`, `test_api.py`, `test_api_urllib.py`, `test_error.py`, `test_gemini.py`, `test_macro.py`, `test_vnstock.py`) — trong đó một số file vẫn gọi endpoint cũ `/api/analyze` (không còn tồn tại) — cùng với `debug_output.txt` và `package-lock.json` thừa ở thư mục gốc.
* **Bảo mật & Cấu hình**: Vẫn còn file `api key.ini` nằm trong thư mục làm việc (dù đã đưa vào `.gitignore`), và `.env.example` vẫn còn biến thừa từ dự án khác (`ROBOFLOW_API_KEY`, `MODEL_ID=helmet-eogse/2`).

---

## 3. Kế hoạch Quy hoạch & Cải tiến (Lộ trình Triển khai)

Dự án đã được chốt phương án quy hoạch tổng thể theo 4 hạng mục lớn sau:

### 🗂️ Hạng mục 1: Quy hoạch lại Cấu trúc Thư mục (Tách `backend/` và `web/`) — ✅ ĐÃ HOÀN THÀNH
* [x] Tách toàn bộ mã nguồn Python vào thư mục `backend/`, tài liệu Prompt vào `backend/prompts/`, và gom các kịch bản kiểm thử vào `backend/tests/`.
* [x] Dọn dẹp triệt để các file rác và dữ liệu dự án Helmet (`api key.ini`, biến `ROBOFLOW_API_KEY`, `MODEL_ID=helmet-eogse/2`, `debug_output.txt`, `package-lock.json` thừa, thư mục tạm `.claude/worktrees`).
* [x] Chuẩn hóa lại `.env.example`, `.env`, `.gitignore` và cập nhật `start.bat` để khởi chạy đồng bộ từ cấu trúc `backend/` + `web/`.

```text
2-DU-AN-AI-CHUNG-KHOAN/
├── backend/                  # Toàn bộ mã nguồn Backend (FastAPI + AI + Data)
│   ├── api.py
│   ├── ai_analyzer.py
│   ├── data_fetcher.py
│   ├── macro_fetcher.py
│   ├── news_fetcher.py
│   ├── cache_manager.py
│   ├── database.py
│   ├── main.py
│   ├── requirements.txt
│   ├── prompts/              # Tài liệu chuẩn hóa System Prompt chứng khoán VN
│   └── tests/                # Các kịch bản kiểm thử được quy hoạch gọn gàng
├── web/                      # Mã nguồn Frontend (React + Vite)
│   ├── src/
│   │   ├── App.jsx
│   │   └── App.css
│   └── package.json
├── .env.example
├── .gitignore
├── start.bat
└── README.md
```

### 🤖 Hạng mục 2: Nâng cấp Lõi AI (`ai_analyzer.py`)
* [ ] Chuyển đổi từ `google-generativeai` sang SDK chính thức mới **`google-genai`** (`>= 2.30.1`, Interactions API `client.interactions.create`).
* [ ] Sử dụng dòng model thế hệ mới (**`gemini-3.8-flash`** làm mặc định tốc độ cao, hạn mức rộng; hỗ trợ fallback sang `gemini-3.5-flash-lite` / `gemini-4-argon`) và bỏ lệnh gọi `list_models()` dư thừa ở mỗi request.
* [ ] Áp dụng **Structured Outputs (`response_format` với Pydantic `model_json_schema()`)** để ép Gemini trả về đúng cấu trúc JSON 100%, loại bỏ hoàn toàn lỗi parse JSON.
* [ ] Đồng bộ lại hệ thống mốc thời gian dự báo (`T+1`, `T+3`, `T+5`, `T+10`) giữa Prompt và biểu đồ.

### 📊 Hạng mục 3: Cải tiến Nguồn Dữ liệu (`data_fetcher`, `macro_fetcher`, `news_fetcher`)
* [ ] **Vĩ mô & VN-Index**: Bổ sung dữ liệu điểm số và biến động của `VN-Index` thực tế; chạy song song toàn bộ tác vụ lấy dữ liệu vĩ mô.
* [ ] **So sánh Ngành (`Peers`)**: Mở rộng danh mục ngành (`SECTOR_MAP`) và tải song song dữ liệu các mã cùng ngành bằng `ThreadPoolExecutor` để giảm thời gian chờ.
* [ ] **Tin tức (`News`)**: Sửa lỗi vòng lặp giới hạn 5 tin trong `news_fetcher.py`, làm sạch thẻ HTML trong tóm tắt RSS và bổ sung nguồn tin theo mã cổ phiếu.
* [ ] **Chỉ báo Kỹ thuật (`TA`)**: Đưa kết quả tính toán `EMA10`, `SMA20`, `RSI`, `MACD`, `Volume` vào trực tiếp response của `/api/market_data`.

### 💻 Hạng mục 4: Nâng cấp Giao diện Web (`web/`)
* [ ] **Tái cấu trúc Component**: Tách `App.jsx` thành các component độc lập (`Sidebar`, `MacroTicker`, `StockChart`, `RadarScoreCard`, `PriceTargets`, `PeersComparison`, `AnalysisReport`).
* [ ] **Biểu đồ Chuyên sâu**: Vẽ thêm cột khối lượng (`Volume` histogram) và đường trung bình động (`EMA10`, `SMA20`) lên biểu đồ `lightweight-charts`.
* [ ] **Bảng So sánh Ngành (Peers)**: Hiển thị trực quan dữ liệu các cổ phiếu cùng ngành trên Dashboard (hiện Backend đã trả về nhưng Frontend chưa hiển thị).
* [ ] **Tối ưu UX**: Đổi nhãn `"Start Date"` thành `"Ngày chốt dữ liệu (Backtest)"`, tối ưu hóa hiệu ứng gõ chữ (typewriter) để không gây giật lag khi render bảng biểu Markdown.

---

## 4. Hướng dẫn Khởi chạy Hiện tại

1. **Cấu hình biến môi trường**:
   * Sao chép `.env.example` thành `.env` và điền khóa `GEMINI_API_KEY` của bạn.
2. **Chạy tự động (Windows)**:
   * Nháy đúp hoặc chạy file `start.bat` để mở đồng thời Backend (`http://localhost:8000`) và Frontend (`http://localhost:5173`).

