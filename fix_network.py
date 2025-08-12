#!/usr/bin/env python3
"""
Fix Network Access - Fuerza el servidor a usar solo la IP WiFi
"""

from flask import Flask, request, jsonify, render_template_string
import json
import os
import threading
import time
from datetime import datetime

app = Flask(__name__)

# Dashboard HTML template
dashboard_html = """
<!DOCTYPE html>
<html>
<head>
    <title>Trading Dashboard</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: Arial; margin: 20px; background: #1a1a1a; color: white; }
        .header { text-align: center; margin-bottom: 30px; }
        .status { background: #2a2a2a; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
        .positions-container { max-height: 600px; overflow-y: auto; padding-right: 10px; }
        .position { background: #333; margin: 10px 0; padding: 15px; border-radius: 8px; border-left: 4px solid #4CAF50; }
        .position.loss { border-left-color: #f44336; }
        .symbol { font-size: 18px; font-weight: bold; margin-bottom: 8px; }
        .pnl { font-size: 16px; margin-bottom: 5px; }
        .details { font-size: 14px; color: #ccc; }
        .profit { color: #4CAF50; }
        .loss-text { color: #f44336; }
        .refresh { background: #4CAF50; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; }
        @media (max-width: 768px) { .positions-container { max-height: 400px; } body { margin: 10px; } }
    </style>
    <script>
        function refreshData() {
            location.reload();
        }
        setInterval(refreshData, 30000);
    </script>
</head>
<body>
    <div class="header">
        <h1>[CHART] Trading Dashboard</h1>
        <button class="refresh" onclick="refreshData()">[REFRESH] Refresh</button>
    </div>
    
    <div class="status">
        <h3>[CHART] Portfolio Status</h3>
        <p><strong>Total P&L:</strong> <span class="{{ 'profit' if data.total_pnl >= 0 else 'loss-text' }}">${{ "%.2f"|format(data.total_pnl) }}</span></p>
        <p><strong>Positions:</strong> {{ data.positions|length }} active</p>
        <p><strong>Last Update:</strong> {{ data.timestamp }}</p>
        <p><strong>Network:</strong> WiFi IP: 192.168.1.155</p>
    </div>
    
    <div class="positions-container">
        {% for symbol, pos in data.positions.items() %}
        <div class="position {{ 'loss' if pos.pnl_percent < 0 else '' }}">
            <div class="symbol">{{ symbol }} {{ pos.type }}</div>
            <div class="pnl">
                <span class="{{ 'profit' if pos.pnl_percent >= 0 else 'loss-text' }}">
                    {{ "%.2f"|format(pos.pnl_percent) }}% (${{ "%.2f"|format(pos.pnl_usd) }})
                </span>
            </div>
            <div class="details">
                Quantity: {{ "%.8f"|format(pos.quantity) }}<br>
                Entry: ${{ "%.4f"|format(pos.entry_price) }} → Current: ${{ "%.4f"|format(pos.current_price) }}<br>
                Value: ${{ "%.2f"|format(pos.current_price * pos.quantity) }}
            </div>
        </div>
        {% endfor %}
    </div>
</body>
</html>
"""

@app.route('/')
def dashboard():
    try:
        status_file = 'web/status.json'
        if os.path.exists(status_file):
            with open(status_file, 'r') as f:
                data = json.load(f)
        else:
            data = {
                'timestamp': datetime.now().isoformat(),
                'total_pnl': 0.0,
                'positions': {}
            }
        return render_template_string(dashboard_html, data=data)
    except Exception as e:
        return f"Error: {e}", 500

@app.route('/api/status')
def api_status():
    try:
        status_file = 'web/status.json'
        if os.path.exists(status_file):
            with open(status_file, 'r') as f:
                return jsonify(json.load(f))
        return jsonify({'error': 'No data available'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("=== SERVIDOR FORZADO A WiFi ===")
    print("[NETWORK] URL: http://192.168.1.155:5000")
    print("[MOBILE] Acceso movil: Conecta a la MISMA WiFi")
    print("[FIX] Forzando bind a IP especifica...")
    
    # Forzar el servidor a usar solo la IP WiFi
    app.run(
        host='192.168.1.155',  # Solo esta IP específica
        port=5000,
        debug=False,
        threaded=True
    )