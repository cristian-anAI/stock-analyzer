"""
PupupuV3 API Router - Scalping 1-min Strategy

Endpoints para el frontend con estrategia de scalping en 1 minuto.
Incluye predicciones ML para TP2/TP3 dinámicos.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, List, Optional
from datetime import datetime
import sys
from pathlib import Path

# Add paths
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from src.data.binance_client_v3 import BinanceClientV3
from src.strategy.pupupuv3_signals import PupupuV3Strategy, signal_to_dict
from src.data.database_pupupuv3 import PupupuV3Database
from src.api.services.telegram_service import telegram_service

# Try to load ML model
try:
    sys.path.append(str(Path(__file__).parent.parent.parent.parent / 'tools' / 'backtest' / 'box_strategy' / 'ml'))
    from tp_ratio_predictor import TPRatioMLModel

    tp_model = TPRatioMLModel()
    try:
        tp_model.load('models/tp_ratio_predictor_v1.pkl')
        ML_MODEL_LOADED = True
    except:
        ML_MODEL_LOADED = False
except:
    ML_MODEL_LOADED = False

router = APIRouter(prefix="/api/v1/pupupuv3", tags=["PupupuV3 Scalping"])

# Initialize components
data_client = BinanceClientV3(cache_dir="cache")
db = PupupuV3Database("pupupuv3.db")

config = {
    'ema_period': 15,
    'pivot_lookback': 100,
    'capital_crypto': 30000,
    'risk_per_trade_pct': 0.02,
    'risk_reduced_pct': 0.01,
    'tp1_ratio': 1.0,
    'pivot_touch_threshold': 0.1
}

strategy = PupupuV3Strategy(config)

# Signal tracking to avoid duplicate Telegram notifications
last_notified_signal = {}  # {symbol: signal_id}


@router.get("/status")
async def get_status():
    """Get system status"""
    return {
        "strategy": "PupupuV3 Scalping",
        "timeframe": "1 minute",
        "ml_model_loaded": ML_MODEL_LOADED,
        "status": "active",
        "timestamp": datetime.now().isoformat()
    }


@router.get("/current-analysis")
async def get_current_analysis(symbol: str = Query(default="BTC/USDT")):
    """
    Get current market analysis with signal detection

    Returns:
    - Current price, EMA, VWAP
    - Active pivots (resistances and supports)
    - Volume Profile (7d)
    - Current signal (if any)
    - ML-predicted TP2/TP3 (if signal exists)
    """
    try:
        # Fetch data
        ohlcv_data = data_client.get_1min_data(symbol, days=7, use_cache=True)
        current_price = float(ohlcv_data[-1, 4])

        # Analyze for signal
        signal = strategy.analyze_for_signals(ohlcv_data, symbol)

        # Calculate indicators
        from src.indicators.session_indicators import (
            calculate_ema,
            calculate_session_vwap,
            find_session_start
        )
        from src.indicators.volume_profile_v3 import get_7d_volume_profile, get_vp_context

        closes = ohlcv_data[:, 4]
        ema_values = calculate_ema(closes, period=15)

        # Find session start for VWAP reset
        session_start = find_session_start(ohlcv_data)
        current_vwap = calculate_session_vwap(ohlcv_data, session_start_idx=session_start)

        current_ema = float(ema_values[-1])

        # Get pivots with session start (current_only=True for frontend - solo pivote actual)
        pivot_result = strategy.pivot_detector.detect_pivots(ohlcv_data, session_start_idx=session_start, current_only=True)

        active_resistances = [
            {
                'price': float(p.price),
                'strength': float(p.strength),
                'touches': int(p.touches),
                'bars_since': int(p.bars_since_formation)
            }
            for p in pivot_result['resistances']
        ]

        active_supports = [
            {
                'price': float(p.price),
                'strength': float(p.strength),
                'touches': int(p.touches),
                'bars_since': int(p.bars_since_formation)
            }
            for p in pivot_result['supports']
        ]

        # Volume Profile
        vp_7d = get_7d_volume_profile(ohlcv_data, num_bins=60)
        vp_context = get_vp_context(current_price, vp_7d) if vp_7d else {}

        # Signal info
        signal_info = None
        ml_prediction = None

        if signal and signal.is_valid:
            signal_info = signal_to_dict(signal)

            # ML prediction for TP2/TP3
            if ML_MODEL_LOADED:
                try:
                    features = tp_model.extract_features(
                        ohlcv_data, len(ohlcv_data) - 1,
                        signal.entry_price, signal.stop_loss,
                        signal.direction, signal.pivot_strength,
                        signal.ema_value, signal.vwap_value
                    )

                    prediction = tp_model.predict(features)

                    risk = abs(signal.entry_price - signal.stop_loss)

                    if signal.direction == 'LONG':
                        tp2_price = signal.entry_price + (risk * prediction.tp2_ratio)
                        tp3_price = signal.entry_price + (risk * prediction.tp3_ratio)
                    else:
                        tp2_price = signal.entry_price - (risk * prediction.tp2_ratio)
                        tp3_price = signal.entry_price - (risk * prediction.tp3_ratio)

                    ml_prediction = {
                        'tp2_ratio': float(prediction.tp2_ratio),
                        'tp2_price': round(tp2_price, 2),
                        'tp2_probability': round(prediction.tp2_probability * 100, 2),
                        'tp2_timeframe': prediction.tp2_timeframe,
                        'tp3_ratio': float(prediction.tp3_ratio),
                        'tp3_price': round(tp3_price, 2),
                        'tp3_probability': round(prediction.tp3_probability * 100, 2),
                        'tp3_timeframe': prediction.tp3_timeframe,
                        'confidence_score': round(prediction.confidence_score * 100, 2)
                    }

                    # ✅ SEND TELEGRAM NOTIFICATION FOR NEW SIGNAL
                    signal_id = f"{symbol}_{signal.timestamp}_{signal.direction}"

                    if last_notified_signal.get(symbol) != signal_id:
                        try:
                            telegram_service.send_pupupuv3_trade_notification(
                                symbol=symbol,
                                direction=signal.direction,
                                entry_price=signal.entry_price,
                                stop_loss=signal.stop_loss,
                                tp1=signal.take_profit_1,
                                tp2_price=tp2_price,
                                tp2_ratio=prediction.tp2_ratio,
                                tp2_probability=prediction.tp2_probability,
                                tp2_timeframe=prediction.tp2_timeframe,
                                tp3_price=tp3_price,
                                tp3_ratio=prediction.tp3_ratio,
                                tp3_probability=prediction.tp3_probability,
                                tp3_timeframe=prediction.tp3_timeframe,
                                risk_amount=signal.risk_usd,
                                position_size=signal.position_size_usd,
                                ml_confidence=signal.ml_confidence,
                                conditions_met={
                                    'pivot_touch': True,
                                    'ema_cross': signal.cross_type,
                                    'vwap_bias': signal.vwap_bias,
                                    'with_vwap': signal.with_vwap_bias
                                }
                            )
                            last_notified_signal[symbol] = signal_id
                        except Exception as telegram_error:
                            # Log but don't fail the request
                            import logging
                            logging.error(f"Failed to send Telegram notification: {telegram_error}")

                except Exception as e:
                    ml_prediction = {'error': str(e)}

        # Note: Removed all_pivots - now only showing current window pivots

        # Signal conditions (why no signal)
        signal_conditions = None
        if not signal_info:
            resistances = pivot_result['resistances']
            supports = pivot_result['supports']

            # Find closest resistance
            if resistances:
                closest_resistance = min(
                    [(abs(current_price - p.price), p.price) for p in resistances]
                )
            else:
                closest_resistance = (None, None)

            # Find closest support
            if supports:
                closest_support = min(
                    [(abs(current_price - p.price), p.price) for p in supports]
                )
            else:
                closest_support = (None, None)

            signal_conditions = {
                'price_near_resistance': bool(closest_resistance[0] is not None and closest_resistance[0] < (current_price * 0.001)),  # 0.1%
                'closest_resistance_distance': round(float(closest_resistance[0]), 2) if closest_resistance[0] is not None else None,
                'closest_resistance_price': round(float(closest_resistance[1]), 2) if closest_resistance[1] is not None else None,
                'price_near_support': bool(closest_support[0] is not None and closest_support[0] < (current_price * 0.001)),  # 0.1%
                'closest_support_distance': round(float(closest_support[0]), 2) if closest_support[0] is not None else None,
                'closest_support_price': round(float(closest_support[1]), 2) if closest_support[1] is not None else None,
                'ema_above_price': bool(current_ema > current_price),
                'ema_distance': round(float(abs(current_ema - current_price)), 2),
                'ema_distance_pct': round(float(abs(current_ema - current_price) / current_price * 100), 2),
                'vwap_above_price': bool(current_vwap > current_price),
                'vwap_distance': round(float(abs(current_vwap - current_price)), 2),
                'vwap_distance_pct': round(float(abs(current_vwap - current_price) / current_price * 100), 2),
                'in_value_area': bool(int(vp_context.get('in_value_area', False))),
                'near_hvn': bool(int(vp_context.get('near_hvn', False)))
            }

        return {
            'symbol': symbol,
            'timestamp': int(float(ohlcv_data[-1, 0])),
            'datetime': datetime.fromtimestamp(float(ohlcv_data[-1, 0]) / 1000).isoformat(),
            'current_price': float(round(current_price, 2)),
            'indicators': {
                'ema_15': round(float(current_ema), 2),
                'ema_distance_pct': round(float(abs(current_ema - current_price) / current_price * 100), 2),
                'ema_above_price': bool(current_ema > current_price),
                'vwap': round(float(current_vwap), 2),
                'vwap_distance_pct': round(float(abs(current_vwap - current_price) / current_price * 100), 2),
                'vwap_above_price': bool(current_vwap > current_price)
            },
            'active_resistances': active_resistances,
            'active_supports': active_supports,
            'volume_profile': {
                'poc': round(float(vp_7d['poc']), 2) if vp_7d else 0,
                'vah': round(float(vp_7d['vah']), 2) if vp_7d else 0,
                'val': round(float(vp_7d['val']), 2) if vp_7d else 0,
                'in_value_area': bool(int(vp_context.get('in_value_area', False))),
                'near_hvn': bool(int(vp_context.get('near_hvn', False)))
            },
            'signal': signal_info,
            'signal_conditions': signal_conditions,
            'ml_prediction': ml_prediction,
            'ml_model_active': ML_MODEL_LOADED
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/signals/recent")
async def get_recent_signals(
    limit: int = Query(default=50, le=100),
    valid_only: bool = Query(default=True)
):
    """Get recent signals from database"""
    try:
        signals = db.get_recent_signals(limit=limit, valid_only=valid_only)
        return {
            'signals': signals,
            'count': len(signals)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trades/pending")
async def get_pending_trades():
    """Get all pending trades (limit orders waiting)"""
    try:
        trades = db.get_trades_by_state('PENDING')
        return {
            'pending_trades': trades,
            'count': len(trades)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trades/active")
async def get_active_trades():
    """Get all active trades (positions opened)"""
    try:
        trades = db.get_active_trades()
        return {
            'active_trades': trades,
            'count': len(trades)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trades/completed")
async def get_completed_trades(limit: int = Query(default=100, le=500)):
    """Get completed trades"""
    try:
        trades = db.get_completed_trades(limit=limit)
        return {
            'completed_trades': trades,
            'count': len(trades)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_statistics(days: int = Query(default=30, le=365)):
    """Get trading statistics for last N days"""
    try:
        stats = db.get_statistics(days=days)
        return {
            'statistics': stats,
            'days': days
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/backtest-results")
async def get_backtest_results():
    """Get latest backtest results if available"""
    try:
        import json
        from glob import glob

        # Find latest backtest results file
        files = glob("backtest_complete_*.json")

        if not files:
            return {
                'available': False,
                'message': 'No backtest results found'
            }

        # Get most recent
        latest_file = max(files, key=lambda f: Path(f).stat().st_mtime)

        with open(latest_file, 'r') as f:
            results = json.load(f)

        return {
            'available': True,
            'file': latest_file,
            'results': results
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config")
async def get_config():
    """Get current strategy configuration"""
    return {
        'config': config,
        'description': {
            'timeframe': '1 minute',
            'ema_period': '15 candles (15 minutes)',
            'pivot_lookback': '100 candles',
            'capital': '$30,000',
            'risk_per_trade': '2% ($600)',
            'risk_reduced': '1% ($300) when against VWAP',
            'tp1_ratio': '1:1 (automatic to breakeven)',
            'tp2': 'ML-predicted (probability > 60%)',
            'tp3': 'ML-predicted (probability > 45%)'
        }
    }


@router.get("/debug-filters")
async def debug_filters(symbol: str = Query(default="BTC/USDT")):
    """
    Debug endpoint - shows why signals are or aren't being generated
    Shows all filter conditions and their current state
    """
    try:
        # Fetch data
        ohlcv_data = data_client.get_1min_data(symbol, days=1, use_cache=True)

        # Use only last 200 candles
        if len(ohlcv_data) > 200:
            ohlcv_data = ohlcv_data[-200:]

        current_candle = ohlcv_data[-1]
        current_close = float(current_candle[4])

        # Calculate indicators
        from src.indicators.session_indicators import (
            calculate_ema,
            calculate_session_vwap,
            find_session_start
        )
        from src.indicators.vwap import get_vwap_position, should_allow_trade

        closes = ohlcv_data[:, 4]
        ema_values = calculate_ema(closes, period=15)

        session_start = find_session_start(ohlcv_data)
        current_vwap = calculate_session_vwap(ohlcv_data, session_start_idx=session_start)
        current_ema = float(ema_values[-1])

        # Check EMA cross (intra-candle preferred)
        current_open = float(current_candle[1])
        prev_close = float(ohlcv_data[-2, 4])
        prev_ema = float(ema_values[-2])

        # Intra-candle cross (preferred): Open < EMA < Close or Open > EMA > Close
        intra_cross_above = current_open < current_ema and current_close > current_ema
        intra_cross_below = current_open > current_ema and current_close < current_ema

        # Inter-candle cross (fallback): previous close vs current close
        inter_cross_above = prev_close <= prev_ema and current_close > current_ema
        inter_cross_below = prev_close >= prev_ema and current_close < current_ema

        cross_above = intra_cross_above or inter_cross_above
        cross_below = intra_cross_below or inter_cross_below

        cross_type = "intra" if (intra_cross_above or intra_cross_below) else "inter" if (cross_above or cross_below) else "none"

        ema_distance_pct = ((current_close / current_ema - 1) * 100) if current_close > current_ema else ((1 - current_close / current_ema) * 100) * -1

        # Get pivots
        pivot_result = strategy.pivot_detector.detect_pivots(ohlcv_data, session_start_idx=session_start, current_only=False)

        # Check pivot touches
        pivot_touch_info = {}
        if cross_above:
            nearest_support = strategy.pivot_detector.get_nearest_pivot(current_close, "below")
            if nearest_support:
                touched = False
                touch_bar = None
                for i in range(1, min(strategy.pivot_lookback + 1, len(ohlcv_data))):
                    candle = ohlcv_data[-i]
                    if strategy.pivot_detector.candle_touched_pivot(candle, nearest_support):
                        touched = True
                        touch_bar = i
                        break
                pivot_touch_info = {
                    'pivot_price': float(nearest_support.price),
                    'touched': touched,
                    'bars_ago': touch_bar
                }
        elif cross_below:
            nearest_resistance = strategy.pivot_detector.get_nearest_pivot(current_close, "above")
            if nearest_resistance:
                touched = False
                touch_bar = None
                for i in range(1, min(strategy.pivot_lookback + 1, len(ohlcv_data))):
                    candle = ohlcv_data[-i]
                    if strategy.pivot_detector.candle_touched_pivot(candle, nearest_resistance):
                        touched = True
                        touch_bar = i
                        break
                pivot_touch_info = {
                    'pivot_price': float(nearest_resistance.price),
                    'touched': touched,
                    'bars_ago': touch_bar
                }

        # VWAP filter check
        vwap_position = get_vwap_position(current_close, current_vwap)

        signal_direction = "LONG" if cross_above else "SHORT" if cross_below else None
        vwap_filter = None

        if signal_direction:
            # Mock ML confidence for now
            ml_confidence = 55.0  # Placeholder
            allow_trade, reason, risk_multiplier = should_allow_trade(
                signal_direction,
                vwap_position,
                ml_confidence
            )
            vwap_filter = {
                'passed': allow_trade,
                'reason': reason,
                'risk_multiplier': risk_multiplier,
                'ml_confidence': ml_confidence
            }

        # Build response
        return {
            'symbol': symbol,
            'timestamp': int(current_candle[0]),
            'current_price': round(current_close, 2),
            'filters': {
                'ema_cross': {
                    'cross_detected': cross_above or cross_below,
                    'cross_type': cross_type,
                    'direction': 'above' if cross_above else 'below' if cross_below else 'none',
                    'current_open': round(current_open, 2),
                    'current_close': round(current_close, 2),
                    'current_ema': round(current_ema, 2),
                    'distance_pct': round(ema_distance_pct, 2)
                },
                'pivot_touch': pivot_touch_info if pivot_touch_info else None,
                'vwap': {
                    'value': round(current_vwap, 2),
                    'position': vwap_position['position'],
                    'bias': vwap_position['directional_bias'],
                    'distance_pct': round(vwap_position['distance_pct'], 2),
                    'filter_result': vwap_filter
                }
            },
            'pivots': {
                'resistances': len(pivot_result['resistances']),
                'supports': len(pivot_result['supports'])
            },
            'signal_expected': cross_above or cross_below,
            'signal_direction': signal_direction,
            'all_filters_passed': (cross_above or cross_below) and pivot_touch_info.get('touched', False) and (vwap_filter['passed'] if vwap_filter else False) if signal_direction else False
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        'status': 'healthy',
        'strategy': 'PupupuV3',
        'ml_model': 'loaded' if ML_MODEL_LOADED else 'not loaded',
        'database': 'connected',
        'timestamp': datetime.now().isoformat()
    }
