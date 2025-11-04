# Frontend Implementation Prompt - PupupuV3 Scalping Strategy

## Overview
Implement a complete dashboard for the PupupuV3 1-minute scalping strategy with ML-predicted dynamic take profits. The dashboard should be accessible as a new tab alongside the existing Box Strategy dashboard.

---

## 1. Architecture & Layout

### Tab Structure
```
Main Dashboard
├── Tab 1: "Box Strategy" (existing 5-min strategy)
└── Tab 2: "PupupuV3 Scalping" (NEW - 1-min strategy)
```

### API Base URL
```
http://localhost:8000/api/v1/pupupuv3
```

---

## 2. API Endpoints Reference

### 2.1 Current Analysis (Real-time)
**GET** `/current-analysis?symbol=BTC/USDT`

**Response**:
```json
{
  "symbol": "BTC/USDT",
  "timestamp": "2025-10-29T15:30:00Z",
  "current_price": 68500.50,
  "ema_15": 68450.20,
  "vwap": 68400.00,
  "active_resistances": [
    {"price": 68800.00, "type": "swing_high", "age_bars": 50},
    {"price": 69200.00, "type": "swing_high", "age_bars": 120}
  ],
  "active_supports": [
    {"price": 68200.00, "type": "swing_low", "age_bars": 45},
    {"price": 67900.00, "type": "swing_low", "age_bars": 80}
  ],
  "volume_profile": {
    "poc": 68350.00,
    "vah": 68700.00,
    "val": 68000.00,
    "lookback_days": 7
  },
  "signal": {
    "type": "LONG",
    "entry": 68520.00,
    "stop_loss": 68320.00,
    "tp1": 68720.00,
    "risk_amount": 600.00,
    "position_size": 0.0875,
    "conditions_met": {
      "touch": true,
      "ema_test": true,
      "vwap_alignment": true,
      "volume_profile_support": true
    }
  },
  "ml_prediction": {
    "tp2": {
      "ratio": 8.0,
      "price": 69120.00,
      "probability": 0.72,
      "timeframe": "2h",
      "exit_percentage": 30
    },
    "tp3": {
      "ratio": 14.0,
      "price": 70320.00,
      "probability": 0.51,
      "timeframe": "4h",
      "exit_percentage": 20
    },
    "confidence_score": 0.815,
    "model_version": "v1"
  }
}
```

### 2.2 Recent Signals
**GET** `/signals/recent?limit=50`

**Response**:
```json
{
  "signals": [
    {
      "id": 1234,
      "timestamp": "2025-10-29T14:25:00Z",
      "symbol": "BTC/USDT",
      "type": "LONG",
      "entry": 68200.00,
      "stop_loss": 68000.00,
      "tp1": 68400.00,
      "status": "closed",
      "outcome": "win",
      "pnl": 450.00
    }
  ],
  "total": 50
}
```

### 2.3 Active Trades
**GET** `/trades/active`

**Response**:
```json
{
  "active_trades": [
    {
      "id": 5678,
      "symbol": "BTC/USDT",
      "type": "SHORT",
      "entry": 68800.00,
      "current_price": 68650.00,
      "stop_loss": 69000.00,
      "tp1": 68600.00,
      "tp2": 68200.00,
      "tp3": 67400.00,
      "unrealized_pnl": 112.50,
      "position_remaining": 50,
      "status": "tp1_hit_at_be"
    }
  ]
}
```

### 2.4 Statistics
**GET** `/statistics?days=30`

**Response**:
```json
{
  "period_days": 30,
  "signals_total": 469,
  "signals_valid": 465,
  "trades_total": 465,
  "wins": 228,
  "losses": 237,
  "win_rate": 49.03,
  "total_pnl": 109980.00,
  "avg_win": 1108.68,
  "avg_loss": -627.42,
  "profit_factor": 1.77,
  "expectancy": 236.43,
  "no_test_count": 82,
  "max_drawdown": -4500.00
}
```

### 2.5 Backtest Results
**GET** `/backtest-results`

