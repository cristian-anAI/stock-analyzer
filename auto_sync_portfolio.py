#!/usr/bin/env python3
"""
Auto Sync Portfolio - Reconcile PortfolioManager with actual database state
"""

import sys
import os
from datetime import datetime

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from api.services.portfolio_manager import portfolio_manager
from api.database.database import db_manager

def calculate_realized_pnl_from_transactions(portfolio_type):
    """Calculate realized P&L from completed transactions"""
    
    # Get all transactions for this portfolio type
    transactions = db_manager.execute_query("""
        SELECT symbol, action, quantity, price, total_amount, timestamp
        FROM portfolio_transactions 
        WHERE portfolio_type = ? AND source = 'autotrader'
        ORDER BY symbol, timestamp ASC
    """, (portfolio_type,))
    
    # Track positions and calculate realized P&L
    symbol_positions = {}  # {symbol: {'quantity': X, 'cost_basis': Y}}
    realized_pnl = 0.0
    
    for txn in transactions:
        symbol = txn['symbol']
        action = txn['action']
        quantity = txn['quantity']
        price = txn['price']
        total_amount = txn['total_amount']
        
        if symbol not in symbol_positions:
            symbol_positions[symbol] = {'quantity': 0, 'cost_basis': 0}
        
        if action == 'buy':
            # Add to position
            old_quantity = symbol_positions[symbol]['quantity']
            old_cost_basis = symbol_positions[symbol]['cost_basis']
            
            new_quantity = old_quantity + quantity
            new_cost_basis = old_cost_basis + total_amount
            
            symbol_positions[symbol]['quantity'] = new_quantity
            symbol_positions[symbol]['cost_basis'] = new_cost_basis
            
        elif action == 'sell':
            # Calculate realized P&L for this sell
            if symbol_positions[symbol]['quantity'] > 0:
                avg_buy_price = symbol_positions[symbol]['cost_basis'] / symbol_positions[symbol]['quantity']
                sell_pnl = (price - avg_buy_price) * quantity
                realized_pnl += sell_pnl
                
                # Reduce position
                symbol_positions[symbol]['quantity'] -= quantity
                symbol_positions[symbol]['cost_basis'] -= avg_buy_price * quantity
                
                # Clean up if quantity is zero
                if abs(symbol_positions[symbol]['quantity']) < 0.0001:
                    symbol_positions[symbol] = {'quantity': 0, 'cost_basis': 0}
    
    return realized_pnl

