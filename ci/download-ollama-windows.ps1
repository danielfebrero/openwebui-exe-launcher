# Download+extract Ollama for Windows
param(
    [string]$LatestTag = '',
    [switch]$SkipExtract
)

$ErrorActionPreference = 'Stop'

# get latest tag if not given
if (-not $LatestTag) {
    $latest = Invoke-RestMethod -Uri "https://api.github.com/repos/ollama/ollama/releases/latest"
    $LatestTag = $latest.tag_name
} else {
    $latest = Invoke-RestMethod -Uri "https://api.github.com/repos/ollama/ollama/releases/tags/$LatestTag"
}
Write-Host "Downloading Ollama $LatestTag"

# Candidate patterns
$priorityPatterns = @('windows.*amd64','windows.*64','windows')

 # Gather candidates that look like windows builds
$assetCandidates = @()
foreach ($p in $priorityPatterns) {
    $assetCandidates += $latest.assets | Where-Object { $_.name -match $p }
}
$assetCandidates = $assetCandidates | Select-Object -Unique

# Exclude GPU/library-specific bundles that do not contain an executable, like ROCm/CUDA builds
# These builds often contain only native libraries (DLL/so/hsaco) and not the `ollama.exe` runtime
$assetCandidates = $assetCandidates | Where-Object { $_.name -notmatch 'rocm|cuda|hip|ggml|lib' }

if (-not $assetCandidates -or $assetCandidates.Count -eq 0) {
    Write-Host "WARNING: No windows asset found in release; falling back to default name"
    $assetCandidates = @(@{ name = 'ollama-windows-amd64.zip'; browser_download_url = "https://github.com/ollama/ollama/releases/download/$LatestTag/ollama-windows-amd64.zip" })
}

$found = $false
foreach ($asset in $assetCandidates) {
    $assetName = $asset.name
    Write-Host "Trying asset: $assetName"
    $url = $asset.browser_download_url
    $maxRetries = 3
    for ($i = 1; $i -le $maxRetries; $i++) {
        try {
            Write-Host "Download attempt $i/$maxRetries..."
            $ext = [System.IO.Path]::GetExtension($assetName)
            $downloadPath = "ollama_download$ext"
            Invoke-WebRequest -Uri $url -OutFile $downloadPath -ErrorAction Stop

            if ($downloadPath -match '\.zip$') {
                if (-not (Test-Path "ollama_temp")) { New-Item -ItemType Directory -Path "ollama_temp" | Out-Null }
                Expand-Archive -Path $downloadPath -DestinationPath "ollama_temp" -Force
                $ollamaExe = Get-ChildItem -Path "ollama_temp" -Recurse -File | Where-Object { $_.Name -match 'ollama' -and $_.Extension -ieq '.exe' } | Select-Object -First 1
            } else {
                $ollamaExe = $null
                if ($downloadPath -match '\.exe$') {
                    $ollamaExe = Get-Item -Path $downloadPath -ErrorAction SilentlyContinue
                }
                if (-not $ollamaExe) {
                    $ollamaExe = Get-ChildItem -Path '.' -Filter '*ollama*.exe' -Recurse | Select-Object -First 1
                }
            }

            if ($ollamaExe) {
                Copy-Item $ollamaExe.FullName -Destination "ollama.exe" -Force
                if (Test-Path "ollama_temp") { Remove-Item "ollama_temp" -Recurse -Force }
                if (Test-Path $downloadPath) { Remove-Item $downloadPath -Force }
                Write-Host "✓ ollama.exe downloaded successfully"
                $found = $true
                break
            } else {
                Write-Host "ollama.exe not found inside $assetName"
                if ($downloadPath -match '\.zip$') {
                    Write-Host "Contents of ${assetName}:"
                    Get-ChildItem -Path "ollama_temp" -Recurse | Select-Object FullName | ForEach-Object { Write-Host (" - " + $_.FullName) }
                }
                if (Test-Path "ollama_temp") { Remove-Item "ollama_temp" -Recurse -Force }
            }
        } catch {
            if ($i -eq $maxRetries) {
                Write-Host "Failed to download or extract $assetName after $maxRetries attempts: $_"
            }
            Write-Host "Retrying in 5 seconds..."
            Start-Sleep -Seconds 5
        }
    }
    if ($found) { break }
}

if (-not $found) {
    Write-Host "NOTICE: None of the candidate assets contained an executable - trying fallback to the canonical Windows asset name (ollama-windows-amd64.zip)"
    try {
        $fallbackUrl = "https://github.com/ollama/ollama/releases/download/$LatestTag/ollama-windows-amd64.zip"
        Invoke-WebRequest -Uri $fallbackUrl -OutFile "ollama_download.zip" -ErrorAction Stop
        if (-not (Test-Path "ollama_temp")) { New-Item -ItemType Directory -Path "ollama_temp" | Out-Null }
        Expand-Archive -Path "ollama_download.zip" -DestinationPath "ollama_temp" -Force
        $ollamaExe = Get-ChildItem -Path "ollama_temp" -Recurse -File | Where-Object { $_.Name -match 'ollama' -and $_.Extension -ieq '.exe' } | Select-Object -First 1
        if ($ollamaExe) {
            Copy-Item $ollamaExe.FullName -Destination "ollama.exe" -Force
            Remove-Item "ollama_temp" -Recurse -Force
            Remove-Item "ollama_download.zip" -Force
            Write-Host "✓ ollama.exe downloaded successfully (fallback asset)"
            $found = $true
        }
    } catch {
        Write-Host "Fallback attempt failed: $_"
    }
}

if (-not $found) { throw "ERROR: Failed to download ollama.exe: none of the windows assets contained an executable (tried $($assetCandidates.Count) candidate(s))." }

# exit 0 on success
exit 0