**Response**:
```json
{
  "comparison": {
    "phase1_tp1_only": {
      "total_pnl": -6000.00,
      "win_rate": 48.93,
      "avg_win": 600.00,
      "avg_loss": -600.00,
      "profit_factor": 0.96,
      "expectancy": -12.88
    },
    "phase3_ml_dynamic": {
      "total_pnl": 109980.00,
      "win_rate": 48.93,
      "avg_win": 1108.68,
      "avg_loss": -627.42,
      "profit_factor": 1.77,
      "expectancy": 236.01
    },
    "improvement": {
      "pnl_change": 115980.00,
      "pnl_percentage": 1933.0,
      "win_rate_change": 0.0,
      "avg_win_improvement": 84.78
    }
  },
  "test_period": "7 days",
  "symbol": "BTC/USDT",
  "total_signals": 469
}
```

### 2.6 System Status
**GET** `/status`

**Response**:
```json
{
  "status": "running",
  "ml_model_loaded": true,
  "ml_model_version": "v1",
  "last_analysis": "2025-10-29T15:30:00Z",
  "active_trades_count": 1,
  "data_cache_status": "healthy"
}
```

---

## 3. Component Structure

### 3.1 Main Dashboard Component
```typescript
interface PupupuV3DashboardProps {
  symbol: string;
  refreshInterval?: number; // default: 60000 (60s)
}

const PupupuV3Dashboard: React.FC<PupupuV3DashboardProps> = ({
  symbol = "BTC/USDT",
  refreshInterval = 60000
}) => {
  // State management
  const [currentAnalysis, setCurrentAnalysis] = useState<CurrentAnalysis | null>(null);
  const [statistics, setStatistics] = useState<Statistics | null>(null);
  const [backtestResults, setBacktestResults] = useState<BacktestComparison | null>(null);
  const [activeTrades, setActiveTrades] = useState<Trade[]>([]);
  const [recentSignals, setRecentSignals] = useState<Signal[]>([]);

  // Auto-refresh logic with useEffect

  return (
    <div className="pupupuv3-dashboard">
      <DashboardHeader status={systemStatus} />
      <div className="dashboard-grid">
        <CurrentSignalCard analysis={currentAnalysis} />
        <MLPredictionCard prediction={currentAnalysis?.ml_prediction} />
        <ActiveTradesPanel trades={activeTrades} />
        <StatisticsPanel stats={statistics} />
        <BacktestComparisonChart results={backtestResults} />
        <RecentSignalsTable signals={recentSignals} />
        <VolumeProfileChart volumeProfile={currentAnalysis?.volume_profile} />
        <PivotLevelsChart
          supports={currentAnalysis?.active_supports}
          resistances={currentAnalysis?.active_resistances}
          currentPrice={currentAnalysis?.current_price}
        />
      </div>
    </div>
  );
};
```

### 3.2 Current Signal Card
**Display**:
- Symbol name + current price
- Signal direction (LONG/SHORT) with color coding
- Entry price with horizontal line on mini chart
- Stop Loss (red line)
- TP1 (green line) - "50% exit + move to BE"
- TP2 (yellow line) - "30% exit" with ML ratio + probability
- TP3 (blue line) - "20% exit" with ML ratio + probability
- Risk amount ($600 or $300)
- All conditions met checkboxes (touch, EMA test, VWAP alignment, VP support)

**Visual Design**:
```
┌─────────────────────────────────────────┐
│ 🟢 LONG SIGNAL - BTC/USDT               │
│ Current: $68,520.00                     │
├─────────────────────────────────────────┤
│ Entry:     $68,520.00  ────────────────│
│ Stop Loss: $68,320.00  ────── (Red)    │
│ TP1:       $68,720.00  ────── (Green)  │
│   └─ 50% exit + BE                      │
│ TP2:       $69,120.00  ────── (Yellow) │
│   └─ 30% exit | R:R 8:1 | 72% prob | 2h│
│ TP3:       $70,320.00  ────── (Blue)   │
│   └─ 20% exit | R:R 14:1 | 51% prob |4h│
├─────────────────────────────────────────┤
│ Risk: $600 | Size: 0.0875 BTC          │
│ ML Confidence: 81.5% ████████░░         │
├─────────────────────────────────────────┤
│ Conditions:                             │
│ ✅ Pivot Touch                          │
│ ✅ EMA(15) Test                         │
│ ✅ VWAP Alignment                       │
│ ✅ Volume Profile Support               │
└─────────────────────────────────────────┘
```

### 3.3 ML Prediction Card
**Display**:
- Model version and confidence score
- Visual probability bars for TP2 and TP3
- Timeframe estimates
- Risk/Reward ratios
- Color coding: >70% (green), 60-70% (yellow), 45-60% (orange), <45% (red)

