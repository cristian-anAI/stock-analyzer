# Backtest Data Issues & Solutions

## 🔴 CRITICAL ISSUES FOUND

### 1. SPX/NDX Data Duplication Bug

**Status**: CONFIRMED
**Impact**: HIGH - All ML training data is invalid

**Problem**:
- SPX and NDX backtests show identical trades on all dates
- Oct 3, 2025: Both show Entry=6789.25, Stop=6766.50, P&L=-23.75
- This is IMPOSSIBLE - SPX ~6,800 and NDX ~25,000 are completely different price levels

**Root Cause**:
yfinance downloads CORRECT data:
- ES=F (SPX): 6771.0 ✓
- NQ=F (NDX): 25074.5 ✓

BUT the backtester processes them incorrectly, likely due to:
1. Cache file corruption/confusion
2. MultiIndex column handling in data_loader.py
3. Shared state between parallel backtest workers

**Evidence**:
```
# Fresh yfinance download (CORRECT)
SPX: 6771.0
NDX: 25074.5

# Backtest output (WRONG - both identical)
SPX: LONG Entry: 6789.25 Stop: 6766.50 P&L: -23.75
NDX: LONG Entry: 6789.25 Stop: 6766.50 P&L: -23.75
```

**Impact on ML**:
- All 61 trades used for training are potentially duplicated
- ML model learned from corrupted data
- Predictions on SPX/NDX are unreliable
- Claimed 68.3% win rate improvement is based on duplicate data

---

### 2. yfinance Historical Data Limitation

**Status**: KNOWN LIMITATION
**Impact**: MEDIUM - Limited training data

**Problem**:
- yfinance only provides ~60 days of 5-minute intraday data
- Current backtest: Aug 6 - Oct 5, 2025 (60 days)
- ML needs 300-500+ trades for optimal training
- Current dataset: only 61 trades total

**Solutions**:

#### Option A: Free/Low-Cost (Recommended for now)
1. **Polygon.io** - $200/month
   - Full historical intraday data
   - Professional-grade quality
   - Easy API integration

2. **Alpha Vantage** - Free tier available
   - 500 requests/day on free tier
   - Decent 5min historical data
   - Would need batching

3. **Interactive Brokers API** - Free if you have IB account
   - Excellent data quality
   - Requires active IB account
   - Complex API

#### Option B: Commercial (Professional)
4. **FirstRate Data** - One-time purchase
   - Buy specific historical periods
   - Very high quality
   - Expensive ($100-500+ per market)

5. **QuantConnect** - Cloud platform
   - Includes data + backtesting
   - $20-200/month depending on features

---

## ✅ IMMEDIATE ACTION ITEMS

### Priority 1: Fix Data Duplication Bug

1. **Identify exact cause**:
   - [ ] Check if cache files are being shared between SPX/NDX
   - [ ] Verify MultiIndex column handling
   - [ ] Test ThreadPoolExecutor state sharing

2. **Fix implementation**:
   - [ ] Ensure each market downloads to separate cache
   - [ ] Fix MultiIndex handling in data_loader.py
   - [ ] Add validation to detect identical trades

3. **Re-run backtest**:
   - [ ] Clear ALL cache files
   - [ ] Run SPX and NDX sequentially (not parallel) for testing
   - [ ] Verify Oct 3 trades are DIFFERENT

### Priority 2: Validate ML Training Data

1. **Once backtest is fixed**:
   - [ ] Re-extract features from corrected backtest
   - [ ] Verify SPX and NDX trades are independent
   - [ ] Re-train all ML models
   - [ ] Re-evaluate model performance

### Priority 3: Extend Historical Data (Future Enhancement)

1. **Evaluate data providers** (can wait until bug is fixed)
2. **Implement adapter for chosen provider**
3. **Re-train with 6-12 months of data**

---

## 📊 CURRENT STATE

### Backtest Results (Aug 6 - Oct 5, 2025)
```
SPX: 20 trades, 40% win rate, -8.23% return
NDX: 20 trades, 40% win rate, -10.41% return
```

**WARNING**: These results are IDENTICAL (Profit Factor: 0.78, Sharpe: -4.16)
This is statistically IMPOSSIBLE for two different indices.

### ML Training Data
```
Total trades: 61
Markets: 7 (FTSE, DAX, STOXX, CAC, NKY, ASX, IBEX, HSI, SPX, NDX)
Features: 48 (including new rsi_divergence_5min)
```

**WARNING**: Unknown how many trades are duplicated.

---

## 🔧 NEW FEATURES ADDED

### RSI Divergence Indicator

**Status**: ✅ IMPLEMENTED
**Feature**: `rsi_divergence_5min`
**Values**:
- `-1.0` = Bearish divergence (price up, RSI down)
- `0.0` = No divergence
- `+1.0` = Bullish divergence (price down, RSI up)

**Detection Logic**:
- Lookback: 20 periods (5min candles)
- RSI window: 14 periods
- Compares price peaks/troughs vs RSI peaks/troughs
- Identifies classic divergence patterns

**Integration**:
- Added to `TradeFeatures` dataclass
- Calculated in `FeatureEngineer._detect_rsi_divergence()`
- Included in all ML model training
- Total features now: 48 (was 47)

---

## 📝 NEXT STEPS

1. **URGENT**: Fix SPX/NDX data duplication
   - This invalidates all current ML results
   - Must be fixed before ANY further ML work

2. **RE-TRAIN**: Once data is fixed
   - Re-run backtest with verified independent data
   - Re-extract features
   - Re-train all models
   - Re-analyze predictions

3. **VALIDATE**: Verify improvements
   - Confirm Oct 3 SPX was LONG→SL (as you remember)
   - Confirm Oct 3 NDX was SHORT→TP1 (as you remember)
   - Analyze what ML would have predicted on REAL data

4. **FUTURE**: Extend historical data
   - Once bugs are fixed and ML is working
   - Evaluate data providers
   - Implement chosen provider
   - Re-train with 6-12 months of data

---

## ⚠️ USER NOTES

Tu memoria es correcta:
- NDX Oct 3: SHORT → TP1 (WIN) ✓
- SPX Oct 3: LONG → SL (LOSS) ✓

Los datos actuales muestran ambos como LONG con el mismo entry (6789.25), lo cual es IMPOSIBLE ya que:
- SPX (S&P 500): ~6,800 puntos ✓
- NDX (NASDAQ-100): ~25,000 puntos ✗

Esto confirma que el backtest tiene datos corruptos/duplicados.

---

**Created**: 2025-10-05
**Last Updated**: 2025-10-05 23:10 UTC
**Status**: CRITICAL BUGS - DO NOT USE CURRENT ML RESULTS
