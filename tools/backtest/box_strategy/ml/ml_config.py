"""
Machine Learning Configuration for Box Strategy

Centralized configuration for all ML components including:
- Feature engineering parameters
- Model hyperparameters (with GPU optimization)
- Training pipeline settings
- Prediction thresholds
- GPU/CUDA settings
"""

import torch
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).parent.parent
ML_DIR = BASE_DIR / "ml"
MODELS_DIR = BASE_DIR / "models"
ML_RESULTS_DIR = BASE_DIR / "ml_results"
DATA_DIR = BASE_DIR / "results"

# Create directories if they don't exist
MODELS_DIR.mkdir(exist_ok=True)
ML_RESULTS_DIR.mkdir(exist_ok=True)

# GPU/CUDA Configuration
GPU_AVAILABLE = torch.cuda.is_available()
GPU_NAME = torch.cuda.get_device_name(0) if GPU_AVAILABLE else "CPU"
DEVICE = torch.device('cuda' if GPU_AVAILABLE else 'cpu')

ML_CONFIG = {
    # ============================================================
    # FEATURE ENGINEERING
    # ============================================================
    'feature_engineering': {
        # Technical indicators
        'rsi_periods': [14, 21],  # RSI calculation periods
        'atr_period': 14,  # Average True Range period
        'bollinger_period': 20,  # Bollinger Bands period
        'bollinger_std': 2,  # Bollinger Bands standard deviation
        'macd_fast': 12,  # MACD fast period
        'macd_slow': 26,  # MACD slow period
        'macd_signal': 9,  # MACD signal period
        'ema_periods': [9, 21, 50],  # Exponential Moving Average periods

        # Volume analysis
        'volume_ma_period': 20,  # Volume moving average

        # Box characteristics
        'box_range_lookback': 20,  # Days to calculate box range percentile

        # Market conditions
        'market_trend_periods': [5, 10, 20],  # Days for trend calculation

        # Feature selection
        'min_feature_importance': 0.01,  # Minimum importance to keep feature
        'max_features': 50,  # Maximum number of features to use
    },

    # ============================================================
    # DATA SPLITTING & VALIDATION
    # ============================================================
    'training': {
        # Train/validation/test split
        'test_size': 0.2,  # 20% for final testing
        'validation_size': 0.2,  # 20% of training data for validation
        'shuffle': True,  # Shuffle data before splitting
        'random_state': 42,  # Reproducibility

        # Cross-validation
        'cv_folds': 5,  # K-fold cross-validation
        'cv_shuffle': True,

        # Class balancing
        'balance_classes': True,  # Use SMOTE or class weights
        'balancing_method': 'smote',  # 'smote', 'class_weight', or 'undersample'

        # Feature scaling
        'scale_features': True,  # StandardScaler
        'scaler_type': 'standard',  # 'standard', 'minmax', 'robust'
    },

    # ============================================================
    # MODEL HYPERPARAMETERS
    # ============================================================
    'models': {
        # Random Forest (CPU/GPU)
        'random_forest': {
            'n_estimators': 200,
            'max_depth': 15,
            'min_samples_split': 5,
            'min_samples_leaf': 2,
            'max_features': 'sqrt',
            'bootstrap': True,
            'n_jobs': -1,  # Use all CPU cores
            'random_state': 42,
            'class_weight': 'balanced'
        },

        # XGBoost (GPU-optimized)
        'xgboost': {
            'n_estimators': 150,
            'max_depth': 8,
            'learning_rate': 0.1,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'gamma': 0.1,
            'reg_alpha': 0.1,
            'reg_lambda': 1.0,
            'tree_method': 'gpu_hist' if GPU_AVAILABLE else 'hist',  # GPU acceleration
            'gpu_id': 0,
            'predictor': 'gpu_predictor' if GPU_AVAILABLE else 'auto',
            'random_state': 42,
            'eval_metric': 'logloss'
        },

        # LightGBM (GPU-optimized)
        'lightgbm': {
            'n_estimators': 150,
            'max_depth': 10,
            'learning_rate': 0.1,
            'num_leaves': 31,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'reg_alpha': 0.1,
            'reg_lambda': 1.0,
            'device': 'gpu' if GPU_AVAILABLE else 'cpu',  # GPU acceleration
            'gpu_platform_id': 0,
            'gpu_device_id': 0,
            'random_state': 42,
            'verbose': -1
        },

        # PyTorch Neural Network (GPU-optimized)
        'neural_network': {
            'hidden_layers': [128, 64, 32],  # Layer sizes
            'activation': 'relu',  # Activation function
            'dropout_rate': 0.3,  # Dropout for regularization
            'batch_size': 32,
            'epochs': 100,
            'learning_rate': 0.001,
            'optimizer': 'adam',  # 'adam', 'sgd', 'rmsprop'
            'weight_decay': 0.0001,  # L2 regularization
            'early_stopping_patience': 15,
            'device': str(DEVICE),  # 'cuda' or 'cpu'
            'random_state': 42
        },

        # Ensemble (Voting Classifier)
        'ensemble': {
            'voting': 'soft',  # 'soft' (probabilities) or 'hard' (majority vote)
            'weights': [1.5, 2.0, 2.0, 1.5],  # RF, XGBoost, LightGBM, NN
            'n_jobs': -1
        }
    },

    # ============================================================
    # HYPERPARAMETER TUNING
    # ============================================================
    'hyperparameter_tuning': {
        'enabled': False,  # Enable GridSearchCV/RandomizedSearchCV
        'method': 'random',  # 'grid' or 'random'
        'n_iter': 50,  # For RandomizedSearchCV
        'cv_folds': 3,
        'n_jobs': -1,
        'verbose': 2,

        # Parameter grids for tuning
        'param_grids': {
            'random_forest': {
                'n_estimators': [100, 200, 300],
                'max_depth': [10, 15, 20, None],
                'min_samples_split': [2, 5, 10]
            },
            'xgboost': {
                'n_estimators': [100, 150, 200],
                'max_depth': [6, 8, 10],
                'learning_rate': [0.05, 0.1, 0.15]
            }
        }
    },

    # ============================================================
    # PREDICTION SETTINGS
    # ============================================================
    'prediction': {
        # Confidence thresholds
        'confidence_high_threshold': 0.75,  # >= 75% = HIGH confidence
        'confidence_medium_threshold': 0.50,  # 50-75% = MEDIUM confidence
        # < 50% = LOW confidence

        # Trade recommendations
        'trade_threshold': 0.60,  # Min confidence to recommend TRADE
        'skip_threshold': 0.40,  # Below this = SKIP
        # Between skip and trade = REDUCE_SIZE

        # Position sizing adjustments
        'confidence_position_multipliers': {
            'HIGH': 1.0,  # Full position size
            'MEDIUM': 0.6,  # 60% position size
            'LOW': 0.0  # No trade
        },

        # Model selection
        'use_ensemble': True,  # Use ensemble model by default
        'fallback_model': 'xgboost'  # If ensemble not available
    },

    # ============================================================
    # MODEL EVALUATION
    # ============================================================
    'evaluation': {
        # Metrics to calculate
        'metrics': [
            'accuracy', 'precision', 'recall', 'f1',
            'roc_auc', 'confusion_matrix', 'classification_report'
        ],

        # Visualization
        'generate_plots': True,
        'plot_types': [
            'confusion_matrix', 'roc_curve', 'precision_recall_curve',
            'feature_importance', 'learning_curve', 'calibration_curve'
        ],
        'plot_dpi': 300,
        'plot_format': 'png',

        # SHAP analysis (model interpretability)
        'use_shap': True,
        'shap_sample_size': 100,  # Samples for SHAP calculation (can be slow)

        # Feature importance
        'top_n_features': 20  # Show top N important features
    },

    # ============================================================
    # BACKTESTING WITH ML
    # ============================================================
    'ml_backtest': {
        # ML filtering
        'enable_ml_filter': True,
        'min_confidence': 0.60,  # Only trade setups with >= 60% confidence

        # Position sizing
        'dynamic_position_sizing': True,  # Adjust size based on ML confidence

        # Comparison settings
        'compare_with_baseline': True,  # Compare ML vs no-ML performance

        # A/B testing
        'confidence_thresholds_to_test': [0.50, 0.55, 0.60, 0.65, 0.70, 0.75],
    },

    # ============================================================
    # MODEL PERSISTENCE
    # ============================================================
    'persistence': {
        'model_format': 'joblib',  # 'joblib' or 'pickle'
        'compress_level': 3,  # Compression level (0-9)
        'save_training_data': True,  # Save preprocessed training data
        'versioning': True,  # Add version suffix to saved models

        # Model filenames
        'model_names': {
            'random_forest': 'random_forest_v{version}.pkl',
            'xgboost': 'xgboost_v{version}.pkl',
            'lightgbm': 'lightgbm_v{version}.pkl',
            'neural_network': 'neural_network_v{version}.pth',  # PyTorch format
            'ensemble': 'ensemble_v{version}.pkl',
            'scaler': 'feature_scaler_v{version}.pkl',
            'feature_names': 'feature_names_v{version}.json'
        }
    },

    # ============================================================
    # LOGGING & DEBUGGING
    # ============================================================
    'logging': {
        'level': 'INFO',  # 'DEBUG', 'INFO', 'WARNING', 'ERROR'
        'log_file': str(ML_RESULTS_DIR / 'ml_training.log'),
        'log_to_console': True,
        'log_to_file': True,

        # Progress tracking
        'show_progress_bars': True,
        'verbose': 1  # 0: silent, 1: progress, 2: detailed
    }
}

