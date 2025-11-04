"""
Box Strategy ML Service

Provides ML-powered confidence predictions for box strategy trades across multiple markets.
Integrates with the backtesting ML system to provide real-time trade evaluation.

Features:
- Multi-market support (SPX, NDX, DAX, FTSE, etc.)
- Market hours awareness (different opening times)
- Real-time ML confidence predictions
- Box formation detection
- Trade setup evaluation
"""

import sys
from pathlib import Path
from datetime import datetime, time, timedelta
from typing import Dict, List, Optional, Tuple
import logging
import pytz
from dataclasses import dataclass, asdict

# Add box strategy ML system to path
box_strategy_path = Path(__file__).parent.parent.parent.parent / "tools" / "backtest" / "box_strategy"
sys.path.insert(0, str(box_strategy_path))

try:
    from data_loader import DataLoader
    from ml.ml_predictor import MLPredictor
    ML_AVAILABLE = True
except ImportError as e:
    ML_AVAILABLE = False
    logging.warning(f"Box strategy ML system not available: {e}")

logger = logging.getLogger(__name__)


@dataclass
class MarketConfig:
    """Configuration for a market"""
    code: str
    name: str
    ticker: str  # yfinance ticker
    timezone: str
    box_start: time  # Local market time
    box_end: time
    currency: str = "USD"
    points_per_contract: float = 50.0


# Market configurations with proper timezones and box hours
MARKET_CONFIGS = {
    "SPX": MarketConfig(
        code="SPX",
        name="S&P 500",
        ticker="ES=F",
        timezone="America/New_York",
        box_start=time(8, 30),
        box_end=time(10, 0),
        currency="USD",
        points_per_contract=50.0
    ),
    "NDX": MarketConfig(
        code="NDX",
        name="NASDAQ 100",
        ticker="NQ=F",
        timezone="America/New_York",
        box_start=time(8, 30),
        box_end=time(10, 0),
        currency="USD",
        points_per_contract=20.0
    ),
    "DAX": MarketConfig(
        code="DAX",
        name="DAX",
        ticker="FDAX=F",
        timezone="Europe/Berlin",
        box_start=time(8, 0),
        box_end=time(9, 30),
        currency="EUR",
        points_per_contract=25.0
    ),
    "FTSE": MarketConfig(
        code="FTSE",
        name="FTSE 100",
        ticker="^FTSE",
        timezone="Europe/London",
        box_start=time(8, 0),
        box_end=time(9, 30),
        currency="GBP",
        points_per_contract=10.0
    ),
    "STOXX": MarketConfig(
        code="STOXX",
        name="Euro Stoxx 50",
        ticker="^STOXX50E",
        timezone="Europe/Paris",
        box_start=time(8, 0),
        box_end=time(9, 30),
        currency="EUR",
        points_per_contract=10.0
    ),
    "CAC": MarketConfig(
        code="CAC",
        name="CAC 40",
        ticker="^FCHI",
        timezone="Europe/Paris",
        box_start=time(8, 0),
        box_end=time(9, 30),
        currency="EUR",
        points_per_contract=10.0
    ),
    "NKY": MarketConfig(
        code="NKY",
        name="Nikkei 225",
        ticker="^N225",
        timezone="Asia/Tokyo",
        box_start=time(9, 0),
        box_end=time(10, 30),
        currency="JPY",
        points_per_contract=1000.0
    ),
    "HSI": MarketConfig(
        code="HSI",
        name="Hang Seng",
        ticker="^HSI",
        timezone="Asia/Hong_Kong",
        box_start=time(9, 30),
        box_end=time(11, 0),
        currency="HKD",
        points_per_contract=50.0
    ),
    "ASX": MarketConfig(
        code="ASX",
        name="ASX 200",
        ticker="^AXJO",
        timezone="Australia/Sydney",
        box_start=time(10, 0),
        box_end=time(11, 30),
        currency="AUD",
        points_per_contract=25.0
    ),
    "IBEX": MarketConfig(
        code="IBEX",
        name="IBEX 35",
        ticker="^IBEX",
        timezone="Europe/Madrid",
        box_start=time(9, 0),
        box_end=time(10, 30),
        currency="EUR",
        points_per_contract=10.0
    ),
    "RUT": MarketConfig(
        code="RUT",
        name="Russell 2000",
        ticker="^RUT",
        timezone="America/New_York",
        box_start=time(8, 30),
        box_end=time(10, 0),
        currency="USD",
        points_per_contract=50.0  # Russell 2000 futures
    )
}


