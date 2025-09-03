"""
Generador de contexto completo para Ollama - Equivalente a Claude Code
Crea contexto comprehensive con TODO el conocimiento del código
"""

import json
from pathlib import Path
from datetime import datetime
import sqlite3
import pandas as pd
from code_knowledge_extractor import CodeKnowledgeExtractor

class OllamaContextGenerator:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.extractor = CodeKnowledgeExtractor()
        
    def generate_comprehensive_context(self, focus_area: str = "complete") -> str:
        """Genera contexto comprehensivo como Claude Code"""
        
        # Extraer conocimiento completo
        print("🔍 Extrayendo conocimiento completo...")
        knowledge_base = self.extractor.generate_complete_knowledge_base()
        
        # Obtener datos actuales
        current_data = self._get_current_trading_data()
        
        # Generar contexto según el área de enfoque
        context_sections = {
            "complete": self._generate_complete_context,
            "trading": self._generate_trading_focused_context,
            "technical": self._generate_technical_context,
            "performance": self._generate_performance_context
        }
        
        generator = context_sections.get(focus_area, self._generate_complete_context)
        context = generator(knowledge_base, current_data)
        
        return context
    
    def _generate_complete_context(self, knowledge_base: dict, current_data: dict) -> str:
        """Genera contexto completo como Claude Code"""
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        context = f"""
# SISTEMA COMPLETO DE TRADING - CONTEXTO PARA OLLAMA
**Timestamp:** {timestamp}

Eres un EXPERTO en sistemas de trading automatizados. Tienes acceso completo a este sistema avanzado de análisis y trading. Analiza TODO con el mismo nivel de detalle que Claude Code.

## 📊 ESTADO ACTUAL DEL SISTEMA

### Posiciones Activas:
{self._format_positions(current_data.get('positions', []))}

### Estado del Portfolio:
{self._format_portfolio(current_data.get('portfolio', {}))}

## 🎯 ESTRATEGIAS DE TRADING IMPLEMENTADAS

{self._format_strategies(knowledge_base.get('strategies', []))}

## 🔧 SERVICIOS Y ARQUITECTURA

{self._format_services(knowledge_base.get('services', []))}

## 🗄️ ESTRUCTURA DE BASE DE DATOS

{self._format_database_schema(knowledge_base.get('database_schema', []))}

## 🌐 API ENDPOINTS DISPONIBLES

{self._format_api_endpoints(knowledge_base.get('api_endpoints', []))}

## 📈 REPORTES Y ANÁLISIS RECIENTES

{self._format_recent_reports(knowledge_base.get('recent_reports', []))}

## 📁 ESTRUCTURA DEL PROYECTO

{self._format_file_structure(knowledge_base.get('file_structure', {}))}

## ⚙️ CONFIGURACIÓN DEL SISTEMA

{self._format_system_config(knowledge_base.get('configuration', {}))}

---

**INSTRUCCIONES PARA OLLAMA:**
- Analiza TODA esta información como lo haría un experto trader cuantitativo
- Puedes referenciar cualquier archivo, servicio, o función específica
- Usa datos reales del sistema para tus análisis
- Proporciona recomendaciones concretas y accionables
- Identifica patrones, problemas, y oportunidades de mejora
- Sugiere optimizaciones específicas del código cuando sea relevante

**¿Qué necesitas analizar o optimizar en el sistema?**
        """
        
        return context.strip()
    
    def _get_current_trading_data(self) -> dict:
        """Obtiene datos actuales del sistema de trading"""
        data = {"positions": [], "portfolio": {}, "recent_transactions": []}
        
        try:
            db_path = self.project_root / "trading.db"
            if not db_path.exists():
                return data
            
            conn = sqlite3.connect(db_path)
            
            # Posiciones actuales
            positions = pd.read_sql_query("""
                SELECT symbol, name, pnl, pnl_percent, entry_price, current_price, 
                       value, asset_type, position_side, entry_date, strategy_used
                FROM positions 
                ORDER BY abs(pnl) DESC
            """, conn)
            data["positions"] = positions.to_dict('records') if not positions.empty else []
            
            # Estado del portfolio
            portfolio = pd.read_sql_query("""
                SELECT * FROM portfolio_state 
                ORDER BY created_at DESC LIMIT 1
            """, conn)
            data["portfolio"] = portfolio.to_dict('records')[0] if not portfolio.empty else {}
            
            # Transacciones recientes
            transactions = pd.read_sql_query("""
                SELECT * FROM transactions 
                ORDER BY created_at DESC LIMIT 20
            """, conn)
            data["recent_transactions"] = transactions.to_dict('records') if not transactions.empty else []
            
            conn.close()
            
        except Exception as e:
            print(f"Error getting trading data: {e}")
        
        return data
    
    def _format_positions(self, positions: list) -> str:
        """Formatea información de posiciones"""
        if not positions:
            return "**No hay posiciones activas**"
        
        formatted = "```\n"
        for pos in positions:
            pnl_sign = "📈" if pos.get('pnl', 0) > 0 else "📉"
            formatted += f"{pnl_sign} {pos.get('symbol', 'N/A')} ({pos.get('position_side', 'N/A')})\n"
            formatted += f"   PnL: ${pos.get('pnl', 0):.2f} ({pos.get('pnl_percent', 0):.2f}%)\n"
            formatted += f"   Entrada: ${pos.get('entry_price', 0):.2f} | Actual: ${pos.get('current_price', 0):.2f}\n"
            formatted += f"   Estrategia: {pos.get('strategy_used', 'N/A')}\n\n"
        
        formatted += "```"
        return formatted
    
    def _format_portfolio(self, portfolio: dict) -> str:
        """Formatea estado del portfolio"""
        if not portfolio:
            return "**Estado del portfolio no disponible**"
        
        return f"""```
💰 Capital Total: ${portfolio.get('total_value', 0):,.2f}
📊 PnL Total: ${portfolio.get('total_pnl', 0):,.2f}
📈 Rendimiento: {portfolio.get('total_return_percent', 0):.2f}%
🏦 Cash Disponible: ${portfolio.get('cash', 0):,.2f}
📍 Posiciones Activas: {portfolio.get('active_positions', 0)}
```"""
    
    def _format_strategies(self, strategies: list) -> str:
        """Formatea información de estrategias"""
        if not strategies:
            return "**No se encontraron estrategias**"
        
        formatted = ""
        for strategy in strategies:
            formatted += f"""
### 📋 {strategy['name']}
**Archivo:** `{strategy['file_path']}`
**Descripción:** {strategy['description'][:200]}...

**Métodos principales:**
{', '.join(strategy['methods'][:5])}

**Condiciones de entrada:** {len(strategy['entry_conditions'])} definidas
**Condiciones de salida:** {len(strategy['exit_conditions'])} definidas
**Risk Management:** {len(strategy['risk_management'])} parámetros

---
"""
        return formatted
    
    def _format_services(self, services: list) -> str:
        """Formatea información de servicios"""
        if not services:
            return "**No se encontraron servicios**"
        
        formatted = ""
        for service in services:
            formatted += f"""
### 🔧 {service['name']}
**Archivo:** `{service['file_path']}`
**Métodos clave:** {', '.join(service['key_methods'][:5])}
**Dependencias:** {len(service['dependencies'])} módulos

"""
        return formatted
    
    def _format_database_schema(self, schemas: list) -> str:
        """Formatea esquema de base de datos"""
        if not schemas:
            return "**Esquema de BD no disponible**"
        
        formatted = ""
        for schema in schemas:
            formatted += f"""
### 🗄️ {schema['table_name']}
**Propósito:** {schema['purpose']}
**Columnas:** {len(schema['columns'])} campos
```
{', '.join([col['name'] + ' (' + col['type'] + ')' for col in schema['columns'][:5]])}
```

"""
        return formatted
    
    def _format_api_endpoints(self, endpoints: list) -> str:
        """Formatea endpoints de la API"""
        if not endpoints:
            return "**No se encontraron endpoints**"
        
        formatted = "```\n"
        grouped = {}
        for endpoint in endpoints:
            method = endpoint['method']
            if method not in grouped:
                grouped[method] = []
            grouped[method].append(endpoint['path'])
        
        for method, paths in grouped.items():
            formatted += f"{method}:\n"
            for path in paths[:10]:  # Limitar a 10 por método
                formatted += f"  {path}\n"
            formatted += "\n"
        
        formatted += "```"
        return formatted
    
    def _format_recent_reports(self, reports: list) -> str:
        """Formatea reportes recientes"""
        if not reports:
            return "**No se encontraron reportes recientes**"
        
        formatted = ""
        for report in reports[:5]:  # Solo los 5 más recientes
            formatted += f"""
### 📊 {report['filename']}
**Hojas:** {', '.join(report['sheets'])}
**Última modificación:** {datetime.fromtimestamp(report['modified']).strftime('%Y-%m-%d %H:%M')}

"""
        return formatted
    
    def _format_file_structure(self, structure: dict) -> str:
        """Formatea estructura de archivos"""
        if not structure:
            return "**Estructura no disponible**"
        
        formatted = "```\n"
        for path, content in structure.items():
            formatted += f"📁 {path}/\n"
            for file in content.get('files', [])[:5]:
                formatted += f"   📄 {file}\n"
            for subdir in content.get('subdirs', {}).keys():
                formatted += f"   📁 {subdir}/\n"
            formatted += "\n"
        
        formatted += "```"
        return formatted
    
    def _format_system_config(self, config: dict) -> str:
        """Formatea configuración del sistema"""
        formatted = ""
        
        if 'dependencies' in config:
            formatted += f"**Dependencias:** {len(config['dependencies'])} paquetes instalados\n\n"
        
        if 'project_instructions' in config:
            instructions = config['project_instructions'][:500]
            formatted += f"**Instrucciones del proyecto:**\n```\n{instructions}...\n```\n"
        
        return formatted
    
    def generate_and_copy_context(self, focus_area: str = "complete"):
        """Genera contexto y lo copia al clipboard"""
        print(f"🚀 Generando contexto {focus_area}...")
        context = self.generate_comprehensive_context(focus_area)
        
        # Intentar copiar al clipboard
        try:
            import pyperclip
            pyperclip.copy(context)
            print("✅ Contexto copiado al clipboard!")
            print("📋 Pega en Ollama UI con Ctrl+V")
        except ImportError:
            print("⚠️ pyperclip no disponible - instala con: pip install pyperclip")
        
        # Guardar archivo
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ollama_complete_context_{focus_area}_{timestamp}.txt"
        
        output_path = self.project_root / filename
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(context)
        
        print(f"💾 Contexto guardado en: {filename}")
        print(f"📏 Tamaño del contexto: {len(context):,} caracteres")
        
        return context, output_path

