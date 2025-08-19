# 📂 STOCK ANALYZER PROJECT STRUCTURE

## 🎯 Overview
This project has been reorganized for better maintainability, clarity, and professional structure.

---

## 📁 Root Directory Structure

```
stock-analyzer-main/
├── 🚀 CORE APPLICATION
├── 🔧 TOOLS & UTILITIES  
├── 📚 DOCUMENTATION
├── 📊 DATA & REPORTS
├── 🗃️ ARCHIVES
└── ⚙️ CONFIGURATION
```

---

## 🚀 CORE APPLICATION

### `/src/` - Main Source Code
```
src/
├── api/                    # FastAPI Backend
│   ├── database/          # Database management
│   ├── middleware/        # API middleware
│   ├── models/           # Data models
│   ├── routers/          # API endpoints
│   │   ├── short_monitoring.py  # NEW: SHORT monitoring endpoints
│   │   └── ...
│   ├── services/         # Business logic
│   │   ├── autotrader_service.py     # Main autotrader with SHORT
│   │   ├── advanced_scoring_service.py  # NEW: Advanced SHORT scoring
│   │   └── ...
│   └── tests/           # API tests
├── core/               # Core components
├── data/               # Data collection
├── traders/            # Trading strategies
├── utils/              # Utilities
└── web/                # Web interfaces
```

### Core Execution Files
- `run_api.py` - **Main API server startup**
- `main.py` - Alternative entry point
- `start_autotrader.py` - Standalone autotrader
- `trading.db` - **Main database**

---

## 🔧 TOOLS & UTILITIES

### `/tools/analysis/` - Analysis Tools
- `analyze_performance.py` - Performance analysis
- `check_all_positions.py` - Position checker
- `check_autotrader_transactions.py` - Transaction analysis
- `check_manual_positions.py` - Manual position checker
- `check_positions.py` - General position checker
- `check_trades_history.py` - Trade history analysis
- `diagnose_portfolio_inconsistencies.py` - Portfolio diagnostics

### `/tools/testing/` - Testing & Validation
- `test_complete_short_system.py` - **NEW: Complete SHORT system test**
- `test_improved_short_logic.py` - **NEW: SHORT logic testing**
- `test_advanced_scoring.py` - Scoring system tests
- `test_calibrated_scoring.py` - Calibrated scoring tests
- `test_excel_content.py` - Excel export tests
- `test_alerts_endpoint.py` - **NEW: SHORT alerts testing**
- `audit_short_logic.py` - **NEW: SHORT logic audit**

### `/tools/debugging/` - Debugging Tools
- `debug_alerts.py` - **NEW: Debug SHORT alerts**

### `/tools/maintenance/` - Maintenance Scripts
- `fix_short_positions_stops.py` - **NEW: Fix SHORT stop losses**
- `fix_database.py` - Database fixes
- `cleanup_for_production.py` - Production cleanup
- `reset_production_database.py` - Database reset
- `reset_production_clean.py` - Clean production reset
- `generate_excel_reports.py` - Report generation
- `generate_reports_now.py` - Immediate reports

### `/tools/dashboards/` - Interactive Dashboards
- `short_dashboard.py` - **NEW: SHORT positions dashboard**
- `portfolio_dashboard.py` - Portfolio dashboard

---

## 📚 DOCUMENTATION

### `/docs/` - Main Documentation
- `README.md` - **Main project documentation**
- `DEPLOYMENT.md` - Deployment instructions
- `TRADING_EXPANSION_SUMMARY.md` - Trading system overview
- `SHORT_IMPLEMENTATION_COMPLETE.md` - **NEW: Complete SHORT system docs**

### `/docs/short-system/` - SHORT System Documentation
- `short_logic_audit_20250817_193526.txt` - **SHORT system audit report**

### `/docs/deployment/` - Deployment Files
- `Dockerfile` - Docker configuration
- `docker-compose.prod.yml` - Production docker compose
- `deploy_to_gcloud.sh` - Google Cloud deployment

### `/docs/api/` - API Documentation
- (Auto-generated via FastAPI `/docs` endpoint)

---

## 📊 DATA & REPORTS

