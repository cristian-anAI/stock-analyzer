#!/usr/bin/env python3
import sqlite3
from datetime import datetime

conn = sqlite3.connect('trading.db')
c = conn.cursor()

# Get all completed trades
c.execute('SELECT COUNT(*) FROM trades_history')
total_trades = c.fetchone()[0]

print(f"Total trades in history: {total_trades}")

if total_trades > 0:
    # Get recent trades
    c.execute('''SELECT symbol, entry_date, exit_date, entry_price, exit_price, 
                 quantity, pnl, pnl_percent, reason 
                 FROM trades_history 
                 ORDER BY exit_date DESC 
                 LIMIT 10''')
    trades = c.fetchall()
    
    print("\nRecent completed trades:")
    print("-" * 80)
    for trade in trades:
        symbol, entry_date, exit_date, entry_price, exit_price, quantity, pnl, pnl_percent, reason = trade
        print(f"{symbol:<6} | Entry: {entry_date} | Exit: {exit_date}")
        print(f"       | ${entry_price:.2f} -> ${exit_price:.2f} | Qty: {quantity} | P&L: ${pnl:.2f} ({pnl_percent:.1f}%)")
        print(f"       | Reason: {reason}")
        print("-" * 80)
        
    # Get summary stats
    c.execute('SELECT SUM(pnl), AVG(pnl_percent), COUNT(*) FROM trades_history WHERE pnl > 0')
    winning_stats = c.fetchone()
    c.execute('SELECT SUM(pnl), AVG(pnl_percent), COUNT(*) FROM trades_history WHERE pnl < 0')
    losing_stats = c.fetchone()
    
    print(f"\nTRADING SUMMARY:")
    print(f"Winning trades: {winning_stats[2]} | Total P&L: ${winning_stats[0] or 0:.2f} | Avg: {winning_stats[1] or 0:.1f}%")
    print(f"Losing trades: {losing_stats[2]} | Total P&L: ${losing_stats[0] or 0:.2f} | Avg: {losing_stats[1] or 0:.1f}%")
    
    total_pnl = (winning_stats[0] or 0) + (losing_stats[0] or 0)
    win_rate = (winning_stats[2] / total_trades) * 100 if total_trades > 0 else 0
    print(f"Total P&L: ${total_pnl:.2f} | Win Rate: {win_rate:.1f}%")

else:
    print("No completed trades found in history.")

conn.close()