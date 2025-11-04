# Market Wake Scheduler
# Configures Windows to wake from sleep 1 hour before US market open (2:30 PM CET / 8:30 AM EST)

param(
    [switch]$Install,
    [switch]$Uninstall,
    [switch]$Status
)

$TaskName = "StockAnalyzer-MarketWake"
$WakeTime = "14:30"  # 2:30 PM CET (1 hour before market open at 3:30 PM CET / 9:30 AM EST)
$ScriptPath = Join-Path $PSScriptRoot "backend-health-check.ps1"

function Install-WakeTask {
    Write-Host "Installing Market Wake Scheduler..." -ForegroundColor Cyan

    # Check if task already exists
    $existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($existingTask) {
        Write-Host "Task already exists. Removing old task..." -ForegroundColor Yellow
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    }

    # Create the action (run backend health check script)
    $action = New-ScheduledTaskAction -Execute "PowerShell.exe" `
        -Argument "-ExecutionPolicy Bypass -File `"$ScriptPath`""

    # Create the trigger (daily at 2:30 PM CET)
    $trigger = New-ScheduledTaskTrigger -Daily -At $WakeTime

    # Create settings (allow wake from sleep)
    $settings = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -WakeToRun `
        -ExecutionTimeLimit (New-TimeSpan -Hours 4) `
        -RestartCount 3 `
        -RestartInterval (New-TimeSpan -Minutes 5)

    # Create principal (run as current user)
    $principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Highest

    # Register the task
    Register-ScheduledTask `
        -TaskName $TaskName `
        -Action $action `
        -Trigger $trigger `
        -Settings $settings `
        -Principal $principal `
        -Description "Wakes computer 1 hour before US market open and ensures Stock Analyzer backend is running" | Out-Null

    Write-Host "Task '$TaskName' installed successfully!" -ForegroundColor Green
    Write-Host "  Wake time: $WakeTime (Monday-Sunday)" -ForegroundColor Gray
    Write-Host "  Script: $ScriptPath" -ForegroundColor Gray
    Write-Host ""
    Write-Host "IMPORTANT: Your computer's BIOS must support wake timers." -ForegroundColor Yellow
    Write-Host "To verify BIOS support, run: powercfg /devicequery wake_armed" -ForegroundColor Yellow
}

function Uninstall-WakeTask {
    Write-Host "Uninstalling Market Wake Scheduler..." -ForegroundColor Cyan

    $existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($existingTask) {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Write-Host "Task '$TaskName' removed successfully!" -ForegroundColor Green
    } else {
        Write-Host "Task '$TaskName' not found." -ForegroundColor Yellow
    }
}

function Show-TaskStatus {
    Write-Host "Market Wake Scheduler Status" -ForegroundColor Cyan
    Write-Host "=============================" -ForegroundColor Cyan

    $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($task) {
        Write-Host "Status: INSTALLED" -ForegroundColor Green
        Write-Host "State: $($task.State)" -ForegroundColor Gray
        Write-Host "Wake Time: $WakeTime daily" -ForegroundColor Gray
        Write-Host "Last Run: $($task.LastRunTime)" -ForegroundColor Gray
        Write-Host "Next Run: $($task.NextRunTime)" -ForegroundColor Gray
        Write-Host "Last Result: $($task.LastTaskResult)" -ForegroundColor Gray
    } else {
        Write-Host "Status: NOT INSTALLED" -ForegroundColor Red
    }

    Write-Host ""
    Write-Host "Power Configuration:" -ForegroundColor Cyan
    Write-Host "-------------------" -ForegroundColor Cyan

    # Check if wake timers are enabled
    $wakeTimersOutput = powercfg /query SCHEME_CURRENT SUB_SLEEP RTCWAKE | Select-String "Current AC Power Setting Index"
    $wakeTimers = if ($wakeTimersOutput) { $wakeTimersOutput.Line -replace ".*: 0x", "" } else { "" }
    if ($wakeTimers -eq "00000001") {
        Write-Host "Wake Timers: ENABLED" -ForegroundColor Green
    } else {
        Write-Host "Wake Timers: DISABLED" -ForegroundColor Red
        Write-Host "To enable: powercfg /change standby-timeout-ac 0" -ForegroundColor Yellow
    }

    # Check devices that can wake the computer
    Write-Host ""
    Write-Host "Devices configured to wake PC:" -ForegroundColor Cyan
    powercfg /devicequery wake_armed
}

# Main execution
if ($Install) {
    Install-WakeTask
} elseif ($Uninstall) {
    Uninstall-WakeTask
} elseif ($Status) {
    Show-TaskStatus
} else {
    Write-Host "Market Wake Scheduler for Stock Analyzer" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Usage:" -ForegroundColor White
    Write-Host "  .\market-wake-scheduler.ps1 -Install    Install the scheduled task"
    Write-Host "  .\market-wake-scheduler.ps1 -Uninstall  Remove the scheduled task"
    Write-Host "  .\market-wake-scheduler.ps1 -Status     Show current status"
    Write-Host ""
    Write-Host "The task will wake your PC at 2:30 PM CET (1 hour before US market open)"
    Write-Host "and ensure the Stock Analyzer backend is running."
}
