"""
Telegram notification service for trading alerts
"""
import os
import logging
from typing import Optional
import requests
from datetime import datetime

logger = logging.getLogger(__name__)


class TelegramService:
    """Service for sending Telegram notifications"""

    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")  # Group chat ID
        self.personal_chat_id = os.getenv("TELEGRAM_PERSONAL_CHAT_ID")  # Personal chat ID
        self.enabled = bool(self.bot_token and self.chat_id)

        # Cache para evitar notificaciones duplicadas de oportunidades
        self._opportunity_alerts_sent_today = {}  # {symbol: date}
        self._current_date = datetime.now().date()

        if not self.enabled:
            logger.warning("Telegram service disabled - missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID")
        else:
            logger.info(f"Telegram service initialized - Group: {self.chat_id}, Personal: {self.personal_chat_id or 'None'}")

    def send_message(self, message: str, parse_mode: str = "HTML", send_to_personal: bool = False) -> bool:
        """
        Send a message via Telegram to group and optionally to personal chat

        Args:
            message: Message text (supports HTML formatting)
            parse_mode: Telegram parse mode (HTML or Markdown)
            send_to_personal: If True, also send to personal chat

        Returns:
            True if message sent successfully to group, False otherwise
        """
        if not self.enabled:
            logger.debug("Telegram service disabled, skipping message")
            return False

        success = True
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

        # Always send to group
        try:
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": parse_mode
            }

            response = requests.post(url, json=payload, timeout=10)

            if response.status_code == 200:
                logger.info("Telegram message sent to group successfully")
            else:
                logger.error(f"Telegram API error (group): {response.status_code} - {response.text}")
                success = False

        except Exception as e:
            logger.error(f"Failed to send Telegram message to group: {e}")
            success = False

        # Also send to personal chat if requested
        if send_to_personal and self.personal_chat_id:
            try:
                payload = {
                    "chat_id": self.personal_chat_id,
                    "text": message,
                    "parse_mode": parse_mode
                }

                response = requests.post(url, json=payload, timeout=10)

                if response.status_code == 200:
                    logger.info("Telegram message sent to personal chat successfully")
                else:
                    logger.error(f"Telegram API error (personal): {response.status_code} - {response.text}")

            except Exception as e:
                logger.error(f"Failed to send Telegram message to personal chat: {e}")

        return success

    def _check_and_reset_daily_cache(self):
        """Reset opportunity cache if it's a new day"""
        today = datetime.now().date()
        if today != self._current_date:
            logger.info(f"New day detected, resetting opportunity alerts cache (was: {len(self._opportunity_alerts_sent_today)} alerts)")
            self._opportunity_alerts_sent_today.clear()
            self._current_date = today

    def send_opportunity_alert(
        self,
        symbol: str,
        price: float,
        score: float,
        position_type: str = "LONG",
        reason_not_bought: str = None
    ) -> bool:
        """
        Send an alert for a high-score opportunity (score >= 6.0) that was NOT bought
        Only sends once per day per symbol to avoid spam

        Args:
            symbol: Stock symbol
            price: Current price
            score: Trading score
            position_type: LONG, SHORT, CRYPTO_LONG, or CRYPTO_SHORT
            reason_not_bought: Why it wasn't purchased (e.g., "Sin capital", "Max posiciones")

        Returns:
            True if notification sent successfully, False if already sent today or sending failed
        """
        # Check if new day and reset cache if needed
        self._check_and_reset_daily_cache()

        # Check if we already sent an alert for this symbol today
        if symbol in self._opportunity_alerts_sent_today:
            logger.debug(f"Skipping opportunity alert for {symbol} - already sent today at {self._opportunity_alerts_sent_today[symbol]}")
            return False

        emoji = "⚠️"
        action = "OPORTUNIDAD LONG" if "LONG" in position_type else "OPORTUNIDAD SHORT"

        reason_section = ""
        if reason_not_bought:
            reason_section = f"\n<b>No comprado:</b> {reason_not_bought}"

        message = f"""
{emoji} <b>{action} - NO EJECUTADA</b>

<b>Symbol:</b> {symbol}
<b>Precio:</b> ${price:.2f}
<b>Score:</b> {score:.2f} ⭐
<b>Tipo:</b> {position_type}{reason_section}

<i>{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</i>
"""

        # Try to send the message
        success = self.send_message(message.strip(), send_to_personal=True)

        # If successful, mark this symbol as notified today
        if success:
            self._opportunity_alerts_sent_today[symbol] = datetime.now()
            logger.info(f"Opportunity alert sent for {symbol} (score: {score:.2f}) - won't notify again today")

        return success

    def send_buy_notification(
        self,
        symbol: str,
        price: float,
        quantity: int,
        score: float,
        total_value: float,
        remaining_capital: float,
        position_type: str = "LONG"
    ) -> bool:
        """
        Send a buy trade notification

        Args:
            symbol: Stock symbol
            price: Entry price
            quantity: Number of shares
            score: Trading score
            total_value: Total position value
            remaining_capital: Remaining liquid capital
            position_type: LONG, SHORT, CRYPTO_LONG, or CRYPTO_SHORT

        Returns:
            True if notification sent successfully
        """
        emoji = "🟢" if "LONG" in position_type else "🔴"
        action = "COMPRA" if "LONG" in position_type else "SHORT"

        message = f"""
{emoji} <b>{action} EJECUTADA</b>

<b>Symbol:</b> {symbol}
<b>Precio:</b> ${price:.2f}
<b>Cantidad:</b> {quantity:,} acciones
<b>Score:</b> {score:.2f}
<b>Tipo:</b> {position_type}
<b>Valor total:</b> ${total_value:,.2f}
<b>Capital restante:</b> ${remaining_capital:,.2f}

<i>{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</i>
"""

        return self.send_message(message.strip(), send_to_personal=True)

    def send_sell_notification(
        self,
        symbol: str,
        entry_price: float,
        exit_price: float,
        quantity: int,
        pnl: float,
        pnl_percent: float,
        position_type: str = "LONG"
    ) -> bool:
        """
        Send a sell trade notification

        Args:
            symbol: Stock symbol
            entry_price: Entry price
            exit_price: Exit price
            quantity: Number of shares
            pnl: Profit/Loss amount
            pnl_percent: Profit/Loss percentage
            position_type: Position type

        Returns:
            True if notification sent successfully
        """
        emoji = "💰" if pnl > 0 else "📉"
        result = "GANANCIA" if pnl > 0 else "PÉRDIDA"

        message = f"""
{emoji} <b>VENTA EJECUTADA - {result}</b>

<b>Symbol:</b> {symbol}
<b>Precio entrada:</b> ${entry_price:.2f}
<b>Precio salida:</b> ${exit_price:.2f}
<b>Cantidad:</b> {quantity:,} acciones
<b>Tipo:</b> {position_type}

<b>P&L:</b> ${pnl:,.2f} ({pnl_percent:+.2f}%)

<i>{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</i>
"""

        return self.send_message(message.strip(), send_to_personal=True)

    def send_error_notification(self, error_message: str, context: str = "") -> bool:
        """
        Send an error notification

        Args:
            error_message: Error description
            context: Additional context

        Returns:
            True if notification sent successfully
        """
        message = f"""
⚠️ <b>ERROR EN AUTOTRADER</b>

<b>Error:</b> {error_message}

{f"<b>Contexto:</b> {context}" if context else ""}

<i>{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</i>
"""

        return self.send_message(message.strip(), send_to_personal=True)

    def send_portfolio_update(
        self,
        total_value: float,
        liquid_capital: float,
        invested_capital: float,
        total_pnl: float,
        pnl_percent: float,
        open_positions: int
    ) -> bool:
        """
        Send a portfolio status update

        Args:
            total_value: Total portfolio value
            liquid_capital: Available liquid capital
            invested_capital: Capital in positions
            total_pnl: Total profit/loss
            pnl_percent: Total P&L percentage
            open_positions: Number of open positions

        Returns:
            True if notification sent successfully
        """
        emoji = "📊"
        pnl_emoji = "💰" if total_pnl > 0 else "📉" if total_pnl < 0 else "➖"

        message = f"""
{emoji} <b>RESUMEN DE PORTFOLIO</b>

<b>Valor total:</b> ${total_value:,.2f}
<b>Capital líquido:</b> ${liquid_capital:,.2f}
<b>Capital invertido:</b> ${invested_capital:,.2f}

{pnl_emoji} <b>P&L Total:</b> ${total_pnl:,.2f} ({pnl_percent:+.2f}%)

<b>Posiciones abiertas:</b> {open_positions}

<i>{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</i>
"""

        return self.send_message(message.strip(), send_to_personal=True)

    def send_autotrader_positions_summary(self, positions: list, portfolio_stats: dict) -> bool:
        """
        Send a detailed summary of autotrader positions (daily market close)

        Args:
            positions: List of position dictionaries
            portfolio_stats: Portfolio statistics dictionary

        Returns:
            True if notification sent successfully
        """
        if not positions:
            message = """
📊 <b>CIERRE DE MERCADO - AUTOTRADER</b>

✅ <b>No hay posiciones abiertas</b>

<i>{}</i>
""".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            return self.send_message(message.strip(), send_to_personal=True)

        # Build positions summary
        positions_text = []
        for pos in positions:
            symbol = pos.get('symbol', 'N/A')
            quantity = pos.get('quantity', 0)
            entry_price = pos.get('entry_price', 0)
            current_price = pos.get('current_price', 0)
            pnl = pos.get('pnl', 0)
            pnl_percent = pos.get('pnl_percent', 0)

            pnl_emoji = "🟢" if pnl > 0 else "🔴" if pnl < 0 else "⚪"

            positions_text.append(
                f"{pnl_emoji} <b>{symbol}</b>\n"
                f"   Cantidad: {int(quantity):,} | Entrada: ${entry_price:.2f}\n"
                f"   Precio actual: ${current_price:.2f}\n"
                f"   P&L: ${pnl:,.2f} ({pnl_percent:+.2f}%)"
            )

        # Portfolio stats
        total_pnl = portfolio_stats.get('total_pnl', 0)
        total_invested = portfolio_stats.get('invested_capital', 0)
        liquid_capital = portfolio_stats.get('liquid_capital', 0)
        total_value = portfolio_stats.get('total_value', 0)

        pnl_emoji = "💰" if total_pnl > 0 else "📉" if total_pnl < 0 else "➖"

        message = f"""
📊 <b>CIERRE DE MERCADO - AUTOTRADER</b>

<b>Posiciones abiertas:</b> {len(positions)}

{chr(10).join(positions_text)}

━━━━━━━━━━━━━━━━━━━━
{pnl_emoji} <b>RESUMEN TOTAL</b>
<b>Capital invertido:</b> ${total_invested:,.2f}
<b>Capital líquido:</b> ${liquid_capital:,.2f}
<b>Valor total portfolio:</b> ${total_value:,.2f}
<b>P&L Total:</b> ${total_pnl:,.2f}

<i>{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</i>
"""

        return self.send_message(message.strip(), send_to_personal=True)

    def send_box_trade_notification(
        self,
        market: str,
        direction: str,
        entry_price: float,
        stop_loss: float,
        tp1: float,
        tp2: float,
        tp3: float,
        box_high: float,
        box_low: float,
        box_range: float,
        risk_points: float,
        ml_confidence: str = None,
        ml_probability: float = None,
        entry_time: str = None
    ) -> bool:
        """
        Send a box strategy trade notification

        Args:
            market: Market code (SPX, NDX, etc.)
            direction: LONG or SHORT
            entry_price: Entry price
            stop_loss: Stop loss level
            tp1: Take profit 1
            tp2: Take profit 2
            tp3: Take profit 3
            box_high: Box high level
            box_low: Box low level
            box_range: Box range in points
            risk_points: Risk in points (distance to stop)
            ml_confidence: ML confidence level (HIGH/MEDIUM/LOW)
            ml_probability: ML win probability (0-100)
            entry_time: Entry timestamp

        Returns:
            True if notification sent successfully
        """
        emoji = "🟢" if direction == "LONG" else "🔴"
        direction_text = "COMPRA (LONG)" if direction == "LONG" else "VENTA (SHORT)"

        # Calculate risk/reward ratios
        rr1 = abs(tp1 - entry_price) / risk_points if risk_points > 0 else 0
        rr2 = abs(tp2 - entry_price) / risk_points if risk_points > 0 else 0
        rr3 = abs(tp3 - entry_price) / risk_points if risk_points > 0 else 0

        ml_section = ""
        if ml_confidence and ml_probability:
            ml_emoji = "🎯" if ml_confidence == "HIGH" else "⚡" if ml_confidence == "MEDIUM" else "⚠️"
            ml_section = f"""
{ml_emoji} <b>ML Confidence:</b> {ml_confidence} ({ml_probability:.1f}%)"""

        message = f"""
{emoji} <b>BOX STRATEGY - {direction_text}</b>

<b>Market:</b> {market}
<b>Dirección:</b> {direction}
<b>Entrada:</b> ${entry_price:.2f}
<b>Stop Loss:</b> ${stop_loss:.2f}
<b>Riesgo:</b> {risk_points:.2f} puntos
{ml_section}

📊 <b>CAJA (Box)</b>
<b>Alto:</b> ${box_high:.2f}
<b>Bajo:</b> ${box_low:.2f}
<b>Rango:</b> {box_range:.2f} puntos

🎯 <b>OBJETIVOS (Take Profits)</b>
<b>TP1 (50%):</b> ${tp1:.2f} | R:R {rr1:.2f}x
<b>TP2 (25%):</b> ${tp2:.2f} | R:R {rr2:.2f}x
<b>TP3 (25%):</b> ${tp3:.2f} | R:R {rr3:.2f}x

<i>{entry_time if entry_time else datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</i>
"""

        return self.send_message(message.strip(), send_to_personal=True)

    def send_box_trade_exit_notification(
        self,
        market: str,
        direction: str,
        entry_price: float,
        exit_price: float,
        exit_level: str,
        pnl: float,
        pnl_points: float,
        rr_multiple: float
    ) -> bool:
        """
        Send a box strategy trade exit notification

        Args:
            market: Market code
            direction: LONG or SHORT
            entry_price: Entry price
            exit_price: Exit price
            exit_level: Exit reason (TP1, TP2, TP3, STOP_LOSS, MANUAL)
            pnl: Profit/Loss in currency
            pnl_points: Profit/Loss in points
            rr_multiple: Risk/Reward multiple achieved

        Returns:
            True if notification sent successfully
        """
        is_profit = pnl > 0
        emoji = "💰" if is_profit else "🛑"
        result = "GANANCIA" if is_profit else "PÉRDIDA"

        exit_emoji_map = {
            "TP1": "🎯",
            "TP2": "🎯🎯",
            "TP3": "🎯🎯🎯",
            "STOP_LOSS": "🛑",
            "MANUAL": "👤"
        }
        exit_emoji = exit_emoji_map.get(exit_level, "📤")

        message = f"""
{emoji} <b>BOX STRATEGY - {result}</b>

<b>Market:</b> {market}
<b>Dirección:</b> {direction}
{exit_emoji} <b>Salida:</b> {exit_level}

<b>Precio entrada:</b> ${entry_price:.2f}
<b>Precio salida:</b> ${exit_price:.2f}

<b>P&L:</b> ${pnl:,.2f}
<b>Puntos:</b> {pnl_points:+.2f}
<b>R:R:</b> {rr_multiple:.2f}x

<i>{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</i>
"""

        return self.send_message(message.strip(), send_to_personal=True)

    def send_pupupuv3_trade_notification(
        self,
        symbol: str,
        direction: str,
        entry_price: float,
        stop_loss: float,
        tp1: float,
        tp2_price: float,
        tp2_ratio: float,
        tp2_probability: float,
        tp2_timeframe: str,
        tp3_price: float,
        tp3_ratio: float,
        tp3_probability: float,
        tp3_timeframe: str,
        risk_amount: float,
        position_size: float,
        ml_confidence: float,
        conditions_met: dict = None
    ) -> bool:
        """
        Send a PupupuV3 scalping strategy trade notification

        Args:
            symbol: Trading pair (e.g., BTC/USDT)
            direction: LONG or SHORT
            entry_price: Entry price
            stop_loss: Stop loss level
            tp1: Take profit 1 (50% exit + BE)
            tp2_price: Take profit 2 price (ML predicted)
            tp2_ratio: TP2 risk/reward ratio
            tp2_probability: ML probability for TP2
            tp2_timeframe: Estimated timeframe for TP2
            tp3_price: Take profit 3 price (ML predicted)
            tp3_ratio: TP3 risk/reward ratio
            tp3_probability: ML probability for TP3
            tp3_timeframe: Estimated timeframe for TP3
            risk_amount: Risk amount in USD
            position_size: Position size
            ml_confidence: Overall ML confidence score (0-1)
            conditions_met: Dictionary of condition checks

        Returns:
            True if notification sent successfully
        """
        emoji = "🟢" if direction == "LONG" else "🔴"
        direction_text = "COMPRA (LONG)" if direction == "LONG" else "VENTA (SHORT)"

        # Calculate risk/reward for TP1
        risk_points = abs(entry_price - stop_loss)
        rr1 = abs(tp1 - entry_price) / risk_points if risk_points > 0 else 0

        # ML confidence indicator
        ml_emoji = "🎯" if ml_confidence >= 0.80 else "⚡" if ml_confidence >= 0.70 else "⚠️"
        ml_level = "ALTA" if ml_confidence >= 0.80 else "MEDIA" if ml_confidence >= 0.70 else "BAJA"

        # Conditions section (if provided)
        conditions_section = ""
        if conditions_met:
            checks = []
            if conditions_met.get('touch'):
                checks.append("✅ Pivot Touch")
            if conditions_met.get('ema_test'):
                checks.append("✅ EMA(15) Test")
            if conditions_met.get('vwap_alignment'):
                checks.append("✅ VWAP Alignment")
            if conditions_met.get('volume_profile_support'):
                checks.append("✅ Volume Profile Support")

            if checks:
                conditions_section = f"""
📋 <b>CONDICIONES:</b>
{chr(10).join(checks)}
"""

        message = f"""
{emoji} <b>PUPUPUV3 SCALPING - {direction_text}</b>

<b>Símbolo:</b> {symbol}
<b>Entrada:</b> ${entry_price:,.2f}
<b>Stop Loss:</b> ${stop_loss:,.2f}
<b>Riesgo:</b> ${risk_amount:,.2f}
<b>Tamaño posición:</b> {position_size:.4f}
{ml_emoji} <b>ML Confidence:</b> {ml_level} ({ml_confidence*100:.1f}%)

🎯 <b>TAKE PROFITS (Escalado)</b>

<b>TP1 (50% + move to BE):</b> ${tp1:,.2f}
   └─ R:R {rr1:.2f}x

<b>TP2 (30% exit):</b> ${tp2_price:,.2f}
   └─ R:R {tp2_ratio:.0f}:1 | Prob: {tp2_probability*100:.0f}% | Tiempo: {tp2_timeframe}

<b>TP3 (20% exit):</b> ${tp3_price:,.2f}
   └─ R:R {tp3_ratio:.0f}:1 | Prob: {tp3_probability*100:.0f}% | Tiempo: {tp3_timeframe}
{conditions_section}
<i>{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</i>
"""

        return self.send_message(message.strip(), send_to_personal=True)

    def send_pupupuv3_exit_notification(
        self,
        symbol: str,
        direction: str,
        entry_price: float,
        exit_price: float,
        exit_level: str,
        pnl: float,
        percentage_remaining: float,
        rr_achieved: float
    ) -> bool:
        """
        Send a PupupuV3 partial exit notification

        Args:
            symbol: Trading pair
            direction: LONG or SHORT
            entry_price: Entry price
            exit_price: Exit price
            exit_level: TP1, TP2, TP3, STOP_LOSS, or MANUAL
            pnl: Profit/Loss for this partial exit
            percentage_remaining: Percentage of position still open
            rr_achieved: Risk/reward ratio achieved

        Returns:
            True if notification sent successfully
        """
        is_profit = pnl > 0
        emoji = "💰" if is_profit else "🛑"
        result = "GANANCIA" if is_profit else "PÉRDIDA"

        exit_emoji_map = {
            "TP1": "🎯 (50%)",
            "TP2": "🎯🎯 (30%)",
            "TP3": "🎯🎯🎯 (20%)",
            "STOP_LOSS": "🛑",
            "MANUAL": "👤",
            "BREAK_EVEN": "🟰"
        }
        exit_emoji = exit_emoji_map.get(exit_level, "📤")

        remaining_text = ""
        if percentage_remaining > 0:
            remaining_text = f"\n<b>Posición restante:</b> {percentage_remaining:.0f}%"
        else:
            remaining_text = "\n✅ <b>Posición completamente cerrada</b>"

        message = f"""
{emoji} <b>PUPUPUV3 - {result}</b>

<b>Símbolo:</b> {symbol}
<b>Dirección:</b> {direction}
{exit_emoji} <b>Salida:</b> {exit_level}

<b>Precio entrada:</b> ${entry_price:,.2f}
<b>Precio salida:</b> ${exit_price:,.2f}

<b>P&L (parcial):</b> ${pnl:,.2f}
<b>R:R alcanzado:</b> {rr_achieved:.2f}x{remaining_text}

<i>{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</i>
"""

        return self.send_message(message.strip(), send_to_personal=True)


# Global instance
telegram_service = TelegramService()
