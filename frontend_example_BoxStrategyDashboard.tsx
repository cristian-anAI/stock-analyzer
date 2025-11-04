/**
 * Box Strategy Dashboard Component
 *
 * Displays real-time box strategy monitoring with ML predictions across multiple markets.
 *
 * Features:
 * - Multi-market overview with different timezones
 * - Box formation status for each market
 * - ML confidence predictions (HIGH/MEDIUM/LOW)
 * - Breakout detection (LONG/SHORT)
 * - Trade setup details (entry, stop, targets)
 * - Auto-refresh every 5 minutes
 *
 * Usage:
 *   import BoxStrategyDashboard from './components/BoxStrategyDashboard';
 *
 *   <BoxStrategyDashboard mlVersion="1" />
 */

import React, { useState, useEffect } from 'react';
import axios from 'axios';

// TypeScript interfaces
interface MLPrediction {
  win_probability: number;
  confidence_level: 'HIGH' | 'MEDIUM' | 'LOW';
  recommendation: 'TRADE' | 'REDUCE_SIZE' | 'SKIP';
  position_size_multiplier: number;
  model_used: string;
  model_version: string;
}

interface BoxSetup {
  market: string;
  date: string;
  box_high: number;
  box_low: number;
  box_range: number;
  box_midpoint: number;
  candles_in_box: number;
  current_price: number | null;
  breakout_detected: boolean;
  direction: 'LONG' | 'SHORT' | null;
  entry_price: number | null;
  stop_loss: number | null;
  tp1: number | null;
  tp2: number | null;
  tp3: number | null;
  risk_points: number | null;
}

interface MarketStatus {
  market: string;
  local_time: string;
  is_box_period: boolean;
  is_post_box: boolean;
  box_complete: boolean;
  next_box_time: string | null;
  market_open: boolean;
}

interface MarketData {
  market: string;
  name: string;
  timezone: string;
  status: MarketStatus;
  box_setup: BoxSetup | null;
  ml_prediction: MLPrediction | null;
}

interface DashboardData {
  timestamp: string;
  ml_version: string;
  summary: {
    total_markets: number;
    pending_box: number;
    active_box: number;
    box_complete: number;
    breakouts: number;
    high_confidence: number;
    avg_win_probability: number;
  };
  markets_by_status: {
    pending: string[];
    active: string[];
    complete: string[];
  };
  high_confidence_setups: MarketData[];
  all_breakouts: MarketData[];
  all_markets: MarketData[];
}

interface BoxStrategyDashboardProps {
  mlVersion?: string;
  apiBaseUrl?: string;
  refreshInterval?: number; // in milliseconds
}

