"""
Script simplificado para ejecutar el sistema maestro de Ollama
Sin emojis para compatibilidad con Windows
"""

import os
import sys
from pathlib import Path

# Añadir el directorio local_ai al path
sys.path.append(str(Path(__file__).parent))

from code_knowledge_extractor import CodeKnowledgeExtractor
from excel_analyzer import ExcelAnalyzer
import json
import sqlite3
import pandas as pd
from datetime import datetime

def generate_complete_context():
    """Genera contexto completo sin interfaz interactiva"""
    
    project_root = Path(__file__).parent.parent
    
    print("GENERANDO CONOCIMIENTO COMPLETO PARA OLLAMA...")
    print("=" * 50)
    
    # 1. Extraer conocimiento del código
    print("1. Extrayendo conocimiento del código...")
    code_extractor = CodeKnowledgeExtractor()
    code_knowledge = code_extractor.generate_complete_knowledge_base()
    
    # 2. Analizar Excel files  
    print("2. Analizando archivos Excel...")
    excel_analyzer = ExcelAnalyzer()
    excel_files = excel_analyzer.find_all_excel_files()[:10]
    excel_analysis = []
    for excel_file in excel_files:
        analysis = excel_analyzer.analyze_excel_file(excel_file)
        excel_analysis.append(analysis)
    
    # 3. Obtener datos actuales
    print("3. Obteniendo datos actuales de trading...")
    current_data = get_current_trading_data(project_root)
    
    # 4. Generar contexto final
    print("4. Generando contexto final...")
    context = generate_context(code_knowledge, excel_analysis, current_data)
    
    # 5. Guardar y mostrar resultado
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"ollama_complete_context_{timestamp}.txt"
    
    output_path = project_root / filename
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(context)
    
    # Intentar copiar al clipboard
    try:
        import pyperclip
        pyperclip.copy(context)
        print("EXITO: Contexto copiado al clipboard!")
        print("-> Ve a Ollama UI y pega con Ctrl+V")
    except ImportError:
        print("INFO: Para auto-copy instala: pip install pyperclip")
    
    print("=" * 50)
    print("CONTEXTO GENERADO EXITOSAMENTE")
    print("=" * 50)
    print(f"Archivo: {filename}")
    print(f"Tamaño: {len(context):,} caracteres")
    print(f"Strategies: {len(code_knowledge.get('strategies', []))}")
    print(f"Services: {len(code_knowledge.get('services', []))}")
    print(f"Excel files: {len(excel_analysis)}")
    print(f"Posiciones: {len(current_data.get('positions', []))}")
    print()
    print("SIGUIENTE PASO:")
    print("1. Abre Ollama UI (http://localhost:11434)")
    print("2. Pega el contexto (Ctrl+V)")
    print("3. Ollama tendra TODO el conocimiento de tu codigo!")
    
    return context, output_path

def get_current_trading_data(project_root):
    """Obtiene datos actuales de trading"""
    data = {"positions": [], "portfolio": {}, "performance_metrics": {}}
    
    try:
        db_path = project_root / "trading.db"
        if not db_path.exists():
            return data
        
        conn = sqlite3.connect(db_path)
        
        # Posiciones
        positions = pd.read_sql_query("""
            SELECT symbol, pnl, pnl_percent, entry_price, current_price, 
                   value, asset_type, position_side, strategy_used
            FROM positions 
            ORDER BY abs(pnl) DESC
        """, conn)
        data["positions"] = positions.to_dict('records') if not positions.empty else []
        
        # Portfolio
        portfolio = pd.read_sql_query("""
            SELECT * FROM portfolio_state 
            ORDER BY created_at DESC LIMIT 1
        """, conn)
        data["portfolio"] = portfolio.to_dict('records')[0] if not portfolio.empty else {}
        
        # Métricas básicas
        if len(data["positions"]) > 0:
            positions_df = pd.DataFrame(data["positions"])
            wins = len(positions_df[positions_df['pnl'] > 0])
            total = len(positions_df)
            win_rate = (wins / total * 100) if total > 0 else 0
            total_pnl = positions_df['pnl'].sum()
            
            data["performance_metrics"] = {
                "win_rate_percent": round(win_rate, 2),
                "total_pnl": round(total_pnl, 2),
                "total_positions": total,
                "winning_positions": wins
            }
        
        conn.close()
        
    except Exception as e:
        data["error"] = str(e)
    
    return data

