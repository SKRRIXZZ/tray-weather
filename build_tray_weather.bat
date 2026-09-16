@echo off
cd /d "%~dp0"
python -m PyInstaller --noconfirm --clean --onefile --windowed --icon=icon.ico --name=WeatherTray "tray_weather_world_multilang.pyw"
echo.
echo Done: dist\WeatherTray.exe
pause
