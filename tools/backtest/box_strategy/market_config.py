"""
Global Market Configuration for Box Strategy

Defines market-specific parameters including:
- Trading symbols
- Timezones
- Market hours
- Contract specifications
- Point values
"""

from dataclasses import dataclass
from typing import Tuple
from zoneinfo import ZoneInfo


@dataclass
class MarketConfig:
    """Configuration for a specific market"""

    # Identification
    code: str              # Market code (e.g., 'SPX', 'DAX')
    name: str              # Full market name
    symbol: str            # Yahoo Finance symbol

    # Timezone and hours
    timezone: ZoneInfo     # Market timezone
    market_open: str       # Market open time (HH:MM)
    market_close: str      # Market close time (HH:MM)

    # Box strategy parameters
    box_start_offset_minutes: int  # Minutes before market open for box start
    box_duration_minutes: int      # Box formation period in minutes

    # Contract specifications
    point_value: float     # Dollar/Euro value per point
    currency: str          # Contract currency
    tick_size: float       # Minimum price movement

    # Risk parameters
    typical_box_range: Tuple[float, float]  # Min, Max typical box range
    recommended_slippage: float             # Typical slippage in points

    # Market characteristics
    avg_daily_volume: str  # Typical volume description
    liquidity_rating: int  # 1-5, 5 being most liquid


# Global market configurations
MARKETS = {
    'SPX': MarketConfig(
        code='SPX',
        name='S&P 500 E-mini Futures',
        symbol='ES=F',
        timezone=ZoneInfo('America/New_York'),
        market_open='09:30',
        market_close='16:00',
        box_start_offset_minutes=-60,  # 8:30 AM (1 hour before open)
        box_duration_minutes=90,        # 1.5 hours
        point_value=50.0,
        currency='USD',
        tick_size=0.25,
        typical_box_range=(5.0, 40.0),
        recommended_slippage=1.0,
        avg_daily_volume='High',
        liquidity_rating=5
    ),

    'NDX': MarketConfig(
        code='NDX',
        name='NASDAQ 100 E-mini Futures',
        symbol='NQ=F',
        timezone=ZoneInfo('America/New_York'),
        market_open='09:30',
        market_close='16:00',
        box_start_offset_minutes=-60,
        box_duration_minutes=90,
        point_value=20.0,  # $20 per point for NQ
        currency='USD',
        tick_size=0.25,
        typical_box_range=(10.0, 100.0),
        recommended_slippage=1.0,
        avg_daily_volume='Very High',
        liquidity_rating=5
    ),

    'DAX': MarketConfig(
        code='DAX',
        name='DAX 40 Futures',
        symbol='FDAX=F',
        timezone=ZoneInfo('Europe/Berlin'),
        market_open='09:00',
        market_close='17:30',
        box_start_offset_minutes=-60,  # 8:00 AM
        box_duration_minutes=90,
        point_value=25.0,  # €25 per point
        currency='EUR',
        tick_size=0.5,
        typical_box_range=(10.0, 80.0),
        recommended_slippage=2.0,
        avg_daily_volume='Very High',
        liquidity_rating=5
    ),

    'FTSE': MarketConfig(
        code='FTSE',
        name='FTSE 100 Index',
        symbol='^FTSE',
        timezone=ZoneInfo('Europe/London'),
        market_open='08:00',
        market_close='16:30',
        box_start_offset_minutes=-60,  # 7:00 AM
        box_duration_minutes=90,
        point_value=10.0,  # £10 per point
        currency='GBP',
        tick_size=0.5,
        typical_box_range=(10.0, 60.0),
        recommended_slippage=1.5,
        avg_daily_volume='High',
        liquidity_rating=4
    ),

    'CAC': MarketConfig(
        code='CAC',
        name='CAC 40 Index',
        symbol='^FCHI',
        timezone=ZoneInfo('Europe/Paris'),
        market_open='09:00',
        market_close='17:30',
        box_start_offset_minutes=-60,  # 8:00 AM
        box_duration_minutes=90,
        point_value=10.0,  # €10 per point
        currency='EUR',
        tick_size=0.5,
        typical_box_range=(8.0, 50.0),
        recommended_slippage=1.5,
        avg_daily_volume='Medium-High',
        liquidity_rating=4
    ),

    'STOXX': MarketConfig(
        code='STOXX',
        name='Euro Stoxx 50',
        symbol='^STOXX50E',
        timezone=ZoneInfo('Europe/Berlin'),
        market_open='09:00',
        market_close='17:30',
        box_start_offset_minutes=-60,
        box_duration_minutes=90,
        point_value=10.0,  # €10 per point
        currency='EUR',
        tick_size=1.0,
        typical_box_range=(5.0, 40.0),
        recommended_slippage=1.0,
        avg_daily_volume='High',
        liquidity_rating=4
    ),

    'NKY': MarketConfig(
        code='NKY',
        name='Nikkei 225 Futures',
        symbol='NKD=F',
        timezone=ZoneInfo('Asia/Tokyo'),
        market_open='09:00',
        market_close='15:15',
        box_start_offset_minutes=-60,  # 8:00 AM JST
        box_duration_minutes=90,
        point_value=5.0,  # ¥500 per point (mini contract)
        currency='JPY',
        tick_size=5.0,
        typical_box_range=(50.0, 300.0),
        recommended_slippage=10.0,
        avg_daily_volume='High',
        liquidity_rating=4
    ),

    'HSI': MarketConfig(
        code='HSI',
        name='Hang Seng Index',
        symbol='^HSI',
        timezone=ZoneInfo('Asia/Hong_Kong'),
        market_open='09:30',
        market_close='16:00',
        box_start_offset_minutes=-60,  # 8:30 AM HKT
        box_duration_minutes=90,
        point_value=50.0,  # HK$50 per point
        currency='HKD',
        tick_size=1.0,
        typical_box_range=(50.0, 300.0),
        recommended_slippage=5.0,
        avg_daily_volume='High',
        liquidity_rating=4
    ),

    'ASX': MarketConfig(
        code='ASX',
        name='ASX 200 Index',
        symbol='^AXJO',
        timezone=ZoneInfo('Australia/Sydney'),
        market_open='10:00',
        market_close='16:00',
        box_start_offset_minutes=-60,  # 9:00 AM AEST
        box_duration_minutes=90,
        point_value=25.0,  # A$25 per point
        currency='AUD',
        tick_size=1.0,
        typical_box_range=(5.0, 40.0),
        recommended_slippage=1.5,
        avg_daily_volume='Medium-High',
        liquidity_rating=3
    ),

    'IBEX': MarketConfig(
        code='IBEX',
        name='IBEX 35 Index',
        symbol='^IBEX',
        timezone=ZoneInfo('Europe/Madrid'),
        market_open='09:00',
        market_close='17:30',
        box_start_offset_minutes=-60,  # 8:00 AM CET
        box_duration_minutes=90,
        point_value=10.0,  # €10 per point
        currency='EUR',
        tick_size=1.0,
        typical_box_range=(10.0, 60.0),
        recommended_slippage=2.0,
        avg_daily_volume='Medium',
        liquidity_rating=3
    ),
}


