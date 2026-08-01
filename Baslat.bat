@echo off
title MP3 MP4 Loader Every Link Server
color 0A
cls

echo ============================================================
echo   🚀 MP3 MP4 LOADER EVERY LINK
echo   YouTube, TikTok, Instagram, Web Media, MP3, MP4, HD, 2K, 4K Converter
echo ============================================================
echo.

echo [*] Gerekli Python paketleri kontrol ediliyor...
python -m pip install yt-dlp flask imageio-ffmpeg --quiet --no-warn-script-location

echo [*] Windows Firewall'da 5001 portu aciliyor (arkadas erisimi icin)...
netsh advfirewall firewall add rule name="MediaDownloader Port 5001" dir=in action=allow protocol=TCP localport=5001 >nul 2>&1

echo [*] Sunucu baslatiliyor...
timeout /t 2 /nobreak > nul

start http://127.0.0.1:5001

echo.
echo ============================================================
echo [OK] Kendi bilgisayarin: http://127.0.0.1:5001
echo [OK] Arkadasin icin IP adresini asagida goruyorsun:
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /i "IPv4" ^| findstr /v "127.0.0.1"') do (
    set IP=%%a
    goto :found
)
:found
set IP=%IP: =%
echo [LINK] http://%IP%:5001
echo.
echo [*] Arkadaşın aynı Wi-Fi/ağdaysa bu linki tarayıcıya yapıştırabilir!
echo [*] Kapatmak icin bu pencereyi kapat veya Ctrl+C yap.
echo ============================================================
echo.

python app.py
pause
