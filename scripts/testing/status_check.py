#!/usr/bin/env python3
import requests
import json

try:
    response = requests.get('http://localhost:5000/api/status')
    data = response.json()
    
    print('=== ESTADO ACTUAL DEL SERVIDOR ===')
    print(f'[STATUS] Status: {"ONLINE" if data.get("running", False) else "OFFLINE"}')
    print(f'[TIME] Uptime: {data.get("uptime_hours", 0):.1f} horas')
    print(f'[PORTFOLIO] Posiciones: {len(data.get("positions", {}))}')
    print(f'[P&L] P&L Total: ${data.get("total_pnl", 0):.2f}')
    print()
    print('[POSITIONS] POSICIONES:')
    for symbol, pos in data.get('positions', {}).items():
        status_icon = '[MANUAL]' if pos['type'] == 'MANUAL' else '[AUTO]'
        pnl_icon = '[UP]' if pos['pnl_usd'] >= 0 else '[DOWN]'
        print(f'{status_icon} {symbol}: {pnl_icon} {pos["pnl_percent"]:+.2f}% (${pos["pnl_usd"]:+.2f})')
        print(f'    {pos["quantity"]:.8f} @ ${pos["entry_price"]:.4f} -> ${pos["current_price"]:.4f}')
        print()

except Exception as e:
    print(f'Error: {e}')