def auto_sync_portfolio():
    """Auto-sync PortfolioManager with actual database state"""
    
    print("=" * 80)
    print("    AUTO-SYNC PORTFOLIO - RECONCILIATION")
    print("=" * 80)
    
    # Constants
    INITIAL_STOCKS_CAPITAL = 70000.0
    INITIAL_CRYPTO_CAPITAL = 30000.0
    
    try:
        # Step 1: Get actual positions from database
        print("\n[1] CALCULATING ACTUAL INVESTED CAPITAL FROM POSITIONS...")
        
        positions_query = """
            SELECT type, SUM(COALESCE(value, 0)) as total_value, SUM(COALESCE(pnl, 0)) as total_pnl, COUNT(*) as count
            FROM positions 
            WHERE source = 'autotrader'
            GROUP BY type
        """
        positions_data = db_manager.execute_query(positions_query)
        
        actual_stocks_invested = 0
        actual_crypto_invested = 0
        actual_stocks_pnl_unrealized = 0
        actual_crypto_pnl_unrealized = 0
        
        for pos in positions_data:
            if pos['type'] == 'stock':
                actual_stocks_invested = pos['total_value'] or 0
                actual_stocks_pnl_unrealized = pos['total_pnl'] or 0
                print(f"   STOCKS: ${actual_stocks_invested:,.0f} invested, ${actual_stocks_pnl_unrealized:,.2f} unrealized P&L, {pos['count']} positions")
            elif pos['type'] == 'crypto':
                actual_crypto_invested = pos['total_value'] or 0
                actual_crypto_pnl_unrealized = pos['total_pnl'] or 0
                print(f"   CRYPTO: ${actual_crypto_invested:,.0f} invested, ${actual_crypto_pnl_unrealized:,.2f} unrealized P&L, {pos['count']} positions")
        
        # Step 2: Calculate realized P&L from transactions
        print("\n[2] CALCULATING REALIZED P&L FROM TRANSACTIONS...")
        
        stocks_realized_pnl = calculate_realized_pnl_from_transactions('stocks')
        crypto_realized_pnl = calculate_realized_pnl_from_transactions('crypto')
        
        print(f"   STOCKS realized P&L: ${stocks_realized_pnl:,.2f}")
        print(f"   CRYPTO realized P&L: ${crypto_realized_pnl:,.2f}")
        
        # Step 3: Calculate available cash
        print("\n[3] CALCULATING AVAILABLE CASH...")
        
        stocks_available_cash = INITIAL_STOCKS_CAPITAL - actual_stocks_invested + stocks_realized_pnl
        crypto_available_cash = INITIAL_CRYPTO_CAPITAL - actual_crypto_invested + crypto_realized_pnl
        
        print(f"   STOCKS: ${INITIAL_STOCKS_CAPITAL:,.0f} initial - ${actual_stocks_invested:,.0f} invested + ${stocks_realized_pnl:,.2f} realized = ${stocks_available_cash:,.2f} available")
        print(f"   CRYPTO: ${INITIAL_CRYPTO_CAPITAL:,.0f} initial - ${actual_crypto_invested:,.0f} invested + ${crypto_realized_pnl:,.2f} realized = ${crypto_available_cash:,.2f} available")
        
        # Step 4: Update portfolio_config table
        print("\n[4] UPDATING PORTFOLIO_CONFIG TABLE...")
        
        # Update stocks config
        stocks_total_pnl = stocks_realized_pnl + actual_stocks_pnl_unrealized
        stocks_current_capital = stocks_available_cash + actual_stocks_invested
        
        db_manager.execute_update("""
            UPDATE portfolio_config 
            SET current_capital = ?, available_cash = ?, invested_amount = ?, total_pnl = ?, last_updated = ?
            WHERE type = 'stocks'
        """, (stocks_current_capital, stocks_available_cash, actual_stocks_invested, stocks_total_pnl, datetime.now().isoformat()))
        
        # Update crypto config
        crypto_total_pnl = crypto_realized_pnl + actual_crypto_pnl_unrealized
        crypto_current_capital = crypto_available_cash + actual_crypto_invested
        
        db_manager.execute_update("""
            UPDATE portfolio_config 
            SET current_capital = ?, available_cash = ?, invested_amount = ?, total_pnl = ?, last_updated = ?
            WHERE type = 'crypto'
        """, (crypto_current_capital, crypto_available_cash, actual_crypto_invested, crypto_total_pnl, datetime.now().isoformat()))
        
        print(f"   UPDATED stocks config: Current=${stocks_current_capital:,.2f}, Cash=${stocks_available_cash:,.2f}, Invested=${actual_stocks_invested:,.2f}, P&L=${stocks_total_pnl:,.2f}")
        print(f"   UPDATED crypto config: Current=${crypto_current_capital:,.2f}, Cash=${crypto_available_cash:,.2f}, Invested=${actual_crypto_invested:,.2f}, P&L=${crypto_total_pnl:,.2f}")
        
        # Step 5: Update portfolio_state table 
        print("\n[5] UPDATING PORTFOLIO_STATE TABLE...")
        
        # Clear old state and insert new
        db_manager.execute_update("DELETE FROM portfolio_state")
        db_manager.execute_insert("""
            INSERT INTO portfolio_state (
                date, liquid_capital_stocks, liquid_capital_crypto,
                invested_capital_stocks, invested_capital_crypto,
                total_pnl_stocks, total_pnl_crypto,
                total_positions_stocks, total_positions_crypto
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            stocks_available_cash, crypto_available_cash,
            actual_stocks_invested, actual_crypto_invested,
            stocks_total_pnl, crypto_total_pnl,
            len([p for p in positions_data if p['type'] == 'stock']),
            len([p for p in positions_data if p['type'] == 'crypto'])
        ))
        
        print("   UPDATED portfolio_state with current values")
        
        # Step 6: Reset PortfolioManager to load new state
        print("\n[6] RESETTING PORTFOLIO MANAGER...")
        
        portfolio_manager.reset_portfolio()
        
        # Verify sync
        new_summary = portfolio_manager.get_portfolio_summary()
        print(f"   NEW PM STATE:")
        print(f"     Stocks: Liquid=${new_summary['stocks']['liquid_capital']:,.2f}, Invested=${new_summary['stocks']['invested_capital']:,.2f}, P&L=${new_summary['stocks']['total_pnl']:,.2f}")
        print(f"     Crypto: Liquid=${new_summary['crypto']['liquid_capital']:,.2f}, Invested=${new_summary['crypto']['invested_capital']:,.2f}, P&L=${new_summary['crypto']['total_pnl']:,.2f}")
        
        # Step 7: Summary
        print("\n[7] SYNC COMPLETED SUCCESSFULLY!")
        print("=" * 50)
        print(f"STOCKS PORTFOLIO:")
        print(f"  Available Cash: ${stocks_available_cash:,.2f}")
        print(f"  Invested Capital: ${actual_stocks_invested:,.2f}")
        print(f"  Total P&L: ${stocks_total_pnl:,.2f} (${stocks_realized_pnl:,.2f} realized + ${actual_stocks_pnl_unrealized:,.2f} unrealized)")
        
        print(f"\nCRYPTO PORTFOLIO:")
        print(f"  Available Cash: ${crypto_available_cash:,.2f}")
        print(f"  Invested Capital: ${actual_crypto_invested:,.2f}")
        print(f"  Total P&L: ${crypto_total_pnl:,.2f} (${crypto_realized_pnl:,.2f} realized + ${actual_crypto_pnl_unrealized:,.2f} unrealized)")
        
        print(f"\nTOTALS:")
        total_capital = stocks_current_capital + crypto_current_capital
        total_pnl = stocks_total_pnl + crypto_total_pnl
        print(f"  Total Portfolio Value: ${total_capital:,.2f}")
        print(f"  Total P&L: ${total_pnl:,.2f}")
        print(f"  ROI: {(total_pnl / (INITIAL_STOCKS_CAPITAL + INITIAL_CRYPTO_CAPITAL)) * 100:.2f}%")
        
        return True
        
    except Exception as e:
        print(f"\nERROR during auto-sync: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("AUTO-SYNC PORTFOLIO - Reconciling PortfolioManager with database")
    print("This will fix discrepancies between in-memory state and actual positions")
    
    confirm = input("\nProceed with auto-sync? (y/N): ").lower()
    
    if confirm != 'y':
        print("Operation cancelled")
    else:
        success = auto_sync_portfolio()
        if success:
            print("\nPortfolio sync completed successfully!")
            print("Frontend should now show correct values.")
        else:
            print("\nPortfolio sync failed - check errors above")