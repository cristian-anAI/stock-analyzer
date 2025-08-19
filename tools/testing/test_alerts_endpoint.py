#!/usr/bin/env python3
"""
Test the alerts endpoint in isolation
"""

import sys
import os
from datetime import datetime

# Add the src directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.api.database.database import db_manager

def test_alerts_minimal():
    """Test a minimal version of the alerts endpoint"""
    
    try:
        alerts = []
        
        # Get current SHORT positions - this is the first thing the endpoint does
        print("Getting SHORT positions...")
        positions = db_manager.execute_query("""
            SELECT p.symbol, p.entry_price, p.current_price, p.pnl_percent,
                   p.stop_loss_updated, p.created_at,
                   c.score as current_score, c.change_percent
            FROM positions p
            LEFT JOIN cryptos c ON p.symbol = c.symbol
            WHERE p.position_side = 'SHORT'
        """)
        
        print(f"Found {len(positions)} positions")
        
        # Check if there are NULL values that might be causing type errors
        for i, pos in enumerate(positions):
            print(f"\nPosition {i+1}: {pos['symbol']}")
            for key, value in pos.items():
                print(f"  {key}: {value} ({type(value)})")
                
            # Try to replicate the operations that might fail
            try:
                symbol = pos['symbol']
                entry_price = pos['entry_price'] 
                current_price = pos['current_price'] or entry_price
                pnl_percent = pos['pnl_percent'] or 0
                stop_loss = pos['stop_loss_updated'] or 0
                current_score = pos['current_score'] or 0
                
                # This might fail if created_at is not proper ISO format
                created_at = datetime.fromisoformat(pos['created_at'])
                days_held = (datetime.now() - created_at).days
                
                print(f"  Processed values: entry={entry_price}, current={current_price}, score={current_score}")
                
                # Test arithmetic operations that might fail
                if current_price and entry_price:
                    price_change = ((current_price - entry_price) / entry_price) * 100
                    print(f"  Price change: {price_change:.2f}%")
                
                if stop_loss > 0 and current_price > 0:
                    distance_to_stop = ((stop_loss - current_price) / current_price) * 100
                    print(f"  Distance to stop: {distance_to_stop:.2f}%")
                
            except Exception as e:
                print(f"  ERROR processing position {symbol}: {e}")
                import traceback
                traceback.print_exc()
                return False
                
        print("\nAll positions processed successfully!")
        return True
        
    except Exception as e:
        print(f"Error in minimal test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_alerts_minimal()
    print(f"\nTest result: {'PASSED' if success else 'FAILED'}")