@echo off
cd /d "%~dp0"

python --version
if errorlevel 1 (
    echo Chua cai Python. Hay cai Python 3.13 roi chay lai file nay.
    pause
    exit /b 1
)

python -m venv .venv
if errorlevel 1 (
    echo Khong tao duoc moi truong Python.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -m pip install -r requirements-lock.txt
if errorlevel 1 (
    echo Cai thu vien that bai. Hay kiem tra Internet.
    pause
    exit /b 1
)

if not exist ".env" (
    for /f "delims=" %%S in ('".venv\Scripts\python.exe" -c "import secrets; print(secrets.token_urlsafe(48))"') do echo EXAM_JWT_SECRET=%%S> ".env"
)

echo Cai dat hoan tat. Xem HUONG_DAN.md de chay server.
if exist "HUONG_DAN.md" start "" "HUONG_DAN.md"
pause