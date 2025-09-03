# Guía Completa: Usar Ollama UI con tu Sistema de Trading

## 3 FORMAS DE USAR OLLAMA CON TU TRADING SYSTEM

### 1. AUTOMÁTICO (Recomendado)
```bash
cd local_ai
python ollama_bridge_fixed.py
```
- Genera contexto automáticamente con tus datos reales
- Copia al clipboard automáticamente  
- Selección interactiva de tipo de análisis
- Templates optimizados para trading

### 2. TEMPLATES RÁPIDOS
```bash
cd local_ai
python quick_templates.py
```
- 7 templates especializados
- Copy/paste listo para Ollama UI
- Instrucciones claras para cada template

### 3. CONTEXTO PERSONALIZADO
```bash
cd local_ai
python context_builder.py
```
- Constructor interactivo de contexto
- Incluye datos completos del sistema
- Guarda en archivos para reutilizar

## TIPOS DE ANÁLISIS DISPONIBLES

| Tipo | Script | Template | Descripción |
|------|---------|----------|-------------|
| **Performance** | `ollama_bridge_fixed.py` | `performance_analysis` | ROI, drawdown, win rate |
| **Estrategias** | `ollama_bridge_fixed.py` | `strategy_optimization` | Optimizar parámetros |
| **Posiciones** | `ollama_bridge_fixed.py` | `position_review` | Qué mantener/cerrar |
| **Riesgo** | `ollama_bridge_fixed.py` | `risk_assessment` | Gestión de riesgo |
| **Mercado** | `ollama_bridge_fixed.py` | `market_analysis` | Sentiment y timing |
| **Automatización** | `ollama_bridge_fixed.py` | `automation_ideas` | Mejoras técnicas |
| **Bugs** | `quick_templates.py` | `bug_hunting` | Debug de problemas |

## FLUJO RECOMENDADO (PASO A PASO)

### Paso 1: Generar Contexto
```bash
cd local_ai
python ollama_bridge_fixed.py
```

### Paso 2: Seleccionar Análisis
```
¿Qué análisis necesitas?
1. Análisis de Performance del Portfolio    ← Para ROI y métricas
2. Optimización de Estrategias              ← Para ajustar parámetros  
3. Revisión de Posiciones Actuales          ← Para decisiones específicas
4. Evaluación de Riesgo                     ← Para gestión de riesgo
5. Análisis de Mercado                      ← Para timing y sentiment
6. Ideas de Automatización                  ← Para mejoras técnicas
```

### Paso 3: Auto-Copy al Clipboard
```
[OK] Contexto copiado al clipboard!
[INFO] Ve a Ollama UI y pega con Ctrl+V
```

### Paso 4: Ollama UI
1. Abre Ollama UI (http://localhost:11434)
2. Pega el contexto (Ctrl+V)
3. Haz tu pregunta específica

## EJEMPLOS DE PREGUNTAS EFECTIVAS

### Para Performance Analysis:
```
"¿Cómo está performando mi portfolio? Dame:
1. ROI actual vs esperado
2. Top 3 problemas críticos
3. 5 acciones concretas para mejorar
4. Qué posiciones cerrar esta semana"
```

### Para Strategy Optimization:
```
"¿Qué parámetros específicos debo cambiar? Dame:
1. Valores concretos para RSI, MACD thresholds
2. Timeframes óptimos por estrategia  
3. Position sizing recommendations
4. Risk management improvements"
```

### Para Position Review:
```
"Para CADA posición, dime:
1. MANTENER/CERRAR/AJUSTAR con razón específica
2. Stop-loss y take-profit levels exactos
3. Timeline esperado
4. Risk level (1-10)"
```

## PERSONALIZACIÓN AVANZADA

### Crear tu propio template:
```python
# En quick_templates.py
"mi_template": {
    "title": "Mi Análisis Custom",
    "context": "Eres experto en... [mi prompt específico]",
    "instructions": "Inserta aquí..."
}
```

### Modificar contexto automático:
```python
# En ollama_bridge_fixed.py
def mi_contexto_personalizado(self):
    # Tu lógica custom para generar contexto
    return context
```

## SHORTCUTS ÚTILES

### Análisis rápido de performance:
```bash
cd local_ai
python -c "from ollama_bridge_fixed import OllamaBridge; OllamaBridge().quick_ollama_context('performance')"
```

### Solo mostrar templates:
```bash
cd local_ai
python -c "from quick_templates import list_templates; list_templates()"
```

### Context builder directo:
```bash
cd local_ai  
python -c "from context_builder import OllamaContextBuilder; print(OllamaContextBuilder().build_complete_context())"
```

## TROUBLESHOOTING

### Error: "No such table"
- Verifica que `trading.db` existe
- Ejecuta primero tu autotrader para crear datos

### Error: "pyperclip not found"
```bash
pip install pyperclip
```

### Contexto muy largo
- Usa templates específicos en lugar del contexto completo
- Ajusta LIMIT en las queries SQL

### Ollama no responde bien
- Usa preguntas más específicas
- Incluye "Dame números concretos" o "Sé específico"
- Pide formato estructurado: "Dame lista numerada"

## MEJORES PRÁCTICAS

### Para obtener respuestas accionables:
1. Pide **números específicos** ("Dame RSI threshold exacto")
2. Pide **timeframes** ("Para implementar en 1 semana")  
3. Pide **priorización** ("Top 3 más críticos")
4. Pide **formato estructurado** ("Lista numerada")

### Para análisis de código:
1. Incluye el código específico problemático
2. Describe síntomas observados
3. Pide fix paso a paso

### Para optimización:
1. Incluye métricas actuales de performance
2. Especifica objetivos ("Quiero 15% más ROI")
3. Pide implementación concreta

## RESULTADOS ESPERADOS

Con este setup obtendrás de Ollama:
- Análisis específicos basados en TUS datos reales
- Recomendaciones accionables con pasos concretos  
- Optimizaciones técnicas implementables
- Detección de riesgos no visibles
- Ideas de mejora con impacto estimado

Tu Ollama UI ahora tiene contexto completo de tu sistema de trading!