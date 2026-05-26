@echo off
:: Tạo shortcut Quiz App trên Desktop
:: Double-click để chạy
PowerShell -ExecutionPolicy Bypass -File "%~dp0create_shortcut.ps1"
if errorlevel 1 (
    pause
) else (
    timeout /t 2 /nobreak >nul
)
