<#
.SYNOPSIS
    Tạo shortcut Quiz App trên Desktop với icon tùy chỉnh.

.DESCRIPTION
    Script tạo file .lnk chuẩn Windows có trường IconLocation.
    Để thay icon: đổi file assets\icons\app_icon.ico rồi chạy lại script này.

.USAGE
    PowerShell -ExecutionPolicy Bypass -File create_shortcut.ps1
    hoặc double-click run_create_shortcut.bat
#>

$ScriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Definition
$PythonExe   = Join-Path $ScriptDir ".venv\Scripts\pythonw.exe"
$MainPy      = Join-Path $ScriptDir "main.py"
$IconFile    = Join-Path $ScriptDir "assets\icons\app_icon.ico"
$ShortcutName = "Quiz App.lnk"

# Đặt shortcut trên Desktop của user hiện tại
$DesktopPath = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $DesktopPath $ShortcutName

# Kiểm tra pythonw.exe
if (-not (Test-Path $PythonExe)) {
    Write-Warning "pythonw.exe not found: $PythonExe"
    Write-Warning "Run: python -m venv .venv  then  pip install -r requirements.txt"
    exit 1
}

# Check icon
if (-not (Test-Path $IconFile)) {
    Write-Warning "Icon not found: $IconFile"
    Write-Warning "Run: python assets\icons\generate_icon.py to create the default icon."
    exit 1
}

$WShell   = New-Object -ComObject WScript.Shell
$Shortcut = $WShell.CreateShortcut($ShortcutPath)

$Shortcut.TargetPath      = $PythonExe
$Shortcut.Arguments       = "`"$MainPy`""
$Shortcut.WorkingDirectory = $ScriptDir
$Shortcut.IconLocation    = "$IconFile,0"
$Shortcut.Description     = "Quiz Desktop App"
$Shortcut.WindowStyle     = 1   # Normal window

$Shortcut.Save()

Write-Host "Shortcut created: $ShortcutPath" -ForegroundColor Green
Write-Host ""
Write-Host "To change icon:" -ForegroundColor Cyan
Write-Host "  1. Replace file: $IconFile" -ForegroundColor Cyan
Write-Host "  2. Run this script again" -ForegroundColor Cyan
