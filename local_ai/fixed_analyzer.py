"""
Trading System Analyzer - FIXED para estructura DB real
"""

import ollama
import pandas as pd
import sqlite3
import json
import os
from pathlib import Path
from datetime import datetime, timedelta
import glob

class FixedTradingAnalyzer:
    def __init__(self, model="llama3.1:8b"):
        self.model = model
        self.project_root = Path(__file__).parent.parent
        self.reports_dir = self.project_root / "reports"
        self.db_path = self.project_root / "trading.db"
        
    def get_system_prompt(self):
        """System prompt especializado para análisis de trading"""
        return """
        Eres un EXPERTO TRADER CUANTITATIVO y ANALISTA DE SISTEMAS DE TRADING con 20+ años de experiencia.

        ESPECIALIDADES:
        - Análisis técnico avanzado 
        - Risk Management y Money Management
        - Sistemas automatizados de trading
        - Python/FastAPI para trading systems
        - Crypto vs Stock markets

        FORMATO DE RESPUESTA:
        1. ANÁLISIS CRÍTICO (problemas/riesgos)
        2. FORTALEZAS (lo que funciona)
        3. PUNTOS CRÍTICOS (atención inmediata)
        4. RECOMENDACIONES ESPECÍFICAS (pasos concretos)
        5. OPTIMIZACIONES (mejoras rendimiento)

        Sé DIRECTO, ESPECÍFICO y ACTIONABLE.
        """

    def analyze_current_positions(self):
        """Analiza las posiciones actuales"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Posiciones actuales
            positions = pd.read_sql_query("""
                SELECT symbol, name, type, quantity, entry_price, current_price, 
                       value, pnl, pnl_percent, asset_type, position_side,
                       created_at, strategy_used, entry_score
                FROM positions 
                ORDER BY created_at DESC
            """, conn)
            
            # Stocks activos
            stocks = pd.read_sql_query("""
                SELECT symbol, name, current_price, score, change_percent, 
                       volume, market_cap, sector, updated_at
                FROM stocks 
                ORDER BY score DESC 
                LIMIT 20
            """, conn)
            
            # Cryptos activos
            cryptos = pd.read_sql_query("""
                SELECT symbol, name, current_price, score, change_percent, 
                       volume, market_cap, updated_at
                FROM cryptos 
                ORDER BY score DESC 
                LIMIT 10
            """, conn)
            
            # Estado del portfolio
            portfolio_state = pd.read_sql_query("""
                SELECT * FROM portfolio_state 
                ORDER BY created_at DESC 
                LIMIT 1
            """, conn)
            
            conn.close()
            
            analysis_data = {
                "positions": positions.to_dict('records'),
                "top_stocks": stocks.to_dict('records'),
                "top_cryptos": cryptos.to_dict('records'), 
                "portfolio_state": portfolio_state.to_dict('records'),
                "position_count": len(positions),
                "total_pnl": positions['pnl'].sum() if not positions.empty else 0,
                "avg_pnl_percent": positions['pnl_percent'].mean() if not positions.empty else 0
            }
            
            prompt = f"""
            ANALIZA EL ESTADO ACTUAL DEL SISTEMA DE TRADING:

            POSICIONES ACTUALES ({len(positions)} activas):
            {json.dumps(analysis_data["positions"], indent=2, default=str)}

            TOP STOCKS (por score):
            {json.dumps(analysis_data["top_stocks"], indent=2, default=str)}

            TOP CRYPTOS (por score):
            {json.dumps(analysis_data["top_cryptos"], indent=2, default=str)}

            ESTADO DEL PORTFOLIO:
            {json.dumps(analysis_data["portfolio_state"], indent=2, default=str)}

            MÉTRICAS CLAVE:
            - Total posiciones: {analysis_data["position_count"]}
            - PnL total: ${analysis_data["total_pnl"]:.2f}
            - PnL promedio: {analysis_data["avg_pnl_percent"]:.2f}%

            ANALIZA ESPECÍFICAMENTE:
            1. Calidad de las posiciones actuales
            2. Distribución de riesgo (stocks vs crypto)
            3. Performance de las estrategias
            4. Oportunidades en el watchlist
            5. Gestión del capital
            """
            
            response = ollama.chat(model=self.model, messages=[
                {'role': 'system', 'content': self.get_system_prompt()},
                {'role': 'user', 'content': prompt}
            ])
            
            return response['message']['content']
            
        except Exception as e:
            return f"[ERROR] Error analizando posiciones: {str(e)}"

    def analyze_portfolio_performance(self):
        """Analiza performance del portfolio"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Configuración portfolio
            portfolio_config = pd.read_sql_query("""
                SELECT type, initial_capital, current_capital, available_cash,
                       invested_amount, total_pnl, win_rate, total_trades
                FROM portfolio_config
            """, conn)
            
            # Historial portfolio
            portfolio_history = pd.read_sql_query("""
                SELECT * FROM portfolio_state 
                ORDER BY created_at ASC
            """, conn)
            
            # Performance trades (si existe data)
            try:
                trade_performance = pd.read_sql_query("""
                    SELECT asset_type, strategy_used, realized_pnl_percent,
                           days_held, exit_reason
                    FROM trade_performance 
                    ORDER BY entry_date DESC
                    LIMIT 50
                """, conn)
            except:
                trade_performance = pd.DataFrame()
            
            conn.close()
            
            analysis_data = {
                "portfolio_config": portfolio_config.to_dict('records'),
                "portfolio_history": portfolio_history.to_dict('records'),
                "trade_performance": trade_performance.to_dict('records') if not trade_performance.empty else [],
                "capital_allocation": {
                    "stocks": portfolio_config[portfolio_config['type'] == 'stocks']['current_capital'].iloc[0] if not portfolio_config.empty else 0,
                    "crypto": portfolio_config[portfolio_config['type'] == 'crypto']['current_capital'].iloc[0] if len(portfolio_config) > 1 else 0
                }
            }
            
            prompt = f"""
            ANALIZA LA PERFORMANCE DEL PORTFOLIO:

            CONFIGURACIÓN ACTUAL:
            {json.dumps(analysis_data["portfolio_config"], indent=2, default=str)}

            HISTORIAL DEL PORTFOLIO:
            {json.dumps(analysis_data["portfolio_history"], indent=2, default=str)}

            PERFORMANCE DE TRADES:
            {json.dumps(analysis_data["trade_performance"][:10], indent=2, default=str)}

            ASIGNACIÓN DE CAPITAL:
            {json.dumps(analysis_data["capital_allocation"], indent=2)}

            EVALÚA ESPECÍFICAMENTE:
            1. Eficiencia en el uso del capital
            2. Performance histórica vs expectativas
            3. Diversificación stocks vs crypto
            4. Win rate y profit factor
            5. Gestión del riesgo
            6. Oportunidades de optimización
            """
            
            response = ollama.chat(model=self.model, messages=[
                {'role': 'system', 'content': self.get_system_prompt()},
                {'role': 'user', 'content': prompt}
            ])
            
            return response['message']['content']
            
        except Exception as e:
            return f"[ERROR] Error analizando performance: {str(e)}"

    def analyze_strategy_effectiveness(self):
        """Analiza efectividad de las estrategias"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Configuración estrategias
            strategy_config = pd.read_sql_query("""
                SELECT asset_type, strategy_name, config_key, config_value, is_active
                FROM strategy_config
                WHERE is_active = 1
            """, conn)
            
            # Posiciones por estrategia
            positions_by_strategy = pd.read_sql_query("""
                SELECT strategy_used, asset_type, COUNT(*) as position_count,
                       AVG(pnl_percent) as avg_pnl_percent,
                       SUM(pnl) as total_pnl
                FROM positions 
                WHERE strategy_used IS NOT NULL
                GROUP BY strategy_used, asset_type
            """, conn)
            
            conn.close()
            
            analysis_data = {
                "active_strategies": strategy_config.to_dict('records'),
                "strategy_performance": positions_by_strategy.to_dict('records'),
                "strategy_count": len(strategy_config['strategy_name'].unique()) if not strategy_config.empty else 0
            }
            
            prompt = f"""
            ANALIZA LA EFECTIVIDAD DE LAS ESTRATEGIAS:

            ESTRATEGIAS ACTIVAS:
            {json.dumps(analysis_data["active_strategies"], indent=2, default=str)}

            PERFORMANCE POR ESTRATEGIA:
            {json.dumps(analysis_data["strategy_performance"], indent=2, default=str)}

            TOTAL ESTRATEGIAS: {analysis_data["strategy_count"]}

            EVALÚA:
            1. Efectividad de cada estrategia
            2. Configuraciones óptimas vs actuales
            3. Adaptación a diferentes mercados (stocks/crypto)
            4. Posibles mejoras en parámetros
            5. Estrategias subutilizadas o sobreusadas
            6. Necesidad de nuevas estrategias
            """
            
            response = ollama.chat(model=self.model, messages=[
                {'role': 'system', 'content': self.get_system_prompt()},
                {'role': 'user', 'content': prompt}
            ])
            
            return response['message']['content']
            
        except Exception as e:
            return f"[ERROR] Error analizando estrategias: {str(e)}"

    def get_critical_recommendations(self):
        """Genera recomendaciones críticas"""
        prompt = """
        GENERA RECOMENDACIONES CRÍTICAS Y ACCIONABLES:

        Como experto trader cuantitativo, dame:

        1. TOP 3 PROBLEMAS CRÍTICOS que debe arreglar YA
        2. TOP 5 OPTIMIZACIONES de mayor impacto
        3. GESTIÓN DE RIESGOS mejoras urgentes
        4. MÉTRICAS adicionales que debería monitorear
        5. AUTOMATIZACIÓN opportunities
        6. RESEARCH áreas para profundizar

        Cada recomendación debe ser:
        - Específica (no genérica)
        - Actionable (pasos concretos)
        - Priorizada (orden de importancia)
        - Con timeframe estimado

        Formato: 
        ## CRÍTICO
        1. [Problema] - [Solución específica] - [Timeframe]

        ## OPTIMIZACIONES
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
        """Ejecuta análisis completo adaptado a la DB real"""
        print("INICIANDO ANALISIS COMPLETO (DB ADAPTADO)...")
        print("=" * 80)
        
        analyses = {
            "[1] ANALISIS POSICIONES ACTUALES": self.analyze_current_positions,
            "[2] ANALISIS PERFORMANCE PORTFOLIO": self.analyze_portfolio_performance,
            "[3] ANALISIS EFECTIVIDAD ESTRATEGIAS": self.analyze_strategy_effectiveness,
            "[4] RECOMENDACIONES CRITICAS": self.get_critical_recommendations
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
        output_file = self.project_root / f"trading_analysis_fixed_{timestamp}.txt"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("ANALISIS COMPLETO DEL SISTEMA DE TRADING (ADAPTADO)\n")
            f.write("=" * 80 + "\n")
            f.write(f"Fecha: {datetime.now().isoformat()}\n")
            f.write(f"Modelo: {self.model}\n\n")
            
            for title, result in results.items():
                f.write(f"{title}\n")
                f.write("-" * 60 + "\n")
                f.write(result + "\n\n")
                f.write("=" * 80 + "\n\n")
        
        print(f"\n[DONE] Analisis guardado en: {output_file}")
        return results

if __name__ == "__main__":
    analyzer = FixedTradingAnalyzer()
    analyzer.run_complete_analysis()