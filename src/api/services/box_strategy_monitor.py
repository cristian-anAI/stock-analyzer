"""
Box Strategy Trade Monitor
Monitors NDX, SPX, and RTY for breakouts and sends Telegram notifications
"""

import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Set
from dataclasses import dataclass

from .box_strategy_service import BoxStrategyService, BoxSetup, MLPrediction
from .telegram_service import telegram_service

logger = logging.getLogger(__name__)


@dataclass
class ActiveTrade:
    """Track active box strategy trades"""
    market: str
    direction: str
    entry_price: float
    entry_time: str
    stop_loss: float
    tp1: float
    tp2: float
    tp3: float
    box_high: float
    box_low: float
    risk_points: float
    ml_confidence: str
    ml_probability: float
    tp1_hit: bool = False
    stop_moved_to_breakeven: bool = False


class BoxStrategyMonitor:
    """Monitor box strategy breakouts and send notifications"""

    def __init__(self):
        self.box_service = BoxStrategyService(ml_version="1")
        self.monitored_markets = ["NDX", "SPX", "RTY"]  # NASDAQ, S&P 500, Russell 2000

        # Track notified breakouts to avoid duplicates
        self.notified_breakouts: Set[str] = set()  # Format: "MARKET_DATE_DIRECTION"

        # Track active trades
        self.active_trades: Dict[str, ActiveTrade] = {}

        logger.info(f"Box Strategy Monitor initialized for markets: {self.monitored_markets}")

    def _get_breakout_key(self, market: str, date: str, direction: str) -> str:
        """Generate unique key for a breakout"""
        return f"{market}_{date}_{direction}"

    async def check_for_breakouts(self) -> List[Dict]:
        """
        Check monitored markets for new breakouts

        Returns:
            List of new breakout notifications sent
        """
        notifications_sent = []

        for market in self.monitored_markets:
            try:
                # Get market status
                status = self.box_service.get_market_status(market)

                # Only check if box is complete
                if not status.box_complete:
                    logger.debug(f"{market}: Box not complete yet")
                    continue

                # Get box setup
                box_setup = self.box_service.get_box_setup(market)

                if not box_setup:
                    logger.debug(f"{market}: No box setup available")
                    continue

                # Check if breakout detected
                if not box_setup.breakout_detected:
                    logger.debug(f"{market}: No breakout detected")
                    continue

                # Check if we already notified this breakout
                breakout_key = self._get_breakout_key(
                    market,
                    box_setup.date,
                    box_setup.direction
                )

                if breakout_key in self.notified_breakouts:
                    logger.debug(f"{market}: Already notified breakout {breakout_key}")
                    continue

                # Get ML prediction
                ml_prediction = self.box_service.get_ml_prediction(box_setup)

                if not ml_prediction:
                    logger.warning(f"{market}: No ML prediction available")
                    continue

                # Send Telegram notification
                success = await self._send_breakout_notification(
                    box_setup,
                    ml_prediction
                )

                if success:
                    # Mark as notified
                    self.notified_breakouts.add(breakout_key)

                    # Track as active trade
                    self.active_trades[breakout_key] = ActiveTrade(
                        market=box_setup.market,
                        direction=box_setup.direction,
                        entry_price=box_setup.entry_price,
                        entry_time=box_setup.entry_time,
                        stop_loss=box_setup.stop_loss,
                        tp1=box_setup.tp1,
                        tp2=box_setup.tp2,
                        tp3=box_setup.tp3,
                        box_high=box_setup.box_high,
                        box_low=box_setup.box_low,
                        risk_points=box_setup.risk_points,
                        ml_confidence=ml_prediction.confidence_level,
                        ml_probability=ml_prediction.win_probability
                    )

                    notifications_sent.append({
                        "market": market,
                        "breakout_key": breakout_key,
                        "direction": box_setup.direction,
                        "confidence": ml_prediction.confidence_level,
                        "timestamp": datetime.now().isoformat()
                    })

                    logger.info(f"✅ {market}: Breakout notification sent - {box_setup.direction} @ ${box_setup.entry_price:.2f}")

            except Exception as e:
                logger.error(f"Error checking {market} for breakouts: {e}")
                continue

        return notifications_sent

    async def _send_breakout_notification(
        self,
        box_setup: BoxSetup,
        ml_prediction: MLPrediction
    ) -> bool:
        """
        Send Telegram notification for new breakout

        Args:
            box_setup: Box setup with breakout details
            ml_prediction: ML prediction for the trade

        Returns:
            True if notification sent successfully
        """
        try:
            # Prepare notification data
            success = telegram_service.send_box_trade_notification(
                market=box_setup.market,
                direction=box_setup.direction,
                entry_price=box_setup.entry_price,
                stop_loss=box_setup.stop_loss,
                tp1=box_setup.tp1,
                tp2=box_setup.tp2,
                tp3=box_setup.tp3,
                box_high=box_setup.box_high,
                box_low=box_setup.box_low,
                box_range=box_setup.box_range,
                risk_points=box_setup.risk_points,
                ml_confidence=ml_prediction.confidence_level,
                ml_probability=ml_prediction.win_probability * 100,  # Convert to percentage
                entry_time=box_setup.entry_time
            )

            return success

        except Exception as e:
            logger.error(f"Failed to send breakout notification: {e}")
            return False

    async def monitor_active_trades(self) -> List[Dict]:
        """
        Monitor active trades for TP1 hit to move stop to breakeven

        Returns:
            List of trade updates
        """
        updates = []

        for breakout_key, trade in list(self.active_trades.items()):
            try:
                # Get current price for the market
                box_setup = self.box_service.get_box_setup(trade.market)

                if not box_setup or not box_setup.current_price:
                    continue

                current_price = box_setup.current_price

                # Check if TP1 hit and stop not moved yet
                if not trade.tp1_hit and not trade.stop_moved_to_breakeven:
                    tp1_hit = False

                    if trade.direction == "LONG":
                        tp1_hit = current_price >= trade.tp1
                    else:  # SHORT
                        tp1_hit = current_price <= trade.tp1

                    if tp1_hit:
                        # Mark TP1 as hit and move stop to breakeven
                        trade.tp1_hit = True
                        trade.stop_moved_to_breakeven = True
                        trade.stop_loss = trade.entry_price  # Move to breakeven

                        logger.info(f"🎯 {trade.market}: TP1 hit! Stop loss moved to breakeven @ ${trade.entry_price:.2f}")

                        # Send notification
                        message = f"""
🎯 <b>TP1 ALCANZADO - {trade.market}</b>

<b>Dirección:</b> {trade.direction}
<b>Precio actual:</b> ${current_price:.2f}
<b>TP1:</b> ${trade.tp1:.2f} ✅

🛡️ <b>Stop Loss movido a Break Even</b>
<b>Nuevo SL:</b> ${trade.entry_price:.2f}

<i>{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</i>
"""
                        telegram_service.send_message(message.strip())

                        updates.append({
                            "market": trade.market,
                            "action": "tp1_hit_stop_moved",
                            "new_stop": trade.entry_price,
                            "timestamp": datetime.now().isoformat()
                        })

            except Exception as e:
                logger.error(f"Error monitoring trade {breakout_key}: {e}")
                continue

        return updates

    def clear_old_notifications(self, days: int = 7):
        """
        Clear old breakout notifications to free memory

        Args:
            days: Keep notifications from last N days
        """
        # For now, just clear everything older than 7 days
        # In production, you'd want to parse dates and remove selectively
        if len(self.notified_breakouts) > 100:  # Arbitrary limit
            logger.info(f"Clearing old breakout notifications (count: {len(self.notified_breakouts)})")
            self.notified_breakouts.clear()

    async def run_monitoring_cycle(self) -> Dict:
        """
        Run a complete monitoring cycle

        Returns:
            Summary of actions taken
        """
        logger.debug("Starting box strategy monitoring cycle...")

        # Check for new breakouts
        new_breakouts = await self.check_for_breakouts()

        # Monitor active trades
        trade_updates = await self.monitor_active_trades()

        # Clean up old notifications
        self.clear_old_notifications()

        summary = {
            "timestamp": datetime.now().isoformat(),
            "new_breakouts": len(new_breakouts),
            "trade_updates": len(trade_updates),
            "active_trades": len(self.active_trades),
            "breakouts": new_breakouts,
            "updates": trade_updates
        }

        if new_breakouts or trade_updates:
            logger.info(f"📊 Monitoring cycle: {len(new_breakouts)} new breakouts, {len(trade_updates)} updates")

        return summary


# Global instance
box_strategy_monitor = BoxStrategyMonitor()
