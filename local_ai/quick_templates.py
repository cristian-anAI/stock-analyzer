"""
Quick Templates para Ollama UI
Templates optimizados para diferentes tipos de análisis
"""

QUICK_TEMPLATES = {
    
    "performance_analysis": {
        "title": "Análisis de Performance",
        "context": """
Eres un EXPERTO TRADER CUANTITATIVO. Analiza la performance de este portfolio:

DATOS DEL PORTFOLIO:
[INSERTAR AQUÍ datos de positions y portfolio_state]

PREGUNTA ESPECÍFICA:
¿Cómo está performando mi sistema de trading? Dame:
1. Análisis del ROI actual
2. Drawdown máximo y riesgos
3. Win rate estimado
4. 3 acciones concretas para mejorar performance
5. Qué posiciones cerrar/mantener/abrir

Sé ESPECÍFICO y ACTIONABLE.
""",
        "instructions": "Copia tus datos de posiciones y estado del portfolio donde dice [INSERTAR AQUÍ]"
    },

    "strategy_optimization": {
        "title": "Optimización de Estrategias", 
        "context": """
Eres un EXPERTO en ESTRATEGIAS DE TRADING. Optimiza mi configuración:

ESTRATEGIAS ACTUALES:
[INSERTAR AQUÍ strategy_config data]

PERFORMANCE ACTUAL:
[INSERTAR AQUÍ positions con strategy_used]

PREGUNTA:
¿Cómo optimizar estas estrategias? Dame:
1. Parámetros específicos a cambiar (con valores)
2. Qué estrategia funciona mejor para stocks vs crypto
3. Nuevos indicadores a integrar
4. Timeframes óptimos por estrategia
5. Risk management improvements

RESPUESTA TÉCNICA y ESPECÍFICA.
""",
        "instructions": "Copia configuración de estrategias y performance por estrategia"
    },

    "risk_assessment": {
        "title": "Evaluación de Riesgo",
        "context": """
Eres un EXPERTO en RISK MANAGEMENT. Evalúa los riesgos de mi portfolio:

CAPITAL ACTUAL:
- Stocks: $10,000 asignado
- Crypto: $50,000 asignado

POSICIONES:
[INSERTAR AQUÍ posiciones actuales con PnL]

PREGUNTA:
¿Qué riesgos críticos veo? Dame:
1. Riesgos de concentración por símbolo/sector
2. Exposure excesivo en algún asset
3. Position sizing óptimo 
4. Stop-loss levels recomendados
5. Hedging opportunities

FOCO EN PREVENIR PÉRDIDAS.
""",
        "instructions": "Copia tus posiciones actuales con PnL y exposure"
    },

    "position_review": {
        "title": "Revisión de Posiciones",
        "context": """
Eres un PORTFOLIO MANAGER experto. Revisa mis posiciones actuales:

POSICIONES ABIERTAS:
[INSERTAR AQUÍ todas las positions con detalles]

WATCHLIST TOP:
[INSERTAR AQUÍ top stocks y cryptos por score]

PREGUNTA:
¿Qué hacer con cada posición? Dame para CADA UNA:
1. MANTENER/CERRAR/AJUSTAR con razón específica
2. Stop-loss y take-profit levels
3. Position size óptimo
4. Timeframe esperado de la posición
5. Nuevas oportunidades del watchlist para entrar

UNA DECISIÓN POR POSICIÓN.
""",
        "instructions": "Copia todas tus posiciones actuales y el watchlist"
    },

    "market_analysis": {
        "title": "Análisis de Mercado",
        "context": """
Eres un ANALISTA TÉCNICO experto. Analiza el estado del mercado:

DATOS ACTUALES:
[INSERTAR AQUÍ top stocks y cryptos con scores, cambios %]

SENTIMENT ACTUAL:
[INSERTAR AQUÍ distribución de scores, volatilidad]

PREGUNTA:
¿En qué fase está el mercado? Dame:
1. Sentiment general (bull/bear/neutral)
2. Sectores/cryptos con mejor momentum
3. Señales de reversión o continuación
4. Oportunidades de entry en próximos días
5. Riesgos macro a vigilar

ENFOQUE EN TIMING DE MERCADO.
""",
        "instructions": "Copia datos de stocks/cryptos con scores y cambios recientes"
    },

    "automation_ideas": {
        "title": "Ideas de Automatización",
        "context": """
Eres un EXPERTO en TRADING AUTOMATION. Mejora mi sistema:

SISTEMA ACTUAL:
- FastAPI backend
- Autotrader con estrategias SwingTrading/CryptoCompetition
- Database SQLite con positions, portfolio, strategies

CÓDIGO CLAVE:
[INSERTAR AQUÍ estructura de servicios principales]

PREGUNTA:
¿Cómo automatizar más el sistema? Dame:
1. Procesos manuales que puedo automatizar
2. Nuevas APIs o data sources a integrar  
3. Machine learning opportunities
4. Alerting y monitoring improvements
5. Backtesting automation

IDEAS TÉCNICAS Y IMPLEMENTABLES.
""",
        "instructions": "Copia estructura de tus servicios principales (autotrader, portfolio, etc.)"
    },

    "bug_hunting": {
        "title": "Detección de Bugs",
        "context": """
Eres un EXPERTO DEBUGGER de sistemas de trading. Encuentra problemas:

SÍNTOMAS:
[INSERTAR AQUÍ problema específico que observas]

CÓDIGO RELACIONADO:
[INSERTAR AQUÍ el código donde sospechas está el bug]

DATOS:
[INSERTAR AQUÍ datos relevantes - logs, posiciones afectadas]

PREGUNTA:
¿Dónde está el bug? Dame:
1. Líneas específicas de código problemáticas
2. Causa root del problema
3. Fix específico paso a paso
4. Tests para evitar regresión
5. Otros lugares donde puede estar el mismo bug

DEBUGGING SISTEMÁTICO.
""",
        "instructions": "Describe el problema específico y pega el código relacionado"
    }
}

