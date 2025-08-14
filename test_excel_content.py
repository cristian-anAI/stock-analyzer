#!/usr/bin/env python3
"""
Test Excel content - Verify generated reports have data
"""

import pandas as pd
import os
from pathlib import Path

def test_excel_reports():
    reports_dir = Path("reports")
    
    if not reports_dir.exists():
        print("Reports directory not found!")
        return
    
    excel_files = list(reports_dir.glob("*.xlsx"))
    if not excel_files:
        print("No Excel files found!")
        return
    
    # Get latest files
    latest_files = {}
    for file_path in excel_files:
        base_name = file_path.name.split('_2025')[0]  # Get base name
        if base_name not in latest_files:
            latest_files[base_name] = file_path
        elif file_path.stat().st_mtime > latest_files[base_name].stat().st_mtime:
            latest_files[base_name] = file_path
    
    print("=== EXCEL REPORTS CONTENT VERIFICATION ===")
    print()
    
    for base_name, file_path in latest_files.items():
        print(f"FILE: {file_path.name}")
        print("-" * 50)
        
        try:
            # Read Excel file
            excel_data = pd.read_excel(file_path, sheet_name=None)  # Read all sheets
            
            for sheet_name, df in excel_data.items():
                print(f"  Sheet: {sheet_name}")
                print(f"     Rows: {len(df)}")
                print(f"     Columns: {list(df.columns)}")
                
                if len(df) > 0:
                    print("     Sample data:")
                    for i, row in df.head(2).iterrows():
                        print(f"       Row {i+1}: {dict(row)}")
                else:
                    print("     WARNING: No data in this sheet")
                print()
            
        except Exception as e:
            print(f"     ERROR reading file: {str(e)}")
        
        print()

if __name__ == "__main__":
    test_excel_reports()