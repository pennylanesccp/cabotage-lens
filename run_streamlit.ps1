param(
    [int]$Port = 8501,
    [switch]$Headless,
    [switch]$NoBrowser
)

$ErrorActionPreference = 'Stop'

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$AppPath = Join-Path $RepoRoot 'app\main\page.py'
$NewCompatAppPath = Join-Path $RepoRoot 'app\app_streamlit.py'
$LegacyAppPath = Join-Path $RepoRoot 'apps\app_streamlit.py'
$LegacyRootAppPath = Join-Path $RepoRoot 'streamlit_app.py'

if (-not (Test-Path $AppPath)) {
    if (Test-Path $NewCompatAppPath) {
        $AppPath = $NewCompatAppPath
    } elseif (Test-Path $LegacyAppPath) {
        $AppPath = $LegacyAppPath
    } elseif (Test-Path $LegacyRootAppPath) {
        $AppPath = $LegacyRootAppPath
    } else {
        throw "Streamlit app not found. Expected '$AppPath' (or '$NewCompatAppPath' / '$LegacyAppPath' / '$LegacyRootAppPath')."
    }
}

$VenvPython = Join-Path $RepoRoot 'venv\Scripts\python.exe'
$VenvStreamlit = Join-Path $RepoRoot 'venv\Scripts\streamlit.exe'

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

Write-Host "Launching Streamlit app: $AppPath"
Write-Host "Port: $Port"

Push-Location $RepoRoot
try {
    if (Test-Path $VenvStreamlit) {
        & $VenvStreamlit @streamlitArgs
    } else {
        & $VenvPython -m streamlit @streamlitArgs
    }
} finally {
    Pop-Location
}

