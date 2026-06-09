$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$stateDir = Join-Path $projectRoot "data\state"
$pidFile = Join-Path $stateDir "learning_supervisor.pid"

function Read-PidValue {
    param(
        [string]$Path
    )

    if (-not (Test-Path $Path)) {
        return $null
    }

    $content = Get-Content -Path $Path -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -eq $content) {
        return $null
    }

    $value = $content.ToString().Trim()
    if ($value -match '^\d+$') {
        return [int]$value
    }

    return $null
}

if (-not (Test-Path $pidFile)) {
    exit 0
}

$pidValue = Read-PidValue -Path $pidFile
if ($null -ne $pidValue) {
    $process = Get-Process -Id $pidValue -ErrorAction SilentlyContinue
    if ($process) {
        Stop-Process -Id $process.Id -Force
    }
}

Remove-Item -Path $pidFile -Force -ErrorAction SilentlyContinue
