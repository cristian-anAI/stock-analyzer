"""
Context Builder para Ollama UI
Genera contexto completo del sistema de trading para copiar/pegar en Ollama UI
"""

import pandas as pd
import sqlite3
import json
from pathlib import Path
from datetime import datetime
import glob

class OllamaContextBuilder:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.db_path = self.project_root / "trading.db"
        self.reports_dir = self.project_root / "reports"
        
    def get_basic_context(self):
        """Contexto básico del sistema"""
        return """
SISTEMA: Stock Analyzer - Sistema de trading automatizado
TECNOLOGÍA: FastAPI + SQLite + Python
CAPITAL: $10,000 stocks + $50,000 crypto
ESTRATEGIAS: SwingTrading, CryptoCompetition, RiskManagement
"""

    def get_database_summary(self):
        """Resume datos clave de la database"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Posiciones actuales
            positions = pd.read_sql_query("""
                SELECT symbol, type, pnl, pnl_percent, asset_type, position_side
                FROM positions 
                ORDER BY created_at DESC
            """, conn)
            
            # Top stocks
            stocks = pd.read_sql_query("""
                SELECT symbol, name, score, change_percent, sector
                FROM stocks 
                ORDER BY score DESC 
                LIMIT 10
            """, conn)
            
            # Top cryptos
            cryptos = pd.read_sql_query("""
                SELECT symbol, name, score, change_percent
                FROM cryptos 
                ORDER BY score DESC 
                LIMIT 5
            """, conn)
            
            # Portfolio state
            portfolio = pd.read_sql_query("""
                SELECT * FROM portfolio_state 
                ORDER BY created_at DESC 
                LIMIT 1
            """, conn)
            
            # Strategy config
            strategies = pd.read_sql_query("""
                SELECT asset_type, strategy_name, config_key, config_value
                FROM strategy_config 
                WHERE is_active = 1
            """, conn)
            
            conn.close()
            
            context = f"""
DATABASE SUMMARY:
- Posiciones activas: {len(positions)}
- PnL total: ${positions['pnl'].sum():.2f}
- PnL promedio: {positions['pnl_percent'].mean():.2f}%

POSICIONES ACTUALES:
{positions.to_string() if not positions.empty else "Ninguna"}

TOP STOCKS (por score):
{stocks[['symbol', 'score', 'change_percent', 'sector']].to_string()}

TOP CRYPTOS (por score):
{cryptos[['symbol', 'score', 'change_percent']].to_string()}

ESTADO PORTFOLIO:
{portfolio.to_string() if not portfolio.empty else "Sin datos"}

ESTRATEGIAS ACTIVAS:
{strategies.to_string() if not strategies.empty else "Sin configuración"}
"""
            return context
            
        except Exception as e:
            return f"ERROR accediendo a database: {str(e)}"

    def get_code_structure(self):
        """Estructura del código principal"""
        key_files = [
            "src/api/services/autotrader_service.py",
            "src/api/services/portfolio_manager.py", 
            "src/api/services/risk_management_service.py",
            "src/traders/strategies/base_strategy.py"
        ]
        
        context = "ESTRUCTURA CLAVE DEL CÓDIGO:\n"
        for file_path in key_files:
            full_path = self.project_root / file_path
            if full_path.exists():
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = len(content.split('\n'))
                    functions = content.count('def ')
                    classes = content.count('class ')
                    context += f"\n{file_path}:\n"
                    context += f"  - Líneas: {lines}\n"
                    context += f"  - Funciones: {functions}\n"  
                    context += f"  - Clases: {classes}\n"
        
        return context

    def build_complete_context(self, analysis_type="general"):
        """Construye contexto completo para Ollama UI"""
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        context = f"""
=== CONTEXTO COMPLETO SISTEMA DE TRADING ===
Generado: {timestamp}

{self.get_basic_context()}

{self.get_database_summary()}

{self.get_code_structure()}

=== CLAUDE.md (INSTRUCCIONES DEL PROYECTO) ===
Stock Analyzer es un sistema avanzado de trading automatizado para stocks y cryptos.
- FastAPI backend con múltiples estrategias
- Soporte LONG/SHORT positions  
- Monitoreo tiempo real
- Capital: $10k stocks, $50k crypto
- Database SQLite con posiciones, transacciones, símbolos

COMANDOS PRINCIPALES:
- python run_api.py (servidor principal)
- python start_autotrader.py (trading automático)
- python tools/analysis/analyze_performance.py

=== PROMPT PARA OLLAMA ===
Eres un EXPERTO TRADER CUANTITATIVO con 20+ años experiencia.

Analiza este sistema de trading basándote en el contexto anterior y responde específicamente sobre:
1. Performance actual del portfolio
2. Calidad de las estrategias implementadas  
3. Gestión del riesgo
4. Oportunidades de optimización
5. Problemas críticos a resolver

Responde de forma ESPECÍFICA y ACTIONABLE.

TU PREGUNTA: [ESCRIBE AQUÍ TU PREGUNTA ESPECÍFICA]