def interactive_context_generator():
    """Interfaz interactiva para generar contexto"""
    print("🤖 GENERADOR DE CONTEXTO COMPLETO PARA OLLAMA")
    print("=" * 50)
    print("Genera contexto comprehensive como Claude Code\n")
    
    options = {
        "1": ("complete", "🎯 Contexto COMPLETO (recomendado)"),
        "2": ("trading", "📊 Enfoque en Trading"),
        "3": ("technical", "🔧 Enfoque Técnico"), 
        "4": ("performance", "📈 Enfoque en Performance")
    }
    
    for key, (_, desc) in options.items():
        print(f"{key}. {desc}")
    
    try:
        choice = input("\nElige tipo de contexto (1-4): ").strip()
        
        if choice in options:
            focus_area, description = options[choice]
            print(f"\n🔄 {description}")
            
            generator = OllamaContextGenerator()
            context, output_file = generator.generate_and_copy_context(focus_area)
            
            print("\n" + "=" * 60)
            print("✅ CONTEXTO GENERADO EXITOSAMENTE")
            print("=" * 60)
            print(f"📊 Información extraída:")
            print(f"   - Estrategias de trading")
            print(f"   - Servicios y arquitectura")
            print(f"   - Esquema de base de datos")
            print(f"   - API endpoints")
            print(f"   - Reportes Excel recientes")
            print(f"   - Posiciones y portfolio actual")
            print(f"\n🎯 SIGUIENTE PASO:")
            print(f"   1. Abre Ollama UI (http://localhost:11434)")
            print(f"   2. Pega el contexto (Ctrl+V)")
            print(f"   3. Ollama tendrá el mismo conocimiento que Claude Code!")
            
        else:
            print("❌ Opción inválida")
            
    except KeyboardInterrupt:
        print("\n👋 Cancelado por usuario")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    interactive_context_generator()