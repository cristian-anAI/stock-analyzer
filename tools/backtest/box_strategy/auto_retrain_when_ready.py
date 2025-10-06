"""
Auto-monitor backtest and re-train ML when ready
"""
import subprocess
import time
import json
from pathlib import Path
import sys

print("="*80)
print("AUTO-MONITOR: BACKTEST -> ML TRAINING")
print("="*80)

# Step 1: Wait for backtest to complete
print("\n[1/4] Monitoring backtest completion...")
print("Checking every 30 seconds...")

max_wait_minutes = 30
checks = 0
max_checks = max_wait_minutes * 2  # 30 sec intervals

while checks < max_checks:
    # Check for latest results file
    results_dir = Path("results")
    if results_dir.exists():
        json_files = sorted(results_dir.glob("multi_market_results_*.json"), key=lambda x: x.stat().st_mtime)

        if json_files:
            latest_file = json_files[-1]
            file_age_seconds = time.time() - latest_file.stat().st_mtime

            # If file was modified in last 2 minutes, might still be writing
            if file_age_seconds > 120:
                print(f"\n[OK] Found completed backtest: {latest_file.name}")
                print(f"     File age: {file_age_seconds/60:.1f} minutes")
                break

    checks += 1
    elapsed_min = (checks * 30) / 60
    print(f"  Check {checks}/{max_checks} - Elapsed: {elapsed_min:.1f} min", end='\r')
    time.sleep(30)
else:
    print(f"\n[TIMEOUT] Backtest didn't complete in {max_wait_minutes} minutes")
    print("You can run ML training manually when backtest finishes:")
    print(f"  python ml/train_models.py --data results/multi_market_results_*.json --version 1")
    sys.exit(1)

# Step 2: Verify results
print("\n[2/4] Verifying results...")

with open(latest_file, 'r') as f:
    results = json.load(f)

# Check SPX and NDX exist and are different
if 'SPX' not in results or 'NDX' not in results:
    print("[ERROR] Missing SPX or NDX data")
    sys.exit(1)

spx_trades = results['SPX'].get('trades', [])
ndx_trades = results['NDX'].get('trades', [])

if not spx_trades or not ndx_trades:
    print("[ERROR] No trades found for SPX or NDX")
    sys.exit(1)

# Compare first trades
spx_first = spx_trades[0]['entry_price']
ndx_first = ndx_trades[0]['entry_price']

if abs(spx_first - ndx_first) < 100:
    print(f"[ERROR] SPX and NDX still too similar!")
    print(f"  SPX first entry: {spx_first:.2f}")
    print(f"  NDX first entry: {ndx_first:.2f}")
    sys.exit(1)

print(f"[OK] Data verification passed:")
print(f"  SPX trades: {len(spx_trades)}, first entry: {spx_first:.2f}")
print(f"  NDX trades: {len(ndx_trades)}, first entry: {ndx_first:.2f}")
print(f"  Difference: {abs(spx_first - ndx_first):.2f} points")

# Step 3: Count total trades across all markets
total_trades = 0
markets_with_trades = []
for market, data in results.items():
    trades = data.get('trades', [])
    if trades:
        total_trades += len(trades)
        markets_with_trades.append(market)

print(f"\n[OK] Total dataset:")
print(f"  Markets: {len(markets_with_trades)} ({', '.join(markets_with_trades)})")
print(f"  Total trades: {total_trades}")

if total_trades < 30:
    print(f"[WARNING] Only {total_trades} trades - ML may underperform")
    print("Consider collecting more data for better results")

# Step 4: Launch ML training
print("\n[3/4] Launching ML training...")
print(f"Training with: {latest_file.name}")
print("Models: Random Forest, XGBoost")
print("Features: 48 (including rsi_divergence_5min)")

cmd = [
    sys.executable,  # Current Python interpreter
    "ml/train_models.py",
    "--data", str(latest_file),
    "--version", "1",
    "--models", "random_forest", "xgboost"
]

print(f"\nCommand: {' '.join(cmd)}")
print("\n" + "="*80)
print("STARTING ML TRAINING...")
print("="*80 + "\n")

result = subprocess.run(cmd, cwd=Path.cwd())

# Step 5: Summary
print("\n" + "="*80)
if result.returncode == 0:
    print("SUCCESS - ML TRAINING COMPLETE!")
    print("="*80)
    print(f"\nBacktest data: {latest_file}")
    print(f"Models saved in: models/")
    print(f"Results saved in: ml_results/")
    print(f"\nNext steps:")
    print(f"  1. Review training report in ml_results/")
    print(f"  2. Run: python analyze_ml_on_real_trades.py")
    print(f"  3. Analyze Oct 3 predictions for SPX/NDX")
else:
    print("ERROR - ML TRAINING FAILED!")
    print("="*80)
    print(f"Exit code: {result.returncode}")
    print(f"Check logs above for errors")
