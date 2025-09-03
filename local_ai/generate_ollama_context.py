"""
Generador limpio de contexto para Ollama - Compatible Windows
"""

import os
import ast
import json
import pandas as pd
from pathlib import Path
from datetime import datetime
import sqlite3
import re

def main():
    print("GENERANDO CONTEXTO COMPLETO PARA OLLAMA")
    print("=" * 50)
    
    project_root = Path(__file__).parent.parent
    
    # Generar contexto
    context = generate_complete_context(project_root)
    
    # Guardar archivo
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"ollama_context_complete_{timestamp}.txt"
    output_path = project_root / filename
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(context)
    
    # Copiar al clipboard si es posible
    try:
        import pyperclip
        pyperclip.copy(context)
        print("EXITO: Contexto copiado al clipboard!")
        print("-> Ve a Ollama UI (http://localhost:11434) y pega con Ctrl+V")
    except ImportError:
        print("INFO: Para auto-copy instala: pip install pyperclip")
    
    print("=" * 50)
    print("CONTEXTO GENERADO EXITOSAMENTE")
    print("=" * 50)
    print(f"Archivo guardado: {filename}")
    print(f"Tamaño del contexto: {len(context):,} caracteres")
    print()
    print("SIGUIENTE PASO:")
    print("1. Abre Ollama UI: http://localhost:11434")
    print("2. Inicia un nuevo chat")
    print("3. Pega todo el contexto (Ctrl+V)")
    print("4. Ollama ahora conoce TODO tu sistema de trading!")
    print()
    print("EJEMPLOS DE PREGUNTAS PARA OLLAMA:")
    print("- Analiza el performance de mis estrategias SHORT")
    print("- Que posiciones debería cerrar basado en los datos actuales?")
    print("- Sugiere mejoras especificas al archivo autotrader_service.py")
    print("- Como puedo optimizar mi win rate actual?")

def generate_complete_context(project_root):
    """Genera contexto completo combinando código, datos y reportes"""
    
    print("1. Analizando estrategias de trading...")
    strategies = extract_strategies(project_root)
    
    print("2. Analizando servicios del sistema...")
    services = extract_services(project_root)
    
    print("3. Extrayendo esquema de base de datos...")
    database_info = extract_database_info(project_root)
    
    print("4. Obteniendo datos actuales de trading...")
    current_data = get_current_trading_data(project_root)
    
    print("5. Analizando archivos Excel...")
    excel_info = analyze_excel_files(project_root)
    
    print("6. Compilando contexto final...")
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    context = f"""
# SISTEMA COMPLETO DE TRADING - CONTEXTO MAESTRO PARA OLLAMA
Generado: {timestamp}

Eres un EXPERTO TRADER CUANTITATIVO Y DESARROLLADOR. Tienes acceso completo a este sistema avanzado de trading automatizado. Conoces TODA la arquitectura, código, datos actuales y reportes.

## RESUMEN EJECUTIVO DEL SISTEMA

Total Posiciones Activas: {len(current_data.get('positions', []))}
PnL Total Actual: ${current_data.get('total_pnl', 0):,.2f}
Win Rate: {current_data.get('win_rate', 0):.1f}%
Estrategias Implementadas: {len(strategies)}
Servicios Activos: {len(services)}
Archivos Excel Analizados: {len(excel_info)}

## ESTADO ACTUAL DE POSICIONES - DATOS REALES

{format_current_positions(current_data.get('positions', []))}

## ESTRATEGIAS DE TRADING - IMPLEMENTACION COMPLETA

{format_strategies(strategies)}

## SERVICIOS Y ARQUITECTURA DEL SISTEMA

{format_services(services)}

## BASE DE DATOS - ESTRUCTURA COMPLETA

{format_database(database_info)}

## REPORTES Y ANALISIS EXCEL

{format_excel_analysis(excel_info)}

## ENDPOINTS DE LA API

{format_api_info(project_root)}

## CONFIGURACION DEL SISTEMA

{format_system_config(project_root)}

---

INSTRUCCIONES PARA TU ANALISIS:

CONOCIMIENTO DISPONIBLE:
- Tienes acceso a TODA la implementacion del codigo
- Conoces las posiciones actuales con PnL real
- Tienes datos de performance historica
- Puedes referenciar archivos especificos con lineas exactas
- Entiendes la arquitectura completa del sistema

CAPACIDADES DE ANALISIS:
- Optimizar estrategias basado en performance real
- Identificar problemas especificos en el codigo
- Sugerir mejoras tecnicas concretas
- Analizar riesgo de posiciones actuales
- Comparar efectividad entre estrategias

RESPONDE SIEMPRE CON:
- Referencias especificas a archivos (ej: src/traders/autotrader_service.py:156)
- Datos reales del sistema (posiciones, PnL, metricas)
- Recomendaciones accionables y especificas
- Ejemplos de codigo cuando sea relevante

¿Qué aspecto del sistema de trading necesitas analizar u optimizar?
"""
    
    return context.strip()

