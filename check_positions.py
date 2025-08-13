#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('trading.db')
c = conn.cursor()

# Get all positions
c.execute('SELECT symbol, type, quantity, entry_price, current_price, pnl, source FROM positions')
positions = c.fetchall()

print(f"Total positions: {len(positions)}")
print("Current positions:")
for p in positions:
    print(f"  {p[0]} ({p[1]}) - Qty: {p[2]}, Entry: ${p[3]:.2f}, Current: ${p[4] or 0:.2f}, PnL: ${p[5] or 0:.2f}, Source: {p[6]}")

conn.close()