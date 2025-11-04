# Estrategia de Acumulación Incremental de Datos

**Fecha**: 14 Octubre 2025
**Pregunta clave**: ¿Estamos guardando datos diariamente para acumular histórico?

---

## 🔍 Situación Actual

### Cache Existente

**Archivos encontrados**: 54 archivos `.pkl` en `tools/backtest/box_strategy/cache/`

**Formato de archivos**:
```
SPX_5m_20251001_20251008.pkl  # Fecha inicio _ Fecha fin
CAC_5m_20251002_20251009.pkl
FTSE_5m_20251011_20251018.pkl
```

**Ejemplo de archivos por mercado**:
```bash
# CAC tiene múltiples archivos con ventanas solapadas:
CAC_5m_20251001_20251008.pkl  (Oct 1-8)
CAC_5m_20251002_20251009.pkl  (Oct 2-9)
CAC_5m_20251005_20251012.pkl  (Oct 5-12)
CAC_5m_20251006_20251013.pkl  (Oct 6-13)
CAC_5m_20251007_20251014.pkl  (Oct 7-14)
CAC_5m_20251008_20251015.pkl  (Oct 8-15)
CAC_5m_20251011_20251018.pkl  (Oct 11-18)
```

### 📊 Análisis del Sistema Actual

**✅ LO QUE SÍ FUNCIONA:**
- Cache existe (`data_loader.py` líneas 116-123)
- Archivos se guardan automáticamente cuando se descargan
- Se evita re-descargar si ya existe el archivo

**❌ LO QUE NO FUNCIONA:**
1. **No hay proceso diario automatizado**
   - Los archivos se crean solo cuando ejecutas backtest/API manualmente
   - No hay cron job o scheduled task

2. **Cache por ventanas, no acumulativo**
   - Cada archivo es una ventana de 7-8 días independiente
   - No hay un "archivo maestro" que acumule todos los datos
   - Archivos se solapan (Oct 1-8, Oct 2-9, etc.)

3. **No hay merge inteligente**
   - Si tienes `SPX_5m_20251001_20251008.pkl` (Oct 1-8)
   - Y luego `SPX_5m_20251009_20251016.pkl` (Oct 9-16)
   - El sistema NO los combina automáticamente en un dataset de 15 días

4. **Espacio desperdiciado**
   - Datos duplicados por solapamiento
   - 54 archivos cuando podrían ser 11 (uno por mercado)

---

## 🎯 Tu Idea es CORRECTA

**Sí, tienes razón:**
> "Si cada día guardamos datos, en 1 año tenemos 1 año de datos sin pagar Polygon"

**Estrategia**:
```
Día 1:  Descargar últimos 60 días con yfinance → Guardar
Día 2:  Descargar últimos 60 días → Merge con día 1 → 61 días totales
Día 3:  Descargar últimos 60 días → Merge con día 1-2 → 62 días totales
...
Día 365: Merge automático → 365 días de datos acumulados ✅
```

**Beneficios**:
- ✅ GRATIS (sigue usando yfinance)
- ✅ En 6 meses → 6 meses de datos
- ✅ En 1 año → 1 año de datos
- ✅ En 2 años → 2 años de datos
- ✅ Calidad igual a Polygon (es la misma data)

**Problema**:
- ⏳ Toma TIEMPO REAL (no puedes acelerar)
- 🔧 Requiere automatización (script diario)

---

## 🛠️ Implementación: Sistema de Acumulación Incremental

### Paso 1: Crear Data Accumulator

