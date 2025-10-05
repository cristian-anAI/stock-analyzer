#!/usr/bin/env python3
"""
Run database migrations
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

# Set database path
os.environ['SQLITE_DB_PATH'] = str(project_root / 'trading.db')

import logging
from api.database.migrations import run_portfolio_migrations

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def main():
    logger.info("=" * 70)
    logger.info("Running database migrations...")
    logger.info("=" * 70)

    success = run_portfolio_migrations()

    if success:
        logger.info("=" * 70)
        logger.info("✅ Migrations completed successfully!")
        logger.info("=" * 70)
        return 0
    else:
        logger.error("=" * 70)
        logger.error("❌ Migrations failed!")
        logger.error("=" * 70)
        return 1

if __name__ == "__main__":
    sys.exit(main())
