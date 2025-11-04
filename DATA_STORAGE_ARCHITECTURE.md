# Arquitectura de Almacenamiento de Datos Históricos

**Fecha**: 14 Octubre 2025
**Problema**: ¿Dónde guardar datos históricos para que funcionen en local Y producción?

---

## 🔍 Situación Actual

### Local (Tu PC):
```
📁 c:\repos\stock-analyzer\
├── trading.db (2.1 MB - SQLite, posiciones/trades)
├── tools/backtest/box_strategy/
│   └── cache/
│       └── *.pkl (54 archivos - datos temporales)
```

### Producción (Servidor):
```
📁 /app/stock-analyzer/  (Docker container)
├── trading.db (montado desde volumen)
├── tools/backtest/box_strategy/
│   └── cache/  ❌ NO EXISTE en producción
```

---

## ❌ Problemas Actuales

### Problema 1: Archivos Locales No Van a Producción
```python
# data_accumulator.py guardaría en:
storage_dir = "tools/backtest/box_strategy/historical_data"

# ❌ Este directorio:
#   - Está en local solamente
#   - NO está en Docker image
#   - NO se sincroniza a producción
#   - Se pierde al rebuild
```

### Problema 2: No Hay Sincronización
- Acumulas datos en local
- Despliegas a producción
- Producción NO tiene esos datos ❌
- Modelo se entrena con datos viejos

### Problema 3: Duplicación de Esfuerzo
- Local descarga datos
- Producción descarga datos (otra vez)
- Desperdicio de tiempo/recursos

### Problema 4: Gestión Manual Compleja
- Para mover datos: copiar archivos manualmente
- Para actualizar producción: rebuild Docker
- No hay control centralizado

---

## ✅ Solución: Base de Datos Centralizada

### Arquitectura Propuesta

```
┌─────────────────────────────────────────────────────────────┐
│                    PostgreSQL Database                       │
│                   (Servidor Cloud/Local)                     │
│                                                              │
│  Tables:                                                     │
│  ├── market_data_5m (datos OHLCV históricos)              │
│  ├── positions (ya existe)                                  │
│  ├── transactions (ya existe)                               │
│  └── data_quality_log (metadata, actualizaciones)          │
└─────────────────────────────────────────────────────────────┘
                           ↑
          ┌────────────────┼────────────────┐
          │                │                │
    ┌─────┴─────┐    ┌─────┴─────┐   ┌─────┴─────┐
    │  LOCAL    │    │   PROD    │   │  BACKTEST │
    │  (Tu PC)  │    │  (Docker) │   │  Scripts  │
    └───────────┘    └───────────┘   └───────────┘
         ↓                ↓                ↓
    Todos leen los mismos datos históricos
    Todos escriben a la misma BBDD
```

### Beneficios:
- ✅ **Un solo source of truth** - Datos en un lugar
- ✅ **Sincronización automática** - Local y prod ven lo mismo
- ✅ **Accumulator corre en cualquier lado** - Local, servidor, cron job
- ✅ **Gestión centralizada** - Control desde cualquier máquina
- ✅ **No rebuild necesario** - Datos persisten independiente de código
- ✅ **Escalable** - Puedes añadir más instancias

---

## 🎯 Opciones de Implementación

### OPCIÓN 1: PostgreSQL en Docker (RECOMENDADA) ⭐⭐⭐⭐⭐

**Setup**: PostgreSQL en contenedor Docker, accesible desde local y producción

#### Ventajas:
- ✅ **Profesional** - BBDD real, no SQLite
- ✅ **Centralizado** - Un solo lugar para todos los datos
- ✅ **Fácil backup** - `pg_dump` automatizado
- ✅ **Concurrent access** - Múltiples conexiones simultáneas
- ✅ **Gestión remota** - Puedes administrar desde cualquier lado
- ✅ **GRATIS** - Open source, sin costos

#### Desventajas:
- ⚠️ Requiere servidor PostgreSQL corriendo
- ⚠️ Configuración inicial (1-2 horas)

#### Implementación:

