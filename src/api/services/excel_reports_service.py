"""
Excel Reports Service - Generate comprehensive analysis reports
Creates multiple Excel files with trading data, positions, and signals
"""

import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import os
import logging
from typing import Dict, Any, List
from pathlib import Path

logger = logging.getLogger(__name__)

class ExcelReportsService:
    """Service for generating Excel reports with trading analysis"""
    
    def __init__(self, output_dir: str = "reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
    def get_db_connection(self):
        """Get database connection"""
        return sqlite3.connect('trading.db', check_same_thread=False)
    
    def generate_all_reports(self):
        """Generate all Excel reports"""
        try:
            logger.info("Starting Excel reports generation...")
            
            # Generate individual reports
            self._generate_trading_history_report()
            self._generate_positions_report()
            self._generate_buy_signals_report()
            self._generate_portfolio_summary_report()
            
            logger.info("All Excel reports generated successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error generating Excel reports: {str(e)}")
            return False
    
    def _generate_trading_history_report(self):
        """Generate complete trading history Excel with buy/sell reasons"""
        conn = self.get_db_connection()
        
        # Get all portfolio transactions
        query = """
        SELECT 
            portfolio_type,
            symbol,
            action,
            quantity,
            price,
            total_amount,
            fees,
            buy_reason,
            sell_reason,
            score,
            timestamp,
            source
        FROM portfolio_transactions 
        ORDER BY timestamp DESC
        """
        
        df = pd.read_sql_query(query, conn)
        
        # Add calculated columns
        df['reason'] = df.apply(
            lambda row: row['buy_reason'] if row['action'] == 'buy' else row['sell_reason'], 
            axis=1
        )
        df['date'] = pd.to_datetime(df['timestamp']).dt.date
        df['time'] = pd.to_datetime(df['timestamp']).dt.time
        
        # Separate sheets for stocks and crypto
        with pd.ExcelWriter(
            self.output_dir / f"Trading_History_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            engine='openpyxl'
        ) as writer:
            
            # All transactions
            df_display = df[[
                'date', 'time', 'portfolio_type', 'symbol', 'action', 
                'quantity', 'price', 'total_amount', 'reason', 'score', 'source'
            ]].copy()
            df_display.to_excel(writer, sheet_name='All_Transactions', index=False)
            
            # Stocks only
            stocks_df = df[df['portfolio_type'] == 'stocks'].copy()
            if not stocks_df.empty:
                stocks_display = stocks_df[[
                    'date', 'time', 'symbol', 'action', 
                    'quantity', 'price', 'total_amount', 'reason', 'score'
                ]].copy()
                stocks_display.to_excel(writer, sheet_name='Stocks_History', index=False)
            
            # Crypto only
            crypto_df = df[df['portfolio_type'] == 'crypto'].copy()
            if not crypto_df.empty:
                crypto_display = crypto_df[[
                    'date', 'time', 'symbol', 'action', 
                    'quantity', 'price', 'total_amount', 'reason', 'score'
                ]].copy()
                crypto_display.to_excel(writer, sheet_name='Crypto_History', index=False)
            
            # Trading Summary
            summary_data = []
            
            # Portfolio summary
            for portfolio in ['stocks', 'crypto']:
                portfolio_df = df[df['portfolio_type'] == portfolio]
                if not portfolio_df.empty:
                    buys = portfolio_df[portfolio_df['action'] == 'buy']
                    sells = portfolio_df[portfolio_df['action'] == 'sell']
                    
                    summary_data.append({
                        'Portfolio': portfolio.upper(),
                        'Total_Transactions': len(portfolio_df),
                        'Buy_Orders': len(buys),
                        'Sell_Orders': len(sells),
                        'Buy_Volume': buys['total_amount'].sum() if not buys.empty else 0,
                        'Sell_Volume': sells['total_amount'].sum() if not sells.empty else 0,
                        'Net_Flow': (sells['total_amount'].sum() - buys['total_amount'].sum()) if not sells.empty and not buys.empty else 0,
                        'Avg_Buy_Size': buys['total_amount'].mean() if not buys.empty else 0,
                        'Avg_Sell_Size': sells['total_amount'].mean() if not sells.empty else 0,
                        'Unique_Symbols': portfolio_df['symbol'].nunique(),
                        'Last_Activity': portfolio_df['date'].max() if not portfolio_df.empty else None
                    })
            
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Trading_Summary', index=False)
        
        conn.close()
        logger.info("Trading history report generated")
    
    def _generate_positions_report(self):
        """Generate current positions and evaluation report"""
        conn = self.get_db_connection()
        
        # Get current positions
        positions_query = """
        SELECT 
            portfolio_type,
            symbol,
            quantity,
            avg_entry_price,
            total_invested,
            current_price,
            current_value,
            unrealized_pnl,
            unrealized_pnl_percent,
            last_updated
        FROM portfolio_positions
        ORDER BY total_invested DESC
        """
        
        positions_df = pd.read_sql_query(positions_query, conn)
        
        # Get current market data for evaluation
        stocks_query = "SELECT symbol, current_price, score, change_percent, volume, market_cap FROM stocks"
        cryptos_query = "SELECT symbol, current_price as currentPrice, score, change_percent as changePercent, volume, market_cap as marketCap FROM cryptos"
        
        stocks_market = pd.read_sql_query(stocks_query, conn)
        cryptos_market = pd.read_sql_query(cryptos_query, conn)
        
        with pd.ExcelWriter(
            self.output_dir / f"Current_Positions_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            engine='openpyxl'
        ) as writer:
            
            if not positions_df.empty:
                # Current positions
                positions_display = positions_df.copy()
                positions_display['last_updated'] = pd.to_datetime(positions_display['last_updated']).dt.date
                positions_display.to_excel(writer, sheet_name='Current_Positions', index=False)
                
                # Positions evaluation
                evaluation_data = []
                
                for _, position in positions_df.iterrows():
                    symbol = position['symbol']
                    portfolio_type = position['portfolio_type']
                    
                    # Get current market data
                    if portfolio_type == 'stocks':
                        market_data = stocks_market[stocks_market['symbol'] == symbol]
                    else:
                        market_data = cryptos_market[cryptos_market['symbol'] == symbol]
                    
                    if not market_data.empty:
                        market_row = market_data.iloc[0]
                        
                        # Days held calculation (simplified)
                        entry_date = datetime.now() - timedelta(days=30)  # Approximate
                        days_held = (datetime.now() - entry_date).days
                        
                        evaluation_data.append({
                            'Symbol': symbol,
                            'Portfolio': portfolio_type.upper(),
                            'Quantity': position['quantity'],
                            'Entry_Price': position['avg_entry_price'],
                            'Current_Price': market_row.get('current_price', market_row.get('currentPrice', 0)),
                            'Total_Invested': position['total_invested'],
                            'Current_Value': position['current_value'] or 0,
                            'Unrealized_PnL': position['unrealized_pnl'] or 0,
                            'Unrealized_PnL_Percent': position['unrealized_pnl_percent'] or 0,
                            'Current_Score': market_row['score'],
                            'Daily_Change_Percent': market_row.get('change_percent', market_row.get('changePercent', 0)),
                            'Volume': market_row['volume'],
                            'Market_Cap': market_row.get('market_cap', market_row.get('marketCap', 0)),
                            'Days_Held_Approx': days_held,
                            'Recommendation': self._get_position_recommendation(
                                market_row['score'], 
                                position['unrealized_pnl_percent'] or 0,
                                market_row.get('change_percent', market_row.get('changePercent', 0))
                            )
                        })
                
                if evaluation_data:
                    evaluation_df = pd.DataFrame(evaluation_data)
                    evaluation_df.to_excel(writer, sheet_name='Position_Evaluation', index=False)
            
            # Portfolio configuration
            config_query = """
            SELECT 
                type as Portfolio,
                initial_capital as Initial_Capital,
                current_capital as Current_Capital,
                available_cash as Available_Cash,
                invested_amount as Invested_Amount,
                total_pnl as Total_PnL,
                (total_pnl / initial_capital * 100) as ROI_Percent,
                total_trades as Total_Trades,
                last_updated as Last_Updated
            FROM portfolio_config
            """
            
            config_df = pd.read_sql_query(config_query, conn)
            config_df.to_excel(writer, sheet_name='Portfolio_Config', index=False)
        
        conn.close()
        logger.info("Positions report generated")
    
    def _get_position_recommendation(self, score: float, unrealized_pnl_pct: float, daily_change_pct: float) -> str:
        """Generate recommendation based on current metrics"""
        if score >= 7:
            return "HOLD - Strong score"
        elif score <= 3:
            if unrealized_pnl_pct < -10:
                return "CONSIDER SELL - Low score & significant loss"
            else:
                return "WATCH - Low score"
        elif unrealized_pnl_pct > 20:
            return "CONSIDER TAKING PROFITS - Good gains"
        elif unrealized_pnl_pct < -15:
            return "REVIEW - Significant unrealized loss"
        else:
            return "HOLD - Monitor score changes"
    
    def _generate_buy_signals_report(self):
        """Generate current buy signals report (updated, removes old signals)"""
        conn = self.get_db_connection()
        
        # Get current market data with scores
        stocks_query = """
        SELECT 
            symbol,
            name,
            current_price,
            score,
            change_amount as daily_change,
            change_percent,
            volume,
            market_cap,
            sector,
            'stocks' as asset_type
        FROM stocks 
        WHERE score >= 6
        ORDER BY score DESC, change_percent ASC
        """
        
        cryptos_query = """
        SELECT 
            symbol,
            name,
            current_price as currentPrice,
            score,
            change_amount as daily_change,
            change_percent as changePercent,
            volume,
            market_cap as marketCap,
            '' as sector,
            'crypto' as asset_type
        FROM cryptos 
        WHERE score >= 5
        ORDER BY score DESC, change_percent ASC
        """
        
        stocks_signals = pd.read_sql_query(stocks_query, conn)
        cryptos_signals = pd.read_sql_query(cryptos_query, conn)
        
        # Normalize column names
        if not cryptos_signals.empty:
            cryptos_signals = cryptos_signals.rename(columns={
                'currentPrice': 'current_price',
                'changePercent': 'change_percent',
                'marketCap': 'market_cap'
            })
        
        with pd.ExcelWriter(
            self.output_dir / f"Buy_Signals_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            engine='openpyxl'
        ) as writer:
            
            # Combined signals
            all_signals = []
            
            if not stocks_signals.empty:
                all_signals.append(stocks_signals)
            
            if not cryptos_signals.empty:
                all_signals.append(cryptos_signals)
            
            if all_signals:
                combined_df = pd.concat(all_signals, ignore_index=True)
                combined_df = combined_df.sort_values(['score', 'change_percent'], ascending=[False, True])
                
                # Add analysis columns
                combined_df['signal_strength'] = combined_df.apply(self._calculate_signal_strength, axis=1)
                combined_df['risk_level'] = combined_df['asset_type'].map({'stocks': 'Medium', 'crypto': 'High'})
                combined_df['generated_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # Display columns
                display_df = combined_df[[
                    'symbol', 'name', 'asset_type', 'current_price', 'score', 
                    'daily_change', 'change_percent', 'volume', 'market_cap', 
                    'sector', 'signal_strength', 'risk_level', 'generated_time'
                ]].copy()
                
                display_df.to_excel(writer, sheet_name='All_Buy_Signals', index=False)
                
                # Stocks only
                stocks_display = display_df[display_df['asset_type'] == 'stocks'].copy()
                if not stocks_display.empty:
                    stocks_display.to_excel(writer, sheet_name='Stock_Signals', index=False)
                
                # Crypto only
                crypto_display = display_df[display_df['asset_type'] == 'crypto'].copy()
                if not crypto_display.empty:
                    crypto_display.to_excel(writer, sheet_name='Crypto_Signals', index=False)
                
                # Signal summary
                summary_data = [{
                    'Total_Signals': len(combined_df),
                    'Stock_Signals': len(stocks_display) if not stocks_display.empty else 0,
                    'Crypto_Signals': len(crypto_display) if not crypto_display.empty else 0,
                    'Strong_Signals': len(combined_df[combined_df['signal_strength'] == 'Strong']),
                    'Medium_Signals': len(combined_df[combined_df['signal_strength'] == 'Medium']),
                    'Weak_Signals': len(combined_df[combined_df['signal_strength'] == 'Weak']),
                    'Avg_Score': combined_df['score'].mean(),
                    'Generated_At': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }]
                
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name='Signal_Summary', index=False)
        
        conn.close()
        logger.info("Buy signals report generated")
    
    def _calculate_signal_strength(self, row) -> str:
        """Calculate signal strength based on score and other factors"""
        score = row['score']
        change_pct = row['change_percent']
        
        if score >= 8:
            return "Strong"
        elif score >= 7:
            if change_pct <= -2:  # Dip buying opportunity
                return "Strong"
            else:
                return "Medium"
        elif score >= 6:
            if change_pct <= -5:
                return "Medium"
            else:
                return "Weak"
        else:
            return "Weak"
    
    def _generate_portfolio_summary_report(self):
        """Generate comprehensive portfolio summary"""
        conn = self.get_db_connection()
        
        with pd.ExcelWriter(
            self.output_dir / f"Portfolio_Summary_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            engine='openpyxl'
        ) as writer:
            
            # Portfolio overview
            overview_query = """
            SELECT 
                type as Portfolio,
                initial_capital as Initial_Capital,
                current_capital as Current_Capital,
                available_cash as Available_Cash,
                invested_amount as Invested_Amount,
                total_pnl as Total_PnL,
                (total_pnl / initial_capital * 100) as ROI_Percent,
                total_trades as Total_Trades
            FROM portfolio_config
            """
            
            overview_df = pd.read_sql_query(overview_query, conn)
            overview_df.to_excel(writer, sheet_name='Portfolio_Overview', index=False)
            
            # Recent performance (last 30 days transactions)
            recent_query = """
            SELECT 
                portfolio_type,
                COUNT(*) as Transactions,
                SUM(CASE WHEN action = 'buy' THEN total_amount ELSE 0 END) as Buy_Volume,
                SUM(CASE WHEN action = 'sell' THEN total_amount ELSE 0 END) as Sell_Volume,
                COUNT(DISTINCT symbol) as Unique_Symbols
            FROM portfolio_transactions 
            WHERE timestamp >= date('now', '-30 days')
            GROUP BY portfolio_type
            """
            
            recent_df = pd.read_sql_query(recent_query, conn)
            if not recent_df.empty:
                recent_df['Net_Flow'] = recent_df['Sell_Volume'] - recent_df['Buy_Volume']
                recent_df.to_excel(writer, sheet_name='Recent_Performance', index=False)
            
            # Top performers
            top_performers_query = """
            SELECT 
                symbol,
                portfolio_type,
                COUNT(*) as Trade_Count,
                SUM(CASE WHEN action = 'sell' THEN total_amount ELSE -total_amount END) as Net_PnL,
                AVG(score) as Avg_Score
            FROM portfolio_transactions 
            GROUP BY symbol, portfolio_type
            HAVING Trade_Count >= 2
            ORDER BY Net_PnL DESC
            LIMIT 20
            """
            
            top_performers_df = pd.read_sql_query(top_performers_query, conn)
            if not top_performers_df.empty:
                top_performers_df.to_excel(writer, sheet_name='Top_Performers', index=False)
        
        conn.close()
        logger.info("Portfolio summary report generated")
    
    def cleanup_old_reports(self, days_to_keep: int = 7):
        """Remove old Excel reports"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            for file_path in self.output_dir.glob("*.xlsx"):
                if file_path.stat().st_mtime < cutoff_date.timestamp():
                    file_path.unlink()
                    logger.info(f"Removed old report: {file_path.name}")
            
        except Exception as e:
            logger.error(f"Error cleaning up old reports: {str(e)}")

# Service instance
excel_reports_service = ExcelReportsService()