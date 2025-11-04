import sqlite3
import sys

db_path = sys.argv[1] if len(sys.argv) > 1 else 'trading.db'
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Get all tables
tables = [t[0] for t in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]

print(f"Database: {db_path}")
print(f"Tables: {len(tables)}\n")

for table in tables:
    if table == 'sqlite_sequence':
        continue

    print(f"\n{'='*80}")
    print(f"TABLE: {table}")
    print('='*80)

    # Get schema
    schema = cur.execute(f'PRAGMA table_info({table})').fetchall()
    print("\nColumns:")
    for col in schema:
        col_id, name, type_, notnull, default, pk = col
        nullable = "NOT NULL" if notnull else "NULL"
        pk_str = "PRIMARY KEY" if pk else ""
        default_str = f"DEFAULT {default}" if default else ""
        print(f"  {name:30} {type_:15} {nullable:10} {pk_str:15} {default_str}")

    # Get row count
    count = cur.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
    print(f"\nRows: {count}")

    # Get sample data
    if count > 0:
        print("\nSample row:")
        sample = cur.execute(f'SELECT * FROM {table} LIMIT 1').fetchone()
        col_names = [col[1] for col in schema]
        for col_name, value in zip(col_names, sample):
            print(f"  {col_name}: {value}")

conn.close()