# ============================================================
# GPU INFORMATION
# ============================================================
def print_gpu_info():
    """Print GPU configuration information"""
    print("\n" + "="*80)
    print("GPU/CUDA CONFIGURATION")
    print("="*80)
    print(f"GPU Available: {GPU_AVAILABLE}")
    print(f"Device: {GPU_NAME}")
    print(f"PyTorch Device: {DEVICE}")

    if GPU_AVAILABLE:
        print(f"CUDA Version: {torch.version.cuda}")
        print(f"PyTorch Version: {torch.__version__}")
        print(f"GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")
        print(f"\nXGBoost tree_method: {ML_CONFIG['models']['xgboost']['tree_method']}")
        print(f"LightGBM device: {ML_CONFIG['models']['lightgbm']['device']}")
        print(f"Neural Network device: {ML_CONFIG['models']['neural_network']['device']}")
    else:
        print("\nWARNING: GPU not available. Models will train on CPU (slower).")
        print("To enable GPU:")
        print("  1. Install CUDA Toolkit 11.8")
        print("  2. Install PyTorch with CUDA: pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118")
        print("  3. Rebuild XGBoost/LightGBM with GPU support")

    print("="*80 + "\n")

# ============================================================
# UTILITY FUNCTIONS
# ============================================================
def get_model_path(model_name: str, version: str = "1") -> Path:
    """Get full path for a model file"""
    filename = ML_CONFIG['persistence']['model_names'][model_name].format(version=version)
    return MODELS_DIR / filename

