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

for /f "tokens=*" %%i in ('python -c "import platform; print(platform.python_version())"') do set PY_VERSION=%%i
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)"
if errorlevel 1 (
    echo ERROR: Python 3.11 or newer is required ^(found %PY_VERSION%^)
    exit /b 1
)

REM Install dependencies
echo Installing Python dependencies...
python -m pip install -r requirements.txt
python -m pip install pyinstaller

REM Download Ollama binary if not present
if not exist "ollama.exe" (
    echo Downloading Ollama binary...
        powershell -Command "$ProgressPreference = 'SilentlyContinue'; $latest = Invoke-RestMethod -Uri 'https://api.github.com/repos/ollama/ollama/releases/latest'; $latestTag = $latest.tag_name; Write-Host \"Latest version: $latestTag\"; $asset = $latest.assets | Where-Object { $_.name -match 'windows' } | Select-Object -First 1; if ($asset) { $assetName = $asset.name; Write-Host \"Selected asset: $assetName\"; $url = $asset.browser_download_url } else { $assetName = 'ollama-windows-amd64.zip'; $url = \"https://github.com/ollama/ollama/releases/download/$latestTag/$assetName\" }; $ext = [System.IO.Path]::GetExtension($assetName); $downloadPath = 'ollama_download' + $ext; Invoke-WebRequest -Uri $url -OutFile $downloadPath; if ($downloadPath -match '\\.zip$') { Expand-Archive -Path $downloadPath -DestinationPath '.' -Force; Write-Host 'Extracted ZIP'; } else { Write-Host 'Downloaded als non-zip; check for exe'; }; $ollamaCandidate = Get-ChildItem -Path '.' -Filter '*ollama*.exe' -Recurse -File | Select-Object -First 1; if ($ollamaCandidate) { Copy-Item -Path $ollamaCandidate.FullName -Destination 'ollama.exe' -Force; Write-Host ('Found and copied ' + $ollamaCandidate.FullName + ' to ollama.exe'); } else { Write-Host 'No ollama executable found in the extracted files'; }; if (Test-Path $downloadPath) { Remove-Item $downloadPath -Force }"
    %SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe -Command "if (Test-Path 'ollama.exe') { Write-Host '✓ Ollama downloaded' } else { Write-Error 'ERROR: Ollama executable not found after download/extraction'; exit 1 }"
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
