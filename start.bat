@echo off
chcp 65001 > nul
set "ROOT_DIR=%~dp0"
echo [*] Đang khởi động AI Stock Analyzer (Antigravity WallStreet AI)...

:: Chạy Backend (FastAPI) từ thư mục backend/
start "Backend - FastAPI (8000)" cmd /k "cd /d "%ROOT_DIR%backend" && "%ROOT_DIR%.venv\Scripts\python.exe" -m uvicorn api:app --host 0.0.0.0 --port 8000 --reload"

:: Chờ 3 giây để Backend khởi động trước
ping 127.0.0.1 -n 4 > nul

:: Chạy Frontend (Vite) từ thư mục web/
start "Frontend - Vite (5173)" cmd /k "cd /d "%ROOT_DIR%web" && npm run dev"

echo.
echo [+] Hệ thống đang được khởi động!
echo [+] Backend API: http://localhost:8000/docs
echo [+] Frontend UI: http://localhost:5173/
echo [!] Lưu ý: Không đóng 2 cửa sổ lệnh đang chạy.
echo.
pause
