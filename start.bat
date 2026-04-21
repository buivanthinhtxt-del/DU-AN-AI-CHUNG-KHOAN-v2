@echo off
echo [*] Dang khoi dong AI Stock Analyzer...

:: Chay Backend trong cua so moi
start cmd /k "echo [*] Dang chay Backend (FastAPI)... && .venv\Scripts\python.exe -m uvicorn api:app --host 0.0.0.0 --port 8000"

:: Cho 3 giay de Backend khoi dong truoc
timeout /t 3 /nobreak > nul

:: Chay Frontend trong cua so moi
start cmd /k "echo [*] Dang chay Frontend (Vite)... && cd web && npm run dev"

echo.
echo [+] He thong dang duoc khoi dong!
echo [+] Dia chi truy cap: http://localhost:5173/
echo [!] Luu y: Khong dong cac cua so lenh dang chay.
echo.
pause
