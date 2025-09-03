#!/usr/bin/env python3
"""
Análisis de ratio de acierto y profit real
Evalúa performance histórica de los stocks que califican con nuevos thresholds
"""

import yfinance as yf
import requests
import numpy as np
from datetime import datetime, timedelta
import time
import pandas as pd

def analyze_win_rate_and_profit():
    print("ANÁLISIS DE RATIO DE ACIERTO Y PROFIT REAL")
    print("=" * 60)
    print(f"Análisis: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Obtener stocks que califican con nuevos thresholds
    print("\n1. Obteniendo stocks que califican con NUEVOS thresholds...")
    
    try:
        response = requests.get("http://localhost:8000/api/v1/stocks")
        if response.status_code != 200:
            print("Error conectando al API")
            return
        
        stocks = response.json()
        
        # Filtrar por nuevos thresholds
        new_thresholds = {
            'buy_long': 6.0,
            'sell_long': 4.0,
            'short': 1.8
        }
        
        long_candidates = [s for s in stocks if s.get('score', 0) >= new_thresholds['buy_long']]
        short_candidates = [s for s in stocks if s.get('score', 0) < new_thresholds['short']]
        
        print(f"   LONG candidates: {len(long_candidates)}")
        print(f"   SHORT candidates: {len(short_candidates)}")
        
        if not long_candidates and not short_candidates:
            print("   No hay candidatos para analizar")
            return
        
        # Analizar performance histórica de LONGs
        if long_candidates:
            print(f"\n2. ANÁLISIS DE PERFORMANCE HISTÓRICA - LONG POSITIONS")
            print("-" * 60)
            
            long_results = analyze_long_performance(long_candidates)
            
        # Analizar performance histórica de SHORTs
        if short_candidates:
            print(f"\n3. ANÁLISIS DE PERFORMANCE HISTÓRICA - SHORT POSITIONS")
            print("-" * 60)
            
            short_results = analyze_short_performance(short_candidates)
        
        # Análisis combinado
        print(f"\n4. ANÁLISIS CONSOLIDADO DE PORTFOLIO")
        print("-" * 60)
        
        analyze_combined_performance(
            long_candidates if long_candidates else [],
            short_candidates if short_candidates else []
        )
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

def analyze_long_performance(long_candidates):
    """Analizar performance histórica de candidatos LONG"""
    
    periods = [7, 14, 30, 60]  # días
    results = {}
    
    print(f"Analizando {len(long_candidates)} candidatos LONG...")
    
    all_performances = {period: [] for period in periods}
    individual_results = []
    
    for i, stock in enumerate(long_candidates):
        symbol = stock['symbol']
        current_score = stock['score']
        current_price = stock['current_price']
        
        print(f"   {i+1:2d}/{len(long_candidates)} {symbol} (Score: {current_score})", end="")
        
        try:
            # Obtener datos históricos
            ticker = yf.Ticker(symbol)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=90)
            
            hist_data = ticker.history(start=start_date, end=end_date)
            
            if len(hist_data) < 60:
                print(" - Datos insuficientes")
                continue
            
            stock_results = {'symbol': symbol, 'score': current_score}
            
            # Analizar diferentes períodos
            for period in periods:
                if len(hist_data) > period:
                    price_then = hist_data['Close'].iloc[-(period+1)]
                    price_now = hist_data['Close'].iloc[-1]
                    performance = ((price_now - price_then) / price_then) * 100
                    
                    stock_results[f'{period}d'] = performance
                    all_performances[period].append(performance)
            
            individual_results.append(stock_results)
            
            # Mostrar performance reciente
            if '7d' in stock_results and '30d' in stock_results:
                print(f" | 7d: {stock_results['7d']:+.1f}% | 30d: {stock_results['30d']:+.1f}%")
            else:
                print(" - OK")
            
        except Exception as e:
            print(f" - Error: {str(e)[:30]}")
            continue
        
        time.sleep(0.1)  # Rate limiting
    
    # Calcular estadísticas
    print(f"\nRESULTADOS LONG POSITIONS:")
    print(f"{'Período':<10} {'Promedio':<10} {'Win Rate':<10} {'Mejor':<10} {'Peor':<10} {'Trades':<8}")
    print("-" * 60)
    
    period_stats = {}
    
    for period in periods:
        if all_performances[period]:
            performances = all_performances[period]
            avg_perf = np.mean(performances)
            win_rate = (sum(1 for p in performances if p > 0) / len(performances)) * 100
            best = max(performances)
            worst = min(performances)
            count = len(performances)
            
            period_stats[period] = {
                'avg': avg_perf,
                'win_rate': win_rate,
                'best': best,
                'worst': worst,
                'count': count
            }
            
            print(f"{period}d{'':<7} {avg_perf:+.2f}%{'':<3} {win_rate:.1f}%{'':<5} {best:+.1f}%{'':<4} {worst:+.1f}%{'':<4} {count:<8}")
    
    # Top y worst performers
    if individual_results:
        print(f"\nTOP 5 PERFORMERS (30 días):")
        sorted_30d = [r for r in individual_results if '30d' in r]
        sorted_30d.sort(key=lambda x: x['30d'], reverse=True)
        
        for i, stock in enumerate(sorted_30d[:5], 1):
            print(f"   {i}. {stock['symbol']:6s} | Score {stock['score']:3.1f} | 30d: {stock['30d']:+6.2f}%")
        
        print(f"\nWORST 5 PERFORMERS (30 días):")
        for i, stock in enumerate(sorted_30d[-5:], 1):
            print(f"   {i}. {stock['symbol']:6s} | Score {stock['score']:3.1f} | 30d: {stock['30d']:+6.2f}%")
    
    return period_stats

