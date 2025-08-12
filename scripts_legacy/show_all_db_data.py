from database_manager import DatabaseManager

if __name__ == "__main__":
    db = DatabaseManager()
    print("--- POSITIONS (ABIERTAS) ---")
    positions = db.load_positions()
    if not positions:
        print("No hay posiciones abiertas.")
    else:
        for pos in positions:
            print(pos)
    print("\n--- TRADES HISTORY (CERRADAS) ---")
    c = db.conn.cursor()
    c.execute('SELECT * FROM trades_history')
    rows = c.fetchall()
    columns = [desc[0] for desc in c.description]
    for row in rows:
        print(dict(zip(columns, row)))
    print("\n--- DAILY SNAPSHOTS ---")
    c.execute('SELECT * FROM daily_snapshots')
    rows = c.fetchall()
    columns = [desc[0] for desc in c.description]
    for row in rows:
        print(dict(zip(columns, row)))