# Market groups by region
MARKET_REGIONS = {
    'AMERICAS': ['SPX', 'NDX'],
    'EUROPE': ['DAX', 'FTSE', 'CAC', 'STOXX', 'IBEX'],
    'ASIA_PACIFIC': ['NKY', 'HSI', 'ASX']
}


# Currency conversion rates (approximate, for display purposes)
# For real trading, use live forex rates
CURRENCY_TO_USD = {
    'USD': 1.0,
    'EUR': 1.10,
    'GBP': 1.27,
    'JPY': 0.0067,
    'HKD': 0.13,
    'AUD': 0.66
}


def get_market_config(market_code: str) -> MarketConfig:
    """
    Get configuration for a specific market

    Args:
        market_code: Market code (e.g., 'SPX', 'DAX')

    Returns:
        MarketConfig object

    Raises:
        ValueError: If market code not found
    """
    if market_code not in MARKETS:
        raise ValueError(
            f"Unknown market code: {market_code}. "
            f"Available markets: {list(MARKETS.keys())}"
        )

    return MARKETS[market_code]


def get_markets_by_region(region: str) -> list:
    """
    Get list of market codes for a specific region

    Args:
        region: Region name (AMERICAS, EUROPE, ASIA_PACIFIC)

    Returns:
        List of market codes
    """
    if region not in MARKET_REGIONS:
        raise ValueError(
            f"Unknown region: {region}. "
            f"Available regions: {list(MARKET_REGIONS.keys())}"
        )

    return MARKET_REGIONS[region]


def convert_to_usd(amount: float, currency: str) -> float:
    """
    Convert amount to USD for comparison

    Args:
        amount: Amount in original currency
        currency: Currency code

    Returns:
        Amount in USD
    """
    if currency not in CURRENCY_TO_USD:
        raise ValueError(f"Unknown currency: {currency}")

    return amount * CURRENCY_TO_USD[currency]


def get_all_market_codes() -> list:
    """Get list of all available market codes"""
    return list(MARKETS.keys())


def print_market_summary():
    """Print summary of all configured markets"""
    print("\n" + "="*80)
    print("GLOBAL MARKETS CONFIGURATION")
    print("="*80)

    for region, markets in MARKET_REGIONS.items():
        print(f"\n{region}:")
        print("-" * 80)

        for code in markets:
            config = MARKETS[code]
            print(f"  {code:6s} | {config.name:35s} | "
                  f"{config.symbol:12s} | "
                  f"{config.timezone} | "
                  f"Liquidity: {config.liquidity_rating}/5")

    print("\n" + "="*80)


if __name__ == "__main__":
    print_market_summary()

    # Test market configuration
    print("\n\nTest: DAX Configuration")
    print("-" * 80)
    dax = get_market_config('DAX')
    print(f"Name: {dax.name}")
    print(f"Symbol: {dax.symbol}")
    print(f"Timezone: {dax.timezone}")
    print(f"Market Hours: {dax.market_open} - {dax.market_close}")
    print(f"Point Value: {dax.currency} {dax.point_value}")
    print(f"Typical Box Range: {dax.typical_box_range}")
