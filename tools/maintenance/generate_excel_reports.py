#!/usr/bin/env python3
"""
Generate Excel Reports - Standalone script
Creates comprehensive Excel reports for trading analysis
"""

import sys
import os
from datetime import datetime, timedelta

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.api.services.excel_reports_service import ExcelReportsService

def main():
    print("=" * 60)
    print("          STOCK ANALYZER - EXCEL REPORTS GENERATOR")
    print("=" * 60)
    print(f"Starting report generation at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Initialize service
    reports_service = ExcelReportsService(output_dir="reports")
    
    # Generate all reports
    success = reports_service.generate_all_reports()
    
    if success:
        print("\nREPORTS GENERATED SUCCESSFULLY!")
        print("-" * 40)
        
        # List generated files
        reports_dir = reports_service.output_dir
        if reports_dir.exists():
            excel_files = list(reports_dir.glob("*.xlsx"))
            
            if excel_files:
                print(f"Generated {len(excel_files)} Excel files in '{reports_dir}':")
                print()
                
                for file_path in sorted(excel_files, key=lambda x: x.stat().st_mtime, reverse=True):
                    stat = file_path.stat()
                    size_mb = stat.st_size / (1024 * 1024)
                    created_time = datetime.fromtimestamp(stat.st_mtime)
                    
                    print(f"  {file_path.name}")
                    print(f"    Size: {size_mb:.2f} MB")
                    print(f"    Created: {created_time.strftime('%Y-%m-%d %H:%M:%S')}")
                    print()
                
                print("EXCEL FILES CONTENT:")
                print("-" * 40)
                print("1. Trading_History_*.xlsx")
                print("   - All_Transactions: Complete trading history")
                print("   - Stocks_History: Stock transactions only") 
                print("   - Crypto_History: Crypto transactions only")
                print("   - Trading_Summary: Portfolio statistics")
                print()
                print("2. Current_Positions_*.xlsx")
                print("   - Current_Positions: All open positions")
                print("   - Position_Evaluation: Analysis and recommendations")
                print("   - Portfolio_Config: Capital and P&L overview")
                print()
                print("3. Buy_Signals_*.xlsx")
                print("   - All_Buy_Signals: Combined signals (score >= 5)")
                print("   - Stock_Signals: Stock opportunities only")
                print("   - Crypto_Signals: Crypto opportunities only") 
                print("   - Signal_Summary: Signal statistics")
                print()
                print("4. Portfolio_Summary_*.xlsx")
                print("   - Portfolio_Overview: Complete portfolio status")
                print("   - Recent_Performance: Last 30 days activity")
                print("   - Top_Performers: Best performing assets")
                print()
                
                # Cleanup old reports
                print("CLEANING UP OLD REPORTS...")
                reports_service.cleanup_old_reports(days_to_keep=7)
                print("Removed reports older than 7 days")
                
            else:
                print("No Excel files found in reports directory")
        else:
            print("Reports directory not found")
    
    else:
        print("\nERROR: Failed to generate reports!")
        print("Check the logs for more details.")
        return 1
    
    print("=" * 60)
    print("Report generation completed!")
    print("=" * 60)
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)