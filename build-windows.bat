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
    powershell -Command "if (-not (Test-Path 'ollama_temp')) { New-Item -ItemType Directory -Path 'ollama_temp' | Out-Null }"
           powershell -Command "$ProgressPreference = 'SilentlyContinue'; $latest = Invoke-RestMethod -Uri 'https://api.github.com/repos/ollama/ollama/releases/latest'; $latestTag = $latest.tag_name; Write-Host \"Latest version: $latestTag\"; Write-Host 'Available assets:'; $latest.assets | ForEach-Object { Write-Host (' - ' + $_.name) }; $priorityPatterns = @('windows.*amd64','windows.*64','windows'); $assetCandidates = @(); foreach ($p in $priorityPatterns) { $assetCandidates += $latest.assets | Where-Object { $_.name -match $p } }; $assetCandidates = $assetCandidates | Select-Object -Unique; if (-not $assetCandidates -or $assetCandidates.Count -eq 0) { Write-Host 'WARNING: No windows asset found in release; falling back to default name'; $assetCandidates = @(@{ name = 'ollama-windows-amd64.zip'; browser_download_url = 'https://github.com/ollama/ollama/releases/download/$latestTag/ollama-windows-amd64.zip' }) }; $found = $false; foreach ($asset in $assetCandidates) { $assetName = $asset.name; Write-Host 'Trying asset: $assetName'; $url = $asset.browser_download_url; $maxRetries = 3; for ($i = 1; $i -le $maxRetries; $i++) { try { Write-Host 'Download attempt $i/$maxRetries...'; $ext = [System.IO.Path]::GetExtension($assetName); $downloadPath = 'ollama_download' + $ext; Invoke-WebRequest -Uri $url -OutFile $downloadPath -ErrorAction Stop; if ($downloadPath -match '\\.zip$') { Expand-Archive -Path $downloadPath -DestinationPath 'ollama_temp' -Force; $ollamaCandidate = Get-ChildItem -Path 'ollama_temp' -Recurse -File | Where-Object { $_.Name -match 'ollama' -and $_.Extension -ieq '.exe' } | Select-Object -First 1 } else { $ollamaCandidate = $null; if ($downloadPath -match '\\.exe$') { $ollamaCandidate = Get-Item -Path $downloadPath -ErrorAction SilentlyContinue }; if (-not $ollamaCandidate) { $ollamaCandidate = Get-ChildItem -Path '.' -Filter '*ollama*.exe' -Recurse | Select-Object -First 1 } }; if ($ollamaCandidate) { Copy-Item -Path $ollamaCandidate.FullName -Destination 'ollama.exe' -Force; if (Test-Path 'ollama_temp') { Remove-Item 'ollama_temp' -Recurse -Force }; if (Test-Path $downloadPath) { Remove-Item $downloadPath -Force }; Write-Host ('Found and copied ' + $ollamaCandidate.FullName + ' to ollama.exe'); $found = $true; break } else { Write-Host 'ollama.exe not inside $assetName'; if ($downloadPath -match '\\.zip$') { Write-Host 'Archive contents:'; Get-ChildItem -Path 'ollama_temp' -Recurse | Select-Object FullName | ForEach-Object { Write-Host (' - ' + $_.FullName) } }; if (Test-Path 'ollama_temp') { Remove-Item 'ollama_temp' -Recurse -Force } } } catch { if ($i -eq $maxRetries) { Write-Host 'Failed to download or extract $assetName after $maxRetries attempts: $_' } Write-Host 'Retrying in 5 seconds...'; Start-Sleep -Seconds 5 } }; if ($found) { break } }; if (-not $found) { Write-Error 'ERROR: Ollama executable not found in any windows asset'; exit 1 }"
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