**docker-compose.yml**:
```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    container_name: stock_analyzer_db
    environment:
      POSTGRES_DB: stock_analyzer
      POSTGRES_USER: trader
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"  # Accesible desde local
    restart: unless-stopped

  api:
    build: .
    depends_on:
      - postgres
    environment:
      DATABASE_URL: postgresql://trader:${DB_PASSWORD}@postgres:5432/stock_analyzer

volumes:
  postgres_data:
```

**Schema para datos históricos**:
```sql
-- Tabla principal de datos OHLCV
CREATE TABLE market_data_5m (
    id BIGSERIAL PRIMARY KEY,
    market VARCHAR(10) NOT NULL,           -- 'SPX', 'NDX', etc.
    ticker VARCHAR(20) NOT NULL,           -- 'ES=F', 'NQ=F', etc.
    timestamp TIMESTAMPTZ NOT NULL,        -- Hora de la vela
    open DECIMAL(12, 2) NOT NULL,
    high DECIMAL(12, 2) NOT NULL,
    low DECIMAL(12, 2) NOT NULL,
    close DECIMAL(12, 2) NOT NULL,
    volume BIGINT,
    created_at TIMESTAMPTZ DEFAULT NOW(),  -- Cuándo se insertó

    -- Constraints
    UNIQUE(market, timestamp)              -- Evita duplicados
);

-- Índices para performance
CREATE INDEX idx_market_timestamp ON market_data_5m(market, timestamp DESC);
CREATE INDEX idx_timestamp ON market_data_5m(timestamp DESC);
CREATE INDEX idx_market ON market_data_5m(market);

-- Tabla de metadata/control
CREATE TABLE data_quality_log (
    id SERIAL PRIMARY KEY,
    market VARCHAR(10) NOT NULL,
    update_date DATE NOT NULL,
    candles_added INTEGER,
    total_candles INTEGER,
    first_timestamp TIMESTAMPTZ,
    last_timestamp TIMESTAMPTZ,
    days_span INTEGER,
    update_source VARCHAR(50),             -- 'yfinance', 'polygon', 'ibkr'
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**data_accumulator.py (PostgreSQL version)**:
```python
import psycopg2
from psycopg2.extras import execute_batch
import pandas as pd
import yfinance as yf
import os
from datetime import datetime, timedelta

class DataAccumulatorDB:
    """Acumula datos en PostgreSQL"""

    def __init__(self):
        self.db_url = os.getenv(
            'DATABASE_URL',
            'postgresql://trader:password@localhost:5432/stock_analyzer'
        )

        self.markets = {
            'SPX': 'ES=F',
            'NDX': 'NQ=F',
            'RUT': 'RTY=F',
            # ... resto de mercados
        }

    def get_connection(self):
        return psycopg2.connect(self.db_url)

    def get_existing_data_range(self, market):
        """Obtener rango de datos existentes"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        MIN(timestamp) as first_date,
                        MAX(timestamp) as last_date,
                        COUNT(*) as total_candles
                    FROM market_data_5m
                    WHERE market = %s
                """, (market,))

                result = cur.fetchone()

                if result[0] is None:
                    return None, None, 0

                return result[0], result[1], result[2]

    def insert_candles(self, market, df):
        """Insertar velas en BBDD (ignora duplicados)"""

        # Preparar datos
        data = [
            (
                market,
                self.markets[market],
                row.Index.to_pydatetime(),
                float(row.Open),
                float(row.High),
                float(row.Low),
                float(row.Close),
                int(row.Volume) if pd.notna(row.Volume) else 0
            )
            for row in df.itertuples()
        ]

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                # INSERT con ON CONFLICT (ignora duplicados)
                execute_batch(cur, """
                    INSERT INTO market_data_5m
                        (market, ticker, timestamp, open, high, low, close, volume)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (market, timestamp) DO NOTHING
                """, data)

                inserted = cur.rowcount
                conn.commit()

        return inserted

    def update_market(self, market):
        """Actualizar datos de un mercado"""

        print(f"\nUpdating {market}...")

        # 1. Ver qué tenemos
        first_date, last_date, total = self.get_existing_data_range(market)

        if first_date:
            print(f"  Existing: {total} candles from {first_date} to {last_date}")
        else:
            print(f"  No existing data")

        # 2. Descargar últimos 60 días
        ticker = self.markets[market]
        end_date = datetime.now()
        start_date = end_date - timedelta(days=60)

        print(f"  Downloading {ticker} last 60 days...")
        df = yf.download(ticker, start=start_date, end=end_date, interval='5m', progress=False)

        if df.empty:
            print(f"  ERROR: No data downloaded")
            return False

        # Handle MultiIndex
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)

        # 3. Insertar en BBDD
        inserted = self.insert_candles(market, df)

        # 4. Actualizar log
        new_first, new_last, new_total = self.get_existing_data_range(market)
        days_span = (new_last - new_first).days if new_first else 0

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO data_quality_log
                        (market, update_date, candles_added, total_candles,
                         first_timestamp, last_timestamp, days_span, update_source)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    market,
                    datetime.now().date(),
                    inserted,
                    new_total,
                    new_first,
                    new_last,
                    days_span,
                    'yfinance'
                ))
                conn.commit()

        print(f"  RESULT: {inserted} new candles added. Total: {new_total} ({days_span} days)")

        return True

    def update_all_markets(self):
        """Actualizar todos los mercados"""

        for market in self.markets.keys():
            try:
                self.update_market(market)
            except Exception as e:
                print(f"  ERROR updating {market}: {e}")

