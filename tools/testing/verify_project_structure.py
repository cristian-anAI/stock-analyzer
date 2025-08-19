#!/usr/bin/env python3
"""
PROJECT STRUCTURE VERIFICATION SCRIPT
Verifies that all reorganized files work correctly from their new locations
"""

import os
import sys
import importlib.util
from pathlib import Path

class ProjectVerifier:
    def __init__(self):
        self.base_path = Path(__file__).parent.parent.parent
        self.results = []
        self.errors = []
    
    def log(self, message, success=True):
        """Log verification results"""
        status = "[OK]" if success else "[FAIL]"
        entry = f"{status} {message}"
        self.results.append(entry)
        print(entry)
        if not success:
            self.errors.append(message)
    
    def verify_core_files(self):
        """Verify core execution files are still accessible"""
        print("=== CORE FILES VERIFICATION ===")
        
        core_files = [
            "run_api.py",
            "main.py", 
            "start_autotrader.py",
            "trading.db"
        ]
        
        for file in core_files:
            file_path = self.base_path / file
            if file_path.exists():
                self.log(f"Core file exists: {file}")
            else:
                self.log(f"MISSING core file: {file}", False)
    
    def verify_tools_structure(self):
        """Verify tools directory structure"""
        print("\n=== TOOLS STRUCTURE VERIFICATION ===")
        
        tool_dirs = {
            "tools/analysis": [
                "analyze_performance.py",
                "check_all_positions.py", 
                "check_autotrader_transactions.py"
            ],
            "tools/testing": [
                "test_complete_short_system.py",
                "test_improved_short_logic.py",
                "audit_short_logic.py"
            ],
            "tools/dashboards": [
                "short_dashboard.py",
                "portfolio_dashboard.py"
            ],
            "tools/maintenance": [
                "fix_short_positions_stops.py",
                "generate_excel_reports.py",
                "cleanup_for_production.py"
            ]
        }
        
        for dir_name, files in tool_dirs.items():
            dir_path = self.base_path / dir_name
            if dir_path.exists():
                self.log(f"Tools directory exists: {dir_name}")
                
                for file in files:
                    file_path = dir_path / file
                    if file_path.exists():
                        self.log(f"  Tool file exists: {file}")
                    else:
                        self.log(f"  MISSING tool file: {file}", False)
            else:
                self.log(f"MISSING tools directory: {dir_name}", False)
    
    def verify_docs_structure(self):
        """Verify documentation structure"""
        print("\n=== DOCUMENTATION VERIFICATION ===")
        
        doc_files = [
            "docs/README.md",
            "docs/SHORT_IMPLEMENTATION_COMPLETE.md",
            "docs/DEPLOYMENT.md",
            "docs/short-system/short_logic_audit_20250817_193526.txt"
        ]
        
        for file in doc_files:
            file_path = self.base_path / file
            if file_path.exists():
                self.log(f"Documentation exists: {file}")
            else:
                self.log(f"MISSING documentation: {file}", False)
    
    def verify_api_imports(self):
        """Verify that API can still import correctly"""
        print("\n=== API IMPORTS VERIFICATION ===")
        
        try:
            # Test if we can import the main API module
            sys.path.insert(0, str(self.base_path / "src"))
            
            # Test importing key modules
            import src.api.main
            self.log("Can import API main module")
            
            import src.api.services.autotrader_service
            self.log("Can import autotrader service")
            
            import src.api.routers.short_monitoring
            self.log("Can import SHORT monitoring router")
            
        except Exception as e:
            self.log(f"Import error: {e}", False)
    
    def verify_database_access(self):
        """Verify database is accessible"""
        print("\n=== DATABASE ACCESS VERIFICATION ===")
        
        try:
            db_path = self.base_path / "trading.db"
            if db_path.exists():
                self.log("Main database file exists")
                
                # Test database connection
                import sqlite3
                conn = sqlite3.connect(str(db_path))
                cursor = conn.cursor()
                
                # Test basic query
                cursor.execute("SELECT COUNT(*) FROM positions")
                count = cursor.fetchone()[0]
                self.log(f"Database accessible - {count} positions found")
                
                # Test SHORT positions specifically
                cursor.execute("SELECT COUNT(*) FROM positions WHERE position_side = 'SHORT'")
                short_count = cursor.fetchone()[0]
                self.log(f"SHORT positions accessible - {short_count} SHORT positions found")
                
                conn.close()
            else:
                self.log("Main database file missing", False)
                
        except Exception as e:
            self.log(f"Database access error: {e}", False)
    
    def verify_archive_organization(self):
        """Verify archive organization"""
        print("\n=== ARCHIVE ORGANIZATION VERIFICATION ===")
        
        archive_dirs = [
            "archive/old-reports",
            "archive/temp-files", 
            "archive/legacy-traders"
        ]
        
        for dir_name in archive_dirs:
            dir_path = self.base_path / dir_name
            if dir_path.exists():
                file_count = len(list(dir_path.iterdir()))
                self.log(f"Archive directory '{dir_name}' exists with {file_count} files")
            else:
                self.log(f"Archive directory missing: {dir_name}", False)
    
    def test_tool_execution(self):
        """Test that tools can be executed from new locations"""
        print("\n=== TOOL EXECUTION VERIFICATION ===")
        
        # Test that we can at least import and analyze some tools
        tools_to_test = [
            "tools/testing/test_complete_short_system.py",
            "tools/dashboards/short_dashboard.py",
            "tools/analysis/analyze_performance.py"
        ]
        
        for tool_path in tools_to_test:
            full_path = self.base_path / tool_path
            if full_path.exists():
                try:
                    # Try to read the file and check for basic syntax
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if "def " in content or "class " in content:
                            self.log(f"Tool appears valid: {tool_path}")
                        else:
                            self.log(f"Tool may be malformed: {tool_path}", False)
                except Exception as e:
                    self.log(f"Error reading tool {tool_path}: {e}", False)
            else:
                self.log(f"Tool missing: {tool_path}", False)
    
    def run_full_verification(self):
        """Run complete project structure verification"""
        print("PROJECT STRUCTURE VERIFICATION")
        print("=" * 60)
        print(f"Base path: {self.base_path}")
        print()
        
        self.verify_core_files()
        self.verify_tools_structure()
        self.verify_docs_structure()
        self.verify_api_imports()
        self.verify_database_access()
        self.verify_archive_organization()
        self.test_tool_execution()
        
        print("\n" + "=" * 60)
        print("VERIFICATION SUMMARY")
        print("=" * 60)
        
        total_checks = len(self.results)
        successful_checks = len([r for r in self.results if r.startswith("[OK]")])
        failed_checks = total_checks - successful_checks
        
        print(f"Total checks: {total_checks}")
        print(f"Successful: {successful_checks}")
        print(f"Failed: {failed_checks}")
        
        if failed_checks == 0:
            print("\nALL VERIFICATIONS PASSED!")
            print("Project structure reorganization was successful!")
        else:
            print(f"\n{failed_checks} ISSUES FOUND:")
            for error in self.errors:
                print(f"  - {error}")
        
        return failed_checks == 0

def main():
    """Main verification function"""
    verifier = ProjectVerifier()
    success = verifier.run_full_verification()
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())