**Visual Design**:
```
┌─────────────────────────────────────────┐
│ 🤖 ML Dynamic Take Profits (v1)         │
│ Overall Confidence: 81.5%               │
├─────────────────────────────────────────┤
│ TP2 Prediction:                         │
│   Ratio: 8:1 ($69,120)                  │
│   Probability: 72% ███████▓░░ (2h)     │
│   Exit: 30% of position                 │
├─────────────────────────────────────────┤
│ TP3 Prediction:                         │
│   Ratio: 14:1 ($70,320)                 │
│   Probability: 51% █████░░░░░ (4h)     │
│   Exit: 20% of position                 │
├─────────────────────────────────────────┤
│ 📊 Probability Distribution (1h-8h):    │
│ [Interactive chart showing all ratios]  │
└─────────────────────────────────────────┘
```

### 3.4 Backtest Comparison Chart
**Display**:
- Side-by-side comparison: Phase 1 (TP1 only) vs Phase 3 (ML Dynamic)
- Metrics: Total PnL, Win Rate, Profit Factor, Expectancy, Avg Win/Loss
- Visual bars showing improvement percentage
- Highlight the +1,933% PnL improvement prominently

**Visual Design**:
```
┌────────────────────────────────────────────────────────────┐
│ 📈 Backtest Comparison (7 days, 469 signals)               │
├────────────────────────────────────────────────────────────┤
│                    Phase 1         Phase 3      Improvement│
│                   (TP1 Only)    (ML Dynamic)                │
├────────────────────────────────────────────────────────────┤
│ Total PnL      │  -$6,000      │ +$109,980   │ +1,933% 🚀 │
│ Win Rate       │   48.93%      │   48.93%    │     0%     │
│ Avg Win        │  $600.00      │ $1,108.68   │   +84.78%  │
│ Avg Loss       │ -$600.00      │  -$627.42   │    -4.57%  │
│ Profit Factor  │    0.96       │    1.77     │   +84.38%  │
│ Expectancy     │  -$12.88      │  +$236.01   │  +1,933%   │
└────────────────────────────────────────────────────────────┘

[Visual bar chart showing PnL comparison with dramatic growth]
```

### 3.5 Statistics Panel
**Display**:
- Period selector (7d, 30d, 90d, All)
- Total signals count
- Win/Loss breakdown with pie chart
- Total PnL with color (green/red)
- Average win vs average loss
- Max drawdown
- "No EMA Test" count (direct trades)

### 3.6 Active Trades Panel
**Display**:
- List of currently open positions
- Entry price, current price, unrealized PnL
- Progress indicators showing which TPs hit
- "At BE" badge when TP1 hit
- Percentage remaining (100% → 50% → 20% → 0%)

### 3.7 Recent Signals Table
**Display**:
- Last 50 signals in chronological order
- Columns: Timestamp, Type (L/S), Entry, SL, TP1, TP2, TP3, Outcome, PnL
- Filter by: All / Wins / Losses / Active
- Sort by: Time, PnL, R:R achieved

### 3.8 Volume Profile Chart
**Display**:
- 7-day Volume Profile histogram
- POC (Point of Control) line
- VAH (Value Area High) line
- VAL (Value Area Low) line
- Current price marker
- Entry/SL/TP levels overlaid

### 3.9 Pivot Levels Chart
**Display**:
- Mini price chart (last 200 candles)
- Active resistance levels (red dashed lines) with age
- Active support levels (green dashed lines) with age
- EMA(15) line (blue)
- VWAP line (purple)
- Current signal markers (entry arrow, SL, TPs)

---

## 4. TypeScript Interfaces

