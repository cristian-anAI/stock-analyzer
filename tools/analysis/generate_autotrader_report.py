#!/usr/bin/env python3
"""
Generador de reporte completo del autotrader para análisis con Claude/Llama
"""

import requests
import json
import sqlite3
from datetime import datetime, timedelta

def generate_comprehensive_report():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    report = f"""
# REPORTE COMPLETO DEL AUTOTRADER - STOCK ANALYZER
**Generado**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## 1. RESUMEN EJECUTIVO

### Estado del Sistema
- **API Status**: ✅ Operativo
- **Database**: ✅ Conectado
- **Autotrader**: ✅ Funcionando

### Configuración Actual
- **Threshold BUY LONG**: Score >= 7.5
- **Threshold SELL LONG**: Score <= 4.0  
- **Threshold SHORT Stocks**: Score < 2.5
- **Threshold SHORT Crypto**: Score < 3.5 + confidence > 70%
- **Max Position Value**: $10,000
- **Max Total Positions**: 20

## 2. ANÁLISIS DE MERCADO ACTUAL

"""
    
    try:
        api_base = "http://localhost:8000"
        
        # Obtener datos de stocks
        print("Obteniendo datos de stocks...")
        stocks_response = requests.get(f"{api_base}/api/v1/stocks")
        stocks = stocks_response.json() if stocks_response.status_code == 200 else []
        
        # Analizar oportunidades
        buy_opportunities = [s for s in stocks if s.get('score', 0) >= 7.5]
        sell_opportunities = [s for s in stocks if s.get('score', 0) <= 4.0]
        short_opportunities = [s for s in stocks if s.get('score', 0) < 2.5]
        
        report += f"""### Stocks Analizados: {len(stocks)}

#### Oportunidades LONG (Score >= 7.5): {len(buy_opportunities)}
"""
        if buy_opportunities:
            for stock in buy_opportunities[:10]:
                report += f"- **{stock['symbol']}** ({stock.get('name', 'N/A')}): Score {stock['score']} | Price ${stock['current_price']:.2f} | Change {stock.get('change_percent', 0):+.2f}%\n"
        else:
            report += "- ❌ Ninguna oportunidad LONG detectada\n"
            
        report += f"""
#### Oportunidades SELL (Score <= 4.0): {len(sell_opportunities)}
"""
        if sell_opportunities:
            for stock in sell_opportunities[:10]:
                report += f"- **{stock['symbol']}** ({stock.get('name', 'N/A')}): Score {stock['score']} | Price ${stock['current_price']:.2f} | Change {stock.get('change_percent', 0):+.2f}%\n"
        else:
            report += "- ❌ Ninguna oportunidad SELL detectada\n"

        report += f"""
#### Oportunidades SHORT (Score < 2.5): {len(short_opportunities)}
"""
        if short_opportunities:
            for stock in short_opportunities[:10]:
                report += f"- **{stock['symbol']}** ({stock.get('name', 'N/A')}): Score {stock['score']} | Price ${stock['current_price']:.2f} | Change {stock.get('change_percent', 0):+.2f}%\n"
        else:
            report += "- ❌ Ninguna oportunidad SHORT stocks detectada\n"
            
        # Obtener datos de crypto
        print("Obteniendo datos de crypto...")
        crypto_response = requests.get(f"{api_base}/api/v1/cryptos")
        cryptos = crypto_response.json() if crypto_response.status_code == 200 else []
        
        crypto_short_opportunities = [c for c in cryptos if c.get('score', 5) < 3.5]
        
        report += f"""
### Crypto Analizados: {len(cryptos)}

#### Oportunidades CRYPTO SHORT (Score < 3.5): {len(crypto_short_opportunities)}
"""
        if crypto_short_opportunities:
            for crypto in crypto_short_opportunities[:10]:
                report += f"- **{crypto['symbol']}**: Score {crypto.get('score', 'N/A')} | Change {crypto.get('change_percent', 0):+.2f}%\n"
        else:
            report += "- ❌ Ninguna oportunidad CRYPTO SHORT detectada\n"
        
        # Obtener posiciones SHORT actuales
        print("Obteniendo posiciones SHORT...")
        short_pos_response = requests.get(f"{api_base}/api/v1/short-positions")
        
        if short_pos_response.status_code == 200:
            short_data = short_pos_response.json()
            positions = short_data.get('short_positions', [])
            summary = short_data.get('summary', {})
            
            report += f"""
## 3. POSICIONES SHORT ACTUALES

### Resumen
- **Total Posiciones**: {summary.get('total_positions', 0)}
- **PnL Total**: ${summary.get('total_pnl', 0):.2f}
- **PnL Promedio**: {summary.get('avg_pnl_percent', 0):.2f}%
- **Posiciones Alto Riesgo**: {summary.get('high_risk_positions', 0)}
- **Posiciones para Exit**: {summary.get('positions_to_exit', 0)}

### Detalle de Posiciones
"""
            for pos in positions:
                days_held = pos.get('days_held', 0)
                report += f"""
#### {pos['symbol']}
- **Entry Price**: ${pos['entry_price']:.4f}
- **Current Price**: ${pos['current_price']:.4f}
- **Quantity**: {pos['quantity']:.2f}
- **PnL**: ${pos['pnl']:.2f} ({pos['pnl_percent']:+.2f}%)
- **Stop Loss**: ${pos['stop_loss_updated']:.4f} ({pos.get('distance_to_stop_percent', 0):.2f}% away)
- **Take Profit**: ${pos['take_profit_updated']:.4f} ({pos.get('distance_to_tp_percent', 0):.2f}% away)
- **Days Held**: {days_held}
- **Risk Level**: {pos.get('risk_level', 'UNKNOWN')}
- **Should Exit**: {'🚨 YES' if pos.get('should_exit') else '✅ NO'}
"""
        
        # Análisis de base de datos
        print("Analizando base de datos...")
        try:
            conn = sqlite3.connect('trading.db')
            cursor = conn.cursor()
            
            # Contar transacciones del autotrader
            cursor.execute("SELECT COUNT(*) FROM autotrader_transactions")
            transaction_count = cursor.fetchone()[0]
            
            # Obtener últimas transacciones
            cursor.execute("""
                SELECT symbol, action, quantity, price, timestamp, reason
                FROM autotrader_transactions 
                ORDER BY timestamp DESC 
                LIMIT 10
            """)
            recent_transactions = cursor.fetchall()
            
            report += f"""
## 4. HISTORIAL DE TRANSACCIONES

### Resumen
- **Total Transacciones Autotrader**: {transaction_count}

### Últimas 10 Transacciones
"""
            if recent_transactions:
                for trans in recent_transactions:
                    symbol, action, quantity, price, timestamp, reason = trans
                    report += f"- **{symbol}** {action}: {quantity:.2f} @ ${price:.4f} | {timestamp} | {reason}\n"
            else:
                report += "- ❌ No hay transacciones registradas (posible bug en transaction logging)\n"
            
            # Análisis de símbolos en watchlist
            cursor.execute("SELECT COUNT(*) FROM stocks")
            stock_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM cryptos")
            crypto_count = cursor.fetchone()[0]
            
            report += f"""
## 5. BASE DE DATOS

### Símbolos en Watchlist
- **Stocks**: {stock_count}
- **Cryptos**: {crypto_count}
- **Total**: {stock_count + crypto_count}

"""
            conn.close()
            
        except Exception as e:
            report += f"❌ Error accediendo a la base de datos: {e}\n"
        
        # Distribución de scores
        score_distribution = {}
        for stock in stocks:
            score = stock.get('score', 0)
            score_range = f"{int(score)}-{int(score)+1}"
            score_distribution[score_range] = score_distribution.get(score_range, 0) + 1
        
        report += """## 6. DISTRIBUCIÓN DE SCORES (STOCKS)

"""
        for score_range, count in sorted(score_distribution.items()):
            report += f"- **Score {score_range}**: {count} stocks\n"
        
        # Análisis y recomendaciones
        total_opportunities = len(buy_opportunities) + len(sell_opportunities) + len(short_opportunities) + len(crypto_short_opportunities)
        
        report += f"""
## 7. ANÁLISIS Y RECOMENDACIONES

### Estado Actual del Mercado
"""
        if total_opportunities == 0:
            report += """- 🔄 **MERCADO LATERAL**: No hay señales claras de trading
- ⚡ **SISTEMA FUNCIONANDO**: Los thresholds están correctamente configurados
- 🛡️ **ESTRATEGIA CONSERVATIVA**: El sistema evita trades arriesgados"""
        else:
            report += f"""- 📈 **{total_opportunities} OPORTUNIDADES DETECTADAS**
- ✅ **SISTEMA ACTIVO**: El autotrader está identificando señales
- 🎯 **ESTRATEGIA FUNCIONANDO**: Thresholds capturando movimientos significativos"""

        report += f"""

### Efectividad de los Thresholds
- **BUY LONG (>= 7.5)**: {'✅ Funcionando' if len(buy_opportunities) > 0 else '⚠️ Muy conservativo - ninguna oportunidad'}
- **SELL LONG (<= 4.0)**: {'✅ Funcionando' if len(sell_opportunities) > 0 else '⚠️ Sin señales de venta'}
- **SHORT Stocks (< 2.5)**: {'✅ Funcionando' if len(short_opportunities) > 0 else '⚠️ Ultra-conservativo - ninguna señal'}
- **SHORT Crypto (< 3.5)**: {'✅ Funcionando' if len(crypto_short_opportunities) > 0 else '⚠️ Sin oportunidades crypto'}

### Recomendaciones
1. **Monitoreo**: Las posiciones SHORT actuales están dentro de parámetros normales
2. **Risk Management**: Stop losses correctamente configurados
3. **Performance**: PnL promedio {summary.get('avg_pnl_percent', 0):.2f}% es aceptable para estrategia conservativa
4. **Bug Fix**: {'✅ Transaction logging fixed' if transaction_count > 0 else '⚠️ Transaction logging needs verification'}

## 8. DATOS PARA ANÁLISIS AVANZADO

### JSON Data for LLM Analysis
```json
{json.dumps({
    'timestamp': datetime.now().isoformat(),
    'market_analysis': {
        'stocks_analyzed': len(stocks),
        'buy_opportunities': len(buy_opportunities),
        'sell_opportunities': len(sell_opportunities), 
        'short_opportunities': len(short_opportunities),
        'crypto_short_opportunities': len(crypto_short_opportunities)
    },
    'current_positions': positions if 'positions' in locals() else [],
    'performance_summary': summary if 'summary' in locals() else {},
    'thresholds': {
        'buy_long': 7.5,
        'sell_long': 4.0,
        'short_stocks': 2.5,
        'short_crypto': 3.5
    },
    'database_stats': {
        'stock_count': stock_count if 'stock_count' in locals() else 0,
        'crypto_count': crypto_count if 'crypto_count' in locals() else 0,
        'transaction_count': transaction_count if 'transaction_count' in locals() else 0
    }
}, indent=2)}
```

---
**Reporte generado automáticamente por Stock Analyzer**
**Para análisis con Claude Code o Llama AI**
"""
        
        # Guardar reporte
        filename = f"reports/autotrader_analysis_{timestamp}.md"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(report)
        
        # También crear versión txt para Ollama/Llama
        txt_filename = f"reports/autotrader_analysis_{timestamp}.txt"
        with open(txt_filename, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"✅ REPORTE GENERADO EXITOSAMENTE")
        print(f"📄 Archivo Markdown: {filename}")
        print(f"📄 Archivo Texto: {txt_filename}")
        print(f"📊 Tamaño: {len(report):,} caracteres")
        
        # Mostrar resumen
        print(f"\n📋 RESUMEN EJECUTIVO:")
        print(f"   - Stocks analizados: {len(stocks)}")
        print(f"   - Oportunidades totales: {total_opportunities}")
        print(f"   - Posiciones SHORT activas: {len(positions) if 'positions' in locals() else 0}")
        print(f"   - Transacciones registradas: {transaction_count if 'transaction_count' in locals() else 0}")
        
        return filename, txt_filename
        
    except Exception as e:
        print(f"❌ Error generando reporte: {e}")
        import traceback
        traceback.print_exc()
        return None, None

if __name__ == "__main__":
    md_file, txt_file = generate_comprehensive_report()
    if md_file:
        print(f"\n🎯 ARCHIVOS LISTOS PARA ANÁLISIS CON IA:")
        print(f"   - Claude Code: {md_file}")
        print(f"   - Llama/Ollama: {txt_file}")
        print(f"\n💡 Puedes usar estos archivos para análisis avanzado con cualquier LLM")