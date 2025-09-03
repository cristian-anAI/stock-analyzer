"""
Generador final de contexto para Ollama - Sin Unicode, con datos reales
"""

import pandas as pd
import sqlite3
from pathlib import Path
from datetime import datetime

def main():
    print("GENERANDO CONTEXTO CON DATOS REALES...")
    
    project_root = Path(__file__).parent.parent
    context = generate_context_with_real_data(project_root)
    
    # Guardar archivo
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"ollama_real_context_{timestamp}.txt"
    
    with open(project_root / filename, 'w', encoding='utf-8') as f:
        f.write(context)
    
    # Copiar al clipboard
    try:
        import pyperclip
        pyperclip.copy(context)
        print("SUCCESS: Contexto copiado al clipboard!")
        print("-> Pega en Ollama con Ctrl+V")
    except ImportError:
        print("INFO: Para auto-copy: pip install pyperclip")
    
    print(f"Archivo guardado: {filename}")
    print(f"Tamaño contexto: {len(context):,} caracteres")
    print()
    print("INSTRUCCIONES PARA OLLAMA:")
    print("1. Ve a http://localhost:11434")
    print("2. Inicia NUEVO chat")
    print("3. Pega TODO el contexto (Ctrl+V)")
    print("4. Pregunta: 'Analiza mi situacion actual de trading'")

def generate_context_with_real_data(project_root):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Obtener datos reales
    positions_data = get_real_positions(project_root)
    portfolio_data = get_portfolio_state(project_root)
    
    context = f"""
# SISTEMA DE TRADING - CONTEXTO CON DATOS REALES PARA OLLAMA
Timestamp: {timestamp}

Eres un EXPERTO TRADER CUANTITATIVO. Tienes acceso a TODOS los datos reales de este sistema de trading automatizado.

## DATOS REALES ACTUALES

### POSICIONES ACTIVAS CON PNL REAL:
{format_real_positions(positions_data)}

### ESTADO DEL PORTFOLIO:
{format_portfolio(portfolio_data)}

### ANALISIS DE PERFORMANCE:
{calculate_performance_metrics(positions_data)}

## INFORMACION DEL SISTEMA

### ARQUITECTURA COMPLETA:
- Base de datos: SQLite (trading.db)
- API: FastAPI con endpoints REST
- Trading: Soporte LONG y SHORT positions  
- Activos: Stocks (acciones) y Crypto (criptomonedas)
- Capital: $10,000 stocks + $50,000 crypto allocated

### SERVICIOS PRINCIPALES:
- autotrader_service.py: Sistema de trading automatizado
- advanced_scoring_service.py: Algoritmo de scoring para SHORT positions
- portfolio_manager.py: Gestion completa del portfolio
- risk_management_service.py: Sistema de gestion de riesgo

### ESTRATEGIAS IMPLEMENTADAS:
- Base Strategy: Fundacion abstracta para todas las estrategias
- Swing Trading Strategy: Posiciones de medio plazo
- Crypto Competition Strategy: Trading especializado en criptomonedas

### SISTEMA DE SCORING SHORT:
- Algoritmo avanzado para identificar oportunidades SHORT
- Risk management con stop-loss y take-profit
- Monitoreo en tiempo real via /api/v1/short/positions

### COMANDOS DISPONIBLES:
```bash
# Iniciar sistema
python run_api.py
python start_autotrader.py

# Analisis y dashboards
python tools/analysis/analyze_performance.py
python tools/dashboards/short_dashboard.py
python tools/dashboards/portfolio_dashboard.py

# Testing
python tools/testing/test_complete_short_system.py
python tools/testing/test_advanced_scoring.py
```

### ESTRUCTURA DE ARCHIVOS CLAVE:
- src/api/services/autotrader_service.py - Trading automatizado
- src/api/services/advanced_scoring_service.py - Scoring SHORT
- src/traders/strategies/ - Implementacion de estrategias
- src/core/database_manager.py - Gestion de BD
- src/core/position_manager.py - Gestion de posiciones

## INSTRUCCIONES PARA TU ANALISIS:

DATOS DISPONIBLES:
- Posiciones reales con PnL actual exacto
- Precios de entrada vs precios actuales
- Performance historica completa
- Configuracion detallada de estrategias

CAPACIDADES DE ANALISIS:
- Analizar por que las posiciones estan perdiendo dinero
- Sugerir cuando cerrar posiciones especificas
- Optimizar estrategias basandose en performance real
- Recomendar ajustes de risk management
- Identificar patrones en losses/wins

COMO RESPONDER:
- Usa SIEMPRE datos reales del sistema
- Referencia archivos especificos cuando sea relevante
- Da recomendaciones concretas y accionables
- Justifica tecnicamente tus sugerencias
- Incluye metricas cuantitativas en tus analisis

EJEMPLO DE ANALISIS ESPERADO:
"Basado en tus posiciones SHORT actuales, veo que HP tiene un PnL de -$20.14 (-0.19%). 
Sugiero revisar el codigo en src/api/services/autotrader_service.py linea 156 donde se 
calcula el stop-loss para SHORT positions. El problema podria estar en..."

¿Que aspecto especifico del trading performance necesitas que analice primero?
"""

    return context.strip()

