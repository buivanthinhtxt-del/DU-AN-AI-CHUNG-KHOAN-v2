---
title: AI Workstation Phân Tích Chứng Khoán
emoji: 📈
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
---

# 📈 AI Workstation Phân Tích Chứng Khoán Việt Nam

Hệ thống phân tích chứng khoán chuyên sâu và dự báo thông minh thế hệ mới kết hợp **Mô hình Định lượng Độc lập (Quant Engine)**, **Lý thuyết Chu kỳ Xu hướng Weinstein**, dữ liệu thị trường tài chính đa tầng và **Trí tuệ Nhân tạo Google Gemini** đóng vai trò Hội đồng Đầu tư Phản biện.

Ứng dụng được đóng gói toàn diện dạng **All-in-One Docker Container**, tích hợp đồng thời Giao diện người dùng **React 19** và Máy chủ API **FastAPI** trong cùng một container duy nhất, sẵn sàng triển khai đám mây 24/7 hoàn toàn miễn phí trên **Render.com** và **Hugging Face Spaces**.

---

## 🌟 Tính Năng Nổi Bật

- **Đóng gói All-in-One Siêu Nhẹ**: Phục vụ Frontend React (biên dịch qua Vite) và Backend FastAPI trên cùng một cổng dịch vụ (mặc định `7860` hoặc nhận động qua `$PORT`). Loại bỏ hoàn toàn lỗi CORS liên miền.
- **Công cụ Định lượng 6 Bước (Quant Engine)**:
  - Phân loại 4 giai đoạn xu hướng theo phương pháp Stan Weinstein (Tích lũy, Tăng giá, Phân phối, Giảm giá).
  - Đánh giá sức mạnh giá tương đối (RS) và Beta so với VN-Index.
  - Phân tích dòng tiền tích lũy / phân phối qua Volume Profile, MFI, OBV, Chaikin Money Flow.
  - Nhận diện ngưỡng hỗ trợ / kháng cự động kết hợp Fibonacci Pivot Points.
  - Dải giá xác suất thống kê 68% (1-sigma) và 95% (2-sigma).
  - Kế hoạch giao dịch cơ sở với tỷ trọng đề xuất quản trị rủi ro theo % NAV.
- **Hội đồng Phản biện Đầu tư AI (Google Gemini)**:
  - Tự động kích hoạt cơ chế failover đa model (`gemini-2.5-flash`, `gemini-1.5-flash`...).
  - Hậu kiểm nhất quán nghiêm ngặt: Tỷ lệ R:R ≥ 1.5, mức cắt lỗ dựa trên 1.5×ATR, kiểm tra trần chất lượng dữ liệu.
  - Chế độ phân tích định lượng dự phòng (Fallback) khi không có kết nối internet hoặc hết quota AI.
- **Chuỗi Nguồn Dữ Liệu Giá Dự Phòng Đa Tầng (Zero-Dependency)**:
  - `ssi`: API FastConnect chính thức của SSI.
  - `public`: Xoay vòng cầu dao tự động qua các API bảng giá web công khai (DNSE, VNDirect, Vietcap, KBSV) — hoạt động độc lập, không phụ thuộc thư viện bên ngoài.
  - `local store`: Kho dữ liệu nến CSV cục bộ tự động đồng bộ (`backend/data/ohlcv/`), duy trì hoạt động ổn định ngay cả khi offline.
  - *(Tùy chọn mở rộng: Module kế thừa vnstock được bọc lớp fallback an toàn, không bắt buộc cài đặt)*.
- **Vĩ mô & Tin tức Thời gian thực**: Tự động tổng hợp giá Vàng thế giới, Dầu Brent, Tỷ giá USD/VND và luồng tin tức RSS tài chính (CafeF, VnExpress).
- **Giao diện Trực quan & Tương tác Cao**: Xây dựng trên React 19 + Modern Native CSS, biểu đồ tài chính TradingView `lightweight-charts`, biểu đồ Radar đa chiều, danh mục theo dõi (Watchlist) lưu trữ SQLite cục bộ. Trang demo vi cấu trúc (`fiintrade_demo.html`) cung cấp trực quan hóa kịch bản tác chiến (lưu ý: phân tầng Shark Tracker tại đây là mô phỏng ý tưởng thiết kế khi chưa có luồng Tick Data L2/L3).

---

## 🏗️ Kiến Trúc Hệ Thống (All-in-One Container)

