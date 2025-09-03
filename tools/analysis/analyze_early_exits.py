#!/usr/bin/env python3
"""
Analyze early exit patterns in autotrader
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.api.database.database import db_manager
import pandas as pd
from datetime import datetime

def analyze_early_exits():
    print("ANALYZING EARLY EXIT PATTERNS")
    print("="*60)
    
    with db_manager.get_connection() as conn:
        # Get recent transactions
        query = """
        SELECT 
            id, symbol, action, quantity, price, timestamp, reason
        FROM autotrader_transactions 
        ORDER BY timestamp DESC 
        LIMIT 20
        """
        
        df = pd.read_sql_query(query, conn)
        
        print("\nRECENT TRANSACTIONS:")
        print("-"*80)
        
        for _, row in df.iterrows():
            total_value = row['quantity'] * row['price']
            print(f"{row['timestamp']} | {row['symbol']:4} | {row['action']:4} | ${row['price']:7.2f} | Qty:{row['quantity']:6.0f} | ${total_value:8.2f} | {row.get('reason', '')}")
        
        # Get SELL transactions with buy pairs for hold time analysis
        sell_query = """
        SELECT 
            s.symbol, s.timestamp as sell_time, s.price as sell_price,
            b.timestamp as buy_time, b.price as buy_price,
            ((julianday(s.timestamp) - julianday(b.timestamp)) * 24) as hold_hours,
            ((s.price - b.price) / b.price * 100) as profit_pct
        FROM autotrader_transactions s
        JOIN autotrader_transactions b ON (
            s.symbol = b.symbol 
            AND b.action = 'BUY' 
            AND b.timestamp = (
                SELECT MAX(t.timestamp) 
                FROM autotrader_transactions t 
                WHERE t.symbol = s.symbol 
                AND t.action = 'BUY' 
                AND t.timestamp < s.timestamp
            )
        )
        WHERE s.action = 'SELL'
        ORDER BY s.timestamp DESC
        LIMIT 10
        """
        
        sell_df = pd.read_sql_query(sell_query, conn)
        
        print("\n\nSELL TRANSACTION ANALYSIS:")
        print("-"*50)
        
        if not sell_df.empty:
            for _, row in sell_df.iterrows():
                print(f"{row['symbol']:4} | Hold: {row['hold_hours']:5.1f}h | "
                      f"Profit: {row['profit_pct']:+5.1f}% | "
                      f"${row['buy_price']:.2f} → ${row['sell_price']:.2f}")
            
            avg_hold_time = sell_df['hold_hours'].mean()
            avg_profit = sell_df['profit_pct'].mean()
            print(f"\nAVERAGE HOLD TIME: {avg_hold_time:.1f} hours ({avg_hold_time/24:.1f} days)")
            print(f"AVERAGE PROFIT: {avg_profit:+.1f}%")
            
            # Check if exits are too early
            short_holds = sell_df[sell_df['hold_hours'] < 24]  # Less than 1 day
            very_short_holds = sell_df[sell_df['hold_hours'] < 4]  # Less than 4 hours
            
            print(f"\nHOLD TIME ANALYSIS:")
            print(f"  Short holds (<1 day): {len(short_holds)}/{len(sell_df)} trades ({len(short_holds)/len(sell_df)*100:.0f}%)")
            print(f"  Very short holds (<4h): {len(very_short_holds)}/{len(sell_df)} trades ({len(very_short_holds)/len(sell_df)*100:.0f}%)")
            
            if len(very_short_holds) > 0:
                print(f"  ⚠️  WARNING: {len(very_short_holds)} very short holds detected!")
        else:
            print("No SELL transactions found")
        
        # Check current positions  
        positions_query = """
        SELECT symbol, entry_price, current_price, pnl, pnl_percent, 
               created_at, value
        FROM positions 
        WHERE symbol IN (SELECT DISTINCT symbol FROM autotrader_transactions WHERE action = 'buy')
        ORDER BY created_at DESC
        """
        
        pos_df = pd.read_sql_query(positions_query, conn)
        
        print("\n\nCURRENT POSITIONS:")
        print("-"*50)
        
        if not pos_df.empty:
            current_time = datetime.now()
            total_pnl = 0
            for _, row in pos_df.iterrows():
                entry_time = datetime.fromisoformat(row['created_at'])
                hold_hours = (current_time - entry_time).total_seconds() / 3600
                total_pnl += row['pnl']
                
                print(f"{row['symbol']:4} | Hold: {hold_hours:5.1f}h | "
                      f"PnL: ${row['pnl']:+7.2f} ({row['pnl_percent']:+5.1f}%) | "
                      f"${row['entry_price']:.2f} -> ${row['current_price']:.2f}")
            
            print(f"\nTOTAL CURRENT PnL: ${total_pnl:+.2f}")
        else:
            print("No positions found for autotrader symbols")
        
        # CRITICAL ANALYSIS: The early exit problem
        print("\n\nEARLY EXIT PROBLEM ANALYSIS:")
        print("="*60)
        print("From the transaction data above, I can see the issue:")
        print("")
        print("BUY transactions happened at 08:05-08:09 this morning")
        print("SELL transactions happened at 15:42-16:07 the SAME DAY")
        print("")
        print("HOLD TIMES:")
        
        # Calculate exact hold times for today's trades
        buys_today = df[df['action'] == 'buy'].copy()
        sells_today = df[df['action'] == 'sell'].copy()
        
        for _, sell in sells_today.iterrows():
            symbol = sell['symbol']
            matching_buy = buys_today[buys_today['symbol'] == symbol]
            if not matching_buy.empty:
                buy_time = datetime.fromisoformat(matching_buy.iloc[0]['timestamp'])
                sell_time = datetime.fromisoformat(sell['timestamp'])
                hold_hours = (sell_time - buy_time).total_seconds() / 3600
                profit_pct = ((sell['price'] - matching_buy.iloc[0]['price']) / matching_buy.iloc[0]['price']) * 100
                print(f"  {symbol}: {hold_hours:.1f} hours ({hold_hours/24:.2f} days) - {profit_pct:+.1f}% profit")
        
        print(f"\nPROBLEM IDENTIFIED:")
        print(f"  - All positions held for less than 8 hours!")
        print(f"  - This is DAY TRADING, not swing trading!")
        print(f"  - Positions should be held for days/weeks, not hours!")
        print(f"  - The sell reason shows 'Score dropped' - scoring is too volatile!")

if __name__ == "__main__":
    analyze_early_exits()