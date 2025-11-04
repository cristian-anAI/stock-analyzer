# Wake-Up System Setup Guide

## Overview
This system automatically wakes your PC from sleep/suspension 1 hour before US market open (2:30 PM CET / 8:30 AM EST) and ensures the Stock Analyzer backend API is running.

## Components

### 1. `backend-health-check.ps1`
Health monitoring script that:
- Checks if the API is running and healthy
- Starts the API if not running
- Retries with exponential backoff on failures
- Logs all activity to `backend-health.log`

**Configuration:**
```powershell
$BackendPath = "c:\repos\stock-analyzer"
$ApiUrl = "http://localhost:8000"
$MaxRetries = 5
$RetryDelaySeconds = 10
```

### 2. `market-wake-scheduler.ps1`
Task scheduler management script with three modes:

**Install mode:**
```bash
powershell -ExecutionPolicy Bypass -File market-wake-scheduler.ps1 -Install
```
Creates a Windows scheduled task that:
- Runs daily at 14:30 CET (2:30 PM)
- Wakes the computer from sleep
- Executes the backend health check
- Runs with highest privileges

**Status mode:**
```bash
powershell -ExecutionPolicy Bypass -File market-wake-scheduler.ps1 -Status
```
Shows:
- Task installation status
- Next scheduled wake time
- Wake timers configuration
- Devices that can wake the PC

**Uninstall mode:**
```bash
powershell -ExecutionPolicy Bypass -File market-wake-scheduler.ps1 -Uninstall
```
Removes the scheduled task completely.

### 3. `INSTALL_WAKE_TASK.bat`
Convenience installer with administrator privilege checks.

## Installation Steps

### Step 1: Run as Administrator
Right-click `INSTALL_WAKE_TASK.bat` and select **"Run as Administrator"**

OR manually:
```powershell
# Open PowerShell as Administrator
cd c:\repos\stock-analyzer\scripts\wake_up
powershell -ExecutionPolicy Bypass -File market-wake-scheduler.ps1 -Install
```

### Step 2: Enable Wake Timers
Wake timers must be enabled in Windows power settings:

```powershell
# Enable wake timers
powercfg /change standby-timeout-ac 0
```

Or via GUI:
1. Open **Control Panel** > **Power Options**
2. Click **Change plan settings** on your current plan
3. Click **Change advanced power settings**
4. Expand **Sleep** > **Allow wake timers**
5. Set to **Enable** for both battery and plugged in

### Step 3: Verify BIOS Support
Most modern PCs support wake timers, but verify:

```powershell
powercfg /devicequery wake_armed
```

If nothing is listed, check your BIOS settings:
- Boot into BIOS (usually F2, Del, or F10 during startup)
- Look for "Wake on RTC" or "Wake Timers" setting
- Enable if disabled

### Step 4: Verify Installation
Check the task status:

```powershell
powershell -File market-wake-scheduler.ps1 -Status
```

Expected output:
```
Market Wake Scheduler Status
=============================
Status: INSTALLED
State: Ready
Wake Time: 14:30 daily
Next Run: [tomorrow's date] 14:30:00
```

## How It Works

### Daily Cycle

**14:30 CET (2:30 PM)** - Wake Event
1. Windows Task Scheduler wakes the PC from sleep
2. `backend-health-check.ps1` is executed automatically
3. Script checks if API is healthy at `http://localhost:8000/health`

**If API is healthy:**
- Logs success
- Exits

**If API is not running:**
1. Starts `python run_api.py` in a minimized window
2. Waits 15 seconds for startup
3. Performs health checks every 10 seconds (up to 6 times)
4. Logs all activity

**15:30 CET (3:30 PM)** - Market Opens
- Backend is running and ready
- Box strategy monitoring is active (NDX, SPX, RTY)
- Autotrader analyzes market opening

## Troubleshooting

### Task Not Waking PC
**Cause:** Wake timers disabled or BIOS doesn't support RTC wake

**Solution:**
```powershell
# Check current power scheme
powercfg /query SCHEME_CURRENT SUB_SLEEP RTCWAKE

# Enable wake timers
powercfg /setactive SCHEME_CURRENT
powercfg /change standby-timeout-ac 0
```

