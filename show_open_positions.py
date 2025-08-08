from database_manager import DatabaseManager

if __name__ == "__main__":
    db = DatabaseManager()
    positions = db.load_positions()
    if not positions:
        print("No hay posiciones abiertas en la base de datos.")
    else:
        print("Posiciones abiertas:")
        for pos in positions:
            print(f"{pos['symbol']} | Entrada: {pos['entry_date']} | Precio: {pos['entry_price']} | Cantidad: {pos['quantity']} | P&L: {pos.get('unrealized_pnl', 0):.2f}")
