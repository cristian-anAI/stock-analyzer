"""
Mostrar pivotes de las últimas 2 horas
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from datetime import datetime, timedelta
from src.data.binance_client_v3 import BinanceClientV3
from src.indicators.pivot_detector_simple import SimplePivotDetector

print("="*100)
print("NIVELES DE SOPORTE Y RESISTENCIA - ULTIMAS 2 HORAS")
print("="*100)

# Fetch data
client = BinanceClientV3(cache_dir="cache")
ohlcv_data = client.get_1min_data("BTC/USDT", days=7)

current_price = ohlcv_data[-1, 4]
current_time = datetime.fromtimestamp(ohlcv_data[-1, 0] / 1000)

print(f"\nHora actual: {current_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")
print(f"Precio actual: ${current_price:,.2f}")

# Initialize detector with 100-period lookback
detector = SimplePivotDetector(
    lookback_periods=100,
    max_pivots_per_side=10,  # Mostrar más niveles
    merge_threshold_pct=0.3  # Merge más agresivo
)

# Detect pivots
result = detector.detect_pivots(ohlcv_data)

# Filter only pivots from last 2 hours (120 candles)
recent_resistances = [p for p in result['resistances'] if p.bars_since_formation <= 120]
recent_supports = [p for p in result['supports'] if p.bars_since_formation <= 120]

print(f"\n{'='*100}")
print(f"RESISTENCIAS (arriba del precio actual)")
print(f"{'='*100}")

if recent_resistances:
    print(f"{'Nivel':<5} {'Precio':<15} {'Toques':<10} {'Hace':<20} {'Distancia':<15}")
    print(f"{'-'*100}")

    for i, pivot in enumerate(recent_resistances, 1):
        distance = pivot.price - current_price
        distance_pct = (distance / current_price) * 100
        mins_ago = pivot.bars_since_formation
        hours = mins_ago // 60
        mins = mins_ago % 60

        time_str = f"{hours}h {mins}m ago" if hours > 0 else f"{mins}m ago"

        print(f"R{i:<4} ${pivot.price:<14,.2f} {pivot.touches:<10} {time_str:<20} +${distance:,.2f} ({distance_pct:>6.2f}%)")
else:
    print("No hay resistencias en las últimas 2 horas")

print(f"\n{'='*100}")
print(f"SOPORTES (debajo del precio actual)")
print(f"{'='*100}")

if recent_supports:
    print(f"{'Nivel':<5} {'Precio':<15} {'Toques':<10} {'Hace':<20} {'Distancia':<15}")
    print(f"{'-'*100}")

    for i, pivot in enumerate(recent_supports, 1):
        distance = current_price - pivot.price
        distance_pct = (distance / current_price) * 100
        mins_ago = pivot.bars_since_formation
        hours = mins_ago // 60
        mins = mins_ago % 60

        time_str = f"{hours}h {mins}m ago" if hours > 0 else f"{mins}m ago"

        print(f"S{i:<4} ${pivot.price:<14,.2f} {pivot.touches:<10} {time_str:<20} -${distance:,.2f} ({distance_pct:>6.2f}%)")
else:
    print("No hay soportes en las últimas 2 horas")

print(f"\n{'='*100}")
print("TODOS LOS NIVELES (incluyendo más antiguos)")
print(f"{'='*100}")

print(f"\nRESISTENCIAS:")
print(f"{'Nivel':<5} {'Precio':<15} {'Toques':<10} {'Distancia':<15}")
print(f"{'-'*100}")

for i, pivot in enumerate(result['resistances'], 1):
    distance_pct = ((pivot.price - current_price) / current_price) * 100
    print(f"R{i:<4} ${pivot.price:<14,.2f} {pivot.touches:<10} +{distance_pct:>6.2f}%")

print(f"\nSOPORTES:")
print(f"{'Nivel':<5} {'Precio':<15} {'Toques':<10} {'Distancia':<15}")
print(f"{'-'*100}")

for i, pivot in enumerate(result['supports'], 1):
    distance_pct = ((current_price - pivot.price) / current_price) * 100
    print(f"S{i:<4} ${pivot.price:<14,.2f} {pivot.touches:<10} -{distance_pct:>6.2f}%")

print(f"\n{'='*100}")
