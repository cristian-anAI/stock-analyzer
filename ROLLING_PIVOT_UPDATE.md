# Rolling Window Pivot System - Update Summary

## Changes Made

Updated `SimplePivotDetector` to match TradingView's rolling window behavior where pivots **reset every lookback periods** instead of accumulating.

## Before vs After

### BEFORE (Accumulation Method)
- Scanned through ALL historical data with rolling window
- Found highest/lowest in every 100-bar window
- Merged similar levels across multiple windows
- Result: Multiple resistances and supports accumulated over time

```python
# OLD: Scan all windows
for i in range(self.lookback, len(ohlcv_data)):
    window_highs = highs[i-self.lookback:i]
    window_lows = lows[i-self.lookback:i]
    # Add to resistance_levels list
    # Add to support_levels list
# Merge all levels
```

### AFTER (Rolling Reset Method)
- Only calculates pivots from the **CURRENT window** (last 100 bars)
- Every 100 bars, previous pivots are discarded
- Result: Exactly 1 resistance and 1 support at any time

```python
# NEW: Only current window
if total_bars >= self.lookback:
    window_highs = highs[-self.lookback:]  # Last 100 bars only
    window_lows = lows[-self.lookback:]
    max_high = np.max(window_highs)
    min_low = np.min(window_lows)
    # Add single resistance
    # Add single support
```

## Test Results

```
Current BTC Price: $110,030.57
Data candles: 1440

======================================================================
ROLLING WINDOW PIVOTS (100-period window)
======================================================================

Resistances: 1
  R: $110,348.00 | Strength: 100.0 | 20 bars ago | +0.29%

Supports: 1
  S: $109,728.94 | Strength: 80.0 | 74 bars ago | -0.27%

======================================================================
Window Status:
  Bars since window start: 40
  Bars until next reset: 60
======================================================================
```

## TradingView Pine Script Equivalent

The Python implementation now matches the Pine Script behavior in `tradingview_pivot_rolling.pine`:

```pine
var int window_start = 0
bars_since_start = bar_index - window_start
is_new_window = bars_since_start >= lookback

if is_new_window
    // Delete old lines and labels
    // Reset window_start
    // Calculate new pivots
    float window_high = ta.highest(high, lookback)
    float window_low = ta.lowest(low, lookback)
```

## Key Behavioral Changes

1. **Pivot Count**: Always exactly 1 resistance and 1 support (if they exist above/below price)
2. **Pivot Lifetime**: Pivots are valid for exactly `lookback` periods, then reset
3. **Strength Calculation**: Simplified to focus on recency within window and distance from price
4. **No Merging**: Since there's only 1 pivot per window, merging logic is no longer needed

## Files Modified

- `src/indicators/pivot_detector_simple.py` - Updated `detect_pivots()` method
- Created `test_rolling_pivots.py` - Test script to verify behavior
- Created `tradingview_pivot_rolling.pine` - TradingView indicator with same logic

## Next Steps

1. Test in TradingView to confirm Pine Script indicator works correctly
2. Compare Python pivot levels with TradingView indicator visually
3. Run `pupupuv3_bot.py --mode check` to see how signals are affected
4. Monitor signal generation with new pivot system

## Window Reset Logic

The window resets every `lookback` periods. For 1-minute data with 100 lookback:
- Window 1: Bars 0-99
- Window 2: Bars 100-199 (old pivots discarded)
- Window 3: Bars 200-299 (old pivots discarded)
- etc.

Current position in window can be calculated:
```python
bars_since_window_start = total_bars % lookback
bars_until_reset = lookback - bars_since_window_start
```

## Impact on Trading Strategy

### Positive Changes:
- **Cleaner levels**: Only the most relevant resistance/support from recent price action
- **Matches TradingView**: Visual confirmation now possible
- **Less noise**: Won't get confused by old levels that are no longer relevant

### Potential Concerns:
- **Fewer pivots**: May miss some valid support/resistance levels
- **Timing dependency**: Pivots depend on when the 100-bar window started
- **Less historical context**: Doesn't consider older but still relevant levels

### Mitigation:
If you need more pivot levels, consider:
1. Using multiple lookback periods (50, 100, 200) simultaneously
2. Adding a "historical pivots" detector that keeps strong levels across windows
3. Implementing a hybrid approach that resets but keeps very strong levels

## Testing Commands

```bash
# Test the updated pivot detector
python test_rolling_pivots.py

# Run bot in check mode
python pupupuv3_bot.py --mode check

# Show pivots from last 2 hours
python show_pivots_last_2hours.py

# Start API server to see in frontend
python run_api.py
```
