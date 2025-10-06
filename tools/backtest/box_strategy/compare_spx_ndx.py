"""Compare SPX vs NDX trade data to identify duplicates"""
import json

# Load data
with open(r'C:\repos\stock-analyzer\tools\backtest\box_strategy\tools\backtest\box_strategy\results\multi_market_results_20251005_173628.json', 'r') as f:
    data = json.load(f)

print('='*80)
print('COMPARING SPX vs NDX TRADES')
print('='*80)
print()

# Get all trades
spx_trades = data['SPX']['trades']
ndx_trades = data['NDX']['trades']

print(f'SPX: {len(spx_trades)} trades')
print(f'NDX: {len(ndx_trades)} trades')
print()

# Compare each date
print('TRADE BY TRADE COMPARISON:')
print('-'*80)

identical_count = 0
different_count = 0

for spx_trade in spx_trades:
    date = spx_trade['date']

    # Find matching NDX trade
    ndx_trade = next((t for t in ndx_trades if t['date'] == date), None)

    if ndx_trade:
        # Check if identical
        same_direction = spx_trade['direction'] == ndx_trade['direction']
        same_entry = abs(spx_trade['entry_price'] - ndx_trade['entry_price']) < 0.01
        same_stop = abs(spx_trade['stop_loss'] - ndx_trade['stop_loss']) < 0.01
        same_pnl = abs(spx_trade['pnl_points'] - ndx_trade['pnl_points']) < 0.01

        is_identical = same_direction and same_entry and same_stop and same_pnl

        if is_identical:
            identical_count += 1
            status = '[IDENTICAL - BUG!]'
        else:
            different_count += 1
            status = '[DIFFERENT - OK]'

        print(f'{date} {status}')
        print(f'  SPX: {spx_trade["direction"]:5s} Entry:{spx_trade["entry_price"]:8.2f} Stop:{spx_trade["stop_loss"]:8.2f} P&L:{spx_trade["pnl_points"]:+7.2f} {spx_trade["status"]}')
        print(f'  NDX: {ndx_trade["direction"]:5s} Entry:{ndx_trade["entry_price"]:8.2f} Stop:{ndx_trade["stop_loss"]:8.2f} P&L:{ndx_trade["pnl_points"]:+7.2f} {ndx_trade["status"]}')
        print()

print('='*80)
print('SUMMARY')
print('='*80)
print(f'Identical trades (DATA BUG): {identical_count}/{len(spx_trades)}')
print(f'Different trades (CORRECT):  {different_count}/{len(spx_trades)}')
print()

if identical_count > 0:
    print('[CRITICAL] SPX and NDX have duplicate data!')
    print('This indicates a bug in the backtest data collection.')
    print('SPX and NDX should have independent trade signals.')
else:
    print('[OK] All trades are independent.')
