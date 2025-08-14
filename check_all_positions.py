#!/usr/bin/env python3
"""
Check all positions in database
"""
import sqlite3

def check_positions():
    conn = sqlite3.connect('trading.db')
    conn.row_factory = sqlite3.Row

    print('=== ALL POSITIONS ===')
    cursor = conn.execute('SELECT * FROM positions ORDER BY created_at DESC')
    positions = cursor.fetchall()

    if positions:
        print(f'Found {len(positions)} total positions:')
        for i, pos in enumerate(positions):
            columns = [col[0] for col in cursor.description]
            print(f'Position #{i+1}:')
            for col in columns:
                value = pos[col]
                if col in ['entry_price', 'current_price'] and value:
                    print(f'  {col}: ${value:.2f}')
                else:
                    print(f'  {col}: {value}')
            print('  ---')
    else:
        print('No positions found')

    conn.close()

if __name__ == "__main__":
    check_positions()