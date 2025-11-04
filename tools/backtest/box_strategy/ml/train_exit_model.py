"""
Train Exit Signal Model

Entrena un modelo ML para predecir el punto óptimo de salida basado en
señales de agotamiento (RSI divergencias en 15min).

Training Data:
- Usa trades históricos del backtest
- Para cada trade, simula monitoreo cada 15 minutos
- Extrae features en momentos clave (TP1, máximo antes de reversión, etc.)
- Label: ¿Llegó a TP2? (1) o se revirtió en TP1? (0)

Output Model:
- Classification: [EXIT_AT_TP1, HOLD_FOR_TP2, HOLD_FOR_TP3]
- Features: 15+ features incluyendo RSI divergence, momentum, volatility
- Confidence scores para cada acción
"""

import sys
import json
import argparse
from pathlib import Path
from typing import List, Dict, Tuple
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

# ML imports
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, confusion_matrix
import joblib

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data_loader import DataLoader
from ml.exit_signal_predictor import ExitFeatureEngineer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ExitModelTrainer:
    """
    Trainer for exit signal prediction model

    Simula el trade en tiempo real y captura features en momentos clave
    """

    def __init__(self, backtest_results_file: str):
        """
        Initialize trainer

        Args:
            backtest_results_file: Path to backtest results JSON
        """
        self.backtest_file = Path(backtest_results_file)
        self.data_loader = DataLoader()
        self.feature_engineer = ExitFeatureEngineer()

        # Load backtest results
        with open(self.backtest_file, 'r') as f:
            self.backtest_data = json.load(f)

        logger.info(f"Loaded backtest data from {self.backtest_file}")

    def simulate_trade_monitoring(
        self,
        trade: Dict,
        market: str,
        df_5min: pd.DataFrame
    ) -> List[Dict]:
        """
        Simula el monitoreo del trade cada 15 minutos y captura features

        Args:
            trade: Trade data from backtest
            market: Market code
            df_5min: 5-minute data

        Returns:
            List of feature snapshots at 15-min intervals
        """
        snapshots = []

        try:
            # Parse times
            entry_time = pd.to_datetime(trade['entry_time'])
            exit_time = pd.to_datetime(trade['exit_time'])

            direction = trade['direction']
            entry_price = trade['entry_price']
            exit_price = trade['exit_price']

            # Calculate TPs (usando risk del trade)
            box_range = trade.get('box_range', abs(trade['box_high'] - trade['box_low']))

            if direction == "LONG":
                stop_loss = trade.get('stop_loss', entry_price - box_range)
                risk = entry_price - stop_loss
                tp1 = entry_price + (1.0 * risk)
                tp2 = entry_price + (2.0 * risk)
                tp3 = entry_price + (3.0 * risk)
            else:
                stop_loss = trade.get('stop_loss', entry_price + box_range)
                risk = stop_loss - entry_price
                tp1 = entry_price - (1.0 * risk)
                tp2 = entry_price - (2.0 * risk)
                tp3 = entry_price - (3.0 * risk)

            # Convertir 5min data a 15min
            df_15min = self._convert_to_15min(df_5min)

            # Filtrar datos solo hasta el exit
            df_15min_trade = df_15min[
                (df_15min.index >= entry_time) &
                (df_15min.index <= exit_time)
            ].copy()

            if df_15min_trade.empty:
                logger.warning(f"No 15min data for trade {trade.get('date')}")
                return snapshots

            # Determinar label real (qué TP alcanzó)
            actual_exit_level = self._determine_exit_level(
                trade, entry_price, exit_price, tp1, tp2, tp3, direction
            )

            # Tomar snapshots cada 15 minutos durante el trade
            for i in range(len(df_15min_trade)):
                current_time = df_15min_trade.index[i]
                current_price = df_15min_trade.iloc[i]['Close']

                # Tomar datos históricos hasta este punto
                df_15min_history = df_15min[df_15min.index <= current_time].copy()

                if len(df_15min_history) < 20:
                    continue  # Necesitamos historia suficiente

                # Extraer features
                features = self.feature_engineer.extract_exit_features(
                    df_15min_history,
                    entry_price,
                    current_price,
                    direction,
                    tp1,
                    tp2,
                    tp3
                )

                # Determinar label para este momento
                # Label: ¿Debería haber cerrado aquí?
                should_exit = self._should_have_exited(
                    current_price,
                    current_time,
                    actual_exit_level,
                    features,
                    direction,
                    tp1,
                    tp2,
                    tp3
                )

                # Agregar snapshot
                snapshot = {
                    **features,
                    'label': should_exit,
                    'actual_exit_level': actual_exit_level,
                    'timestamp': str(current_time),
                    'market': market,
                    'trade_id': f"{market}_{trade['date']}"
                }

                snapshots.append(snapshot)

        except Exception as e:
            logger.error(f"Error simulating trade monitoring: {e}")

        return snapshots

    def _convert_to_15min(self, df_5min: pd.DataFrame) -> pd.DataFrame:
        """Convierte datos de 5min a 15min"""
        df_15min = df_5min.resample('15min').agg({
            'Open': 'first',
            'High': 'max',
            'Low': 'min',
            'Close': 'last',
            'Volume': 'sum'
        }).dropna()

        return df_15min

    def _determine_exit_level(
        self,
        trade: Dict,
        entry: float,
        exit: float,
        tp1: float,
        tp2: float,
        tp3: float,
        direction: str
    ) -> str:
        """
        Determina qué nivel de TP alcanzó el trade

        Returns:
            "TP1", "TP2", "TP3", "STOPPED_OUT"
        """
        outcome = trade.get('outcome', 'UNKNOWN')

        if outcome in ['STOPPED_OUT', 'LOSS']:
            return "STOPPED_OUT"

        # Calcular cuántos R alcanzó
        pnl = trade.get('pnl', 0)
        risk = abs(entry - trade.get('stop_loss', entry))

        if risk > 0:
            r_achieved = abs(pnl) / risk
        else:
            r_achieved = 0

        # Clasificar por R alcanzado
        if r_achieved >= 2.5:
            return "TP3"
        elif r_achieved >= 1.5:
            return "TP2"
        elif r_achieved >= 0.5:
            return "TP1"
        else:
            return "STOPPED_OUT"

    def _should_have_exited(
        self,
        current_price: float,
        current_time: pd.Timestamp,
        actual_exit_level: str,
        features: Dict,
        direction: str,
        tp1: float,
        tp2: float,
        tp3: float
    ) -> str:
        """
        Determina si debería haber salido en este momento

        Returns:
            "EXIT_NOW", "HOLD_FOR_TP2", "HOLD_FOR_TP3"
        """
        # Si ya pasó TP1
        current_r = features['current_r']

        if current_r < 0.8:
            # Aún no llegó a TP1
            return "HOLD_FOR_TP1"

        elif 0.8 <= current_r < 1.5:
            # Entre TP1 y TP2
            # Si el trade finalmente llegó a TP2+, debería haber esperado
            if actual_exit_level in ["TP2", "TP3"]:
                return "HOLD_FOR_TP2"
            else:
                # Se revirtió en TP1
                return "EXIT_AT_TP1"

        elif 1.5 <= current_r < 2.5:
            # Entre TP2 y TP3
            if actual_exit_level == "TP3":
                return "HOLD_FOR_TP3"
            else:
                return "EXIT_AT_TP2"

        else:
            # Más allá de TP3
            return "EXIT_AT_TP3"

    def extract_training_data(self) -> Tuple[pd.DataFrame, np.ndarray]:
        """
        Extrae datos de entrenamiento de todos los trades del backtest

        Returns:
            (X_features, y_labels)
        """
        all_snapshots = []

        for market, market_data in self.backtest_data.items():
            if isinstance(market_data, dict) and 'trades' in market_data:
                trades = market_data['trades']

                logger.info(f"Processing {market}: {len(trades)} trades")

                for trade in trades:
                    # Download data for this trade
                    trade_date = pd.to_datetime(trade['date'])
                    start_date = trade_date - timedelta(days=7)
                    end_date = trade_date + timedelta(days=1)

                    try:
                        df_5min = self.data_loader.download_5min_data(
                            market,
                            start_date=start_date,
                            end_date=end_date,
                            force_refresh=False
                        )

                        if df_5min is None or df_5min.empty:
                            continue

                        # Simulate monitoring
                        snapshots = self.simulate_trade_monitoring(trade, market, df_5min)
                        all_snapshots.extend(snapshots)

                    except Exception as e:
                        logger.error(f"Error processing trade {trade.get('date')} for {market}: {e}")
                        continue

        logger.info(f"Extracted {len(all_snapshots)} training snapshots")

        # Convert to DataFrame
        df = pd.DataFrame(all_snapshots)

        if df.empty:
            raise ValueError("No training data extracted!")

        # Select feature columns
        feature_cols = [
            'current_r',
            'distance_to_next_tp_r',
            'rsi_divergence_15min',
            'rsi_current',
            'momentum_weakening',
            'momentum_score',
            'volatility_expansion'
        ]

        X = df[feature_cols].values
        y = df['label'].values

        return X, y, df

    def train_model(self, X: np.ndarray, y: np.ndarray) -> RandomForestClassifier:
        """
        Train exit signal model

        Args:
            X: Feature matrix
            y: Labels

        Returns:
            Trained model
        """
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )

        logger.info(f"Training set: {len(X_train)} samples")
        logger.info(f"Test set: {len(X_test)} samples")

        # Scale features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)

        # Train Random Forest
        logger.info("Training Random Forest Classifier...")

        model = RandomForestClassifier(
            n_estimators=200,
            max_depth=10,
            min_samples_split=10,
            min_samples_leaf=5,
            random_state=42,
            class_weight='balanced',
            n_jobs=-1
        )

        model.fit(X_train_scaled, y_train)

        # Cross-validation
        cv_scores = cross_val_score(model, X_train_scaled, y_train, cv=5, scoring='accuracy')
        logger.info(f"Cross-validation accuracy: {cv_scores.mean():.3f} (+/- {cv_scores.std():.3f})")

        # Test set evaluation
        y_pred = model.predict(X_test_scaled)
        test_accuracy = (y_pred == y_test).mean()

        logger.info(f"Test set accuracy: {test_accuracy:.3f}")
        logger.info("\nClassification Report:")
        print(classification_report(y_test, y_pred))

        logger.info("\nConfusion Matrix:")
        print(confusion_matrix(y_test, y_pred))

        # Feature importance
        feature_names = [
            'current_r',
            'distance_to_next_tp_r',
            'rsi_divergence_15min',
            'rsi_current',
            'momentum_weakening',
            'momentum_score',
            'volatility_expansion'
        ]

        logger.info("\nFeature Importance:")
        for name, importance in zip(feature_names, model.feature_importances_):
            logger.info(f"  {name:30s}: {importance:.4f}")

        return model, scaler

    def save_model(self, model, scaler, version: str = "1"):
        """Save trained model and scaler"""
        models_dir = Path(__file__).parent.parent / "models"
        models_dir.mkdir(exist_ok=True)

        model_path = models_dir / f"exit_model_v{version}.pkl"
        scaler_path = models_dir / f"exit_scaler_v{version}.pkl"

        joblib.dump(model, model_path)
        joblib.dump(scaler, scaler_path)

        logger.info(f"Model saved to {model_path}")
        logger.info(f"Scaler saved to {scaler_path}")


def main():
    parser = argparse.ArgumentParser(description='Train exit signal prediction model')
    parser.add_argument('--data', required=True, help='Path to backtest results JSON')
    parser.add_argument('--version', default='1', help='Model version')

    args = parser.parse_args()

    # Initialize trainer
    trainer = ExitModelTrainer(args.data)

    # Extract training data
    logger.info("Extracting training data...")
    X, y, df = trainer.extract_training_data()

    # Train model
    logger.info("Training model...")
    model, scaler = trainer.train_model(X, y)

    # Save model
    trainer.save_model(model, scaler, args.version)

    logger.info("\nTraining complete!")
    logger.info(f"Model version: {args.version}")


if __name__ == "__main__":
    main()
