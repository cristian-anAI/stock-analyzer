"""
Position Sizer V3 for PupupuV3 Strategy
Dynamic risk management based on VWAP alignment

Features:
- Full risk ($600) when trading with VWAP bias
- Reduced risk ($300) when trading against VWAP bias (requires ML > 60%)
- 2% base risk of $30,000 capital
- Position size calculation based on stop loss distance
"""

from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class PositionSizeResult:
    """Result of position sizing calculation"""
    position_size_usd: float
    position_size_units: float
    risk_usd: float
    risk_pct: float
    stop_loss_distance_pct: float
    risk_reward_ratio: float
    is_valid: bool
    reason: str


class PositionSizerV3:
    """
    Position sizing calculator for PupupuV3 strategy
    """

    def __init__(
        self,
        capital: float = 30000,
        risk_per_trade_pct: float = 0.02,
        risk_reduced_pct: float = 0.01,
        max_position_size_pct: float = 0.20,
        min_position_size_usd: float = 100
    ):
        """
        Args:
            capital: Total capital available for trading (default: $30,000)
            risk_per_trade_pct: Full risk percentage (default: 2% = $600)
            risk_reduced_pct: Reduced risk percentage (default: 1% = $300)
            max_position_size_pct: Maximum position size as % of capital (default: 20%)
            min_position_size_usd: Minimum position size in USD (default: $100)
        """
        self.capital = capital
        self.risk_per_trade_pct = risk_per_trade_pct
        self.risk_reduced_pct = risk_reduced_pct
        self.max_position_size_pct = max_position_size_pct
        self.min_position_size_usd = min_position_size_usd

        # Calculate risk amounts
        self.full_risk_usd = capital * risk_per_trade_pct
        self.reduced_risk_usd = capital * risk_reduced_pct
        self.max_position_size_usd = capital * max_position_size_pct

    def calculate_position_size(
        self,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        risk_multiplier: float = 1.0,
        direction: str = "LONG"
    ) -> PositionSizeResult:
        """
        Calculate position size based on entry, SL, and TP

        Args:
            entry_price: Entry price for the trade
            stop_loss: Stop loss price
            take_profit: Take profit price
            risk_multiplier: 1.0 for full risk, 0.5 for reduced risk
            direction: 'LONG' or 'SHORT'

        Returns:
            PositionSizeResult with all calculations
        """
        # Validate inputs
        if entry_price <= 0 or stop_loss <= 0 or take_profit <= 0:
            return PositionSizeResult(
                position_size_usd=0.0,
                position_size_units=0.0,
                risk_usd=0.0,
                risk_pct=0.0,
                stop_loss_distance_pct=0.0,
                risk_reward_ratio=0.0,
                is_valid=False,
                reason="Invalid prices (must be > 0)"
            )

        # Calculate stop loss distance
        if direction == "LONG":
            if stop_loss >= entry_price:
                return PositionSizeResult(
                    position_size_usd=0.0,
                    position_size_units=0.0,
                    risk_usd=0.0,
                    risk_pct=0.0,
                    stop_loss_distance_pct=0.0,
                    risk_reward_ratio=0.0,
                    is_valid=False,
                    reason="Invalid LONG: SL must be < entry"
                )
            stop_loss_distance = entry_price - stop_loss
            take_profit_distance = take_profit - entry_price
        else:  # SHORT
            if stop_loss <= entry_price:
                return PositionSizeResult(
                    position_size_usd=0.0,
                    position_size_units=0.0,
                    risk_usd=0.0,
                    risk_pct=0.0,
                    stop_loss_distance_pct=0.0,
                    risk_reward_ratio=0.0,
                    is_valid=False,
                    reason="Invalid SHORT: SL must be > entry"
                )
            stop_loss_distance = stop_loss - entry_price
            take_profit_distance = entry_price - take_profit

        # Validate distances
        if take_profit_distance <= 0:
            return PositionSizeResult(
                position_size_usd=0.0,
                position_size_units=0.0,
                risk_usd=0.0,
                risk_pct=0.0,
                stop_loss_distance_pct=0.0,
                risk_reward_ratio=0.0,
                is_valid=False,
                reason="Invalid TP distance"
            )

        # Calculate risk amount based on multiplier
        risk_usd = self.full_risk_usd * risk_multiplier

        # Calculate position size
        # Position Size = Risk Amount / Stop Loss Distance (in price)
        # Then convert to USD value
        if stop_loss_distance > 0:
            position_size_units = risk_usd / stop_loss_distance
            position_size_usd = position_size_units * entry_price
        else:
            return PositionSizeResult(
                position_size_usd=0.0,
                position_size_units=0.0,
                risk_usd=0.0,
                risk_pct=0.0,
                stop_loss_distance_pct=0.0,
                risk_reward_ratio=0.0,
                is_valid=False,
                reason="Stop loss distance is zero"
            )

        # Check minimum position size
        if position_size_usd < self.min_position_size_usd:
            return PositionSizeResult(
                position_size_usd=position_size_usd,
                position_size_units=position_size_units,
                risk_usd=risk_usd,
                risk_pct=(risk_usd / self.capital) * 100,
                stop_loss_distance_pct=(stop_loss_distance / entry_price) * 100,
                risk_reward_ratio=take_profit_distance / stop_loss_distance,
                is_valid=False,
                reason=f"Position size ${position_size_usd:.2f} below minimum ${self.min_position_size_usd}"
            )

        # Check maximum position size
        if position_size_usd > self.max_position_size_usd:
            return PositionSizeResult(
                position_size_usd=position_size_usd,
                position_size_units=position_size_units,
                risk_usd=risk_usd,
                risk_pct=(risk_usd / self.capital) * 100,
                stop_loss_distance_pct=(stop_loss_distance / entry_price) * 100,
                risk_reward_ratio=take_profit_distance / stop_loss_distance,
                is_valid=False,
                reason=f"Position size ${position_size_usd:.2f} exceeds maximum ${self.max_position_size_usd:.2f}"
            )

        # Calculate percentages and ratios
        stop_loss_distance_pct = (stop_loss_distance / entry_price) * 100
        risk_reward_ratio = take_profit_distance / stop_loss_distance
        actual_risk_pct = (risk_usd / self.capital) * 100

        # All checks passed
        return PositionSizeResult(
            position_size_usd=position_size_usd,
            position_size_units=position_size_units,
            risk_usd=risk_usd,
            risk_pct=actual_risk_pct,
            stop_loss_distance_pct=stop_loss_distance_pct,
            risk_reward_ratio=risk_reward_ratio,
            is_valid=True,
            reason="Position size calculated successfully"
        )

    def get_risk_multiplier(
        self,
        with_vwap_bias: bool,
        ml_confidence: float
    ) -> float:
        """
        Determine risk multiplier based on VWAP alignment and ML confidence

        Rules:
        - With VWAP bias: 1.0 (full risk)
        - Against VWAP bias + ML > 60%: 0.5 (reduced risk)
        - Against VWAP bias + ML <= 60%: 0.0 (no trade)

        Args:
            with_vwap_bias: True if trading with VWAP bias
            ml_confidence: ML prediction confidence (0-100)

        Returns:
            Risk multiplier (0.0, 0.5, or 1.0)
        """
        if with_vwap_bias:
            return 1.0
        elif ml_confidence > 60.0:
            return 0.5
        else:
            return 0.0


