#!/usr/bin/env python3
"""
Production Cleanup Script
Removes unnecessary files and directories before Docker build
"""

import os
import shutil
import glob
from pathlib import Path

def cleanup_for_production():
    """Remove unnecessary files and directories for production deployment"""
    
    print("🧹 CLEANING PROJECT FOR PRODUCTION DEPLOYMENT")
    print("=" * 55)
    
    # Define directories and files to remove
    cleanup_items = [
        # Directories
        "reports/",
        "logs/", 
        "backups/",
        "legacy/",
        "scripts/testing/",
        "scripts/setup/",
        "web/",
        "src/logs/",
        "src/reports/",
        
        # Specific files
        "*.db",
        "*.backup", 
        "*.sqlite",
        "*.sqlite3",
        "temp_*.json",
        "*.log",
        "*.tmp",
        "*.temp",
        
        # Development scripts
        "analyze_performance.py",
        "check_*.py",
        "create_portfolio_tracking.py",
        "enhanced_automated_trader.py",
        "fix_database.py",
        "generate_*.py",
        "main.py",
        "portfolio_dashboard.py",
        "run_api.py",
        "start_autotrader.*",
        "test_*.py",
        "trading.db.backup",
        
        # Old Docker files
        "docker/",
        "src/api/Dockerfile",
        "src/api/docker-compose.yml",
    ]
    
    total_cleaned = 0
    total_size = 0
    
    for item in cleanup_items:
        # Handle glob patterns
        if '*' in item:
            matches = glob.glob(item, recursive=True)
            for match in matches:
                if os.path.exists(match):
                    size = get_size(match)
                    if os.path.isdir(match):
                        shutil.rmtree(match)
                        print(f"🗑️  Removed directory: {match} ({format_size(size)})")
                    else:
                        os.remove(match)
                        print(f"🗑️  Removed file: {match} ({format_size(size)})")
                    total_cleaned += 1
                    total_size += size
        else:
            # Handle direct paths
            if os.path.exists(item):
                size = get_size(item)
                if os.path.isdir(item):
                    shutil.rmtree(item)
                    print(f"🗑️  Removed directory: {item} ({format_size(size)})")
                else:
                    os.remove(item)
                    print(f"🗑️  Removed file: {item} ({format_size(size)})")
                total_cleaned += 1
                total_size += size
    
    # Clean __pycache__ directories
    pycache_count = 0
    pycache_size = 0
    for root, dirs, files in os.walk('.'):
        if '__pycache__' in dirs:
            pycache_path = os.path.join(root, '__pycache__')
            size = get_size(pycache_path)
            shutil.rmtree(pycache_path)
            pycache_count += 1
            pycache_size += size
    
    if pycache_count > 0:
        print(f"🗑️  Removed {pycache_count} __pycache__ directories ({format_size(pycache_size)})")
        total_cleaned += pycache_count
        total_size += pycache_size
    
    print("=" * 55)
    print(f"✅ CLEANUP COMPLETE!")
    print(f"📊 Removed {total_cleaned} items")
    print(f"💾 Freed {format_size(total_size)} of space")
    print("🚀 Project ready for production deployment!")

def get_size(path):
    """Get size of file or directory in bytes"""
    if os.path.isfile(path):
        return os.path.getsize(path)
    elif os.path.isdir(path):
        total = 0
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                try:
                    total += os.path.getsize(file_path)
                except (OSError, FileNotFoundError):
                    pass
        return total
    return 0

def format_size(bytes_size):
    """Format bytes to human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} TB"

if __name__ == "__main__":
    cleanup_for_production()