### `/reports/` - Generated Reports
- `Trading_History_*.xlsx` - Trading history reports (recent only)
- `Current_Positions_*.xlsx` - Position reports (recent only) 
- `Portfolio_Summary_*.xlsx` - Portfolio summaries (recent only)
- `Buy_Signals_*.xlsx` - Buy signal reports (recent only)

### `/data/` - Data Storage
- Market data cache and configurations

### `/logs/` - Application Logs
- `api.log` - API server logs
- `api_console.log` - Console logs
- Various dated log files

---

## 🗃️ ARCHIVES

### `/archive/old-reports/` - Archived Reports
- Historical reports (2025-08-14 to 2025-08-16)
- Moved to reduce clutter

### `/archive/temp-files/` - Temporary Files
- `temp_stocks.json` - Temporary stock data
- `temp_all_stocks.json` - Temporary all stocks data

### `/archive/legacy-traders/` - Legacy Trading Systems
- `enhanced_automated_trader.py` - Legacy enhanced trader
- `expanded_crypto_watchlist.py` - Legacy watchlist
- `optimized_trading_strategy.py` - Legacy strategy

### `/legacy/` - Legacy Components
- Old trading components (kept for reference)

---

## ⚙️ CONFIGURATION & SETUP

### `/scripts/` - Setup & Utility Scripts
```
scripts/
├── manual_positions/      # Manual position management
├── setup/                # Server setup scripts
└── testing/              # Testing utilities
```

### `/config/` - Configuration Files
- Application configurations

### `/backups/` - Database Backups
- `trading_20250810.db` - Historical backups
- `trading_20250811.db`
- `trading_20250812.db`

### `/docker/` - Docker Configuration
- Alternative Docker setups

---

## 🎯 KEY NEW FEATURES (SHORT SYSTEM)

### Recently Added Files:
1. **`/src/api/routers/short_monitoring.py`** - SHORT monitoring API
2. **`/src/api/services/advanced_scoring_service.py`** - Advanced SHORT scoring
3. **`/tools/dashboards/short_dashboard.py`** - Interactive SHORT dashboard
4. **`/tools/testing/test_complete_short_system.py`** - Complete system test
5. **`/tools/maintenance/fix_short_positions_stops.py`** - Stop loss fixes
6. **`/docs/SHORT_IMPLEMENTATION_COMPLETE.md`** - Complete documentation

### Enhanced Files:
- **`/src/api/services/autotrader_service.py`** - Now includes full SHORT support
- **`/src/api/main.py`** - Added SHORT monitoring routes

---

## 🚦 QUICK START COMMANDS

### Start the System:
```bash
# Start main API server
python run_api.py

# View SHORT dashboard
python tools/dashboards/short_dashboard.py

# Test SHORT system
python tools/testing/test_complete_short_system.py
```

### Analysis Commands:
```bash
# Analyze performance
python tools/analysis/analyze_performance.py

# Check all positions
python tools/analysis/check_all_positions.py

# Debug SHORT alerts
python tools/debugging/debug_alerts.py
```

### Maintenance Commands:
```bash
# Fix SHORT stop losses
python tools/maintenance/fix_short_positions_stops.py

# Generate reports
python tools/maintenance/generate_reports_now.py

# Clean production
python tools/maintenance/cleanup_for_production.py
```

---

## 📊 Project Statistics

- **Core Source Files**: ~40 files in `/src/`
- **Analysis Tools**: 7 files in `/tools/analysis/`
- **Testing Tools**: 6 files in `/tools/testing/`
- **Maintenance Scripts**: 8 files in `/tools/maintenance/`
- **Documentation**: 4+ markdown files
- **Archives**: 100+ old reports moved to archive

**Total Organization**: ~200+ files properly categorized and structured.

---

## 🔄 Migration Notes

All files have been moved to their appropriate directories while maintaining:
- ✅ **Functionality** - All scripts work from new locations
- ✅ **Import paths** - Relative imports updated where needed
- ✅ **Database connections** - Paths adjusted for new structure
- ✅ **Documentation** - Updated to reflect new structure

The project is now significantly more organized and professional!