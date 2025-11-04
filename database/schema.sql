-- ============================================================================
-- PostgreSQL Schema for Stock Analyzer
-- Complete migration from SQLite with enhancements for historical data
-- ============================================================================

-- Drop existing tables (for clean setup)
DROP TABLE IF EXISTS ml_model_results CASCADE;
DROP TABLE IF EXISTS ml_training_features CASCADE;
DROP TABLE IF EXISTS data_quality_log CASCADE;
DROP TABLE IF EXISTS market_data_5m CASCADE;
DROP TABLE IF EXISTS decision_logs CASCADE;
DROP TABLE IF EXISTS volatility_tracking CASCADE;
DROP TABLE IF EXISTS mtss_scores CASCADE;
DROP TABLE IF EXISTS sentiment_analysis CASCADE;
DROP TABLE IF EXISTS price_alerts CASCADE;
DROP TABLE IF EXISTS portfolio_state CASCADE;
DROP TABLE IF EXISTS portfolio_snapshots CASCADE;
DROP TABLE IF EXISTS portfolio_transactions CASCADE;
DROP TABLE IF EXISTS autotrader_transactions CASCADE;
DROP TABLE IF EXISTS transactions CASCADE;
DROP TABLE IF EXISTS positions CASCADE;
DROP TABLE IF EXISTS symbols CASCADE;
DROP TABLE IF EXISTS market_status CASCADE;
DROP TABLE IF EXISTS system_config CASCADE;

-- ============================================================================
-- EXISTING TABLES (from trading.db)
-- ============================================================================

