"""
SISTEMA MAESTRO OLLAMA - Conocimiento Completo del Código
Equivalente a tener Claude Code pero en Ollama local
"""

import json
import os
from pathlib import Path
from datetime import datetime
from code_knowledge_extractor import CodeKnowledgeExtractor
from ollama_context_generator import OllamaContextGenerator  
from excel_analyzer import ExcelAnalyzer
import sqlite3
import pandas as pd

class OllamaMasterSystem:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.knowledge_cache_path = self.project_root / "local_ai" / "knowledge_cache.json"
        self.last_update_file = self.project_root / "local_ai" / "last_knowledge_update.txt"
        
        # Inicializar componentes
        self.code_extractor = CodeKnowledgeExtractor()
        self.context_generator = OllamaContextGenerator()
        self.excel_analyzer = ExcelAnalyzer()
        
        self.master_knowledge = {
            "last_updated": None,
            "system_version": "1.0",
            "code_knowledge": {},
            "excel_analysis": {},
            "current_data": {},
            "context_templates": {},
            "quick_access": {}
        }
    
    def should_update_knowledge(self) -> bool:
        """Determina si necesita actualizar el conocimiento"""
        if not self.knowledge_cache_path.exists():
            return True
        
        if not self.last_update_file.exists():
            return True
        
        try:
            last_update = datetime.fromtimestamp(self.last_update_file.stat().st_mtime)
            time_diff = datetime.now() - last_update
            
            # Actualizar si han pasado más de 6 horas
            return time_diff.total_seconds() > 21600
            
        except:
            return True
    
    def build_complete_knowledge_base(self, force_update: bool = False):
        """Construye la base de conocimiento completa"""
        
        if not force_update and not self.should_update_knowledge():
            print("📚 Cargando conocimiento desde cache...")
            return self.load_cached_knowledge()
        
        print("🔄 Construyendo base de conocimiento completa...")
        
        # 1. Extraer conocimiento del código
        print("   🔍 Extrayendo conocimiento del código...")
        self.master_knowledge["code_knowledge"] = self.code_extractor.generate_complete_knowledge_base()
        
        # 2. Analizar reportes Excel
        print("   📊 Analizando reportes Excel...")
        excel_files = self.excel_analyzer.find_all_excel_files()[:20]  # Top 20
        excel_analysis = []
        for excel_file in excel_files:
            analysis = self.excel_analyzer.analyze_excel_file(excel_file)
            excel_analysis.append(analysis)
        self.master_knowledge["excel_analysis"] = excel_analysis
        
        # 3. Obtener datos actuales del trading
        print("   💹 Obteniendo datos actuales de trading...")
        self.master_knowledge["current_data"] = self._get_comprehensive_trading_data()
        
        # 4. Generar templates de contexto rápido
        print("   📝 Generando templates de contexto...")
        self.master_knowledge["context_templates"] = self._generate_context_templates()
        
        # 5. Crear índices de acceso rápido
        print("   ⚡ Creando índices de acceso rápido...")
        self.master_knowledge["quick_access"] = self._generate_quick_access_indices()
        
        # Marcar timestamp
        self.master_knowledge["last_updated"] = datetime.now().isoformat()
        
        # Guardar cache
        self.save_knowledge_cache()
        
        print("✅ Base de conocimiento completa construida!")
        return self.master_knowledge
    
    def _get_comprehensive_trading_data(self) -> dict:
        """Obtiene datos comprehensivos del sistema de trading"""
        data = {
            "positions": [],
            "portfolio": {},
            "recent_transactions": [],
            "performance_metrics": {},
            "symbols_watchlist": [],
            "strategy_performance": []
        }
        
        try:
            db_path = self.project_root / "trading.db"
            if not db_path.exists():
                return data
            
            conn = sqlite3.connect(db_path)
            
            # Posiciones con detalles completos
            positions_query = """
                SELECT p.*, 
                       s.name, s.sector, s.market_cap, s.score as symbol_score,
                       CASE 
                         WHEN p.position_side = 'SHORT' THEN 'SHORT 📉'
                         WHEN p.position_side = 'LONG' THEN 'LONG 📈'
                         ELSE p.position_side 
                       END as position_display
                FROM positions p
                LEFT JOIN stocks s ON p.symbol = s.symbol
                ORDER BY abs(p.pnl) DESC
            """
            
            positions_df = pd.read_sql_query(positions_query, conn)
            if not positions_df.empty:
                data["positions"] = positions_df.to_dict('records')
            
            # Portfolio state con histórico
            portfolio_query = """
                SELECT * FROM portfolio_state 
                ORDER BY created_at DESC LIMIT 5
            """
            portfolio_df = pd.read_sql_query(portfolio_query, conn)
            if not portfolio_df.empty:
                data["portfolio"] = {
                    "current": portfolio_df.iloc[0].to_dict(),
                    "history": portfolio_df.to_dict('records')
                }
            
            # Transacciones recientes con contexto
            transactions_query = """
                SELECT t.*, p.name, p.strategy_used
                FROM transactions t
                LEFT JOIN positions p ON t.symbol = p.symbol
                ORDER BY t.created_at DESC LIMIT 50
            """
            transactions_df = pd.read_sql_query(transactions_query, conn)
            if not transactions_df.empty:
                data["recent_transactions"] = transactions_df.to_dict('records')
            
            # Métricas de performance
            data["performance_metrics"] = self._calculate_performance_metrics(conn)
            
            # Watchlist con scores
            watchlist_query = """
                SELECT symbol, name, score, change_percent, sector
                FROM stocks 
                ORDER BY score DESC LIMIT 50
            """
            watchlist_df = pd.read_sql_query(watchlist_query, conn)
            if not watchlist_df.empty:
                data["symbols_watchlist"] = watchlist_df.to_dict('records')
            
            # Performance por estrategia
            strategy_query = """
                SELECT strategy_used, 
                       COUNT(*) as positions_count,
                       AVG(pnl) as avg_pnl,
                       SUM(pnl) as total_pnl,
                       AVG(pnl_percent) as avg_return_pct
                FROM positions 
                WHERE strategy_used IS NOT NULL
                GROUP BY strategy_used
                ORDER BY total_pnl DESC
            """
            strategy_df = pd.read_sql_query(strategy_query, conn)
            if not strategy_df.empty:
                data["strategy_performance"] = strategy_df.to_dict('records')
            
            conn.close()
            
        except Exception as e:
            print(f"Error getting trading data: {e}")
            data["error"] = str(e)
        
        return data
    
    def _calculate_performance_metrics(self, conn) -> dict:
        """Calcula métricas avanzadas de performance"""
        try:
            # Win rate
            win_rate_query = "SELECT COUNT(*) as wins FROM positions WHERE pnl > 0"
            total_query = "SELECT COUNT(*) as total FROM positions"
            
            wins = pd.read_sql_query(win_rate_query, conn).iloc[0]['wins']
            total = pd.read_sql_query(total_query, conn).iloc[0]['total']
            win_rate = (wins / total * 100) if total > 0 else 0
            
            # Profit factor
            profit_query = "SELECT SUM(pnl) as total_profit FROM positions WHERE pnl > 0"
            loss_query = "SELECT SUM(abs(pnl)) as total_loss FROM positions WHERE pnl < 0"
            
            profit = pd.read_sql_query(profit_query, conn).iloc[0]['total_profit'] or 0
            loss = pd.read_sql_query(loss_query, conn).iloc[0]['total_loss'] or 1
            profit_factor = profit / loss if loss > 0 else 0
            
            # Drawdown (simplificado)
            pnl_series = pd.read_sql_query("SELECT pnl FROM positions ORDER BY created_at", conn)['pnl']
            cumulative_pnl = pnl_series.cumsum()
            running_max = cumulative_pnl.expanding().max()
            drawdown = (cumulative_pnl - running_max).min() if len(cumulative_pnl) > 0 else 0
            
            return {
                "win_rate_percent": round(win_rate, 2),
                "profit_factor": round(profit_factor, 2),
                "max_drawdown": round(drawdown, 2),
                "total_positions": int(total),
                "winning_positions": int(wins),
                "losing_positions": int(total - wins)
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def _generate_context_templates(self) -> dict:
        """Genera templates de contexto para diferentes análisis"""
        return {
            "complete_analysis": {
                "name": "Análisis Completo del Sistema",
                "description": "Contexto completo con código, datos y reportes",
                "includes": ["code", "data", "excel", "performance"]
            },
            "trading_performance": {
                "name": "Análisis de Performance de Trading", 
                "description": "Enfoque en métricas y performance de estrategias",
                "includes": ["positions", "performance", "strategies"]
            },
            "code_review": {
                "name": "Revisión Técnica del Código",
                "description": "Análisis de arquitectura y código",
                "includes": ["strategies", "services", "database"]
            },
            "excel_reports": {
                "name": "Análisis de Reportes Excel",
                "description": "Enfoque en datos de reportes",
                "includes": ["excel", "recent_data"]
            },
            "strategy_optimization": {
                "name": "Optimización de Estrategias",
                "description": "Análisis para mejorar estrategias",
                "includes": ["strategy_performance", "positions", "code"]
            }
        }
    
    def _generate_quick_access_indices(self) -> dict:
        """Genera índices para acceso rápido a información"""
        indices = {
            "active_positions_count": 0,
            "total_pnl": 0,
            "win_rate": 0,
            "strategies_implemented": 0,
            "excel_files_count": 0,
            "recent_files": [],
            "top_performers": [],
            "worst_performers": [],
            "key_files": []
        }
        
        try:
            # Datos actuales
            current_data = self.master_knowledge.get("current_data", {})
            
            if "positions" in current_data:
                positions = current_data["positions"]
                indices["active_positions_count"] = len(positions)
                indices["total_pnl"] = sum(pos.get("pnl", 0) for pos in positions)
                
                # Top y worst performers
                sorted_positions = sorted(positions, key=lambda x: x.get("pnl", 0), reverse=True)
                indices["top_performers"] = sorted_positions[:3]
                indices["worst_performers"] = sorted_positions[-3:]
            
            # Performance metrics
            if "performance_metrics" in current_data:
                indices["win_rate"] = current_data["performance_metrics"].get("win_rate_percent", 0)
            
            # Estrategias
            code_knowledge = self.master_knowledge.get("code_knowledge", {})
            if "strategies" in code_knowledge:
                indices["strategies_implemented"] = len(code_knowledge["strategies"])
            
            # Excel files
            excel_analysis = self.master_knowledge.get("excel_analysis", [])
            indices["excel_files_count"] = len(excel_analysis)
            
            # Archivos recientes (últimos 7 días)
            recent_files = []
            for file_analysis in excel_analysis:
                if file_analysis.get("summary", {}).get("file_age_days", 999) <= 7:
                    recent_files.append(file_analysis["filename"])
            indices["recent_files"] = recent_files[:5]
            
        except Exception as e:
            indices["error"] = str(e)
        
        return indices
    
    def generate_smart_context_for_ollama(self, analysis_type: str = "complete") -> str:
        """Genera contexto inteligente basado en el conocimiento completo"""
        
        # Asegurar que tenemos conocimiento actualizado
        if not self.master_knowledge.get("last_updated"):
            self.build_complete_knowledge_base()
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        context = f"""
# 🤖 SISTEMA COMPLETO DE TRADING - CONTEXTO MAESTRO PARA OLLAMA
**Generado:** {timestamp}
**Tipo de Análisis:** {analysis_type.upper()}

Eres un EXPERTO TRADER CUANTITATIVO con acceso completo a este sistema avanzado de trading. Tienes el MISMO NIVEL DE CONOCIMIENTO que Claude Code sobre este proyecto.

## ⚡ RESUMEN EJECUTIVO INSTANTÁNEO

{self._format_quick_summary()}

## 📊 ESTADO ACTUAL DEL TRADING

{self._format_current_trading_state()}

## 🎯 ESTRATEGIAS Y CÓDIGO (IMPLEMENTACIÓN COMPLETA)

{self._format_complete_strategies()}

## 🔧 ARQUITECTURA Y SERVICIOS

{self._format_system_architecture()}

## 📈 ANÁLISIS DE REPORTES EXCEL

{self._format_excel_insights()}

## 🗄️ BASE DE DATOS Y ESQUEMAS

{self._format_database_complete()}

## 📋 COMANDOS Y HERRAMIENTAS DISPONIBLES

{self._format_available_tools()}

## 🎖️ MÉTRICAS DE PERFORMANCE AVANZADAS

{self._format_advanced_metrics()}

---

## 🧠 INSTRUCCIONES PARA ANÁLISIS EXPERTO

**TU NIVEL DE CONOCIMIENTO:**
- Conoces TODA la arquitectura del sistema
- Tienes acceso a TODOS los datos actuales
- Puedes referenciar archivos específicos con paths exactos
- Entiendes las estrategias de trading implementadas
- Tienes contexto completo de los reportes Excel

**CAPACIDADES DE ANÁLISIS:**
- Optimización de estrategias basada en performance real
- Identificación de problemas en el código
- Sugerencias de mejoras específicas
- Análisis de riesgo avanzado
- Comparación entre estrategias

**RESPONDE SIEMPRE CON:**
- Referencias específicas a archivos (ej: `src/traders/strategies/swing_strategy.py:45`)
- Datos reales del sistema (posiciones, PnL, métricas)
- Recomendaciones accionables y específicas
- Código de ejemplo cuando sea relevante

**¿Qué análisis específico necesitas del sistema?**
        """
        
        return context.strip()
    
    def _format_quick_summary(self) -> str:
        """Resumen ejecutivo rápido"""
        quick_access = self.master_knowledge.get("quick_access", {})
        
        return f"""```
💰 Posiciones Activas: {quick_access.get('active_positions_count', 0)}
📊 PnL Total: ${quick_access.get('total_pnl', 0):,.2f}
🎯 Win Rate: {quick_access.get('win_rate', 0):.1f}%
🔧 Estrategias: {quick_access.get('strategies_implemented', 0)} implementadas
📄 Reportes Excel: {quick_access.get('excel_files_count', 0)} archivos
⏰ Archivos recientes: {len(quick_access.get('recent_files', []))}
```"""
    
    def _format_current_trading_state(self) -> str:
        """Estado actual detallado del trading"""
        current_data = self.master_knowledge.get("current_data", {})
        positions = current_data.get("positions", [])
        
        if not positions:
            return "**No hay posiciones activas**"
        
        formatted = "### 📈 Posiciones Activas Detalladas\n\n"
        
        for i, pos in enumerate(positions[:10], 1):  # Top 10
            pnl_emoji = "📈" if pos.get('pnl', 0) > 0 else "📉"
            formatted += f"""
**{i}. {pos.get('symbol', 'N/A')} ({pos.get('position_display', pos.get('position_side', 'N/A'))})**
- PnL: ${pos.get('pnl', 0):.2f} ({pos.get('pnl_percent', 0):.2f}%) {pnl_emoji}
- Precio: ${pos.get('entry_price', 0):.2f} → ${pos.get('current_price', 0):.2f}
- Valor: ${pos.get('value', 0):,.2f}
- Estrategia: `{pos.get('strategy_used', 'N/A')}`
- Score: {pos.get('symbol_score', 'N/A')}
"""
        
        return formatted
    
    def _format_complete_strategies(self) -> str:
        """Información completa de estrategias"""
        strategies = self.master_knowledge.get("code_knowledge", {}).get("strategies", [])
        
        if not strategies:
            return "**No se encontraron estrategias**"
        
        formatted = ""
        for strategy in strategies:
            formatted += f"""
### 🎯 {strategy['name']}
**Archivo:** `{strategy['file_path']}`

**Descripción:** {strategy['description'][:300]}...

**Implementación:**
- Métodos: {len(strategy['methods'])} implementados
- Condiciones entrada: {len(strategy['entry_conditions'])}
- Condiciones salida: {len(strategy['exit_conditions'])}
- Risk Management: {len(strategy['risk_management'])} parámetros

**Métodos clave:**
```python
{', '.join(strategy['methods'][:8])}
```

---
"""
        
        return formatted
    
    def _format_system_architecture(self) -> str:
        """Arquitectura completa del sistema"""
        services = self.master_knowledge.get("code_knowledge", {}).get("services", [])
        
        formatted = "### 🔧 Servicios Implementados\n\n"
        
        for service in services:
            formatted += f"""
**{service['name']}**
- Archivo: `{service['file_path']}`
- Métodos: {len(service['key_methods'])} públicos
- Dependencias: {len(service['dependencies'])}

"""
        
        return formatted
    
    def _format_excel_insights(self) -> str:
        """Insights de archivos Excel"""
        excel_analysis = self.master_knowledge.get("excel_analysis", [])
        
        if not excel_analysis:
            return "**No se encontraron reportes Excel**"
        
        # Filtrar archivos con datos de trading
        trading_files = [f for f in excel_analysis if f.get('potential_trading_data', False)]
        
        formatted = f"### 📊 Reportes con Datos de Trading ({len(trading_files)} encontrados)\n\n"
        
        for excel_file in trading_files[:5]:  # Top 5
            formatted += f"""
**{excel_file['filename']}**
- Modificado: {excel_file['modified_date']}
- Hojas: {excel_file['summary']['total_sheets']}
- Filas: {excel_file['summary']['total_rows']:,}
- Insights: {len(excel_file['key_insights'])}

"""
        
        return formatted
    
    def _format_database_complete(self) -> str:
        """Esquema completo de base de datos"""
        schemas = self.master_knowledge.get("code_knowledge", {}).get("database_schema", [])
        
        formatted = "### 🗄️ Esquema de Base de Datos\n\n"
        
        for schema in schemas:
            formatted += f"""
**{schema['table_name']}**
- Propósito: {schema['purpose']}
- Columnas: {len(schema['columns'])}
- Estructura: `{', '.join([col['name'] for col in schema['columns'][:5]])}`

"""
        
        return formatted
    
    def _format_available_tools(self) -> str:
        """Herramientas y comandos disponibles"""
        config = self.master_knowledge.get("code_knowledge", {}).get("configuration", {})
        
        if "project_instructions" in config:
            # Extraer comandos del CLAUDE.md
            instructions = config["project_instructions"]
            
            # Buscar secciones de comandos
            commands_section = ""
            if "## Common Commands" in instructions:
                start = instructions.find("## Common Commands")
                end = instructions.find("##", start + 1)
                commands_section = instructions[start:end] if end != -1 else instructions[start:start+1000]
            
            return f"### 📋 Comandos Disponibles\n\n```bash\n{commands_section}\n```"
        
        return "**Comandos disponibles en CLAUDE.md**"
    
    def _format_advanced_metrics(self) -> str:
        """Métricas avanzadas de performance"""
        metrics = self.master_knowledge.get("current_data", {}).get("performance_metrics", {})
        
        if not metrics:
            return "**Métricas no disponibles**"
        
        return f"""
### 📊 Métricas de Performance

```
🎯 Win Rate: {metrics.get('win_rate_percent', 0):.1f}%
⚖️ Profit Factor: {metrics.get('profit_factor', 0):.2f}
📉 Max Drawdown: ${metrics.get('max_drawdown', 0):,.2f}
📈 Posiciones Ganadoras: {metrics.get('winning_positions', 0)}
📉 Posiciones Perdedoras: {metrics.get('losing_positions', 0)}
📊 Total Posiciones: {metrics.get('total_positions', 0)}
```
"""
    
    def save_knowledge_cache(self):
        """Guarda cache de conocimiento"""
        with open(self.knowledge_cache_path, 'w', encoding='utf-8') as f:
            json.dump(self.master_knowledge, f, indent=2, ensure_ascii=False, default=str)
        
        # Actualizar timestamp
        with open(self.last_update_file, 'w') as f:
            f.write(datetime.now().isoformat())
    
    def load_cached_knowledge(self) -> dict:
        """Carga conocimiento desde cache"""
        try:
            with open(self.knowledge_cache_path, 'r', encoding='utf-8') as f:
                self.master_knowledge = json.load(f)
            return self.master_knowledge
        except:
            return self.build_complete_knowledge_base(force_update=True)
    
    def run_interactive_system(self):
        """Sistema interactivo maestro"""
        
        print("SISTEMA MAESTRO OLLAMA - CONOCIMIENTO COMPLETO")
        print("=" * 60)
        print("Genera contexto comprehensivo como Claude Code")
        print()
        
        # Construir conocimiento si es necesario
        self.build_complete_knowledge_base()
        
        print("\nTIPOS DE ANALISIS DISPONIBLES:")
        options = {
            "1": ("complete", "ANALISIS COMPLETO (Recomendado)"),
            "2": ("trading", "Enfoque en Trading Performance"),
            "3": ("code", "Revision Tecnica del Codigo"),
            "4": ("excel", "Analisis de Reportes Excel"),
            "5": ("strategy", "Optimizacion de Estrategias")
        }
        
        for key, (_, desc) in options.items():
            print(f"{key}. {desc}")
        
        try:
            choice = input("\nElige tipo de análisis (1-5): ").strip()
            
            if choice in options:
                analysis_type, description = options[choice]
                print(f"\nGenerando {description}...")
                
                # Generar contexto
                context = self.generate_smart_context_for_ollama(analysis_type)
                
                # Guardar archivo
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"ollama_master_context_{analysis_type}_{timestamp}.txt"
                output_path = self.project_root / filename
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(context)
                
                # Copiar al clipboard
                try:
                    import pyperclip
                    pyperclip.copy(context)
                    print("✅ Contexto copiado al clipboard!")
                except ImportError:
                    print("⚠️ Para auto-copy: pip install pyperclip")
                
                print("\n" + "=" * 60)
                print("CONTEXTO MAESTRO GENERADO EXITOSAMENTE")
                print("=" * 60)
                print(f"📁 Archivo: {filename}")
                print(f"📏 Tamaño: {len(context):,} caracteres")
                print(f"🧠 Conocimiento: {len(self.master_knowledge)} secciones")
                print()
                print("🎯 SIGUIENTE PASO:")
                print("   1. Abre Ollama UI (http://localhost:11434)")
                print("   2. Pega el contexto (Ctrl+V)")
                print("   3. ¡Ollama tendrá TODO el conocimiento de tu código!")
                print()
                print("💡 Ahora puedes preguntar a Ollama:")
                print("   - Analiza el performance de mis estrategias")
                print("   - Qué archivos Excel tienen datos más relevantes") 
                print("   - Sugiere optimizaciones específicas del código")
                print("   - Identifica problemas en mis posiciones SHORT")
                
            else:
                print("❌ Opción inválida")
                
        except KeyboardInterrupt:
            print("\n👋 Cancelado por usuario")
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    master_system = OllamaMasterSystem()
    master_system.run_interactive_system()