def generate_context(code_knowledge, excel_analysis, current_data):
    """Genera el contexto final para Ollama"""
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    context = f"""
# SISTEMA COMPLETO DE TRADING - CONTEXTO MAESTRO PARA OLLAMA
Timestamp: {timestamp}

Eres un EXPERTO TRADER CUANTITATIVO con acceso completo a este sistema avanzado de trading. Tienes el MISMO NIVEL DE CONOCIMIENTO que Claude Code sobre este proyecto.

## RESUMEN EJECUTIVO

Posiciones Activas: {len(current_data.get('positions', []))}
PnL Total: ${current_data.get('performance_metrics', {}).get('total_pnl', 0):,.2f}
Win Rate: {current_data.get('performance_metrics', {}).get('win_rate_percent', 0):.1f}%
Estrategias Implementadas: {len(code_knowledge.get('strategies', []))}
Reportes Excel: {len(excel_analysis)} archivos

## POSICIONES ACTIVAS DETALLADAS

{format_positions(current_data.get('positions', []))}

## ESTRATEGIAS DE TRADING IMPLEMENTADAS

{format_strategies(code_knowledge.get('strategies', []))}

## SERVICIOS Y ARQUITECTURA

{format_services(code_knowledge.get('services', []))}

## BASE DE DATOS

{format_database(code_knowledge.get('database_schema', []))}

## REPORTES EXCEL ANALIZADOS

{format_excel_files(excel_analysis)}

## API ENDPOINTS

{format_endpoints(code_knowledge.get('api_endpoints', []))}

---

INSTRUCCIONES PARA OLLAMA:
- Analiza TODA esta información como un experto trader cuantitativo
- Puedes referenciar archivos específicos con paths exactos
- Usa datos reales del sistema para análisis
- Proporciona recomendaciones concretas y accionables
- Identifica patrones, problemas y oportunidades
- Sugiere optimizaciones específicas del código

¿Qué necesitas analizar o optimizar en el sistema?
"""
    
    return context.strip()

def format_positions(positions):
    """Formatea posiciones"""
    if not positions:
        return "No hay posiciones activas"
    
    formatted = ""
    for i, pos in enumerate(positions[:15], 1):
        pnl_status = "GANANDO" if pos.get('pnl', 0) > 0 else "PERDIENDO"
        formatted += f"""
{i}. {pos.get('symbol', 'N/A')} ({pos.get('position_side', 'N/A')}) - {pnl_status}
   PnL: ${pos.get('pnl', 0):.2f} ({pos.get('pnl_percent', 0):.2f}%)
   Precio: ${pos.get('entry_price', 0):.2f} -> ${pos.get('current_price', 0):.2f}
   Valor: ${pos.get('value', 0):,.2f}
   Estrategia: {pos.get('strategy_used', 'N/A')}
"""
    
    return formatted

def format_strategies(strategies):
    """Formatea estrategias"""
    if not strategies:
        return "No se encontraron estrategias"
    
    formatted = ""
    for strategy in strategies:
        formatted += f"""
### {strategy['name']}
Archivo: {strategy['file_path']}
Descripción: {strategy['description'][:200]}...
Métodos: {len(strategy['methods'])} implementados
Condiciones entrada: {len(strategy['entry_conditions'])}
Condiciones salida: {len(strategy['exit_conditions'])}
Risk Management: {len(strategy['risk_management'])} parámetros

Métodos principales: {', '.join(strategy['methods'][:5])}

"""
    return formatted

def format_services(services):
    """Formatea servicios"""
    if not services:
        return "No se encontraron servicios"
    
    formatted = ""
    for service in services:
        formatted += f"""
{service['name']} - {service['file_path']}
Métodos: {len(service['key_methods'])} públicos
Dependencias: {len(service['dependencies'])}
"""
    return formatted

def format_database(schemas):
    """Formatea esquemas de BD"""
    if not schemas:
        return "Esquema de BD no disponible"
    
    formatted = ""
    for schema in schemas:
        formatted += f"""
{schema['table_name']}: {schema['purpose']}
Columnas: {len(schema['columns'])} campos
Estructura: {', '.join([col['name'] for col in schema['columns'][:5]])}

"""
    return formatted

def format_excel_files(excel_analysis):
    """Formatea análisis de Excel"""
    if not excel_analysis:
        return "No se encontraron archivos Excel"
    
    # Filtrar archivos con datos de trading
    trading_files = [f for f in excel_analysis if f.get('potential_trading_data', False)]
    
    formatted = f"Archivos con datos de trading: {len(trading_files)}\n\n"
    
    for excel_file in trading_files[:5]:
        formatted += f"""
{excel_file['filename']}
Modificado: {excel_file['modified_date']}
Hojas: {excel_file['summary']['total_sheets']}
Filas: {excel_file['summary']['total_rows']:,}
Insights: {len(excel_file['key_insights'])}

"""
    
    return formatted

def format_endpoints(endpoints):
    """Formatea endpoints"""
    if not endpoints:
        return "No se encontraron endpoints"
    
    grouped = {}
    for endpoint in endpoints:
        method = endpoint['method']
        if method not in grouped:
            grouped[method] = []
        grouped[method].append(endpoint['path'])
    
    formatted = ""
    for method, paths in grouped.items():
        formatted += f"\n{method}:\n"
        for path in paths[:8]:
            formatted += f"  {path}\n"
    
    return formatted

if __name__ == "__main__":
    generate_complete_context()