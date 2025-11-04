# Daily Automated Learning System

Sistema automatizado que aprende continuamente de los trades completados cada día.

## Características

### 1. **Trade Logger** - Registro de Trades Completados
- Guarda cada trade en formato JSON
- Valida campos requeridos
- Marca trades ya usados para entrenamiento

### 2. **Incremental Trainer** - Entrenamiento Incremental
- Combina datos históricos con nuevos trades
- Re-entrena modelos cuando hay suficientes trades nuevos
- Auto-incrementa versiones de modelos

### 3. **Scheduler** - Programador Automático
- Ejecuta diariamente a las 5:00 PM ET (después del cierre)
- Verifica cada hora si es momento de ejecutar
- Puede ejecutarse en background

## Uso

### Opción 1: Ejecución Manual (Recomendado para empezar)

```bash
# Ver estado actual
python daily_learning_system.py --status

# Añadir un trade completado manualmente
python daily_learning_system.py --add-trade my_trade.json

# Ejecutar una vez (recolectar trades y re-entrenar si hay suficientes)
python daily_learning_system.py --run-once

# Forzar re-entrenamiento con trades acumulados
python daily_learning_system.py --force-retrain
```

### Opción 2: Daemon Automático

```bash
# Ejecutar como daemon (programa automático)
python daily_learning_system.py --daemon

# Con umbral personalizado (re-entrena cada 10 trades)
python daily_learning_system.py --daemon --min-trades 10
```

## Formato de Trade

Para añadir un trade manualmente, crea un JSON con este formato:

```json
{
  "market": "SPX",
  "date": "2025-10-08",
  "direction": "LONG",
  "entry_price": 6776.50,
  "exit_price": 6788.50,
  "entry_time": "2025-10-08T10:05:00-04:00",
  "exit_time": "2025-10-08T11:30:00-04:00",
  "outcome": "WIN",
  "pnl_points": 12.00,
  "box_high": 6776.50,
  "box_low": 6764.50,
  "box_range": 12.00,
  "stop_loss": 6764.50,
  "tp1": 6788.50,
  "tp2": 6800.50,
  "tp3": 6812.50,
  "notes": "Opcional - notas sobre el trade"
}
```

Ver [trade_template.json](trade_template.json) para plantilla completa.

## Workflow Diario

### Automático (con --daemon):
1. Sistema se ejecuta a las 5:00 PM ET todos los días
2. Revisa si hay trades nuevos pendientes
3. Si hay ≥5 trades nuevos:
   - Combina con datos históricos
   - Re-entrena modelos ML
   - Guarda nueva versión
   - Marca trades como procesados

### Manual:
1. Al cerrar un trade durante el día, crear JSON con detalles
2. Ejecutar: `python daily_learning_system.py --add-trade trade.json`
3. Al final del día: `python daily_learning_system.py --run-once`
4. Sistema re-entrena si hay suficientes trades

## Configuración

### Umbral de Re-entrenamiento
Por defecto, re-entrena cada 5 trades nuevos. Ajustar con `--min-trades`:

```bash
# Re-entrena cada 3 trades (más frecuente, más CPU)
python daily_learning_system.py --daemon --min-trades 3

# Re-entrena cada 10 trades (menos frecuente, más datos)
python daily_learning_system.py --daemon --min-trades 10
```

### Recomendación:
- **5 trades**: Balance óptimo entre frecuencia y cantidad de datos
- **3 trades**: Para mercados muy activos o testing
- **10 trades**: Para mercados menos activos o evitar overfitting

## Archivos Generados

```
tools/backtest/box_strategy/
├── daily_trades/              # Trades completados
│   ├── SPX_20251008_LONG_140523.json
│   ├── SPX_20251008_LONG_140523.json.trained  # Marca de "ya usado"
│   └── NDX_20251009_SHORT_093012.json
├── results/
│   └── merged_data_20251008_170530.json  # Datos combinados
└── models/
    ├── random_forest_v2.pkl   # Modelos re-entrenados
    └── xgboost_v2.pkl
```

## Integración con Sistema Actual

### 1. Verificar Confianza de Trade de Hoy
```bash
python check_todays_trade.py --market SPX --direction LONG
```

### 2. Añadir Trade Completado
Después de cerrar el trade (WIN o LOSS):
```bash
python daily_learning_system.py --add-trade completed_trade.json
```

### 3. Re-entrenar con Nuevos Datos
```bash
python daily_learning_system.py --run-once
```

### 4. Verificar Nueva Versión
```bash
# Los nuevos trades usarán modelo v2 automáticamente
python check_todays_trade.py --market NDX --version 2
```

## Task Scheduler (Windows)

Para ejecutar automáticamente cada día:

1. Abrir "Task Scheduler" (Programador de Tareas)
2. Crear nueva tarea básica:
   - Nombre: "Box Strategy Daily Learning"
   - Trigger: Diariamente a las 5:00 PM
   - Acción: Ejecutar programa
     - Programa: `python`
     - Argumentos: `daily_learning_system.py --run-once`
     - Directorio: `C:\repos\stock-analyzer\tools\backtest\box_strategy`
3. Condiciones:
   - ✓ Ejecutar solo si el equipo está encendido
   - ✗ No despertar el equipo para ejecutar

## Monitoring y Debugging

### Ver Estado
```bash
python daily_learning_system.py --status
```

Output:
```
================================================================================
DAILY LEARNING SYSTEM STATUS
================================================================================

Trade Statistics:
  Total trades:   12
  Pending:        3
  Trained:        9

Retrain threshold: 5 trades
Ready to retrain:  NO
```

### Logs
- Los mensajes se imprimen a consola
- Redirigir a archivo: `python daily_learning_system.py --run-once > daily_learning.log 2>&1`

## Preguntas Frecuentes

### ¿Cuánto tarda el re-entrenamiento?
- Con 5-10 trades nuevos: ~2-3 minutos
- Depende de CPU/GPU disponible

### ¿Puedo ejecutar mientras tradeo?
- Sí, los archivos se guardan sin interferir
- Recomendado: ejecutar después del cierre

### ¿Qué pasa si falla el entrenamiento?
- Los trades NO se marcan como procesados
- Siguiente ejecución lo intenta de nuevo
- Revisar logs para errores

### ¿Cómo sé qué versión de modelo usar?
- `check_todays_trade.py` usa la última versión por defecto
- Especificar versión: `--version 2`
- Versiones más altas = más datos

## Ejemplo Completo: Día de Trading

```bash
# 9:00 AM - Verificar confianza del setup de hoy
python check_todays_trade.py --market SPX
# Output: WIN PROBABILITY: 55.1%, RECOMMENDATION: REDUCE_SIZE

# [Abres posición reducida (60%) basado en recomendación]

# 2:30 PM - Trade cerrado en TP1 (WIN)
# Crear completed_trade.json con detalles

# 3:00 PM - Registrar trade
python daily_learning_system.py --add-trade completed_trade.json

# 5:00 PM - Sistema automático revisa y re-entrena si hay 5+ trades
# (o ejecutar manual: python daily_learning_system.py --run-once)

# Al día siguiente:
python check_todays_trade.py --market NDX
# Ahora usa modelo mejorado con trade de ayer incluido
```

## Próximos Pasos

1. **Ejecutar sistema por 1 semana** manualmente para validar
2. **Configurar Task Scheduler** para automatización completa
3. **Ajustar umbral** (`--min-trades`) según actividad
4. **Monitorear performance** de versiones de modelos

## Soporte

Si encuentras problemas:
1. Revisar logs de error
2. Validar formato JSON de trades
3. Verificar que backtest data existe
4. Comprobar espacio en disco para modelos
