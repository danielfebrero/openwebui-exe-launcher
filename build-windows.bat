@echo off
REM Build script for Open WebUI + Ollama Portable Launcher (Windows)

echo ============================================
echo Building Open WebUI + Ollama for Windows
echo ============================================

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python 3 is required
    exit /b 1
)

REM Install dependencies
echo Installing Python dependencies...
pip install -r requirements.txt
pip install pyinstaller

REM Download Ollama binary if not present
if not exist "ollama.exe" (
    echo Downloading Ollama binary...
    powershell -Command "$ProgressPreference = 'SilentlyContinue'; $latestTag = (Invoke-RestMethod -Uri 'https://api.github.com/repos/ollama/ollama/releases/latest').tag_name; Write-Host \"Latest version: $latestTag\"; $url = \"https://github.com/ollama/ollama/releases/download/$latestTag/ollama-windows-amd64.zip\"; Invoke-WebRequest -Uri $url -OutFile 'ollama.zip'; Expand-Archive -Path 'ollama.zip' -DestinationPath '.' -Force; Remove-Item 'ollama.zip'"
    echo ✓ Ollama downloaded
) else (
    echo ✓ Ollama binary already exists
)

REM Build the exe
echo Building .exe with PyInstaller...
pyinstaller --clean openwebui-portable.spec

REM Check if build succeeded
if exist "dist\OpenWebUI-Ollama-Portable\OpenWebUI-Ollama-Portable.exe" (
    echo ✓ Build successful!
    echo.
    echo Application: dist\OpenWebUI-Ollama-Portable\
    echo.
    echo To create ZIP:
    echo   powershell Compress-Archive -Path "dist\OpenWebUI-Ollama-Portable" -DestinationPath "OpenWebUI-Ollama-Portable-Windows.zip"
    echo.
    echo To run:
    echo   dist\OpenWebUI-Ollama-Portable\OpenWebUI-Ollama-Portable.exe
) else (
    echo ERROR: Build failed
    exit /b 1
)
