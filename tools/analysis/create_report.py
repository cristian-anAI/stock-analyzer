#!/usr/bin/env python3
"""
Generador simple de reporte del autotrader
"""

import requests
import json
import sqlite3
from datetime import datetime

def create_simple_report():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    report_lines = []
    report_lines.append("# AUTOTRADER ANALYSIS REPORT")
    report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("")
    
    try:
        api_base = "http://localhost:8000"
        
        # Obtener datos de stocks
        print("Getting stocks data...")
        stocks_response = requests.get(f"{api_base}/api/v1/stocks")
        stocks = stocks_response.json() if stocks_response.status_code == 200 else []
        
        # Analizar oportunidades
        buy_opportunities = [s for s in stocks if s.get('score', 0) >= 7.5]
        sell_opportunities = [s for s in stocks if s.get('score', 0) <= 4.0]
        short_opportunities = [s for s in stocks if s.get('score', 0) < 2.5]
        
        report_lines.append("## MARKET ANALYSIS")
        report_lines.append(f"Stocks analyzed: {len(stocks)}")
        report_lines.append(f"BUY opportunities (score >= 7.5): {len(buy_opportunities)}")
        report_lines.append(f"SELL opportunities (score <= 4.0): {len(sell_opportunities)}")
        report_lines.append(f"SHORT opportunities (score < 2.5): {len(short_opportunities)}")
        report_lines.append("")
        
        # TOP stocks for each category
        if buy_opportunities:
            report_lines.append("### TOP BUY OPPORTUNITIES")
            for stock in buy_opportunities[:5]:
                report_lines.append(f"- {stock['symbol']}: Score {stock['score']} | Price ${stock['current_price']:.2f} | Change {stock.get('change_percent', 0):+.2f}%")
            report_lines.append("")
        
        if sell_opportunities:
            report_lines.append("### TOP SELL OPPORTUNITIES")
            for stock in sell_opportunities[:5]:
                report_lines.append(f"- {stock['symbol']}: Score {stock['score']} | Price ${stock['current_price']:.2f} | Change {stock.get('change_percent', 0):+.2f}%")
            report_lines.append("")
        
        if short_opportunities:
            report_lines.append("### TOP SHORT OPPORTUNITIES")
            for stock in short_opportunities[:5]:
                report_lines.append(f"- {stock['symbol']}: Score {stock['score']} | Price ${stock['current_price']:.2f} | Change {stock.get('change_percent', 0):+.2f}%")
            report_lines.append("")
        
        # Crypto data
        print("Getting crypto data...")
        crypto_response = requests.get(f"{api_base}/api/v1/cryptos")
        cryptos = crypto_response.json() if crypto_response.status_code == 200 else []
        
        crypto_short_opportunities = [c for c in cryptos if c.get('score', 5) < 3.5]
        
        report_lines.append("## CRYPTO ANALYSIS")
        report_lines.append(f"Cryptos analyzed: {len(cryptos)}")
        report_lines.append(f"CRYPTO SHORT opportunities (score < 3.5): {len(crypto_short_opportunities)}")
        report_lines.append("")
        
        if crypto_short_opportunities:
            report_lines.append("### CRYPTO SHORT OPPORTUNITIES")
            for crypto in crypto_short_opportunities[:5]:
                report_lines.append(f"- {crypto['symbol']}: Score {crypto.get('score', 'N/A')} | Change {crypto.get('change_percent', 0):+.2f}%")
            report_lines.append("")
        
        # Current SHORT positions
        print("Getting SHORT positions...")
        short_pos_response = requests.get(f"{api_base}/api/v1/short-positions")
        
        if short_pos_response.status_code == 200:
            short_data = short_pos_response.json()
            positions = short_data.get('short_positions', [])
            summary = short_data.get('summary', {})
            
            report_lines.append("## CURRENT SHORT POSITIONS")
            report_lines.append(f"Total positions: {summary.get('total_positions', 0)}")
            report_lines.append(f"Total PnL: ${summary.get('total_pnl', 0):.2f}")
            report_lines.append(f"Average PnL: {summary.get('avg_pnl_percent', 0):.2f}%")
            report_lines.append("")
            
            for pos in positions:
                report_lines.append(f"### {pos['symbol']}")
                report_lines.append(f"- Entry: ${pos['entry_price']:.4f} | Current: ${pos['current_price']:.4f}")
                report_lines.append(f"- PnL: ${pos['pnl']:.2f} ({pos['pnl_percent']:+.2f}%)")
                report_lines.append(f"- Stop Loss: ${pos['stop_loss_updated']:.4f}")
                report_lines.append(f"- Take Profit: ${pos['take_profit_updated']:.4f}")
                report_lines.append(f"- Days held: {pos.get('days_held', 0)}")
                report_lines.append(f"- Risk level: {pos.get('risk_level', 'UNKNOWN')}")
                report_lines.append("")
        
        # Database analysis
        print("Analyzing database...")
        try:
            conn = sqlite3.connect('trading.db')
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM autotrader_transactions")
            transaction_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM stocks")
            stock_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM cryptos")
            crypto_count = cursor.fetchone()[0]
            
            report_lines.append("## DATABASE STATS")
            report_lines.append(f"Autotrader transactions: {transaction_count}")
            report_lines.append(f"Stocks in watchlist: {stock_count}")
            report_lines.append(f"Cryptos in watchlist: {crypto_count}")
            report_lines.append("")
            
            # Recent transactions
            cursor.execute("""
                SELECT symbol, action, quantity, price, timestamp, reason
                FROM autotrader_transactions 
                ORDER BY timestamp DESC 
                LIMIT 5
            """)
            recent_transactions = cursor.fetchall()
            
            if recent_transactions:
                report_lines.append("### RECENT TRANSACTIONS")
                for trans in recent_transactions:
                    symbol, action, quantity, price, timestamp, reason = trans
                    report_lines.append(f"- {symbol} {action}: {quantity:.2f} @ ${price:.4f} | {timestamp}")
                report_lines.append("")
            
            conn.close()
            
        except Exception as e:
            report_lines.append(f"Database error: {e}")
            report_lines.append("")
        
        # Summary and recommendations
        total_opportunities = len(buy_opportunities) + len(sell_opportunities) + len(short_opportunities) + len(crypto_short_opportunities)
        
        report_lines.append("## SUMMARY")
        report_lines.append(f"Total trading opportunities: {total_opportunities}")
        report_lines.append("")
        
        report_lines.append("### AUTOTRADER STATUS")
        if total_opportunities > 0:
            report_lines.append("- ACTIVE: System detecting trading signals")
            report_lines.append("- STRATEGY: Functioning according to configured thresholds")
        else:
            report_lines.append("- NEUTRAL: No clear trading signals at this time")
            report_lines.append("- MARKET: Sideways/consolidation phase")
        
        report_lines.append("")
        report_lines.append("### THRESHOLD EFFECTIVENESS")
        report_lines.append(f"- BUY LONG (>= 7.5): {'ACTIVE' if len(buy_opportunities) > 0 else 'CONSERVATIVE - no signals'}")
        report_lines.append(f"- SELL LONG (<= 4.0): {'ACTIVE' if len(sell_opportunities) > 0 else 'CONSERVATIVE - no signals'}")
        report_lines.append(f"- SHORT Stocks (< 2.5): {'ACTIVE' if len(short_opportunities) > 0 else 'ULTRA-CONSERVATIVE - no signals'}")
        report_lines.append(f"- SHORT Crypto (< 3.5): {'ACTIVE' if len(crypto_short_opportunities) > 0 else 'CONSERVATIVE - no signals'}")
        
        report_lines.append("")
        report_lines.append("---")
        report_lines.append("Report generated automatically by Stock Analyzer")
        report_lines.append("Ready for analysis with Claude Code or Llama AI")
        
        # Save report
        report_content = "\n".join(report_lines)
        
        # Create reports directory if it doesn't exist
        import os
        if not os.path.exists('reports'):
            os.makedirs('reports')
        
        filename = f"reports/autotrader_report_{timestamp}.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        print(f"SUCCESS: Report generated")
        print(f"File: {filename}")
        print(f"Size: {len(report_content):,} characters")
        print("")
        print("EXECUTIVE SUMMARY:")
        print(f"  - Stocks analyzed: {len(stocks)}")
        print(f"  - Total opportunities: {total_opportunities}")
        print(f"  - SHORT positions: {len(positions) if 'positions' in locals() else 0}")
        print(f"  - Transactions logged: {transaction_count if 'transaction_count' in locals() else 0}")
        
        return filename
        
    except Exception as e:
        print(f"Error generating report: {e}")
        return None

if __name__ == "__main__":
    filename = create_simple_report()
    if filename:
        print(f"\nREPORT READY FOR AI ANALYSIS: {filename}")
    else:
        print("\nReport generation failed")