# Uso:
if __name__ == '__main__':
    accumulator = DataAccumulatorDB()
    accumulator.update_all_markets()
```

**Acceso desde data_loader.py**:
```python
class DataLoader:
    def load_from_db(self, market, start_date, end_date):
        """Cargar datos desde PostgreSQL"""

        db_url = os.getenv('DATABASE_URL')
        conn = psycopg2.connect(db_url)

        query = """
            SELECT timestamp, open, high, low, close, volume
            FROM market_data_5m
            WHERE market = %s
              AND timestamp >= %s
              AND timestamp <= %s
            ORDER BY timestamp
        """

        df = pd.read_sql_query(
            query,
            conn,
            params=(market, start_date, end_date),
            index_col='timestamp'
        )

        conn.close()

        return df
```

---

### OPCIÓN 2: SQLite Compartido (Simple pero limitado) ⭐⭐⭐

**Setup**: Usar SQLite pero en volumen compartido entre local y producción

#### Ventajas:
- ✅ **Simple** - Ya usas SQLite para `trading.db`
- ✅ **No requiere servidor** - Archivo único
- ✅ **Fácil backup** - Copiar archivo

#### Desventajas:
- ❌ **No concurrent writes** - Solo una conexión escribiendo
- ❌ **Manual sync** - Tienes que copiar archivo a producción
- ❌ **Tamaño** - SQLite empieza a ser lento con >10GB
- ❌ **No remoto** - Necesitas acceso al archivo

#### Implementación:

```python
# Crear tabla en trading.db existente
CREATE TABLE market_data_5m (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    market TEXT NOT NULL,
    timestamp TEXT NOT NULL,  -- ISO format
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume INTEGER,
    UNIQUE(market, timestamp)
);
```

**Pros**: Rápido de implementar (30 min)
**Cons**: No escala, manual sync a producción

---

### OPCIÓN 3: Cloud Storage (S3/Azure) + Cache Local ⭐⭐⭐⭐

**Setup**: Datos maestros en S3, cache local para velocidad

#### Ventajas:
- ✅ **Escalable** - Ilimitado
- ✅ **Barato** - S3 muy económico
- ✅ **Accesible globalmente** - Desde cualquier lado
- ✅ **Backup automático** - S3 tiene versioning

#### Desventajas:
- ⚠️ Requiere cuenta AWS/Azure
- ⚠️ Latencia en queries (usar cache)
- ⚠️ Costo (~$1-5/mes para tus datos)

#### Implementación:

```python
class DataAccumulatorS3:
    def __init__(self):
        self.s3 = boto3.client('s3')
        self.bucket = 'stock-analyzer-historical-data'

    def save_market_data(self, market, df):
        """Guardar en S3 como parquet (comprimido)"""
        buffer = io.BytesIO()
        df.to_parquet(buffer)

        key = f"market_data/{market}_5m_master.parquet"
        self.s3.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=buffer.getvalue()
        )

    def load_market_data(self, market):
        """Cargar desde S3"""
        key = f"market_data/{market}_5m_master.parquet"

        obj = self.s3.get_object(Bucket=self.bucket, Key=key)
        df = pd.read_parquet(io.BytesIO(obj['Body'].read()))

        return df
