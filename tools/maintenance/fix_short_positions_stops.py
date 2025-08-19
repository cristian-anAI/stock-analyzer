#!/usr/bin/env python3
"""
FIX SHORT POSITIONS - Add missing stop losses and take profits
"""

import sqlite3
import sys
import os
from datetime import datetime

# Add the src directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def fix_short_stops():
    """Add stop losses and take profits to existing SHORT positions"""
    
    conn = sqlite3.connect('trading.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("=== FIXING SHORT POSITION STOPS ===")
    print(f"Timestamp: {datetime.now()}")
    print()
    
    # Get SHORT positions without stops
    cursor.execute("""
        SELECT id, symbol, entry_price, current_price
        FROM positions 
        WHERE position_side = 'SHORT' 
        AND (stop_loss_updated IS NULL OR stop_loss_updated = 0)
    """)
    
    positions = cursor.fetchall()
    
    if not positions:
        print("No SHORT positions need stop loss updates")
        return
    
    print(f"Found {len(positions)} SHORT positions without stops:")
    print()
    
    for pos in positions:
        position_id = pos['id']
        symbol = pos['symbol']
        entry_price = pos['entry_price']
        current_price = pos['current_price'] or entry_price
        
        # Calculate stop loss (8% price rise = loss)
        stop_loss_price = entry_price * 1.08
        
        # Calculate take profit (5% price fall = profit)  
        take_profit_price = entry_price * 0.95
        
        print(f"  {symbol}:")
        print(f"    Entry Price: ${entry_price:.4f}")
        print(f"    Stop Loss: ${stop_loss_price:.4f} (+8%)")
        print(f"    Take Profit: ${take_profit_price:.4f} (-5%)")
        
        # Update the position
        cursor.execute("""
            UPDATE positions 
            SET stop_loss_updated = ?, 
                take_profit_updated = ?,
                updated_at = ?
            WHERE id = ?
        """, (stop_loss_price, take_profit_price, datetime.now().isoformat(), position_id))
        
        print(f"    -> Updated stops for {symbol}")
        print()
    
    conn.commit()
    
    # Verify the updates
    print("=== VERIFICATION ===")
    cursor.execute("""
        SELECT symbol, entry_price, stop_loss_updated, take_profit_updated
        FROM positions 
        WHERE position_side = 'SHORT'
    """)
    
    updated_positions = cursor.fetchall()
    
    for pos in updated_positions:
        symbol = pos['symbol']
        entry = pos['entry_price']
        stop = pos['stop_loss_updated']
        tp = pos['take_profit_updated']
        
        print(f"  {symbol}: Entry=${entry:.4f}, Stop=${stop:.4f}, TP=${tp:.4f}")
    
    conn.close()
    print()
    print("-> All SHORT positions now have stop losses and take profits!")

if __name__ == "__main__":
    fix_short_stops()