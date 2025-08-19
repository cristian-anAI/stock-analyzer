#!/usr/bin/env python3
"""
Simple Web Dashboard for monitoring trading system
"""

from flask import Flask, render_template_string, jsonify
from datetime import datetime
import os
import sqlite3
import json

app = Flask(__name__)

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title> Trading System Dashboard</title>
    <meta http-equiv="refresh" content="30">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .card { background: white; padding: 20px; margin: 10px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .positive { color: #28a745; }
        .negative { color: #dc3545; }
        .neutral { color: #6c757d; }
        .header { text-align: center; color: #2c3e50; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .status { padding: 10px; border-radius: 4px; margin: 10px 0; }
        .status.running { background: #d4edda; color: #155724; }
        .status.error { background: #f8d7da; color: #721c24; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background: #f8f9fa; }
    </style>
</head>
<body>
    <div class="container">
        <h1 class="header"> Trading System Dashboard</h1>
        <p class="header">Last updated: {{ current_time }}</p>
        
        <div class="grid">
            <div class="card">
                <h3> Portfolio Summary</h3>
                <div class="status running">System Status: Running </div>
                <p><strong>Total Positions:</strong> {{ portfolio.total_positions }}</p>
                <p><strong>Total P&L:</strong> 
                   <span class="{{ 'positive' if portfolio.total_pnl >= 0 else 'negative' }}">
                   ${{ "%.2f"|format(portfolio.total_pnl) }}
                   </span>
                </p>
                <p><strong>Portfolio Value:</strong> ${{ "%.2f"|format(portfolio.total_value) }}</p>
            </div>
            
            <div class="card">
                <h3> Recent Signals</h3>
                {% for signal in recent_signals %}
                <div class="status">
                    {{ signal.time }} | {{ signal.symbol }}: {{ signal.message }}
                </div>
                {% endfor %}
            </div>
        </div>
        
        <div class="card">
            <h3> Active Positions</h3>
            <table>
                <tr>
                    <th>Symbol</th>
                    <th>Entry Price</th>
                    <th>Current Price</th>
                    <th>Quantity</th>
                    <th>P&L</th>
                    <th>P&L %</th>
                </tr>
                {% for pos in positions %}
                <tr>
                    <td>{{ pos.symbol }}</td>
                    <td>${{ "%.2f"|format(pos.entry_price) }}</td>
                    <td>${{ "%.2f"|format(pos.current_price) }}</td>
                    <td>{{ pos.quantity }}</td>
                    <td class="{{ 'positive' if pos.unrealized_pnl >= 0 else 'negative' }}">
                        ${{ "%.2f"|format(pos.unrealized_pnl) }}
                    </td>
                    <td class="{{ 'positive' if pos.unrealized_pnl_percent >= 0 else 'negative' }}">
                        {{ "%.1f"|format(pos.unrealized_pnl_percent) }}%
                    </td>
                </tr>
                {% endfor %}
            </table>
        </div>
    </div>
</body>
</html>
"""

def get_portfolio_data():
    """Get portfolio data from SQLite database"""
    try:
        db_path = "/app/data/trading.db"
        if not os.path.exists(db_path):
            return {"total_positions": 0, "total_pnl": 0, "total_value": 0}, []
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get positions
        cursor.execute("SELECT * FROM positions")
        positions = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        
        position_list = []
        total_pnl = 0
        total_value = 0
        
        for pos in positions:
            pos_dict = dict(zip(columns, pos))
            position_list.append(pos_dict)
            total_pnl += pos_dict.get('unrealized_pnl', 0)
            total_value += pos_dict.get('current_price', 0) * pos_dict.get('quantity', 0)
        
        portfolio = {
            "total_positions": len(position_list),
            "total_pnl": total_pnl,
            "total_value": total_value
        }
        
        conn.close()
        return portfolio, position_list
        
    except Exception as e:
        print(f"Database error: {e}")
        return {"total_positions": 0, "total_pnl": 0, "total_value": 0}, []

@app.route('/')
def dashboard():
    portfolio, positions = get_portfolio_data()
    
    # Mock recent signals (you can enhance this)
    recent_signals = [
        {"time": "12:30", "symbol": "BTC-USD", "message": "Manual review - P&L: +54.8%"},
        {"time": "12:25", "symbol": "NDAQ", "message": "Manual review - P&L: +25.6%"},
        {"time": "12:20", "symbol": "SLV", "message": "Take partial profit - P&L: +9.4%"}
    ]
    
    return render_template_string(DASHBOARD_HTML, 
                                  current_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                  portfolio=portfolio,
                                  positions=positions,
                                  recent_signals=recent_signals)

@app.route('/api/status')
def api_status():
    portfolio, positions = get_portfolio_data()
    return jsonify({
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "portfolio": portfolio,
        "positions_count": len(positions)
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False)