def get_template(template_name):
    """Obtiene un template específico"""
    return QUICK_TEMPLATES.get(template_name, {
        "title": "Template no encontrado",
        "context": "Template no válido",
        "instructions": "Usa list_templates() para ver opciones"
    })

def list_templates():
    """Lista todos los templates disponibles"""
    print("TEMPLATES DISPONIBLES PARA OLLAMA UI:")
    print("=" * 50)
    for key, template in QUICK_TEMPLATES.items():
        print(f"\n[{key}]:")
        print(f"   {template['title']}")
        print(f"   Uso: get_template('{key}')")
    
    print(f"\n[INFO] Total: {len(QUICK_TEMPLATES)} templates disponibles")

def generate_template_context(template_name, custom_data=None):
    """Genera contexto completo para un template"""
    template = get_template(template_name)
    
    context = f"""
=== {template['title']} - OLLAMA UI ===

{template['context']}

=== INSTRUCCIONES ===
{template['instructions']}

=== READY TO COPY/PASTE ===
El contexto de arriba está listo para copiar a Ollama UI.
Reemplaza [INSERTAR AQUÍ] con tus datos específicos.
"""
    return context

def interactive_template_selector():
    """Selector interactivo de templates"""
    print("QUICK TEMPLATE SELECTOR")
    print("=" * 40)
    
    templates_list = list(QUICK_TEMPLATES.keys())
    
    for i, key in enumerate(templates_list, 1):
        title = QUICK_TEMPLATES[key]['title']
        print(f"{i}. {title} ({key})")
    
    try:
        choice = int(input(f"\nElige template (1-{len(templates_list)}): "))
        
        if 1 <= choice <= len(templates_list):
            selected = templates_list[choice - 1]
            template = get_template(selected)
            
            print("\n" + "="*60)
            print(f"TEMPLATE: {template['title']}")
            print("="*60)
            print(template['context'])
            print("\n" + "="*60)
            print("INSTRUCCIONES:")
            print(template['instructions'])
            print("="*60)
            
            return selected
        else:
            print("[ERROR] Opcion invalida")
            return None
            
    except (ValueError, KeyboardInterrupt):
        print("[CANCELLED] Cancelado")
        return None

if __name__ == "__main__":
    # Mostrar selector interactivo
    selected = interactive_template_selector()
    
    if selected:
        print(f"\n[READY] Template '{selected}' listo para usar en Ollama UI")
        print("[INFO] Copia el texto de arriba y pegalo en Ollama UI")
        print("[INFO] Reemplaza [INSERTAR AQUI] con tus datos especificos")