```
┌─────────────────────────────────────────────────────────────┐
│                ALL-IN-ONE DOCKER CONTAINER                  │
│                                                             │
│   ┌─────────────────────────────────────────────────────┐   │
│   │  React 19 SPA (Lightweight Charts + Dashboard)       │   │
│   │  Biên dịch tĩnh tại /app/web/dist                   │   │
│   └──────────────────────────┬──────────────────────────┘   │
│                              │ Phục vụ tĩnh nội bộ           │
│   ┌──────────────────────────▼──────────────────────────┐   │
│   │  FastAPI Application Server (Python 3.11-slim)       │   │
│   │  • Router API: /api/market_data, /api/watchlist...   │   │
│   │  • Static Mount: /assets -> /app/web/dist/assets    │   │
│   │  • Catch-all Route: /* -> index.html (SPA routing)  │   │
│   │  • Health Check: GET / HEAD /api/health             │   │
│   └──────────────────────────┬──────────────────────────┘   │
│                              │ Cổng động ${PORT:-7860}      │
└──────────────────────────────┼──────────────────────────────┘
                               │
                Trình duyệt Web người dùng 24/7
```

---

## 🚀 Khởi Chạy Cục Bộ (Local Quickstart)

### Cách 1: Khởi chạy bằng Docker (Khuyến nghị số 1)

Yêu cầu máy tính đã cài đặt và bật Docker Desktop.

```bash
# 1. Tải hoặc chuyển vào thư mục dự án
cd 2-DU-AN-AI-CHUNG-KHOAN

# 2. Xây dựng Docker image (Multi-stage build tự động build Frontend & Backend)
docker build -t ai-stock-workstation:latest .

# 3. Khởi chạy container
docker run -d \
  -p 7860:7860 \
  -e GEMINI_API_KEY="dien_khoa_gemini_api_tai_day" \
  -e AI_RATE_LIMIT_PER_HOUR=25 \
  --name ai-stock-workstation \
  ai-stock-workstation:latest

# 4. Kiểm tra sức khỏe hệ thống
curl http://localhost:7860/api/health
```

Sau khi chạy lệnh trên, mở trình duyệt web và truy cập: **`http://localhost:7860`** để sử dụng ứng dụng ngay.

---

### Cách 2: Khởi chạy Trực tiếp bằng Python & Node.js

Yêu cầu môi trường đã cài **Python 3.11+** và **Node.js 20+**.

#### Trên Windows (Tự động 1-Click):
Nháy đúp vào tệp tin **`start.bat`** tại thư mục gốc của dự án. File script sẽ tự động kích hoạt môi trường ảo Python và khởi động song song Backend (`http://127.0.0.1:8000`) cùng Frontend Vite Dev Server (`http://localhost:5173`).

#### Khởi chạy thủ công từng phần:
```bash
# Khởi chạy Backend (Terminal 1)
cd backend
python -m venv .venv
# Kích hoạt venv (Windows: .venv\Scripts\activate | Linux/macOS: source .venv/bin/activate)
pip install -r requirements.txt
uvicorn api:app --reload --port 8000

# Khởi chạy Frontend (Terminal 2)
cd web
npm install
npm run dev
```

---

## ☁️ Triển Khai Đám Mây 24/7 Miễn Phí (Cloud Deployment)

Ứng dụng được thiết kế tối ưu tuyệt đối cho hai nền tảng đám mây phổ biến nhất hiện nay:

| Nền tảng | Cấu hình Miễn phí | Cổng lắng nghe | Chống ngủ đông 24/7 |
|---|---|:---:|---|
| **Render.com** | 512 MB RAM, 0.1 vCPU | Tự động qua `$PORT` | Ping `/api/health` mỗi 5 phút qua UptimeRobot |
| **Hugging Face Spaces** | 16 GB RAM, 2 vCPU | Cổng cố định `7860` | Đã cấu hình non-root UID 1000, ping mỗi 1-2 ngày |

### Hướng Dẫn Chi Tiết
👉 **Đọc toàn bộ tài liệu hướng dẫn từng bước tại: [`DEPLOY_CLOUD_247.md`](./DEPLOY_CLOUD_247.md)**

Tài liệu bao gồm:
1. Hướng dẫn kết nối GitHub Repo lên **Render.com Web Service**.
2. Hướng dẫn tạo **Hugging Face Spaces** với Docker SDK.
3. Hướng dẫn thiết lập dịch vụ giám sát miễn phí **UptimeRobot** / **cron-job.org** ping vào endpoint `/api/health` để giữ ứng dụng thức 24/7 mà không tốn quota AI.

---

## ⚙️ Biến Môi Trường (Environment Variables)

