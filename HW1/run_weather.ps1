# PowerShell wrapper to run HW1/main.py reliably from Task Scheduler
# - Sets working directory
# - Ensures UTF-8
# - Writes timestamped logs to HW1/logs

$ErrorActionPreference = 'Stop'

# Resolve script directory and project paths
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# Create logs directory if missing
$logsDir = Join-Path $ScriptDir 'logs'
if (-not (Test-Path $logsDir)) { New-Item -Path $logsDir -ItemType Directory | Out-Null }

# Timestamped log file
$timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$logFile = Join-Path $logsDir "run_$timestamp.log"

# Prefer 'py' launcher if available, otherwise fallback to 'python'
$pythonCmd = 'py'
try {
    $null = & $pythonCmd -3 -V 2>$null
} catch {
    $pythonCmd = 'python'
}

# Command to run main.py with UTF-8
$env:PYTHONUTF8 = '1'
$commandArgs = @('main.py')

# Run and capture output
"[INFO] Starting Weather-Kakao-Bot at $(Get-Date -Format 'u')" | Tee-Object -FilePath $logFile -Append | Out-Null
"[INFO] Working directory: $ScriptDir" | Tee-Object -FilePath $logFile -Append | Out-Null
"[INFO] Using Python command: $pythonCmd" | Tee-Object -FilePath $logFile -Append | Out-Null

try {
    & $pythonCmd $commandArgs 2>&1 | Tee-Object -FilePath $logFile -Append
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) {
        "[ERROR] Script exited with code $exitCode" | Tee-Object -FilePath $logFile -Append | Out-Null
        exit $exitCode
    } else {
        "[INFO] Completed successfully." | Tee-Object -FilePath $logFile -Append | Out-Null
    }
} catch {
    "[EXCEPTION] $($_.Exception.Message)" | Tee-Object -FilePath $logFile -Append | Out-Null
    exit 1
}
