@echo off
cd /d "%~dp0"

if not exist "backend\.env" (
    echo Khong tim thay backend\.env. Hay chay setup.bat truoc.
    pause
    exit /b 1
)

cd /d "%~dp0backend"

echo Server tren may nay: http://127.0.0.1:8000
echo Cac dia chi IPv4 cua may:
ipconfig | findstr /i "IPv4"
echo Dung dia chi IPv4 trong muc Wi-Fi hoac Ethernet de may khac truy cap.
echo.

"..\.venv\Scripts\python.exe" -m uvicorn python:app --host 0.0.0.0 --port 8000

pause