-- System Configuration
CREATE TABLE system_config (
    id SERIAL PRIMARY KEY,
    key VARCHAR(100) UNIQUE NOT NULL,
    value TEXT,
    description TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Market Status Tracking
CREATE TABLE market_status (
    id SERIAL PRIMARY KEY,
    date DATE UNIQUE NOT NULL,
    is_open BOOLEAN DEFAULT FALSE,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Symbols Watchlist
CREATE TABLE symbols (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(200),
    sector VARCHAR(100),
    market_cap BIGINT,

    -- Scoring fields
    base_score DECIMAL(10, 4),
    momentum_score DECIMAL(10, 4),
    technical_score DECIMAL(10, 4),
    total_score DECIMAL(10, 4),

    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    last_updated TIMESTAMPTZ,
    added_date TIMESTAMPTZ DEFAULT NOW(),

    -- Metadata
    data_source VARCHAR(50),
    notes TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_symbols_symbol ON symbols(symbol);
CREATE INDEX idx_symbols_total_score ON symbols(total_score DESC);
CREATE INDEX idx_symbols_is_active ON symbols(is_active);

-- Positions
CREATE TABLE positions (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    position_type VARCHAR(20) NOT NULL, -- LONG, SHORT, CRYPTO_LONG, CRYPTO_SHORT

    -- Entry details
    entry_price DECIMAL(18, 8) NOT NULL,
    entry_date TIMESTAMPTZ NOT NULL,
    quantity DECIMAL(18, 8) NOT NULL,

    -- Position value
    current_price DECIMAL(18, 8),
    current_value DECIMAL(18, 8),
    cost_basis DECIMAL(18, 8),

    -- P&L
    unrealized_pnl DECIMAL(18, 8),
    unrealized_pnl_pct DECIMAL(10, 4),

    -- Risk management
    stop_loss DECIMAL(18, 8),
    take_profit DECIMAL(18, 8),
    trailing_stop DECIMAL(18, 8),

    -- Strategy info
    strategy VARCHAR(100),
    entry_score DECIMAL(10, 4),

    -- Status
    is_open BOOLEAN DEFAULT TRUE,

    -- Exit details (when closed)
    exit_price DECIMAL(18, 8),
    exit_date TIMESTAMPTZ,
    realized_pnl DECIMAL(18, 8),
    realized_pnl_pct DECIMAL(10, 4),
    exit_reason VARCHAR(200),

    -- Metadata
    notes TEXT,
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_positions_symbol ON positions(symbol);
CREATE INDEX idx_positions_is_open ON positions(is_open);
CREATE INDEX idx_positions_type ON positions(position_type);
CREATE INDEX idx_positions_entry_date ON positions(entry_date);

-- Transactions
CREATE TABLE transactions (
    id SERIAL PRIMARY KEY,
    position_id INTEGER REFERENCES positions(id) ON DELETE CASCADE,

    symbol VARCHAR(20) NOT NULL,
    action VARCHAR(20) NOT NULL, -- BUY, SELL, SHORT, COVER

    quantity DECIMAL(18, 8) NOT NULL,
    price DECIMAL(18, 8) NOT NULL,
    total_value DECIMAL(18, 8) NOT NULL,

    transaction_date TIMESTAMPTZ NOT NULL,

    -- Fees and costs
    commission DECIMAL(18, 8) DEFAULT 0,
    fees DECIMAL(18, 8) DEFAULT 0,

    -- Strategy context
    strategy VARCHAR(100),
    reason TEXT,

    -- Metadata
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_transactions_symbol ON transactions(symbol);
CREATE INDEX idx_transactions_position_id ON transactions(position_id);
CREATE INDEX idx_transactions_date ON transactions(transaction_date);
CREATE INDEX idx_transactions_action ON transactions(action);

-- Autotrader Transactions
CREATE TABLE autotrader_transactions (
    id SERIAL PRIMARY KEY,

    symbol VARCHAR(20) NOT NULL,
    action VARCHAR(20) NOT NULL,

    quantity DECIMAL(18, 8) NOT NULL,
    price DECIMAL(18, 8) NOT NULL,
    total_value DECIMAL(18, 8) NOT NULL,

    transaction_date TIMESTAMPTZ NOT NULL,

    -- Strategy details
    strategy VARCHAR(100),
    entry_score DECIMAL(10, 4),

    -- Risk management
    stop_loss DECIMAL(18, 8),
    take_profit DECIMAL(18, 8),

    -- Outcome (filled when position closes)
    exit_price DECIMAL(18, 8),
    exit_date TIMESTAMPTZ,
    pnl DECIMAL(18, 8),
    pnl_pct DECIMAL(10, 4),

    -- Metadata
    reason TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_autotrader_symbol ON autotrader_transactions(symbol);
CREATE INDEX idx_autotrader_date ON autotrader_transactions(transaction_date);
CREATE INDEX idx_autotrader_action ON autotrader_transactions(action);

-- Portfolio Transactions (high-level tracking)
CREATE TABLE portfolio_transactions (
    id SERIAL PRIMARY KEY,

    transaction_type VARCHAR(50) NOT NULL, -- DEPOSIT, WITHDRAWAL, TRADE_PNL, DIVIDEND, etc
    amount DECIMAL(18, 8) NOT NULL,

    currency VARCHAR(10) DEFAULT 'USD',
    account_type VARCHAR(20), -- STOCKS, CRYPTO

    transaction_date TIMESTAMPTZ NOT NULL,

    description TEXT,
    notes TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_portfolio_trans_date ON portfolio_transactions(transaction_date);
CREATE INDEX idx_portfolio_trans_type ON portfolio_transactions(transaction_type);

-- Portfolio Snapshots (daily/periodic snapshots)
CREATE TABLE portfolio_snapshots (
    id SERIAL PRIMARY KEY,

    snapshot_date TIMESTAMPTZ NOT NULL,

    -- Stocks
    liquid_capital_stocks DECIMAL(18, 8) DEFAULT 0,
    invested_capital_stocks DECIMAL(18, 8) DEFAULT 0,
    total_pnl_stocks DECIMAL(18, 8) DEFAULT 0,
    total_value_stocks DECIMAL(18, 8) DEFAULT 0,

    -- Crypto
    liquid_capital_crypto DECIMAL(18, 8) DEFAULT 0,
    invested_capital_crypto DECIMAL(18, 8) DEFAULT 0,
    total_pnl_crypto DECIMAL(18, 8) DEFAULT 0,
    total_value_crypto DECIMAL(18, 8) DEFAULT 0,

    -- Overall
    total_portfolio_value DECIMAL(18, 8) DEFAULT 0,

    -- Position counts
    open_positions_stocks INTEGER DEFAULT 0,
    open_positions_crypto INTEGER DEFAULT 0,

    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(snapshot_date)
);

CREATE INDEX idx_portfolio_snapshots_date ON portfolio_snapshots(snapshot_date DESC);

-- Portfolio State (current state - single row table)
CREATE TABLE portfolio_state (
    id SERIAL PRIMARY KEY,

    -- Stocks
    liquid_capital_stocks DECIMAL(18, 8) DEFAULT 10000.00,
    invested_capital_stocks DECIMAL(18, 8) DEFAULT 0,
    total_pnl_stocks DECIMAL(18, 8) DEFAULT 0,

    -- Crypto
    liquid_capital_crypto DECIMAL(18, 8) DEFAULT 50000.00,
    invested_capital_crypto DECIMAL(18, 8) DEFAULT 0,
    total_pnl_crypto DECIMAL(18, 8) DEFAULT 0,

    -- Metadata
    last_updated TIMESTAMPTZ DEFAULT NOW(),

    -- Constraint: only one row allowed
    CONSTRAINT single_row CHECK (id = 1)
);

-- Insert initial state
INSERT INTO portfolio_state (id, liquid_capital_stocks, liquid_capital_crypto)
VALUES (1, 10000.00, 50000.00)
ON CONFLICT (id) DO NOTHING;

-- Price Alerts
CREATE TABLE price_alerts (
    id SERIAL PRIMARY KEY,

    symbol VARCHAR(20) NOT NULL,
    alert_type VARCHAR(50) NOT NULL, -- PRICE_ABOVE, PRICE_BELOW, PERCENT_CHANGE, etc

    target_price DECIMAL(18, 8),
    current_price DECIMAL(18, 8),

    is_active BOOLEAN DEFAULT TRUE,
    is_triggered BOOLEAN DEFAULT FALSE,

    triggered_at TIMESTAMPTZ,

    -- Notification details
    notification_method VARCHAR(50), -- EMAIL, SMS, PUSH, etc
    notification_sent BOOLEAN DEFAULT FALSE,

    notes TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_alerts_symbol ON price_alerts(symbol);
CREATE INDEX idx_alerts_active ON price_alerts(is_active);
CREATE INDEX idx_alerts_triggered ON price_alerts(is_triggered);

-- Sentiment Analysis
CREATE TABLE sentiment_analysis (
    id SERIAL PRIMARY KEY,

    symbol VARCHAR(20) NOT NULL,

    analysis_date TIMESTAMPTZ NOT NULL,
    source VARCHAR(100), -- TWITTER, REDDIT, NEWS, etc

    sentiment_score DECIMAL(5, 4), -- -1.0 to 1.0
    confidence DECIMAL(5, 4), -- 0.0 to 1.0

    text_sample TEXT,

    -- Aggregated metrics
    positive_mentions INTEGER DEFAULT 0,
    negative_mentions INTEGER DEFAULT 0,
    neutral_mentions INTEGER DEFAULT 0,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_sentiment_symbol ON sentiment_analysis(symbol);
CREATE INDEX idx_sentiment_date ON sentiment_analysis(analysis_date DESC);

-- MTSS Scores (Multi-Timeframe Scoring System)
CREATE TABLE mtss_scores (
    id SERIAL PRIMARY KEY,

    symbol VARCHAR(20) NOT NULL,

    score_date TIMESTAMPTZ NOT NULL,

    -- Scores by timeframe
    score_1d DECIMAL(10, 4),
    score_4h DECIMAL(10, 4),
    score_1h DECIMAL(10, 4),

    -- Combined score
    total_score DECIMAL(10, 4),

    -- Technical indicators
    rsi_14 DECIMAL(10, 4),
    macd DECIMAL(10, 4),
    signal DECIMAL(10, 4),

    -- Momentum
    momentum_7d DECIMAL(10, 4),
    momentum_30d DECIMAL(10, 4),

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_mtss_symbol ON mtss_scores(symbol);
CREATE INDEX idx_mtss_date ON mtss_scores(score_date DESC);
CREATE INDEX idx_mtss_total_score ON mtss_scores(total_score DESC);

-- Volatility Tracking
CREATE TABLE volatility_tracking (
    id SERIAL PRIMARY KEY,

    symbol VARCHAR(20) NOT NULL,

    tracking_date TIMESTAMPTZ NOT NULL,

    -- Volatility metrics
    volatility_1d DECIMAL(10, 4),
    volatility_7d DECIMAL(10, 4),
    volatility_30d DECIMAL(10, 4),

    atr_14 DECIMAL(18, 8), -- Average True Range

    -- Price data
    close_price DECIMAL(18, 8),
    high_price DECIMAL(18, 8),
    low_price DECIMAL(18, 8),

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_volatility_symbol ON volatility_tracking(symbol);
CREATE INDEX idx_volatility_date ON volatility_tracking(tracking_date DESC);

-- Decision Logs (ML/Strategy decision audit trail)
CREATE TABLE decision_logs (
    id SERIAL PRIMARY KEY,

    decision_date TIMESTAMPTZ NOT NULL,

    symbol VARCHAR(20) NOT NULL,
    decision_type VARCHAR(50) NOT NULL, -- BUY, SELL, HOLD, SKIP

    strategy VARCHAR(100),

    -- Scores/Confidence
    score DECIMAL(10, 4),
    confidence DECIMAL(10, 4),

    -- Decision factors
    factors JSONB,

    -- Outcome (filled later)
    action_taken VARCHAR(50),
    outcome VARCHAR(50), -- SUCCESS, FAILURE, PENDING

    notes TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_decision_logs_symbol ON decision_logs(symbol);
CREATE INDEX idx_decision_logs_date ON decision_logs(decision_date DESC);
CREATE INDEX idx_decision_logs_type ON decision_logs(decision_type);
CREATE INDEX idx_decision_logs_factors ON decision_logs USING GIN(factors);

-- ============================================================================
-- NEW TABLES (for historical data and ML training)
-- ============================================================================

-- Historical Market Data (5-minute OHLCV)
CREATE TABLE market_data_5m (
    id BIGSERIAL PRIMARY KEY,

    market VARCHAR(10) NOT NULL, -- SPX, NDX, RUT, DAX, FTSE, etc
    ticker VARCHAR(20) NOT NULL, -- ES=F, NQ=F, RTY=F, etc

    timestamp TIMESTAMPTZ NOT NULL,

    -- OHLCV
    open DECIMAL(18, 8) NOT NULL,
    high DECIMAL(18, 8) NOT NULL,
    low DECIMAL(18, 8) NOT NULL,
    close DECIMAL(18, 8) NOT NULL,
    volume BIGINT,

    -- Metadata
    source VARCHAR(50) DEFAULT 'yfinance',
    quality_score DECIMAL(5, 4) DEFAULT 1.0, -- Data quality (0.0 to 1.0)

    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(market, timestamp)
);

CREATE INDEX idx_market_data_market ON market_data_5m(market);
CREATE INDEX idx_market_data_timestamp ON market_data_5m(timestamp DESC);
CREATE INDEX idx_market_data_market_timestamp ON market_data_5m(market, timestamp DESC);
CREATE INDEX idx_market_data_ticker ON market_data_5m(ticker);

-- Data Quality Log
CREATE TABLE data_quality_log (
    id SERIAL PRIMARY KEY,

    market VARCHAR(10) NOT NULL,
    check_date TIMESTAMPTZ NOT NULL,

    -- Date range checked
    start_date TIMESTAMPTZ,
    end_date TIMESTAMPTZ,

    -- Quality metrics
    total_candles INTEGER,
    missing_candles INTEGER,
    duplicate_candles INTEGER,
    quality_score DECIMAL(5, 4),

    -- Issues found
    issues JSONB,

    -- Resolution
    resolution_action VARCHAR(100),
    resolved_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_data_quality_market ON data_quality_log(market);
CREATE INDEX idx_data_quality_date ON data_quality_log(check_date DESC);

-- ML Training Features
CREATE TABLE ml_training_features (
    id BIGSERIAL PRIMARY KEY,

    market VARCHAR(10) NOT NULL,
    strategy VARCHAR(50) NOT NULL, -- box_strategy, swing_strategy, etc

    timestamp TIMESTAMPTZ NOT NULL,

    -- Feature vector (JSONB for flexibility)
    features JSONB NOT NULL,

    -- Label (target)
    label VARCHAR(50), -- WIN, LOSS, BREAKEVEN
    label_value DECIMAL(10, 4), -- Actual profit/loss

    -- Model version
    model_version VARCHAR(20),

    -- Metadata
    trade_id INTEGER, -- Reference to actual trade if available

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_ml_features_market ON ml_training_features(market);
CREATE INDEX idx_ml_features_strategy ON ml_training_features(strategy);
CREATE INDEX idx_ml_features_timestamp ON ml_training_features(timestamp DESC);
CREATE INDEX idx_ml_features_label ON ml_training_features(label);
CREATE INDEX idx_ml_features_features ON ml_training_features USING GIN(features);

-- ML Model Results (performance tracking)
CREATE TABLE ml_model_results (
    id SERIAL PRIMARY KEY,

    model_version VARCHAR(20) NOT NULL,
    strategy VARCHAR(50) NOT NULL,

    training_date TIMESTAMPTZ NOT NULL,

    -- Dataset info
    training_samples INTEGER,
    validation_samples INTEGER,
    test_samples INTEGER,

    -- Performance metrics
    accuracy DECIMAL(10, 4),
    precision_score DECIMAL(10, 4),
    recall DECIMAL(10, 4),
    f1_score DECIMAL(10, 4),

    -- Specific to trading
    win_rate DECIMAL(10, 4),
    avg_profit DECIMAL(10, 4),
    sharpe_ratio DECIMAL(10, 4),

    -- Model details
    algorithm VARCHAR(100), -- RandomForest, XGBoost, etc
    hyperparameters JSONB,

    -- Feature importance
    feature_importance JSONB,

    -- Model file location
    model_path TEXT,

    -- Status
    is_active BOOLEAN DEFAULT FALSE,

    notes TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_ml_results_version ON ml_model_results(model_version);
CREATE INDEX idx_ml_results_strategy ON ml_model_results(strategy);
CREATE INDEX idx_ml_results_date ON ml_model_results(training_date DESC);
CREATE INDEX idx_ml_results_active ON ml_model_results(is_active);

-- ============================================================================
-- FUNCTIONS AND TRIGGERS
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to relevant tables
CREATE TRIGGER update_symbols_updated_at BEFORE UPDATE ON symbols
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_positions_updated_at BEFORE UPDATE ON positions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_price_alerts_updated_at BEFORE UPDATE ON price_alerts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_system_config_updated_at BEFORE UPDATE ON system_config
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to update portfolio_state last_updated
CREATE OR REPLACE FUNCTION update_portfolio_state_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_updated = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_portfolio_state_timestamp BEFORE UPDATE ON portfolio_state
    FOR EACH ROW EXECUTE FUNCTION update_portfolio_state_timestamp();

-- ============================================================================
-- VIEWS (Useful aggregations)
-- ============================================================================

-- View: Open positions with current P&L
CREATE OR REPLACE VIEW v_open_positions AS
SELECT
    p.*,
    CASE
        WHEN p.position_type IN ('LONG', 'CRYPTO_LONG')
        THEN (p.current_price - p.entry_price) * p.quantity
        WHEN p.position_type IN ('SHORT', 'CRYPTO_SHORT')
        THEN (p.entry_price - p.current_price) * p.quantity
    END as calculated_pnl,
    CASE
        WHEN p.position_type IN ('LONG', 'CRYPTO_LONG')
        THEN ((p.current_price - p.entry_price) / p.entry_price) * 100
        WHEN p.position_type IN ('SHORT', 'CRYPTO_SHORT')
        THEN ((p.entry_price - p.current_price) / p.entry_price) * 100
    END as calculated_pnl_pct
FROM positions p
WHERE p.is_open = TRUE;

-- View: Portfolio summary
CREATE OR REPLACE VIEW v_portfolio_summary AS
SELECT
    (SELECT liquid_capital_stocks FROM portfolio_state WHERE id = 1) as liquid_stocks,
    (SELECT invested_capital_stocks FROM portfolio_state WHERE id = 1) as invested_stocks,
    (SELECT total_pnl_stocks FROM portfolio_state WHERE id = 1) as pnl_stocks,
    (SELECT liquid_capital_crypto FROM portfolio_state WHERE id = 1) as liquid_crypto,
    (SELECT invested_capital_crypto FROM portfolio_state WHERE id = 1) as invested_crypto,
    (SELECT total_pnl_crypto FROM portfolio_state WHERE id = 1) as pnl_crypto,
    (SELECT COUNT(*) FROM positions WHERE is_open = TRUE AND position_type IN ('LONG', 'SHORT')) as open_stock_positions,
    (SELECT COUNT(*) FROM positions WHERE is_open = TRUE AND position_type IN ('CRYPTO_LONG', 'CRYPTO_SHORT')) as open_crypto_positions,
    (SELECT liquid_capital_stocks + invested_capital_stocks + total_pnl_stocks +
            liquid_capital_crypto + invested_capital_crypto + total_pnl_crypto
     FROM portfolio_state WHERE id = 1) as total_portfolio_value;

-- ============================================================================
-- INITIAL DATA
-- ============================================================================

-- System config defaults
INSERT INTO system_config (key, value, description) VALUES
('autotrader_enabled', 'false', 'Enable/disable automated trading'),
('max_positions_stocks', '10', 'Maximum number of stock positions'),
('max_positions_crypto', '5', 'Maximum number of crypto positions'),
('buy_score_threshold', '6.0', 'Minimum score to buy LONG'),
('sell_score_threshold', '4.5', 'Score threshold to sell LONG'),
('short_score_threshold', '1.8', 'Maximum score to open SHORT'),
('risk_per_trade', '0.02', 'Risk 2% per trade'),
('max_portfolio_risk', '0.10', 'Maximum 10% portfolio risk')
ON CONFLICT (key) DO NOTHING;

-- ============================================================================
-- GRANTS (for application user - adjust username as needed)
-- ============================================================================

-- Note: Run these commands after creating the database user
-- CREATE USER stock_analyzer_user WITH PASSWORD 'your_secure_password';
-- GRANT CONNECT ON DATABASE stock_analyzer_local TO stock_analyzer_user;
-- GRANT USAGE ON SCHEMA public TO stock_analyzer_user;
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO stock_analyzer_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO stock_analyzer_user;

-- ============================================================================
-- END OF SCHEMA
-- ============================================================================
