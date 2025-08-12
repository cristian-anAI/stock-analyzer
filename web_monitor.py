#!/usr/bin/env python3
"""
Web Monitor - Dashboard web para monitoreo remoto del servidor de trading
"""

import os
import json
import glob
from datetime import datetime, timedelta
from flask import Flask, render_template_string, jsonify, send_from_directory
import threading
import time

app = Flask(__name__)

# HTML Template for the dashboard
DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Trading Server Monitor</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #1e1e1e; color: white; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { text-align: center; margin-bottom: 30px; }
        .status-box { background: #2d2d2d; padding: 20px; margin: 10px 0; border-radius: 8px; border-left: 4px solid #4CAF50; }
        .status-box.error { border-left-color: #f44336; }
        .status-box.warning { border-left-color: #ff9800; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .positions-container { max-height: 600px; overflow-y: auto; padding-right: 10px; }
        .positions-container::-webkit-scrollbar { width: 8px; }
        .positions-container::-webkit-scrollbar-track { background: #1e1e1e; border-radius: 4px; }
        .positions-container::-webkit-scrollbar-thumb { background: #4CAF50; border-radius: 4px; }
        .positions-container::-webkit-scrollbar-thumb:hover { background: #45a049; }
        .position { background: #2d2d2d; padding: 15px; border-radius: 8px; margin: 5px 0; transition: all 0.3s ease; }
        .position:hover { transform: translateY(-2px); box-shadow: 0 4px 8px rgba(0,0,0,0.3); }
        .position.manual { border-left: 4px solid #2196F3; }
        .position.auto { border-left: 4px solid #4CAF50; }
        .profit { color: #4CAF50; font-weight: bold; }
        .loss { color: #f44336; font-weight: bold; }
        .logs { background: #000; color: #0f0; padding: 15px; border-radius: 8px; font-family: monospace; font-size: 12px; max-height: 400px; overflow-y: auto; }
        .position-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
        .position-type { font-size: 10px; padding: 2px 6px; border-radius: 3px; font-weight: bold; }
        .position-details { font-size: 11px; color: #ccc; line-height: 1.4; }
        .position-pnl { font-size: 14px; font-weight: bold; }
        .scroll-indicator { text-align: center; color: #888; font-size: 12px; margin-top: 10px; }
        .refresh { position: fixed; top: 20px; right: 20px; background: #4CAF50; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; }
        .stats { display: flex; justify-content: space-around; text-align: center; }
        .stats div { background: #2d2d2d; padding: 15px; border-radius: 8px; }
        h1, h2 { color: #4CAF50; }
        .timestamp { color: #888; font-size: 12px; }
        
        /* Mobile Responsive */
        @media (max-width: 768px) {
            .container { margin: 10px; }
            .grid { grid-template-columns: 1fr; gap: 15px; }
            .stats { flex-direction: column; gap: 10px; }
            .stats div { margin-bottom: 10px; }
            .positions-container { max-height: 400px; }
            .position { padding: 12px; }
            .position-header { flex-direction: column; align-items: flex-start; gap: 5px; }
            .position-pnl { align-self: flex-end; }
            .refresh { position: relative; top: 0; right: 0; margin: 10px 0; width: 100%; }
        }
        
        /* Improved scrollbar for mobile */
        @media (max-width: 768px) {
            .positions-container::-webkit-scrollbar { width: 6px; }
        }
    </style>
    <script>
        function refreshData() {
            location.reload();
        }
        
        function autoRefresh() {
            setInterval(refreshData, 30000); // Refresh every 30 seconds
        }
        
        window.onload = autoRefresh;
        
        function formatNumber(num) {
            return new Intl.NumberFormat('en-US', { 
                minimumFractionDigits: 2, 
                maximumFractionDigits: 2 
            }).format(num);
        }
    </script>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>[SERVER] Trading Server Monitor</h1>
            <p class="timestamp">Last Update: {{ last_update }}</p>
            <button class="refresh" onclick="refreshData()">[REFRESH]</button>
        </div>
        
        <div class="status-box {{ status_class }}">
            <h2>[STATUS] Server Status</h2>
            <div class="stats">
                <div><strong>{{ uptime_hours }}</strong><br>Hours Online</div>
                <div><strong>{{ total_positions }}</strong><br>Positions</div>
                <div><strong class="{{ pnl_class }}">${{ total_pnl }}</strong><br>Total P&L</div>
                <div><strong>{{ running_status }}</strong><br>Status</div>
            </div>
        </div>
        
        <div class="grid">
            <div>
                <h2>[POSITIONS] Positions ({{ total_positions }})</h2>
                <div class="positions-container">
                    {% for symbol, pos in positions.items() %}
                    <div class="position {{ pos.type.lower() }}">
                        <div class="position-header">
                            <div>
                                <strong>{{ symbol }}</strong>
                                <span class="position-type" style="background: {{ '#2196F3' if pos.type == 'MANUAL' else '#4CAF50' }}; color: white;">{{ pos.type }}</span>
                            </div>
                            <div class="position-pnl {{ 'profit' if pos.pnl_usd >= 0 else 'loss' }}">
                                {{ pos.pnl_percent|round(2) }}% ({{ '$%.2f'|format(pos.pnl_usd) }})
                            </div>
                        </div>
                        <div class="position-details">
                            Quantity: {{ '%.8f'|format(pos.quantity) }}<br>
                            Entry: ${{ '%.4f'|format(pos.entry_price) }} → Current: ${{ '%.4f'|format(pos.current_price) }}<br>
                            Value: ${{ '$%.2f'|format(pos.quantity * pos.current_price) }}
                        </div>
                    </div>
                    {% endfor %}
                    {% if total_positions > 4 %}
                    <div class="scroll-indicator">
                        ↕ Scroll para ver todas las {{ total_positions }} posiciones
                    </div>
                    {% endif %}
                </div>
            </div>
            
            <div>
                <h2>[ACTIVITY] Recent Activity</h2>
                <div class="logs">
                    {% for log_line in recent_logs %}
                    <div>{{ log_line }}</div>
                    {% endfor %}
                </div>
            </div>
        </div>
        
        <div style="margin-top: 30px;">
            <h2>[LOGS] Log Files</h2>
            <div style="display: flex; flex-wrap: wrap; gap: 10px;">
                {% for log_file in log_files %}
                <a href="/logs/{{ log_file }}" target="_blank" style="color: #4CAF50; text-decoration: none; background: #2d2d2d; padding: 8px 12px; border-radius: 5px;">
                    {{ log_file }}
                </a>
                {% endfor %}
            </div>
        </div>
    </div>
</body>
</html>
"""

@app.route('/')
def dashboard():
    try:
        # Read status file
        status = {'running': False, 'positions': {}, 'total_pnl': 0, 'uptime_hours': 0}
        if os.path.exists('web/status.json'):
            with open('web/status.json', 'r') as f:
                status = json.load(f)
        
        # Read recent logs
        recent_logs = []
        today = datetime.now().strftime("%Y%m%d")
        trade_log_file = f'logs/trades_{today}.log'
        if os.path.exists(trade_log_file):
            with open(trade_log_file, 'r') as f:
                lines = f.readlines()
                recent_logs = [line.strip() for line in lines[-20:]]  # Last 20 lines
        
        # Get log files
        log_files = [os.path.basename(f) for f in glob.glob('logs/*.log')]
        log_files.sort(reverse=True)
        
        # Prepare template variables
        template_vars = {
            'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'uptime_hours': f"{status.get('uptime_hours', 0):.1f}",
            'total_positions': len(status.get('positions', {})),
            'total_pnl': f"{status.get('total_pnl', 0):.2f}",
            'running_status': 'ONLINE' if status.get('running', False) else 'OFFLINE',
            'status_class': 'status-box' if status.get('running', False) else 'status-box error',
            'pnl_class': 'profit' if status.get('total_pnl', 0) >= 0 else 'loss',
            'positions': status.get('positions', {}),
            'recent_logs': recent_logs,
            'log_files': log_files
        }
        
        return render_template_string(DASHBOARD_HTML, **template_vars)
        
    except Exception as e:
        return f"<h1>Error loading dashboard: {e}</h1>", 500

@app.route('/api/status')
def api_status():
    """API endpoint for status data"""
    try:
        if os.path.exists('web/status.json'):
            with open('web/status.json', 'r') as f:
                return jsonify(json.load(f))
        else:
            return jsonify({'error': 'Status file not found'})
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/logs/<filename>')
def serve_logs(filename):
    """Serve log files"""
    return send_from_directory('logs', filename)

def run_web_server():
    """Run the web server"""
    print("[WEB] Starting web monitor on http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)

if __name__ == "__main__":
    run_web_server()