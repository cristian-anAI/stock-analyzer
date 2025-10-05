"""
Monthly Score Debug Logger
Comprehensive logging system for debugging monthly scoring issues
"""

import logging
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class MonthlyScoreDebugLogger:
    """Dedicated logger for monthly scoring debugging"""
    
    def __init__(self, log_dir: str = "logs/monthly_scoring"):
        self.log_dir = log_dir
        self.ensure_log_directory()
        
        # Set up dedicated file handler for monthly scoring
        self.debug_logger = self._setup_debug_logger()
        
    def ensure_log_directory(self):
        """Ensure log directory exists"""
        os.makedirs(self.log_dir, exist_ok=True)
        
    def _setup_debug_logger(self):
        """Set up dedicated logger for monthly scoring debug"""
        debug_logger = logging.getLogger('monthly_scoring_debug')
        debug_logger.setLevel(logging.DEBUG)
        
        # File handler for detailed debug logs
        debug_file = os.path.join(self.log_dir, f"monthly_debug_{datetime.now().strftime('%Y%m%d')}.log")
        file_handler = logging.FileHandler(debug_file)
        file_handler.setLevel(logging.DEBUG)
        
        # Detailed formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - [%(funcName)s:%(lineno)d] - %(message)s'
        )
        file_handler.setFormatter(formatter)
        
        if not debug_logger.handlers:
            debug_logger.addHandler(file_handler)
        
        return debug_logger
        
    def log_monthly_score_calculation(self, symbol: str, asset_type: str, 
                                    calculation_data: Dict[str, Any]):
        """Log detailed monthly score calculation"""
        timestamp = datetime.now().isoformat()
        
        log_entry = {
            'timestamp': timestamp,
            'symbol': symbol,
            'asset_type': asset_type,
            'calculation_type': 'monthly_score',
            'data': calculation_data
        }
        
        self.debug_logger.info(f"MONTHLY_SCORE_CALC: {json.dumps(log_entry, indent=2)}")
        
        # Also log human-readable summary
        data_periods = calculation_data.get('data_periods', 0)
        macd_histogram = calculation_data.get('macd_histogram', 0)
        final_score = calculation_data.get('final_score', 0)
        data_quality = calculation_data.get('data_quality', 'unknown')
        
        summary = (f"MONTHLY: {symbol} | {data_periods} periods | "
                  f"MACD: {macd_histogram:.4f} | Score: {final_score:.1f} | "
                  f"Quality: {data_quality}")
        
        self.debug_logger.info(summary)
        
    def log_unified_score_breakdown(self, symbol: str, unified_result: Dict[str, Any]):
        """Log complete unified score breakdown"""
        timestamp = datetime.now().isoformat()
        
        log_entry = {
            'timestamp': timestamp,
            'symbol': symbol,
            'calculation_type': 'unified_score_breakdown',
            'unified_score': unified_result.get('unified_score', 0),
            'trading_signal': unified_result.get('trading_signal', 'HOLD'),
            'confidence': unified_result.get('confidence', 0),
            'breakdown': unified_result.get('breakdown', {}),
            'recommendations': unified_result.get('recommendations', {}),
            'debug_info': unified_result.get('debug_info', {})
        }
        
        self.debug_logger.info(f"UNIFIED_BREAKDOWN: {json.dumps(log_entry, indent=2)}")
        
        # Log human-readable summary
        mtss_data = unified_result.get('breakdown', {}).get('mtss', {})
        monthly_filter = mtss_data.get('monthly_filter_passed', False)
        timeframe_scores = mtss_data.get('timeframe_scores', {})
        
        summary = (f"UNIFIED: {symbol} | Score: {unified_result.get('unified_score', 0):.2f} | "
                  f"Signal: {unified_result.get('trading_signal', 'HOLD')} | "
                  f"Monthly: {'PASS' if monthly_filter else 'FAIL'} | "
                  f"TF Scores: {timeframe_scores}")
        
        self.debug_logger.info(summary)
        
    def log_data_quality_issues(self, symbol: str, timeframe: str, 
                               quality_data: Dict[str, Any]):
        """Log data quality issues"""
        timestamp = datetime.now().isoformat()
        
        log_entry = {
            'timestamp': timestamp,
            'symbol': symbol,
            'timeframe': timeframe,
            'calculation_type': 'data_quality_issue',
            'quality_data': quality_data
        }
        
        self.debug_logger.warning(f"DATA_QUALITY_ISSUE: {json.dumps(log_entry, indent=2)}")
        
    def log_monthly_filter_decision(self, symbol: str, monthly_score: float, 
                                  threshold: float, passed: bool, reasoning: str):
        """Log monthly filter decisions"""
        timestamp = datetime.now().isoformat()
        
        log_entry = {
            'timestamp': timestamp,
            'symbol': symbol,
            'calculation_type': 'monthly_filter_decision',
            'monthly_score': monthly_score,
            'threshold': threshold,
            'filter_passed': passed,
            'reasoning': reasoning
        }
        
        self.debug_logger.info(f"MONTHLY_FILTER: {json.dumps(log_entry, indent=2)}")
        
        # Human-readable summary
        status = "PASSED" if passed else "BLOCKED"
        summary = (f"FILTER: {symbol} | Score: {monthly_score:.1f} | "
                  f"Threshold: {threshold} | {status} | {reasoning}")
        
        self.debug_logger.info(summary)
        
    def log_error(self, symbol: str, error_type: str, error_message: str, 
                  context: Optional[Dict[str, Any]] = None):
        """Log errors in monthly scoring"""
        timestamp = datetime.now().isoformat()
        
        log_entry = {
            'timestamp': timestamp,
            'symbol': symbol,
            'calculation_type': 'error',
            'error_type': error_type,
            'error_message': error_message,
            'context': context or {}
        }
        
        self.debug_logger.error(f"SCORING_ERROR: {json.dumps(log_entry, indent=2)}")
        
    def log_performance_metrics(self, symbol: str, calculation_time_ms: float, 
                               data_fetch_time_ms: float, method_breakdown: Dict[str, float]):
        """Log performance metrics"""
        timestamp = datetime.now().isoformat()
        
        log_entry = {
            'timestamp': timestamp,
            'symbol': symbol,
            'calculation_type': 'performance_metrics',
            'total_time_ms': calculation_time_ms,
            'data_fetch_time_ms': data_fetch_time_ms,
            'scoring_time_ms': calculation_time_ms - data_fetch_time_ms,
            'method_breakdown_ms': method_breakdown
        }
        
        self.debug_logger.info(f"PERFORMANCE: {json.dumps(log_entry, indent=2)}")
        
    def generate_daily_summary(self) -> Dict[str, Any]:
        """Generate daily summary of monthly scoring issues"""
        try:
            today = datetime.now().strftime('%Y%m%d')
            log_file = os.path.join(self.log_dir, f"monthly_debug_{today}.log")
            
            if not os.path.exists(log_file):
                return {'error': 'No log file found for today'}
            
            with open(log_file, 'r') as f:
                lines = f.readlines()
            
            # Parse log entries
            monthly_calcs = 0
            unified_calcs = 0
            data_quality_issues = 0
            filter_blocks = 0
            filter_passes = 0
            errors = 0
            
            symbols_processed = set()
            avg_calculation_time = []
            
            for line in lines:
                if 'MONTHLY_SCORE_CALC' in line:
                    monthly_calcs += 1
                elif 'UNIFIED_BREAKDOWN' in line:
                    unified_calcs += 1
                    # Extract symbol
                    try:
                        symbol = line.split('symbol')[1].split(',')[0].strip(': "')
                        symbols_processed.add(symbol)
                    except:
                        pass
                elif 'DATA_QUALITY_ISSUE' in line:
                    data_quality_issues += 1
                elif 'MONTHLY_FILTER' in line:
                    if 'BLOCKED' in line:
                        filter_blocks += 1
                    elif 'PASSED' in line:
                        filter_passes += 1
                elif 'SCORING_ERROR' in line:
                    errors += 1
                elif 'PERFORMANCE' in line:
                    # Extract timing data
                    try:
                        import re
                        time_match = re.search(r'"total_time_ms": ([\d.]+)', line)
                        if time_match:
                            avg_calculation_time.append(float(time_match.group(1)))
                    except:
                        pass
            
            summary = {
                'date': today,
                'total_symbols_processed': len(symbols_processed),
                'monthly_score_calculations': monthly_calcs,
                'unified_score_calculations': unified_calcs,
                'data_quality_issues': data_quality_issues,
                'monthly_filter_blocks': filter_blocks,
                'monthly_filter_passes': filter_passes,
                'scoring_errors': errors,
                'avg_calculation_time_ms': sum(avg_calculation_time) / len(avg_calculation_time) if avg_calculation_time else 0,
                'symbols_processed': list(symbols_processed)
            }
            
            # Log summary
            self.debug_logger.info(f"DAILY_SUMMARY: {json.dumps(summary, indent=2)}")
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating daily summary: {e}")
            return {'error': str(e)}

# Global instance
monthly_debug_logger = MonthlyScoreDebugLogger()