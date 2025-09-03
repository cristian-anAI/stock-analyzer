"""
Ollama Bridge - Version without Unicode characters
"""

import pandas as pd
import sqlite3
from pathlib import Path
from datetime import datetime
from context_builder import OllamaContextBuilder
from quick_templates import QUICK_TEMPLATES, get_template

class OllamaBridge:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.db_path = self.project_root / "trading.db"
        self.context_builder = OllamaContextBuilder()
        
    def copy_to_clipboard(self, text):
        """Copia texto al clipboard"""
        try:
            import pyperclip
            pyperclip.copy(text)
            return True
        except Exception:
            return False
    
    def auto_context_with_data(self, template_name="performance_analysis"):
        """Genera contexto automático con datos reales insertados"""
        template = get_template(template_name)
        context = template["context"]
        
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Datos según el template
            if template_name == "performance_analysis":
                positions = pd.read_sql_query("""
                    SELECT symbol, pnl, pnl_percent, value, asset_type, position_side
                    FROM positions
                """, conn)
                
                portfolio = pd.read_sql_query("""
                    SELECT * FROM portfolio_state 
                    ORDER BY created_at DESC LIMIT 1
                """, conn)
                
                data_insert = f"POSICIONES:\n{positions.to_string()}\n\nPORTFOLIO STATE:\n{portfolio.to_string()}"
                
            elif template_name == "strategy_optimization":
                strategies = pd.read_sql_query("""
                    SELECT asset_type, strategy_name, config_key, config_value
                    FROM strategy_config WHERE is_active = 1
                """, conn)
                
                positions = pd.read_sql_query("""
                    SELECT strategy_used, asset_type, AVG(pnl_percent) as avg_pnl
                    FROM positions GROUP BY strategy_used, asset_type
                """, conn)
                
                data_insert = f"ESTRATEGIAS:\n{strategies.to_string()}\n\nPERFORMANCE:\n{positions.to_string()}"
                
            elif template_name == "position_review":
                positions = pd.read_sql_query("""
                    SELECT symbol, name, pnl, pnl_percent, entry_price, current_price, asset_type
                    FROM positions
                """, conn)
                
                stocks = pd.read_sql_query("""
                    SELECT symbol, name, score, change_percent FROM stocks 
                    ORDER BY score DESC LIMIT 10
                """, conn)
                
                data_insert = f"POSICIONES:\n{positions.to_string()}\n\nWATCHLIST STOCKS:\n{stocks.to_string()}"
                
            else:
                # Template genérico
                data_insert = "DATOS DEL SISTEMA:\n" + self.context_builder.get_database_summary()
            
            conn.close()
            
            # Reemplazar placeholder con datos reales
            context = context.replace("[INSERTAR AQUÍ datos de positions y portfolio_state]", data_insert)
            context = context.replace("[INSERTAR AQUÍ strategy_config data]", data_insert)
            context = context.replace("[INSERTAR AQUÍ posiciones actuales con PnL]", data_insert)
            context = context.replace("[INSERTAR AQUÍ todas las positions con detalles]", data_insert)
            
            return context
            
        except Exception as e:
            return f"{context}\n\n[ERROR] No se pudieron cargar datos automaticamente: {str(e)}"
    
    def quick_ollama_context(self, analysis_type="performance", auto_copy=True):
        """Genera contexto rápido y lo copia automáticamente"""
        
        context_map = {
            "performance": "performance_analysis",
            "strategy": "strategy_optimization", 
            "positions": "position_review",
            "risk": "risk_assessment",
            "market": "market_analysis",
            "automation": "automation_ideas"
        }
        
        template_name = context_map.get(analysis_type, "performance_analysis")
        context = self.auto_context_with_data(template_name)
        
        # Agregar timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        full_context = f"=== TRADING ANALYSIS - {timestamp} ===\n\n{context}"
        
        if auto_copy:
            if self.copy_to_clipboard(full_context):
                print("[OK] Contexto copiado al clipboard!")
                print("[INFO] Ve a Ollama UI y pega con Ctrl+V")
            else:
                print("[WARN] No se pudo copiar automaticamente")
                print("[INFO] Copia manualmente el contexto de abajo:")
        
        print("\n" + "="*60)
        print("CONTEXTO GENERADO:")
        print("="*60)
        print(full_context[:500] + "..." if len(full_context) > 500 else full_context)
        print("="*60)
        
        return full_context
    
    def interactive_ollama_helper(self):
        """Helper interactivo para Ollama UI"""
        print("OLLAMA UI HELPER")
        print("=" * 40)
        print("Genera contexto especifico para copiar/pegar en Ollama UI")
        
        print("\nQue analisis necesitas?")
        options = {
            "1": ("performance", "Analisis de Performance del Portfolio"),
            "2": ("strategy", "Optimizacion de Estrategias"), 
            "3": ("positions", "Revision de Posiciones Actuales"),
            "4": ("risk", "Evaluacion de Riesgo"),
            "5": ("market", "Analisis de Mercado"),
            "6": ("automation", "Ideas de Automatizacion")
        }
        
        for key, (_, desc) in options.items():
            print(f"{key}. {desc}")
        
        try:
            choice = input("\nElige opcion (1-6): ").strip()
            
            if choice in options:
                analysis_type, description = options[choice]
                print(f"\n[GENERATING] {description}")
                
                context = self.quick_ollama_context(analysis_type, auto_copy=True)
                
                print("\n[NEXT STEP]:")
                print("1. Ve a Ollama UI (http://localhost:11434)")
                print("2. Pega el contexto (Ctrl+V)")
                print("3. Ollama respondera con analisis especifico")
                
                # Guardar también en archivo
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"ollama_context_{analysis_type}_{timestamp}.txt"
                output_file = self.project_root / filename
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(context)
                
                print(f"[SAVED] Tambien guardado en: {filename}")
                
            else:
                print("[ERROR] Opcion invalida")
                
        except KeyboardInterrupt:
            print("\n[CANCELLED] Cancelado por usuario")
        except Exception as e:
            print(f"[ERROR] Error: {str(e)}")

def install_clipboard_support():
    """Instala pyperclip si no está disponible"""
    try:
        import pyperclip
        return True
    except ImportError:
        print("[INFO] Instalando soporte para clipboard...")
        try:
            import subprocess
            subprocess.check_call(["pip", "install", "pyperclip"])
            print("[OK] pyperclip instalado correctamente")
            return True
        except:
            print("[ERROR] No se pudo instalar pyperclip")
            print("[INFO] Instala manualmente: pip install pyperclip")
            return False

if __name__ == "__main__":
    # Verificar dependencias
    if not install_clipboard_support():
        print("[WARN] Funcionara sin auto-copy al clipboard")
    
    # Ejecutar helper interactivo
    bridge = OllamaBridge()
    bridge.interactive_ollama_helper()