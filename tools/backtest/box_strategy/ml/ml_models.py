"""
ML Models for Box Strategy Prediction

Implements 5 machine learning models with GPU acceleration:
1. Random Forest Classifier
2. XGBoost Classifier (GPU-optimized)
3. LightGBM Classifier (GPU-optimized)
4. PyTorch Neural Network (GPU-accelerated)
5. Ensemble Voting Classifier

All models predict binary outcome: win (1) vs loss (0)
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import joblib
import json
import warnings

warnings.filterwarnings('ignore')

# Scikit-learn
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.model_selection import cross_val_score, StratifiedKFold
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, classification_report
)

# XGBoost
try:
    from xgboost import XGBClassifier
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    print("WARNING: XGBoost not installed. Install with: pip install xgboost")

# LightGBM
try:
    from lightgbm import LGBMClassifier
    LIGHTGBM_AVAILABLE = True
except ImportError:
    LIGHTGBM_AVAILABLE = False
    print("WARNING: LightGBM not installed. Install with: pip install lightgbm")

# PyTorch
try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import Dataset, DataLoader, TensorDataset
    PYTORCH_AVAILABLE = True
except ImportError:
    PYTORCH_AVAILABLE = False
    print("WARNING: PyTorch not installed. Install with: pip install torch")

# SMOTE for class balancing
try:
    from imblearn.over_sampling import SMOTE
    SMOTE_AVAILABLE = True
except ImportError:
    SMOTE_AVAILABLE = False
    print("WARNING: imbalanced-learn not installed. Install with: pip install imbalanced-learn")

from .ml_config import ML_CONFIG, DEVICE, GPU_AVAILABLE, MODELS_DIR


# ============================================================
# PYTORCH NEURAL NETWORK
# ============================================================
if PYTORCH_AVAILABLE:
    class TradingNeuralNet(nn.Module):
        """Neural Network for trade classification"""

        def __init__(self, input_dim: int, hidden_layers: List[int] = [128, 64, 32], dropout_rate: float = 0.3):
            super(TradingNeuralNet, self).__init__()

            self.input_dim = input_dim
            self.hidden_layers = hidden_layers
            self.dropout_rate = dropout_rate

            # Build layers
            layers = []
            prev_dim = input_dim

            for hidden_dim in hidden_layers:
                layers.append(nn.Linear(prev_dim, hidden_dim))
                layers.append(nn.ReLU())
                layers.append(nn.Dropout(dropout_rate))
                layers.append(nn.BatchNorm1d(hidden_dim))
                prev_dim = hidden_dim

            # Output layer
            layers.append(nn.Linear(prev_dim, 1))
            layers.append(nn.Sigmoid())

            self.model = nn.Sequential(*layers)

        def forward(self, x):
            return self.model(x)

    class PyTorchClassifier:
        """Wrapper for PyTorch model to match sklearn interface"""

        def __init__(self, input_dim: int, config: Optional[Dict] = None):
            self.config = config or ML_CONFIG['models']['neural_network']
            self.input_dim = input_dim

            # Model architecture
            hidden_layers = self.config.get('hidden_layers', [128, 64, 32])
            dropout_rate = self.config.get('dropout_rate', 0.3)

            # Training parameters
            self.batch_size = self.config.get('batch_size', 32)
            self.epochs = self.config.get('epochs', 100)
            self.learning_rate = self.config.get('learning_rate', 0.001)
            self.weight_decay = self.config.get('weight_decay', 0.0001)
            self.early_stopping_patience = self.config.get('early_stopping_patience', 15)

            # Device
            self.device = torch.device(self.config.get('device', 'cuda' if GPU_AVAILABLE else 'cpu'))

            # Initialize model
            self.model = TradingNeuralNet(input_dim, hidden_layers, dropout_rate).to(self.device)

            # Loss and optimizer
            self.criterion = nn.BCELoss()
            self.optimizer = optim.Adam(
                self.model.parameters(),
                lr=self.learning_rate,
                weight_decay=self.weight_decay
            )

            # Training history
            self.history = {'train_loss': [], 'val_loss': [], 'train_acc': [], 'val_acc': []}

        def fit(self, X_train: np.ndarray, y_train: np.ndarray,
                X_val: Optional[np.ndarray] = None, y_val: Optional[np.ndarray] = None,
                verbose: int = 1):
            """Train the model"""

            # Convert to tensors
            X_train_tensor = torch.FloatTensor(X_train).to(self.device)
            y_train_tensor = torch.FloatTensor(y_train).unsqueeze(1).to(self.device)

            # Create dataset and dataloader
            train_dataset = TensorDataset(X_train_tensor, y_train_tensor)
            train_loader = DataLoader(train_dataset, batch_size=self.batch_size, shuffle=True)

            # Validation data
            has_validation = X_val is not None and y_val is not None
            if has_validation:
                X_val_tensor = torch.FloatTensor(X_val).to(self.device)
                y_val_tensor = torch.FloatTensor(y_val).unsqueeze(1).to(self.device)

            # Early stopping
            best_val_loss = float('inf')
            patience_counter = 0

            # Training loop
            for epoch in range(self.epochs):
                # Training phase
                self.model.train()
                train_loss = 0.0
                train_correct = 0
                train_total = 0

                for batch_X, batch_y in train_loader:
                    # Forward pass
                    self.optimizer.zero_grad()
                    outputs = self.model(batch_X)
                    loss = self.criterion(outputs, batch_y)

                    # Backward pass
                    loss.backward()
                    self.optimizer.step()

                    # Statistics
                    train_loss += loss.item()
                    predicted = (outputs > 0.5).float()
                    train_correct += (predicted == batch_y).sum().item()
                    train_total += batch_y.size(0)

                avg_train_loss = train_loss / len(train_loader)
                train_accuracy = train_correct / train_total

                self.history['train_loss'].append(avg_train_loss)
                self.history['train_acc'].append(train_accuracy)

                # Validation phase
                if has_validation:
                    self.model.eval()
                    with torch.no_grad():
                        val_outputs = self.model(X_val_tensor)
                        val_loss = self.criterion(val_outputs, y_val_tensor).item()
                        val_predicted = (val_outputs > 0.5).float()
                        val_accuracy = (val_predicted == y_val_tensor).float().mean().item()

                    self.history['val_loss'].append(val_loss)
                    self.history['val_acc'].append(val_accuracy)

                    # Early stopping
                    if val_loss < best_val_loss:
                        best_val_loss = val_loss
                        patience_counter = 0
                    else:
                        patience_counter += 1

                    if patience_counter >= self.early_stopping_patience:
                        if verbose:
                            print(f"Early stopping at epoch {epoch+1}")
                        break

                    if verbose and (epoch + 1) % 10 == 0:
                        print(f"Epoch [{epoch+1}/{self.epochs}] - "
                              f"Train Loss: {avg_train_loss:.4f}, Train Acc: {train_accuracy:.4f}, "
                              f"Val Loss: {val_loss:.4f}, Val Acc: {val_accuracy:.4f}")
                else:
                    if verbose and (epoch + 1) % 10 == 0:
                        print(f"Epoch [{epoch+1}/{self.epochs}] - "
                              f"Train Loss: {avg_train_loss:.4f}, Train Acc: {train_accuracy:.4f}")

            return self

        def predict(self, X: np.ndarray) -> np.ndarray:
            """Predict class labels"""
            self.model.eval()
            with torch.no_grad():
                X_tensor = torch.FloatTensor(X).to(self.device)
                outputs = self.model(X_tensor)
                predicted = (outputs > 0.5).float().cpu().numpy()
            return predicted.flatten().astype(int)

        def predict_proba(self, X: np.ndarray) -> np.ndarray:
            """Predict class probabilities"""
            self.model.eval()
            with torch.no_grad():
                X_tensor = torch.FloatTensor(X).to(self.device)
                outputs = self.model(X_tensor).cpu().numpy()

            # Return probabilities for both classes
            proba_class_0 = 1 - outputs
            proba_class_1 = outputs
            return np.concatenate([proba_class_0, proba_class_1], axis=1)

        def save(self, filepath: Path):
            """Save model to file"""
            torch.save({
                'model_state_dict': self.model.state_dict(),
                'optimizer_state_dict': self.optimizer.state_dict(),
                'config': self.config,
                'input_dim': self.input_dim,
                'history': self.history
            }, filepath)

        def load(self, filepath: Path):
            """Load model from file"""
            checkpoint = torch.load(filepath, map_location=self.device)
            self.model.load_state_dict(checkpoint['model_state_dict'])
            self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
            self.history = checkpoint.get('history', {})
            return self


# ============================================================
# ML MODEL TRAINER
# ============================================================
class MLModelTrainer:
    """Train and manage multiple ML models"""

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize model trainer

        Args:
            config: Optional configuration (uses ML_CONFIG if not provided)
        """
        self.config = config or ML_CONFIG

        # Model configurations
        self.rf_config = self.config['models']['random_forest']
        self.xgb_config = self.config['models']['xgboost'] if XGBOOST_AVAILABLE else None
        self.lgbm_config = self.config['models']['lightgbm'] if LIGHTGBM_AVAILABLE else None
        self.nn_config = self.config['models']['neural_network'] if PYTORCH_AVAILABLE else None
        self.ensemble_config = self.config['models']['ensemble']

        # Training configuration
        self.cv_folds = self.config['training']['cv_folds']
        self.balance_classes = self.config['training']['balance_classes']
        self.balancing_method = self.config['training']['balancing_method']
        self.scale_features = self.config['training']['scale_features']

        # Models
        self.models = {}
        self.scaler = StandardScaler() if self.scale_features else None
        self.feature_names = []

        print(f"MLModelTrainer initialized")
        print(f"  - XGBoost: {'[OK]' if XGBOOST_AVAILABLE else '[NO]'}")
        print(f"  - LightGBM: {'[OK]' if LIGHTGBM_AVAILABLE else '[NO]'}")
        print(f"  - PyTorch: {'[OK]' if PYTORCH_AVAILABLE else '[NO]'} (Device: {DEVICE})")
        print(f"  - SMOTE: {'[OK]' if SMOTE_AVAILABLE else '[NO]'}")

    def train_random_forest(self, X_train: np.ndarray, y_train: np.ndarray,
                           X_val: Optional[np.ndarray] = None, y_val: Optional[np.ndarray] = None) -> RandomForestClassifier:
        """Train Random Forest model"""
        print("\n" + "="*80)
        print("Training Random Forest Classifier")
        print("="*80)

        model = RandomForestClassifier(**self.rf_config)
        model.fit(X_train, y_train)

        # Cross-validation
        cv_scores = cross_val_score(model, X_train, y_train,
                                   cv=self.cv_folds, scoring='roc_auc', n_jobs=-1)
        print(f"Cross-validation AUC: {cv_scores.mean():.4f} (+/- {cv_scores.std():.4f})")

        # Validation performance
        if X_val is not None and y_val is not None:
            y_val_pred = model.predict(X_val)
            val_acc = accuracy_score(y_val, y_val_pred)
            print(f"Validation Accuracy: {val_acc:.4f}")

        self.models['random_forest'] = model
        return model

    def train_xgboost(self, X_train: np.ndarray, y_train: np.ndarray,
                     X_val: Optional[np.ndarray] = None, y_val: Optional[np.ndarray] = None) -> Optional[XGBClassifier]:
        """Train XGBoost model (GPU-optimized)"""
        if not XGBOOST_AVAILABLE:
            print("XGBoost not available. Skipping...")
            return None

        print("\n" + "="*80)
        print(f"Training XGBoost Classifier (tree_method: {self.xgb_config['tree_method']})")
        print("="*80)

        model = XGBClassifier(**self.xgb_config)

        # Early stopping with validation set
        if X_val is not None and y_val is not None:
            model.fit(
                X_train, y_train,
                eval_set=[(X_val, y_val)],
                verbose=False
            )
        else:
            model.fit(X_train, y_train)

        # Cross-validation
        cv_scores = cross_val_score(model, X_train, y_train,
                                   cv=self.cv_folds, scoring='roc_auc', n_jobs=-1)
        print(f"Cross-validation AUC: {cv_scores.mean():.4f} (+/- {cv_scores.std():.4f})")

        # Validation performance
        if X_val is not None and y_val is not None:
            y_val_pred = model.predict(X_val)
            val_acc = accuracy_score(y_val, y_val_pred)
            print(f"Validation Accuracy: {val_acc:.4f}")

        self.models['xgboost'] = model
        return model

    def train_lightgbm(self, X_train: np.ndarray, y_train: np.ndarray,
                      X_val: Optional[np.ndarray] = None, y_val: Optional[np.ndarray] = None) -> Optional[LGBMClassifier]:
        """Train LightGBM model (GPU-optimized)"""
        if not LIGHTGBM_AVAILABLE:
            print("LightGBM not available. Skipping...")
            return None

        print("\n" + "="*80)
        print(f"Training LightGBM Classifier (device: {self.lgbm_config['device']})")
        print("="*80)

        model = LGBMClassifier(**self.lgbm_config)

        # Early stopping with validation set
        if X_val is not None and y_val is not None:
            model.fit(
                X_train, y_train,
                eval_set=[(X_val, y_val)],
                callbacks=[
                    # Early stopping removed in newer versions, handled internally
                ]
            )
        else:
            model.fit(X_train, y_train)

        # Cross-validation
        cv_scores = cross_val_score(model, X_train, y_train,
                                   cv=self.cv_folds, scoring='roc_auc', n_jobs=-1)
        print(f"Cross-validation AUC: {cv_scores.mean():.4f} (+/- {cv_scores.std():.4f})")

        # Validation performance
        if X_val is not None and y_val is not None:
            y_val_pred = model.predict(X_val)
            val_acc = accuracy_score(y_val, y_val_pred)
            print(f"Validation Accuracy: {val_acc:.4f}")

        self.models['lightgbm'] = model
        return model

    def train_neural_network(self, X_train: np.ndarray, y_train: np.ndarray,
                            X_val: Optional[np.ndarray] = None, y_val: Optional[np.ndarray] = None) -> Optional[PyTorchClassifier]:
        """Train PyTorch Neural Network (GPU-accelerated)"""
        if not PYTORCH_AVAILABLE:
            print("PyTorch not available. Skipping...")
            return None

        print("\n" + "="*80)
        print(f"Training PyTorch Neural Network (device: {DEVICE})")
        print("="*80)

        input_dim = X_train.shape[1]
        model = PyTorchClassifier(input_dim, config=self.nn_config)
        model.fit(X_train, y_train, X_val, y_val, verbose=1)

        # Validation performance
        if X_val is not None and y_val is not None:
            y_val_pred = model.predict(X_val)
            val_acc = accuracy_score(y_val, y_val_pred)
            print(f"Final Validation Accuracy: {val_acc:.4f}")

        self.models['neural_network'] = model
        return model

    def train_ensemble(self, X_train: np.ndarray, y_train: np.ndarray,
                      X_val: Optional[np.ndarray] = None, y_val: Optional[np.ndarray] = None) -> Optional[VotingClassifier]:
        """Train ensemble model (combines all available models)"""
        print("\n" + "="*80)
        print("Training Ensemble Model")
        print("="*80)

        # Collect trained models
        estimators = []
        weights = []

        model_weights = self.ensemble_config.get('weights', [1.5, 2.0, 2.0, 1.5])

        if 'random_forest' in self.models:
            estimators.append(('rf', self.models['random_forest']))
            weights.append(model_weights[0])

        if 'xgboost' in self.models:
            estimators.append(('xgb', self.models['xgboost']))
            weights.append(model_weights[1])

        if 'lightgbm' in self.models:
            estimators.append(('lgbm', self.models['lightgbm']))
            weights.append(model_weights[2])

        # Note: PyTorch model cannot be directly used in VotingClassifier
        # We'll create a simplified ensemble without it

        if len(estimators) < 2:
            print("Not enough models for ensemble. Skipping...")
            return None

        # Create voting classifier
        ensemble = VotingClassifier(
            estimators=estimators,
            voting=self.ensemble_config['voting'],
            weights=weights,
            n_jobs=self.ensemble_config.get('n_jobs', -1)
        )

        ensemble.fit(X_train, y_train)

        # Cross-validation
        cv_scores = cross_val_score(ensemble, X_train, y_train,
                                   cv=self.cv_folds, scoring='roc_auc', n_jobs=-1)
        print(f"Cross-validation AUC: {cv_scores.mean():.4f} (+/- {cv_scores.std():.4f})")

        # Validation performance
        if X_val is not None and y_val is not None:
            y_val_pred = ensemble.predict(X_val)
            val_acc = accuracy_score(y_val, y_val_pred)
            print(f"Validation Accuracy: {val_acc:.4f}")

        self.models['ensemble'] = ensemble
        return ensemble

    def train_all_models(self, X_train: np.ndarray, y_train: np.ndarray,
                        X_val: Optional[np.ndarray] = None, y_val: Optional[np.ndarray] = None,
                        feature_names: Optional[List[str]] = None):
        """Train all available models"""
        print("\n" + "="*80)
        print("TRAINING ALL ML MODELS")
        print("="*80)
        print(f"Training samples: {len(X_train)}")
        print(f"Validation samples: {len(X_val) if X_val is not None else 0}")
        print(f"Features: {X_train.shape[1]}")
        print(f"Positive class ratio: {y_train.mean():.2%}")

        # Store feature names
        if feature_names:
            self.feature_names = feature_names

        # Apply class balancing if needed
        X_train_balanced = X_train
        y_train_balanced = y_train

        if self.balance_classes and self.balancing_method == 'smote' and SMOTE_AVAILABLE:
            print("\nApplying SMOTE for class balancing...")
            smote = SMOTE(random_state=42)
            X_train_balanced, y_train_balanced = smote.fit_resample(X_train, y_train)
            print(f"After SMOTE - samples: {len(X_train_balanced)}, positive ratio: {y_train_balanced.mean():.2%}")

        # Feature scaling
        if self.scale_features:
            print("\nScaling features...")
            X_train_balanced = self.scaler.fit_transform(X_train_balanced)
            if X_val is not None:
                X_val = self.scaler.transform(X_val)

        # Train individual models
        self.train_random_forest(X_train_balanced, y_train_balanced, X_val, y_val)

        if XGBOOST_AVAILABLE:
            self.train_xgboost(X_train_balanced, y_train_balanced, X_val, y_val)

        if LIGHTGBM_AVAILABLE:
            self.train_lightgbm(X_train_balanced, y_train_balanced, X_val, y_val)

        if PYTORCH_AVAILABLE:
            self.train_neural_network(X_train_balanced, y_train_balanced, X_val, y_val)

        # Train ensemble
        self.train_ensemble(X_train_balanced, y_train_balanced, X_val, y_val)

        print("\n" + "="*80)
        print(f"Training complete! Trained {len(self.models)} models")
        print("="*80)

    def save_models(self, version: str = "1"):
        """Save all trained models"""
        print(f"\nSaving models (version {version})...")

        for model_name, model in self.models.items():
            if model is None:
                continue

            if model_name == 'neural_network' and PYTORCH_AVAILABLE:
                # PyTorch model
                filepath = MODELS_DIR / f"neural_network_v{version}.pth"
                model.save(filepath)
                print(f"  [OK] Saved {model_name} to {filepath}")
            else:
                # Scikit-learn models
                filepath = MODELS_DIR / f"{model_name}_v{version}.pkl"
                joblib.dump(model, filepath, compress=3)
                print(f"  [OK] Saved {model_name} to {filepath}")

        # Save scaler
        if self.scaler:
            scaler_path = MODELS_DIR / f"feature_scaler_v{version}.pkl"
            joblib.dump(self.scaler, scaler_path, compress=3)
            print(f"  [OK] Saved scaler to {scaler_path}")

        # Save feature names
        if self.feature_names:
            feature_path = MODELS_DIR / f"feature_names_v{version}.json"
            with open(feature_path, 'w') as f:
                json.dump(self.feature_names, f, indent=2)
            print(f"  [OK] Saved feature names to {feature_path}")

        print("All models saved successfully!")