def extract_strategies(project_root):
    """Extrae información de estrategias"""
    strategies = []
    strategies_path = project_root / "src" / "traders" / "strategies"
    
    if strategies_path.exists():
        for py_file in strategies_path.glob("*.py"):
            if py_file.name.startswith("__"):
                continue
            
            try:
                content = py_file.read_text(encoding='utf-8')
                tree = ast.parse(content)
                
                strategy_info = {
                    "name": py_file.stem,
                    "file_path": str(py_file.relative_to(project_root)),
                    "methods": [],
                    "description": "Trading strategy implementation",
                    "risk_management": [],
                    "entry_conditions": [],
                    "exit_conditions": []
                }
                
                # Extraer métodos y clases
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        if "Strategy" in node.name:
                            strategy_info["name"] = node.name
                            docstring = ast.get_docstring(node)
                            if docstring:
                                strategy_info["description"] = docstring[:300]
                            
                            for item in node.body:
                                if isinstance(item, ast.FunctionDef):
                                    strategy_info["methods"].append(item.name)
                                    
                                    # Detectar condiciones
                                    if "entry" in item.name.lower() or "buy" in item.name.lower():
                                        strategy_info["entry_conditions"].append(item.name)
                                    elif "exit" in item.name.lower() or "sell" in item.name.lower():
                                        strategy_info["exit_conditions"].append(item.name)
                
                # Buscar patrones de risk management
                risk_patterns = re.findall(r'stop_loss|take_profit|risk', content, re.IGNORECASE)
                strategy_info["risk_management"] = list(set(risk_patterns))
                
                strategies.append(strategy_info)
                
            except Exception as e:
                continue
    
    return strategies

def extract_services(project_root):
    """Extrae información de servicios"""
    services = []
    services_path = project_root / "src" / "api" / "services"
    
    if services_path.exists():
        for py_file in services_path.glob("*.py"):
            if py_file.name.startswith("__"):
                continue
            
            try:
                content = py_file.read_text(encoding='utf-8')
                tree = ast.parse(content)
                
                service_info = {
                    "name": py_file.stem,
                    "file_path": str(py_file.relative_to(project_root)),
                    "classes": [],
                    "methods": [],
                    "purpose": f"Service: {py_file.stem}"
                }
                
                # Extraer clases y métodos
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        service_info["classes"].append(node.name)
                        for item in node.body:
                            if isinstance(item, ast.FunctionDef) and not item.name.startswith('_'):
                                service_info["methods"].append(f"{node.name}.{item.name}")
                
                services.append(service_info)
                
            except Exception as e:
                continue
    
    return services

def extract_database_info(project_root):
    """Extrae información de la base de datos"""
    db_info = {"tables": [], "error": None}
    
    try:
        db_path = project_root / "trading.db"
        if not db_path.exists():
            return db_info
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Obtener tablas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        for (table_name,) in tables:
            # Obtener info de cada tabla
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            
            # Obtener count de registros
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            record_count = cursor.fetchone()[0]
            
            table_info = {
                "name": table_name,
                "columns": [{"name": col[1], "type": col[2], "pk": bool(col[5])} for col in columns],
                "record_count": record_count,
                "purpose": get_table_purpose(table_name)
            }
            
            db_info["tables"].append(table_info)
        
        conn.close()
        
    except Exception as e:
        db_info["error"] = str(e)
    
    return db_info

