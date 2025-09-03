# Local AI Trading Analysis

Sistema de análisis inteligente local usando Ollama para analizar tu autotrader.

## Quick Start

### 1. Instalar Ollama
```bash
# Descargar desde: https://ollama.ai/
ollama pull llama3.1:8b
```

### 2. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 3. Ejecutar análisis completo
```bash
cd local_ai
python trading_analyzer.py
```

## Análisis Disponibles

### Análisis Principal
- **Señales de Compra**: Evalúa RSI, MACD, Bollinger bands
- **Estructura de Código**: Revisa arquitectura y calidad
- **Reportes Excel**: Analiza performance histórica  
- **Stocks vs Crypto**: Compara estrategias por mercado
- **Recomendaciones**: Puntos críticos y optimizaciones

### Análisis Especializados
```python
from quick_prompts import get_specialized_prompt, list_available_prompts

# Ver prompts disponibles
list_available_prompts()

# Usar prompt específico
prompt = get_specialized_prompt("RISK_ASSESSMENT")
```

## Prompts Especializados

| Prompt | Descripción |
|--------|------------|
| `MARKET_SENTIMENT` | Sentiment analysis del mercado |
| `RISK_ASSESSMENT` | Evaluación de riesgos del portfolio |
| `PERFORMANCE_DEEP_DIVE` | Análisis profundo de rendimiento |
| `STRATEGY_OPTIMIZATION` | Sugerencias de optimización |
| `MARKET_REGIME_ANALYSIS` | Identificación de régimen de mercado |
| `CRYPTO_SPECIFIC` | Análisis específico para crypto |

## Configuración

### Cambiar modelo de Ollama
```python
analyzer = TradingSystemAnalyzer(model="llama3.1:70b")  # Para análisis más profundo
```

### Personalizar análisis
```python
# Analizar solo un componente
result = analyzer.analyze_buy_signals()
print(result)
```

## Estructura

```
local_ai/
├── trading_analyzer.py    # Análisis principal
├── quick_prompts.py       # Prompts especializados  
├── requirements.txt       # Dependencias
└── README.md             # Esta documentación
```

## Outputs

Los análisis se guardan automáticamente como:
- `trading_analysis_YYYYMMDD_HHMMSS.txt`
- Formato estructurado con recomendaciones accionables
- Puntos críticos destacados con etiquetas

## Próximos Features

- [ ] Integración con libros de trading (PDF processing)
- [ ] Backtesting automático de sugerencias
- [ ] Alertas inteligentes basadas en IA
- [ ] Comparación con benchmarks de mercado