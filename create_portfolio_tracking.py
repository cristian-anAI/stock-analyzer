#!/usr/bin/env python3
"""
Create comprehensive portfolio tracking system
Separate stocks and crypto with fixed initial capital
"""

import sqlite3
from datetime import datetime

def create_portfolio_tables():
    conn = sqlite3.connect('trading.db')
    c = conn.cursor()
    
    # Create portfolio configuration table
    c.execute('''DROP TABLE IF EXISTS portfolio_config''')
    c.execute('''CREATE TABLE portfolio_config (
        id INTEGER PRIMARY KEY,
        type TEXT NOT NULL, -- 'stocks' or 'crypto'
        initial_capital REAL NOT NULL,
        current_capital REAL NOT NULL,
        available_cash REAL NOT NULL,
        invested_amount REAL NOT NULL,
        total_pnl REAL NOT NULL DEFAULT 0,
        win_rate REAL NOT NULL DEFAULT 0,
        total_trades INTEGER NOT NULL DEFAULT 0,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Create detailed transactions table
    c.execute('''DROP TABLE IF EXISTS portfolio_transactions''')
    c.execute('''CREATE TABLE portfolio_transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        portfolio_type TEXT NOT NULL, -- 'stocks' or 'crypto'
        symbol TEXT NOT NULL,
        action TEXT NOT NULL, -- 'buy' or 'sell'
        quantity REAL NOT NULL,
        price REAL NOT NULL,
        total_amount REAL NOT NULL,
        fees REAL DEFAULT 0,
        buy_reason TEXT,
        sell_reason TEXT,
        score REAL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        source TEXT DEFAULT 'autotrader' -- 'autotrader' or 'manual'
    )''')
    
    # Create portfolio positions table (current holdings)
    c.execute('''DROP TABLE IF EXISTS portfolio_positions''')
    c.execute('''CREATE TABLE portfolio_positions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        portfolio_type TEXT NOT NULL,
        symbol TEXT NOT NULL UNIQUE,
        quantity REAL NOT NULL,
        avg_entry_price REAL NOT NULL,
        total_invested REAL NOT NULL,
        current_price REAL,
        current_value REAL,
        unrealized_pnl REAL,
        unrealized_pnl_percent REAL,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Create portfolio performance snapshots
    c.execute('''DROP TABLE IF EXISTS portfolio_snapshots''')
    c.execute('''CREATE TABLE portfolio_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        portfolio_type TEXT NOT NULL,
        date TEXT NOT NULL,
        total_capital REAL NOT NULL,
        available_cash REAL NOT NULL,
        invested_amount REAL NOT NULL,
        portfolio_value REAL NOT NULL,
        total_pnl REAL NOT NULL,
        day_change REAL,
        win_rate REAL,
        total_trades INTEGER
    )''')
    
    # Initialize with fixed capital amounts
    initial_stock_capital = 100000.00  # $100k for stocks
    initial_crypto_capital = 50000.00  # $50k for crypto
    
    # Insert initial portfolio configurations
    c.execute('''INSERT INTO portfolio_config 
                 (type, initial_capital, current_capital, available_cash, invested_amount) 
                 VALUES (?, ?, ?, ?, ?)''', 
              ('stocks', initial_stock_capital, initial_stock_capital, initial_stock_capital, 0))
    
    c.execute('''INSERT INTO portfolio_config 
                 (type, initial_capital, current_capital, available_cash, invested_amount) 
                 VALUES (?, ?, ?, ?, ?)''', 
              ('crypto', initial_crypto_capital, initial_crypto_capital, initial_crypto_capital, 0))
    
    print(f" Created portfolio tracking system:")
    print(f"   - Stocks initial capital: ${initial_stock_capital:,.2f}")
    print(f"   - Crypto initial capital: ${initial_crypto_capital:,.2f}")
    print(f"   - Total initial capital: ${initial_stock_capital + initial_crypto_capital:,.2f}")
    
    conn.commit()
    conn.close()