=== FIN DEL CONTEXTO ===
"""
        return context

    def get_quick_context(self, question_type="performance"):
        """Contexto rápido para preguntas específicas"""
        
        quick_contexts = {
            "performance": self.get_performance_context(),
            "strategies": self.get_strategies_context(), 
            "positions": self.get_positions_context(),
            "risk": self.get_risk_context(),
            "optimization": self.get_optimization_context()
        }
        
        return quick_contexts.get(question_type, self.get_basic_context())

    def get_performance_context(self):
        """Contexto específico para análisis de performance"""
        try:
            conn = sqlite3.connect(self.db_path)
            positions = pd.read_sql_query("SELECT * FROM positions", conn)
            portfolio = pd.read_sql_query("SELECT * FROM portfolio_state ORDER BY created_at DESC LIMIT 1", conn)
            conn.close()
            
            return f"""
ANÁLISIS DE PERFORMANCE:

POSICIONES ACTUALES:
{positions[['symbol', 'pnl', 'pnl_percent', 'asset_type']].to_string()}

ESTADO PORTFOLIO:
{portfolio.to_string()}

PREGUNTA PARA OLLAMA:
"Analiza la performance de este portfolio de trading. Dame insights específicos sobre ROI, drawdown, y sugerencias de mejora."
"""
        except:
            return "Error generando contexto de performance"

    def get_strategies_context(self):
        """Contexto específico para análisis de estrategias"""
        try:
            conn = sqlite3.connect(self.db_path)
            strategies = pd.read_sql_query("SELECT * FROM strategy_config WHERE is_active = 1", conn)
            conn.close()
            
            return f"""
ANÁLISIS DE ESTRATEGIAS:

CONFIGURACIÓN ACTUAL:
{strategies.to_string()}

PREGUNTA PARA OLLAMA:
"Evalúa estas estrategias de trading. ¿Son óptimas? ¿Qué parámetros debería ajustar para mejorar performance?"
"""
        except:
            return "Error generando contexto de estrategias"

    def get_positions_context(self):
        """Contexto específico para análisis de posiciones"""
        try:
            conn = sqlite3.connect(self.db_path)
            positions = pd.read_sql_query("SELECT * FROM positions", conn)
            conn.close()
            
            return f"""
ANÁLISIS DE POSICIONES:

POSICIONES DETALLADAS:
{positions.to_string()}

PREGUNTA PARA OLLAMA:
"Analiza estas posiciones de trading. ¿Cuáles debería mantener, cerrar o ajustar? ¿Hay riesgos concentrados?"
"""
        except:
            return "Error generando contexto de posiciones"

    def get_risk_context(self):
        """Contexto específico para análisis de riesgo"""
        return """
ANÁLISIS DE RIESGO:

CAPITAL ASIGNADO:
- Stocks: $10,000
- Crypto: $50,000

PREGUNTA PARA OLLAMA:
"Evalúa los riesgos de este sistema de trading. ¿La asignación de capital es óptima? ¿Qué riesgos no estoy viendo?"
"""

    def get_optimization_context(self):
        """Contexto específico para optimización"""
        return """
OPTIMIZACIÓN DEL SISTEMA:

TECNOLOGÍA: FastAPI + SQLite + Python
ESTRATEGIAS: SwingTrading, CryptoCompetition

PREGUNTA PARA OLLAMA:
"¿Cómo puedo optimizar este sistema de trading? Dame 5 mejoras específicas con mayor impacto en performance."
"""

    def save_context_to_file(self, context, filename=None):
        """Guarda contexto en archivo para fácil copia"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"ollama_context_{timestamp}.txt"
        
        output_file = self.project_root / filename
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(context)
        
        print(f"[SAVED] Contexto guardado en: {output_file}")
        return output_file

    def interactive_builder(self):
        """Constructor interactivo de contexto"""
        print("=== OLLAMA CONTEXT BUILDER ===")
        print("\n¿Qué tipo de análisis quieres hacer?")
        print("1. Análisis completo del sistema")
        print("2. Performance del portfolio")
        print("3. Efectividad de estrategias")
        print("4. Análisis de posiciones actuales") 
        print("5. Gestión de riesgo")
        print("6. Optimización del sistema")
        
        try:
            choice = input("\nElige opción (1-6): ").strip()
            
            contexts = {
                "1": self.build_complete_context(),
                "2": self.get_quick_context("performance"),
                "3": self.get_quick_context("strategies"),
                "4": self.get_quick_context("positions"),
                "5": self.get_quick_context("risk"),
                "6": self.get_quick_context("optimization")
            }
            
            context = contexts.get(choice, contexts["1"])
            
            print("\n" + "="*60)
            print("CONTEXTO GENERADO:")
            print("="*60)
            print(context)
            print("="*60)
            
            save_choice = input("\n¿Guardar en archivo? (y/n): ").strip().lower()
            if save_choice == 'y':
                self.save_context_to_file(context)
            
            print(f"\n[INFO] Copia el contexto de arriba y pégalo en Ollama UI")
            print(f"[INFO] Luego escribe tu pregunta específica al final")
            
        except KeyboardInterrupt:
            print("\n[INFO] Cancelado por usuario")
        except Exception as e:
            print(f"[ERROR] {str(e)}")

if __name__ == "__main__":
    builder = OllamaContextBuilder()
    builder.interactive_builder()