def get_real_positions(project_root):
    """Obtiene posiciones reales de la base de datos"""
    positions = []
    
    try:
        db_path = project_root / "trading.db"
        if not db_path.exists():
            print("Warning: trading.db not found")
            return positions
        
        conn = sqlite3.connect(db_path)
        
        # Query simplificado para evitar errores de columnas
        query = """
            SELECT p.symbol, p.pnl, p.pnl_percent, p.entry_price, p.current_price, 
                   p.value, p.asset_type, p.position_side, p.strategy_used
            FROM positions p
            ORDER BY abs(p.pnl) DESC
        """
        
        df = pd.read_sql_query(query, conn)
        positions = df.to_dict('records') if not df.empty else []
        
        print(f"Positions found: {len(positions)}")
        conn.close()
        
    except Exception as e:
        print(f"Error obteniendo posiciones: {e}")
    
    return positions

def get_portfolio_state(project_root):
    """Obtiene estado del portfolio"""
    portfolio = {}
    
    try:
        db_path = project_root / "trading.db"
        if not db_path.exists():
            return portfolio
        
        conn = sqlite3.connect(db_path)
        
        # Intentar obtener portfolio_state
        try:
            query = "SELECT * FROM portfolio_state ORDER BY created_at DESC LIMIT 1"
            df = pd.read_sql_query(query, conn)
            portfolio = df.to_dict('records')[0] if not df.empty else {}
        except:
            # Si no existe la tabla, crear portfolio basico
            portfolio = {"info": "Portfolio state table not found"}
        
        conn.close()
        
    except Exception as e:
        print(f"Error obteniendo portfolio: {e}")
    
    return portfolio

def format_real_positions(positions):
    """Formatea posiciones reales con todos los detalles"""
    if not positions:
        return "NO HAY POSICIONES ACTIVAS"
    
    formatted = f"TOTAL POSICIONES: {len(positions)}\n\n"
    
    for i, pos in enumerate(positions, 1):
        pnl = pos.get('pnl', 0)
        status = "GANANDO" if pnl > 0 else "PERDIENDO"
        
        formatted += f"""
{i}. {pos.get('symbol', 'N/A')} - {pos.get('position_side', 'N/A')} - {status}
   PnL: ${pnl:.2f} ({pos.get('pnl_percent', 0):.2f}%)
   Precios: ${pos.get('entry_price', 0):.2f} -> ${pos.get('current_price', 0):.2f}
   Valor posicion: ${pos.get('value', 0):,.2f}
   Estrategia: {pos.get('strategy_used', 'No especificada')}
   Tipo activo: {pos.get('asset_type', 'N/A')}

"""
    
    return formatted

def format_portfolio(portfolio):
    """Formatea estado del portfolio"""
    if not portfolio:
        return "NO HAY DATOS DEL PORTFOLIO"
    
    if "info" in portfolio:
        return portfolio["info"]
    
    return f"""
VALOR TOTAL: ${portfolio.get('total_value', 0):,.2f}
PnL TOTAL: ${portfolio.get('total_pnl', 0):,.2f}
RENDIMIENTO: {portfolio.get('total_return_percent', 0):.2f}%
CASH DISPONIBLE: ${portfolio.get('cash', 0):,.2f}
POSICIONES ACTIVAS: {portfolio.get('active_positions', 0)}
ULTIMA ACTUALIZACION: {portfolio.get('created_at', 'N/A')}
"""

def calculate_performance_metrics(positions):
    """Calcula métricas de performance"""
    if not positions:
        return "NO HAY DATOS PARA METRICAS"
    
    total_pnl = sum(pos.get('pnl', 0) for pos in positions)
    wins = len([pos for pos in positions if pos.get('pnl', 0) > 0])
    total = len(positions)
    win_rate = (wins / total * 100) if total > 0 else 0
    
    # Posiciones por tipo
    shorts = len([pos for pos in positions if pos.get('position_side') == 'SHORT'])
    longs = len([pos for pos in positions if pos.get('position_side') == 'LONG'])
    
    # PnL por tipo
    short_pnl = sum(pos.get('pnl', 0) for pos in positions if pos.get('position_side') == 'SHORT')
    long_pnl = sum(pos.get('pnl', 0) for pos in positions if pos.get('position_side') == 'LONG')
    
    return f"""
METRICAS DE PERFORMANCE:
   PnL Total: ${total_pnl:,.2f}
   Win Rate: {win_rate:.1f}% ({wins}/{total})
   Posiciones Ganadoras: {wins}
   Posiciones Perdedoras: {total - wins}
   
POR TIPO DE POSICION:
   SHORT: {shorts} posiciones (PnL: ${short_pnl:,.2f})
   LONG: {longs} posiciones (PnL: ${long_pnl:,.2f})
   
SITUACION ACTUAL:
   {"Portfolio en positivo" if total_pnl > 0 else "Portfolio en negativo - REQUIERE ATENCION"}
   {"Mayoria de posiciones ganando" if win_rate > 50 else "Mayoria de posiciones perdiendo - REVISAR ESTRATEGIAS"}

POSICIONES DETALLADAS PARA ANALISIS:
{get_positions_summary(positions)}
"""

def get_positions_summary(positions):
    """Resume las posiciones para análisis"""
    if not positions:
        return "No hay posiciones para analizar"
    
    summary = ""
    for pos in positions:
        pnl = pos.get('pnl', 0)
        symbol = pos.get('symbol', 'N/A')
        side = pos.get('position_side', 'N/A')
        pnl_pct = pos.get('pnl_percent', 0)
        
        summary += f"- {symbol} ({side}): ${pnl:.2f} ({pnl_pct:.2f}%)\n"
    
    return summary

if __name__ == "__main__":
    main()