"""
Position Sizing and Risk Management

Calculates position size based on fixed risk percentage of account balance.
"""

from typing import Dict, Optional


def calculate_position_size(
    account_balance: float,
    risk_percent: float,
    entry_price: float,
    stop_loss: float,
    max_position_usd: Optional[float] = None
) -> Dict[str, float]:
    """
    Calculate position size based on fixed risk.

    Formula:
    - Risk amount = account_balance * risk_percent
    - Position size = risk_amount / (|entry - stop_loss| / entry)

    Args:
        account_balance: Total capital in USD
        risk_percent: % of capital to risk (0.01 = 1%, 0.02 = 2%)
        entry_price: Trade entry price
        stop_loss: Stop loss price
        max_position_usd: Optional max position size (position sizing cap)

    Returns:
        {
            'position_size_usd': amount in USD,
            'position_size_btc': amount in BTC (for crypto),
            'risk_usd': dollar amount at risk,
            'risk_pct': percentage of account at risk
        }
    """
    # Calculate risk amount in dollars
    risk_usd = account_balance * risk_percent

    # Calculate price distance (risk per unit)
    price_diff = abs(entry_price - stop_loss)

    if price_diff == 0:
        return {
            'position_size_usd': 0,
            'position_size_btc': 0,
            'risk_usd': 0,
            'risk_pct': 0
        }

    # Position size = risk / (stop distance in %)
    stop_distance_pct = price_diff / entry_price
    position_size_usd = risk_usd / stop_distance_pct

    # Apply max position cap if specified
    if max_position_usd and position_size_usd > max_position_usd:
        position_size_usd = max_position_usd
        # Recalculate actual risk with capped position
        risk_usd = position_size_usd * stop_distance_pct

    # Calculate BTC amount
    position_size_btc = position_size_usd / entry_price

    return {
        'position_size_usd': round(position_size_usd, 2),
        'position_size_btc': round(position_size_btc, 6),
        'risk_usd': round(risk_usd, 2),
        'risk_pct': round((risk_usd / account_balance) * 100, 2)
    }


def calculate_leverage_required(
    position_size_usd: float,
    available_margin: float
) -> float:
    """
    Calculate leverage required for position.

    Args:
        position_size_usd: Total position size
        available_margin: Available margin/capital

    Returns:
        Leverage multiplier (e.g., 3.5 = 3.5x)
    """
    if available_margin == 0:
        return 0

    return position_size_usd / available_margin


def validate_risk_limits(
    position_size_usd: float,
    risk_usd: float,
    account_balance: float,
    max_risk_per_trade: float = 0.02,
    max_position_size_pct: float = 0.25
) -> Dict[str, any]:
    """
    Validate if trade respects risk limits.

    Args:
        position_size_usd: Calculated position size
        risk_usd: Dollar risk amount
        account_balance: Total account balance
        max_risk_per_trade: Max % risk per trade (default: 2%)
        max_position_size_pct: Max position as % of account (default: 25%)

    Returns:
        {
            'valid': bool,
            'violations': list of violated rules,
            'warnings': list of warnings
        }
    """
    violations = []
    warnings = []

    # Check risk percentage
    actual_risk_pct = risk_usd / account_balance
    if actual_risk_pct > max_risk_per_trade:
        violations.append(
            f"Risk {actual_risk_pct:.1%} exceeds max {max_risk_per_trade:.1%}"
        )

    # Check position size percentage
    position_pct = position_size_usd / account_balance
    if position_pct > max_position_size_pct:
        violations.append(
            f"Position size {position_pct:.1%} exceeds max {max_position_size_pct:.1%}"
        )

    # Warnings for edge cases
    if actual_risk_pct > max_risk_per_trade * 0.8:
        warnings.append(f"Risk approaching limit: {actual_risk_pct:.1%}")

    if position_pct > max_position_size_pct * 0.8:
        warnings.append(f"Position size approaching limit: {position_pct:.1%}")

    return {
        'valid': len(violations) == 0,
        'violations': violations,
        'warnings': warnings
    }


def calculate_potential_pnl(
    entry_price: float,
    exit_price: float,
    position_size_btc: float,
    direction: str = "LONG"
) -> float:
    """
    Calculate potential P&L for a trade.

    Args:
        entry_price: Entry price
        exit_price: Exit price (TP or SL)
        position_size_btc: Position size in BTC
        direction: "LONG" or "SHORT"

    Returns:
        P&L in USD (positive = profit, negative = loss)
    """
    if direction == "LONG":
        pnl = (exit_price - entry_price) * position_size_btc
    else:  # SHORT
        pnl = (entry_price - exit_price) * position_size_btc

    return round(pnl, 2)


# Testing
if __name__ == "__main__":
    print("="*70)
    print("TESTING POSITION SIZER")
    print("="*70)

    # Test scenario: $10,000 account, 2% risk
    account = 10000
    risk = 0.02  # 2%

    # Example trade: BTC at $112,000 with SL at $111,500
    entry = 112000
    sl = 111500

    print(f"\nAccount balance: ${account:,.2f}")
    print(f"Risk per trade: {risk:.1%}")
    print(f"Entry: ${entry:,.2f}")
    print(f"Stop Loss: ${sl:,.2f}")
    print(f"Risk distance: ${abs(entry - sl):,.2f} ({abs(entry-sl)/entry*100:.2f}%)")

    # Calculate position size
    sizing = calculate_position_size(account, risk, entry, sl)

    print(f"\n[POSITION SIZING]")
    print(f"Position size: ${sizing['position_size_usd']:,.2f}")
    print(f"Position size: {sizing['position_size_btc']:.6f} BTC")
    print(f"Risk amount: ${sizing['risk_usd']:,.2f} ({sizing['risk_pct']:.2f}%)")

    # Calculate leverage needed
    leverage = calculate_leverage_required(sizing['position_size_usd'], account)
    print(f"Leverage required: {leverage:.2f}x")

    # Validate risk limits
    validation = validate_risk_limits(
        sizing['position_size_usd'],
        sizing['risk_usd'],
        account
    )

    print(f"\n[RISK VALIDATION]")
    print(f"Valid: {validation['valid']}")
    if validation['violations']:
        print(f"Violations: {', '.join(validation['violations'])}")
    if validation['warnings']:
        print(f"Warnings: {', '.join(validation['warnings'])}")

    # Calculate potential P&L
    tp = entry + (abs(entry - sl) * 1.7)  # 1.7 R:R
    pnl_tp = calculate_potential_pnl(entry, tp, sizing['position_size_btc'], "LONG")
    pnl_sl = calculate_potential_pnl(entry, sl, sizing['position_size_btc'], "LONG")

    print(f"\n[POTENTIAL P&L]")
    print(f"If TP hit (${tp:,.2f}): +${pnl_tp:,.2f}")
    print(f"If SL hit (${sl:,.2f}): -${abs(pnl_sl):,.2f}")
    print(f"Risk:Reward ratio: 1:{abs(pnl_tp/pnl_sl):.2f}")

    print("\n" + "="*70)
