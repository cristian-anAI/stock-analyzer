"""
Generador rápido de contexto con datos reales para Ollama
"""

import pandas as pd
import sqlite3
from pathlib import Path
from datetime import datetime

def main():
    print("GENERANDO CONTEXTO CON DATOS REALES...")
    
    project_root = Path(__file__).parent.parent
    context = generate_context_with_real_data(project_root)
    
    # Guardar y copiar
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"ollama_real_data_context_{timestamp}.txt"
    
    with open(project_root / filename, 'w', encoding='utf-8') as f:
        f.write(context)
    
    try:
        import pyperclip
        pyperclip.copy(context)
        print("✅ CONTEXTO COPIADO AL CLIPBOARD!")
        print("-> Pega en Ollama con Ctrl+V")
    except ImportError:
        print("INFO: Para auto-copy: pip install pyperclip")
    
    print(f"Archivo: {filename}")
    print(f"Tamaño: {len(context):,} caracteres")
    print()
    print("INSTRUCCIONES:")
    print("1. Ve a Ollama UI (http://localhost:11434)")
    print("2. Inicia NUEVO chat")
    print("3. Pega TODO el contexto (Ctrl+V)")
    print("4. Pregunta: 'Resume mi situación actual de trading'")

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

### ANÁLISIS DE PERFORMANCE:
{calculate_performance_metrics(positions_data)}

## INFORMACIÓN DEL SISTEMA

### ARQUITECTURA:
- Base de datos: SQLite (trading.db)
- API: FastAPI con múltiples endpoints
- Trading: Soporte LONG y SHORT positions
- Activos: Stocks y Crypto

### SERVICIOS PRINCIPALES:
- autotrader_service.py: Trading automatizado
- advanced_scoring_service.py: Scoring para SHORT positions
- portfolio_manager.py: Gestión de portfolio
- risk_management_service.py: Gestión de riesgo

### ESTRATEGIAS:
- Base Strategy: Fundación para todas las estrategias
- Swing Trading: Posiciones de medio plazo
- Crypto Competition: Trading especializado en crypto

### COMANDOS DISPONIBLES:
```bash
# Iniciar sistema
python run_api.py
python start_autotrader.py

# Análisis
python tools/analysis/analyze_performance.py
python tools/dashboards/short_dashboard.py
```

## INSTRUCCIONES PARA TU ANÁLISIS:

DATOS DISPONIBLES:
- Posiciones reales con PnL actual
- Precios de entrada vs precios actuales
- Performance histórica
- Configuración de estrategias

CAPACIDADES:
- Analizar por qué las posiciones están perdiendo dinero
- Sugerir cuándo cerrar posiciones específicas
- Optimizar estrategias basándose en performance real
- Recomendar ajustes de risk management

RESPONDE SIEMPRE:
- Con análisis basado en datos reales
- Referencias a archivos específicos cuando sea relevante
- Recomendaciones concretas y accionables
- Justificación técnica de tus sugerencias

¿Qué aspecto específico del trading performance necesitas que analice?
"""

    return context.strip()

def get_real_positions(project_root):
    """Obtiene posiciones reales de la base de datos"""
    positions = []
    
    try:
        db_path = project_root / "trading.db"
        if not db_path.exists():
            return positions
        
        conn = sqlite3.connect(db_path)
        
        query = """
            SELECT p.symbol, p.pnl, p.pnl_percent, p.entry_price, p.current_price, 
                   p.value, p.asset_type, p.position_side, p.strategy_used,
                   p.entry_date, p.quantity, s.name, s.score
            FROM positions p
            LEFT JOIN stocks s ON p.symbol = s.symbol
            ORDER BY abs(p.pnl) DESC
        """
        
        df = pd.read_sql_query(query, conn)
        positions = df.to_dict('records') if not df.empty else []
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
        
        query = """
            SELECT * FROM portfolio_state 
            ORDER BY created_at DESC LIMIT 1
        """
        
        df = pd.read_sql_query(query, conn)
        portfolio = df.to_dict('records')[0] if not df.empty else {}
        conn.close()
        
    except Exception as e:
        print(f"Error obteniendo portfolio: {e}")
    
    return portfolio

def format_real_positions(positions):
    """Formatea posiciones reales con todos los detalles"""
    if not positions:
        return "❌ NO HAY POSICIONES ACTIVAS"
    
    formatted = f"📊 TOTAL POSICIONES: {len(positions)}\n\n"
    
    for i, pos in enumerate(positions, 1):
        pnl = pos.get('pnl', 0)
        status = "🟢 GANANDO" if pnl > 0 else "🔴 PERDIENDO"
        
        formatted += f"""
{i}. {pos.get('symbol', 'N/A')} - {pos.get('position_side', 'N/A')} - {status}
   📈 PnL: ${pnl:.2f} ({pos.get('pnl_percent', 0):.2f}%)
   💰 Precios: ${pos.get('entry_price', 0):.2f} → ${pos.get('current_price', 0):.2f}
   🎯 Valor posición: ${pos.get('value', 0):,.2f}
   📊 Cantidad: {pos.get('quantity', 'N/A')}
   🔧 Estrategia: {pos.get('strategy_used', 'No especificada')}
   🏢 Empresa: {pos.get('name', 'N/A')}
   ⭐ Score: {pos.get('score', 'N/A')}
   📅 Entrada: {pos.get('entry_date', 'N/A')}
   🏷️ Tipo: {pos.get('asset_type', 'N/A')}

"""
    
    return formatted

def format_portfolio(portfolio):
    """Formatea estado del portfolio"""
    if not portfolio:
        return "❌ NO HAY DATOS DEL PORTFOLIO"
    
    return f"""
💰 VALOR TOTAL: ${portfolio.get('total_value', 0):,.2f}
📊 PnL TOTAL: ${portfolio.get('total_pnl', 0):,.2f}
📈 RENDIMIENTO: {portfolio.get('total_return_percent', 0):.2f}%
🏦 CASH DISPONIBLE: ${portfolio.get('cash', 0):,.2f}
📍 POSICIONES ACTIVAS: {portfolio.get('active_positions', 0)}
🔄 ÚLTIMA ACTUALIZACIÓN: {portfolio.get('created_at', 'N/A')}
"""

def calculate_performance_metrics(positions):
    """Calcula métricas de performance"""
    if not positions:
        return "❌ NO HAY DATOS PARA MÉTRICAS"
    
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
📊 MÉTRICAS DE PERFORMANCE:
   💰 PnL Total: ${total_pnl:,.2f}
   🎯 Win Rate: {win_rate:.1f}% ({wins}/{total})
   📈 Posiciones Ganadoras: {wins}
   📉 Posiciones Perdedoras: {total - wins}
   
📍 POR TIPO DE POSICIÓN:
   🔴 SHORT: {shorts} posiciones (PnL: ${short_pnl:,.2f})
   🟢 LONG: {longs} posiciones (PnL: ${long_pnl:,.2f})
   
⚠️ SITUACIÓN ACTUAL:
   {"✅ Portfolio en positivo" if total_pnl > 0 else "❌ Portfolio en negativo - REQUIERE ATENCIÓN"}
   {"🎉 Mayoría de posiciones ganando" if win_rate > 50 else "⚠️ Mayoría de posiciones perdiendo"}
"""

if __name__ == "__main__":
    main()