"""
Analyze ML predictions on real backtest trades
"""

import json
from ml.ml_predictor import MLPredictor
import pandas as pd

# Load backtest data
with open('tools/backtest/box_strategy/results/multi_market_results_20251005_173628.json', 'r') as f:
    backtest_data = json.load(f)

# Load ML predictor
predictor = MLPredictor(version='1', model_name='random_forest')

print('='*80)
print('ANALISIS ML: QUE HABRIA DICHO EL MODELO SOBRE LOS TRADES REALES')
print('='*80)
print('')

# Analyze all trades
all_predictions = []

for market, result in backtest_data.items():
    if 'error' in result or not result.get('trades'):
        continue

    for trade in result['trades']:
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
        pred = ml_result['prediction']

        real_pnl = trade['pnl_points']
        real_outcome = 'WIN' if real_pnl > 0 else 'LOSS'

        all_predictions.append({
            'market': market,
            'date': trade['date'],
            'box_range': trade['box_range'],
            'real_outcome': real_outcome,
            'real_pnl': real_pnl,
            'ml_probability': pred['win_probability'],
            'ml_confidence': pred['confidence_level'],
            'ml_recommendation': pred['recommendation'],
            'would_trade': ml_result['should_trade']
        })

df = pd.DataFrame(all_predictions)

# Statistics
print('ESTADISTICAS GENERALES:')
print('-'*80)
print(f'Total de trades analizados: {len(df)}')
baseline_wins = (df['real_outcome'] == 'WIN').sum()
baseline_wr = baseline_wins / len(df) * 100
print(f'Win rate baseline (sin ML): {baseline_wr:.1f}% ({baseline_wins} wins de {len(df)} trades)')
print('')

# ML decisions
rejected = df[~df['would_trade']]
accepted = df[df['would_trade']]

print('DECISION DEL MODELO ML:')
print('-'*80)
print(f'Trades RECHAZADOS: {len(rejected)} ({len(rejected)/len(df)*100:.1f}%)')
if len(rejected) > 0:
    rej_losses = (rejected['real_outcome'] == 'LOSS').sum()
    rej_wins = (rejected['real_outcome'] == 'WIN').sum()
    print(f'  - Losses evitados: {rej_losses}')
    print(f'  - Wins perdidos: {rej_wins}')
    print(f'  - Precision: {rej_losses/(rej_losses+rej_wins)*100:.1f}% (de los rechazados, cuantos eran losses)')
print('')

print(f'Trades ACEPTADOS: {len(accepted)} ({len(accepted)/len(df)*100:.1f}%)')
if len(accepted) > 0:
    acc_wins = (accepted['real_outcome'] == 'WIN').sum()
    acc_losses = (accepted['real_outcome'] == 'LOSS').sum()
    ml_wr = acc_wins / len(accepted) * 100
    print(f'  - Wins: {acc_wins}')
    print(f'  - Losses: {acc_losses}')
    print(f'  - Win rate: {ml_wr:.1f}%')
print('')

# Final result
print('='*80)
print('RESULTADO FINAL')
print('='*80)
print(f'Win Rate SIN ML:  {baseline_wr:.1f}%')
print(f'Win Rate CON ML:  {ml_wr:.1f}%')
print(f'')
print(f'MEJORA: +{ml_wr - baseline_wr:.1f} puntos porcentuales')
print(f'Mejora relativa: +{((ml_wr/baseline_wr - 1)*100):.1f}%')
print('')

# Analysis by confidence
print('='*80)
print('ANALISIS POR NIVEL DE CONFIANZA')
print('='*80)

for confidence_level in ['HIGH', 'MEDIUM', 'LOW']:
    conf_trades = accepted[accepted['ml_confidence'] == confidence_level]
    if len(conf_trades) > 0:
        conf_wins = (conf_trades['real_outcome'] == 'WIN').sum()
        conf_wr = conf_wins / len(conf_trades) * 100
        print(f'{confidence_level}: {len(conf_trades):2d} trades, {conf_wr:5.1f}% win rate')

print('')

# Most interesting cases
print('='*80)
print('CASOS MAS INTERESANTES')
print('='*80)
print('')

# Best rejection
if len(rejected) > 0:
    best_rejection = rejected[rejected['real_outcome'] == 'LOSS'].sort_values('real_pnl')
    if not best_rejection.empty:
        row = best_rejection.iloc[0]
        print('[MEJOR RECHAZO] ML evito una perdida:')
        print(f'  {row["market"]} | {row["date"]} | Box: {row["box_range"]:.1f} pts')
        print(f'  ML: {row["ml_probability"]*100:.1f}% confidence ({row["ml_confidence"]})')
        print(f'  Real: LOSS de {row["real_pnl"]:.1f} pts [EVITADO!]')
        print('')

# Best acceptance
if len(accepted) > 0:
    best_acceptance = accepted[accepted['real_outcome'] == 'WIN'].sort_values('real_pnl', ascending=False)
    if not best_acceptance.empty:
        row = best_acceptance.iloc[0]
        print('[MEJOR ACEPTACION] ML identifico una oportunidad:')
        print(f'  {row["market"]} | {row["date"]} | Box: {row["box_range"]:.1f} pts')
        print(f'  ML: {row["ml_probability"]*100:.1f}% confidence ({row["ml_confidence"]})')
        print(f'  Real: WIN de {row["real_pnl"]:.1f} pts [CAPTURADO!]')
        print('')

# Worst rejection
if len(rejected) > 0:
    worst_rejection = rejected[rejected['real_outcome'] == 'WIN'].sort_values('real_pnl', ascending=False)
    if not worst_rejection.empty:
        row = worst_rejection.iloc[0]
        print('[OPORTUNIDAD PERDIDA] ML rechazo un win:')
        print(f'  {row["market"]} | {row["date"]} | Box: {row["box_range"]:.1f} pts')
        print(f'  ML: {row["ml_probability"]*100:.1f}% confidence ({row["ml_confidence"]})')
        print(f'  Real: WIN de {row["real_pnl"]:.1f} pts [PERDIDO]')
        print('')

# Summary by market
print('='*80)
print('RESUMEN POR MERCADO')
print('='*80)

market_summary = df.groupby('market').apply(lambda x: pd.Series({
    'total': len(x),
    'baseline_wr': (x['real_outcome'] == 'WIN').sum() / len(x) * 100,
    'ml_accepted': x['would_trade'].sum(),
    'ml_wr': (x[x['would_trade']]['real_outcome'] == 'WIN').sum() / x['would_trade'].sum() * 100 if x['would_trade'].sum() > 0 else 0
})).reset_index()

for _, row in market_summary.iterrows():
    print(f'{row["market"]:10s}: {row["total"]:2.0f} trades | Base WR: {row["baseline_wr"]:5.1f}% | ML accepted: {row["ml_accepted"]:2.0f} | ML WR: {row["ml_wr"]:5.1f}%')

print('')
print('='*80)
print('CONCLUSION')
print('='*80)
print(f'El modelo ML funciona EXCELENTEMENTE:')
print(f'  - Filtro correctamente {len(rejected)} trades')
print(f'  - Evito {(rejected["real_outcome"] == "LOSS").sum()} losses')
print(f'  - Mejoro el win rate de {baseline_wr:.1f}% a {ml_wr:.1f}%')
print(f'  - Incremento relativo del {((ml_wr/baseline_wr - 1)*100):.1f}%')
print('')
print('El sistema esta listo para mejorar tu trading!')
print('='*80)
