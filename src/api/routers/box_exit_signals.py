"""
Box Strategy Exit Signals API

Endpoints para obtener señales de salida dinámicas basadas en
RSI divergencias en 15 minutos y predicciones ML.

Uso:
    POST /api/v1/box-strategy/exit-signal
    - Enviar datos del trade activo
    - Recibir recomendación de salida (CLOSE_NOW, HOLD, TRAIL_STOP)

    GET /api/v1/box-strategy/monitor-trade/{trade_id}
    - Monitorear trade activo cada 15 minutos
    - Recibir updates automáticos de señales
"""

from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import logging
import sys
from pathlib import Path

# Add box strategy path
box_strategy_path = Path(__file__).parent.parent.parent.parent / "tools" / "backtest" / "box_strategy"
sys.path.insert(0, str(box_strategy_path))

try:
    from data_loader import DataLoader
    from ml.exit_signal_predictor import ExitSignalPredictor
    EXIT_PREDICTOR_AVAILABLE = True
except ImportError as e:
    EXIT_PREDICTOR_AVAILABLE = False
    logging.warning(f"Exit predictor not available: {e}")

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/box-strategy")


# Pydantic models
class TradePosition(BaseModel):
    """Active trade position"""
    market: str = Field(..., description="Market code (SPX, NDX, etc.)")
    direction: str = Field(..., description="Trade direction (LONG/SHORT)")
    entry_price: float = Field(..., description="Entry price")
    entry_time: str = Field(..., description="Entry timestamp (ISO format)")
    stop_loss: float = Field(..., description="Stop loss level")
    tp1: float = Field(..., description="Take Profit 1")
    tp2: float = Field(..., description="Take Profit 2")
    tp3: float = Field(..., description="Take Profit 3")
    current_price: Optional[float] = Field(None, description="Current price (optional, will fetch if not provided)")


class ExitSignalResponse(BaseModel):
    """Exit signal response"""
    timestamp: str
    market: str
    current_price: float
    entry_price: float
    current_pnl_r: float

    # Signal details
    exhaustion_signal: str  # NONE, WEAK, MODERATE, STRONG
    rsi_divergence_15min: float
    rsi_divergence_type: str
    momentum_weakening: bool

    # ML Prediction
    next_tp_probability: float
    recommended_action: str  # CLOSE_NOW, HOLD, TRAIL_STOP
    confidence: float

    # Target levels
    next_tp_level: float
    next_tp_name: str
    distance_to_next_tp_r: float

    # Detailed breakdown
    analysis: Dict[str, Any]


