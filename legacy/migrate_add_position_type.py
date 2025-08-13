# migrate_add_position_type.py
"""
Script to add 'position_type' column to the positions table if it does not exist.
"""
from database_manager import DatabaseManager


# Si la columna ya existe, actualiza el registro de BNB-USD a MANUAL
MIGRATION_SQL = """
UPDATE positions SET position_type = 'MANUAL' WHERE symbol = 'BNB-USD';
"""

def main():
    db = DatabaseManager()
    try:
        db.migrate(MIGRATION_SQL)
        print("Migration successful: 'position_type' column added to positions table.")
    except Exception as e:
        print(f"Migration failed or column already exists: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