const BoxStrategyDashboard: React.FC<BoxStrategyDashboardProps> = ({
  mlVersion = "1",
  apiBaseUrl = "http://localhost:8000",
  refreshInterval = 300000 // 5 minutes
}) => {
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);

  // Fetch dashboard data
  const fetchDashboard = async () => {
    try {
      setLoading(true);
      const response = await axios.get<DashboardData>(
        `${apiBaseUrl}/api/v1/box-strategy/dashboard`,
        { params: { ml_version: mlVersion } }
      );
      setDashboardData(response.data);
      setLastUpdate(new Date());
      setError(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to fetch dashboard data');
    } finally {
      setLoading(false);
    }
  };

  // Initial fetch and auto-refresh
  useEffect(() => {
    fetchDashboard();
    const interval = setInterval(fetchDashboard, refreshInterval);
    return () => clearInterval(interval);
  }, [mlVersion, refreshInterval]);

  // Confidence badge color
  const getConfidenceColor = (level: string): string => {
    switch (level) {
      case 'HIGH': return 'bg-green-500';
      case 'MEDIUM': return 'bg-yellow-500';
      case 'LOW': return 'bg-red-500';
      default: return 'bg-gray-500';
    }
  };

  // Direction badge color
  const getDirectionColor = (direction: string | null): string => {
    if (direction === 'LONG') return 'bg-blue-500';
    if (direction === 'SHORT') return 'bg-orange-500';
    return 'bg-gray-400';
  };

  // Format price
  const formatPrice = (price: number | null): string => {
    if (price === null) return 'N/A';
    return price.toFixed(2);
  };

  // Format percentage
  const formatPercent = (value: number): string => {
    return `${(value * 100).toFixed(1)}%`;
  };

  // Render loading state
  if (loading && !dashboardData) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading Box Strategy Dashboard...</p>
        </div>
      </div>
    );
  }

  // Render error state
  if (error) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
          <strong className="font-bold">Error: </strong>
          <span>{error}</span>
          <button
            onClick={fetchDashboard}
            className="ml-4 px-3 py-1 bg-red-500 text-white rounded hover:bg-red-600"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!dashboardData) return null;

  return (
    <div className="max-w-7xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-800">Box Strategy Dashboard</h1>
            <p className="text-gray-600 mt-1">
              ML-Powered Trade Monitoring • Model v{dashboardData.ml_version}
            </p>
          </div>
          <div className="text-right">
            <p className="text-sm text-gray-500">Last Updated</p>
            <p className="text-sm font-medium text-gray-700">
              {lastUpdate?.toLocaleTimeString()}
            </p>
            <button
              onClick={fetchDashboard}
              className="mt-2 px-3 py-1 bg-blue-500 text-white text-sm rounded hover:bg-blue-600"
            >
              Refresh
            </button>
          </div>
        </div>
      </div>

      {/* Summary Statistics */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
        <StatCard
          label="Total Markets"
          value={dashboardData.summary.total_markets}
          color="bg-blue-500"
        />
        <StatCard
          label="Pending Box"
          value={dashboardData.summary.pending_box}
          color="bg-gray-500"
        />
        <StatCard
          label="Active Box"
          value={dashboardData.summary.active_box}
          color="bg-yellow-500"
        />
        <StatCard
          label="Box Complete"
          value={dashboardData.summary.box_complete}
          color="bg-green-500"
        />
        <StatCard
          label="Breakouts"
          value={dashboardData.summary.breakouts}
          color="bg-purple-500"
        />
        <StatCard
          label="High Confidence"
          value={dashboardData.summary.high_confidence}
          color="bg-emerald-500"
        />
      </div>

      {/* High Confidence Setups (Priority) */}
      {dashboardData.high_confidence_setups.length > 0 && (
        <div className="bg-gradient-to-r from-green-50 to-emerald-50 rounded-lg shadow-lg p-6 border-2 border-green-300">
          <h2 className="text-2xl font-bold text-green-800 mb-4 flex items-center">
            <span className="inline-block w-3 h-3 bg-green-500 rounded-full mr-2 animate-pulse"></span>
            High Confidence Setups ({dashboardData.high_confidence_setups.length})
          </h2>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {dashboardData.high_confidence_setups.map((market) => (
              <MarketCard key={market.market} market={market} highlight={true} />
            ))}
          </div>
        </div>
      )}

      {/* All Breakouts */}
      {dashboardData.all_breakouts.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-2xl font-bold text-gray-800 mb-4">
            All Breakouts ({dashboardData.all_breakouts.length})
          </h2>
          <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
            {dashboardData.all_breakouts.map((market) => (
              <MarketCard key={market.market} market={market} />
            ))}
          </div>
        </div>
      )}

      {/* All Markets Overview */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-2xl font-bold text-gray-800 mb-4">All Markets</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {dashboardData.all_markets.map((market) => (
            <MarketOverviewCard key={market.market} market={market} />
          ))}
        </div>
      </div>

      {/* Average Win Probability */}
      {dashboardData.all_breakouts.length > 0 && (
        <div className="bg-white rounded-lg shadow p-4 text-center">
          <p className="text-sm text-gray-600">Average Win Probability (Active Breakouts)</p>
          <p className="text-3xl font-bold text-blue-600">
            {formatPercent(dashboardData.summary.avg_win_probability)}
          </p>
        </div>
      )}
    </div>
  );
};

// Stat Card Component
const StatCard: React.FC<{ label: string; value: number; color: string }> = ({ label, value, color }) => (
  <div className="bg-white rounded-lg shadow p-4">
    <p className="text-sm text-gray-600">{label}</p>
    <div className="flex items-center mt-2">
      <div className={`w-2 h-8 ${color} rounded mr-2`}></div>
      <p className="text-3xl font-bold text-gray-800">{value}</p>
    </div>
  </div>
);

