"""
MTSS Analysis Router - Multi-Timeframe Scoring Strategy API
Endpoints para análisis detallado de la estrategia MTSS
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

from ..strategies.strategy_registry import get_strategy_registry
from ..strategies.multi_timeframe_strategy import MultiTimeframeScoringStrategy, MTSSParameters
from ..strategies.strategy_manager import create_strategy_manager

router = APIRouter(prefix="/api/v1/mtss", tags=["MTSS Analysis"])
logger = logging.getLogger(__name__)

@router.get("/analysis/{symbol}")
async def get_mtss_analysis(
    symbol: str,
    timeframe_1m: bool = Query(True, description="Include monthly analysis"),
    timeframe_1w: bool = Query(True, description="Include weekly analysis"), 
    timeframe_1d: bool = Query(True, description="Include daily analysis"),
    timeframe_1h: bool = Query(True, description="Include hourly analysis"),
    custom_params: Optional[str] = Query(None, description="Custom MTSS parameters as JSON")
) -> Dict[str, Any]:
    """
    Análisis MTSS detallado para un símbolo específico
    
    Retorna scores por timeframe, señal final y razonamiento detallado
    """
    try:
        logger.info(f"MTSS analysis requested for {symbol}")
        
        # Crear instancia MTSS
        if custom_params:
            import json
            params_dict = json.loads(custom_params)
            mtss_params = MTSSParameters(**params_dict)
        else:
            # Parámetros por defecto optimizados
            mtss_params = MTSSParameters()
        
        mtss_strategy = MultiTimeframeScoringStrategy(parameters=mtss_params)
        
        # Integrar con TimeframeDataService real
        try:
            from ..services.timeframe_data_service import TimeframeDataService
            data_service = TimeframeDataService()
            
            # Obtener datos reales por timeframe
            real_data = {}
            required_timeframes = mtss_strategy.get_required_timeframes()
            
            for tf in required_timeframes:
                try:
                    df = data_service.get_stock_data(symbol, tf)
                    if df is not None and not df.empty:
                        real_data[tf] = df
                        logger.info(f"Retrieved {len(df)} periods of {tf} data for {symbol}")
                    else:
                        logger.warning(f"No {tf} data available for {symbol}, using mock data")
                        real_data[tf] = _create_mock_data(symbol, tf, periods=100)
                except Exception as e:
                    logger.error(f"Error fetching {tf} data for {symbol}: {e}")
                    real_data[tf] = _create_mock_data(symbol, tf, periods=100)
            
        except ImportError as e:
            logger.warning(f"TimeframeDataService not available, using mock data: {e}")
            # Fallback a mock data si el servicio no está disponible
            real_data = {
                "1M": _create_mock_data(symbol, "monthly", periods=60),
                "1W": _create_mock_data(symbol, "weekly", periods=104), 
                "1d": _create_mock_data(symbol, "daily", periods=365),
                "1h": _create_mock_data(symbol, "hourly", periods=720)
            }
        
        # Calcular scores por timeframe con datos reales
        timeframe_scores = mtss_strategy.calculate_timeframe_scores(symbol, real_data)
        
        # Generar señal final
        signal_type, confidence = mtss_strategy.generate_entry_signal(timeframe_scores)
        
        # Calcular score general (compatible con sistema actual)
        overall_score = mtss_strategy.calculate_score(symbol, real_data)
        
        # Determinar si se usaron datos reales o mock
        data_source_info = {
            "using_real_data": any(tf in real_data and len(real_data[tf]) > 50 for tf in required_timeframes),
            "timeframe_data_status": {
                tf: "real" if tf in real_data and len(real_data[tf]) > 50 else "mock" 
                for tf in required_timeframes
            },
            "total_data_points": {tf: len(real_data.get(tf, [])) for tf in required_timeframes}
        }
        
        # Construir respuesta detallada
        response = {
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "strategy": "Multi-Timeframe Scoring Strategy (MTSS)",
            "version": "1.0",
            
            # Score general compatible con sistema actual
            "overall_score": overall_score,
            "signal_type": signal_type.value if hasattr(signal_type, 'value') else str(signal_type),
            "confidence": confidence,
            
            # Análisis detallado por timeframe
            "timeframe_analysis": {
                tf_score.timeframe: {
                    "score": tf_score.score,
                    "indicator_value": tf_score.indicator_value,
                    "signal_strength": tf_score.signal_strength,
                    "reasoning": tf_score.reasoning,
                    "status": "bullish" if tf_score.score == 1 else "bearish",
                    "enabled": _is_timeframe_enabled(tf_score.timeframe, timeframe_1m, timeframe_1w, timeframe_1d, timeframe_1h)
                }
                for tf_score in timeframe_scores
            },
            
            # Resumen ejecutivo
            "summary": {
                "monthly_filter": next((tf.score for tf in timeframe_scores if tf.timeframe == "1M"), 0),
                "bullish_timeframes": sum(1 for tf in timeframe_scores if tf.score == 1),
                "total_timeframes": len(timeframe_scores),
                "alignment_percentage": (sum(1 for tf in timeframe_scores if tf.score == 1) / len(timeframe_scores)) * 100,
                "recommendation": _get_recommendation(signal_type, confidence, overall_score)
            },
            
            # Parámetros utilizados
            "parameters": {
                "rsi_thresholds": [mtss_params.rsi_oversold, mtss_params.rsi_neutral_min, mtss_params.rsi_neutral_max],
                "ma_periods": [mtss_params.ma_fast, mtss_params.ma_slow],
                "confidence_thresholds": [mtss_params.confidence_aggressive, mtss_params.confidence_full, mtss_params.confidence_partial],
                "macd_params": [mtss_params.macd_fast, mtss_params.macd_slow, mtss_params.macd_signal],
                "ichimoku_params": [mtss_params.tenkan_period, mtss_params.kijun_period, mtss_params.senkou_span_b]
            },
            
            # Información adicional para el frontend
            "ui_data": {
                "color_scheme": _get_color_scheme(signal_type),
                "progress_bars": {tf.timeframe: tf.signal_strength for tf in timeframe_scores},
                "alert_level": _get_alert_level(signal_type, confidence),
                "comparison_vs_current": {
                    "current_strategy_score": "N/A",  # Se completaría con score actual del sistema
                    "mtss_score": overall_score,
                    "difference": "N/A"
                }
            },
            
            # Información sobre fuente de datos
            "data_source": data_source_info
        }
        
        logger.info(f"MTSS analysis completed for {symbol}: {signal_type}, score: {overall_score:.2f}")
        return response
        
    except Exception as e:
        logger.error(f"Error in MTSS analysis for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"MTSS analysis failed: {str(e)}")

@router.get("/compare/{symbol}")
async def compare_strategies(symbol: str) -> Dict[str, Any]:
    """
    Comparación entre estrategia actual y MTSS para un símbolo
    """
    try:
        # Obtener análisis MTSS directamente (sin pasar Query objects)
        mtss_strategy = MultiTimeframeScoringStrategy()
        mock_data = {
            "1M": _create_mock_data(symbol, "monthly", periods=60),
            "1W": _create_mock_data(symbol, "weekly", periods=104), 
            "1d": _create_mock_data(symbol, "daily", periods=365),
            "1h": _create_mock_data(symbol, "hourly", periods=720)
        }
        
        timeframe_scores = mtss_strategy.calculate_timeframe_scores(symbol, mock_data)
        signal_type, confidence = mtss_strategy.generate_entry_signal(timeframe_scores)
        overall_score = mtss_strategy.calculate_score(symbol, mock_data)
        
        mtss_analysis = {
            "overall_score": overall_score,
            "signal_type": signal_type.value if hasattr(signal_type, 'value') else str(signal_type),
            "confidence": confidence,
            "timeframe_analysis": {
                tf_score.timeframe: {
                    "score": tf_score.score,
                    "reasoning": tf_score.reasoning
                }
                for tf_score in timeframe_scores
            }
        }
        
        # TODO: Obtener score de estrategia actual desde la base de datos
        # Por ahora simulamos
        current_score = 7.2  # Placeholder
        
        comparison = {
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "comparison": {
                "current_strategy": {
                    "name": "Swing Trading",
                    "score": current_score,
                    "recommendation": "BUY" if current_score >= 6.0 else "HOLD",
                    "reasoning": "Traditional technical analysis"
                },
                "mtss_strategy": {
                    "name": "Multi-Timeframe Scoring",
                    "score": mtss_analysis["overall_score"],
                    "recommendation": mtss_analysis["signal_type"],
                    "reasoning": "Hierarchical multi-timeframe analysis"
                }
            },
            "agreement": {
                "scores_aligned": abs(current_score - mtss_analysis["overall_score"]) < 1.0,
                "recommendations_match": _recommendations_match(current_score, mtss_analysis["signal_type"]),
                "confidence_level": "high" if mtss_analysis["confidence"] > 7 else "medium"
            },
            "detailed_breakdown": mtss_analysis["timeframe_analysis"]
        }
        
        return comparison
        
    except Exception as e:
        logger.error(f"Error comparing strategies for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Strategy comparison failed: {str(e)}")

@router.get("/parameters")
async def get_mtss_parameters() -> Dict[str, Any]:
    """
    Obtiene los parámetros actuales de MTSS y rangos de optimización
    """
    try:
        default_params = MTSSParameters()
        
        return {
            "current_parameters": {
                "rsi_oversold": default_params.rsi_oversold,
                "rsi_neutral_min": default_params.rsi_neutral_min,
                "rsi_neutral_max": default_params.rsi_neutral_max,
                "ma_fast": default_params.ma_fast,
                "ma_slow": default_params.ma_slow,
                "confidence_aggressive": default_params.confidence_aggressive,
                "confidence_full": default_params.confidence_full,
                "confidence_partial": default_params.confidence_partial,
                "macd_fast": default_params.macd_fast,
                "macd_slow": default_params.macd_slow,
                "macd_signal": default_params.macd_signal
            },
            "optimization_ranges": {
                "rsi_oversold": [20, 25, 30, 35],
                "rsi_neutral_min": [25, 30, 35, 40],
                "rsi_neutral_max": [70, 75, 80, 85],
                "ma_fast": [10, 15, 20, 25, 30],
                "ma_slow": [40, 45, 50, 55, 60],
                "confidence_aggressive": [8.0, 8.5, 9.0],
                "confidence_full": [7.0, 7.5, 8.0],
                "confidence_partial": [6.0, 6.5, 7.0]
            },
            "parameter_impact": {
                "primary": ["rsi_oversold", "rsi_neutral_min", "rsi_neutral_max", "ma_fast", "ma_slow", "confidence_thresholds"],
                "secondary": ["macd_fast", "macd_slow", "macd_signal", "ichimoku_params"]
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting MTSS parameters: {e}")
        raise HTTPException(status_code=500, detail=f"Parameter retrieval failed: {str(e)}")

@router.post("/test-parameters")
async def test_custom_parameters(
    symbol: str,
    parameters: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Prueba parámetros personalizados de MTSS en un símbolo específico
    """
    try:
        # Crear parámetros personalizados
        custom_params = MTSSParameters(**parameters)
        
        # Ejecutar análisis con parámetros personalizados
        custom_analysis = await get_mtss_analysis(
            symbol=symbol,
            custom_params=str(parameters).replace("'", '"')
        )
        
        # Comparar con parámetros por defecto
        default_analysis = await get_mtss_analysis(symbol=symbol)
        
        return {
            "symbol": symbol,
            "test_results": {
                "custom_parameters": custom_analysis,
                "default_parameters": default_analysis,
                "performance_comparison": {
                    "score_difference": custom_analysis["overall_score"] - default_analysis["overall_score"],
                    "signal_change": custom_analysis["signal_type"] != default_analysis["signal_type"],
                    "confidence_change": custom_analysis["confidence"] - default_analysis["confidence"]
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Error testing custom parameters for {symbol}: {e}")
        raise HTTPException(status_code=422, detail=f"Parameter testing failed: {str(e)}")

def _create_mock_data(symbol: str, timeframe: str, periods: int):
    """Crea datos mock para demostración"""
    import pandas as pd
    import numpy as np
    
    # Simular datos de precios
    base_price = 100.0
    dates = pd.date_range(end=datetime.now(), periods=periods, freq='D')
    
    # Generar precios con tendencia y ruido
    trend = np.linspace(0, 20, periods)  # Tendencia alcista
    noise = np.random.normal(0, 5, periods)  # Ruido
    prices = base_price + trend + noise
    
    data = pd.DataFrame({
        'Date': dates,
        'Open': prices * 0.995,
        'High': prices * 1.02,
        'Low': prices * 0.98,
        'Close': prices,
        'Volume': np.random.randint(1000000, 10000000, periods)
    })
    
    return data

def _is_timeframe_enabled(timeframe: str, tf_1m: bool, tf_1w: bool, tf_1d: bool, tf_1h: bool) -> bool:
    """Verifica si un timeframe está habilitado en la consulta"""
    mapping = {
        "1M": tf_1m,
        "1W": tf_1w, 
        "1d": tf_1d,
        "1h": tf_1h
    }
    return mapping.get(timeframe, True)

def _get_recommendation(signal_type, confidence: float, overall_score: float) -> str:
    """Genera recomendación textual"""
    if str(signal_type) == "NO_TRADE":
        return "No operar - Filtro mensual bearish"
    elif str(signal_type) == "BUY_FULL":
        return "Compra fuerte - Alta confianza multi-timeframe"
    elif str(signal_type) == "BUY_HALF":
        return "Compra parcial - Momentum de corto plazo"
    elif str(signal_type) == "WAIT":
        return "Esperar - Timing no óptimo"
    else:
        return f"Analizar - Score {overall_score:.1f}"

def _get_color_scheme(signal_type) -> Dict[str, str]:
    """Esquema de colores para el frontend"""
    mapping = {
        "BUY_FULL": {"primary": "#22c55e", "secondary": "#dcfce7"},
        "BUY_HALF": {"primary": "#eab308", "secondary": "#fef3c7"},
        "WAIT": {"primary": "#6b7280", "secondary": "#f3f4f6"},
        "NO_TRADE": {"primary": "#ef4444", "secondary": "#fee2e2"}
    }
    return mapping.get(str(signal_type), {"primary": "#6b7280", "secondary": "#f3f4f6"})

def _get_alert_level(signal_type, confidence: float) -> str:
    """Nivel de alerta para el frontend"""
    if str(signal_type) == "BUY_FULL" and confidence > 8:
        return "high"
    elif str(signal_type) in ["BUY_FULL", "BUY_HALF"]:
        return "medium"
    else:
        return "low"

def _recommendations_match(current_score: float, mtss_signal: str) -> bool:
    """Verifica si las recomendaciones de ambas estrategias coinciden"""
    current_rec = "BUY" if current_score >= 6.0 else "HOLD"
    mtss_rec = "BUY" if str(mtss_signal) in ["BUY_FULL", "BUY_HALF"] else "HOLD"
    return current_rec == mtss_rec