```

---

## 🎯 Mi Recomendación

### FASE 1 - AHORA (Mientras configuras IBKR):

**Opción Temporal**: SQLite + Archivos Pickle
```python
# Guardar en dos sitios:
1. SQLite (trading.db) - Fácil de copiar a producción
2. Pickle files - Backup y compatibilidad

# Ventaja: Implementas YA, sin esperas
# Desventaja: Temporal, migrarás después
```

**Implementación**: 1 hora

### FASE 2 - PRÓXIMA SEMANA (Cuando tengas tiempo):

**Opción Definitiva**: PostgreSQL en Docker
```
1. Levantar PostgreSQL container
2. Migrar datos de SQLite → PostgreSQL
3. Actualizar data_accumulator
4. Configurar backup automático

Ventaja: Solución profesional para siempre
Tiempo: 2-3 horas setup inicial
```

---

## 📋 Plan de Acción Propuesto

### HOY (30 minutos):
```bash
# 1. Implementar data_accumulator con SQLite
python tools/backtest/box_strategy/data_accumulator_sqlite.py

# 2. Primera ejecución - guardar 60 días actuales
# Crea tabla market_data_5m en trading.db

# 3. Configurar tarea diaria (Task Scheduler Windows)
# Ejecuta accumulator cada día a las 18:00
```

### ESTA SEMANA (2-3 horas cuando tengas tiempo):
```bash
# 1. Levantar PostgreSQL con Docker
docker-compose up -d postgres

# 2. Crear schema (tablas)
psql -U trader -d stock_analyzer -f schema.sql

# 3. Migrar datos de SQLite → PostgreSQL
python migrate_to_postgres.py

# 4. Actualizar data_accumulator para usar PostgreSQL
# 5. Actualizar data_loader.py

# 6. Desplegar a producción
# Docker ya tiene acceso a PostgreSQL
```

### LARGO PLAZO:
```bash
# PostgreSQL sigue acumulando datos diariamente
# Local y producción siempre sincronizados
# Backups automáticos con pg_dump
```

---

## 💰 Costos Comparados

| Solución | Setup | Costo/mes | Escalabilidad | Complejidad |
|----------|-------|-----------|---------------|-------------|
| **Pickle files local** | 0h | $0 | ❌ Baja | ✅ Muy fácil |
| **SQLite compartido** | 1h | $0 | ⚠️ Media | ✅ Fácil |
| **PostgreSQL local** | 2h | $0 | ✅ Alta | ⚠️ Media |
| **PostgreSQL cloud** | 3h | $10-20 | ✅ Muy alta | ⚠️ Media |
| **S3 + Cache** | 4h | $1-5 | ✅ Ilimitada | ❌ Compleja |

---

## ✅ Decisión Final

**Mi recomendación para TU caso:**

### Plan A - RÁPIDO (Hoy):
```
1. data_accumulator_sqlite.py → Guarda en trading.db
2. Task Scheduler → Corre diariamente
3. Copiar trading.db a producción manualmente (cuando quieras)

Tiempo: 30 minutos
Funciona: Hoy mismo
Limitación: Manual sync a prod
```

### Plan B - PROFESIONAL (Próxima semana):
```
1. PostgreSQL en Docker → BBDD centralizada
2. data_accumulator_postgres.py
3. Local y prod conectan a misma BBDD
4. Sincronización automática

Tiempo: 2-3 horas
Funciona: Para siempre
Limitación: Ninguna
```

---

## 🚀 ¿Qué Prefieres?

**Opción 1**: Implemento SQLite version HOY (30 min) y migras a PostgreSQL cuando tengas tiempo

**Opción 2**: Espero y hago PostgreSQL directamente (2-3 horas pero solución definitiva)

**Opción 3**: SQLite HOY + PostgreSQL próxima semana (lo mejor de ambos)

¿Cuál prefieres? Te recomiendo **Opción 3** - funciona hoy, profesional después.
