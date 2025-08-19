#!/usr/bin/env python3
"""
Debug the SHORT alerts endpoint error
"""

import sys
import os
from datetime import datetime

# Add the src directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.api.database.database import db_manager

def debug_alerts():
    """Debug the alerts function step by step"""
    
    try:
        alerts = []
        
        print("Step 1: Get SHORT positions...")
        positions = db_manager.execute_query("""
            SELECT p.symbol, p.entry_price, p.current_price, p.pnl_percent,
                   p.stop_loss_updated, p.created_at,
                   c.score as current_score, c.change_percent
            FROM positions p
            LEFT JOIN cryptos c ON p.symbol = c.symbol
            WHERE p.position_side = 'SHORT'
        """)
        
        print(f"Found {len(positions)} positions")
        
        print("\nStep 2: Process each position...")
        for pos in positions:
            symbol = pos['symbol']
            entry_price = pos['entry_price']
            current_price = pos['current_price'] or entry_price
            pnl_percent = pos['pnl_percent'] or 0
            stop_loss = pos['stop_loss_updated'] or 0
            current_score = pos['current_score'] or 0
            created_at = datetime.fromisoformat(pos['created_at'])
            days_held = (datetime.now() - created_at).days
            
            print(f"  {symbol}: entry={entry_price}, current={current_price}, pnl={pnl_percent}%")
            
            # Test each alert condition
            if pnl_percent < -6:
                print(f"    HIGH LOSS alert for {symbol}")
            
            if current_score >= 4.0:
                print(f"    SCORE IMPROVED alert for {symbol}")
            
            if current_score >= 3.0:
                print(f"    Score improved alert for {symbol}")
            
            if days_held > 7:
                print(f"    Long hold alert for {symbol}")
            
            # Near stop loss
            if stop_loss > 0 and current_price > 0:
                distance_to_stop = ((stop_loss - current_price) / current_price) * 100
                if distance_to_stop < 2:
                    print(f"    Near stop loss alert for {symbol}")
        
        print("\nStep 3: Market condition alerts...")
        btc_data = db_manager.execute_query("SELECT change_percent FROM cryptos WHERE symbol = 'BTC-USD' LIMIT 1")
        if btc_data:
            print(f"  BTC change: {btc_data[0]['change_percent']}%")
            if btc_data[0]['change_percent'] > 3:
                print("  BTC uptrend alert")
        
        print("\nStep 4: SHORT exposure check...")
        exposure_result = db_manager.execute_query("""
            SELECT COALESCE(SUM(quantity * entry_price), 0) as total
            FROM positions WHERE position_side = 'SHORT'
        """)
        
        total_short_exposure = exposure_result[0]['total'] if exposure_result else 0
        print(f"  Total SHORT exposure: ${total_short_exposure:.2f}")
        
        if total_short_exposure > 100000:
            print("  High exposure alert")
        
        print("\nDebug completed successfully!")
        
    except Exception as e:
        print(f"Error at step: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_alerts()