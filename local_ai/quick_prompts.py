"""
Prompts adicionales especializados para análisis específicos
"""

ADVANCED_PROMPTS = {
    
    "MARKET_SENTIMENT": """
    ANALISIS DE SENTIMENT DEL MERCADO
    
    Analiza el sentiment actual del mercado basándote en:
    - Posiciones largas vs cortas activas
    - Volatilidad reciente de los símbolos
    - Distribución de RSI en el watchlist
    - Patrones de volumen
    
    Dame insights sobre:
    1. ¿El mercado está en modo FEAR o GREED?
    2. ¿Hay oportunidades contrarian?
    3. ¿Qué sectores están sobrevalorados/infravalorados?
    4. Timing para siguiente entrada grande
    """,
    
    "RISK_ASSESSMENT": """
    EVALUACION DE RIESGO PORTFOLIO
    
    Evalúa los riesgos actuales del portfolio:
    - Concentración por símbolo/sector
    - Correlaciones entre posiciones
    - Exposure a eventos macro
    - Liquidez de las posiciones
    
    Identifica:
    1. Riesgos ocultos no detectados
    2. Metricas de riesgo faltantes
    3. Ajustes urgentes de position sizing
    4. Hedging opportunities
    """,
    
    "PERFORMANCE_DEEP_DIVE": """
    ANALISIS PROFUNDO DE PERFORMANCE
    
    Analiza el rendimiento desde múltiples ángulos:
    - Risk-adjusted returns por estrategia
    - Win rate vs average win/loss ratio
    - Time-based performance patterns
    - Drawdown recovery times
    
    Calcula y evalúa:
    1. Sharpe ratio real vs esperado
    2. Maximum drawdown risk
    3. Profit factor optimization
    4. Monthly/weekly performance patterns
    """,
    
    "STRATEGY_OPTIMIZATION": """
    OPTIMIZACION DE ESTRATEGIAS
    
    Sugiere mejoras específicas para:
    - Entry/exit timing
    - Position sizing algorithms  
    - Stop loss/take profit levels
    - Indicator combinations
    
    Recomienda:
    1. Parametros a ajustar (con valores especificos)
    2. Nuevos indicadores a integrar
    3. Timeframes alternativos a probar
    4. A/B testing framework
    """,
    
    "MARKET_REGIME_ANALYSIS": """
    ANALISIS DE REGIMEN DE MERCADO
    
    Identifica el régimen actual del mercado:
    - Trending vs ranging markets
    - Volatility regime (low/high vol)
    - Correlation regime changes
    - Sector rotation patterns
    
    Adapta estrategias para:
    1. Bull market optimization
    2. Bear market protection
    3. Sideways market tactics
    4. Regime change detection
    """,
    
    "CRYPTO_SPECIFIC": """
    ANALISIS ESPECIFICO CRYPTO
    
    Evalúa diferencias crypto vs stocks:
    - 24/7 trading implications
    - Higher volatility management
    - Correlation with BTC/ETH
    - DeFi vs CEX considerations
    
    Optimiza para crypto:
    1. Position sizing for volatility
    2. Weekend/night trading rules
    3. Correlation-based hedging
    4. Regulatory risk assessment
    """
}

def get_specialized_prompt(prompt_type="MARKET_SENTIMENT"):
    """Devuelve prompt especializado según el tipo"""
    return ADVANCED_PROMPTS.get(prompt_type, ADVANCED_PROMPTS["MARKET_SENTIMENT"])

def list_available_prompts():
    """Lista todos los prompts disponibles"""
    print("PROMPTS ESPECIALIZADOS DISPONIBLES:")
    print("=" * 50)
    for key, value in ADVANCED_PROMPTS.items():
        title = value.split('\n')[1].strip()  # Segunda línea es el título
        print(f"[{key}]: {title}")
    print("\n[INFO] Uso: analyzer.run_specialized_analysis('PROMPT_TYPE')")

if __name__ == "__main__":
    list_available_prompts()