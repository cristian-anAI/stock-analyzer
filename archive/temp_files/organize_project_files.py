#!/usr/bin/env python3
"""
Organize project files into proper directory structure
"""
import os
import shutil
from pathlib import Path

def organize_files():
    """Move files to appropriate directories"""
    
    # File organization mapping
    moves = {
        # Analysis tools
        'tools/analysis/': [
            'analyze_early_exits.py',
            'analyze_win_rate_profit.py',
            'create_report.py',
            'generate_autotrader_report.py',
        ],
        
        # Testing tools  
        'tools/testing/': [
            'test_autotrader_api.py',
            'test_autotrader_live.py', 
            'test_buy_signals.py',
            'test_current_positions_fix.py',
            'test_database_score.py',
            'test_market_timing.py',
            'test_new_thresholds.py',
            'test_portfolio_status.py',
            'test_simple_autotrader.py',
            'test_swing_exit_fix.py',
            'test_transaction_pnl.py',
        ],
        
        # Debugging tools
        'tools/debugging/': [
            'fix_early_exits.py',
            'document_autotrader_rules.py',
        ],
        
        # Backtest tools
        'tools/backtest/': [
            'backtest_autotrader.py',
            'backtest_new_strategy.py', 
            'backtest_simplified.py',
            'quick_backtest.py',
            'quick_strategy_comparison.py',
            'run_1year_backtest.py',
        ],
        
        # Maintenance tools
        'tools/maintenance/': [
            'create_portfolio_tracking.py',
            'implement_refined_strategy.py',
        ],
        
        # Documentation
        'docs/': [
            'AUTOTRADER_COMPLETE_RULES.md',
            'PROJECT_STRUCTURE.md', 
            'REORGANIZATION_COMPLETE.md',
        ],
        
        # Archive temp files
        'archive/temp_files/': [
            'create_trading_model.ps1',
            'openapi_spec.json',
        ]
    }
    
    print("ORGANIZING PROJECT FILES")
    print("="*60)
    
    total_moved = 0
    
    for target_dir, files in moves.items():
        print(f"\nMoving to {target_dir}:")
        
        # Ensure target directory exists
        os.makedirs(target_dir, exist_ok=True)
        
        for filename in files:
            if os.path.exists(filename):
                try:
                    shutil.move(filename, os.path.join(target_dir, filename))
                    print(f"   MOVED: {filename}")
                    total_moved += 1
                except Exception as e:
                    print(f"   ERROR: {filename}: {e}")
            else:
                print(f"   MISSING: {filename}")
    
    print(f"\nSUMMARY: {total_moved} files organized")
    
    # Create/update README files for each directory
    create_readme_files()

def create_readme_files():
    """Create README files for organized directories"""
    
    readmes = {
        'tools/README.md': """# Tools Directory

This directory contains various tools and utilities for the stock analyzer project.

## Subdirectories

- `/analysis/` - Performance analysis and reporting tools
- `/testing/` - Test scripts for different components  
- `/debugging/` - Debug utilities and troubleshooting tools
- `/backtest/` - Backtesting scripts and strategies
- `/maintenance/` - Database and system maintenance scripts
""",

        'tools/analysis/README.md': """# Analysis Tools

Scripts for analyzing autotrader performance and generating reports.

- `analyze_early_exits.py` - Analyze early exit patterns
- `analyze_win_rate_profit.py` - Win rate and profit analysis  
- `create_report.py` - Generate trading reports
- `generate_autotrader_report.py` - Autotrader performance reports
""",

        'tools/testing/README.md': """# Testing Tools

Test scripts for validating different components of the system.

- `test_autotrader_*.py` - Autotrader functionality tests
- `test_market_timing.py` - Market timing restriction tests
- `test_*_fix.py` - Tests for specific fixes and improvements
""",

        'tools/debugging/README.md': """# Debugging Tools

Utilities for troubleshooting and fixing issues.

- `fix_early_exits.py` - Analysis and fix for early exit problem
- `document_autotrader_rules.py` - Complete autotrader rules documentation
""",

        'tools/backtest/README.md': """# Backtesting Tools

Scripts for backtesting trading strategies.

- `backtest_simplified.py` - Main simplified backtesting script
- `quick_backtest.py` - Quick strategy validation
- `run_1year_backtest.py` - Extended period backtesting
""",

        'docs/strategies/README.md': """# Strategy Documentation  

Complete documentation of trading strategies and rules.

- `AUTOTRADER_COMPLETE_RULES.md` - Comprehensive autotrader rules for backtesting
"""
    }
    
    print(f"\nCreating README files:")
    for readme_path, content in readmes.items():
        os.makedirs(os.path.dirname(readme_path), exist_ok=True)
        with open(readme_path, 'w') as f:
            f.write(content)
        print(f"   CREATED: {readme_path}")

if __name__ == "__main__":
    organize_files()