| Tên biến | Bắt buộc | Giá trị mặc định | Diễn giải |
|---|:---:|:---:|---|
| `GEMINI_API_KEY` | **Có** | `""` | Khóa API Google Gemini lấy từ [Google AI Studio](https://aistudio.google.com/). |
| `PORT` | Không | `7860` | Cổng dịch vụ lắng nghe (Render tự động truyền giá trị này). |
| `AI_RATE_LIMIT_PER_HOUR` | Không | `25` | Giới hạn số lượt phân tích AI chuyên sâu của mỗi địa chỉ IP trong 1 giờ. |
| `PYTHONUTF8` | Không | `1` | Ép kiểu mã hóa UTF-8 cho Python trên mọi môi trường. |
| `GEMINI_MODELS` | Không | `gemini-2.5-flash,gemini-1.5-flash` | Danh sách model ưu tiên tự động failover khi gặp lỗi 429. |
| `DATA_SOURCES` | Không | `ssi,public,local` | Thứ tự ưu tiên của chuỗi nguồn dữ liệu giá (mặc định zero-dependency). |
| `DISABLE_VNSTOCK` | Không | `1` | Đặt thành `1` (mặc định) để hệ thống chạy độc lập qua public web / SSI / local store. |

---

## 📂 Cấu Trúc Thư Mục Dự Án

```
2-DU-AN-AI-CHUNG-KHOAN/
├── Dockerfile                  # Đóng gói All-in-One Multi-stage (Node + Python 3.11-slim)
├── .dockerignore               # Danh sách loại trừ tối ưu kích thước image build
├── DEPLOY_CLOUD_247.md         # Hướng dẫn chi tiết triển khai Render, HF Spaces & Ping 24/7
├── README.md                   # Tài liệu tổng quan dự án & HF Spaces Frontmatter
├── render.yaml                 # Blueprint triển khai tự động trên Render.com
├── railway.json                # Cấu hình dự phòng trên Railway
├── start.bat                   # Kịch bản khởi chạy nhanh 1-Click trên Windows
├── backend/                    # Toàn bộ mã nguồn máy chủ FastAPI & Lõi AI
│   ├── api.py                  # Điểm vào ứng dụng FastAPI & định tuyến SPA
│   ├── ai_analyzer.py          # Module phân tích kết hợp Gemini AI
│   ├── quant_engine.py         # Module định lượng 6 bước độc lập
│   ├── data_fetcher.py         # Bộ tải dữ liệu giá cổ phiếu
│   ├── data_sources.py         # Quản lý xoay vòng đa nguồn (SSI, Public web APIs, Local store)
│   ├── macro_fetcher.py        # Bộ tải chỉ số kinh tế vĩ mô quốc tế
│   ├── news_fetcher.py         # Quét tin tức RSS CafeF & VnExpress
│   ├── cache_manager.py        # Quản lý bộ đệm file JSON
│   ├── database.py             # SQLite cơ sở dữ liệu danh mục theo dõi
│   ├── requirements.txt        # Danh mục thư viện Python
│   ├── prompts/                # Prompt kỹ thuật chuyên gia chứng khoán
│   └── tests/                  # Bộ kiểm thử đơn vị, phòng vệ và nguồn dữ liệu
└── web/                        # Toàn bộ mã nguồn giao diện người dùng React
    ├── package.json            # Thư viện npm Frontend (React 19, Vite, Lightweight Charts)
    ├── vite.config.js          # Cấu hình đóng gói Vite
    ├── public/                 # Tài nguyên tĩnh (Favicon, icons, demo)
    └── src/                    # Mã nguồn các components giao diện
```

---

## 🧪 Kiểm Thử & Đảm Bảo Chất Lượng

Dự án trang bị đầy đủ các bộ kiểm thử tự động độc lập:

```bash
# 1. Chạy 12 bài test định lượng (Quant Engine)
python backend/tests/test_quant_engine.py

# 2. Chạy 8 bài test phòng vệ biên (Adversarial Tests)
python backend/tests/test_adversarial_v5.py

# 3. Chạy 7 bài test nguồn dữ liệu giá (Data Sources)
python backend/tests/test_data_sources.py

# 4. Kiểm tra biên dịch giao diện React
cd web && npm run build
```

---

## 📜 Giấy Phép & Tuyên Bố Miễn Trừ Trách Nhiệm

- **Giấy phép**: Mã nguồn được phân phối dưới giấy phép mã nguồn mở MIT.
- **Tuyên bố miễn trừ trách nhiệm**: Toàn bộ nhận định, dữ liệu và phân tích từ hệ thống chỉ mang tính chất tham khảo cho hoạt động nghiên cứu công nghệ tài chính. Người dùng tự chịu hoàn toàn trách nhiệm đối với các quyết định đầu tư thực tế trên thị trường chứng khoán.
