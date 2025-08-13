# crypto_specific_analysis.py
"""
Crypto-specific analysis and scoring logic.
- Higher volatility thresholds
- Adjusted scoring (e.g. RSI < 25 = oversold)
- Weekend/weekday pattern analysis
"""
import datetime

def analyze_crypto_signals(tech_indicators, price_data, classification=None):
    """Returns a buy_score and reasons for a crypto asset, using crypto-specific thresholds."""
    buy_score = 0
    reasons = []
    now = datetime.datetime.utcnow()
    is_weekend = now.weekday() >= 5

    # RSI
    rsi = tech_indicators.get('rsi')
    if rsi is not None:
        if rsi < 25:
            buy_score += 3
            reasons.append(f"RSI very oversold: {rsi:.1f}")
        elif rsi < 35:
            buy_score += 1
            reasons.append(f"RSI favorable: {rsi:.1f}")

    # MACD
    macd = tech_indicators.get('macd')
    macd_signal = tech_indicators.get('macd_signal')
    if macd is not None and macd_signal is not None and macd > macd_signal:
        buy_score += 2
        reasons.append("MACD bullish crossover")

    # Bollinger Bands
    close = price_data.get('close')
    bb_lower = tech_indicators.get('bb_lower')
    if close is not None and bb_lower is not None and close < bb_lower:
        buy_score += 2
        reasons.append("Price below lower Bollinger Band")

    # Volatility (crypto moves 5-20% daily)
    pct_change_24h = price_data.get('pct_change_24h', 0)
    if abs(pct_change_24h) > 10:
        buy_score += 1
        reasons.append(f"High 24h volatility: {pct_change_24h:+.1f}%")

    # Weekend/weekday pattern
    if is_weekend:
        buy_score += 1
        reasons.append("Weekend pattern: higher volatility expected")

    # General classification (optional)
    if classification == 'BULLISH':
        buy_score += 2
        reasons.append("Technical analysis bullish")

    return buy_score, reasons
