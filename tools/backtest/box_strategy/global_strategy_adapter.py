"""
Global Strategy Adapter for Box Strategy

Adapts the box strategy to work with different markets and timezones.
Handles market-specific timing, parameters, and configurations.
"""

from datetime import datetime, time, timedelta
from typing import Optional, Tuple
import pandas as pd

from market_config import get_market_config, MarketConfig
from strategy import BoxStrategy, BoxSetup


class GlobalBoxStrategy(BoxStrategy):
    """
    Timezone-aware Box Strategy adapter for global markets
    """

    def __init__(
        self,
        market_code: str,
        risk_per_trade: float = 0.02,
        min_box_range: Optional[float] = None,
        max_box_range: Optional[float] = None,
        use_volatility_filter: bool = False
    ):
        """
        Initialize Global Box Strategy

        Args:
            market_code: Market code (e.g., 'SPX', 'DAX', 'NKY')
            risk_per_trade: Percentage of account to risk per trade
            min_box_range: Minimum box range (uses market config if None)
            max_box_range: Maximum box range (uses market config if None)
            use_volatility_filter: Whether to apply volatility filter
        """
        # Load market configuration
        self.market_config = get_market_config(market_code)
        self.market_code = market_code

        # Set market-specific parameters
        if min_box_range is None:
            min_box_range = self.market_config.typical_box_range[0]

        if max_box_range is None:
            max_box_range = self.market_config.typical_box_range[1]

        slippage = self.market_config.recommended_slippage

        # Initialize base strategy
        super().__init__(
            risk_per_trade=risk_per_trade,
            slippage_points=slippage,
            min_box_range=min_box_range,
            max_box_range=max_box_range,
            use_volatility_filter=use_volatility_filter
        )

        # Override timezone
        self.et_tz = self.market_config.timezone

    def identify_box(self, df: pd.DataFrame, date: datetime.date) -> Optional[BoxSetup]:
        """
        Identify the box formation for a given day using market-specific timing

        Args:
            df: 5-minute OHLCV data
            date: Trading day

        Returns:
            BoxSetup object or None if invalid
        """
        # Calculate box start time based on market configuration
        market_open_time = datetime.strptime(
            self.market_config.market_open, '%H:%M'
        ).time()

        # Box starts N minutes before market open
        box_start_minutes = (
            market_open_time.hour * 60 +
            market_open_time.minute +
            self.market_config.box_start_offset_minutes
        )

        box_start_hour = box_start_minutes // 60
        box_start_minute = box_start_minutes % 60

        # Create box start datetime
        box_start = datetime.combine(
            date,
            time(box_start_hour, box_start_minute),
            tzinfo=self.market_config.timezone
        )

        # Box duration
        box_end = box_start + timedelta(
            minutes=self.market_config.box_duration_minutes
        )

        # Filter data for box period
        box_data = df[(df.index >= box_start) & (df.index < box_end)].copy()

        if box_data.empty:
            return None

        # Calculate box boundaries
        box_high_val = box_data['High'].max()
        box_low_val = box_data['Low'].min()

        # Ensure scalar values (handle numpy/pandas types)
        if hasattr(box_high_val, 'item'):
            box_high = float(box_high_val.item())
            box_low = float(box_low_val.item())
        else:
            box_high = float(box_high_val)
            box_low = float(box_low_val)

        box_range = box_high - box_low

        # Apply filters
        if box_range < self.min_box_range:
            return None

        if self.use_volatility_filter and box_range > self.max_box_range:
            return None

        return BoxSetup(
            date=date,
            box_high=box_high,
            box_low=box_low,
            box_range=box_range,
            formation_start=box_start,
            formation_end=box_end,
            candles_count=len(box_data)
        )

    def get_market_info(self) -> dict:
        """Get market information summary"""
        return {
            'code': self.market_code,
            'name': self.market_config.name,
            'symbol': self.market_config.symbol,
            'timezone': str(self.market_config.timezone),
            'currency': self.market_config.currency,
            'point_value': self.market_config.point_value,
            'market_hours': f"{self.market_config.market_open} - {self.market_config.market_close}",
            'box_parameters': {
                'start_offset_minutes': self.market_config.box_start_offset_minutes,
                'duration_minutes': self.market_config.box_duration_minutes,
                'min_range': self.min_box_range,
                'max_range': self.max_box_range
            },
            'slippage_points': self.slippage_points,
            'liquidity_rating': self.market_config.liquidity_rating
        }

    def format_price(self, price: float) -> str:
        """
        Format price according to market tick size

        Args:
            price: Price value

        Returns:
            Formatted price string
        """
        tick_size = self.market_config.tick_size

        if tick_size >= 1.0:
            return f"{price:.0f}"
        elif tick_size >= 0.1:
            return f"{price:.1f}"
        elif tick_size >= 0.01:
            return f"{price:.2f}"
        else:
            return f"{price:.4f}"


def create_global_strategy(market_code: str, **kwargs) -> GlobalBoxStrategy:
    """
    Factory function to create a global box strategy

    Args:
        market_code: Market code
        **kwargs: Additional strategy parameters

    Returns:
        GlobalBoxStrategy instance
    """
    return GlobalBoxStrategy(market_code, **kwargs)


# Market-specific strategy presets
STRATEGY_PRESETS = {
    'conservative': {
        'risk_per_trade': 0.01,
        'use_volatility_filter': True
    },
    'moderate': {
        'risk_per_trade': 0.02,
        'use_volatility_filter': False
    },
    'aggressive': {
        'risk_per_trade': 0.03,
        'use_volatility_filter': False
    }
}


def create_preset_strategy(
    market_code: str,
    preset: str = 'moderate'
) -> GlobalBoxStrategy:
    """
    Create strategy with preset parameters

    Args:
        market_code: Market code
        preset: Preset name ('conservative', 'moderate', 'aggressive')

    Returns:
        GlobalBoxStrategy instance
    """
    if preset not in STRATEGY_PRESETS:
        raise ValueError(
            f"Unknown preset: {preset}. "
            f"Available: {list(STRATEGY_PRESETS.keys())}"
        )

    params = STRATEGY_PRESETS[preset]
    return GlobalBoxStrategy(market_code, **params)


if __name__ == "__main__":
    # Test global strategy creation
    print("\n" + "="*80)
    print("GLOBAL STRATEGY ADAPTER TEST")
    print("="*80)

    markets = ['SPX', 'DAX', 'NKY', 'HSI']

    for market_code in markets:
        print(f"\n{market_code}:")
        print("-" * 80)

        strategy = create_global_strategy(market_code)
        info = strategy.get_market_info()

        print(f"  Name: {info['name']}")
        print(f"  Symbol: {info['symbol']}")
        print(f"  Timezone: {info['timezone']}")
        print(f"  Market Hours: {info['market_hours']}")
        print(f"  Point Value: {info['currency']} {info['point_value']}")
        print(f"  Box Range: {info['box_parameters']['min_range']:.1f} - "
              f"{info['box_parameters']['max_range']:.1f} points")
        print(f"  Slippage: {info['slippage_points']:.1f} points")
        print(f"  Liquidity: {info['liquidity_rating']}/5")
