"""
SHORT Monitoring API endpoints for specialized SHORT position tracking
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging

from ..database.database import db_manager
from ..services.data_service import DataService

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/short-positions")
async def get_short_positions():
    """Get all SHORT positions with detailed analysis"""
    try:
        # Get all SHORT positions
        positions = db_manager.execute_query("""
            SELECT p.symbol, p.entry_price, p.current_price, p.quantity,
                   p.pnl, p.pnl_percent, p.stop_loss_updated, p.take_profit_updated,
                   p.created_at, p.updated_at,
                   c.score as current_score, c.change_percent, c.volume, c.market_cap
            FROM positions p
            LEFT JOIN cryptos c ON p.symbol = c.symbol
            WHERE p.position_side = 'SHORT'
            ORDER BY p.created_at DESC
        """)
        
        if not positions:
            return {"short_positions": [], "summary": {"total_positions": 0, "total_pnl": 0}}
        
        # Analyze each position
        analyzed_positions = []
        total_pnl = 0
        risk_alerts = []
        
        for pos in positions:
            entry_price = pos['entry_price']
            current_price = pos['current_price'] or entry_price
            stop_loss = pos['stop_loss_updated'] or 0
            take_profit = pos['take_profit_updated'] or 0
            current_score = pos['current_score'] or 0
            
            # Calculate risk metrics
            price_change = ((current_price - entry_price) / entry_price) * 100 if entry_price > 0 else 0
            distance_to_stop = ((stop_loss - current_price) / current_price) * 100 if stop_loss > 0 and current_price > 0 else 0
            distance_to_tp = ((current_price - take_profit) / current_price) * 100 if take_profit > 0 and current_price > 0 else 0
            
            # Risk assessment
            risk_level = "LOW"
            if price_change > 5:  # Price moved against us >5%
                risk_level = "HIGH"
                risk_alerts.append(f"{pos['symbol']}: Price up {price_change:.1f}% (bad for SHORT)")
            elif price_change > 2:
                risk_level = "MEDIUM"
            
            # Score improvement check
            if current_score >= 3.0:
                risk_alerts.append(f"{pos['symbol']}: Score improved to {current_score} (should consider exit)")
            
            analyzed_pos = {
                **dict(pos),
                "price_change_percent": round(price_change, 2),
                "distance_to_stop_percent": round(distance_to_stop, 2),
                "distance_to_tp_percent": round(distance_to_tp, 2),
                "risk_level": risk_level,
                "should_exit": current_score >= 3.0 or price_change > 6,
                "days_held": (datetime.now() - datetime.fromisoformat(pos['created_at'])).days
            }
            
            analyzed_positions.append(analyzed_pos)
            total_pnl += pos['pnl'] or 0
        
        # Summary statistics
        summary = {
            "total_positions": len(analyzed_positions),
            "total_pnl": round(total_pnl, 2),
            "avg_pnl_percent": round(sum(p['pnl_percent'] or 0 for p in analyzed_positions) / len(analyzed_positions), 2),
            "high_risk_positions": len([p for p in analyzed_positions if p['risk_level'] == 'HIGH']),
            "positions_to_exit": len([p for p in analyzed_positions if p['should_exit']]),
            "risk_alerts": risk_alerts
        }
        
        return {
            "short_positions": analyzed_positions,
            "summary": summary,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting SHORT positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/short-performance")
async def get_short_performance():
    """Get SHORT trading performance analytics"""
    try:
        # Get SHORT transaction history
        transactions = db_manager.execute_query("""
            SELECT symbol, action, quantity, price, reason, timestamp
            FROM autotrader_transactions
            WHERE action IN ('short', 'sell') AND symbol IN (
                SELECT DISTINCT symbol FROM autotrader_transactions WHERE action = 'short'
            )
            ORDER BY timestamp DESC
            LIMIT 50
        """)
        
        # Group by symbol to track complete SHORT cycles
        short_cycles = {}
        for tx in transactions:
            symbol = tx['symbol']
            if symbol not in short_cycles:
                short_cycles[symbol] = {'opens': [], 'closes': []}
            
            if tx['action'] == 'short':
                short_cycles[symbol]['opens'].append(tx)
            else:  # sell (exit SHORT)
                short_cycles[symbol]['closes'].append(tx)
        
        # Calculate performance metrics
        completed_cycles = 0
        total_profit = 0
        winning_trades = 0
        losing_trades = 0
        
        cycle_analysis = []
        
        for symbol, cycles in short_cycles.items():
            opens = cycles['opens']
            closes = cycles['closes']
            
            # Match opens and closes
            for i, close in enumerate(closes):
                if i < len(opens):
                    open_tx = opens[i]
                    entry_price = open_tx['price']
                    exit_price = close['price']
                    quantity = min(open_tx['quantity'], close['quantity'])
                    
                    # SHORT P&L: profit when exit price < entry price
                    pnl = (entry_price - exit_price) * quantity
                    pnl_percent = (pnl / (entry_price * quantity)) * 100 if entry_price > 0 else 0
                    
                    cycle_data = {
                        'symbol': symbol,
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'quantity': quantity,
                        'pnl': round(pnl, 2),
                        'pnl_percent': round(pnl_percent, 2),
                        'entry_date': open_tx['timestamp'],
                        'exit_date': close['timestamp'],
                        'exit_reason': close['reason']
                    }
                    
                    cycle_analysis.append(cycle_data)
                    completed_cycles += 1
                    total_profit += pnl
                    
                    if pnl > 0:
                        winning_trades += 1
                    else:
                        losing_trades += 1
        
        # Calculate win rate and metrics
        win_rate = (winning_trades / completed_cycles * 100) if completed_cycles > 0 else 0
        avg_profit_per_trade = total_profit / completed_cycles if completed_cycles > 0 else 0
        
        performance_summary = {
            "completed_cycles": completed_cycles,
            "total_profit": round(total_profit, 2),
            "win_rate_percent": round(win_rate, 2),
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "avg_profit_per_trade": round(avg_profit_per_trade, 2),
            "current_open_shorts": len(db_manager.execute_query("SELECT * FROM positions WHERE position_side = 'SHORT'"))
        }
        
        return {
            "performance_summary": performance_summary,
            "cycle_analysis": cycle_analysis[-10:],  # Last 10 cycles
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting SHORT performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/short-alerts")
async def get_short_alerts():
    """Get critical alerts for SHORT positions"""
    try:
        logger.info("Starting SHORT alerts endpoint")
        alerts = []
        
        # Get current SHORT positions
        logger.info("Querying SHORT positions")
        positions = db_manager.execute_query("""
            SELECT p.symbol, p.entry_price, p.current_price, p.pnl_percent,
                   p.stop_loss_updated, p.created_at,
                   c.score as current_score, c.change_percent
            FROM positions p
            LEFT JOIN cryptos c ON p.symbol = c.symbol
            WHERE p.position_side = 'SHORT'
        """)
        logger.info(f"Found {len(positions)} SHORT positions")
        
        for i, pos in enumerate(positions):
            try:
                logger.info(f"Processing position {i+1}: {pos['symbol']}")
                symbol = pos['symbol']
                entry_price = pos['entry_price']
                current_price = pos['current_price'] or entry_price
                pnl_percent = pos['pnl_percent'] or 0
                stop_loss = pos['stop_loss_updated'] or 0
                current_score = pos['current_score'] or 0
                created_at = datetime.fromisoformat(pos['created_at'])
                days_held = (datetime.now() - created_at).days
            except Exception as e:
                logger.error(f"Error processing position {pos.get('symbol', 'unknown')}: {e}")
                continue
            
            # Critical alerts
            if pnl_percent < -6:  # Losing more than 6%
                alerts.append({
                    "severity": "CRITICAL",
                    "symbol": symbol,
                    "message": f"HIGH LOSS: {pnl_percent:.1f}% loss on SHORT position",
                    "action": "Consider emergency exit"
                })
            
            if current_score >= 4.0:  # Score improved significantly
                alerts.append({
                    "severity": "HIGH",
                    "symbol": symbol,
                    "message": f"SCORE IMPROVED: Score now {current_score} (was bearish)",
                    "action": "Strong exit signal"
                })
            
            if current_score >= 3.0:  # Score improved to neutral
                alerts.append({
                    "severity": "MEDIUM",
                    "symbol": symbol,
                    "message": f"Score improved to {current_score}",
                    "action": "Consider exit"
                })
            
            if days_held > 7:  # Held too long
                alerts.append({
                    "severity": "MEDIUM",
                    "symbol": symbol,
                    "message": f"Position held {days_held} days (max recommended: 7)",
                    "action": "Review exit criteria"
                })
            
            # Near stop loss
            if stop_loss > 0 and current_price > 0:
                distance_to_stop = ((stop_loss - current_price) / current_price) * 100
                if distance_to_stop < 2:  # Within 2% of stop loss
                    alerts.append({
                        "severity": "HIGH",
                        "symbol": symbol,
                        "message": f"NEAR STOP LOSS: {distance_to_stop:.1f}% away from stop",
                        "action": "Prepare for stop loss execution"
                    })
        
        # Market condition alerts
        btc_data = db_manager.execute_query("SELECT change_percent FROM cryptos WHERE symbol = 'BTC-USD' LIMIT 1")
        if btc_data and btc_data[0]['change_percent'] > 3:
            alerts.append({
                "severity": "MEDIUM",
                "symbol": "MARKET",
                "message": f"BTC up {btc_data[0]['change_percent']:.1f}% - crypto market bullish",
                "action": "Consider reducing SHORT exposure"
            })
        
        # Count SHORT exposure
        exposure_result = db_manager.execute_query("""
            SELECT COALESCE(SUM(quantity * entry_price), 0) as total
            FROM positions WHERE position_side = 'SHORT'
        """)
        total_short_exposure = exposure_result[0]['total'] if exposure_result else 0
        
        if total_short_exposure > 100000:  # More than 100k in SHORTs
            alerts.append({
                "severity": "MEDIUM",
                "symbol": "PORTFOLIO",
                "message": f"HIGH SHORT EXPOSURE: ${total_short_exposure:,.0f}",
                "action": "Monitor risk carefully"
            })
        
        # Sort by severity
        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        alerts.sort(key=lambda x: severity_order.get(x['severity'], 4))
        
        return {
            "alerts": alerts,
            "alert_count": len(alerts),
            "critical_count": len([a for a in alerts if a['severity'] == 'CRITICAL']),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting SHORT alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/short-emergency-exit")
async def emergency_exit_all_shorts():
    """Emergency exit all SHORT positions (manual override)"""
    try:
        # Get all SHORT positions
        positions = db_manager.execute_query("""
            SELECT id, symbol, quantity, current_price, entry_price
            FROM positions 
            WHERE position_side = 'SHORT'
        """)
        
        if not positions:
            return {"message": "No SHORT positions to exit", "positions_closed": 0}
        
        closed_positions = []
        data_service = DataService()
        
        for pos in positions:
            symbol = pos['symbol']
            quantity = pos['quantity']
            current_price = pos['current_price'] or pos['entry_price']
            entry_price = pos['entry_price']
            
            # Calculate final P&L
            pnl = (entry_price - current_price) * quantity
            
            # Remove position
            db_manager.execute_update("DELETE FROM positions WHERE id = ?", (pos['id'],))
            
            # Log emergency exit
            db_manager.execute_insert("""
                INSERT INTO autotrader_transactions 
                (symbol, action, quantity, price, reason)
                VALUES (?, 'sell', ?, ?, ?)
            """, (symbol, quantity, current_price, "EMERGENCY EXIT - Manual override"))
            
            closed_positions.append({
                "symbol": symbol,
                "quantity": quantity,
                "exit_price": current_price,
                "pnl": round(pnl, 2)
            })
            
            logger.warning(f"EMERGENCY EXIT: Closed SHORT {symbol} - P&L: ${pnl:.2f}")
        
        return {
            "message": "Emergency exit completed",
            "positions_closed": len(closed_positions),
            "closed_positions": closed_positions,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in emergency exit: {e}")
        raise HTTPException(status_code=500, detail=str(e))