def get_latest_model_version(model_name: str) -> int:
    """Find the latest version number for a model"""
    pattern = ML_CONFIG['persistence']['model_names'][model_name].replace('{version}', '*')
    matching_files = list(MODELS_DIR.glob(pattern))

    if not matching_files:
        return 0

    # Extract version numbers
    versions = []
    for file in matching_files:
        try:
            # Extract version from filename
            version_str = file.stem.split('_v')[-1]
            versions.append(int(version_str))
        except (IndexError, ValueError):
            continue

    return max(versions) if versions else 0

def update_config(updates: dict):
    """Update ML_CONFIG with new values"""
    global ML_CONFIG

    def deep_update(base_dict, update_dict):
        for key, value in update_dict.items():
            if isinstance(value, dict) and key in base_dict:
                deep_update(base_dict[key], value)
            else:
                base_dict[key] = value

    deep_update(ML_CONFIG, updates)

# ============================================================
# VALIDATION
# ============================================================
def validate_config():
    """Validate configuration settings"""
    errors = []

    # Check GPU settings consistency
    if not GPU_AVAILABLE:
        if ML_CONFIG['models']['xgboost']['tree_method'] == 'gpu_hist':
            errors.append("XGBoost configured for GPU but CUDA not available")
        if ML_CONFIG['models']['lightgbm']['device'] == 'gpu':
            errors.append("LightGBM configured for GPU but CUDA not available")

    # Check thresholds
    if ML_CONFIG['prediction']['confidence_high_threshold'] <= ML_CONFIG['prediction']['confidence_medium_threshold']:
        errors.append("HIGH threshold must be > MEDIUM threshold")

    if ML_CONFIG['prediction']['trade_threshold'] <= ML_CONFIG['prediction']['skip_threshold']:
        errors.append("TRADE threshold must be > SKIP threshold")

    # Check directories exist
    for dir_path in [MODELS_DIR, ML_RESULTS_DIR, DATA_DIR]:
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)

    if errors:
        print("Configuration Validation Errors:")
        for error in errors:
            print(f"  - {error}")
        return False

    return True

# Run validation on import
if __name__ != "__main__":
    validate_config()