def analyze_short_performance(short_candidates):
    """Analizar performance de candidatos SHORT"""
    
    print(f"Analizando {len(short_candidates)} candidatos SHORT...")
    
    periods = [7, 14, 30]
    all_performances = {period: [] for period in periods}
    individual_results = []
    
    for i, stock in enumerate(short_candidates):
        symbol = stock['symbol']
        current_score = stock['score']
        
        print(f"   {i+1}/{len(short_candidates)} {symbol} (Score: {current_score})", end="")
        
        try:
            ticker = yf.Ticker(symbol)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=60)
            
            hist_data = ticker.history(start=start_date, end=end_date)
            
            if len(hist_data) < 30:
                print(" - Datos insuficientes")
                continue
            
            stock_results = {'symbol': symbol, 'score': current_score}
            
            # Para SHORT: profit cuando precio baja
            for period in periods:
                if len(hist_data) > period:
                    price_then = hist_data['Close'].iloc[-(period+1)]
                    price_now = hist_data['Close'].iloc[-1]
                    # SHORT profit = precio baja
                    short_performance = ((price_then - price_now) / price_then) * 100
                    
                    stock_results[f'{period}d'] = short_performance
                    all_performances[period].append(short_performance)
            
            individual_results.append(stock_results)
            
            if '7d' in stock_results and '30d' in stock_results:
                print(f" | SHORT 7d: {stock_results['7d']:+.1f}% | 30d: {stock_results['30d']:+.1f}%")
            else:
                print(" - OK")
                
        except Exception as e:
            print(f" - Error: {str(e)[:30]}")
        
        time.sleep(0.1)
    
    # Estadísticas SHORT
    print(f"\nRESULTADOS SHORT POSITIONS:")
    print(f"{'Período':<10} {'Promedio':<10} {'Win Rate':<10} {'Mejor':<10} {'Peor':<10} {'Trades':<8}")
    print("-" * 60)
    
    for period in periods:
        if all_performances[period]:
            performances = all_performances[period]
            avg_perf = np.mean(performances)
            win_rate = (sum(1 for p in performances if p > 0) / len(performances)) * 100
            best = max(performances)
            worst = min(performances)
            count = len(performances)
            
            print(f"{period}d{'':<7} {avg_perf:+.2f}%{'':<3} {win_rate:.1f}%{'':<5} {best:+.1f}%{'':<4} {worst:+.1f}%{'':<4} {count:<8}")