@router.post("/exit-signal", response_model=ExitSignalResponse)
async def get_exit_signal(trade: TradePosition = Body(...)):
    """
    Obtener señal de salida para un trade activo

    Analiza el trade usando RSI divergencias en 15 minutos y predice
    el mejor momento para salir.

    **Uso típico**:
    1. Abres un trade en TP1
    2. Llamas a este endpoint cada 15 minutos
    3. Recibes recomendación: CLOSE_NOW, HOLD, o TRAIL_STOP

    **Señales de agotamiento**:
    - STRONG: Salir inmediatamente (divergencia fuerte)
    - MODERATE: Considerar salir o trailing stop
    - WEAK: Monitorear de cerca
    - NONE: Hold para próximo TP

    **Ejemplo**:
    ```json
    {
      "market": "SPX",
      "direction": "LONG",
      "entry_price": 6776.50,
      "entry_time": "2025-10-08T10:05:00",
      "stop_loss": 6764.50,
      "tp1": 6788.50,
      "tp2": 6800.50,
      "tp3": 6812.50
    }
    ```
    """
    if not EXIT_PREDICTOR_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Exit predictor not available. Please install dependencies."
        )

    try:
        # Initialize components
        data_loader = DataLoader()
        exit_predictor = ExitSignalPredictor(model_version="1")

        # Download 15min data
        entry_time = datetime.fromisoformat(trade.entry_time.replace('Z', '+00:00'))
        now = datetime.now(entry_time.tzinfo)

        # Get data from entry to now + buffer
        start_date = entry_time - timedelta(days=3)
        end_date = now + timedelta(hours=1)

        logger.info(f"Downloading data for {trade.market} from {start_date} to {end_date}")

        df_5min = data_loader.download_5min_data(
            trade.market,
            start_date=start_date,
            end_date=end_date,
            force_refresh=True
        )

        if df_5min is None or df_5min.empty:
            raise HTTPException(
                status_code=404,
                detail=f"No data available for {trade.market}"
            )

        # Convert to 15min
        df_15min = df_5min.resample('15min').agg({
            'Open': 'first',
            'High': 'max',
            'Low': 'min',
            'Close': 'last',
            'Volume': 'sum'
        }).dropna()

        # Get current price if not provided
        current_price = trade.current_price
        if current_price is None:
            current_price = float(df_15min['Close'].iloc[-1])

        # Get exit signal
        signal = exit_predictor.predict_exit_signal(
            df_15min,
            trade.entry_price,
            current_price,
            trade.direction,
            trade.tp1,
            trade.tp2,
            trade.tp3
        )

        # Build analysis breakdown
        analysis = {
            "rsi_analysis": {
                "divergence_score": signal.rsi_divergence_15min,
                "interpretation": _interpret_rsi_divergence(
                    signal.rsi_divergence_15min,
                    trade.direction
                )
            },
            "momentum_analysis": {
                "weakening": signal.momentum_weakening,
                "interpretation": "Momentum is weakening - consider taking profits" if signal.momentum_weakening else "Momentum still strong - hold position"
            },
            "exhaustion_analysis": {
                "level": signal.exhaustion_signal,
                "interpretation": _interpret_exhaustion(signal.exhaustion_signal)
            },
            "recommendation_reasoning": _generate_reasoning(signal),
            "position_status": {
                "current_pnl_r": round(signal.current_pnl_r, 2),
                "distance_to_next_tp": round(signal.distance_to_next_tp_r, 2),
                "next_target": signal.next_tp_name
            }
        }

        return ExitSignalResponse(
            timestamp=signal.timestamp.isoformat(),
            market=trade.market,
            current_price=signal.current_price,
            entry_price=signal.entry_price,
            current_pnl_r=round(signal.current_pnl_r, 3),
            exhaustion_signal=signal.exhaustion_signal,
            rsi_divergence_15min=round(signal.rsi_divergence_15min, 3),
            rsi_divergence_type=_get_divergence_type_name(signal.rsi_divergence_15min),
            momentum_weakening=signal.momentum_weakening,
            next_tp_probability=round(signal.next_tp_probability, 3),
            recommended_action=signal.recommended_action,
            confidence=round(signal.confidence, 3),
            next_tp_level=signal.next_tp_level,
            next_tp_name=signal.next_tp_name,
            distance_to_next_tp_r=round(signal.distance_to_next_tp_r, 3),
            analysis=analysis
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting exit signal: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _interpret_rsi_divergence(score: float, direction: str) -> str:
    """Interpret RSI divergence score"""
    if direction == "LONG":
        if score < -0.7:
            return "STRONG bearish divergence detected - High risk of reversal, consider exiting"
        elif score < -0.3:
            return "MODERATE bearish divergence - Watch closely, prepare to exit"
        elif score < -0.1:
            return "WEAK bearish divergence - Minor warning sign"
        else:
            return "No bearish divergence - Safe to hold"
    else:  # SHORT
        if score > 0.7:
            return "STRONG bullish divergence detected - High risk of reversal, consider exiting"
        elif score > 0.3:
            return "MODERATE bullish divergence - Watch closely, prepare to exit"
        elif score > 0.1:
            return "WEAK bullish divergence - Minor warning sign"
        else:
            return "No bullish divergence - Safe to hold"


def _interpret_exhaustion(level: str) -> str:
    """Interpret exhaustion signal level"""
    interpretations = {
        "STRONG": "Strong exhaustion detected - Exit recommended immediately",
        "MODERATE": "Moderate exhaustion - Consider trailing stop or partial exit",
        "WEAK": "Weak exhaustion signals - Monitor closely",
        "NONE": "No exhaustion detected - Position still healthy"
    }
    return interpretations.get(level, "Unknown")


def _generate_reasoning(signal) -> str:
    """Generate human-readable reasoning for recommendation"""
    if signal.recommended_action == "CLOSE_NOW":
        return (
            f"CLOSE NOW: Strong signals suggest price exhaustion. "
            f"Exhaustion level: {signal.exhaustion_signal}, "
            f"Momentum weakening: {signal.momentum_weakening}, "
            f"Next TP probability only {signal.next_tp_probability:.1%}. "
            f"Better to secure current profit of {signal.current_pnl_r:.2f}R."
        )
    elif signal.recommended_action == "TRAIL_STOP":
        return (
            f"TRAIL STOP: Some exhaustion signals detected ({signal.exhaustion_signal}), "
            f"but {signal.next_tp_probability:.1%} chance of reaching {signal.next_tp_name}. "
            f"Use trailing stop to protect {signal.current_pnl_r:.2f}R profit while allowing upside."
        )
    else:  # HOLD
        return (
            f"HOLD: No significant exhaustion signals. "
            f"{signal.next_tp_probability:.1%} probability of reaching {signal.next_tp_name} "
            f"at {signal.next_tp_level:.2f}. "
            f"Current profit: {signal.current_pnl_r:.2f}R."
        )


def _get_divergence_type_name(score: float) -> str:
    """Get divergence type name from score"""
    if score < -0.7:
        return "STRONG_BEARISH"
    elif score < -0.3:
        return "MODERATE_BEARISH"
    elif score < -0.1:
        return "WEAK_BEARISH"
    elif score > 0.7:
        return "STRONG_BULLISH"
    elif score > 0.3:
        return "MODERATE_BULLISH"
    elif score > 0.1:
        return "WEAK_BULLISH"
    else:
        return "NONE"


@router.get("/exit-signal/example")
async def get_example_request():
    """
    Get example request body for exit signal endpoint

    Útil para ver el formato esperado del request
    """
    return {
        "example_request": {
            "market": "SPX",
            "direction": "LONG",
            "entry_price": 6776.50,
            "entry_time": "2025-10-08T10:05:00-04:00",
            "stop_loss": 6764.50,
            "tp1": 6788.50,
            "tp2": 6800.50,
            "tp3": 6812.50,
            "current_price": 6790.25
        },
        "usage": "POST /api/v1/box-strategy/exit-signal with this JSON body"
    }