```typescript
interface CurrentAnalysis {
  symbol: string;
  timestamp: string;
  current_price: number;
  ema_15: number;
  vwap: number;
  active_resistances: PivotLevel[];
  active_supports: PivotLevel[];
  volume_profile: VolumeProfile;
  signal?: Signal;
  ml_prediction?: MLPrediction;
}

interface PivotLevel {
  price: number;
  type: "swing_high" | "swing_low";
  age_bars: number;
}

interface VolumeProfile {
  poc: number;
  vah: number;
  val: number;
  lookback_days: number;
}

interface Signal {
  type: "LONG" | "SHORT";
  entry: number;
  stop_loss: number;
  tp1: number;
  risk_amount: number;
  position_size: number;
  conditions_met: {
    touch: boolean;
    ema_test: boolean;
    vwap_alignment: boolean;
    volume_profile_support: boolean;
  };
}

interface MLPrediction {
  tp2: TPTarget;
  tp3: TPTarget;
  confidence_score: number;
  model_version: string;
}

interface TPTarget {
  ratio: number;
  price: number;
  probability: number;
  timeframe: string;
  exit_percentage: number;
}

interface Statistics {
  period_days: number;
  signals_total: number;
  signals_valid: number;
  trades_total: number;
  wins: number;
  losses: number;
  win_rate: number;
  total_pnl: number;
  avg_win: number;
  avg_loss: number;
  profit_factor: number;
  expectancy: number;
  no_test_count: number;
  max_drawdown: number;
}

interface BacktestComparison {
  comparison: {
    phase1_tp1_only: BacktestMetrics;
    phase3_ml_dynamic: BacktestMetrics;
    improvement: ImprovementMetrics;
  };
  test_period: string;
  symbol: string;
  total_signals: number;
}

interface BacktestMetrics {
  total_pnl: number;
  win_rate: number;
  avg_win: number;
  avg_loss: number;
  profit_factor: number;
  expectancy: number;
}

interface ImprovementMetrics {
  pnl_change: number;
  pnl_percentage: number;
  win_rate_change: number;
  avg_win_improvement: number;
}

interface Trade {
  id: number;
  symbol: string;
  type: "LONG" | "SHORT";
  entry: number;
  current_price: number;
  stop_loss: number;
  tp1: number;
  tp2?: number;
  tp3?: number;
  unrealized_pnl: number;
  position_remaining: number;
  status: string;
}
```

---

## 5. Data Fetching Strategy

### Polling Implementation
```typescript
const usePupupuV3Data = (symbol: string, refreshInterval: number = 60000) => {
  const [data, setData] = useState<CurrentAnalysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await fetch(
          `http://localhost:8000/api/v1/pupupuv3/current-analysis?symbol=${symbol}`
        );
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const result = await response.json();
        setData(result);
        setError(null);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchData(); // Initial fetch
    const interval = setInterval(fetchData, refreshInterval);

    return () => clearInterval(interval);
  }, [symbol, refreshInterval]);

  return { data, loading, error };
};
```

### Parallel Data Loading
```typescript
const useDashboardData = (symbol: string) => {
  const [allData, setAllData] = useState<DashboardData>({});

  useEffect(() => {
    const fetchAll = async () => {
      const [analysis, stats, backtest, trades, signals] = await Promise.all([
        fetch(`/api/v1/pupupuv3/current-analysis?symbol=${symbol}`).then(r => r.json()),
        fetch(`/api/v1/pupupuv3/statistics?days=30`).then(r => r.json()),
        fetch(`/api/v1/pupupuv3/backtest-results`).then(r => r.json()),
        fetch(`/api/v1/pupupuv3/trades/active`).then(r => r.json()),
        fetch(`/api/v1/pupupuv3/signals/recent?limit=50`).then(r => r.json())
      ]);

      setAllData({ analysis, stats, backtest, trades, signals });
    };

    fetchAll();
    const interval = setInterval(fetchAll, 60000);
    return () => clearInterval(interval);
  }, [symbol]);

  return allData;
};
```

---

## 6. UI/UX Guidelines

### Color Scheme
- **LONG signals**: Green (#10B981)
- **SHORT signals**: Red (#EF4444)
- **TP1**: Bright Green (#22C55E)
- **TP2**: Yellow/Gold (#F59E0B)
- **TP3**: Blue (#3B82F6)
- **Stop Loss**: Dark Red (#DC2626)
- **Profit**: Green background (#ECFDF5)
- **Loss**: Red background (#FEF2F2)
- **Neutral**: Gray (#6B7280)

### Icons
- 🟢 LONG signal active
- 🔴 SHORT signal active
- ⚪ No signal
- 🤖 ML prediction
- 📈 Backtest results
- 📊 Statistics
- 🎯 Active trade
- ✅ Condition met
- ❌ Condition not met
- 🚀 Major improvement indicator

### Responsive Design
- Desktop: 3-column grid layout
- Tablet: 2-column layout
- Mobile: Single column, stacked components

### Real-time Updates
- Use subtle animations when data updates
- Show "Last updated: X seconds ago" timestamp
- Pulse effect on active signals
- Toast notifications for new signals

---

## 7. Integration with Existing Dashboard

### Navigation Structure
```typescript
<Tabs defaultValue="box-strategy">
  <TabsList>
    <TabsTrigger value="box-strategy">
      📦 Box Strategy (5-min)
    </TabsTrigger>
    <TabsTrigger value="pupupuv3">
      ⚡ PupupuV3 Scalping (1-min)
    </TabsTrigger>
  </TabsList>

  <TabsContent value="box-strategy">
    <BoxStrategyDashboard /> {/* Existing component */}
  </TabsContent>

  <TabsContent value="pupupuv3">
    <PupupuV3Dashboard symbol="BTC/USDT" />
  </TabsContent>