```python
# tools/backtest/box_strategy/data_accumulator.py

import pandas as pd
import yfinance as yf
from pathlib import Path
from datetime import datetime, timedelta
import pickle
import pytz

class DataAccumulator:
    """
    Acumula datos históricos diariamente usando yfinance
    """

    def __init__(self, storage_dir="tools/backtest/box_strategy/historical_data"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.markets = {
            'SPX': 'ES=F',
            'NDX': 'NQ=F',
            'RUT': 'RTY=F',
            'DAX': 'FDAX=F',
            'FTSE': '^FTSE',
            'CAC': '^FCHI',
            'STOXX': '^STOXX50E',
            'NKY': 'NKD=F',
            'HSI': '^HSI',
            'ASX': '^AXJO',
            'IBEX': '^IBEX'
        }

    def get_master_file(self, market):
        """Archivo maestro con todos los datos acumulados"""
        return self.storage_dir / f"{market}_5m_master.pkl"

    def get_metadata_file(self, market):
        """Metadatos: última actualización, total días, etc."""
        return self.storage_dir / f"{market}_5m_metadata.json"

    def load_existing_data(self, market):
        """Cargar datos acumulados existentes"""
        master_file = self.get_master_file(market)

        if not master_file.exists():
            return None

        print(f"Loading existing data for {market}...")
        with open(master_file, 'rb') as f:
            df = pickle.load(f)

        print(f"  Existing data: {len(df)} candles from {df.index[0]} to {df.index[-1]}")
        return df

    def download_recent_data(self, market, days=60):
        """Descargar últimos N días con yfinance"""
        ticker = self.markets[market]
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        print(f"\nDownloading recent {days} days for {market} ({ticker})...")

        df = yf.download(
            ticker,
            start=start_date,
            end=end_date,
            interval='5m',
            progress=False
        )

        if df.empty:
            raise ValueError(f"No data downloaded for {market}")

        # Handle MultiIndex columns
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)

        # Ensure timezone
        if df.index.tz is None:
            df.index = df.index.tz_localize('America/New_York')
        else:
            df.index = df.index.tz_convert('America/New_York')

        print(f"  Downloaded: {len(df)} candles from {df.index[0]} to {df.index[-1]}")
        return df

    def merge_data(self, existing, new):
        """Merge datos nuevos con existentes, eliminando duplicados"""

        if existing is None:
            return new

        # Combinar
        combined = pd.concat([existing, new])

        # Eliminar duplicados (mantener el más reciente)
        combined = combined[~combined.index.duplicated(keep='last')]

        # Ordenar por fecha
        combined = combined.sort_index()

        return combined

    def update_market(self, market):
        """Actualizar datos de un mercado"""

        print(f"\n{'='*70}")
        print(f"UPDATING {market}")
        print(f"{'='*70}")

        # 1. Cargar datos existentes
        existing_data = self.load_existing_data(market)

        # 2. Descargar datos recientes
        try:
            new_data = self.download_recent_data(market, days=60)
        except Exception as e:
            print(f"  ERROR downloading {market}: {e}")
            return False

        # 3. Merge
        merged_data = self.merge_data(existing_data, new_data)

        # 4. Guardar
        master_file = self.get_master_file(market)
        with open(master_file, 'wb') as f:
            pickle.dump(merged_data, f)

        # 5. Estadísticas
        print(f"\n  RESULT:")
        print(f"    Total candles: {len(merged_data)}")
        print(f"    Date range: {merged_data.index[0].date()} to {merged_data.index[-1].date()}")

        days_span = (merged_data.index[-1] - merged_data.index[0]).days
        print(f"    Days span: {days_span} days")
        print(f"    Saved to: {master_file}")

        # 6. Guardar metadata
        import json
        metadata = {
            'market': market,
            'ticker': self.markets[market],
            'last_update': datetime.now().isoformat(),
            'total_candles': len(merged_data),
            'first_date': merged_data.index[0].isoformat(),
            'last_date': merged_data.index[-1].isoformat(),
            'days_span': days_span
        }

        metadata_file = self.get_metadata_file(market)
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)

        return True

    def update_all_markets(self):
        """Actualizar todos los mercados"""

        print(f"\n{'='*70}")
        print(f"DAILY DATA ACCUMULATION - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*70}")

        results = {}
        for market in self.markets.keys():
            success = self.update_market(market)
            results[market] = success

        # Resumen
        print(f"\n{'='*70}")
        print("SUMMARY")
        print(f"{'='*70}")

        successful = sum(1 for v in results.values() if v)
        print(f"  Successful: {successful}/{len(results)}")

        for market, success in results.items():
            status = "✅" if success else "❌"
            print(f"    {status} {market}")

        return results


# Script principal
if __name__ == '__main__':
    accumulator = DataAccumulator()
    accumulator.update_all_markets()
```

