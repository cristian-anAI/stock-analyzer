#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('trading.db')
c = conn.cursor()

# Check autotrader transactions
c.execute('SELECT COUNT(*) FROM autotrader_transactions')
total = c.fetchone()[0]
print(f'Total autotrader transactions: {total}')

if total > 0:
    c.execute('''SELECT symbol, action, quantity, price, timestamp, reason 
                 FROM autotrader_transactions 
                 ORDER BY timestamp DESC 
                 LIMIT 15''')
    txns = c.fetchall()
    
    print('\nRecent autotrader transactions:')
    print('-' * 80)
    for txn in txns:
        symbol, action, quantity, price, timestamp, reason = txn
        print(f"{timestamp} | {action.upper():<4} {symbol:<8} | Qty: {quantity:>8.2f} | Price: ${price:>8.2f} | {reason}")
    
    # Get buy/sell summary
    c.execute('SELECT action, COUNT(*), SUM(quantity * price) FROM autotrader_transactions GROUP BY action')
    summary = c.fetchall()
    print('\nTransaction Summary:')
    for action, count, volume in summary:
        print(f"  {action.upper()}: {count} transactions, ${volume:.2f} total volume")

conn.close()