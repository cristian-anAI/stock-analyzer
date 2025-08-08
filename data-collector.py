#!/usr/bin/env python3
"""
Sistema de Recolección de Datos de Acciones
Módulo base para obtener información técnica y fundamental de acciones
"""

import yfinance as yf
import pandas as pd
import requests
from datetime import datetime, timedelta
import time
import json
from typing import Dict, List, Optional
import numpy as np
import warnings
warnings.filterwarnings('ignore')

# Try to import talib, fallback to manual calculations if not available
try:
    import talib
    TALIB_AVAILABLE = True
except ImportError:
    TALIB_AVAILABLE = False
    print("TA-Lib not available, using manual calculations")

class StockDataCollector:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """
        Calcula el RSI (Relative Strength Index)
        """
        try:
            if TALIB_AVAILABLE:
                rsi_values = talib.RSI(prices.values, timeperiod=period)
                return pd.Series(rsi_values, index=prices.index)
            else:
                # Cálculo manual del RSI
                delta = prices.diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs))
                return rsi.fillna(50)  # Llenar NaN con valor neutro
        except Exception as e:
            # En caso de error, devolver RSI neutro
            return pd.Series([50] * len(prices), index=prices.index)
    
    def calculate_macd(self, prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict:
        """
        Calcula MACD (Moving Average Convergence Divergence)
        """
        try:
            if TALIB_AVAILABLE:
                macd_line, macd_signal, macd_hist = talib.MACD(prices.values, fastperiod=fast, slowperiod=slow, signalperiod=signal)
                return {
                    'macd': pd.Series(macd_line, index=prices.index),
                    'signal': pd.Series(macd_signal, index=prices.index),
                    'histogram': pd.Series(macd_hist, index=prices.index)
                }
            else:
                # Cálculo manual del MACD
                exp1 = prices.ewm(span=fast).mean()
                exp2 = prices.ewm(span=slow).mean()
                macd_line = exp1 - exp2
                macd_signal = macd_line.ewm(span=signal).mean()
                macd_hist = macd_line - macd_signal
                return {
                    'macd': macd_line,
                    'signal': macd_signal,
                    'histogram': macd_hist
                }
        except Exception:
            # En caso de error, devolver valores neutros
            neutral_series = pd.Series([0] * len(prices), index=prices.index)
            return {
                'macd': neutral_series,
                'signal': neutral_series,
                'histogram': neutral_series
            }
    
    def calculate_bollinger_bands(self, prices: pd.Series, period: int = 20, std_dev: float = 2) -> Dict:
        """
        Calcula las Bollinger Bands
        """
        try:
            if TALIB_AVAILABLE:
                upper, middle, lower = talib.BBANDS(prices.values, timeperiod=period, nbdevup=std_dev, nbdevdn=std_dev)
                return {
                    'upper': pd.Series(upper, index=prices.index),
                    'middle': pd.Series(middle, index=prices.index),
                    'lower': pd.Series(lower, index=prices.index)
                }
            else:
                # Cálculo manual de Bollinger Bands
                middle = prices.rolling(window=period).mean()
                std = prices.rolling(window=period).std()
                upper = middle + (std * std_dev)
                lower = middle - (std * std_dev)
                return {
                    'upper': upper,
                    'middle': middle,
                    'lower': lower
                }
        except Exception:
            # En caso de error, devolver valores neutros
            neutral_series = pd.Series(prices.mean(), index=prices.index)
            return {
                'upper': neutral_series,
                'middle': neutral_series,
                'lower': neutral_series
            }
    
    def get_stock_data(self, symbol: str, period: str = "6mo") -> Dict:
        """
        Obtiene datos completos de una acción
        
        Args:
            symbol: Ticker de la acción (ej: "AAPL")
            period: Periodo de datos ("1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y")
        
        Returns:
            Dict con toda la información de la acción
        """
        try:
            ticker = yf.Ticker(symbol)
            
            # Datos históricos de precios
            hist = ticker.history(period=period)
            
            # Información fundamental
            info = ticker.info
            
            # Datos recientes (últimos 30 días para análisis técnico)
            recent_data = ticker.history(period="1mo")
            
            # Calcular métricas técnicas básicas
            current_price = hist['Close'].iloc[-1]
            prev_close = hist['Close'].iloc[-2] if len(hist) > 1 else current_price
            change = current_price - prev_close
            change_pct = (change / prev_close) * 100
            
            # Promedios móviles
            ma_20 = recent_data['Close'].rolling(20).mean().iloc[-1]
            ma_50 = hist['Close'].rolling(50).mean().iloc[-1] if len(hist) >= 50 else None
            
            # Volumen promedio
            avg_volume = recent_data['Volume'].mean()
            current_volume = hist['Volume'].iloc[-1]
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
            
            # Indicadores técnicos avanzados
            rsi = self.calculate_rsi(hist['Close'])
            current_rsi = rsi.iloc[-1] if len(rsi) > 0 and not pd.isna(rsi.iloc[-1]) else None
            
            macd_data = self.calculate_macd(hist['Close'])
            current_macd = macd_data['macd'].iloc[-1] if len(macd_data['macd']) > 0 and not pd.isna(macd_data['macd'].iloc[-1]) else None
            current_macd_signal = macd_data['signal'].iloc[-1] if len(macd_data['signal']) > 0 and not pd.isna(macd_data['signal'].iloc[-1]) else None
            current_macd_hist = macd_data['histogram'].iloc[-1] if len(macd_data['histogram']) > 0 and not pd.isna(macd_data['histogram'].iloc[-1]) else None
            
            bb_data = self.calculate_bollinger_bands(hist['Close'])
            current_bb_upper = bb_data['upper'].iloc[-1] if len(bb_data['upper']) > 0 and not pd.isna(bb_data['upper'].iloc[-1]) else None
            current_bb_middle = bb_data['middle'].iloc[-1] if len(bb_data['middle']) > 0 and not pd.isna(bb_data['middle'].iloc[-1]) else None
            current_bb_lower = bb_data['lower'].iloc[-1] if len(bb_data['lower']) > 0 and not pd.isna(bb_data['lower'].iloc[-1]) else None
            
            # Calcular posición dentro de las Bollinger Bands
            bb_position = None
            if current_bb_upper and current_bb_lower:
                bb_width = current_bb_upper - current_bb_lower
                bb_position = (current_price - current_bb_lower) / bb_width if bb_width > 0 else 0.5
            
            result = {
                'symbol': symbol,
                'timestamp': datetime.now().isoformat(),
                'price_data': {
                    'current_price': round(current_price, 2),
                    'prev_close': round(prev_close, 2),
                    'change': round(change, 2),
                    'change_percent': round(change_pct, 2),
                    'day_high': round(hist['High'].iloc[-1], 2),
                    'day_low': round(hist['Low'].iloc[-1], 2),
                    'volume': int(current_volume),
                    'avg_volume': int(avg_volume),
                    'volume_ratio': round(volume_ratio, 2)
                },
                'technical_indicators': {
                    'ma_20': round(ma_20, 2) if ma_20 else None,
                    'ma_50': round(ma_50, 2) if ma_50 else None,
                    'price_vs_ma20': round(((current_price / ma_20) - 1) * 100, 2) if ma_20 else None,
                    'volatility_30d': round(recent_data['Close'].pct_change().std() * 100, 2),
                    # Nuevos indicadores técnicos avanzados
                    'rsi': round(current_rsi, 2) if current_rsi else None,
                    'macd': {
                        'macd_line': round(current_macd, 4) if current_macd else None,
                        'signal_line': round(current_macd_signal, 4) if current_macd_signal else None,
                        'histogram': round(current_macd_hist, 4) if current_macd_hist else None,
                        'bullish_crossover': current_macd > current_macd_signal if (current_macd and current_macd_signal) else None
                    },
                    'bollinger_bands': {
                        'upper': round(current_bb_upper, 2) if current_bb_upper else None,
                        'middle': round(current_bb_middle, 2) if current_bb_middle else None,
                        'lower': round(current_bb_lower, 2) if current_bb_lower else None,
                        'position': round(bb_position, 2) if bb_position is not None else None,  # 0 = lower band, 1 = upper band
                        'squeeze': abs(current_bb_upper - current_bb_lower) / current_bb_middle < 0.1 if (current_bb_upper and current_bb_lower and current_bb_middle) else None
                    }
                },
                'fundamental_data': {
                    'market_cap': info.get('marketCap'),
                    'pe_ratio': info.get('trailingPE'),
                    'forward_pe': info.get('forwardPE'),
                    'dividend_yield': info.get('dividendYield'),
                    'beta': info.get('beta'),
                    'sector': info.get('sector'),
                    'industry': info.get('industry'),
                    'country': info.get('country')
                },
                'company_info': {
                    'name': info.get('longName', symbol),
                    'description': info.get('longBusinessSummary', '')[:200] + '...' if info.get('longBusinessSummary') else None
                }
            }
            
            return result
            
        except Exception as e:
            return {
                'symbol': symbol,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def get_multiple_stocks(self, symbols: List[str], delay: float = 0.5) -> List[Dict]:
        """
        Obtiene datos de múltiples acciones con delay para evitar rate limiting
        
        Args:
            symbols: Lista de tickers
            delay: Segundos de espera entre requests
        
        Returns:
            Lista de diccionarios con datos de cada acción
        """
        results = []
        
        for i, symbol in enumerate(symbols):
            print(f"Obteniendo datos de {symbol} ({i+1}/{len(symbols)})...")
            
            data = self.get_stock_data(symbol)
            results.append(data)
            
            if i < len(symbols) - 1:  # No hacer delay en el último
                time.sleep(delay)
        
        return results
    
    def get_market_movers(self, market: str = "us") -> Dict:
        """
        Obtiene los principales movers del mercado
        (Esta función requeriría una API premium, por ahora devuelve datos mock)
        """
        # Acciones populares para testing
        popular_stocks = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "NFLX"]
        
        print("Obteniendo datos de acciones populares...")
        stock_data = self.get_multiple_stocks(popular_stocks[:5])  # Limitar a 5 para testing
        
        # Filtrar solo las que tienen datos válidos
        valid_stocks = [s for s in stock_data if 'error' not in s]
        
        # Ordenar por cambio porcentual
        gainers = sorted(valid_stocks, key=lambda x: x.get('price_data', {}).get('change_percent', 0), reverse=True)
        losers = sorted(valid_stocks, key=lambda x: x.get('price_data', {}).get('change_percent', 0))
        
        return {
            'timestamp': datetime.now().isoformat(),
            'market': market,
            'top_gainers': gainers[:3],
            'top_losers': losers[:3],
            'all_data': valid_stocks
        }
    
    def analyze_stock_potential(self, data: Dict) -> Dict:
        """
        Análisis avanzado del potencial de una acción usando indicadores técnicos
        """
        if 'error' in data:
            return {'analysis': 'No se pudo analizar por error en datos'}
        
        score = 0
        signals = []
        
        price_data = data.get('price_data', {})
        technical = data.get('technical_indicators', {})
        current_price = price_data.get('current_price', 0)
        
        # 1. Análisis de momentum básico
        change_pct = price_data.get('change_percent', 0)
        if change_pct > 3:
            score += 2
            signals.append(f"🚀 Fuerte momentum positivo: +{change_pct:.2f}%")
        elif change_pct > 1:
            score += 1
            signals.append(f"📈 Momentum positivo: +{change_pct:.2f}%")
        elif change_pct < -3:
            score -= 2
            signals.append(f"📉 Momentum negativo fuerte: {change_pct:.2f}%")
        elif change_pct < -1:
            score -= 1
            signals.append(f"⚠️ Momentum negativo: {change_pct:.2f}%")
        
        # 2. Análisis RSI
        rsi = technical.get('rsi')
        if rsi:
            if rsi < 30:
                score += 2
                signals.append(f"💰 RSI oversold ({rsi:.1f}) - possible buy signal")
            elif rsi < 40:
                score += 1
                signals.append(f"📊 RSI approaching oversold ({rsi:.1f})")
            elif rsi > 70:
                score -= 2
                signals.append(f"⚠️ RSI overbought ({rsi:.1f}) - possible sell signal")
            elif rsi > 60:
                score -= 1
                signals.append(f"🔄 RSI approaching overbought ({rsi:.1f})")
        
        # 3. Análisis MACD
        macd_data = technical.get('macd', {})
        if macd_data.get('macd_line') is not None and macd_data.get('signal_line') is not None:
            if macd_data.get('bullish_crossover'):
                score += 2
                signals.append("🎯 MACD bullish crossover detected - strong buy signal")
            elif macd_data['macd_line'] > macd_data['signal_line']:
                score += 1
                signals.append("📈 MACD above signal line - positive momentum")
            else:
                score -= 1
                signals.append("📉 MACD below signal line - negative momentum")
            
            # Análisis del histograma MACD
            histogram = macd_data.get('histogram')
            if histogram:
                if histogram > 0.001:
                    score += 1
                    signals.append("💪 MACD histogram positive - momentum strengthening")
                elif histogram < -0.001:
                    score -= 1
                    signals.append("⚠️ MACD histogram negative - momentum weakening")
        
        # 4. Análisis Bollinger Bands
        bb_data = technical.get('bollinger_bands', {})
        bb_position = bb_data.get('position')
        bb_upper = bb_data.get('upper')
        bb_lower = bb_data.get('lower')
        
        if bb_position is not None:
            if bb_position <= 0.2:
                score += 2
                signals.append(f"🎯 Price near lower Bollinger Band ({current_price:.2f} vs {bb_lower:.2f}) - support level")
            elif bb_position <= 0.4:
                score += 1
                signals.append("📊 Price in lower Bollinger Band zone - potential support")
            elif bb_position >= 0.8:
                score -= 2
                signals.append(f"⚠️ Price near upper Bollinger Band ({current_price:.2f} vs {bb_upper:.2f}) - resistance level")
            elif bb_position >= 0.6:
                score -= 1
                signals.append("🔄 Price in upper Bollinger Band zone - potential resistance")
        
        # Bollinger Band squeeze (baja volatilidad)
        if bb_data.get('squeeze'):
            signals.append("⚡ Bollinger Band squeeze detected - volatility breakout expected")
        
        # 5. Análisis vs medias móviles (mantenido del código original)
        price_vs_ma20 = technical.get('price_vs_ma20')
        if price_vs_ma20:
            if price_vs_ma20 > 5:
                score += 1
                signals.append(f"📈 Precio {price_vs_ma20:.1f}% sobre MA20 - tendencia alcista")
            elif price_vs_ma20 > 2:
                signals.append(f"📊 Precio {price_vs_ma20:.1f}% sobre MA20")
            elif price_vs_ma20 < -5:
                score -= 1
                signals.append(f"📉 Precio {price_vs_ma20:.1f}% bajo MA20 - tendencia bajista")
            elif price_vs_ma20 < -2:
                signals.append(f"⚠️ Precio {price_vs_ma20:.1f}% bajo MA20")
        
        # 6. Análisis de volumen
        volume_ratio = price_data.get('volume_ratio', 1)
        if volume_ratio > 2:
            score += 2
            signals.append(f"🔥 Volumen muy alto: {volume_ratio:.1f}x promedio - alta actividad")
        elif volume_ratio > 1.5:
            score += 1
            signals.append(f"📊 Volumen alto: {volume_ratio:.1f}x promedio")
        elif volume_ratio < 0.5:
            score -= 1
            signals.append("💤 Volumen bajo - poca actividad")
        
        # Clasificación final mejorada
        if score >= 5:
            classification = "STRONG_BUY"
        elif score >= 3:
            classification = "BUY"
        elif score >= 1:
            classification = "NEUTRAL_POSITIVE"
        elif score <= -5:
            classification = "STRONG_SELL"
        elif score <= -3:
            classification = "SELL"
        elif score <= -1:
            classification = "NEUTRAL_NEGATIVE"
        else:
            classification = "NEUTRAL"
        
        return {
            'score': score,
            'classification': classification,
            'signals': signals,
            'recommendation': self._get_recommendation(classification),
            'technical_summary': {
                'rsi_status': self._get_rsi_status(rsi) if rsi else 'N/A',
                'macd_status': self._get_macd_status(macd_data) if macd_data else 'N/A',
                'bb_status': self._get_bb_status(bb_position) if bb_position is not None else 'N/A'
            }
        }
    
    def _get_rsi_status(self, rsi: float) -> str:
        """Analiza el estado del RSI"""
        if rsi < 30:
            return "OVERSOLD"
        elif rsi < 40:
            return "APPROACHING_OVERSOLD"
        elif rsi > 70:
            return "OVERBOUGHT"
        elif rsi > 60:
            return "APPROACHING_OVERBOUGHT"
        else:
            return "NEUTRAL"
    
    def _get_macd_status(self, macd_data: Dict) -> str:
        """Analiza el estado del MACD"""
        if not macd_data.get('macd_line') or not macd_data.get('signal_line'):
            return "INSUFFICIENT_DATA"
        
        if macd_data.get('bullish_crossover'):
            return "BULLISH_CROSSOVER"
        elif macd_data['macd_line'] > macd_data['signal_line']:
            return "BULLISH"
        else:
            return "BEARISH"
    
    def _get_bb_status(self, bb_position: float) -> str:
        """Analiza la posición en las Bollinger Bands"""
        if bb_position <= 0.2:
            return "NEAR_LOWER_BAND"
        elif bb_position <= 0.4:
            return "LOWER_ZONE"
        elif bb_position >= 0.8:
            return "NEAR_UPPER_BAND"
        elif bb_position >= 0.6:
            return "UPPER_ZONE"
        else:
            return "MIDDLE_ZONE"
    
    def _get_recommendation(self, classification: str) -> str:
        """Genera recomendación basada en la clasificación mejorada"""
        recommendations = {
            'STRONG_BUY': "🚀 COMPRA FUERTE - Múltiples señales técnicas muy positivas",
            'BUY': "📈 COMPRA - Señales técnicas positivas dominantes",
            'NEUTRAL_POSITIVE': "👀 VIGILAR DE CERCA - Algunas señales positivas",
            'NEUTRAL': "⏸️ MANTENER EN WATCHLIST - Sin señales claras",
            'NEUTRAL_NEGATIVE': "⚠️ PRECAUCIÓN - Algunas señales negativas",
            'SELL': "📉 VENTA - Señales técnicas negativas dominantes", 
            'STRONG_SELL': "🔴 VENTA FUERTE - Múltiples señales técnicas muy negativas"
        }
        return recommendations.get(classification, "🤔 Análisis inconcluso")


def main():
    """Función principal para testing"""
    collector = StockDataCollector()
    
    print("=== SISTEMA DE RECOLECCIÓN DE DATOS DE ACCIONES ===\n")
    
    # Test con una acción específica
    print("1. Análisis de acción específica:")
    print("-" * 40)
    
    symbol = "AAPL"  # Cambiar por cualquier ticker
    data = collector.get_stock_data(symbol)
    
    if 'error' not in data:
        print(f"✅ {data['company_info']['name']} ({symbol})")
        print(f"Precio actual: ${data['price_data']['current_price']}")
        print(f"Cambio: {data['price_data']['change']:+.2f} ({data['price_data']['change_percent']:+.2f}%)")
        print(f"Volumen: {data['price_data']['volume']:,} (ratio: {data['price_data']['volume_ratio']:.1f}x)")
        
        if data['technical_indicators']['ma_20']:
            print(f"MA20: ${data['technical_indicators']['ma_20']:.2f}")
            print(f"Precio vs MA20: {data['technical_indicators']['price_vs_ma20']:+.1f}%")
        
        # Mostrar indicadores técnicos avanzados
        tech_indicators = data['technical_indicators']
        
        if tech_indicators.get('rsi'):
            rsi_value = tech_indicators['rsi']
            rsi_emoji = "🔴" if rsi_value > 70 else "🟢" if rsi_value < 30 else "🟡"
            print(f"RSI: {rsi_emoji} {rsi_value:.1f}")
        
        if tech_indicators.get('macd', {}).get('macd_line'):
            macd = tech_indicators['macd']
            macd_emoji = "📈" if macd.get('bullish_crossover') else "📊"
            print(f"MACD: {macd_emoji} {macd['macd_line']:.4f} | Signal: {macd['signal_line']:.4f}")
        
        if tech_indicators.get('bollinger_bands', {}).get('position') is not None:
            bb = tech_indicators['bollinger_bands']
            bb_emoji = "🔵" if bb['position'] <= 0.3 else "🔴" if bb['position'] >= 0.7 else "⚪"
            print(f"Bollinger: {bb_emoji} Posición {bb['position']:.1%} | ${bb['lower']:.2f} - ${bb['upper']:.2f}")
        
        # Análisis de potencial
        analysis = collector.analyze_stock_potential(data)
        print(f"\n📊 ANÁLISIS TÉCNICO AVANZADO:")
        print(f"Clasificación: {analysis['classification']} (Score: {analysis['score']:+d})")
        print(f"Recomendación: {analysis['recommendation']}")
        
        # Mostrar resumen técnico
        tech_summary = analysis.get('technical_summary', {})
        if tech_summary:
            print(f"📈 RSI: {tech_summary.get('rsi_status', 'N/A')} | MACD: {tech_summary.get('macd_status', 'N/A')} | BB: {tech_summary.get('bb_status', 'N/A')}")
        
        if analysis['signals']:
            print("🎯 Señales detectadas:")
            for signal in analysis['signals']:
                print(f"  • {signal}")
    else:
        print(f"❌ Error obteniendo datos de {symbol}: {data['error']}")
    
    print(f"\n{'='*60}\n")
    
    # Test con múltiples acciones
    print("2. Análisis de mercado (top acciones):")
    print("-" * 40)
    
    market_data = collector.get_market_movers()
    
    if market_data['all_data']:
        print("📈 TOP GAINERS:")
        for stock in market_data['top_gainers']:
            name = stock['company_info']['name'][:20] + "..." if len(stock['company_info']['name']) > 20 else stock['company_info']['name']
            print(f"  {stock['symbol']:6} | {name:25} | {stock['price_data']['change_percent']:+6.2f}%")
        
        print(f"\n📉 TOP LOSERS:")
        for stock in market_data['top_losers']:
            name = stock['company_info']['name'][:20] + "..." if len(stock['company_info']['name']) > 20 else stock['company_info']['name']
            print(f"  {stock['symbol']:6} | {name:25} | {stock['price_data']['change_percent']:+6.2f}%")
        
        print(f"\n🎯 ANÁLISIS RÁPIDO:")
        for stock in market_data['all_data']:
            analysis = collector.analyze_stock_potential(stock)
            print(f"  {stock['symbol']:6} | {analysis['classification']:15} | Score: {analysis['score']:+2}")
    
    print(f"\n{'='*60}")
    print("✅ Sistema de recolección funcionando correctamente!")
    print("💡 Próximos pasos: Integrar indicadores técnicos avanzados y sentiment analysis")


if __name__ == "__main__":
    main()