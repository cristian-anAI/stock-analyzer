"""
Machine Learning Module for Box Strategy Backtesting

Phase 3 implementation: ML-enhanced trade prediction and filtering.

Components:
- feature_engineering: Extract 50+ features from trading data
- ml_models: Train and manage multiple ML models (RF, XGBoost, LightGBM, PyTorch)
- ml_predictor: Daily scoring system with confidence levels
- ml_backtest_integration: ML-filtered backtesting
- model_evaluator: Model performance analysis
- train_models: Automated training pipeline
- ml_config: Centralized configuration
"""

__version__ = "1.0.0"
__author__ = "Stock Analyzer ML Team"

# Make key components available at package level
try:
    from .feature_engineering import FeatureEngineer
    from .ml_models import MLModelTrainer, MLModelManager
    from .ml_predictor import MLPredictor, ConfidenceLevel, TradeRecommendation
    from .ml_config import ML_CONFIG

    __all__ = [
        'FeatureEngineer',
        'MLModelTrainer',
        'MLModelManager',
        'MLPredictor',
        'ConfidenceLevel',
        'TradeRecommendation',
        'ML_CONFIG'
    ]
except ImportError:
    # Modules not yet created or dependencies not installed
    __all__ = []
