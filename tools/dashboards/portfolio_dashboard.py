#!/usr/bin/env python3
"""
Portfolio Dashboard - Complete view of trading performance
Shows separated stocks and crypto portfolios with detailed analytics
"""

import sqlite3
from datetime import datetime

def show_portfolio_dashboard():
    conn = sqlite3.connect('trading.db')
    c = conn.cursor()
    
    print("=" * 80)
    print("               PORTFOLIO DASHBOARD - STOCK ANALYZER")
    print("=" * 80)
    
    # Get portfolio overviews
    c.execute('''SELECT type, initial_capital, current_capital, available_cash, 
                        invested_amount, total_pnl, total_trades
                 FROM portfolio_config ORDER BY type''')
    
    portfolios = c.fetchall()
    total_initial = 0
    total_current = 0
    total_pnl = 0
    
    for portfolio in portfolios:
        portfolio_type, initial_capital, current_capital, available_cash, invested_amount, pnl, total_trades = portfolio
        
        print(f"\n{portfolio_type.upper()} PORTFOLIO:")
        print("-" * 40)
        print(f"Initial Capital:    ${initial_capital:>12,.2f}")
        print(f"Current Capital:    ${current_capital:>12,.2f}")
        print(f"Available Cash:     ${available_cash:>12,.2f}")
        print(f"Invested Amount:    ${invested_amount:>12,.2f}")
        print(f"Total P&L:          ${pnl:>12,.2f}")
        print(f"ROI:                {(pnl/initial_capital)*100:>11.2f}%")
        print(f"Total Trades:       {total_trades:>12}")
        
        # Show current positions
        c.execute('''SELECT symbol, quantity, avg_entry_price, total_invested
                     FROM portfolio_positions 
                     WHERE portfolio_type = ?
                     ORDER BY total_invested DESC''', (portfolio_type,))
        
        positions = c.fetchall()
        if positions:
            print(f"\nCurrent Positions ({len(positions)}):")
            print("Symbol    Quantity      Avg Price    Invested")
            print("-" * 48)
            for symbol, quantity, avg_price, invested in positions:
                print(f"{symbol:<8} {quantity:>10.4f} ${avg_price:>10.2f} ${invested:>10.2f}")
        else:
            print("\nNo current positions")
        
        # Show recent transactions
        c.execute('''SELECT symbol, action, quantity, price, timestamp, 
                            COALESCE(buy_reason, sell_reason) as reason
                     FROM portfolio_transactions 
                     WHERE portfolio_type = ?
                     ORDER BY timestamp DESC LIMIT 5''', (portfolio_type,))
        
        recent_txns = c.fetchall()
        if recent_txns:
            print(f"\nRecent Transactions:")
            print("Date       Action Symbol    Quantity     Price    Reason")
            print("-" * 65)
            for symbol, action, quantity, price, timestamp, reason in recent_txns:
                date_str = timestamp[:10] if timestamp else "Unknown"
                action_str = action.upper()
                reason_str = (reason or "")[:15]
                print(f"{date_str} {action_str:<6} {symbol:<8} {quantity:>8.4f} ${price:>8.2f} {reason_str}")
        
        total_initial += initial_capital
        total_current += current_capital
        total_pnl += pnl
    
    # Overall summary
    print("\n" + "=" * 80)
    print("                        OVERALL SUMMARY")
    print("=" * 80)
    print(f"Total Initial Capital:  ${total_initial:>12,.2f}")
    print(f"Total Current Capital:  ${total_current:>12,.2f}")
    print(f"Total P&L:              ${total_pnl:>12,.2f}")
    print(f"Overall ROI:            {(total_pnl/total_initial)*100:>11.2f}%")
    
    # Performance comparison
    if len(portfolios) >= 2:
        stocks_data = next((p for p in portfolios if p[0] == 'stocks'), None)
        crypto_data = next((p for p in portfolios if p[0] == 'crypto'), None)
        
        if stocks_data and crypto_data:
            stocks_roi = (stocks_data[5] / stocks_data[1]) * 100
            crypto_roi = (crypto_data[5] / crypto_data[1]) * 100
            
            print(f"\nPERFORMANCE COMPARISON:")
            print(f"Stocks ROI:             {stocks_roi:>11.2f}%")
            print(f"Crypto ROI:             {crypto_roi:>11.2f}%")
            
            better = "Stocks" if stocks_roi > crypto_roi else "Crypto"
            difference = abs(stocks_roi - crypto_roi)
            print(f"Better Performer:       {better:>12} (+{difference:.2f}%)")
    
    # Trading statistics
    c.execute('''SELECT COUNT(*) as total_txns,
                        SUM(CASE WHEN action = 'buy' THEN 1 ELSE 0 END) as buys,
                        SUM(CASE WHEN action = 'sell' THEN 1 ELSE 0 END) as sells,
                        SUM(CASE WHEN action = 'buy' THEN total_amount ELSE 0 END) as buy_volume,
                        SUM(CASE WHEN action = 'sell' THEN total_amount ELSE 0 END) as sell_volume
                 FROM portfolio_transactions''')
    
    stats = c.fetchone()
    if stats:
        total_txns, buys, sells, buy_volume, sell_volume = stats
        
        print(f"\nTRADING STATISTICS:")
        print(f"Total Transactions:     {total_txns:>12}")
        print(f"Buy Orders:             {buys:>12}")
        print(f"Sell Orders:            {sells:>12}")
        print(f"Total Buy Volume:       ${buy_volume:>11,.2f}")
        print(f"Total Sell Volume:      ${sell_volume:>11,.2f}")
        
        if buys > 0:
            avg_buy_size = buy_volume / buys
            print(f"Average Buy Size:       ${avg_buy_size:>11,.2f}")
    
    # Recent activity summary
    c.execute('''SELECT COUNT(*) FROM portfolio_transactions 
                 WHERE timestamp >= date('now', '-7 days')''')
    recent_activity = c.fetchone()[0]
    
    c.execute('''SELECT COUNT(*) FROM portfolio_transactions 
                 WHERE timestamp >= date('now', '-1 day')''')
    today_activity = c.fetchone()[0]
    
    print(f"\nRECENT ACTIVITY:")
    print(f"Last 7 days:            {recent_activity:>12} transactions")
    print(f"Today:                  {today_activity:>12} transactions")
    
    print("=" * 80)
    print(f"Dashboard generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    conn.close()

if __name__ == "__main__":
    show_portfolio_dashboard()