def migrate_existing_transactions():
    """Migrate existing autotrader_transactions to new portfolio system"""
    conn = sqlite3.connect('trading.db')
    c = conn.cursor()
    
    # Get all existing transactions
    c.execute('''SELECT symbol, action, quantity, price, timestamp, reason 
                 FROM autotrader_transactions 
                 ORDER BY timestamp ASC''')
    transactions = c.fetchall()
    
    stock_symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'PLTR', 'INTC', 'AMD']
    crypto_symbols = ['BTC', 'ETH', 'ADA', 'SOL', 'BNB', 'XRP', 'AVAX', 'DOT', 'LINK', 'DOGE']
    
    print(f"\n Migrating {len(transactions)} existing transactions...")
    
    for symbol, action, quantity, price, timestamp, reason in transactions:
        # Determine portfolio type
        if symbol in stock_symbols:
            portfolio_type = 'stocks'
        elif symbol in crypto_symbols:
            portfolio_type = 'crypto'
        else:
            portfolio_type = 'stocks'  # Default
        
        total_amount = quantity * price
        
        # Determine buy/sell reason
        buy_reason = None
        sell_reason = None
        if action == 'buy':
            buy_reason = reason
        else:
            sell_reason = reason
        
        # Insert into new portfolio transactions
        c.execute('''INSERT INTO portfolio_transactions 
                     (portfolio_type, symbol, action, quantity, price, total_amount, 
                      buy_reason, sell_reason, timestamp, source) 
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (portfolio_type, symbol, action, quantity, price, total_amount,
                   buy_reason, sell_reason, timestamp, 'autotrader'))
    
    print(f" Migrated all transactions to new portfolio system")
    
    conn.commit()
    conn.close()

def calculate_portfolio_positions():
    """Calculate current positions and P&L for both portfolios"""
    conn = sqlite3.connect('trading.db')
    c = conn.cursor()
    
    # Clear existing positions
    c.execute('DELETE FROM portfolio_positions')
    
    # Calculate positions for each portfolio type
    for portfolio_type in ['stocks', 'crypto']:
        c.execute('''SELECT symbol, action, quantity, price, total_amount
                     FROM portfolio_transactions 
                     WHERE portfolio_type = ? 
                     ORDER BY timestamp ASC''', (portfolio_type,))
        
        transactions = c.fetchall()
        positions = {}
        
        for symbol, action, quantity, price, total_amount in transactions:
            if symbol not in positions:
                positions[symbol] = {'quantity': 0, 'total_invested': 0, 'total_quantity_bought': 0}
            
            if action == 'buy':
                positions[symbol]['quantity'] += quantity
                positions[symbol]['total_invested'] += total_amount
                positions[symbol]['total_quantity_bought'] += quantity
            else:  # sell
                positions[symbol]['quantity'] -= quantity
                # Calculate cost basis reduction (FIFO)
                if positions[symbol]['total_quantity_bought'] > 0:
                    cost_per_share = positions[symbol]['total_invested'] / positions[symbol]['total_quantity_bought']
                    positions[symbol]['total_invested'] -= quantity * cost_per_share
        
        # Insert current positions
        for symbol, pos in positions.items():
            if pos['quantity'] > 0.0001:  # Only if we still hold the position
                avg_entry_price = pos['total_invested'] / pos['quantity'] if pos['quantity'] > 0 else 0
                
                c.execute('''INSERT INTO portfolio_positions 
                             (portfolio_type, symbol, quantity, avg_entry_price, total_invested) 
                             VALUES (?, ?, ?, ?, ?)''',
                          (portfolio_type, symbol, pos['quantity'], avg_entry_price, pos['total_invested']))
    
    print(f" Calculated portfolio positions")
    
    conn.commit()
    conn.close()

def update_portfolio_summary():
    """Update portfolio configuration with current stats"""
    conn = sqlite3.connect('trading.db')
    c = conn.cursor()
    
    for portfolio_type in ['stocks', 'crypto']:
        # Calculate invested amount
        c.execute('''SELECT SUM(total_invested) FROM portfolio_positions 
                     WHERE portfolio_type = ?''', (portfolio_type,))
        invested_result = c.fetchone()
        invested_amount = invested_result[0] if invested_result[0] else 0
        
        # Calculate total P&L from completed trades
        c.execute('''SELECT SUM(
                        CASE 
                            WHEN action = 'sell' THEN total_amount
                            WHEN action = 'buy' THEN -total_amount
                        END
                     ) FROM portfolio_transactions 
                     WHERE portfolio_type = ?''', (portfolio_type,))
        pnl_result = c.fetchone()
        total_pnl = pnl_result[0] if pnl_result[0] else 0
        
        # Count trades
        c.execute('''SELECT COUNT(DISTINCT symbol) FROM portfolio_transactions 
                     WHERE portfolio_type = ? AND action = 'sell' ''', (portfolio_type,))
        trades_result = c.fetchone()
        total_trades = trades_result[0] if trades_result[0] else 0
        
        # Get initial capital
        c.execute('''SELECT initial_capital FROM portfolio_config 
                     WHERE type = ?''', (portfolio_type,))
        initial_capital = c.fetchone()[0]
        
        # Calculate available cash (simplified)
        available_cash = initial_capital - invested_amount + total_pnl
        current_capital = available_cash + invested_amount
        
        # Update portfolio config
        c.execute('''UPDATE portfolio_config 
                     SET current_capital = ?, available_cash = ?, invested_amount = ?, 
                         total_pnl = ?, total_trades = ?, last_updated = ?
                     WHERE type = ?''',
                  (current_capital, available_cash, invested_amount, total_pnl, 
                   total_trades, datetime.now().isoformat(), portfolio_type))
    
    print(f" Updated portfolio summaries")
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    print("=== CREANDO SISTEMA DE TRACKING DE PORTFOLIOS ===")
    
    create_portfolio_tables()
    migrate_existing_transactions()
    calculate_portfolio_positions()
    update_portfolio_summary()
    
    print(f"\n Sistema de portfolios creado exitosamente!")
    print(f"Ahora tienes tracking completo de:")
    print(f"   Stocks portfolio ($100,000 inicial)")
    print(f"   Crypto portfolio ($50,000 inicial)")
    print(f"   Transacciones detalladas con razones")
    print(f"   Posiciones actuales y P&L")
    print(f"   Tracking de capital y performance")