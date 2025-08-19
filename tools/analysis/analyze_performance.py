#!/usr/bin/env python3
"""
Análisis completo de performance del autotrader
Calcula P&L real, separando stocks y crypto
"""

import sqlite3
from collections import defaultdict
from datetime import datetime

def analyze_trading_performance():
    conn = sqlite3.connect('trading.db')
    c = conn.cursor()
    
    # Get all autotrader transactions
    c.execute('''SELECT symbol, action, quantity, price, timestamp, reason 
                 FROM autotrader_transactions 
                 ORDER BY timestamp ASC''')
    transactions = c.fetchall()
    
    print("=== ANÁLISIS DE PERFORMANCE DEL AUTOTRADER ===")
    print(f"Total transacciones: {len(transactions)}")
    print()
    
    # Separate by asset type
    stock_symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'PLTR', 'INTC', 'AMD']
    crypto_symbols = ['BTC', 'ETH', 'ADA', 'SOL', 'BNB', 'XRP', 'AVAX', 'DOT', 'LINK', 'DOGE']
    
    # Track positions and P&L
    stock_positions = defaultdict(list)  # symbol -> list of (action, qty, price, timestamp, reason)
    crypto_positions = defaultdict(list)
    
    for symbol, action, quantity, price, timestamp, reason in transactions:
        if symbol in stock_symbols:
            stock_positions[symbol].append((action, quantity, price, timestamp, reason))
        elif symbol in crypto_symbols:
            crypto_positions[symbol].append((action, quantity, price, timestamp, reason))
    
    def calculate_pnl(positions):
        """Calculate P&L for a set of positions using FIFO method"""
        total_pnl = 0
        symbol_stats = {}
        
        for symbol, txns in positions.items():
            buys = []
            sells = []
            
            for action, qty, price, timestamp, reason in txns:
                if action == 'buy':
                    buys.append((qty, price, timestamp, reason))
                else:
                    sells.append((qty, price, timestamp, reason))
            
            # Calculate P&L using FIFO
            symbol_pnl = 0
            remaining_buys = buys.copy()
            total_bought = sum(qty for qty, _, _, _ in buys)
            total_sold = sum(qty for qty, _, _, _ in sells)
            
            for sell_qty, sell_price, sell_time, sell_reason in sells:
                remaining_sell = sell_qty
                
                while remaining_sell > 0 and remaining_buys:
                    buy_qty, buy_price, buy_time, buy_reason = remaining_buys[0]
                    
                    if buy_qty <= remaining_sell:
                        # Use entire buy position
                        pnl = buy_qty * (sell_price - buy_price)
                        symbol_pnl += pnl
                        remaining_sell -= buy_qty
                        remaining_buys.pop(0)
                        
                        print(f"  {symbol}: Vendido {buy_qty:.4f} @ ${sell_price:.2f} (comprado @ ${buy_price:.2f}) = ${pnl:.2f}")
                    else:
                        # Partial sell
                        pnl = remaining_sell * (sell_price - buy_price)
                        symbol_pnl += pnl
                        remaining_buys[0] = (buy_qty - remaining_sell, buy_price, buy_time, buy_reason)
                        
                        print(f"  {symbol}: Vendido {remaining_sell:.4f} @ ${sell_price:.2f} (comprado @ ${buy_price:.2f}) = ${pnl:.2f}")
                        remaining_sell = 0
            
            total_pnl += symbol_pnl
            symbol_stats[symbol] = {
                'pnl': symbol_pnl,
                'total_bought': total_bought,
                'total_sold': total_sold,
                'remaining': total_bought - total_sold,
                'buy_volume': sum(qty * price for qty, price, _, _ in buys),
                'sell_volume': sum(qty * price for qty, price, _, _ in sells)
            }
        
        return total_pnl, symbol_stats
    
    # Analyze stocks
    print(" STOCKS PERFORMANCE:")
    print("-" * 60)
    stock_pnl, stock_stats = calculate_pnl(stock_positions)
    
    stock_buy_volume = 0
    stock_sell_volume = 0
    
    for symbol, stats in stock_stats.items():
        print(f"{symbol}:")
        print(f"  P&L: ${stats['pnl']:.2f}")
        print(f"  Comprado: {stats['total_bought']:.4f} (${stats['buy_volume']:.2f})")
        print(f"  Vendido: {stats['total_sold']:.4f} (${stats['sell_volume']:.2f})")
        print(f"  Restante: {stats['remaining']:.4f}")
        print()
        
        stock_buy_volume += stats['buy_volume']
        stock_sell_volume += stats['sell_volume']
    
    print(f"TOTAL STOCKS P&L: ${stock_pnl:.2f}")
    print(f"Capital invertido: ${stock_buy_volume:.2f}")
    print(f"Capital recuperado: ${stock_sell_volume:.2f}")
    print(f"Capital en posiciones: ${stock_buy_volume - stock_sell_volume:.2f}")
    print()
    
    # Analyze crypto
    print(" CRYPTO PERFORMANCE:")
    print("-" * 60)
    crypto_pnl, crypto_stats = calculate_pnl(crypto_positions)
    
    crypto_buy_volume = 0
    crypto_sell_volume = 0
    
    for symbol, stats in crypto_stats.items():
        print(f"{symbol}:")
        print(f"  P&L: ${stats['pnl']:.2f}")
        print(f"  Comprado: {stats['total_bought']:.4f} (${stats['buy_volume']:.2f})")
        print(f"  Vendido: {stats['total_sold']:.4f} (${stats['sell_volume']:.2f})")
        print(f"  Restante: {stats['remaining']:.4f}")
        print()
        
        crypto_buy_volume += stats['buy_volume']
        crypto_sell_volume += stats['sell_volume']
    
    print(f"TOTAL CRYPTO P&L: ${crypto_pnl:.2f}")
    print(f"Capital invertido: ${crypto_buy_volume:.2f}")
    print(f"Capital recuperado: ${crypto_sell_volume:.2f}")
    print(f"Capital en posiciones: ${crypto_buy_volume - crypto_sell_volume:.2f}")
    print()
    
    # Overall summary
    print(" RESUMEN GENERAL:")
    print("-" * 60)
    total_pnl = stock_pnl + crypto_pnl
    total_invested = stock_buy_volume + crypto_buy_volume
    total_recovered = stock_sell_volume + crypto_sell_volume
    total_in_positions = total_invested - total_recovered
    
    print(f"P&L Total Realizado: ${total_pnl:.2f}")
    print(f"Capital Total Invertido: ${total_invested:.2f}")
    print(f"Capital Recuperado: ${total_recovered:.2f}")
    print(f"Capital en Posiciones: ${total_in_positions:.2f}")
    print(f"ROI Realizado: {(total_pnl/total_invested)*100:.2f}%" if total_invested > 0 else "ROI: N/A")
    
    # Win rate analysis
    winning_trades = sum(1 for stats in {**stock_stats, **crypto_stats}.values() if stats['pnl'] > 0)
    total_completed_trades = len([s for s in {**stock_stats, **crypto_stats}.values() if s['total_sold'] > 0])
    win_rate = (winning_trades / total_completed_trades) * 100 if total_completed_trades > 0 else 0
    
    print(f"Win Rate: {win_rate:.1f}% ({winning_trades}/{total_completed_trades})")
    
    conn.close()
    
    return {
        'total_pnl': total_pnl,
        'stock_pnl': stock_pnl,
        'crypto_pnl': crypto_pnl,
        'total_invested': total_invested,
        'stock_invested': stock_buy_volume,
        'crypto_invested': crypto_buy_volume,
        'win_rate': win_rate,
        'stock_stats': stock_stats,
        'crypto_stats': crypto_stats
    }

if __name__ == "__main__":
    analyze_trading_performance()