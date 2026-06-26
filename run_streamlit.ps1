param(
    [int]$Port = 8501,
    [switch]$Headless,
    [switch]$NoBrowser,
    [switch]$ForceInstall
)

$ErrorActionPreference = 'Stop'

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$AppPath = Join-Path $RepoRoot 'app\app_streamlit.py'
$FallbackAppPath = Join-Path $RepoRoot 'app\main\page.py'
$LegacyRootAppPath = Join-Path $RepoRoot 'streamlit_app.py'

if (-not (Test-Path $AppPath)) {
    if (Test-Path $FallbackAppPath) {
        $AppPath = $FallbackAppPath
    } elseif (Test-Path $LegacyRootAppPath) {
        $AppPath = $LegacyRootAppPath
    } else {
        throw "Streamlit app not found. Expected '$AppPath' (or '$FallbackAppPath' / '$LegacyRootAppPath')."
    }
}

$VenvPython = Join-Path $RepoRoot 'venv\Scripts\python.exe'
$VenvStreamlit = Join-Path $RepoRoot 'venv\Scripts\streamlit.exe'
$RequirementsInstallMarker = Join-Path $RepoRoot 'venv\.cabotagelens-requirements.stamp'
$RequirementsPath = Join-Path $RepoRoot 'requirements.txt'

if (-not (Test-Path $VenvPython)) {
    throw "Virtual environment not found at '$VenvPython'. Create it first: python -m venv venv"
}

$streamlitArgs = @(
    'run'
    $AppPath
    '--server.port'
    "$Port"
)

if ($Headless -or $NoBrowser) {
    $streamlitArgs += @('--server.headless', 'true')
} else {
    $streamlitArgs += @('--server.headless', 'false')
}

if ($NoBrowser) {
    $streamlitArgs += @('--browser.gatherUsageStats', 'false')
}

Write-Host "Launching CabotageLens Streamlit app: $AppPath"
Write-Host "Port: $Port"

Push-Location $RepoRoot
try {
    $NeedsRequirementsInstall = $ForceInstall -or (-not (Test-Path $RequirementsInstallMarker))
    if (-not $NeedsRequirementsInstall -and (Test-Path $RequirementsPath)) {
        $MarkerTime = (Get-Item $RequirementsInstallMarker).LastWriteTimeUtc
        if ((Get-Item $RequirementsPath).LastWriteTimeUtc -gt $MarkerTime) {
            $NeedsRequirementsInstall = $true
        }
    }

    if ($NeedsRequirementsInstall) {
        Write-Host "Installing dependencies from requirements.txt..."
        & $VenvPython -m pip install -r $RequirementsPath
        Set-Content -Path $RequirementsInstallMarker -Value (Get-Date -Format o) -Encoding ascii
    } else {
        Write-Host "Skipping dependency install (requirements unchanged). Use -ForceInstall to reinstall."
    }

    if (Test-Path $VenvStreamlit) {
        & $VenvStreamlit @streamlitArgs
    } else {
        & $VenvPython -m streamlit @streamlitArgs
    }
} finally {
    Pop-Location
}