@dataclass
class BoxSetup:
    """Box formation and trade setup"""
    market: str
    date: str
    box_high: float
    box_low: float
    box_range: float
    box_midpoint: float
    candles_in_box: int
    current_price: Optional[float] = None
    breakout_detected: bool = False
    direction: Optional[str] = None  # LONG or SHORT
    entry_price: Optional[float] = None
    entry_time: Optional[str] = None  # Timestamp when breakout occurred
    stop_loss: Optional[float] = None
    tp1: Optional[float] = None
    tp2: Optional[float] = None
    tp3: Optional[float] = None
    risk_points: Optional[float] = None
    breakout_candle_time: Optional[str] = None  # First candle that broke the box


@dataclass
class MLPrediction:
    """ML model prediction for trade"""
    win_probability: float
    confidence_level: str  # HIGH, MEDIUM, LOW
    recommendation: str  # TRADE, REDUCE_SIZE, SKIP
    position_size_multiplier: float
    model_used: str
    model_version: str


@dataclass
class MarketStatus:
    """Market status and timing"""
    market: str
    local_time: str
    is_box_period: bool
    is_post_box: bool
    box_complete: bool
    next_box_time: Optional[str] = None
    market_open: bool = True


class BoxStrategyService:
    """Service for box strategy ML predictions"""

    def __init__(self, ml_version: str = "1"):
        """
        Initialize box strategy service

        Args:
            ml_version: ML model version to use
        """
        self.ml_version = ml_version
        self.data_loader = None
        self.ml_predictor = None

        if ML_AVAILABLE:
            try:
                self.data_loader = DataLoader()
                self.ml_predictor = MLPredictor(version=ml_version)
                logger.info(f"Box strategy service initialized (ML version {ml_version})")
            except Exception as e:
                logger.error(f"Failed to initialize ML components: {e}")
                logger.error(f"Error details: {e}")
                self.data_loader = None
                self.ml_predictor = None
        else:
            logger.warning("Box strategy ML not available - running in limited mode")

    def get_market_status(self, market_code: str) -> MarketStatus:
        """
        Get current status for a market

        Args:
            market_code: Market code (SPX, NDX, etc.)

        Returns:
            MarketStatus with timing information
        """
        if market_code not in MARKET_CONFIGS:
            raise ValueError(f"Unknown market: {market_code}")

        config = MARKET_CONFIGS[market_code]
        tz = pytz.timezone(config.timezone)
        now = datetime.now(tz)
        today = now.date()

        # Calculate box period times for today
        box_start_dt = tz.localize(datetime.combine(today, config.box_start))
        box_end_dt = tz.localize(datetime.combine(today, config.box_end))

        is_box_period = box_start_dt <= now <= box_end_dt
        is_post_box = now > box_end_dt
        box_complete = is_post_box

        # Calculate next box time
        if is_post_box:
            # Next box is tomorrow
            next_box = tz.localize(
                datetime.combine(today + timedelta(days=1), config.box_start)
            )
        else:
            # Next box is today (if before box start) or tomorrow
            if now < box_start_dt:
                next_box = box_start_dt
            else:
                next_box = tz.localize(
                    datetime.combine(today + timedelta(days=1), config.box_start)
                )

        return MarketStatus(
            market=market_code,
            local_time=now.isoformat(),
            is_box_period=is_box_period,
            is_post_box=is_post_box,
            box_complete=box_complete,
            next_box_time=next_box.isoformat(),
            market_open=True  # Simplified - could add market calendar check
        )

    def get_box_setup(self, market_code: str, date: Optional[datetime] = None) -> Optional[BoxSetup]:
        """
        Get box formation and setup for a market

        Args:
            market_code: Market code (SPX, NDX, etc.)
            date: Date to analyze (default: today)

        Returns:
            BoxSetup or None if not available
        """
        if not self.data_loader:
            logger.error("Data loader not available")
            return None

        if market_code not in MARKET_CONFIGS:
            raise ValueError(f"Unknown market: {market_code}")

        config = MARKET_CONFIGS[market_code]

        # Download recent data (last 7 days)
        try:
            tz = pytz.timezone(config.timezone)
            end_date = datetime.now(tz)
            start_date = end_date - timedelta(days=7)

            df = self.data_loader.download_5min_data(
                market_code,
                start_date=start_date,
                end_date=end_date,
                force_refresh=True
            )

            if df is None or df.empty:
                logger.warning(f"No data available for {market_code}")
                return None

            # Get today's date
            target_date = date.date() if date else datetime.now(tz).date()

            # Get box period data
            box_data, box_high, box_low = self.data_loader.get_box_period_data(df, target_date)

            if box_data.empty or box_high is None:
                logger.info(f"No box data for {market_code} on {target_date}")
                return None

            box_range = box_high - box_low
            box_midpoint = (box_high + box_low) / 2

            # Get post-box data to detect breakout (first 2 hours only)
            # Box ends at 10:00 AM ET, so we only look until 12:00 PM ET (2 hours window)
            post_box_data = self.data_loader.get_post_box_data(df, target_date, hours=2)

            current_price = None
            breakout_detected = False
            direction = None
            entry_price = None
            entry_time = None
            breakout_candle_time = None
            stop_loss = None
            tp1 = None
            tp2 = None
            tp3 = None
            risk_points = None

            if not post_box_data.empty:
                current_price = float(post_box_data['Close'].iloc[-1])

                # CRITICAL FIX: Detect breakout ONLY when candle CLOSES outside box
                # A breakout is valid only when Close > box_high (LONG) or Close < box_low (SHORT)
                # IMPORTANT: Only within first 2 hours after box (10:00 AM - 12:00 PM ET)

                # Find first candle that CLOSED above box_high (LONG breakout)
                long_breakout_candles = post_box_data[post_box_data['Close'] > box_high]

                # Find first candle that CLOSED below box_low (SHORT breakout)
                short_breakout_candles = post_box_data[post_box_data['Close'] < box_low]

                # Determine which breakout happened first (if any)
                long_breakout_time = None
                short_breakout_time = None

                if not long_breakout_candles.empty:
                    long_breakout_time = long_breakout_candles.index[0]

                    # Validate breakout is within 2-hour window (10:00 AM - 12:00 PM ET)
                    box_end_time = tz.localize(datetime.combine(target_date, datetime.strptime("10:00", "%H:%M").time()))
                    timeout_time = box_end_time + timedelta(hours=2)

                    if long_breakout_time > timeout_time:
                        logger.info(f"{market_code} LONG breakout at {long_breakout_time} is AFTER 2-hour window (timeout: {timeout_time}). Ignoring.")
                        long_breakout_time = None

                if not short_breakout_candles.empty:
                    short_breakout_time = short_breakout_candles.index[0]

                    # Validate breakout is within 2-hour window
                    box_end_time = tz.localize(datetime.combine(target_date, datetime.strptime("10:00", "%H:%M").time()))
                    timeout_time = box_end_time + timedelta(hours=2)

                    if short_breakout_time > timeout_time:
                        logger.info(f"{market_code} SHORT breakout at {short_breakout_time} is AFTER 2-hour window (timeout: {timeout_time}). Ignoring.")
                        short_breakout_time = None

                # Process LONG breakout
                if long_breakout_time is not None:
                    # Check if there was a SHORT breakout earlier
                    if short_breakout_time is None or long_breakout_time < short_breakout_time:
                        breakout_detected = True
                        direction = "LONG"
                        entry_price = box_high
                        stop_loss = box_low
                        risk_points = box_range
                        tp1 = entry_price + (1.0 * risk_points)
                        tp2 = entry_price + (2.0 * risk_points)
                        tp3 = entry_price + (3.0 * risk_points)
                        breakout_candle_time = long_breakout_time.isoformat()
                        entry_time = breakout_candle_time

                        logger.info(f"{market_code} LONG breakout: First candle CLOSED above {box_high:.2f} at {breakout_candle_time}")

                # Process SHORT breakout
                elif short_breakout_time is not None:
                    breakout_detected = True
                    direction = "SHORT"
                    entry_price = box_low
                    stop_loss = box_high
                    risk_points = box_range
                    tp1 = entry_price - (1.0 * risk_points)
                    tp2 = entry_price - (2.0 * risk_points)
                    tp3 = entry_price - (3.0 * risk_points)
                    breakout_candle_time = short_breakout_time.isoformat()
                    entry_time = breakout_candle_time

                    logger.info(f"{market_code} SHORT breakout: First candle CLOSED below {box_low:.2f} at {breakout_candle_time}")

                # No breakout detected
                else:
                    logger.debug(f"{market_code} No breakout: No candle closed outside box range ({box_low:.2f} - {box_high:.2f})")

            return BoxSetup(
                market=market_code,
                date=str(target_date),
                box_high=float(box_high),
                box_low=float(box_low),
                box_range=float(box_range),
                box_midpoint=float(box_midpoint),
                candles_in_box=len(box_data),
                current_price=current_price,
                breakout_detected=breakout_detected,
                direction=direction,
                entry_price=entry_price,
                entry_time=entry_time,
                stop_loss=stop_loss,
                tp1=tp1,
                tp2=tp2,
                tp3=tp3,
                risk_points=risk_points,
                breakout_candle_time=breakout_candle_time
            )

        except Exception as e:
            logger.error(f"Error getting box setup for {market_code}: {e}")
            return None

    def get_ml_prediction(self, box_setup: BoxSetup) -> Optional[MLPrediction]:
        """
        Get ML prediction for a box setup

        Args:
            box_setup: BoxSetup to evaluate

        Returns:
            MLPrediction or None if not available
        """
        if not self.ml_predictor or not box_setup.breakout_detected:
            return None

        try:
            # Prepare setup dict for ML predictor
            setup_dict = {
                'market': box_setup.market,
                'date': box_setup.date,
                'direction': box_setup.direction,
                'entry_price': box_setup.entry_price,
                'stop_loss': box_setup.stop_loss,
                'box_high': box_setup.box_high,
                'box_low': box_setup.box_low,
                'box_range': box_setup.box_range,
                'box_midpoint': box_setup.box_midpoint,
                'risk_amount': box_setup.risk_points,
                'risk_points': box_setup.risk_points,
                'candles_in_box': box_setup.candles_in_box,
            }

            # Download market data for feature extraction
            config = MARKET_CONFIGS[box_setup.market]
            tz = pytz.timezone(config.timezone)
            end_date = datetime.now(tz)
            start_date = end_date - timedelta(days=7)

            market_data = self.data_loader.download_5min_data(
                box_setup.market,
                start_date=start_date,
                end_date=end_date,
                force_refresh=False  # Use cached data
            )

            if market_data is None or market_data.empty:
                logger.warning(f"No market data available for ML prediction: {box_setup.market}")
                return None

            # Get prediction
            result = self.ml_predictor.evaluate_setup(setup_dict, market_data=market_data)

            if not result or 'prediction' not in result:
                logger.warning(f"ML predictor returned invalid result for {box_setup.market}")
                return None

            pred = result['prediction']

            return MLPrediction(
                win_probability=pred.get('win_probability', 0.5),
                confidence_level=pred.get('confidence_level', 'MEDIUM'),
                recommendation=pred.get('recommendation', 'HOLD'),
                position_size_multiplier=pred.get('position_size_multiplier', 0.6),
                model_used=pred.get('model_used', 'unknown'),
                model_version=self.ml_version
            )

        except Exception as e:
            logger.error(f"Error getting ML prediction: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    def get_all_markets_status(self) -> List[Dict]:
        """
        Get status and predictions for all markets

        Returns:
            List of market status dictionaries
        """
        results = []

        for market_code in MARKET_CONFIGS.keys():
            try:
                # Get market status
                status = self.get_market_status(market_code)

                # Get box setup if box is complete
                box_setup = None
                ml_prediction = None

                if status.box_complete:
                    box_setup = self.get_box_setup(market_code)

                    if box_setup and box_setup.breakout_detected:
                        ml_prediction = self.get_ml_prediction(box_setup)

                # Build result
                result = {
                    'market': market_code,
                    'name': MARKET_CONFIGS[market_code].name,
                    'timezone': MARKET_CONFIGS[market_code].timezone,
                    'status': asdict(status),
                    'box_setup': asdict(box_setup) if box_setup else None,
                    'ml_prediction': asdict(ml_prediction) if ml_prediction else None
                }

                results.append(result)

            except Exception as e:
                logger.error(f"Error getting status for {market_code}: {e}")
                results.append({
                    'market': market_code,
                    'name': MARKET_CONFIGS[market_code].name,
                    'error': str(e)
                })

        return results

    def get_tradeable_setups(self) -> List[Dict]:
        """
        Get only markets with tradeable setups (box complete + breakout detected)

        Returns:
            List of tradeable setup dictionaries
        """
        all_markets = self.get_all_markets_status()

        tradeable = [
            m for m in all_markets
            if m.get('box_setup') and m['box_setup'].get('breakout_detected')
        ]

        return tradeable