// Market Card Component (Detailed)
const MarketCard: React.FC<{ market: MarketData; highlight?: boolean }> = ({ market, highlight }) => {
  const setup = market.box_setup;
  const pred = market.ml_prediction;

  if (!setup || !setup.breakout_detected) return null;

  const getConfidenceColor = (level: string): string => {
    switch (level) {
      case 'HIGH': return 'bg-green-500';
      case 'MEDIUM': return 'bg-yellow-500';
      case 'LOW': return 'bg-red-500';
      default: return 'bg-gray-500';
    }
  };

  const getDirectionColor = (direction: string | null): string => {
    if (direction === 'LONG') return 'bg-blue-500';
    if (direction === 'SHORT') return 'bg-orange-500';
    return 'bg-gray-400';
  };

  return (
    <div className={`rounded-lg shadow-md p-4 ${highlight ? 'bg-white border-2 border-green-400' : 'bg-gray-50'}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div>
          <h3 className="text-lg font-bold text-gray-800">{market.market}</h3>
          <p className="text-sm text-gray-600">{market.name}</p>
        </div>
        <span className={`px-3 py-1 ${getDirectionColor(setup.direction)} text-white text-sm font-bold rounded`}>
          {setup.direction}
        </span>
      </div>

      {/* ML Prediction */}
      {pred && (
        <div className="mb-3 p-3 bg-white rounded border">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-700">ML Prediction</span>
            <span className={`px-2 py-1 ${getConfidenceColor(pred.confidence_level)} text-white text-xs font-bold rounded`}>
              {pred.confidence_level}
            </span>
          </div>
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div>
              <p className="text-gray-600">Win Probability</p>
              <p className="font-bold text-gray-800">{(pred.win_probability * 100).toFixed(1)}%</p>
            </div>
            <div>
              <p className="text-gray-600">Position Size</p>
              <p className="font-bold text-gray-800">{(pred.position_size_multiplier * 100).toFixed(0)}%</p>
            </div>
          </div>
          <div className="mt-2">
            <p className="text-xs text-gray-600">Recommendation</p>
            <p className="font-bold text-sm text-gray-800">{pred.recommendation.replace('_', ' ')}</p>
          </div>
        </div>
      )}

      {/* Trade Setup */}
      <div className="space-y-1 text-sm">
        <div className="flex justify-between">
          <span className="text-gray-600">Entry:</span>
          <span className="font-medium">{setup.entry_price?.toFixed(2)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">Stop Loss:</span>
          <span className="font-medium text-red-600">{setup.stop_loss?.toFixed(2)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">TP1 (1R):</span>
          <span className="font-medium text-green-600">{setup.tp1?.toFixed(2)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">TP2 (2R):</span>
          <span className="font-medium text-green-600">{setup.tp2?.toFixed(2)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">TP3 (3R):</span>
          <span className="font-medium text-green-600">{setup.tp3?.toFixed(2)}</span>
        </div>
        <div className="flex justify-between border-t pt-1 mt-2">
          <span className="text-gray-600">Risk:</span>
          <span className="font-bold">{setup.risk_points?.toFixed(2)} pts</span>
        </div>
      </div>

      {/* Current Price */}
      {setup.current_price && (
        <div className="mt-3 p-2 bg-blue-50 rounded">
          <p className="text-xs text-gray-600">Current Price</p>
          <p className="text-lg font-bold text-blue-700">{setup.current_price.toFixed(2)}</p>
        </div>
      )}
    </div>
  );
};

// Market Overview Card (Compact)
const MarketOverviewCard: React.FC<{ market: MarketData }> = ({ market }) => {
  const status = market.status;
  const setup = market.box_setup;

  const getStatusBadge = () => {
    if (status.is_box_period) return <span className="px-2 py-1 bg-yellow-500 text-white text-xs rounded">ACTIVE BOX</span>;
    if (status.box_complete) return <span className="px-2 py-1 bg-green-500 text-white text-xs rounded">COMPLETE</span>;
    return <span className="px-2 py-1 bg-gray-400 text-white text-xs rounded">PENDING</span>;
  };

  return (
    <div className="bg-gray-50 rounded-lg p-3 border">
      <div className="flex items-center justify-between mb-2">
        <div>
          <h4 className="font-bold text-gray-800">{market.market}</h4>
          <p className="text-xs text-gray-600">{market.name}</p>
        </div>
        {getStatusBadge()}
      </div>

      {setup && (
        <div className="text-xs space-y-1 text-gray-700">
          <div className="flex justify-between">
            <span>Box Range:</span>
            <span className="font-medium">{setup.box_range.toFixed(2)}</span>
          </div>
          {setup.breakout_detected && (
            <div className="flex justify-between">
              <span>Breakout:</span>
              <span className={`font-bold ${setup.direction === 'LONG' ? 'text-blue-600' : 'text-orange-600'}`}>
                {setup.direction}
              </span>
            </div>
          )}
        </div>
      )}

      <div className="mt-2 text-xs text-gray-500">
        <p>Timezone: {market.timezone.split('/')[1]}</p>
      </div>
    </div>
  );
};

export default BoxStrategyDashboard;