def get_table_purpose(table_name):
    """Determina el propósito de una tabla"""
    purposes = {
        "positions": "Almacena todas las posiciones de trading (LONG/SHORT)",
        "transactions": "Registra historial de todas las transacciones",
        "portfolio_state": "Estado actual del portfolio y capital",
        "symbols": "Símbolos monitoreados con scores y datos",
        "stocks": "Información detallada de acciones",
        "crypto": "Datos de criptomonedas",
        "strategy_config": "Configuración de estrategias"
    }
    return purposes.get(table_name, f"Tabla del sistema: {table_name}")

def get_current_trading_data(project_root):
    """Obtiene datos actuales del sistema"""
    data = {"positions": [], "total_pnl": 0, "win_rate": 0}
    
    try:
        db_path = project_root / "trading.db"
        if not db_path.exists():
            return data
        
        conn = sqlite3.connect(db_path)
        
        # Posiciones detalladas
        positions_query = """
            SELECT p.symbol, p.pnl, p.pnl_percent, p.entry_price, p.current_price, 
                   p.value, p.asset_type, p.position_side, p.strategy_used, p.entry_date,
                   s.name, s.score
            FROM positions p
            LEFT JOIN stocks s ON p.symbol = s.symbol
            ORDER BY abs(p.pnl) DESC
        """
        
        positions_df = pd.read_sql_query(positions_query, conn)
        data["positions"] = positions_df.to_dict('records') if not positions_df.empty else []
        
        # Calcular métricas
        if data["positions"]:
            total_pnl = sum(pos['pnl'] for pos in data["positions"])
            wins = len([pos for pos in data["positions"] if pos['pnl'] > 0])
            total_pos = len(data["positions"])
            
            data["total_pnl"] = total_pnl
            data["win_rate"] = (wins / total_pos * 100) if total_pos > 0 else 0
        
        conn.close()
        
    except Exception as e:
        data["error"] = str(e)
    
    return data

def analyze_excel_files(project_root):
    """Analiza archivos Excel disponibles"""
    excel_files = []
    
    search_paths = [
        project_root,
        project_root / "reports",
        project_root / "archive"
    ]
    
    for search_path in search_paths:
        if search_path.exists():
            for excel_file in search_path.glob("*.xlsx"):
                try:
                    file_info = {
                        "filename": excel_file.name,
                        "path": str(excel_file),
                        "size_mb": round(excel_file.stat().st_size / 1024 / 1024, 2),
                        "modified": datetime.fromtimestamp(excel_file.stat().st_mtime).strftime("%Y-%m-%d"),
                        "sheets": [],
                        "has_trading_data": False
                    }
                    
                    # Analizar hojas
                    xl_file = pd.ExcelFile(excel_file)
                    file_info["sheets"] = xl_file.sheet_names
                    
                    # Detectar datos de trading
                    for sheet in xl_file.sheet_names[:3]:
                        df = pd.read_excel(xl_file, sheet_name=sheet, nrows=10)
                        columns = [col.lower() for col in df.columns]
                        
                        trading_keywords = ['symbol', 'pnl', 'profit', 'position', 'price', 'return']
                        if any(keyword in ' '.join(columns) for keyword in trading_keywords):
                            file_info["has_trading_data"] = True
                            break
                    
                    excel_files.append(file_info)
                    
                except Exception:
                    continue
    
    return excel_files

def format_current_positions(positions):
    """Formatea posiciones actuales"""
    if not positions:
        return "No hay posiciones activas en este momento."
    
    formatted = ""
    for i, pos in enumerate(positions[:20], 1):  # Top 20
        status = "GANANDO" if pos.get('pnl', 0) > 0 else "PERDIENDO"
        
        formatted += f"""
{i}. {pos.get('symbol', 'N/A')} - {pos.get('position_side', 'N/A')} - {status}
   PnL: ${pos.get('pnl', 0):,.2f} ({pos.get('pnl_percent', 0):.2f}%)
   Precios: ${pos.get('entry_price', 0):.2f} -> ${pos.get('current_price', 0):.2f}
   Valor posición: ${pos.get('value', 0):,.2f}
   Estrategia usada: {pos.get('strategy_used', 'No especificada')}
   Nombre: {pos.get('name', 'N/A')}
   Score del símbolo: {pos.get('score', 'N/A')}
   Fecha entrada: {pos.get('entry_date', 'N/A')}
"""
    
    return formatted.strip()

