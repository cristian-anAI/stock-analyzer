#!/usr/bin/env python3
"""
Simple script to run the Stock Analyzer API
"""

import sys
import os
from pathlib import Path

# Add the src directory to Python path
src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))

if __name__ == "__main__":
    import uvicorn
    import logging
    
    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Configure logging to show detailed autotrader logs
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),  # Console output
            logging.FileHandler('logs/api_console.log')
        ]
    )
    
    print("STOCK ANALYZER API - Console Mode")
    print("Watch autotrader logs in real-time!")
    print("=" * 50)
    
    # Check environment for production mode
    environment = os.getenv("ENVIRONMENT", "development").lower()
    is_production = environment == "production"
    
    # Run the API server
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=not is_production,  # Disable reload in production
        reload_excludes=["logs/*", "*.db", "*.db-journal", "*.db-wal", "*.pyc", "__pycache__/*", "*.backup_*"],
        log_level="info"
    )