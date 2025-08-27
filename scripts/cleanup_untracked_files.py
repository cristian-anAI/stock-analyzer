#!/usr/bin/env python3
"""
Cleanup Untracked Files Script
Organizes untracked files in the repository for clean deployment
"""

import os
import shutil
from datetime import datetime

def cleanup_untracked_files():
    """Clean up and organize untracked files"""
    
    print("🧹 CLEANUP UNTRACKED FILES")
    print("=" * 40)
    
    # Create cleanup directory if not exists
    cleanup_dir = "cleanup_temp"
    if not os.path.exists(cleanup_dir):
        os.makedirs(cleanup_dir)
        print(f"📁 Created cleanup directory: {cleanup_dir}")
    
    # Files to move to cleanup directory (testing/audit files)
    files_to_cleanup = [
        "audit_transaction_consistency.py",
        "clean_database_for_new_strategies.py", 
        "clean_db_simple.py",
        "fix_missing_short_entries.py",
        "fix_short_transaction_inconsistency.py",
        "test_data_service.py",
        "test_enhanced_autotrader.py",
        "test_imports.py",
        "test_main_imports.py",
        "test_new_tables.py",
        "test_portfolio_sync.py",
        "test_simple_enhanced.py",
        "test_transaction_logging.py",
        "verify_sync.py",
        "diagnose_portfolio_inconsistencies.py"
    ]
    
    # Move files to cleanup directory
    moved_files = []
    for file_path in files_to_cleanup:
        if os.path.exists(file_path):
            try:
                shutil.move(file_path, os.path.join(cleanup_dir, file_path))
                moved_files.append(file_path)
                print(f"📦 Moved: {file_path}")
            except Exception as e:
                print(f"❌ Error moving {file_path}: {e}")
    
    # Files to add to git (new functionality)
    files_to_add = [
        "src/api/database/new_strategy_migrations.py",
        "src/api/routers/symbol_search.py",
        "src/api/services/overtrading_prevention_service.py",
        "src/api/services/risk_management_service.py", 
        "src/api/services/timeframe_data_service.py",
        "src/api/services/transaction_logger.py",
        "src/api/services/volatility_service.py",
        "src/api/strategies/"
    ]
    
    print(f"\n✅ Cleanup completed!")
    print(f"📦 Moved {len(moved_files)} files to {cleanup_dir}/")
    
    print(f"\n📋 Files ready to add to git:")
    for file_path in files_to_add:
        if os.path.exists(file_path):
            print(f"   ✓ {file_path}")
        else:
            print(f"   ❌ {file_path} (not found)")
    
    print(f"\n🗑️  Files to remove:")
    if os.path.exists("nul"):
        print("   - nul (Windows temp file)")
        try:
            os.remove("nul")
            print("   ✓ Removed nul file")
        except:
            print("   ❌ Could not remove nul file")
    
    return moved_files, files_to_add

if __name__ == "__main__":
    moved, to_add = cleanup_untracked_files()
    
    print(f"\n🚀 Next steps for deployment:")
    print("1. Review the files in cleanup_temp/ directory")
    print("2. Add the new functionality files to git:")
    print("   git add src/api/database/new_strategy_migrations.py")
    print("   git add src/api/routers/symbol_search.py") 
    print("   git add src/api/services/overtrading_prevention_service.py")
    print("   git add src/api/services/risk_management_service.py")
    print("   git add src/api/services/timeframe_data_service.py")
    print("   git add src/api/services/transaction_logger.py")
    print("   git add src/api/services/volatility_service.py")
    print("   git add src/api/strategies/")
    print("3. Update .gitignore file")
    print("4. Commit and push changes")