def analyze_combined_performance(long_candidates, short_candidates):
    """Análisis combinado del portfolio"""
    
    print("SIMULACIÓN DE PORTFOLIO BALANCEADO")
    print("-" * 40)
    
    # Configuración de portfolio simulado
    total_capital = 100000  # $100k
    max_positions = 15  # Máximo 15 posiciones
    
    # Asignación: 80% LONG, 20% SHORT
    long_capital = total_capital * 0.8
    short_capital = total_capital * 0.2
    
    num_long_positions = min(len(long_candidates), 12)
    num_short_positions = min(len(short_candidates), 3)
    
    if num_long_positions > 0:
        capital_per_long = long_capital / num_long_positions
    else:
        capital_per_long = 0
        
    if num_short_positions > 0:
        capital_per_short = short_capital / num_short_positions
    else:
        capital_per_short = 0
    
    print(f"Portfolio simulado:")
    print(f"  Capital total: ${total_capital:,}")
    print(f"  LONGs: {num_long_positions} posiciones x ${capital_per_long:,.0f}")
    print(f"  SHORTs: {num_short_positions} posiciones x ${capital_per_short:,.0f}")
    
    # Simular performance histórica
    periods = [7, 30]
    
    for period in periods:
        print(f"\nPERFORMANCE PORTFOLIO ÚLTIMOS {period} DÍAS:")
        
        total_portfolio_return = 0
        long_return = 0
        short_return = 0
        
        # Calcular LONG performance
        if long_candidates:
            long_performances = []
            for stock in long_candidates[:num_long_positions]:
                try:
                    ticker = yf.Ticker(stock['symbol'])
                    hist_data = ticker.history(period=f"{period+10}d")
                    
                    if len(hist_data) > period:
                        price_then = hist_data['Close'].iloc[-(period+1)]
                        price_now = hist_data['Close'].iloc[-1]
                        stock_return = ((price_now - price_then) / price_then) * 100
                        long_performances.append(stock_return)
                except:
                    continue
            
            if long_performances:
                long_return = np.mean(long_performances)
        
        # Calcular SHORT performance
        if short_candidates:
            short_performances = []
            for stock in short_candidates[:num_short_positions]:
                try:
                    ticker = yf.Ticker(stock['symbol'])
                    hist_data = ticker.history(period=f"{period+10}d")
                    
                    if len(hist_data) > period:
                        price_then = hist_data['Close'].iloc[-(period+1)]
                        price_now = hist_data['Close'].iloc[-1]
                        # SHORT: profit cuando precio baja
                        stock_return = ((price_then - price_now) / price_then) * 100
                        short_performances.append(stock_return)
                except:
                    continue
            
            if short_performances:
                short_return = np.mean(short_performances)
        
        # Portfolio total
        total_portfolio_return = (long_return * 0.8) + (short_return * 0.2)
        
        # Valor final
        final_value = total_capital * (1 + total_portfolio_return / 100)
        profit_loss = final_value - total_capital
        
        print(f"  LONG return (80%): {long_return:+.2f}%")
        print(f"  SHORT return (20%): {short_return:+.2f}%")
        print(f"  PORTFOLIO TOTAL: {total_portfolio_return:+.2f}%")
        print(f"  Valor inicial: ${total_capital:,}")
        print(f"  Valor final: ${final_value:,.0f}")
        print(f"  P&L: ${profit_loss:+,.0f}")
        
        # Comparar con estrategia antigua
        print(f"  vs OLD strategy: {total_portfolio_return:+.2f}% vs 0.00%")

def main():
    analyze_win_rate_and_profit()

if __name__ == "__main__":
    main()