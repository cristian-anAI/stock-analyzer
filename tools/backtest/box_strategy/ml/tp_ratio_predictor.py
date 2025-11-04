"""
TP Ratio Predictor - ML Model for Dynamic TP2/TP3

Predicts probability of reaching different R:R ratios within time windows.

Model Output:
- For each R:R ratio (2:1, 3:1, 4:1, ... 20:1)
- Probability of reaching that ratio in next 1h, 2h, 4h, 8h

TP Selection:
- TP2 = Highest ratio with P > 60%
- TP3 = Highest ratio with P > 45%
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import pickle
import warnings
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
import json

warnings.filterwarnings('ignore')


@dataclass
class TPRatioPrediction:
    """Prediction result for TP ratios"""
    # Probabilities for each ratio
    ratios: List[float]  # [2, 3, 4, ..., 20]
    probabilities_1h: List[float]
    probabilities_2h: List[float]
    probabilities_4h: List[float]
    probabilities_8h: List[float]

    # Recommended TPs
    tp2_ratio: float  # Highest with P > 60%
    tp2_probability: float
    tp2_timeframe: str  # '1h', '2h', '4h', '8h'

    tp3_ratio: float  # Highest with P > 45%
    tp3_probability: float
    tp3_timeframe: str

    # Metadata
    confidence_score: float  # Overall prediction confidence
    feature_importance: Dict[str, float]


class TPRatioMLModel:
    """
    ML Model to predict probability of reaching different R:R ratios
    """

    def __init__(self):
        """Initialize models for different timeframes"""
        self.models_1h = {}  # {ratio: model}
        self.models_2h = {}
        self.models_4h = {}
        self.models_8h = {}

        self.scaler = StandardScaler()
        self.feature_names = []

        self.ratios = [2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0,
                       11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0, 19.0, 20.0]

    def extract_features(self, ohlcv_data: np.ndarray, entry_idx: int,
                        entry_price: float, stop_loss: float,
                        direction: str, pivot_strength: float,
                        ema_value: float, vwap_value: float) -> np.ndarray:
        """
        Extract features for prediction

        Args:
            ohlcv_data: Historical OHLCV data
            entry_idx: Index of entry candle
            entry_price: Entry price
            stop_loss: Stop loss price
            direction: 'LONG' or 'SHORT'
            pivot_strength: Pivot strength score
            ema_value: EMA value at entry
            vwap_value: VWAP value at entry

        Returns:
            Feature array
        """
        if entry_idx < 100:
            raise ValueError("Need at least 100 candles before entry")

        # Get historical window
        window = ohlcv_data[entry_idx-100:entry_idx+1]
        closes = window[:, 4]
        highs = window[:, 2]
        lows = window[:, 3]
        volumes = window[:, 5]

        features = {}

        # 1. Price Position Features
        features['price_vs_ema'] = (entry_price - ema_value) / entry_price * 100
        features['price_vs_vwap'] = (entry_price - vwap_value) / entry_price * 100
        features['distance_to_sl_pct'] = abs(entry_price - stop_loss) / entry_price * 100

        # 2. Momentum Features
        features['momentum_5'] = (closes[-1] - closes[-5]) / closes[-5] * 100
        features['momentum_10'] = (closes[-1] - closes[-10]) / closes[-10] * 100
        features['momentum_20'] = (closes[-1] - closes[-20]) / closes[-20] * 100
        features['momentum_50'] = (closes[-1] - closes[-50]) / closes[-50] * 100

        # 3. Volatility Features
        returns = np.diff(closes) / closes[:-1]
        features['volatility_20'] = np.std(returns[-20:]) * 100
        features['volatility_50'] = np.std(returns[-50:]) * 100

        atr_14 = self._calculate_atr(highs[-14:], lows[-14:], closes[-14:])
        features['atr_14_pct'] = atr_14 / entry_price * 100

        # 4. Volume Features
        features['volume_ratio_20'] = volumes[-1] / np.mean(volumes[-20:])
        features['volume_trend_10'] = (np.mean(volumes[-10:]) - np.mean(volumes[-20:-10])) / np.mean(volumes[-20:-10])

        # 5. Trend Features
        sma_20 = np.mean(closes[-20:])
        sma_50 = np.mean(closes[-50:])
        features['price_vs_sma20'] = (entry_price - sma_20) / entry_price * 100
        features['price_vs_sma50'] = (entry_price - sma_50) / entry_price * 100
        features['sma20_vs_sma50'] = (sma_20 - sma_50) / sma_50 * 100

        # 6. Pivot Features
        features['pivot_strength'] = pivot_strength

        # 7. Pattern Features
        features['higher_highs'] = self._count_higher_highs(highs[-20:])
        features['higher_lows'] = self._count_higher_lows(lows[-20:])

        # 8. Range Features
        recent_high = np.max(highs[-20:])
        recent_low = np.min(lows[-20:])
        features['range_position'] = (entry_price - recent_low) / (recent_high - recent_low)
        features['range_size_pct'] = (recent_high - recent_low) / entry_price * 100

        # 9. Direction-specific features
        features['is_long'] = 1.0 if direction == 'LONG' else 0.0

        # 10. Time features (for intraday patterns)
        # Will be added when we have timestamp

        # Convert to array
        self.feature_names = sorted(features.keys())
        feature_array = np.array([features[k] for k in self.feature_names])

        return feature_array.reshape(1, -1)

    def _calculate_atr(self, highs, lows, closes):
        """Calculate Average True Range"""
        tr = np.maximum(
            highs - lows,
            np.maximum(
                np.abs(highs - np.roll(closes, 1)),
                np.abs(lows - np.roll(closes, 1))
            )
        )
        return np.mean(tr[1:])  # Skip first (invalid due to roll)

    def _count_higher_highs(self, highs):
        """Count number of higher highs in sequence"""
        count = 0
        for i in range(1, len(highs)):
            if highs[i] > highs[i-1]:
                count += 1
        return count

    def _count_higher_lows(self, lows):
        """Count number of higher lows in sequence"""
        count = 0
        for i in range(1, len(lows)):
            if lows[i] > lows[i-1]:
                count += 1
        return count

    def prepare_training_data(self, ohlcv_data: np.ndarray,
                            signals: List[Dict]) -> Tuple[Dict, Dict]:
        """
        Prepare training data from historical signals

        Args:
            ohlcv_data: Complete historical OHLCV data
            signals: List of historical signals with outcomes

        Returns:
            Tuple of (features_dict, labels_dict) for each timeframe
        """
        print(f"Preparing training data from {len(signals)} signals...")

        features_list = []
        labels_1h = {ratio: [] for ratio in self.ratios}
        labels_2h = {ratio: [] for ratio in self.ratios}
        labels_4h = {ratio: [] for ratio in self.ratios}
        labels_8h = {ratio: [] for ratio in self.ratios}

        skipped = 0

        for signal in signals:
            try:
                entry_idx = signal['entry_idx']
                entry_price = signal['entry_price']
                stop_loss = signal['stop_loss']
                direction = signal['direction']

                # Extract features
                features = self.extract_features(
                    ohlcv_data=ohlcv_data,
                    entry_idx=entry_idx,
                    entry_price=entry_price,
                    stop_loss=stop_loss,
                    direction=direction,
                    pivot_strength=signal.get('pivot_strength', 50.0),
                    ema_value=signal.get('ema_value', entry_price),
                    vwap_value=signal.get('vwap_value', entry_price)
                )

                # Calculate labels for each ratio and timeframe
                candles_1h = 60   # 60 candles = 1 hour (1-min data)
                candles_2h = 120
                candles_4h = 240
                candles_8h = 480

                risk = abs(entry_price - stop_loss)

                # Check each ratio
                for ratio in self.ratios:
                    target_price = entry_price + (risk * ratio) if direction == 'LONG' else entry_price - (risk * ratio)

                    # Check if target reached in each timeframe
                    labels_1h[ratio].append(
                        self._check_target_reached(ohlcv_data, entry_idx, target_price,
                                                   candles_1h, direction)
                    )
                    labels_2h[ratio].append(
                        self._check_target_reached(ohlcv_data, entry_idx, target_price,
                                                   candles_2h, direction)
                    )
                    labels_4h[ratio].append(
                        self._check_target_reached(ohlcv_data, entry_idx, target_price,
                                                   candles_4h, direction)
                    )
                    labels_8h[ratio].append(
                        self._check_target_reached(ohlcv_data, entry_idx, target_price,
                                                   candles_8h, direction)
                    )

                features_list.append(features.flatten())

            except Exception as e:
                skipped += 1
                continue

        print(f"Processed {len(features_list)} signals, skipped {skipped}")

        # Convert to arrays
        X = np.array(features_list)

        y_1h = {ratio: np.array(labels_1h[ratio]) for ratio in self.ratios}
        y_2h = {ratio: np.array(labels_2h[ratio]) for ratio in self.ratios}
        y_4h = {ratio: np.array(labels_4h[ratio]) for ratio in self.ratios}
        y_8h = {ratio: np.array(labels_8h[ratio]) for ratio in self.ratios}

        return X, {'1h': y_1h, '2h': y_2h, '4h': y_4h, '8h': y_8h}

    def _check_target_reached(self, ohlcv_data: np.ndarray, entry_idx: int,
                              target_price: float, candles: int, direction: str) -> int:
        """
        Check if target price was reached within timeframe

        Returns:
            1 if target reached, 0 otherwise
        """
        end_idx = min(entry_idx + candles, len(ohlcv_data))
        future_data = ohlcv_data[entry_idx+1:end_idx+1]

        if len(future_data) == 0:
            return 0

        if direction == 'LONG':
            highs = future_data[:, 2]
            return 1 if np.any(highs >= target_price) else 0
        else:  # SHORT
            lows = future_data[:, 3]
            return 1 if np.any(lows <= target_price) else 0

    def train(self, X: np.ndarray, y_dict: Dict) -> Dict:
        """
        Train models for all ratios and timeframes

        Args:
            X: Feature matrix
            y_dict: Labels dictionary {timeframe: {ratio: labels}}

        Returns:
            Training metrics
        """
        print(f"\nTraining TP Ratio Predictor...")
        print(f"Features: {len(self.feature_names)}")
        print(f"Samples: {len(X)}")
        print(f"Ratios: {len(self.ratios)}")
        print(f"Timeframes: 4 (1h, 2h, 4h, 8h)")

        # Scale features
        X_scaled = self.scaler.fit_transform(X)

        metrics = {}

        # Train models for each timeframe and ratio
        for tf_name, y_ratios in y_dict.items():
            print(f"\n=== Training {tf_name} models ===")

            models_dict = {}
            tf_metrics = {}

            for ratio in self.ratios:
                y = y_ratios[ratio]

                # Check class balance
                positive_rate = np.mean(y)

                if positive_rate < 0.05 or positive_rate > 0.95:
                    print(f"  Ratio {ratio:>4.1f}: Skipped (imbalanced: {positive_rate*100:.1f}%)")
                    continue

                # Train Gradient Boosting model
                model = GradientBoostingClassifier(
                    n_estimators=100,
                    max_depth=5,
                    learning_rate=0.1,
                    random_state=42
                )

                # Cross-validation
                cv_scores = cross_val_score(model, X_scaled, y, cv=5, scoring='roc_auc')

                # Train final model
                model.fit(X_scaled, y)

                models_dict[ratio] = model
                tf_metrics[ratio] = {
                    'cv_auc_mean': np.mean(cv_scores),
                    'cv_auc_std': np.std(cv_scores),
                    'positive_rate': positive_rate
                }

                print(f"  Ratio {ratio:>4.1f}: AUC={np.mean(cv_scores):.3f} (+/- {np.std(cv_scores):.3f}) | Pos={positive_rate*100:.1f}%")

            # Save models
            if tf_name == '1h':
                self.models_1h = models_dict
            elif tf_name == '2h':
                self.models_2h = models_dict
            elif tf_name == '4h':
                self.models_4h = models_dict
            elif tf_name == '8h':
                self.models_8h = models_dict

            metrics[tf_name] = tf_metrics

        print(f"\n[OK] Training complete")

        return metrics

    def predict(self, features: np.ndarray) -> TPRatioPrediction:
        """
        Predict TP ratios for a new trade

        Args:
            features: Feature array from extract_features()

        Returns:
            TPRatioPrediction with recommended TP2 and TP3
        """
        # Scale features
        features_scaled = self.scaler.transform(features)

        # Get predictions for all timeframes
        probs_1h = []
        probs_2h = []
        probs_4h = []
        probs_8h = []

        for ratio in self.ratios:
            # 1h
            if ratio in self.models_1h:
                prob = self.models_1h[ratio].predict_proba(features_scaled)[0, 1]
                probs_1h.append(prob)
            else:
                probs_1h.append(0.0)

            # 2h
            if ratio in self.models_2h:
                prob = self.models_2h[ratio].predict_proba(features_scaled)[0, 1]
                probs_2h.append(prob)
            else:
                probs_2h.append(0.0)

            # 4h
            if ratio in self.models_4h:
                prob = self.models_4h[ratio].predict_proba(features_scaled)[0, 1]
                probs_4h.append(prob)
            else:
                probs_4h.append(0.0)

            # 8h
            if ratio in self.models_8h:
                prob = self.models_8h[ratio].predict_proba(features_scaled)[0, 1]
                probs_8h.append(prob)
            else:
                probs_8h.append(0.0)

        # Find TP2 (highest ratio with P > 60%)
        tp2_ratio, tp2_prob, tp2_tf = self._find_best_tp(
            self.ratios, probs_1h, probs_2h, probs_4h, probs_8h, threshold=0.60
        )

        # Find TP3 (highest ratio with P > 45%)
        tp3_ratio, tp3_prob, tp3_tf = self._find_best_tp(
            self.ratios, probs_1h, probs_2h, probs_4h, probs_8h, threshold=0.45
        )

        # Calculate confidence score
        confidence = np.mean([
            np.max(probs_1h), np.max(probs_2h),
            np.max(probs_4h), np.max(probs_8h)
        ])

        # Feature importance (from 1h models as reference)
        feature_importance = {}
        if len(self.models_1h) > 0:
            first_model = list(self.models_1h.values())[0]
            for name, importance in zip(self.feature_names, first_model.feature_importances_):
                feature_importance[name] = float(importance)

        return TPRatioPrediction(
            ratios=self.ratios,
            probabilities_1h=probs_1h,
            probabilities_2h=probs_2h,
            probabilities_4h=probs_4h,
            probabilities_8h=probs_8h,
            tp2_ratio=tp2_ratio,
            tp2_probability=tp2_prob,
            tp2_timeframe=tp2_tf,
            tp3_ratio=tp3_ratio,
            tp3_probability=tp3_prob,
            tp3_timeframe=tp3_tf,
            confidence_score=confidence,
            feature_importance=feature_importance
        )

    def _find_best_tp(self, ratios, probs_1h, probs_2h, probs_4h, probs_8h,
                     threshold: float) -> Tuple[float, float, str]:
        """
        Find highest ratio meeting probability threshold across all timeframes

        Returns:
            (ratio, probability, timeframe)
        """
        best_ratio = 0.0
        best_prob = 0.0
        best_tf = '1h'

        for i, ratio in enumerate(ratios):
            # Check each timeframe
            if probs_1h[i] >= threshold and ratio > best_ratio:
                best_ratio = ratio
                best_prob = probs_1h[i]
                best_tf = '1h'

            if probs_2h[i] >= threshold and ratio > best_ratio:
                best_ratio = ratio
                best_prob = probs_2h[i]
                best_tf = '2h'

            if probs_4h[i] >= threshold and ratio > best_ratio:
                best_ratio = ratio
                best_prob = probs_4h[i]
                best_tf = '4h'

            if probs_8h[i] >= threshold and ratio > best_ratio:
                best_ratio = ratio
                best_prob = probs_8h[i]
                best_tf = '8h'

        return best_ratio, best_prob, best_tf

    def save(self, filepath: str):
        """Save model to disk"""
        model_data = {
            'models_1h': self.models_1h,
            'models_2h': self.models_2h,
            'models_4h': self.models_4h,
            'models_8h': self.models_8h,
            'scaler': self.scaler,
            'feature_names': self.feature_names,
            'ratios': self.ratios
        }

        with open(filepath, 'wb') as f:
            pickle.dump(model_data, f)

        print(f"[OK] Model saved to {filepath}")

    def load(self, filepath: str):
        """Load model from disk"""
        with open(filepath, 'rb') as f:
            model_data = pickle.load(f)

        self.models_1h = model_data['models_1h']
        self.models_2h = model_data['models_2h']
        self.models_4h = model_data['models_4h']
        self.models_8h = model_data['models_8h']
        self.scaler = model_data['scaler']
        self.feature_names = model_data['feature_names']
        self.ratios = model_data['ratios']

        print(f"[OK] Model loaded from {filepath}")


# Test function
if __name__ == "__main__":
    print("Testing TP Ratio Predictor...")

    # This will be tested with real backtest data
    print("\n[OK] Ready for integration with backtest system")
