@echo off
cd /d "%~dp0"

for /f "usebackq tokens=1,* delims==" %%A in ("%~dp0.env") do set "%%A=%%B"

cd /d "%~dp0backend"

echo Server tren may nay: http://127.0.0.1:8000
echo Cac dia chi IPv4 cua may:
ipconfig | findstr /i "IPv4"
echo Dung dia chi IPv4 trong muc Wi-Fi hoac Ethernet de may khac truy cap.
echo.

"..\.venv\Scripts\python.exe" -m uvicorn python:app --host 0.0.0.0 --port 8000

pause