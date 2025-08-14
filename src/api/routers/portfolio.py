"""
Portfolio tracking API endpoints
Provides comprehensive portfolio analytics and transaction history
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
import sqlite3
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

def get_db_connection():
    """Get database connection"""
    return sqlite3.connect('trading.db', check_same_thread=False)

@router.get("/portfolio/overview")
async def get_portfolio_overview():
    """Get complete portfolio overview with stocks and crypto separated"""
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        # Get portfolio configurations
        c.execute('''SELECT type, initial_capital, current_capital, available_cash, 
                            invested_amount, total_pnl, win_rate, total_trades, last_updated
                     FROM portfolio_config''')
        
        portfolios = {}
        total_initial = 0
        total_current = 0
        total_pnl = 0
        
        for row in c.fetchall():
            portfolio_type, initial_capital, current_capital, available_cash, invested_amount, pnl, win_rate, total_trades, last_updated = row
            
            portfolios[portfolio_type] = {
                "initial_capital": initial_capital,
                "current_capital": current_capital,
                "available_cash": available_cash,
                "invested_amount": invested_amount,
                "total_pnl": pnl,
                "win_rate": win_rate,
                "total_trades": total_trades,
                "last_updated": last_updated,
                "roi_percent": (pnl / initial_capital) * 100 if initial_capital > 0 else 0
            }
            
            total_initial += initial_capital
            total_current += current_capital
            total_pnl += pnl
        
        conn.close()
        
        return {
            "portfolios": portfolios,
            "summary": {
                "total_initial_capital": total_initial,
                "total_current_capital": total_current,
                "total_pnl": total_pnl,
                "total_roi_percent": (total_pnl / total_initial) * 100 if total_initial > 0 else 0,
                "last_updated": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting portfolio overview: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving portfolio overview: {str(e)}")

@router.get("/portfolio/{portfolio_type}/positions")
async def get_portfolio_positions(portfolio_type: str):
    """Get current positions for a specific portfolio (stocks or crypto)"""
    try:
        if portfolio_type not in ['stocks', 'crypto']:
            raise HTTPException(status_code=400, detail="Portfolio type must be 'stocks' or 'crypto'")
        
        conn = get_db_connection()
        c = conn.cursor()
        
        c.execute('''SELECT symbol, quantity, avg_entry_price, total_invested, 
                            current_price, current_value, unrealized_pnl, unrealized_pnl_percent, 
                            last_updated
                     FROM portfolio_positions 
                     WHERE portfolio_type = ?
                     ORDER BY total_invested DESC''', (portfolio_type,))
        
        positions = []
        for row in c.fetchall():
            symbol, quantity, avg_entry_price, total_invested, current_price, current_value, unrealized_pnl, unrealized_pnl_percent, last_updated = row
            
            positions.append({
                "symbol": symbol,
                "quantity": quantity,
                "avg_entry_price": avg_entry_price,
                "total_invested": total_invested,
                "current_price": current_price,
                "current_value": current_value,
                "unrealized_pnl": unrealized_pnl,
                "unrealized_pnl_percent": unrealized_pnl_percent,
                "last_updated": last_updated
            })
        
        conn.close()
        
        return {
            "portfolio_type": portfolio_type,
            "positions": positions,
            "summary": {
                "total_positions": len(positions),
                "total_invested": sum(p["total_invested"] for p in positions),
                "total_current_value": sum(p["current_value"] or 0 for p in positions),
                "total_unrealized_pnl": sum(p["unrealized_pnl"] or 0 for p in positions)
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting portfolio positions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving positions: {str(e)}")

@router.get("/portfolio/{portfolio_type}/transactions")
async def get_portfolio_transactions(
    portfolio_type: str,
    limit: int = Query(50, ge=1, le=500),
    symbol: Optional[str] = None
):
    """Get transaction history for a specific portfolio"""
    try:
        if portfolio_type not in ['stocks', 'crypto']:
            raise HTTPException(status_code=400, detail="Portfolio type must be 'stocks' or 'crypto'")
        
        conn = get_db_connection()
        c = conn.cursor()
        
        query = '''SELECT symbol, action, quantity, price, total_amount, fees, 
                          buy_reason, sell_reason, score, timestamp, source
                   FROM portfolio_transactions 
                   WHERE portfolio_type = ?'''
        params = [portfolio_type]
        
        if symbol:
            query += ' AND symbol = ?'
            params.append(symbol.upper())
        
        query += ' ORDER BY timestamp DESC LIMIT ?'
        params.append(limit)
        
        c.execute(query, params)
        
        transactions = []
        for row in c.fetchall():
            symbol, action, quantity, price, total_amount, fees, buy_reason, sell_reason, score, timestamp, source = row
            
            transactions.append({
                "symbol": symbol,
                "action": action,
                "quantity": quantity,
                "price": price,
                "total_amount": total_amount,
                "fees": fees or 0,
                "reason": buy_reason if action == 'buy' else sell_reason,
                "score": score,
                "timestamp": timestamp,
                "source": source
            })
        
        conn.close()
        
        return {
            "portfolio_type": portfolio_type,
            "transactions": transactions,
            "summary": {
                "total_transactions": len(transactions),
                "buy_transactions": len([t for t in transactions if t["action"] == "buy"]),
                "sell_transactions": len([t for t in transactions if t["action"] == "sell"]),
                "total_volume": sum(t["total_amount"] for t in transactions)
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting portfolio transactions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving transactions: {str(e)}")

@router.get("/portfolio/{portfolio_type}/performance")
async def get_portfolio_performance(portfolio_type: str, days: int = Query(30, ge=1, le=365)):
    """Get portfolio performance metrics and analysis"""
    try:
        if portfolio_type not in ['stocks', 'crypto']:
            raise HTTPException(status_code=400, detail="Portfolio type must be 'stocks' or 'crypto'")
        
        conn = get_db_connection()
        c = conn.cursor()
        
        # Get portfolio configuration
        c.execute('''SELECT initial_capital, current_capital, total_pnl, total_trades 
                     FROM portfolio_config WHERE type = ?''', (portfolio_type,))
        config = c.fetchone()
        
        if not config:
            raise HTTPException(status_code=404, detail=f"Portfolio {portfolio_type} not found")
        
        initial_capital, current_capital, total_pnl, total_trades = config
        
        # Get completed trades for analysis
        c.execute('''SELECT symbol, quantity, price, total_amount, timestamp, action,
                            buy_reason, sell_reason
                     FROM portfolio_transactions 
                     WHERE portfolio_type = ? AND timestamp >= ?
                     ORDER BY timestamp DESC''', 
                  (portfolio_type, (datetime.now() - timedelta(days=days)).isoformat()))
        
        recent_transactions = c.fetchall()
        
        # Calculate metrics
        buy_volume = sum(t[3] for t in recent_transactions if t[5] == 'buy')
        sell_volume = sum(t[3] for t in recent_transactions if t[5] == 'sell')
        realized_pnl = sell_volume - buy_volume if sell_volume > 0 else 0
        
        # Get unique symbols traded
        symbols_traded = list(set(t[0] for t in recent_transactions))
        
        # Calculate win rate from sells
        sell_transactions = [t for t in recent_transactions if t[5] == 'sell']
        winning_sells = 0
        total_sells = len(sell_transactions)
        
        # Simple win detection (sell price > average buy price for symbol)
        for sell_txn in sell_transactions:
            symbol = sell_txn[0]
            sell_price = sell_txn[2]
            
            # Get average buy price for this symbol
            c.execute('''SELECT AVG(price) FROM portfolio_transactions 
                         WHERE portfolio_type = ? AND symbol = ? AND action = 'buy' 
                         AND timestamp <= ?''', 
                      (portfolio_type, symbol, sell_txn[4]))
            avg_buy_result = c.fetchone()
            avg_buy_price = avg_buy_result[0] if avg_buy_result[0] else 0
            
            if sell_price > avg_buy_price:
                winning_sells += 1
        
        win_rate = (winning_sells / total_sells) * 100 if total_sells > 0 else 0
        
        conn.close()
        
        return {
            "portfolio_type": portfolio_type,
            "period_days": days,
            "metrics": {
                "initial_capital": initial_capital,
                "current_capital": current_capital,
                "total_pnl": total_pnl,
                "roi_percent": (total_pnl / initial_capital) * 100 if initial_capital > 0 else 0,
                "realized_pnl_period": realized_pnl,
                "total_trades": total_trades,
                "win_rate": win_rate,
                "buy_volume_period": buy_volume,
                "sell_volume_period": sell_volume,
                "symbols_traded_period": len(symbols_traded),
                "avg_trade_size": buy_volume / len([t for t in recent_transactions if t[5] == 'buy']) if any(t[5] == 'buy' for t in recent_transactions) else 0
            },
            "symbols_traded": symbols_traded
        }
        
    except Exception as e:
        logger.error(f"Error getting portfolio performance: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving performance: {str(e)}")

@router.get("/portfolio/analytics/comparison")
async def get_portfolio_comparison():
    """Compare stocks vs crypto portfolio performance"""
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        comparison = {}
        
        for portfolio_type in ['stocks', 'crypto']:
            c.execute('''SELECT initial_capital, current_capital, total_pnl, total_trades
                         FROM portfolio_config WHERE type = ?''', (portfolio_type,))
            
            config = c.fetchone()
            if config:
                initial_capital, current_capital, total_pnl, total_trades = config
                
                comparison[portfolio_type] = {
                    "initial_capital": initial_capital,
                    "current_capital": current_capital,
                    "total_pnl": total_pnl,
                    "roi_percent": (total_pnl / initial_capital) * 100 if initial_capital > 0 else 0,
                    "total_trades": total_trades
                }
        
        conn.close()
        
        # Calculate comparative metrics
        if 'stocks' in comparison and 'crypto' in comparison:
            stocks_roi = comparison['stocks']['roi_percent']
            crypto_roi = comparison['crypto']['roi_percent']
            
            comparison['analysis'] = {
                "better_performer": "stocks" if stocks_roi > crypto_roi else "crypto",
                "roi_difference": abs(stocks_roi - crypto_roi),
                "total_portfolio_roi": (
                    (comparison['stocks']['total_pnl'] + comparison['crypto']['total_pnl']) /
                    (comparison['stocks']['initial_capital'] + comparison['crypto']['initial_capital'])
                ) * 100,
                "risk_assessment": "Higher risk" if crypto_roi > stocks_roi else "Lower risk"
            }
        
        return comparison
        
    except Exception as e:
        logger.error(f"Error getting portfolio comparison: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving comparison: {str(e)}")