</Tabs>
```

### Shared Components
- Header/Navigation bar
- Symbol selector
- Theme toggle (dark/light mode)
- Notification system
- WebSocket connection (if implemented)

---

## 8. Advanced Features (Optional Enhancements)

### 8.1 Multi-Symbol Support
- Add symbol selector dropdown (BTC/USDT, ETH/USDT, etc.)
- Multi-symbol grid view showing all active signals

### 8.2 Sound/Visual Alerts
- Play sound when new signal appears
- Browser notification API for new high-confidence signals (>80%)
- Flashing border on signal card when conditions just met

### 8.3 Trade Journal
- Click any signal to view detailed breakdown
- Add manual notes to trades
- Tag trades (e.g., "perfect setup", "against VWAP", etc.)

### 8.4 ML Model Insights
- Show feature importance chart
- Display all 19 ratio predictions in probability matrix
- Model performance over time

### 8.5 Real-time Chart Integration
- Embed TradingView chart with signal overlays
- Draw entry/SL/TP levels directly on chart
- Highlight EMA(15) and VWAP on chart

### 8.6 Export Functionality
- Export signals to CSV
- Generate PDF report of backtest results
- Share signal card as image

---

## 9. Testing Checklist

- [ ] All API endpoints return expected data format
- [ ] Auto-refresh works correctly (60s interval)
- [ ] ML predictions display with correct probabilities
- [ ] Backtest comparison shows +1,933% improvement
- [ ] Active trades update in real-time
- [ ] Statistics calculate correctly for 7d/30d/90d
- [ ] Tab switching works between Box and PupupuV3
- [ ] Responsive design works on mobile/tablet/desktop
- [ ] Color coding matches signal types (LONG=green, SHORT=red)
- [ ] Error handling works when API is down
- [ ] Loading states display properly
- [ ] Timezone handling for timestamps

---

## 10. Performance Optimization

- Use React.memo() for expensive components
- Implement virtual scrolling for large signal lists
- Debounce API calls when user changes filters
- Cache backtest results (rarely changes)
- Lazy load chart libraries (TradingView, Recharts, etc.)
- Use Web Workers for heavy calculations (if needed)

---

## 11. Deployment Notes

- API must be running on port 8000
- Frontend should proxy `/api/v1/pupupuv3` to avoid CORS issues
- Environment variable for API base URL: `REACT_APP_API_URL`
- Ensure ML model file exists at `tools/backtest/box_strategy/models/tp_ratio_predictor_v1.pkl`

---

## 12. Example Component Code Snippets

### Current Signal Card Component
```typescript
import React from 'react';
import { Card, CardHeader, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

interface CurrentSignalCardProps {
  analysis: CurrentAnalysis | null;
}

export const CurrentSignalCard: React.FC<CurrentSignalCardProps> = ({ analysis }) => {
  if (!analysis?.signal) {
    return (
      <Card>
        <CardHeader>⚪ No Active Signal</CardHeader>
        <CardContent>
          <p className="text-muted-foreground">
            Waiting for setup conditions to align...
          </p>
        </CardContent>
      </Card>
    );
  }

  const { signal, ml_prediction, current_price } = analysis;
  const isLong = signal.type === "LONG";
  const bgColor = isLong ? "bg-green-50" : "bg-red-50";
  const textColor = isLong ? "text-green-700" : "text-red-700";

  return (
    <Card className={bgColor}>
      <CardHeader className="flex flex-row items-center justify-between">
        <h3 className={`text-2xl font-bold ${textColor}`}>
          {isLong ? "🟢" : "🔴"} {signal.type} SIGNAL
        </h3>
        <Badge variant="outline">{analysis.symbol}</Badge>
      </CardHeader>

      <CardContent className="space-y-4">
        <div className="text-3xl font-bold">
          ${current_price.toLocaleString('en-US', { minimumFractionDigits: 2 })}
        </div>

        <div className="space-y-2">
          <PriceLevel label="Entry" price={signal.entry} color="text-blue-600" />
          <PriceLevel label="Stop Loss" price={signal.stop_loss} color="text-red-600" />
          <PriceLevel
            label="TP1"
            price={signal.tp1}
            color="text-green-600"
            subtitle="50% exit + move to BE"
          />

          {ml_prediction && (
            <>
              <PriceLevel
                label="TP2"
                price={ml_prediction.tp2.price}
                color="text-yellow-600"
                subtitle={`30% exit | R:R ${ml_prediction.tp2.ratio}:1 | ${(ml_prediction.tp2.probability * 100).toFixed(0)}% prob | ${ml_prediction.tp2.timeframe}`}
              />
              <PriceLevel
                label="TP3"
                price={ml_prediction.tp3.price}
                color="text-blue-600"
                subtitle={`20% exit | R:R ${ml_prediction.tp3.ratio}:1 | ${(ml_prediction.tp3.probability * 100).toFixed(0)}% prob | ${ml_prediction.tp3.timeframe}`}
              />
            </>
          )}
        </div>

        <div className="border-t pt-4">
          <div className="flex justify-between text-sm">
            <span>Risk: ${signal.risk_amount}</span>
            <span>Size: {signal.position_size.toFixed(4)} BTC</span>
          </div>
          {ml_prediction && (
            <div className="mt-2">
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm font-medium">ML Confidence</span>
                <span className="text-sm">{(ml_prediction.confidence_score * 100).toFixed(1)}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all"
                  style={{ width: `${ml_prediction.confidence_score * 100}%` }}
                />
              </div>
            </div>
          )}
        </div>

        <div className="border-t pt-4">
          <h4 className="font-semibold mb-2">Conditions:</h4>
          <ConditionCheck label="Pivot Touch" met={signal.conditions_met.touch} />
          <ConditionCheck label="EMA(15) Test" met={signal.conditions_met.ema_test} />
          <ConditionCheck label="VWAP Alignment" met={signal.conditions_met.vwap_alignment} />
          <ConditionCheck label="Volume Profile Support" met={signal.conditions_met.volume_profile_support} />
        </div>
      </CardContent>
    </Card>
  );
};

const PriceLevel: React.FC<{label: string; price: number; color: string; subtitle?: string}> =
  ({ label, price, color, subtitle }) => (
    <div className="flex justify-between items-start">
      <span className="font-medium">{label}:</span>
      <div className="text-right">
        <div className={`font-bold ${color}`}>
          ${price.toLocaleString('en-US', { minimumFractionDigits: 2 })}
        </div>
        {subtitle && <div className="text-xs text-muted-foreground">{subtitle}</div>}
      </div>
    </div>
  );

const ConditionCheck: React.FC<{label: string; met: boolean}> = ({ label, met }) => (
  <div className="flex items-center gap-2 text-sm">
    <span>{met ? "✅" : "❌"}</span>
    <span className={met ? "text-green-600" : "text-gray-400"}>{label}</span>
  </div>
);
```

### Backtest Comparison Component
```typescript
import React from 'react';
import { Card, CardHeader, CardContent } from '@/components/ui/card';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

interface BacktestComparisonProps {
  results: BacktestComparison | null;
}

export const BacktestComparisonChart: React.FC<BacktestComparisonProps> = ({ results }) => {
  if (!results) return <Card><CardContent>Loading backtest results...</CardContent></Card>;

  const { comparison, test_period, total_signals } = results;
  const { phase1_tp1_only, phase3_ml_dynamic, improvement } = comparison;

  const chartData = [
    {
      metric: 'Total PnL',
      'TP1 Only': phase1_tp1_only.total_pnl,
      'ML Dynamic': phase3_ml_dynamic.total_pnl
    },
    {
      metric: 'Avg Win',
      'TP1 Only': phase1_tp1_only.avg_win,
      'ML Dynamic': phase3_ml_dynamic.avg_win
    },
    {
      metric: 'Expectancy',
      'TP1 Only': phase1_tp1_only.expectancy,
      'ML Dynamic': phase3_ml_dynamic.expectancy
    }
  ];

  return (
    <Card className="col-span-2">
      <CardHeader>
        <h3 className="text-xl font-bold">📈 Backtest Comparison</h3>
        <p className="text-sm text-muted-foreground">
          {test_period} | {total_signals} signals tested
        </p>
      </CardHeader>

      <CardContent>
        {/* Highlight Box */}
        <div className="bg-gradient-to-r from-green-100 to-green-200 border-2 border-green-400 rounded-lg p-6 mb-6 text-center">
          <div className="text-4xl font-bold text-green-700 mb-2">
            +{improvement.pnl_percentage.toFixed(0)}% 🚀
          </div>
          <div className="text-lg text-green-600">
            PnL Improvement with ML Dynamic TPs
          </div>
          <div className="text-sm text-green-600 mt-2">
            ${improvement.pnl_change.toLocaleString()} additional profit
          </div>
        </div>

        {/* Metrics Table */}
        <div className="grid grid-cols-3 gap-4 mb-6">
          <div className="text-center font-semibold">Metric</div>
          <div className="text-center font-semibold">Phase 1<br/>(TP1 Only)</div>
          <div className="text-center font-semibold">Phase 3<br/>(ML Dynamic)</div>

          <MetricRow
            label="Total PnL"
            value1={phase1_tp1_only.total_pnl}
            value2={phase3_ml_dynamic.total_pnl}
            format="currency"
          />
          <MetricRow
            label="Win Rate"
            value1={phase1_tp1_only.win_rate}
            value2={phase3_ml_dynamic.win_rate}
            format="percentage"
          />
          <MetricRow
            label="Avg Win"
            value1={phase1_tp1_only.avg_win}
            value2={phase3_ml_dynamic.avg_win}
            format="currency"
          />
          <MetricRow
            label="Avg Loss"
            value1={phase1_tp1_only.avg_loss}
            value2={phase3_ml_dynamic.avg_loss}
            format="currency"
          />
          <MetricRow
            label="Profit Factor"
            value1={phase1_tp1_only.profit_factor}
            value2={phase3_ml_dynamic.profit_factor}
            format="number"
          />
          <MetricRow
            label="Expectancy"
            value1={phase1_tp1_only.expectancy}
            value2={phase3_ml_dynamic.expectancy}
            format="currency"
          />
        </div>

        {/* Chart */}
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="metric" />
            <YAxis />
            <Tooltip formatter={(value) => `$${value.toLocaleString()}`} />
            <Legend />
            <Bar dataKey="TP1 Only" fill="#EF4444" />
            <Bar dataKey="ML Dynamic" fill="#10B981" />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
};

const MetricRow: React.FC<{
  label: string;
  value1: number;
  value2: number;
  format: 'currency' | 'percentage' | 'number';
}> = ({ label, value1, value2, format }) => {
  const formatValue = (val: number) => {
    if (format === 'currency') return `$${val.toLocaleString()}`;
    if (format === 'percentage') return `${val.toFixed(2)}%`;
    return val.toFixed(2);
  };

  const isImprovement = value2 > value1;
  const v2Color = isImprovement ? 'text-green-600' : 'text-red-600';

  return (
    <>
      <div className="text-left">{label}</div>
      <div className="text-center">{formatValue(value1)}</div>
      <div className={`text-center font-bold ${v2Color}`}>{formatValue(value2)}</div>
    </>
  );
};
```

---

## Summary

This prompt provides everything needed to implement the complete PupupuV3 frontend dashboard:

1. ✅ **Complete API specification** with all endpoints and response formats
2. ✅ **Component structure** with detailed UI/UX mockups
3. ✅ **TypeScript interfaces** for type safety
4. ✅ **Data fetching strategies** with polling and parallel loading
5. ✅ **Visual design guidelines** with color schemes and icons
6. ✅ **Integration approach** for existing Box Strategy dashboard
7. ✅ **Example React components** ready to adapt
8. ✅ **Testing checklist** for validation
9. ✅ **Performance optimization** tips
10. ✅ **Backtest results visualization** highlighting +1,933% improvement

The dashboard will show real-time signals with ML-predicted dynamic take profits, comprehensive statistics, active trade monitoring, and side-by-side backtest comparison proving the ML system's effectiveness.
