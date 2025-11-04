"""
Exit Signal Predictor - Dynamic TP Level Prediction

Predice dinámicamente cuándo salir de un trade basado en señales de agotamiento.
Usa RSI divergencias en 15 minutos para detectar reversiones inminentes.

Problema que resuelve:
- TPs fijos (1R, 2R, 3R) no consideran momentum del precio
- Un trade puede llegar a TP1 pero mostrar agotamiento antes de TP2
- Necesitamos saber EN TIEMPO REAL si tomar TP1, esperar TP2, o ir por TP3

Enfoque ML:
1. Feature Engineering: RSI divergencias, momentum, volatilidad en 15min
2. Multi-class Classification: [TAKE_PROFIT_NOW, HOLD_FOR_TP2, HOLD_FOR_TP3]
3. Real-time monitoring: Evaluar cada 15 minutos durante el trade

Output:
- Probabilidad de que el precio alcance el próximo TP
- Señal de agotamiento (bearish divergence para LONG, bullish para SHORT)
- Recomendación de acción (CLOSE_NOW, HOLD, TRAIL_STOP)
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

# Technical indicators
try:
    from ta.momentum import RSIIndicator
    from ta.trend import MACD, EMAIndicator
    from ta.volatility import BollingerBands, AverageTrueRange
    TA_AVAILABLE = True
except ImportError:
    TA_AVAILABLE = False
    logging.warning("ta library not available - install with: pip install ta")

from .ml_config import ML_CONFIG

logger = logging.getLogger(__name__)


@dataclass
class ExitSignal:
    """Exit signal with ML prediction"""
    timestamp: datetime
    current_price: float
    entry_price: float
    current_pnl_r: float  # R-múltiples (cuántos R llevamos)

    # Signal strength
    exhaustion_signal: str  # NONE, WEAK, MODERATE, STRONG
    rsi_divergence_15min: float  # -1 (bearish), 0 (none), +1 (bullish)
    momentum_weakening: bool

    # ML Prediction
    next_tp_probability: float  # Probabilidad de alcanzar próximo TP
    recommended_action: str  # CLOSE_NOW, HOLD, TRAIL_STOP
    confidence: float  # Confianza en la predicción

    # Target levels
    next_tp_level: float
    next_tp_name: str  # TP1, TP2, TP3
    distance_to_next_tp_r: float  # R-múltiples hasta próximo TP


class ExitFeatureEngineer:
    """
    Feature engineering for exit signal prediction

    Extrae features de datos de 15 minutos para predecir punto de salida óptimo
    """

    def __init__(self):
        self.rsi_period = 14
        self.lookback_divergence = 20  # Candles para detectar divergencia

    def detect_rsi_divergence_15min(
        self,
        df_15min: pd.DataFrame,
        direction: str,
        lookback: int = 20
    ) -> Tuple[float, str]:
        """
        Detecta divergencias RSI en timeframe de 15 minutos

        Para LONG: Bearish divergence = señal de agotamiento
        Para SHORT: Bullish divergence = señal de agotamiento

        Returns:
            (divergence_score, divergence_type)
            divergence_score: -1.0 (bearish strong), 0.0 (none), +1.0 (bullish strong)
            divergence_type: "STRONG_BEARISH", "MODERATE_BEARISH", "NONE", "MODERATE_BULLISH", "STRONG_BULLISH"
        """
        if not TA_AVAILABLE or len(df_15min) < lookback + self.rsi_period:
            return 0.0, "NONE"

        try:
            # Calcular RSI
            rsi = RSIIndicator(close=df_15min['Close'], window=self.rsi_period).rsi()

            # Últimas N velas
            recent_df = df_15min.tail(lookback).copy()
            recent_rsi = rsi.tail(lookback).values
            recent_prices = recent_df['Close'].values

            if len(recent_prices) < lookback or len(recent_rsi) < lookback:
                return 0.0, "NONE"

            # Dividir en dos mitades para comparar
            mid = lookback // 2

            # Primera mitad vs segunda mitad
            price_first_half_max = np.max(recent_prices[:mid])
            price_second_half_max = np.max(recent_prices[mid:])

            price_first_half_min = np.min(recent_prices[:mid])
            price_second_half_min = np.min(recent_prices[mid:])

            rsi_first_half_max = np.max(recent_rsi[:mid])
            rsi_second_half_max = np.max(recent_rsi[mid:])

            rsi_first_half_min = np.min(recent_rsi[:mid])
            rsi_second_half_min = np.min(recent_rsi[mid:])

            # BEARISH DIVERGENCE (peligro para LONG)
            # Precio hace higher high, pero RSI hace lower high
            price_higher_high = price_second_half_max > price_first_half_max * 1.001
            rsi_lower_high = rsi_second_half_max < rsi_first_half_max - 2

            if price_higher_high and rsi_lower_high:
                # Calcular strength basado en magnitud
                rsi_diff = rsi_first_half_max - rsi_second_half_max

                if rsi_diff > 10:
                    return -1.0, "STRONG_BEARISH"
                elif rsi_diff > 5:
                    return -0.5, "MODERATE_BEARISH"
                else:
                    return -0.3, "WEAK_BEARISH"

            # BULLISH DIVERGENCE (peligro para SHORT)
            # Precio hace lower low, pero RSI hace higher low
            price_lower_low = price_second_half_min < price_first_half_min * 0.999
            rsi_higher_low = rsi_second_half_min > rsi_first_half_min + 2

            if price_lower_low and rsi_higher_low:
                # Calcular strength
                rsi_diff = rsi_second_half_min - rsi_first_half_min

                if rsi_diff > 10:
                    return 1.0, "STRONG_BULLISH"
                elif rsi_diff > 5:
                    return 0.5, "MODERATE_BULLISH"
                else:
                    return 0.3, "WEAK_BULLISH"

            return 0.0, "NONE"

        except Exception as e:
            logger.error(f"Error detecting RSI divergence: {e}")
            return 0.0, "NONE"

    def calculate_momentum_weakening(
        self,
        df_15min: pd.DataFrame,
        direction: str
    ) -> Tuple[bool, float]:
        """
        Detecta si el momentum se está debilitando

        Returns:
            (is_weakening, momentum_score)
        """
        if not TA_AVAILABLE or len(df_15min) < 20:
            return False, 0.0

        try:
            # EMA rápida vs lenta
            ema_fast = EMAIndicator(close=df_15min['Close'], window=5).ema_indicator()
            ema_slow = EMAIndicator(close=df_15min['Close'], window=20).ema_indicator()

            # MACD
            macd_indicator = MACD(close=df_15min['Close'])
            macd = macd_indicator.macd()
            macd_signal = macd_indicator.macd_signal()

            # Últimos valores
            ema_fast_current = ema_fast.iloc[-1]
            ema_fast_prev = ema_fast.iloc[-5] if len(ema_fast) >= 5 else ema_fast.iloc[0]

            ema_slow_current = ema_slow.iloc[-1]

            macd_current = macd.iloc[-1]
            macd_signal_current = macd_signal.iloc[-1]
            macd_prev = macd.iloc[-5] if len(macd) >= 5 else macd.iloc[0]

            # Para LONG: momentum se debilita si...
            if direction == "LONG":
                # EMA rápida se acerca a EMA lenta desde arriba
                ema_gap_current = ema_fast_current - ema_slow_current
                ema_gap_prev = ema_fast_prev - ema_slow.iloc[-5] if len(ema_slow) >= 5 else 0

                ema_weakening = ema_gap_current < ema_gap_prev

                # MACD se debilita
                macd_weakening = macd_current < macd_prev
                macd_below_signal = macd_current < macd_signal_current

                is_weakening = (ema_weakening and macd_weakening) or macd_below_signal
                momentum_score = -0.5 if is_weakening else 0.5

                return is_weakening, momentum_score

            # Para SHORT: momentum se debilita si...
            else:  # SHORT
                # EMA rápida se acerca a EMA lenta desde abajo
                ema_gap_current = ema_slow_current - ema_fast_current
                ema_gap_prev = ema_slow.iloc[-5] - ema_fast_prev if len(ema_slow) >= 5 else 0

                ema_weakening = ema_gap_current < ema_gap_prev

                # MACD se debilita (sube hacia 0)
                macd_weakening = macd_current > macd_prev
                macd_above_signal = macd_current > macd_signal_current

                is_weakening = (ema_weakening and macd_weakening) or macd_above_signal
                momentum_score = -0.5 if is_weakening else 0.5

                return is_weakening, momentum_score

        except Exception as e:
            logger.error(f"Error calculating momentum: {e}")
            return False, 0.0

    def calculate_volatility_expansion(self, df_15min: pd.DataFrame) -> float:
        """
        Detecta expansión de volatilidad (puede indicar reversión)

        Returns:
            volatility_score: 0.0-1.0 (1.0 = alta volatilidad)
        """
        if not TA_AVAILABLE or len(df_15min) < 20:
            return 0.0

        try:
            # ATR reciente vs promedio
            atr = AverageTrueRange(
                high=df_15min['High'],
                low=df_15min['Low'],
                close=df_15min['Close'],
                window=14
            ).average_true_range()

            atr_current = atr.iloc[-1]
            atr_avg = atr.tail(20).mean()

            # Ratio de volatilidad
            volatility_ratio = atr_current / atr_avg if atr_avg > 0 else 1.0

            # Normalizar a 0-1
            if volatility_ratio > 2.0:
                return 1.0
            elif volatility_ratio < 0.5:
                return 0.0
            else:
                return (volatility_ratio - 0.5) / 1.5

        except Exception as e:
            logger.error(f"Error calculating volatility: {e}")
            return 0.0

    def extract_exit_features(
        self,
        df_15min: pd.DataFrame,
        entry_price: float,
        current_price: float,
        direction: str,
        tp1: float,
        tp2: float,
        tp3: float
    ) -> Dict:
        """
        Extrae features completos para predicción de exit

        Args:
            df_15min: DataFrame con datos de 15 minutos
            entry_price: Precio de entrada
            current_price: Precio actual
            direction: LONG o SHORT
            tp1, tp2, tp3: Niveles de take profit

        Returns:
            Dictionary con features para ML
        """
        # Calcular R-múltiples actuales
        if direction == "LONG":
            stop_loss = entry_price - (tp1 - entry_price)  # Asumiendo risk = TP1 distance
            risk = entry_price - stop_loss
            current_pnl = current_price - entry_price
        else:
            stop_loss = entry_price + (entry_price - tp1)
            risk = stop_loss - entry_price
            current_pnl = entry_price - current_price

        current_r = current_pnl / risk if risk > 0 else 0

        # Determinar próximo TP
        if direction == "LONG":
            if current_price < tp1:
                next_tp = tp1
                next_tp_name = "TP1"
            elif current_price < tp2:
                next_tp = tp2
                next_tp_name = "TP2"
            else:
                next_tp = tp3
                next_tp_name = "TP3"
        else:  # SHORT
            if current_price > tp1:
                next_tp = tp1
                next_tp_name = "TP1"
            elif current_price > tp2:
                next_tp = tp2
                next_tp_name = "TP2"
            else:
                next_tp = tp3
                next_tp_name = "TP3"

        distance_to_next_tp = abs(next_tp - current_price)
        distance_to_next_tp_r = distance_to_next_tp / risk if risk > 0 else 0

        # RSI divergence en 15min
        rsi_div_score, rsi_div_type = self.detect_rsi_divergence_15min(
            df_15min, direction
        )

        # Momentum weakening
        momentum_weak, momentum_score = self.calculate_momentum_weakening(
            df_15min, direction
        )

        # Volatility expansion
        volatility_score = self.calculate_volatility_expansion(df_15min)

        # RSI actual
        rsi_current = 50.0
        if TA_AVAILABLE and len(df_15min) >= self.rsi_period:
            rsi_indicator = RSIIndicator(close=df_15min['Close'], window=self.rsi_period)
            rsi_current = rsi_indicator.rsi().iloc[-1]

        # Determinar señal de agotamiento
        exhaustion_signal = "NONE"

        if direction == "LONG":
            # Para LONG: bearish divergence = agotamiento
            if rsi_div_type == "STRONG_BEARISH":
                exhaustion_signal = "STRONG"
            elif rsi_div_type == "MODERATE_BEARISH":
                exhaustion_signal = "MODERATE"
            elif rsi_div_type == "WEAK_BEARISH" or (momentum_weak and rsi_current > 70):
                exhaustion_signal = "WEAK"
        else:  # SHORT
            # Para SHORT: bullish divergence = agotamiento
            if rsi_div_type == "STRONG_BULLISH":
                exhaustion_signal = "STRONG"
            elif rsi_div_type == "MODERATE_BULLISH":
                exhaustion_signal = "MODERATE"
            elif rsi_div_type == "WEAK_BULLISH" or (momentum_weak and rsi_current < 30):
                exhaustion_signal = "WEAK"

        return {
            # Current position
            'current_r': current_r,
            'distance_to_next_tp_r': distance_to_next_tp_r,
            'next_tp_name': next_tp_name,
            'next_tp_level': next_tp,

            # Technical signals
            'rsi_divergence_15min': rsi_div_score,
            'rsi_divergence_type': rsi_div_type,
            'rsi_current': rsi_current,
            'momentum_weakening': 1.0 if momentum_weak else 0.0,
            'momentum_score': momentum_score,
            'volatility_expansion': volatility_score,
            'exhaustion_signal': exhaustion_signal,

            # Context
            'direction': direction,
            'entry_price': entry_price,
            'current_price': current_price
        }


class ExitSignalPredictor:
    """
    ML-based predictor for optimal exit timing

    Predice cuándo salir del trade basado en señales de agotamiento
    """

    def __init__(self, model_version: str = "1"):
        """
        Initialize exit signal predictor

        Args:
            model_version: Version of trained model to use
        """
        self.model_version = model_version
        self.feature_engineer = ExitFeatureEngineer()

        # TODO: Load trained ML model
        self.model = None  # Will be trained with historical exit data

    def predict_exit_signal(
        self,
        df_15min: pd.DataFrame,
        entry_price: float,
        current_price: float,
        direction: str,
        tp1: float,
        tp2: float,
        tp3: float
    ) -> ExitSignal:
        """
        Predice la señal de salida óptima

        Args:
            df_15min: DataFrame con datos de 15 minutos
            entry_price: Precio de entrada del trade
            current_price: Precio actual
            direction: LONG o SHORT
            tp1, tp2, tp3: Niveles de take profit

        Returns:
            ExitSignal con recomendación de acción
        """
        # Extraer features
        features = self.feature_engineer.extract_exit_features(
            df_15min,
            entry_price,
            current_price,
            direction,
            tp1,
            tp2,
            tp3
        )

        # Por ahora, lógica basada en reglas (TODO: Reemplazar con ML model)
        next_tp_probability = self._calculate_tp_probability_rule_based(features)
        recommended_action = self._recommend_action_rule_based(features, next_tp_probability)
        confidence = self._calculate_confidence(features)

        return ExitSignal(
            timestamp=datetime.now(),
            current_price=current_price,
            entry_price=entry_price,
            current_pnl_r=features['current_r'],
            exhaustion_signal=features['exhaustion_signal'],
            rsi_divergence_15min=features['rsi_divergence_15min'],
            momentum_weakening=bool(features['momentum_weakening']),
            next_tp_probability=next_tp_probability,
            recommended_action=recommended_action,
            confidence=confidence,
            next_tp_level=features['next_tp_level'],
            next_tp_name=features['next_tp_name'],
            distance_to_next_tp_r=features['distance_to_next_tp_r']
        )

    def _calculate_tp_probability_rule_based(self, features: Dict) -> float:
        """
        Calcula probabilidad de alcanzar próximo TP (lógica basada en reglas)

        TODO: Reemplazar con modelo ML entrenado
        """
        base_probability = 0.65  # Probabilidad base

        # Ajustar por divergencia RSI
        if features['exhaustion_signal'] == "STRONG":
            base_probability -= 0.30
        elif features['exhaustion_signal'] == "MODERATE":
            base_probability -= 0.15
        elif features['exhaustion_signal'] == "WEAK":
            base_probability -= 0.05

        # Ajustar por momentum
        if features['momentum_weakening']:
            base_probability -= 0.10

        # Ajustar por volatilidad
        if features['volatility_expansion'] > 0.7:
            base_probability -= 0.10

        # Ajustar por distancia al próximo TP
        if features['distance_to_next_tp_r'] > 1.5:
            base_probability -= 0.15

        # Limitar entre 0 y 1
        return max(0.0, min(1.0, base_probability))

    def _recommend_action_rule_based(self, features: Dict, tp_probability: float) -> str:
        """
        Recomienda acción basada en features y probabilidad

        Returns:
            "CLOSE_NOW", "HOLD", "TRAIL_STOP"
        """
        # CLOSE_NOW: Señal fuerte de agotamiento
        if features['exhaustion_signal'] == "STRONG":
            return "CLOSE_NOW"

        # CLOSE_NOW: Momentum débil + divergencia moderada + baja probabilidad
        if (features['exhaustion_signal'] == "MODERATE" and
            features['momentum_weakening'] and
            tp_probability < 0.40):
            return "CLOSE_NOW"

        # TRAIL_STOP: Señal moderada de agotamiento pero aún hay momentum
        if (features['exhaustion_signal'] in ["MODERATE", "WEAK"] and
            not features['momentum_weakening'] and
            tp_probability > 0.50):
            return "TRAIL_STOP"

        # HOLD: Sin señales claras de agotamiento
        if features['exhaustion_signal'] == "NONE" and tp_probability > 0.60:
            return "HOLD"

        # Default: TRAIL_STOP (conservador)
        return "TRAIL_STOP"

    def _calculate_confidence(self, features: Dict) -> float:
        """Calcula confianza en la predicción"""
        confidence = 0.7  # Base

        # Mayor confianza con señales claras
        if features['exhaustion_signal'] in ["STRONG", "NONE"]:
            confidence += 0.2

        # Mayor confianza si momentum confirma
        if features['momentum_weakening'] and features['exhaustion_signal'] != "NONE":
            confidence += 0.1

        return min(1.0, confidence)