def format_position_result(result: PositionSizeResult) -> str:
    """Format position size result for display"""
    if not result.is_valid:
        return f"[INVALID] {result.reason}"

    return f"""
Position Size: ${result.position_size_usd:,.2f} ({result.position_size_units:.4f} units)
Risk: ${result.risk_usd:.2f} ({result.risk_pct:.2f}% of capital)
Stop Loss Distance: {result.stop_loss_distance_pct:.2f}%
Risk:Reward Ratio: 1:{result.risk_reward_ratio:.2f}
Status: VALID
"""


# Test function
if __name__ == "__main__":
    print("Testing Position Sizer V3...")

    sizer = PositionSizerV3(capital=30000)

    print(f"\nCapital: ${sizer.capital:,}")
    print(f"Full Risk: ${sizer.full_risk_usd:.2f} ({sizer.risk_per_trade_pct * 100}%)")
    print(f"Reduced Risk: ${sizer.reduced_risk_usd:.2f} ({sizer.risk_reduced_pct * 100}%)")
    print(f"Max Position Size: ${sizer.max_position_size_usd:,.2f}")

    # Test cases
    test_cases = [
        {
            'name': 'LONG with full risk (with VWAP bias)',
            'entry': 43000,
            'sl': 42980,
            'tp': 43020,
            'risk_mult': 1.0,
            'direction': 'LONG'
        },
        {
            'name': 'LONG with reduced risk (against VWAP, ML > 60%)',
            'entry': 43000,
            'sl': 42980,
            'tp': 43020,
            'risk_mult': 0.5,
            'direction': 'LONG'
        },
        {
            'name': 'SHORT with full risk',
            'entry': 43000,
            'sl': 43025,
            'tp': 42975,
            'risk_mult': 1.0,
            'direction': 'SHORT'
        },
        {
            'name': 'LONG with invalid SL (SL > Entry)',
            'entry': 43000,
            'sl': 43020,
            'tp': 43040,
            'risk_mult': 1.0,
            'direction': 'LONG'
        },
        {
            'name': 'LONG with very tight SL (too large position)',
            'entry': 43000,
            'sl': 42999,
            'tp': 43001,
            'risk_mult': 1.0,
            'direction': 'LONG'
        }
    ]

    for test in test_cases:
        print(f"\n{'=' * 60}")
        print(f"TEST: {test['name']}")
        print(f"{'=' * 60}")
        print(f"Entry: ${test['entry']:.2f}")
        print(f"SL: ${test['sl']:.2f}")
        print(f"TP: ${test['tp']:.2f}")
        print(f"Risk Multiplier: {test['risk_mult']}")
        print(f"Direction: {test['direction']}")

        result = sizer.calculate_position_size(
            entry_price=test['entry'],
            stop_loss=test['sl'],
            take_profit=test['tp'],
            risk_multiplier=test['risk_mult'],
            direction=test['direction']
        )

        print(format_position_result(result))

    # Test risk multiplier logic
    print(f"\n{'=' * 60}")
    print("RISK MULTIPLIER TESTS")
    print(f"{'=' * 60}")

    test_scenarios = [
        ("With VWAP bias", True, 50.0),
        ("Against VWAP, ML 70%", False, 70.0),
        ("Against VWAP, ML 50%", False, 50.0),
        ("With VWAP, ML 30%", True, 30.0),
    ]

    for name, with_bias, ml_conf in test_scenarios:
        mult = sizer.get_risk_multiplier(with_bias, ml_conf)
        risk = sizer.full_risk_usd * mult
        print(f"\n{name}")
        print(f"  With VWAP: {with_bias} | ML: {ml_conf}%")
        print(f"  Multiplier: {mult} | Risk: ${risk:.2f}")

    print("\n[OK] Position Sizer V3 tests complete")