---

### Paso 2: Automatizar Ejecución Diaria

#### Opción A - Windows Task Scheduler (Windows)

**Crear tarea programada:**

1. Crear archivo `daily_data_update.bat`:
```batch
@echo off
cd C:\repos\stock-analyzer
python tools\backtest\box_strategy\data_accumulator.py >> logs\data_accumulation.log 2>&1
echo Data update completed at %date% %time% >> logs\data_accumulation.log
```

2. Configurar Task Scheduler:
```
- Nombre: "Box Strategy Daily Data Update"
- Trigger: Daily, 6:00 PM (después del cierre de mercado US)
- Action: Run daily_data_update.bat
- Run whether user is logged on or not
```

#### Opción B - Cron Job (Linux/Mac)

```bash
# Editar crontab
crontab -e

# Añadir línea (ejecutar diariamente a las 18:00)
0 18 * * * cd /path/to/stock-analyzer && python tools/backtest/box_strategy/data_accumulator.py >> logs/data_accumulation.log 2>&1
```

#### Opción C - Python APScheduler (Multiplataforma)

```python
# tools/backtest/box_strategy/scheduler.py

from apscheduler.schedulers.blocking import BlockingScheduler
from data_accumulator import DataAccumulator
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def daily_update():
    logger.info("Starting daily data accumulation...")
    accumulator = DataAccumulator()
    accumulator.update_all_markets()
    logger.info("Daily data accumulation completed!")

if __name__ == '__main__':
    scheduler = BlockingScheduler()

    # Ejecutar diariamente a las 18:00 (6 PM)
    scheduler.add_job(
        daily_update,
        'cron',
        hour=18,
        minute=0,
        id='daily_data_update'
    )

    logger.info("Scheduler started. Daily updates at 6:00 PM")
    scheduler.start()
```

Ejecutar en background:
```bash
# Windows
start /B python tools\backtest\box_strategy\scheduler.py

# Linux/Mac
nohup python tools/backtest/box_strategy/scheduler.py &
```

---

### Paso 3: Integrar con data_loader.py

Modificar `data_loader.py` para usar datos acumulados:

```python
# Añadir método en DataLoader class

def load_accumulated_data(self, market, start_date=None, end_date=None):
    """
    Cargar datos del archivo maestro acumulado

    Args:
        market: Market code (SPX, NDX, etc.)
        start_date: Optional filter start
        end_date: Optional filter end

    Returns:
        DataFrame or None
    """
    master_file = Path("tools/backtest/box_strategy/historical_data") / f"{market}_5m_master.pkl"

    if not master_file.exists():
        print(f"No accumulated data for {market} yet")
        return None

    with open(master_file, 'rb') as f:
        df = pickle.load(f)

    # Filtrar por fechas si se especifican
    if start_date:
        df = df[df.index >= start_date]
    if end_date:
        df = df[df.index <= end_date]

    print(f"Loaded {len(df)} candles from accumulated data for {market}")
    return df
```

---

## 📅 Timeline de Acumulación

**Hoy (Día 0)**:
- Implementar `data_accumulator.py`
- Ejecutar primera vez → Guardar últimos 60 días
- **Datos actuales**: 60 días

**Semana 1**:
- Script corre diariamente
- **Datos acumulados**: 60 + 7 = 67 días

**Mes 1**:
- **Datos acumulados**: ~90 días

**Mes 3**:
- **Datos acumulados**: ~150 días

