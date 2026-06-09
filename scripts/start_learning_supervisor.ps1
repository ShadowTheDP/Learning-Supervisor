param(
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonExe = Join-Path $projectRoot ".venv\Scripts\python.exe"
$stateDir = Join-Path $projectRoot "data\state"
$logDir = Join-Path $stateDir "logs"
$pidFile = Join-Path $stateDir "learning_supervisor.pid"
$stdoutLog = Join-Path $logDir "learning_supervisor.stdout.log"
$stderrLog = Join-Path $logDir "learning_supervisor.stderr.log"
$appUrl = "http://127.0.0.1:8000"
$healthUrl = "$appUrl/health"

function Show-LauncherError {
    param(
        [string]$Message
    )

    try {
        $shell = New-Object -ComObject WScript.Shell
        $null = $shell.Popup($Message, 0, "Learning Supervisor", 16)
    } catch {
        Write-Error $Message
    }
}

function Test-AppHealth {
    try {
        $response = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 2
        return $response.StatusCode -eq 200
    } catch {
        return $false
    }
}

function Open-AppBrowser {
    if (-not $NoBrowser) {
        Start-Process $appUrl | Out-Null
    }
}

function Get-AppListenerPid {
    try {
        $listener = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction Stop |
            Select-Object -First 1
        if ($listener) {
            return [int]$listener.OwningProcess
        }
    } catch {
        return $null
    }

    return $null
}

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

if (-not (Test-Path $pythonExe)) {
    Show-LauncherError "Cannot find the virtual-environment Python:`n$pythonExe`n`nPlease make sure the project's .venv exists."
    exit 1
}

New-Item -ItemType Directory -Path $logDir -Force | Out-Null

if (Test-AppHealth) {
    $runningPid = Get-AppListenerPid
    if ($null -ne $runningPid) {
        Set-Content -Path $pidFile -Value $runningPid
    }
    Open-AppBrowser
    exit 0
}

$existingPid = Read-PidValue -Path $pidFile
if ($null -ne $existingPid) {
    $existingProcess = Get-Process -Id $existingPid -ErrorAction SilentlyContinue
    if ($existingProcess) {
        for ($attempt = 0; $attempt -lt 10; $attempt += 1) {
            Start-Sleep -Milliseconds 500
            if (Test-AppHealth) {
                Open-AppBrowser
                exit 0
            }
        }
    }
}

$uvicornArgs = @(
    "-m",
    "uvicorn",
    "app.main:app",
    "--host",
    "127.0.0.1",
    "--port",
    "8000"
)

try {
    $process = Start-Process `
        -FilePath $pythonExe `
        -ArgumentList $uvicornArgs `
        -WorkingDirectory $projectRoot `
        -WindowStyle Hidden `
        -RedirectStandardOutput $stdoutLog `
        -RedirectStandardError $stderrLog `
        -PassThru
} catch {
    Show-LauncherError "Failed to launch Learning Supervisor.`n`n$($_.Exception.Message)"
    exit 1
}

for ($attempt = 0; $attempt -lt 60; $attempt += 1) {
    Start-Sleep -Milliseconds 500

    if (Test-AppHealth) {
        $runningPid = Get-AppListenerPid
        if ($null -ne $runningPid) {
            Set-Content -Path $pidFile -Value $runningPid
        } else {
            Set-Content -Path $pidFile -Value $process.Id
        }
        Open-AppBrowser
        exit 0
    }
}

if (Test-Path $pidFile) {
    Remove-Item -Path $pidFile -Force -ErrorAction SilentlyContinue
}

$errorTail = ""
if (Test-Path $stderrLog) {
    $errorTail = ((Get-Content -Path $stderrLog -Tail 20) -join "`n").Trim()
}

if (-not $errorTail) {
    $errorTail = "No additional error output was captured."
}

Show-LauncherError @"
Learning Supervisor failed to start.

Check:
$stderrLog

Recent error output:
$errorTail
"@

exit 1