### Backend Not Starting
**Cause:** Python path not in system PATH or backend path incorrect

**Solution:**
1. Check log file: `scripts\wake_up\backend-health.log`
2. Verify Python is accessible: `python --version`
3. Verify backend path in `backend-health-check.ps1`: `c:\repos\stock-analyzer`
4. Verify script name: `run_api.py`

### Health Check Failing
**Cause:** API starting but not responding on port 8000

**Solution:**
1. Check if port 8000 is blocked by firewall
2. Verify API configuration in `.env.prod`:
   ```
   API_HOST=0.0.0.0
   API_PORT=8000
   ```
3. Test manually:
   ```bash
   cd c:\repos\stock-analyzer
   python run_api.py
   ```

### Task Runs But PC Doesn't Wake
**Cause:** Fast Startup preventing proper wake

**Solution:**
1. Disable Fast Startup:
   - Control Panel > Power Options
   - Choose what the power buttons do
   - Uncheck "Turn on fast startup (recommended)"
2. Use Sleep instead of Hibernate

## Testing

### Test Wake Timer (Without Waiting)
1. Check next run time:
   ```powershell
   powershell -File market-wake-scheduler.ps1 -Status
   ```

2. Manually trigger the task:
   ```powershell
   Get-ScheduledTask -TaskName "StockAnalyzer-MarketWake" | Start-ScheduledTask
   ```

3. Check the log:
   ```powershell
   type scripts\wake_up\backend-health.log
   ```

### Test Backend Health Check Directly
```powershell
cd scripts\wake_up
powershell -ExecutionPolicy Bypass -File backend-health-check.ps1
```

Expected output:
```
=== Stock Analyzer Backend Health Check Started ===
Backend Path: c:\repos\stock-analyzer
API URL: http://localhost:8000
Checking backend health...
Backend is already running and healthy ✓
=== Health Check Completed Successfully ===
```

## Configuration Files

### Backend Paths (Fixed)
- **Before:** `c:\repos\stock-analyzer-backend` ❌
- **After:** `c:\repos\stock-analyzer` ✅

### Script Names (Fixed)
- **Before:** `main.py` ❌
- **After:** `run_api.py` ✅

## Maintenance

### View Recent Logs
```powershell
Get-Content scripts\wake_up\backend-health.log -Tail 50
```

### Change Wake Time
Edit `market-wake-scheduler.ps1` line 11:
```powershell
$WakeTime = "14:30"  # Change to your preferred time
```

Then reinstall:
```powershell
powershell -File market-wake-scheduler.ps1 -Install
```

### Disable Temporarily
```powershell
Disable-ScheduledTask -TaskName "StockAnalyzer-MarketWake"
```

### Re-enable
```powershell
Enable-ScheduledTask -TaskName "StockAnalyzer-MarketWake"
```

### Uninstall
```powershell
powershell -File market-wake-scheduler.ps1 -Uninstall
```

## Environment Variables

Backend uses `.env.prod` for production configuration:

```env
# Database
POSTGRES_DB=stock_analyzer_prod
POSTGRES_USER=stock_analyzer_user
POSTGRES_HOST=localhost
POSTGRES_PORT=5433

# API
API_HOST=0.0.0.0
API_PORT=8000

# Telegram Notifications
TELEGRAM_BOT_TOKEN=8449587269:AAFpKG-2r8Dv8b59UInh-TclaYSAzwq_18s
TELEGRAM_CHAT_ID=554526300

# Trading
AUTOTRADER_ENABLED=false
BOX_STRATEGY_ENABLED=true
BOX_STRATEGY_ML_VERSION=1
```

## Summary

✅ **Wake Time:** 14:30 CET daily (1 hour before market)
✅ **Backend:** Auto-starts if not running
✅ **Health Checks:** Retries with exponential backoff
✅ **Logging:** All activity logged to `backend-health.log`
✅ **Notifications:** Telegram alerts when backend starts
✅ **Box Strategy:** Monitors NDX, SPX, RTY at market open

The system ensures you never miss the market opening analysis, even while at work!
