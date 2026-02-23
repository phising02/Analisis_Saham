@echo off
title ASTRONACCI PRO - ONE CLICK RUNNER
set PYTHON_EXE=.venv\Scripts\python.exe

echo ====================================================
echo   ASTRONACCI PRO - MASTER RUNNER
echo ====================================================

:: 1. Cek Venv
if not exist "%PYTHON_EXE%" (
    echo [ERROR] Virtual environment tidak ditemukan.
    echo Silakan jalankan start.bat terlebih dahulu untuk setup.
    pause
    exit
)

:: 2. Jalankan Dashboard (Background/Hidden)
echo [1/4] Memulai Dashboard di background...
start "Astronacci_Dashboard" /min %PYTHON_EXE% dashboard.py

:: 3. Jalankan Scanners (Visible windows so user can see progress)
echo [2/4] Memulai Multibagger Scanner...
start "Screener_Multibagger" %PYTHON_EXE% multibagger_screener.py

echo [3/4] Memulai LQ45 Scanner...
start "Screener_LQ45" %PYTHON_EXE% screener.py

:: 4. Buka Browser
echo [4/4] Menunggu sistem siap (5 detik)...
timeout /t 5 /nobreak > nul
echo Membuka Dashboard di Browser...
start http://localhost:5000

echo.
echo ====================================================
echo   SEMUA PROGRAM TELAH BERJALAN!
echo   - Dashboard: http://localhost:5000
echo   - Scanners sedang berjalan di jendela terpisah.
echo ====================================================
pause
