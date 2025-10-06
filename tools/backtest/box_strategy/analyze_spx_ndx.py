"""
Analyze ML predictions for SPX and NDX trades specifically
"""

import json
from ml.ml_predictor import MLPredictor

# Load backtest data
with open('tools/backtest/box_strategy/results/multi_market_results_20251005_173628.json', 'r') as f:
    backtest_data = json.load(f)

# Load ML predictor
predictor = MLPredictor(version='1', model_name='random_forest')

print('='*80)
print('ANALISIS ML DETALLADO: SPX Y NDX')
print('='*80)
print('')

# Analyze SPX and NDX
for market in ['SPX', 'NDX']:
    if market not in backtest_data or 'trades' not in backtest_data[market]:
        continue

    result = backtest_data[market]
    trades = result['trades']

    market_name = result.get('name', market)

    print('')
    print('='*80)
    print(f'{market} - {market_name}')
    print('='*80)
    print(f'Total trades: {len(trades)}')
    print(f'Periodo: {trades[0]["date"]} hasta {trades[-1]["date"]}')
    print('')

    # Analyze each trade
    for i, trade in enumerate(trades, 1):
        setup = {
            'market': market,
            'box_high': trade['box_high'],
            'box_low': trade['box_low'],
            'box_range': trade['box_range'],
            'direction': trade['direction'],
            'entry_price': trade['entry_price'],
            'stop_loss': trade['stop_loss'],
            'risk_points': trade['risk_points'],
            'entry_time': trade['entry_time']
        }

        # ML prediction
        ml_result = predictor.evaluate_setup(setup)
        pred = ml_result['prediction']

        # Real outcome
        real_pnl = trade['pnl_points']
        real_outcome = 'WIN' if real_pnl > 0 else 'LOSS'
        outcome_icon = '[WIN]' if real_pnl > 0 else '[LOSS]'

        # ML decision
        ml_decision = 'TRADE' if ml_result['should_trade'] else 'SKIP'

        # Evaluation
        if ml_result['should_trade'] and real_outcome == 'WIN':
            evaluation = 'ACIERTO - acepto un WIN'
        elif ml_result['should_trade'] and real_outcome == 'LOSS':
            evaluation = 'ERROR - acepto un LOSS'
        elif not ml_result['should_trade'] and real_outcome == 'LOSS':
            evaluation = 'ACIERTO - evito un LOSS'
        else:
            evaluation = 'ERROR - rechazo un WIN'

        print(f'{"="*80}')
        print(f'TRADE #{i} - {trade["date"]} - {outcome_icon} {real_outcome}')
        print(f'{"="*80}')
        print(f'SETUP:')
        print(f'  Box High:   ${trade["box_high"]:.2f}')
        print(f'  Box Low:    ${trade["box_low"]:.2f}')
        print(f'  Box Range:  {trade["box_range"]:.1f} puntos')
        print(f'  Direction:  {trade["direction"]}')
        print(f'  Entry:      ${trade["entry_price"]:.2f}')
        print(f'  Stop Loss:  ${trade["stop_loss"]:.2f}')
        print(f'  Risk:       {trade["risk_points"]:.1f} puntos')
        print(f'')
        print(f'PREDICCION ML:')
        print(f'  Win Probability:    {pred["win_probability"]*100:.1f}%')
        print(f'  Confidence Level:   {pred["confidence_level"]}')
        print(f'  Recommendation:     {pred["recommendation"]}')
        print(f'  Position Size:      {pred["position_size_multiplier"]*100:.0f}%')
        print(f'  Decision ML:        {ml_decision}')
        print(f'')
        print(f'RESULTADO REAL:')
        print(f'  P&L:        {real_pnl:+.2f} puntos')
        print(f'  Status:     {trade["status"]}')
        print(f'  Holding:    {trade["holding_time_minutes"]:.0f} minutos')
        if trade['partial_exits']:
            print(f'  Partials:   {len(trade["partial_exits"])} exits')
        print(f'')
        print(f'EVALUACION ML: {evaluation}')
        print('')

    # Summary
    all_outcomes = [trade['pnl_points'] > 0 for trade in trades]
    baseline_wr = sum(all_outcomes) / len(all_outcomes) * 100

    total_pnl = sum(trade['pnl_points'] for trade in trades)

    # ML filtered trades
    accepted_count = 0
    accepted_wins = 0
    accepted_pnl = 0

    for trade in trades:
        setup = {
            'market': market,
            'box_high': trade['box_high'],
            'box_low': trade['box_low'],
            'box_range': trade['box_range'],
            'direction': trade['direction'],
            'entry_price': trade['entry_price'],
            'stop_loss': trade['stop_loss'],
            'risk_points': trade['risk_points'],
            'entry_time': trade['entry_time']
        }
        ml_result = predictor.evaluate_setup(setup)
        if ml_result['should_trade']:
            accepted_count += 1
            accepted_pnl += trade['pnl_points']
            if trade['pnl_points'] > 0:
                accepted_wins += 1

    ml_wr = (accepted_wins / accepted_count * 100) if accepted_count > 0 else 0

    print('='*80)
    print(f'RESUMEN FINAL - {market}')
    print('='*80)
    print(f'SIN ML:')
    print(f'  Trades:     {len(trades)}')
    print(f'  Win Rate:   {baseline_wr:.1f}%')
    print(f'  Total P&L:  {total_pnl:+.2f} puntos')
    print(f'')
    print(f'CON ML (trades aceptados):')
    print(f'  Trades:     {accepted_count}/{len(trades)}')
    print(f'  Win Rate:   {ml_wr:.1f}%')
    print(f'  Total P&L:  {accepted_pnl:+.2f} puntos')
    print(f'')
    print(f'MEJORA:')
    print(f'  Win Rate:   {ml_wr - baseline_wr:+.1f} puntos')
    print(f'  Precision:  {(accepted_count/len(trades)*100):.1f}% de trades filtrados')
    print('')
    print('')
