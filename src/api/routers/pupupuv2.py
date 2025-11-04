"""
PupupuV2 API Router

Endpoints para monitorear señales de trading, pivotes activos,
y análisis en tiempo real del bot pupupuv2.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Optional, List, Dict
from datetime import datetime, timedelta
import json
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from src.data.binance_client import BinanceDataClient
from src.strategy.pupupuv2_signals import PupupuV2Strategy, TradeSignal
from src.indicators.volume_profile import get_multi_timeframe_vp
from src.risk.position_sizer import calculate_position_size
from src.filters.market_context import apply_all_filters
from src.indicators.ema import calculate_ema

router = APIRouter(prefix="/api/v1/pupupuv2", tags=["PupupuV2"])

# Global state (in production, use Redis or database)
_bot_state = {
    'last_analysis_time': None,
    'last_signal': None,
    'active_levels': None,
    'market_context': None,
    'is_monitoring': False
}

# Initialize components
binance_client = BinanceDataClient()
strategy = PupupuV2Strategy({
    'ema_period': 12,
    'lookback_periods': 400,
    'tp_rr': 1.7,
    'sl_padding': 2.5
})


@router.get("/health")
async def health_check():
    """Check if pupupuv2 API is running."""
    return {
        'status': 'healthy',
        'service': 'pupupuv2',
        'timestamp': datetime.now().isoformat(),
        'is_monitoring': _bot_state['is_monitoring']
    }


@router.get("/current-analysis")
async def get_current_analysis(
    account_balance: float = 10000,
    risk_per_trade: float = 0.02
):
    """
    Run fresh analysis on current market conditions.

    Returns:
    - Current price & EMA
    - Active pivots (supports & resistances)
    - Volume Profile nodes
    - Trade signal (if setup exists)
    - Market filters status
    """
    try:
        # 1. Fetch fresh data
        data = binance_client.fetch_multiple_timeframes(
            'BTC/USDT',
            ['5m', '1h'],
            limit=500
        )

        ohlcv_5m = data['5m']
        ohlcv_1h = data['1h']

        if ohlcv_5m is None:
            raise HTTPException(status_code=500, detail="Could not fetch market data")

        current_price = float(ohlcv_5m[-1, 4])
        current_timestamp = datetime.fromtimestamp(ohlcv_5m[-1, 0] / 1000)

        # 2. Calculate EMA
        closes = ohlcv_5m[:, 4]
        ema_values = calculate_ema(closes, 12)
        current_ema = float(ema_values[-1])

        # 3. Calculate Volume Profile
        vp_data = None
        try:
            vp_data = get_multi_timeframe_vp(ohlcv_5m[-500:], num_bins=60)
        except Exception as e:
            print(f"VP calculation warning: {e}")

        # 4. Analyze for signals
        signal = strategy.analyze_for_signals(ohlcv_5m, vp_data)

        # 5. Get active levels
        levels = strategy.get_active_levels()

        # 6. Apply market filters
        current_candle = {
            'timestamp': ohlcv_5m[-1, 0],
            'open': ohlcv_5m[-1, 1],
            'high': ohlcv_5m[-1, 2],
            'low': ohlcv_5m[-1, 3],
            'close': ohlcv_5m[-1, 4],
            'volume': ohlcv_5m[-1, 5]
        }

        filters = apply_all_filters(current_candle, ohlcv_5m, ohlcv_1h)

        # 7. Calculate position size if there's a signal
        signal_dict = None
        if signal:
            sizing = calculate_position_size(
                account_balance,
                risk_per_trade,
                signal.entry_price,
                signal.stop_loss
            )
            signal.position_size_usd = sizing['position_size_usd']
            signal.risk_usd = sizing['risk_usd']

            signal_dict = signal.to_dict()

        # Update global state
        _bot_state['last_analysis_time'] = datetime.now()
        _bot_state['last_signal'] = signal
        _bot_state['active_levels'] = levels
        _bot_state['market_context'] = filters

        # Format response
        response = {
            'timestamp': current_timestamp.isoformat(),
            'current_price': current_price,
            'current_ema': current_ema,
            'price_vs_ema': 'above' if current_price > current_ema else 'below',
            'distance_from_ema_pct': ((current_price - current_ema) / current_ema) * 100,

            'signal': signal_dict,

            'active_resistances': [
                {
                    'price': float(p.price),
                    'strength': float(p.strength),
                    'touches': int(p.touches),
                    'age_candles': int(p.candles_age),
                    'distance_pct': ((p.price - current_price) / current_price) * 100
                }
                for p in levels['resistances'][:5]
            ],

            'active_supports': [
                {
                    'price': float(p.price),
                    'strength': float(p.strength),
                    'touches': int(p.touches),
                    'age_candles': int(p.candles_age),
                    'distance_pct': ((current_price - p.price) / current_price) * 100
                }
                for p in levels['supports'][:5]
            ],

            'volume_profile': {
                'vp_corto': {
                    'poc': float(vp_data['vp_corto']['poc']),
                    'vah': float(vp_data['vp_corto']['vah']),
                    'val': float(vp_data['vp_corto']['val']),
                    'hvn_count': len(vp_data['vp_corto']['hvn']),
                    'lvn_count': len(vp_data['vp_corto']['lvn'])
                } if vp_data and vp_data.get('vp_corto') else None,

                'vp_medio': {
                    'poc': float(vp_data['vp_medio']['poc']),
                    'vah': float(vp_data['vp_medio']['vah']),
                    'val': float(vp_data['vp_medio']['val']),
                    'hvn_count': len(vp_data['vp_medio']['hvn']),
                    'lvn_count': len(vp_data['vp_medio']['lvn'])
                } if vp_data and vp_data.get('vp_medio') else None
            },

            'market_filters': {
                'pass_all': filters['pass_all'],
                'fundamental_event': filters['fundamental_event'][0],
                'fundamental_event_description': filters['fundamental_event'][1] if filters['fundamental_event'][0] else None,
                'liquidity_ok': filters['liquidity'][0],
                'volatility_ok': filters['volatility'][0],
                'ht_trend': filters['ht_trend'][0]
            },

            'metadata': {
                'total_resistances': len(levels['resistances']),
                'total_supports': len(levels['supports']),
                'data_candles': len(ohlcv_5m),
                'analysis_time': datetime.now().isoformat()
            }
        }

        return JSONResponse(content=response)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis error: {str(e)}")


@router.get("/signals/latest")
async def get_latest_signals(limit: int = 10):
    """
    Get latest generated signals from disk.

    Query params:
    - limit: Max number of signals to return (default: 10)
    """
    try:
        signals_dir = 'signals'

        if not os.path.exists(signals_dir):
            return {'signals': [], 'count': 0}

        # Get all signal files
        signal_files = [
            f for f in os.listdir(signals_dir)
            if f.startswith('signal_') and f.endswith('.json')
        ]

        # Sort by modification time (newest first)
        signal_files.sort(
            key=lambda f: os.path.getmtime(os.path.join(signals_dir, f)),
            reverse=True
        )

        # Read signals
        signals = []
        for filename in signal_files[:limit]:
            filepath = os.path.join(signals_dir, filename)
            with open(filepath, 'r') as f:
                signal_data = json.load(f)
                signals.append(signal_data)

        return {
            'signals': signals,
            'count': len(signals),
            'total_stored': len(signal_files)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading signals: {str(e)}")


@router.get("/active-levels")
async def get_active_levels():
    """
    Get currently active support and resistance levels.

    Returns all pivots detected in the last analysis with their strength,
    touches, and distance from current price.
    """
    if _bot_state['active_levels'] is None:
        raise HTTPException(
            status_code=404,
            detail="No active levels. Run /current-analysis first."
        )

    try:
        # Fetch current price
        current_price = binance_client.get_current_price('BTC/USDT')

        levels = _bot_state['active_levels']

        return {
            'current_price': current_price,
            'timestamp': datetime.now().isoformat(),

            'resistances': [
                {
                    'price': float(p.price),
                    'strength': float(p.strength),
                    'touches': int(p.touches),
                    'age_candles': int(p.candles_age),
                    'distance_usd': float(p.price - current_price),
                    'distance_pct': ((p.price - current_price) / current_price) * 100,
                    'timestamp': p.timestamp.isoformat()
                }
                for p in levels['resistances']
            ],

            'supports': [
                {
                    'price': float(p.price),
                    'strength': float(p.strength),
                    'touches': int(p.touches),
                    'age_candles': int(p.candles_age),
                    'distance_usd': float(current_price - p.price),
                    'distance_pct': ((current_price - p.price) / current_price) * 100,
                    'timestamp': p.timestamp.isoformat()
                }
                for p in levels['supports']
            ],

            'summary': {
                'total_resistances': len(levels['resistances']),
                'total_supports': len(levels['supports']),
                'strongest_resistance': {
                    'price': float(levels['resistances'][0].price),
                    'strength': float(levels['resistances'][0].strength)
                } if levels['resistances'] else None,
                'strongest_support': {
                    'price': float(levels['supports'][0].price),
                    'strength': float(levels['supports'][0].strength)
                } if levels['supports'] else None
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.get("/volume-profile")
async def get_volume_profile():
    """
    Get Volume Profile data for all timeframes.

    Returns POC, VAH, VAL, HVN, and LVN nodes for:
    - VP_corto (4h)
    - VP_medio (24h)
    - VP_largo (7d)
    """
    try:
        # Fetch data
        ohlcv = binance_client.fetch_ohlcv('BTC/USDT', '5m', limit=500)
        current_price = float(ohlcv[-1, 4])

        # Calculate VP
        vp_data = get_multi_timeframe_vp(ohlcv, num_bins=60)

        return {
            'timestamp': datetime.now().isoformat(),
            'current_price': current_price,

            'vp_corto': {
                **vp_data['vp_corto'],
                'price_levels': vp_data['vp_corto']['price_levels'][:10],  # Limit for response size
                'volume_distribution': vp_data['vp_corto']['volume_distribution'][:10]
            } if vp_data.get('vp_corto') else None,

            'vp_medio': {
                **vp_data['vp_medio'],
                'price_levels': vp_data['vp_medio']['price_levels'][:10],
                'volume_distribution': vp_data['vp_medio']['volume_distribution'][:10]
            } if vp_data.get('vp_medio') else None,

            'vp_largo': {
                **vp_data['vp_largo'],
                'price_levels': vp_data['vp_largo']['price_levels'][:10],
                'volume_distribution': vp_data['vp_largo']['volume_distribution'][:10]
            } if vp_data.get('vp_largo') else None
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"VP error: {str(e)}")


@router.get("/market-context")
async def get_market_context():
    """
    Get current market context and filter status.

    Returns:
    - Liquidity status
    - Volatility status
    - Fundamental events check
    - Higher timeframe trend
    """
    if _bot_state['market_context'] is None:
        raise HTTPException(
            status_code=404,
            detail="No market context. Run /current-analysis first."
        )

    filters = _bot_state['market_context']

    return {
        'timestamp': datetime.now().isoformat(),
        'pass_all_filters': filters['pass_all'],

        'fundamental_event': {
            'detected': filters['fundamental_event'][0],
            'description': filters['fundamental_event'][1]
        },

        'liquidity': {
            'ok': filters['liquidity'][0],
            'reason': filters['liquidity'][1] if not filters['liquidity'][0] else None
        },

        'volatility': {
            'ok': filters['volatility'][0],
            'reason': filters['volatility'][1] if not filters['volatility'][0] else None
        },

        'higher_timeframe_trend': {
            'trend': filters['ht_trend'][0],
            'details': filters['ht_trend'][1]
        },

        'recommendation': 'SAFE TO TRADE' if filters['pass_all'] else 'DO NOT TRADE'
    }


@router.get("/backtest-summary")
async def get_backtest_summary():
    """
    Get summary of latest backtest results.

    Reads from backtest_results.json if available.
    """
    try:
        backtest_file = 'backtest_results.json'

        if not os.path.exists(backtest_file):
            return {
                'available': False,
                'message': 'No backtest results found. Run backtest_pupupuv2.py first.'
            }

        with open(backtest_file, 'r') as f:
            results = json.load(f)

        return {
            'available': True,
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_signals': results['total_signals'],
                'total_trades': results['total_trades'],
                'wins': results['wins'],
                'losses': results['losses'],
                'win_rate': f"{results['win_rate'] * 100:.1f}%",
                'total_pnl': results['total_pnl'],
                'avg_rr': results['avg_rr'],
                'max_drawdown': results['max_drawdown']
            },
            'recent_trades': results['trades'][-5:]  # Last 5 trades
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading backtest: {str(e)}")


@router.post("/start-monitoring")
async def start_monitoring(background_tasks: BackgroundTasks):
    """
    Start background monitoring (check every 60 seconds).

    Note: In production, use Celery or similar for proper background tasks.
    """
    if _bot_state['is_monitoring']:
        return {'status': 'already_running', 'message': 'Monitoring is already active'}

    _bot_state['is_monitoring'] = True

    # TODO: Implement proper background task
    # For now, just update status

    return {
        'status': 'started',
        'message': 'Background monitoring started',
        'check_interval': '60 seconds'
    }


@router.post("/stop-monitoring")
async def stop_monitoring():
    """Stop background monitoring."""
    _bot_state['is_monitoring'] = False

    return {
        'status': 'stopped',
        'message': 'Background monitoring stopped'
    }


@router.get("/statistics")
async def get_statistics():
    """
    Get overall statistics and performance metrics.
    """
    try:
        # Read all stored signals
        signals_dir = 'signals'
        signal_files = []

        if os.path.exists(signals_dir):
            signal_files = [
                f for f in os.listdir(signals_dir)
                if f.startswith('signal_') and f.endswith('.json')
            ]

        total_signals = len(signal_files)

        # Count by direction
        long_count = 0
        short_count = 0
        avg_confidence = 0

        if signal_files:
            confidences = []
            for filename in signal_files:
                with open(os.path.join(signals_dir, filename), 'r') as f:
                    signal = json.load(f)
                    if signal['direction'] == 'LONG':
                        long_count += 1
                    else:
                        short_count += 1
                    confidences.append(signal['confidence'])

            avg_confidence = sum(confidences) / len(confidences)

        return {
            'timestamp': datetime.now().isoformat(),
            'total_signals_generated': total_signals,
            'signals_by_direction': {
                'long': long_count,
                'short': short_count
            },
            'average_confidence': avg_confidence,
            'last_analysis': _bot_state['last_analysis_time'].isoformat() if _bot_state['last_analysis_time'] else None,
            'monitoring_active': _bot_state['is_monitoring']
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Statistics error: {str(e)}")
