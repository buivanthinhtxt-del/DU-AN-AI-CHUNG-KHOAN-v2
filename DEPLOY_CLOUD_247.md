# HƯỚNG DẪN TRIỂN KHAI ĐÁM MÂY 24/7 & CẤU HÌNH PING GIỮ THỨC
## AI Workstation Phân Tích Chứng Khoán Việt Nam (All-in-One Docker)

Tài liệu này cung cấp hướng dẫn chi tiết từng bước để triển khai ứng dụng **AI Workstation Phân Tích Chứng Khoán Việt Nam** lên các nền tảng đám mây miễn phí chất lượng cao (**Render.com** và **Hugging Face Spaces**), hoạt động ổn định 24/7 mà không cần máy tính cá nhân phải mở, đồng thời hướng dẫn cấu hình cơ chế ping định kỳ để ngăn chặn tình trạng ngủ đông (sleep/hibernation).

---

## MỤC LỤC
1. [Kiến Trúc Triển Khai All-in-One](#1-kiến-trúc-triển-khai-all-in-one)
2. [Triển Khai Trên Render.com (Khuyến Nghị Hàng Đầu)](#2-triển-khai-trên-rendercom-khuyến-nghị-hàng-đầu)
3. [Triển Khai Trên Hugging Face Spaces (Cấu Hình Cao 16GB RAM)](#3-triển-khai-trên-hugging-face-spaces-cấu-hình-cao-16gb-ram)
4. [Cấu Hình Ping Giữ Thức 24/7 (Keep-Alive Ping Mechanism)](#4-cấu-hình-ping-giữ-thức-247-keep-alive-ping-mechanism)
5. [Bảng So Sánh Nền Tảng Đám Mây Miễn Phí](#5-bảng-so-sánh-nền-tảng-đám-mây-miễn-phí)
6. [Xử Lý Sự Cố & Câu Hỏi Thường Gặp (Troubleshooting & FAQs)](#6-xử-lý-sự-cố--câu-hỏi-thường-gặp-troubleshooting--faqs)

---

## 1. KIẾN TRÚC TRIỂN KHAI ALL-IN-ONE

Hệ thống sử dụng mô hình đóng gói **Multi-stage Dockerfile**:
- **Stage 1 (Node.js 20 Alpine)**: Biên dịch toàn bộ mã nguồn React 19 từ thư mục `web/` thành các tệp tài nguyên tĩnh siêu nhẹ trong `web/dist/`.
- **Stage 2 (Python 3.11-slim)**: Cài đặt FastAPI, Uvicorn, các thư viện định lượng và AI; thiết lập người dùng bảo mật không đặc quyền `UID 1000`; tích hợp phục vụ giao diện tĩnh và API qua cùng một tiến trình.
- **Lợi ích vượt trội**:
  - **Zero-CORS**: Trình duyệt gọi trực tiếp `/api/*` trên cùng Domain/Origin, không bao giờ phát sinh lỗi CORS cross-origin.
  - **Single URL**: Chỉ cần duy nhất 1 đường dẫn web để sử dụng đầy đủ mọi tính năng.
  - **Dynamic Port**: Tự động liên kết cổng theo biến môi trường `$PORT` (Render) hoặc nhận mặc định cổng `7860` (Hugging Face Spaces).

---

## 2. TRIỂN KHAI TRÊN RENDER.COM (KHUYẾN NGHỊ HÀNG ĐẦU)

Render.com cung cấp gói Free Web Service mạnh mẽ, hỗ trợ Docker runtime tự động từ GitHub repo và tự động cấp chứng chỉ bảo mật SSL (HTTPS).

### Bước 1: Chuẩn bị GitHub Repository
Đảm bảo mã nguồn dự án đã được đồng bộ lên kho chứa GitHub cá nhân hoặc tổ chức của bạn (ví dụ: `https://github.com/<your-username>/DU-AN-AI-CHUNG-KHOAN-v2`).

### Bước 2: Tạo Web Service mới trên Render
1. Truy cập trang quản trị [dashboard.render.com](https://dashboard.render.com) và đăng nhập (bằng tài khoản GitHub để liên kết nhanh nhất).
2. Nhấn nút **New +** ở góc trên bên phải → Chọn **Web Service**.
3. Chọn tùy chọn **Build and deploy from a Git repository**.
4. Tìm và chọn repository của dự án chứng khoán, sau đó bấm **Connect**.

### Bước 3: Cấu hình thông số dịch vụ
Điền các trường cấu hình như sau:

| Mục cấu hình | Giá trị thiết lập | Ghi chú |
|---|---|---|
| **Name** | `ai-stock-workstation` (hoặc tên tùy thích) | Tên này sẽ quyết định tên miền phụ: `https://<name>.onrender.com` |
| **Region** | `Singapore (Southeast Asia)` | Vị trí gần Việt Nam nhất, giảm thiểu tối đa độ trễ mạng |
| **Branch** | `main` | Nhánh chứa mã nguồn hoàn chỉnh |
| **Runtime** | `Docker` | Render sẽ tự động phát hiện `Dockerfile` ở thư mục gốc |
| **Instance Type** | `Free` (0.1 vCPU, 512 MB RAM) | Hoàn toàn miễn phí, 750 giờ hoạt động/tháng |

### Bước 4: Thiết lập Biến Môi Trường (Environment Variables)
Kéo xuống mục **Environment Variables** và bấm **Add Environment Variable** để thêm các biến sau:

| Key (Khóa) | Value (Giá trị) | Mục đích |
|---|---|---|
| `GEMINI_API_KEY` | *(Khóa Gemini API của bạn)* | Lấy miễn phí tại [Google AI Studio](https://aistudio.google.com/) |
| `AI_RATE_LIMIT_PER_HOUR` | `25` | Bảo vệ quota AI, giới hạn 25 lượt gọi AI chuyên sâu/giờ/IP |
| `PYTHONUTF8` | `1` | Đảm bảo xử lý tiếng Việt trơn tru |

*(Lưu ý: Không cần cấu hình biến `PORT` vì Render sẽ tự động gán cổng động ngẫu nhiên và `Dockerfile` đã được tối ưu để tự bắt biến này).*

### Bước 5: Cấu hình Kiểm Tra Sức Khỏe (Health Check)
1. Bấm mở rộng mục **Advanced**.
2. Tại dòng **Health Check Path**, điền: `/api/health`.
3. Render sẽ gửi request kiểm tra tới endpoint này trước khi chuyển hướng lưu lượng mạng; nếu endpoint trả về HTTP `200 OK`, ứng dụng sẽ chính thức chuyển sang trạng thái **Live**.

### Bước 6: Kích hoạt Triển khai
1. Nhấn nút **Create Web Service**.
2. Render sẽ bắt đầu kéo image, thực hiện `npm ci`, `npm run build` và khởi chạy Uvicorn. Quá trình mất khoảng 2 - 4 phút ở lần build đầu tiên.
3. Khi màn hình log báo `Application startup complete` và trạng thái chuyển sang màu xanh lá **Live**, bạn có thể bấm vào đường dẫn `https://ai-stock-workstation.onrender.com` để mở giao diện Workstation.

---

## 3. TRIỂN KHAI TRÊN HUGGING FACE SPACES (CẤU HÌNH CAO 16GB RAM)

Hugging Face Spaces cung cấp phần cứng miễn phí cực khủng: **2 vCPU, 16 GB RAM** và ổ cứng SSD 50 GB. Ứng dụng đã được tích hợp sẵn metadata và cấu hình tương thích 100%.

### Bước 1: Tạo Space mới trên Hugging Face
1. Đăng nhập [huggingface.co](https://huggingface.co) (hoặc đăng ký tài khoản miễn phí).
2. Bấm vào ảnh đại diện góc phải → Chọn **New Space** (hoặc truy cập `https://huggingface.co/new-space`).
3. Điền các thông số:
   - **Space name**: `ai-stock-workstation`
   - **License**: `mit` (hoặc `apache-2.0`)
   - **Select the Space SDK**: Chọn biểu tượng **Docker** (chọn khuôn mẫu **Blank**).
   - **Space hardware**: `CPU basic · 2 vCPU · 16 GB RAM · Free`.
   - **Public / Private**: Chọn **Public** để mở quyền truy cập tự do cho mọi người.
4. Bấm **Create Space**.

### Bước 2: Cơ chế nhận diện tự động qua README.md
Tại thư mục gốc, file `README.md` của dự án đã có sẵn khối YAML Frontmatter:
```yaml
---
title: AI Workstation Phân Tích Chứng Khoán
emoji: 📈
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
---
```
Hệ thống Hugging Face Spaces sẽ tự động đọc cấu hình này để nhận diện runtime là **Docker** và ánh xạ lưu lượng vào cổng **7860**.

### Bước 3: Đồng bộ mã nguồn lên Hugging Face Space

#### Phương án A: Thêm Git Remote và đẩy trực tiếp (Khuyến nghị cho cá nhân)
Mở terminal trên máy trạm tại thư mục dự án:
```bash
# Thêm remote của Hugging Face (thay <your-hf-username> bằng username của bạn)
git remote add hf https://huggingface.co/spaces/<your-hf-username>/ai-stock-workstation

# Đẩy toàn bộ mã nguồn lên Space
git push hf main
```
*(Nếu hệ thống hỏi mật khẩu, nhập Hugging Face **User Access Token** có quyền Write lấy từ `https://huggingface.co/settings/tokens`).*

#### Phương án B: Tự động đồng bộ bằng GitHub Actions (Khuyến nghị cho CI/CD)
Tạo tệp `.github/workflows/sync_to_hf.yml` trên GitHub repo để mỗi lần push lên GitHub `main`, code sẽ tự động đồng bộ sang Hugging Face Spaces:
```yaml
name: Sync to Hugging Face Hub
on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - name: Push to HF
        env:
          HF_TOKEN: ${{ secrets.HF_TOKEN }}
        run: |
          git push https://<your-hf-username>:$HF_TOKEN@huggingface.co/spaces/<your-hf-username>/ai-stock-workstation main
```

### Bước 4: Thêm Khóa API Bí mật (Secret Key)
1. Trên giao diện Space của bạn trên Hugging Face, vào tab **Settings**.
2. Tìm đến mục **Variables and secrets**.
3. Tại ô **Secrets**, bấm **New secret**:
   - **Name**: `GEMINI_API_KEY`
   - **Value**: *(Dán khóa Gemini API của bạn vào đây)*
4. Bấm **Save**. Space sẽ tự động khởi động lại và nhận diện biến môi trường an toàn.

### Bước 5: Hoàn tất & Trải nghiệm
Sau khi build xong (hiển thị trạng thái **Running**), giao diện AI Workstation sẽ xuất hiện trực tiếp ngay trong khung nhúng của Hugging Face Space hoặc truy cập toàn màn hình tại:
`https://<your-hf-username>-ai-stock-workstation.hf.space`

---

## 4. CẤU HÌNH PING GIỮ THỨC 24/7 (KEEP-ALIVE PING MECHANISM)

### Tại sao cần cơ chế Ping?
- **Render.com Free Tier**: Tự động tạm ngưng (spin down / sleep) container nếu không có lượt truy cập nào trong **15 phút liên tục**. Khi có người dùng mới truy cập, trang web sẽ mất khoảng 30 - 50 giây để khởi động lại (cold start).
- **Hugging Face Spaces Free**: Có thể tự động ngủ đông sau **48 giờ** không có tương tác.
- **Giải pháp tối ưu**: Sử dụng một dịch vụ giám sát miễn phí từ bên ngoài gửi tín hiệu kiểm tra định kỳ (mỗi **5 đến 10 phút**) vào endpoint `/api/health`.

### Tại sao chọn endpoint `/api/health`?
- **Siêu nhẹ & Tốc độ tức thì**: Phản hồi HTTP `200 OK` với JSON nhỏ gọn dưới 100 bytes chỉ trong 1 - 2 mili-giây.
- **Hỗ trợ cả 2 phương thức**: Hỗ trợ đầy đủ cả `HEAD` (chỉ kiểm tra tiêu đề, không tốn băng thông) và `GET`.
- **Không tốn Quota AI**: Endpoint này hoàn toàn độc lập, không gọi tới Google Gemini, không kích hoạt phân tích định lượng, không bao giờ bị trừ hạn mức API.
- **Không bị chặn IP Rate Limit**: Nằm ngoài bộ đếm giới hạn tần suất người dùng.

---

### Hướng Dẫn 1: Cấu hình bằng UptimeRobot (Khuyến nghị số 1)
UptimeRobot là dịch vụ giám sát uptime hàng đầu thế giới, gói miễn phí cho phép tạo tới 50 monitors kiểm tra mỗi 5 phút.

1. **Đăng ký tài khoản**: Truy cập [uptimerobot.com](https://uptimerobot.com) và tạo tài khoản miễn phí.
2. **Tạo Monitor mới**:
   - Nhấn vào nút **+ Add New Monitor**.
   - **Monitor Type**: Chọn `HTTP(s)`.
   - **Friendly Name**: Đặt tên gợi nhớ, ví dụ: `AI Stock Workstation 24/7`.
   - **URL (or IP)**: Điền đường dẫn API sức khỏe của ứng dụng:
     - Trên Render: `https://ai-stock-workstation.onrender.com/api/health`
     - Trên Hugging Face: `https://<your-hf-username>-ai-stock-workstation.hf.space/api/health`
   - **Monitoring Interval**: Kéo thanh chọn về `Every 5 minutes` (mỗi 5 phút).
   - **Monitor HTTP Method**: Chọn `HEAD` (để tiết kiệm tối đa băng thông) hoặc `GET`.
3. **Lưu Monitor**:
   - Bấm **Create Monitor**.
   - Kể từ thời điểm này, UptimeRobot sẽ tự động gõ cửa ứng dụng mỗi 5 phút một lần, đảm bảo container trên Render luôn luôn ấm (warm) và sẵn sàng phản hồi ngay lập tức cho người dùng 24/7.

---

### Hướng Dẫn 2: Cấu hình bằng cron-job.org (Phương án Dự phòng Uy tín)
cron-job.org cung cấp dịch vụ cron job web hoàn toàn miễn phí, cho phép đặt lịch gửi request theo từng phút chính xác.

1. **Đăng ký tài khoản**: Truy cập [cron-job.org](https://cron-job.org/en/signup/) và kích hoạt tài khoản qua email.
2. **Tạo Cron Job mới**:
   - Vào mục **Cronjobs** → Bấm **Create cronjob**.
   - **Title**: `AI Workstation Keep-Alive Ping`.
   - **URL**: `https://ai-stock-workstation.onrender.com/api/health`.
   - **Execution schedule**: Chọn `Every 5 minutes` (hoặc `Every 10 minutes`).
   - **Request method**: Chọn `GET` hoặc `HEAD`.
   - **Status**: Đặt là `Enabled`.
3. **Lưu lại**:
   - Bấm **Create**. Hệ thống sẽ hiển thị lịch sử các lần ping thành công với mã phản hồi `200`.

---

## 5. BẢNG SO SÁNH NỀN TẢNG ĐÁM MÂY MIỄN PHÍ

| Tiêu chí so sánh | Render.com (Free) | Hugging Face Spaces (Free) |
|---|:---:|:---:|
| **Phần cứng miễn phí** | 0.1 vCPU, 512 MB RAM | **2 vCPU, 16 GB RAM** |
| **Dung lượng lưu trữ** | Tạm thời (Ephemera) | 50 GB SSD |
| **Thời gian ngủ đông (Inactivity)** | 15 phút (khắc phục bằng UptimeRobot) | 48 giờ (khắc phục bằng cron-job) |
| **Khởi động nguội (Cold Start)** | ~30 - 50 giây | ~10 - 20 giây |
| **Bảo mật người dùng** | Root hoặc Non-root | **Bắt buộc Non-root (UID 1000)** ✅ Đã hỗ trợ |
| **Tên miền tùy chỉnh (Custom Domain)** | Có hỗ trợ miễn phí | Cần cấu hình qua reverse-proxy/iframe |
| **Chứng chỉ SSL (HTTPS)** | Tự động miễn phí | Tự động miễn phí |
| **Cổng kết nối mặc định** | Cổng động `$PORT` ✅ Đã hỗ trợ | Cổng cố định `7860` ✅ Đã hỗ trợ |

---

## 6. XỬ LÝ SỰ CỐ & CÂU HỎI THƯỜNG GẶP (TROUBLESHOOTING & FAQS)

### Q1: Tại sao container báo lỗi `PermissionError: [Errno 13] Permission denied: '/home/user/.cache'`?
- **Nguyên nhân**: Trên Hugging Face Spaces, toàn bộ container bị cưỡng chế thực thi dưới quyền người dùng không đặc quyền có ID `1000`. Nếu ứng dụng chạy bằng `root` hoặc các thư mục cache thuộc sở hữu của `root`, các thư viện như `yfinance` hoặc `matplotlib` sẽ bị chặn quyền ghi.
- **Giải pháp**: `Dockerfile` của dự án đã tạo sẵn tài khoản `user` với `UID 1000`, thiết lập `ENV HOME=/home/user` và thực thi lệnh phân quyền chuẩn:
  ```dockerfile
  RUN useradd -m -u 1000 user
  RUN chown -R 1000:1000 /app /home/user
  USER user
  ```
  Bạn không cần thay đổi gì thêm.

---

### Q2: Tại sao triển khai trên Render báo lỗi `Port binding failed` hoặc `Timed out waiting for port`?
- **Nguyên nhân**: Render không cố định cổng `80` hay `8000`, mà tự động cấp phát một cổng ngẫu nhiên thông qua biến môi trường `$PORT` (ví dụ: `10000`). Nếu ứng dụng gán cứng một cổng cố định trong lệnh khởi chạy, Render sẽ không thể kết nối tới dịch vụ.
- **Giải pháp**: Lệnh khởi chạy trong `Dockerfile` đã được cấu hình dạng shell expansion:
  ```dockerfile
  CMD ["sh", "-c", "uvicorn api:app --app-dir backend --host 0.0.0.0 --port ${PORT:-7860}"]
  ```
  Khi chạy trên Render, Uvicorn sẽ tự động bắt cổng do Render truyền vào. Khi chạy trên Hugging Face hoặc máy tính cá nhân, Uvicorn tự động dùng cổng mặc định `7860`.

---

### Q3: Gặp lỗi `429 ResourceExhausted` từ Google Gemini API thì xử lý thế nào?
- **Nguyên nhân**: Khóa API miễn phí của Gemini có giới hạn số lượt gọi trong 1 phút (RPM) và số lượt gọi trong 1 ngày (RPD).
- **Cơ chế tự phục hồi của hệ thống**:
  1. Module `backend/llm_client.py` đã tích hợp danh sách model ưu tiên tự động failover: nếu `gemini-2.5-flash` bị quá tải 429, hệ thống sẽ tự động chuyển sang `gemini-1.5-flash` hoặc các model kế tiếp.
  2. Bạn có thể mở rộng danh sách model bằng cách thêm biến môi trường trên Render/HF Spaces:
     `GEMINI_MODELS=gemini-2.5-flash,gemini-1.5-flash,gemini-2.0-flash-lite`
  3. Khi toàn bộ model AI đều hết hạn mức, hệ thống tự động trả về **Báo cáo Phân tích Định lượng Toàn diện** được tính toán bởi thuật toán cục bộ 6 bước, đảm bảo người dùng vẫn nhận được phân tích chi tiết mà không gặp lỗi gián đoạn.

---

### Q4: Tôi có thể sử dụng tên miền riêng (ví dụ: `chungkhoan-ai.vn`) được không?
- **Hoàn toàn được**:
  1. Trên trang quản trị **Render.com**, vào dịch vụ Web Service của bạn → Chọn tab **Settings**.
  2. Kéo xuống mục **Custom Domains** → Nhập tên miền của bạn (ví dụ: `ai.yourdomain.com`).
  3. Cấu hình bản ghi `CNAME` trên nhà cung cấp tên miền của bạn trỏ về địa chỉ do Render cung cấp.
  4. Render sẽ tự động xác thực và cấp chứng chỉ SSL Let's Encrypt hoàn toàn miễn phí.

---

*Tài liệu được phát triển và kiểm toán chất lượng bởi Antigravity AI Engineering Team.*