# ============================================================
# ML MODEL MANAGER (for loading and using trained models)
# ============================================================
class MLModelManager:
    """Load and use trained ML models"""

    def __init__(self, version: str = "1"):
        """
        Initialize model manager

        Args:
            version: Model version to load
        """
        self.version = version
        self.models = {}
        self.scaler = None
        self.feature_names = []

    def load_models(self, model_names: Optional[List[str]] = None):
        """Load trained models"""
        if model_names is None:
            model_names = ['random_forest', 'xgboost', 'lightgbm', 'neural_network', 'ensemble']

        print(f"Loading models (version {self.version})...")

        for model_name in model_names:
            try:
                if model_name == 'neural_network' and PYTORCH_AVAILABLE:
                    # Load PyTorch model (need to know input_dim - load from metadata)
                    filepath = MODELS_DIR / f"neural_network_v{self.version}.pth"
                    if filepath.exists():
                        checkpoint = torch.load(filepath, map_location=DEVICE)
                        input_dim = checkpoint['input_dim']
                        model = PyTorchClassifier(input_dim)
                        model.load(filepath)
                        self.models[model_name] = model
                        print(f"  [OK] Loaded {model_name}")
                else:
                    filepath = MODELS_DIR / f"{model_name}_v{self.version}.pkl"
                    if filepath.exists():
                        model = joblib.load(filepath)
                        self.models[model_name] = model
                        print(f"  [OK] Loaded {model_name}")
            except Exception as e:
                print(f"  [FAIL] Failed to load {model_name}: {e}")

        # Load scaler
        scaler_path = MODELS_DIR / f"feature_scaler_v{self.version}.pkl"
        if scaler_path.exists():
            self.scaler = joblib.load(scaler_path)
            print(f"  [OK] Loaded scaler")

        # Load feature names
        feature_path = MODELS_DIR / f"feature_names_v{self.version}.json"
        if feature_path.exists():
            with open(feature_path, 'r') as f:
                self.feature_names = json.load(f)
            print(f"  [OK] Loaded feature names")

        print(f"Loaded {len(self.models)} models")

    def predict(self, X: np.ndarray, model_name: str = 'ensemble') -> np.ndarray:
        """Make predictions"""
        if model_name not in self.models:
            raise ValueError(f"Model {model_name} not loaded")

        # Scale features if scaler available
        if self.scaler:
            X = self.scaler.transform(X)

        return self.models[model_name].predict(X)

    def predict_proba(self, X: np.ndarray, model_name: str = 'ensemble') -> np.ndarray:
        """Predict probabilities"""
        if model_name not in self.models:
            raise ValueError(f"Model {model_name} not loaded")

        # Scale features if scaler available
        if self.scaler:
            X = self.scaler.transform(X)

        return self.models[model_name].predict_proba(X)
