"""
Demo Trading System Analyzer (sin Ollama)
Muestra qué datos analizaría el sistema con IA
"""

import pandas as pd
import sqlite3
import json
import os
from pathlib import Path
from datetime import datetime, timedelta
import glob

class DemoTradingAnalyzer:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.reports_dir = self.project_root / "reports"
        self.db_path = self.project_root / "trading.db"
        
    def show_available_data(self):
        """Muestra qué datos están disponibles para análisis"""
        print("DATOS DISPONIBLES PARA ANALISIS IA")
        print("=" * 60)
        
        # Database check
        if self.db_path.exists():
            print("[OK] Database encontrada: trading.db")
            try:
                conn = sqlite3.connect(self.db_path)
                
                # Check tables
                tables = pd.read_sql_query("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name NOT LIKE 'sqlite_%'
                """, conn)
                
                print(f"[DB] Tablas en DB: {', '.join(tables['name'].tolist())}")
                
                for table in tables['name']:
                    count = pd.read_sql_query(f"SELECT COUNT(*) as count FROM {table}", conn)
                    print(f"   - {table}: {count['count'].iloc[0]} registros")
                
                # Recent positions
                try:
                    recent_pos = pd.read_sql_query("""
                        SELECT COUNT(*) as recent_positions 
                        FROM positions 
                        WHERE created_at >= datetime('now', '-30 days')
                    """, conn)
                    print(f"[POS] Posiciones ultimos 30 dias: {recent_pos['recent_positions'].iloc[0]}")
                except:
                    print("[WARN] No se pudieron leer posiciones recientes")
                
                # Active symbols
                try:
                    symbols = pd.read_sql_query("""
                        SELECT COUNT(*) as active_symbols 
                        FROM symbols 
                        WHERE last_updated >= datetime('now', '-2 days')
                    """, conn)
                    print(f"[SYM] Simbolos activos: {symbols['active_symbols'].iloc[0]}")
                except:
                    print("[WARN] No se pudieron leer simbolos activos")
                
                conn.close()
                
            except Exception as e:
                print(f"[ERROR] Error accediendo a DB: {e}")
        else:
            print("[ERROR] Database no encontrada")
        
        # Excel reports check
        if self.reports_dir.exists():
            excel_files = list(self.reports_dir.glob("**/*.xlsx"))
            print(f"[XLS] Reportes Excel encontrados: {len(excel_files)}")
            
            if excel_files:
                excel_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                latest = excel_files[0]
                mod_time = datetime.fromtimestamp(latest.stat().st_mtime)
                print(f"   [LATEST] Ultimo reporte: {latest.name}")
                print(f"   [DATE] Fecha: {mod_time.strftime('%Y-%m-%d %H:%M')}")
        else:
            print("[ERROR] Carpeta reports/ no encontrada")
        
        print("\n" + "=" * 60)
        
    def demo_analysis_preview(self):
        """Muestra preview de qué análisis haría la IA"""
        print("\nPREVIEW DE ANALISIS CON IA")
        print("=" * 60)
        
        analyses = [
            {
                "[1] SENALES DE COMPRA": [
                    "• Evaluar RSI, MACD, Bollinger bands en símbolos activos",
                    "• Analizar timing de entradas recientes",  
                    "• Detectar patrones de éxito/fracaso",
                    "• Identificar oportunidades actuales",
                    "• Revisar distribución LONG vs SHORT"
                ]
            },
            {
                "[2] CODIGO": [
                    "• Revisar arquitectura FastAPI",
                    "• Evaluar servicios (autotrader, scoring, portfolio)",
                    "• Detectar code smells y bottlenecks",
                    "• Sugerir mejoras de rendimiento",
                    "• Analizar manejo de errores"
                ]
            },
            {
                "[3] REPORTES": [
                    "• Calcular Sharpe ratio y métricas de riesgo",
                    "• Analizar drawdown máximo",
                    "• Evaluar distribución ganancias/pérdidas",
                    "• Identificar patrones temporales",
                    "• Comparar performance entre períodos"
                ]
            },
            {
                "[4] STOCKS vs CRYPTO": [
                    "• Comparar ROI de $10k (stocks) vs $50k (crypto)",
                    "• Analizar volatilidad relativa",
                    "• Evaluar frequency trading differences", 
                    "• Identificar correlaciones cruzadas",
                    "• Sugerir rebalancing de capital"
                ]
            },
            {
                "[5] RECOMENDACIONES": [
                    "• Top 3 problemas críticos a resolver YA",
                    "• Top 5 optimizaciones de mayor impacto",
                    "• Mejoras urgentes de gestión de riesgo",
                    "• Métricas adicionales a implementar",
                    "• Oportunidades de automatización"
                ]
            }
        ]
        
        for analysis in analyses:
            for title, points in analysis.items():
                print(f"\n{title}")
                print("-" * 40)
                for point in points:
                    print(point)
        
        print("\n" + "=" * 60)
        print("Para activar analisis real:")
        print("   1. Instalar Ollama: https://ollama.ai/")
        print("   2. ollama pull llama3.1:8b")
        print("   3. python trading_analyzer.py")
    
    def run_demo(self):
        """Ejecuta demo completo"""
        print("DEMO: ANALISIS IA TRADING SYSTEM")
        print("=" * 60)
        
        self.show_available_data()
        self.demo_analysis_preview()
        
        print(f"\n[DONE] Demo ejecutado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    demo = DemoTradingAnalyzer()
    demo.run_demo()