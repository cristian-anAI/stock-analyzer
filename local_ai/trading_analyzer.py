"""
Comprehensive Trading System Analyzer using Ollama
Analyzes buy signals, code structure, Excel reports, and strategies
"""

import ollama
import pandas as pd
import sqlite3
import json
import os
from pathlib import Path
from datetime import datetime, timedelta
import glob

class TradingSystemAnalyzer:
    def __init__(self, model="llama3.1:8b"):
        self.model = model
        self.project_root = Path(__file__).parent.parent
        self.reports_dir = self.project_root / "reports"
        self.db_path = self.project_root / "trading.db"
        
    def get_system_prompt(self):
        """System prompt especializado para análisis de trading"""
        return """
        Eres un EXPERTO TRADER CUANTITATIVO y ANALISTA DE SISTEMAS DE TRADING con 20+ años de experiencia en:

        🎯 ESPECIALIDADES:
        - Análisis técnico avanzado (RSI, MACD, Bollinger, Fibonacci)
        - Risk Management y Money Management
        - Backtesting y optimización de estrategias
        - Market microstructure y order flow
        - Crypto vs Stock markets diferencias
        - Sistemas automatizados de trading
        - Python/FastAPI para trading systems

        📊 TU MISIÓN:
        Analizar PROFUNDAMENTE este sistema de trading y dar insights ACCIONABLES, específicos y críticos.

        ⚡ FORMATO DE RESPUESTA:
        Siempre estructura tus respuestas en:
        1. 🔍 ANÁLISIS CRÍTICO (lo que está mal/riesgoso)
        2. ✅ FORTALEZAS (lo que funciona bien)
        3. 🚨 PUNTOS CRÍTICOS (require atención inmediata)
        4. 💡 RECOMENDACIONES ESPECÍFICAS (pasos concretos)
        5. 📈 OPTIMIZACIONES (mejoras de rendimiento)

        Sé DIRECTO, ESPECÍFICO y ACTIONABLE. No uses jerga innecesaria.
        """

    def analyze_buy_signals(self):
        """Analiza las señales de compra del sistema"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Obtener últimas posiciones y transacciones
            recent_positions = pd.read_sql_query("""
                SELECT * FROM positions 
                WHERE created_at >= datetime('now', '-30 days')
                ORDER BY created_at DESC
            """, conn)
            
            recent_transactions = pd.read_sql_query("""
                SELECT * FROM transactions 
                WHERE timestamp >= datetime('now', '-30 days')
                ORDER BY timestamp DESC
            """, conn)
            
            symbols_data = pd.read_sql_query("""
                SELECT symbol, rsi, macd_signal, bb_position, last_price, volume_ratio
                FROM symbols 
                WHERE last_updated >= datetime('now', '-1 day')
            """, conn)
            
            conn.close()
            
            analysis_data = {
                "recent_positions": recent_positions.to_dict('records')[:10],
                "recent_transactions": recent_transactions.to_dict('records')[:10],
                "current_signals": symbols_data.to_dict('records')[:20],
                "position_types": recent_positions['position_type'].value_counts().to_dict(),
                "avg_hold_time": "N/A",  # Calcular si es necesario
                "success_rate": "N/A"   # Calcular si es necesario
            }
            
            prompt = f"""
            ANALIZA LAS SEÑALES DE COMPRA/VENTA de este sistema de trading:

            📊 POSICIONES RECIENTES (últimos 30 días):
            {json.dumps(analysis_data["recent_positions"], indent=2, default=str)}

            💰 TRANSACCIONES RECIENTES:
            {json.dumps(analysis_data["recent_transactions"], indent=2, default=str)}

            📈 SEÑALES ACTUALES:
            {json.dumps(analysis_data["current_signals"], indent=2, default=str)}

            📊 DISTRIBUCIÓN DE POSICIONES:
            {analysis_data["position_types"]}

            🎯 ANALIZA ESPECÍFICAMENTE:
            1. Calidad de las señales de entrada (RSI, MACD, Bollinger)
            2. Timing de las operaciones
            3. Distribución LONG vs SHORT vs CRYPTO
            4. Patrones de éxito/fracaso
            5. Riesgos en las señales actuales
            """
            
            response = ollama.chat(model=self.model, messages=[
                {'role': 'system', 'content': self.get_system_prompt()},
                {'role': 'user', 'content': prompt}
            ])
            
            return response['message']['content']
            
        except Exception as e:
            return f"[ERROR] Error analizando senales: {str(e)}"

    def analyze_code_structure(self):
        """Analiza la estructura del código del sistema"""
        key_files = [
            "src/api/services/autotrader_service.py",
            "src/api/services/advanced_scoring_service.py",
            "src/api/services/portfolio_manager.py",
            "src/api/services/risk_management_service.py",
            "src/traders/strategies/base_strategy.py"
        ]
        
        code_analysis = {}
        for file_path in key_files:
            full_path = self.project_root / file_path
            if full_path.exists():
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    code_analysis[file_path] = {
                        "lines": len(content.split('\n')),
                        "functions": content.count('def '),
                        "classes": content.count('class '),
                        "sample": content[:500] + "..." if len(content) > 500 else content
                    }
        
        prompt = f"""
        ANALIZA LA ARQUITECTURA Y ESTRUCTURA DEL CÓDIGO:

        📁 ARCHIVOS CLAVE ANALIZADOS:
        {json.dumps(code_analysis, indent=2)}

        🎯 EVALÚA ESPECÍFICAMENTE:
        1. Arquitectura del sistema (FastAPI, services, traders)
        2. Separación de responsabilidades
        3. Manejo de errores y excepciones
        4. Escalabilidad del código
        5. Patrones de diseño utilizados
        6. Posibles cuellos de botella
        7. Calidad del código (maintainability)
        8. Testing coverage (si existe)

        🚨 IDENTIFICA:
        - Code smells
        - Posibles bugs o vulnerabilidades
        - Áreas que necesitan refactoring
        - Mejoras de rendimiento
        """
        
        try:
            response = ollama.chat(model=self.model, messages=[
                {'role': 'system', 'content': self.get_system_prompt()},
                {'role': 'user', 'content': prompt}
            ])
            return response['message']['content']
        except Exception as e:
            return f"[ERROR] Error analizando codigo: {str(e)}"

    def analyze_excel_reports(self):
        """Analiza los reportes Excel más recientes"""
        try:
            excel_files = list(self.reports_dir.glob("**/*.xlsx"))
            excel_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            if not excel_files:
                return "[ERROR] No se encontraron reportes Excel"
            
            # Analizar los 3 reportes más recientes
            reports_data = {}
            for i, excel_file in enumerate(excel_files[:3]):
                try:
                    df = pd.read_excel(excel_file)
                    reports_data[excel_file.name] = {
                        "file_date": datetime.fromtimestamp(excel_file.stat().st_mtime).isoformat(),
                        "rows": len(df),
                        "columns": list(df.columns),
                        "sample_data": df.head(3).to_dict('records') if not df.empty else [],
                        "summary": df.describe().to_dict() if not df.empty and df.select_dtypes(include='number').shape[1] > 0 else {}
                    }
                except Exception as e:
                    reports_data[excel_file.name] = {"error": str(e)}
            
            prompt = f"""
            ANALIZA LOS REPORTES EXCEL DEL SISTEMA DE TRADING:

            📊 REPORTES ANALIZADOS (3 más recientes):
            {json.dumps(reports_data, indent=2, default=str)}

            🎯 ANALIZA ESPECÍFICAMENTE:
            1. Performance del portfolio (ROI, Sharpe ratio, drawdown)
            2. Distribución de ganancias/pérdidas
            3. Frecuencia de trading
            4. Gestión del riesgo (stop loss, take profit)
            5. Comparación entre periodos
            6. Tendencias y patrones en los datos
            7. Métricas clave faltantes
            8. Calidad de los datos (inconsistencias)

            🚨 IDENTIFICA:
            - Signos de sobreoptimización
            - Periodos de drawdown excesivo
            - Patrones de riesgo elevado
            - Oportunidades perdidas
            """
            
            response = ollama.chat(model=self.model, messages=[
                {'role': 'system', 'content': self.get_system_prompt()},
                {'role': 'user', 'content': prompt}
            ])
            
            return response['message']['content']
            
        except Exception as e:
            return f"[ERROR] Error analizando reportes Excel: {str(e)}"

    def analyze_strategies_separate(self):
        """Analiza estrategias de stocks y crypto por separado"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Posiciones por tipo
            stock_positions = pd.read_sql_query("""
                SELECT * FROM positions 
                WHERE position_type IN ('LONG', 'SHORT')
                AND created_at >= datetime('now', '-60 days')
            """, conn)
            
            crypto_positions = pd.read_sql_query("""
                SELECT * FROM positions 
                WHERE position_type IN ('CRYPTO_LONG', 'CRYPTO_SHORT')
                AND created_at >= datetime('now', '-60 days')
            """, conn)
            
            # Símbolos por tipo
            stock_symbols = pd.read_sql_query("""
                SELECT * FROM symbols 
                WHERE symbol NOT LIKE '%-USD'
                AND last_updated >= datetime('now', '-2 days')
            """, conn)
            
            crypto_symbols = pd.read_sql_query("""
                SELECT * FROM symbols 
                WHERE symbol LIKE '%-USD'
                AND last_updated >= datetime('now', '-2 days')
            """, conn)
            
            conn.close()
            
            analysis_data = {
                "stocks": {
                    "positions": stock_positions.to_dict('records'),
                    "symbols": stock_symbols.to_dict('records'),
                    "total_capital": 10000,  # Según CLAUDE.md
                    "position_count": len(stock_positions),
                    "avg_rsi": stock_symbols['rsi'].mean() if not stock_symbols.empty else 0
                },
                "crypto": {
                    "positions": crypto_positions.to_dict('records'),
                    "symbols": crypto_symbols.to_dict('records'),
                    "total_capital": 50000,  # Según CLAUDE.md
                    "position_count": len(crypto_positions),
                    "avg_rsi": crypto_symbols['rsi'].mean() if not crypto_symbols.empty else 0
                }
            }
            
            prompt = f"""
            ANALIZA LAS ESTRATEGIAS DE STOCKS vs CRYPTO POR SEPARADO:

            📈 STOCKS (Capital asignado: $10,000):
            Posiciones activas: {analysis_data["stocks"]["position_count"]}
            RSI promedio: {analysis_data["stocks"]["avg_rsi"]:.2f}
            Posiciones recientes:
            {json.dumps(analysis_data["stocks"]["positions"][-10:], indent=2, default=str)}
            
            Símbolos monitoreados:
            {json.dumps(analysis_data["stocks"]["symbols"][-10:], indent=2, default=str)}

            🪙 CRYPTO (Capital asignado: $50,000):
            Posiciones activas: {analysis_data["crypto"]["position_count"]}
            RSI promedio: {analysis_data["crypto"]["avg_rsi"]:.2f}
            Posiciones recientes:
            {json.dumps(analysis_data["crypto"]["positions"][-10:], indent=2, default=str)}
            
            Símbolos monitoreados:
            {json.dumps(analysis_data["crypto"]["symbols"][-10:], indent=2, default=str)}

            🎯 COMPARA Y ANALIZA:
            1. Rendimiento relativo (stocks vs crypto)
            2. Volatilidad y gestión del riesgo
            3. Frecuencia de operaciones
            4. Capitalización y diversificación
            5. Indicadores técnicos efectividad
            6. Market timing differences
            7. Liquidity management
            8. Correlation between markets

            🚨 IDENTIFICA ESPECÍFICAMENTE:
            - ¿Qué estrategia funciona mejor?
            - ¿Asignación de capital óptima?
            - ¿Riesgos específicos por mercado?
            - ¿Oportunidades de arbitraje?
            """
            
            response = ollama.chat(model=self.model, messages=[
                {'role': 'system', 'content': self.get_system_prompt()},
                {'role': 'user', 'content': prompt}
            ])
            
            return response['message']['content']
            
        except Exception as e:
            return f"[ERROR] Error analizando estrategias: {str(e)}"

    def get_critical_recommendations(self):
        """Genera recomendaciones críticas basadas en el análisis completo"""
        prompt = """
        🚨 GENERA RECOMENDACIONES CRÍTICAS Y ACCIONABLES:

        Basándote en tu experiencia como trader cuantitativo, dame:

        1. 🔥 TOP 3 PROBLEMAS CRÍTICOS que debe arreglar YA
        2. 💡 TOP 5 OPTIMIZACIONES de mayor impacto
        3. 🛡️ GESTIÓN DE RIESGOS mejoras urgentes
        4. 📊 MÉTRICAS adicionales que debería monitorear
        5. 🤖 AUTOMATIZACIÓN opportunities
        6. 📚 RESEARCH áreas para profundizar

        Cada recomendación debe ser:
        - Específica (no genérica)
        - Actionable (pasos concretos)
        - Priorizada (orden de importancia)
        - Con timeframe estimado

        Formato: 
        ## 🔥 CRÍTICO
        1. [Problema] - [Solución específica] - [Timeframe]

        ## 💡 OPTIMIZACIONES
        1. [Área] - [Mejora específica] - [Impacto esperado]
        """
        
        try:
            response = ollama.chat(model=self.model, messages=[
                {'role': 'system', 'content': self.get_system_prompt()},
                {'role': 'user', 'content': prompt}
            ])
            return response['message']['content']
        except Exception as e:
            return f"[ERROR] Error generando recomendaciones: {str(e)}"

    def run_complete_analysis(self):
        """Ejecuta análisis completo del sistema"""
        print("INICIANDO ANALISIS COMPLETO DEL SISTEMA DE TRADING...")
        print("=" * 80)
        
        analyses = {
            "[1] ANALISIS DE SENALES DE COMPRA": self.analyze_buy_signals,
            "[2] ANALISIS DE ESTRUCTURA DE CODIGO": self.analyze_code_structure,
            "[3] ANALISIS DE REPORTES EXCEL": self.analyze_excel_reports,
            "[4] ANALISIS STOCKS vs CRYPTO": self.analyze_strategies_separate,
            "[5] RECOMENDACIONES CRITICAS": self.get_critical_recommendations
        }
        
        results = {}
        for title, analysis_func in analyses.items():
            print(f"\n{title}")
            print("-" * 60)
            try:
                result = analysis_func()
                results[title] = result
                print(result)
                print("\n" + "=" * 80)
            except Exception as e:
                error_msg = f"[ERROR] Error en {title}: {str(e)}"
                results[title] = error_msg
                print(error_msg)
        
        # Guardar resultados
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = self.project_root / f"trading_analysis_{timestamp}.txt"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("ANALISIS COMPLETO DEL SISTEMA DE TRADING\n")
            f.write("=" * 80 + "\n")
            f.write(f"Fecha: {datetime.now().isoformat()}\n")
            f.write(f"Modelo: {self.model}\n\n")
            
            for title, result in results.items():
                f.write(f"{title}\n")
                f.write("-" * 60 + "\n")
                f.write(result + "\n\n")
                f.write("=" * 80 + "\n\n")
        
        print(f"\n[DONE] Analisis completo guardado en: {output_file}")
        return results

if __name__ == "__main__":
    analyzer = TradingSystemAnalyzer()
    analyzer.run_complete_analysis()