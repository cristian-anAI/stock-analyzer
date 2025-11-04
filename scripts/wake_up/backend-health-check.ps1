# Backend Health Check and Auto-Start
# Ensures the Stock Analyzer backend is running and healthy

param(
    [string]$BackendPath = "c:\repos\stock-analyzer",
    [string]$ApiUrl = "http://localhost:8000",
    [int]$MaxRetries = 5,
    [int]$RetryDelaySeconds = 10
)

$LogFile = Join-Path $PSScriptRoot "backend-health.log"
$PythonExe = "python"
$BackendScript = Join-Path $BackendPath "run_api.py"

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] [$Level] $Message"
    Write-Host $logMessage
    Add-Content -Path $LogFile -Value $logMessage
}

function Test-BackendHealth {
    try {
        $response = Invoke-WebRequest -Uri "$ApiUrl/health" -Method Get -TimeoutSec 5 -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            return $true
        }
    } catch {
        return $false
    }
    return $false
}

function Test-BackendProcess {
    # Check if uvicorn or python process is running the backend
    $processes = Get-Process -Name "python", "pythonw", "uvicorn" -ErrorAction SilentlyContinue
    foreach ($proc in $processes) {
        $cmdLine = (Get-WmiObject Win32_Process -Filter "ProcessId = $($proc.Id)").CommandLine
        if ($cmdLine -like "*run_api.py*" -or $cmdLine -like "*uvicorn*") {
            Write-Log "Found backend process: PID $($proc.Id)"
            return $true
        }
    }
    return $false
}

function Start-Backend {
    Write-Log "Starting backend at $BackendPath..."

    if (-not (Test-Path $BackendPath)) {
        Write-Log "Backend path not found: $BackendPath" -Level "ERROR"
        return $false
    }

    if (-not (Test-Path $BackendScript)) {
        Write-Log "Backend script not found: $BackendScript" -Level "ERROR"
        return $false
    }

    try {
        # Start backend in new window
        $startInfo = New-Object System.Diagnostics.ProcessStartInfo
        $startInfo.FileName = $PythonExe
        $startInfo.Arguments = "`"$BackendScript`""
        $startInfo.WorkingDirectory = $BackendPath
        $startInfo.UseShellExecute = $true
        $startInfo.WindowStyle = "Minimized"

        $process = [System.Diagnostics.Process]::Start($startInfo)
        Write-Log "Backend process started with PID: $($process.Id)"

        # Wait for backend to be ready
        Write-Log "Waiting for backend to be ready..."
        Start-Sleep -Seconds 15

        return $true
    } catch {
        Write-Log "Failed to start backend: $_" -Level "ERROR"
        return $false
    }
}

# Main execution
Write-Log "=== Stock Analyzer Backend Health Check Started ==="
Write-Log "Backend Path: $BackendPath"
Write-Log "API URL: $ApiUrl"

# Check if backend is already running and healthy
Write-Log "Checking backend health..."
$isHealthy = Test-BackendHealth

if ($isHealthy) {
    Write-Log "Backend is already running and healthy" -Level "SUCCESS"
    Write-Log "=== Health Check Completed Successfully ==="
    exit 0
}

# Check if process exists but not responding
$processExists = Test-BackendProcess
if ($processExists) {
    Write-Log "Backend process found but not responding. Attempting health check retries..." -Level "WARNING"

    for ($i = 1; $i -le 3; $i++) {
        Start-Sleep -Seconds 5
        if (Test-BackendHealth) {
            Write-Log "Backend became healthy on retry $i" -Level "SUCCESS"
            Write-Log "=== Health Check Completed Successfully ==="
            exit 0
        }
    }

    Write-Log "Backend not responding after retries. Process may be stuck." -Level "ERROR"
}

# Backend not running, attempt to start it
Write-Log "Backend is not running. Attempting to start..."

for ($attempt = 1; $attempt -le $MaxRetries; $attempt++) {
    Write-Log "Start attempt $attempt of $MaxRetries"

    $started = Start-Backend
    if (-not $started) {
        Write-Log "Failed to start backend on attempt $attempt" -Level "ERROR"
        if ($attempt -lt $MaxRetries) {
            Write-Log "Retrying in $RetryDelaySeconds seconds..."
            Start-Sleep -Seconds $RetryDelaySeconds
        }
        continue
    }

    # Wait and check health
    for ($healthCheck = 1; $healthCheck -le 6; $healthCheck++) {
        Start-Sleep -Seconds 10
        Write-Log "Health check $healthCheck/6..."

        if (Test-BackendHealth) {
            Write-Log "Backend is now healthy" -Level "SUCCESS"
            Write-Log "=== Health Check Completed Successfully ==="
            exit 0
        }
    }

    Write-Log "Backend started but not healthy after 60 seconds" -Level "WARNING"
}

Write-Log "Failed to start healthy backend after $MaxRetries attempts" -Level "ERROR"
Write-Log "=== Health Check Failed ==="
exit 1
