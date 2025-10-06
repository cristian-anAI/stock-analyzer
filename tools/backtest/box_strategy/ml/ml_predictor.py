"""
ML Prediction System for Box Strategy

Daily scoring system that predicts trade success probability and provides recommendations.

Features:
- Load trained ML models
- Predict win probability (0-100%)
- Classify confidence levels: HIGH, MEDIUM, LOW
- Generate trade recommendations: TRADE, REDUCE_SIZE, SKIP
- Model explainability with SHAP values
- Ensemble predictions combining multiple models
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
import warnings

warnings.filterwarnings('ignore')

# SHAP for model interpretability
try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False

from .ml_models import MLModelManager
from .feature_engineering import FeatureEngineer, TradeFeatures
from .ml_config import ML_CONFIG


class ConfidenceLevel(Enum):
    """Confidence classification"""
    HIGH = "HIGH"      # >= 75% win probability
    MEDIUM = "MEDIUM"  # 50-75% win probability
    LOW = "LOW"        # < 50% win probability


class TradeRecommendation(Enum):
    """Trade action recommendation"""
    TRADE = "TRADE"              # Full position (high confidence)
    REDUCE_SIZE = "REDUCE_SIZE"  # Partial position (medium confidence)
    SKIP = "SKIP"                # No trade (low confidence)


@dataclass
class PredictionResult:
    """Prediction result with all metrics"""
    win_probability: float  # 0.0 to 1.0
    confidence_level: ConfidenceLevel
    recommendation: TradeRecommendation
    position_size_multiplier: float  # 0.0 to 1.0
    model_used: str
    top_features: Optional[List[Tuple[str, float]]] = None  # Feature importance
    prediction_details: Optional[Dict] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'win_probability': self.win_probability,
            'win_probability_pct': f"{self.win_probability * 100:.1f}%",
            'confidence_level': self.confidence_level.value,
            'recommendation': self.recommendation.value,
            'position_size_multiplier': self.position_size_multiplier,
            'model_used': self.model_used,
            'top_features': self.top_features,
            'prediction_details': self.prediction_details
        }

    def __str__(self) -> str:
        """String representation"""
        return (
            f"Prediction: {self.win_probability*100:.1f}% win probability\n"
            f"Confidence: {self.confidence_level.value}\n"
            f"Recommendation: {self.recommendation.value}\n"
            f"Position Size: {self.position_size_multiplier*100:.0f}%\n"
            f"Model: {self.model_used}"
        )


class MLPredictor:
    """ML-based trade prediction system"""

    def __init__(self, version: str = "1", model_name: Optional[str] = None, config: Optional[Dict] = None):
        """
        Initialize ML predictor

        Args:
            version: Model version to load
            model_name: Specific model to use (default: ensemble or best available)
            config: Optional configuration (uses ML_CONFIG if not provided)
        """
        self.version = version
        self.config = config or ML_CONFIG
        self.prediction_config = self.config['prediction']

        # Confidence thresholds
        self.confidence_high_threshold = self.prediction_config['confidence_high_threshold']
        self.confidence_medium_threshold = self.prediction_config['confidence_medium_threshold']

        # Recommendation thresholds
        self.trade_threshold = self.prediction_config['trade_threshold']
        self.skip_threshold = self.prediction_config['skip_threshold']

        # Position size multipliers
        self.position_multipliers = self.prediction_config['confidence_position_multipliers']

        # Load models
        self.model_manager = MLModelManager(version=version)

        # Determine which model to use
        if model_name:
            self.model_name = model_name
        elif self.prediction_config.get('use_ensemble', True):
            self.model_name = 'ensemble'
        else:
            self.model_name = self.prediction_config.get('fallback_model', 'xgboost')

        # Load models
        self._load_models()

        # Feature engineer
        self.feature_engineer = FeatureEngineer(config=self.config)

        # SHAP explainer (for model interpretability)
        self.shap_explainer = None
        if SHAP_AVAILABLE and self.config['evaluation'].get('use_shap', True):
            self._initialize_shap()

        print(f"MLPredictor initialized (version: {version}, model: {self.model_name})")

    def _load_models(self):
        """Load trained models"""
        # Try to load specified model
        try:
            self.model_manager.load_models([self.model_name])

            if self.model_name not in self.model_manager.models:
                # Fallback to any available model
                print(f"Model '{self.model_name}' not found, loading all available models...")
                self.model_manager.load_models()

                if self.model_manager.models:
                    # Use first available model
                    self.model_name = list(self.model_manager.models.keys())[0]
                    print(f"Using fallback model: {self.model_name}")
                else:
                    raise ValueError("No models available! Please train models first.")
        except Exception as e:
            print(f"Error loading models: {e}")
            raise

    def _initialize_shap(self):
        """Initialize SHAP explainer for model interpretability"""
        if not SHAP_AVAILABLE:
            return

        try:
            model = self.model_manager.models.get(self.model_name)
            if model is None:
                return

            # Create SHAP explainer based on model type
            if self.model_name in ['random_forest', 'xgboost', 'lightgbm']:
                # Tree-based models
                self.shap_explainer = shap.TreeExplainer(model)
                print("SHAP explainer initialized (TreeExplainer)")
            else:
                # Use KernelExplainer for other models (slower but more general)
                print("SHAP explainer not initialized for this model type")
        except Exception as e:
            print(f"Failed to initialize SHAP: {e}")

    def predict_from_features(self, features: TradeFeatures, explain: bool = False) -> PredictionResult:
        """
        Predict trade outcome from features

        Args:
            features: TradeFeatures object
            explain: Whether to include SHAP explanations

        Returns:
            PredictionResult with all prediction metrics
        """
        # Convert features to array
        X = features.to_array(exclude_target=True, exclude_categorical=True)
        X = X.reshape(1, -1)  # Single sample

        # Get prediction probability
        y_proba = self.model_manager.predict_proba(X, model_name=self.model_name)
        win_probability = y_proba[0, 1]  # Probability of class 1 (win)

        # Classify confidence level
        confidence_level = self._classify_confidence(win_probability)

        # Generate recommendation
        recommendation = self._generate_recommendation(win_probability)

        # Get position size multiplier
        position_size_multiplier = self.position_multipliers[confidence_level.value]

        # Get feature importance (if SHAP available)
        top_features = None
        if explain and self.shap_explainer is not None:
            top_features = self._get_top_features(X)

        # Create result
        result = PredictionResult(
            win_probability=win_probability,
            confidence_level=confidence_level,
            recommendation=recommendation,
            position_size_multiplier=position_size_multiplier,
            model_used=self.model_name,
            top_features=top_features,
            prediction_details={
                'thresholds': {
                    'high_confidence': self.confidence_high_threshold,
                    'medium_confidence': self.confidence_medium_threshold,
                    'trade': self.trade_threshold,
                    'skip': self.skip_threshold
                }
            }
        )

        return result

    def predict_from_trade_data(self, trade_data: Dict, df_5min: Optional[pd.DataFrame] = None,
                               df_1hour: Optional[pd.DataFrame] = None,
                               market_config: Optional[Dict] = None,
                               explain: bool = False) -> PredictionResult:
        """
        Predict from raw trade data

        Args:
            trade_data: Dictionary with trade information
            df_5min: 5-minute OHLCV data (optional, improves feature quality)
            df_1hour: 1-hour OHLCV data (optional)
            market_config: Market configuration
            explain: Whether to include explanations

        Returns:
            PredictionResult
        """
        # Extract features
        if df_5min is not None:
            features = self.feature_engineer.extract_features_from_trade(
                trade_data, df_5min, df_1hour, market_config
            )
        else:
            # Use simplified feature extraction
            features = self.feature_engineer._create_features_from_trade_only(
                trade_data, trade_data.get('market', 'UNKNOWN'), market_config
            )

        # Predict
        return self.predict_from_features(features, explain=explain)

    def predict_batch(self, features_list: List[TradeFeatures]) -> List[PredictionResult]:
        """
        Predict multiple trades at once

        Args:
            features_list: List of TradeFeatures

        Returns:
            List of PredictionResult
        """
        results = []

        # Convert to array
        X = np.array([f.to_array(exclude_target=True, exclude_categorical=True) for f in features_list])

        # Batch prediction
        y_proba = self.model_manager.predict_proba(X, model_name=self.model_name)

        for i, win_prob in enumerate(y_proba[:, 1]):
            confidence = self._classify_confidence(win_prob)
            recommendation = self._generate_recommendation(win_prob)
            position_mult = self.position_multipliers[confidence.value]

            result = PredictionResult(
                win_probability=win_prob,
                confidence_level=confidence,
                recommendation=recommendation,
                position_size_multiplier=position_mult,
                model_used=self.model_name
            )
            results.append(result)

        return results

    def _classify_confidence(self, probability: float) -> ConfidenceLevel:
        """Classify confidence level based on probability"""
        if probability >= self.confidence_high_threshold:
            return ConfidenceLevel.HIGH
        elif probability >= self.confidence_medium_threshold:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW

    def _generate_recommendation(self, probability: float) -> TradeRecommendation:
        """Generate trade recommendation"""
        if probability >= self.trade_threshold:
            return TradeRecommendation.TRADE
        elif probability >= self.skip_threshold:
            return TradeRecommendation.REDUCE_SIZE
        else:
            return TradeRecommendation.SKIP

    def _get_top_features(self, X: np.ndarray, top_n: int = 10) -> List[Tuple[str, float]]:
        """
        Get top N most important features for the prediction

        Args:
            X: Feature array (single sample)
            top_n: Number of top features to return

        Returns:
            List of (feature_name, importance_value) tuples
        """
        if self.shap_explainer is None or not SHAP_AVAILABLE:
            return None

        try:
            # Calculate SHAP values
            shap_values = self.shap_explainer.shap_values(X)

            # For binary classification, shap_values might be a list
            if isinstance(shap_values, list):
                shap_values = shap_values[1]  # Values for positive class

            # Get absolute importance
            importance = np.abs(shap_values[0])

            # Get feature names
            feature_names = self.model_manager.feature_names

            # Create tuples and sort
            feature_importance = list(zip(feature_names, importance))
            feature_importance.sort(key=lambda x: x[1], reverse=True)

            return feature_importance[:top_n]

        except Exception as e:
            print(f"Error calculating SHAP values: {e}")
            return None

    def evaluate_setup(self, box_setup: Dict, market_data: Optional[pd.DataFrame] = None,
                      market_config: Optional[Dict] = None) -> Dict:
        """
        Evaluate a box setup and provide trading decision

        Args:
            box_setup: Box setup data (from strategy)
            market_data: Historical market data
            market_config: Market configuration

        Returns:
            Dictionary with prediction and recommendation
        """
        # Create trade data from box setup
        trade_data = {
            'box_high': box_setup['box_high'],
            'box_low': box_setup['box_low'],
            'box_range': box_setup['box_range'],
            'direction': box_setup.get('direction', 'LONG'),
            'entry_time': box_setup.get('entry_time', pd.Timestamp.now()),
            'entry_price': box_setup.get('entry_price', box_setup['box_high']),
            'stop_loss': box_setup.get('stop_loss', box_setup['box_low']),
            'risk_points': box_setup.get('risk_points', box_setup['box_range']),
            'pnl_points': 0,  # Unknown yet
            'market': box_setup.get('market', 'UNKNOWN')
        }

        # Predict
        prediction = self.predict_from_trade_data(
            trade_data,
            df_5min=market_data,
            market_config=market_config,
            explain=True
        )

        # Format result
        result = {
            'should_trade': prediction.recommendation != TradeRecommendation.SKIP,
            'prediction': prediction.to_dict(),
            'trading_advice': self._generate_trading_advice(prediction)
        }

        return result

    def _generate_trading_advice(self, prediction: PredictionResult) -> str:
        """Generate human-readable trading advice"""
        prob_pct = prediction.win_probability * 100
        pos_size_pct = prediction.position_size_multiplier * 100

        if prediction.recommendation == TradeRecommendation.TRADE:
            advice = (
                f"TRADE RECOMMENDED (High Confidence)\n"
                f"Win Probability: {prob_pct:.1f}%\n"
                f"Position Size: {pos_size_pct:.0f}% of normal size\n"
                f"This setup has strong indicators for success."
            )
        elif prediction.recommendation == TradeRecommendation.REDUCE_SIZE:
            advice = (
                f"TRADE WITH CAUTION (Medium Confidence)\n"
                f"Win Probability: {prob_pct:.1f}%\n"
                f"Position Size: {pos_size_pct:.0f}% of normal size\n"
                f"Consider reducing position size due to moderate confidence."
            )
        else:  # SKIP
            advice = (
                f"SKIP TRADE (Low Confidence)\n"
                f"Win Probability: {prob_pct:.1f}%\n"
                f"This setup has weak indicators. Consider waiting for better opportunities."
            )

        # Add top features if available
        if prediction.top_features:
            advice += "\n\nKey Factors:"
            for feature, importance in prediction.top_features[:5]:
                advice += f"\n  - {feature}: {importance:.3f}"

        return advice

    def get_statistics(self) -> Dict:
        """Get predictor statistics"""
        return {
            'version': self.version,
            'model_name': self.model_name,
            'models_loaded': list(self.model_manager.models.keys()),
            'num_features': len(self.model_manager.feature_names),
            'scaler_loaded': self.model_manager.scaler is not None,
            'shap_available': self.shap_explainer is not None,
            'thresholds': {
                'confidence_high': self.confidence_high_threshold,
                'confidence_medium': self.confidence_medium_threshold,
                'trade': self.trade_threshold,
                'skip': self.skip_threshold
            },
            'position_multipliers': self.position_multipliers
        }


# ============================================================
# UTILITY FUNCTIONS
# ============================================================
def quick_prediction(box_setup: Dict, model_version: str = "1") -> Dict:
    """
    Quick prediction function for convenience

    Args:
        box_setup: Box setup dictionary
        model_version: Model version to use

    Returns:
        Prediction result dictionary
    """
    predictor = MLPredictor(version=model_version)
    return predictor.evaluate_setup(box_setup)


def batch_predict_setups(setups: List[Dict], model_version: str = "1") -> pd.DataFrame:
    """
    Batch predict multiple setups

    Args:
        setups: List of box setup dictionaries
        model_version: Model version

    Returns:
        DataFrame with predictions for all setups
    """
    predictor = MLPredictor(version=model_version)
    results = []

    for setup in setups:
        pred = predictor.evaluate_setup(setup)
        results.append({
            'market': setup.get('market', 'UNKNOWN'),
            'box_range': setup['box_range'],
            'win_probability': pred['prediction']['win_probability'],
            'confidence': pred['prediction']['confidence_level'],
            'recommendation': pred['prediction']['recommendation'],
            'should_trade': pred['should_trade']
        })

    return pd.DataFrame(results)


# ============================================================
# EXAMPLE USAGE
# ============================================================
if __name__ == "__main__":
    # Example box setup
    example_setup = {
        'market': 'SPX',
        'box_high': 5850.0,
        'box_low': 5820.0,
        'box_range': 30.0,
        'direction': 'LONG',
        'entry_price': 5851.0,
        'stop_loss': 5820.0,
        'risk_points': 31.0,
        'entry_time': pd.Timestamp.now()
    }

    # Make prediction
    predictor = MLPredictor(version="1")
    result = predictor.evaluate_setup(example_setup)

    print("\n" + "="*80)
    print("BOX SETUP EVALUATION")
    print("="*80)
    print(f"\nSetup: {example_setup['market']} - Box Range: {example_setup['box_range']} points")
    print(f"\n{result['trading_advice']}")
    print("\n" + "="*80)
