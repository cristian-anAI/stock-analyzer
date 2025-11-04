"""
Mostrar todos los pivotes detectados en las últimas 4 horas
Para compararlos con TradingView
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

import numpy as np
from datetime import datetime, timedelta
from src.data.binance_client_v3 import BinanceClientV3
from src.indicators.pivot_detector_v3 import PupupuV3PivotDetector

print("="*100)
print("COMPARACION DE PIVOTES - ULTIMAS 4 HORAS")
print("="*100)

# Fetch data
client = BinanceClientV3(cache_dir="cache")
ohlcv_data = client.get_1min_data("BTC/USDT", days=7)

print(f"\nDatos: {len(ohlcv_data)} velas")
print(f"Precio actual: ${ohlcv_data[-1, 4]:.2f}")

# Initialize pivot detector
pivot_detector = PupupuV3PivotDetector(
    lookback_periods=100,
    max_pivots_per_side=10,  # Aumentamos para ver todos
    touch_threshold_pct=0.1
)

# Detect pivots
pivot_result = pivot_detector.detect_pivots(ohlcv_data)

current_price = ohlcv_data[-1, 4]
current_time = datetime.fromtimestamp(ohlcv_data[-1, 0] / 1000)

print(f"\n{'='*100}")
print(f"RESISTENCIAS DETECTADAS (total: {len(pivot_result['resistances'])})")
print(f"{'='*100}")
print(f"{'Precio':<15} {'Fuerza':<10} {'Toques':<10} {'Hace (velas)':<15} {'Distancia':<15} {'Activo'}")
print(f"{'-'*100}")

resistances = sorted(pivot_result['resistances'], key=lambda p: p.price)
for pivot in resistances:
    distance = abs(pivot.price - current_price)
    distance_pct = (distance / current_price) * 100
    active = "SI" if pivot.is_active else "NO"

    print(f"${pivot.price:<14.2f} {pivot.strength:<10.1f} {pivot.touches:<10} {pivot.bars_since_formation:<15} {distance_pct:<14.3f}% {active}")

print(f"\n{'='*100}")
print(f"SOPORTES DETECTADOS (total: {len(pivot_result['supports'])})")
print(f"{'='*100}")
print(f"{'Precio':<15} {'Fuerza':<10} {'Toques':<10} {'Hace (velas)':<15} {'Distancia':<15} {'Activo'}")
print(f"{'-'*100}")

supports = sorted(pivot_result['supports'], key=lambda p: p.price, reverse=True)
for pivot in supports:
    distance = abs(pivot.price - current_price)
    distance_pct = (distance / current_price) * 100
    active = "SI" if pivot.is_active else "NO"

    print(f"${pivot.price:<14.2f} {pivot.strength:<10.1f} {pivot.touches:<10} {pivot.bars_since_formation:<15} {distance_pct:<14.3f}% {active}")

# Mostrar los SWING HIGHS y LOWS en las últimas 100 velas
print(f"\n{'='*100}")
print(f"SWING HIGHS EN ULTIMAS 100 VELAS (sin filtrar)")
print(f"{'='*100}")

# Analizar últimas 100 velas manualmente
lookback = 100
recent_data = ohlcv_data[-lookback:]

# Detectar swing highs (high mayor que 5 velas a cada lado)
swing_period = 5
swing_highs = []

for i in range(swing_period, len(recent_data) - swing_period):
    current_high = recent_data[i, 2]

    # Verificar que sea mayor que todas las velas en el rango
    is_swing_high = True
    for j in range(i - swing_period, i + swing_period + 1):
        if j != i and recent_data[j, 2] >= current_high:
            is_swing_high = False
            break

    if is_swing_high:
        timestamp = int(recent_data[i, 0])
        dt = datetime.fromtimestamp(timestamp / 1000)
        bars_ago = len(recent_data) - i - 1
        swing_highs.append({
            'price': current_high,
            'time': dt,
            'bars_ago': bars_ago,
            'index': i
        })

print(f"{'Precio':<15} {'Hora':<20} {'Hace (velas)'}")
print(f"{'-'*100}")
for sh in sorted(swing_highs, key=lambda x: x['price'], reverse=True)[:15]:
    print(f"${sh['price']:<14.2f} {sh['time'].strftime('%H:%M:%S'):<20} {sh['bars_ago']}")

# Swing lows
print(f"\n{'='*100}")
print(f"SWING LOWS EN ULTIMAS 100 VELAS (sin filtrar)")
print(f"{'='*100}")

swing_lows = []

for i in range(swing_period, len(recent_data) - swing_period):
    current_low = recent_data[i, 3]

    # Verificar que sea menor que todas las velas en el rango
    is_swing_low = True
    for j in range(i - swing_period, i + swing_period + 1):
        if j != i and recent_data[j, 3] <= current_low:
            is_swing_low = False
            break

    if is_swing_low:
        timestamp = int(recent_data[i, 0])
        dt = datetime.fromtimestamp(timestamp / 1000)
        bars_ago = len(recent_data) - i - 1
        swing_lows.append({
            'price': current_low,
            'time': dt,
            'bars_ago': bars_ago,
            'index': i
        })

print(f"{'Precio':<15} {'Hora':<20} {'Hace (velas)'}")
print(f"{'-'*100}")
for sl in sorted(swing_lows, key=lambda x: x['price'], reverse=True)[:15]:
    print(f"${sl['price']:<14.2f} {sl['time'].strftime('%H:%M:%S'):<20} {sl['bars_ago']}")

print(f"\n{'='*100}")
print(f"INSTRUCCIONES:")
print(f"{'='*100}")
print(f"1. Abre TradingView en BTC/USDT 1min")
print(f"2. Dibuja líneas horizontales en los niveles que veas como resistencia/soporte")
print(f"3. Compara con la lista de arriba")
print(f"4. Dime qué niveles VES en TradingView que NO están en nuestra lista")
print(f"{'='*100}")
