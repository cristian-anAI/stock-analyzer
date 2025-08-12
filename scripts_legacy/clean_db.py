# clean_db.py
"""
Elimina todas las posiciones, historial de trades y snapshots diarios de la base de datos para empezar desde cero.
"""
from database_manager import DatabaseManager


def clean_database():
    db = DatabaseManager()
    db.conn.execute('DELETE FROM positions')
    db.conn.execute('DELETE FROM trades_history')
    db.conn.execute('DELETE FROM daily_snapshots')
    db.conn.commit()
    db.close()
    print("Base de datos limpiada. Listo para recopilar datos nuevos.")

if __name__ == "__main__":
    clean_database()