def format_strategies(strategies):
    """Formatea estrategias"""
    if not strategies:
        return "No se encontraron estrategias implementadas."
    
    formatted = ""
    for strategy in strategies:
        formatted += f"""
### {strategy['name']}
Archivo: {strategy['file_path']}

Descripción: {strategy['description']}

Implementación:
- Métodos implementados: {len(strategy['methods'])} ({', '.join(strategy['methods'][:5])})
- Condiciones de entrada: {len(strategy['entry_conditions'])} ({', '.join(strategy['entry_conditions'])})
- Condiciones de salida: {len(strategy['exit_conditions'])} ({', '.join(strategy['exit_conditions'])})
- Risk management: {', '.join(strategy['risk_management']) if strategy['risk_management'] else 'No detectado'}

---
"""
    
    return formatted

def format_services(services):
    """Formatea servicios"""
    if not services:
        return "No se encontraron servicios."
    
    formatted = ""
    for service in services:
        formatted += f"""
### {service['name']}
Archivo: {service['file_path']}
Propósito: {service['purpose']}

Clases: {', '.join(service['classes']) if service['classes'] else 'Ninguna'}
Métodos públicos: {len(service['methods'])} ({', '.join(service['methods'][:5])})

---
"""
    
    return formatted

def format_database(db_info):
    """Formatea información de base de datos"""
    if db_info.get("error"):
        return f"Error accediendo a la base de datos: {db_info['error']}"
    
    if not db_info.get("tables"):
        return "No se encontraron tablas en la base de datos."
    
    formatted = ""
    for table in db_info["tables"]:
        formatted += f"""
### Tabla: {table['name']}
Propósito: {table['purpose']}
Registros: {table['record_count']:,}
Columnas: {len(table['columns'])}

Estructura:
{', '.join([f"{col['name']} ({col['type']})" for col in table['columns'][:8]])}

---
"""
    
    return formatted

def format_excel_analysis(excel_files):
    """Formatea análisis de Excel"""
    if not excel_files:
        return "No se encontraron archivos Excel."
    
    trading_files = [f for f in excel_files if f['has_trading_data']]
    
    formatted = f"Total archivos Excel encontrados: {len(excel_files)}\n"
    formatted += f"Archivos con datos de trading: {len(trading_files)}\n\n"
    
    for excel_file in excel_files[:10]:  # Top 10
        status = "CON DATOS DE TRADING" if excel_file['has_trading_data'] else "ARCHIVO GENERAL"
        
        formatted += f"""
{excel_file['filename']} - {status}
Modificado: {excel_file['modified']}
Tamaño: {excel_file['size_mb']} MB
Hojas: {', '.join(excel_file['sheets'][:5])}

---
"""
    
    return formatted

def format_api_info(project_root):
    """Formatea información de la API"""
    api_path = project_root / "src" / "api" / "routers"
    endpoints = []
    
    if api_path.exists():
        for py_file in api_path.glob("*.py"):
            if py_file.name.startswith("__"):
                continue
            
            try:
                content = py_file.read_text(encoding='utf-8')
                
                # Buscar decoradores de FastAPI
                patterns = [
                    r'@router\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']',
                    r'@app\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']'
                ]
                
                for pattern in patterns:
                    matches = re.findall(pattern, content)
                    for method, path in matches:
                        endpoints.append(f"{method.upper()} {path}")
                        
            except Exception:
                continue
    
    if not endpoints:
        return "No se encontraron endpoints de API."
    
    return f"Endpoints encontrados ({len(endpoints)}):\n" + "\n".join(endpoints[:20])

def format_system_config(project_root):
    """Formatea configuración del sistema"""
    config_info = ""
    
    # Leer CLAUDE.md si existe
    claude_md = project_root / "CLAUDE.md"
    if claude_md.exists():
        content = claude_md.read_text(encoding='utf-8')[:1000]
        config_info += f"Configuración del proyecto (CLAUDE.md):\n{content}...\n\n"
    
    # Leer requirements.txt
    requirements = project_root / "requirements.txt"
    if requirements.exists():
        deps = requirements.read_text(encoding='utf-8')
        config_info += f"Dependencias instaladas:\n{deps}\n"
    
    return config_info if config_info else "Configuración del sistema no encontrada."

if __name__ == "__main__":
    main()