#!/usr/bin/env python3
"""
Check manual positions in database
"""
import sqlite3

def check_manual_positions():
    # Connect to database
    conn = sqlite3.connect('trading.db')
    conn.row_factory = sqlite3.Row

    # Check manual positions table
    print('=== MANUAL POSITIONS TABLE ===')
    cursor = conn.execute('SELECT * FROM manual_positions ORDER BY created_at DESC')
    positions = cursor.fetchall()

    if positions:
        print(f'Found {len(positions)} manual positions:')
        for pos in positions:
            print(f'  ID: {pos["id"]}')
            print(f'  Symbol: {pos["symbol"]}')  
            print(f'  Quantity: {pos["quantity"]}')
            print(f'  Entry Price: ${pos["entry_price"]:.2f}')
            print(f'  Current Price: ${pos["current_price"] if pos["current_price"] else "N/A"}')
            print(f'  Notes: {pos["notes"]}')
            print(f'  Created: {pos["created_at"]}')
            print('  ---')
    else:
        print('No manual positions found')

    conn.close()

if __name__ == "__main__":
    check_manual_positions()