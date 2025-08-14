#!/usr/bin/env python3
"""
Generate Excel reports immediately to see latest manual positions
"""

import sys
import os

# Add the source directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from api.services.excel_reports_service import ExcelReportsService

def generate_reports_now():
    """Generate all Excel reports immediately"""
    print("Generating Excel reports with latest data...")
    
    try:
        excel_service = ExcelReportsService()
        excel_service.generate_all_reports()
        print("SUCCESS: All Excel reports generated successfully!")
        print("\nCheck the reports/ folder for the latest files.")
        
    except Exception as e:
        print(f"ERROR: Error generating reports: {e}")

if __name__ == "__main__":
    generate_reports_now()