**Mes 6**:
- **Datos acumulados**: ~240 días (casi 1 año de trading days)

**Año 1**:
- **Datos acumulados**: ~365 días (1 año completo) ✅
- **Equivalente a Polygon.io sin costo**

---

## 💰 Comparativa: Estrategia Híbrida vs Solo Acumulación

### Opción 1: Solo Acumulación (GRATIS pero lento)
```
Costo: $0
Tiempo: 1 año para tener 1 año de datos
Beneficio: Eventualmente llegas al mismo punto gratis
```

### Opción 2: Polygon ahora + Acumulación después (RÁPIDO + Gratis largo plazo)
```
Mes 1-2: Polygon.io ($29/mes) → Tienes 2 años de datos YA
Mes 3+: Cancelar Polygon, usar acumulación → GRATIS

Costo total: $58 (2 meses)
Beneficio:
  - Mejoras modelo AHORA (esta semana)
  - Win rate sube inmediatamente
  - Después gratis para siempre
```

### Opción 3: Interactive Brokers (GRATIS pero complejo)
```
Semana 1-2: Setup IB (gratis)
Semana 3: Descargar 2 años de TODOS los mercados
Mes 2+: Usar acumulación incremental

Costo: $0
Esfuerzo: ALTO (2 semanas setup)
Beneficio: Todo gratis, todos los mercados, histórico completo
```

---

## 🎯 Mi Recomendación Final

**Plan Óptimo - Combinar TODO:**

### Fase 1 - AHORA (Esta semana):
```
1. Implementar data_accumulator.py HOY
2. Ejecutar primera vez → Guardar 60 días actuales
3. Configurar tarea diaria (Task Scheduler/cron)
```

### Fase 2 - URGENTE (Próxima semana):
```
Opción A: Polygon.io ($29/mes)
  - Descarga 2 años de SPX/NDX/RUT
  - Re-entrena modelo
  - Ve mejora inmediata

Opción B: Interactive Brokers (gratis)
  - Setup IB (1-2 días)
  - Descarga 2 años de TODOS los mercados
  - Más esfuerzo pero gratis
```

### Fase 3 - LARGO PLAZO (Mes 2+):
```
1. Cancelar Polygon (ya tienes datos descargados)
2. Usar solo data_accumulator para ir añadiendo nuevos días
3. En 6 meses: Tienes 2 años descargados + 6 meses acumulados = 2.5 años
4. En 1 año: 2 años + 1 año = 3 años de datos
```

**Resultado:**
- ✅ Datos históricos YA (Polygon o IB)
- ✅ Mejora de modelo INMEDIATA
- ✅ Sistema autónomo para siempre (acumulación)
- ✅ Costo total: $29-58 o $0 (dependiendo de IB vs Polygon)

---

## 📊 Estado Actual vs Propuesto

### AHORA (Sin sistema):
```
Datos: 60 días fijos (última descarga manual)
Cache: 54 archivos solapados, no acumulativos
Futuro: Seguirás con 60 días siempre
```

### CON DATA ACCUMULATOR:
```
Día 1: 60 días
Mes 1: 90 días
Mes 3: 150 días
Mes 6: 240 días
Año 1: 365 días ✅

Sin costo adicional, automático, para siempre
```

---

## ✅ Próximos Pasos

¿Quieres que implemente:

1. **`data_accumulator.py`** (script de acumulación incremental) - 1 hora
2. **Task Scheduler / Cron setup** - 15 minutos
3. **Ejecutar primera vez** para guardar los 60 días actuales - 5 minutos

Y en paralelo, decides si:
- Opción A: Registrarte en Polygon ($29) para datos inmediatos
- Opción B: Setup Interactive Brokers (gratis) para datos en 1-2 semanas
- Opción C: Solo acumulación (gratis) pero esperar 1 año

**Mi voto**: Implementar acumulación HOY + Polygon esta semana = Lo mejor de ambos mundos.

¿Arranco con el `data_accumulator.py`?
