"""
ML Model Training Pipeline for Box Strategy

Complete automated pipeline:
1. Load backtest results
2. Extract features
3. Split train/validation/test sets
4. Balance classes (SMOTE)
5. Train all models (RF, XGBoost, LightGBM, PyTorch, Ensemble)
6. Evaluate performance
7. Save trained models

Usage:
    python train_models.py --data multi_market_results_20251005_173628.json --version 1
    python train_models.py --data-dir results/ --models xgboost lightgbm --version 2
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from ml.feature_engineering import FeatureEngineer
from ml.ml_models import MLModelTrainer
from ml.ml_config import ML_CONFIG, DATA_DIR, MODELS_DIR, ML_RESULTS_DIR, print_gpu_info
from market_config import MARKETS


def load_backtest_results(filepath: Path) -> Dict:
    """
    Load backtest results from JSON file

    Args:
        filepath: Path to backtest results JSON

    Returns:
        Dictionary with all market results
    """
    print(f"\nLoading backtest results from: {filepath}")

    with open(filepath, 'r') as f:
        results = json.load(f)

    # Count total trades
    total_trades = 0
    successful_markets = 0

    for market_code, market_result in results.items():
        if market_result.get('success', False):
            trades = market_result.get('trades', [])
            total_trades += len(trades)
            successful_markets += 1

    print(f"Loaded {successful_markets} markets with {total_trades} total trades")

    return results


def extract_all_features(backtest_results: Dict, engineer: FeatureEngineer) -> pd.DataFrame:
    """
    Extract features from all trades in backtest results

    Args:
        backtest_results: Dictionary with market results
        engineer: FeatureEngineer instance

    Returns:
        DataFrame with all features
    """
    print("\n" + "="*80)
    print("FEATURE EXTRACTION")
    print("="*80)

    # Get market configs
    market_configs = {}
    for market_code in backtest_results.keys():
        if market_code in MARKETS:
            config = MARKETS[market_code]
            market_configs[market_code] = {
                'liquidity_rating': config.liquidity_rating,
                'point_value': config.point_value,
                'typical_box_range': config.typical_box_range
            }

    # Extract features
    df_features = engineer.extract_features_from_backtest_results(
        backtest_results,
        market_configs
    )

    if df_features.empty:
        raise ValueError("No features extracted! Check backtest results.")

    # Remove any NaN values
    print(f"\nChecking for missing values...")
    missing_before = df_features.isnull().sum().sum()
    if missing_before > 0:
        print(f"Found {missing_before} missing values - filling with median")
        df_features = df_features.fillna(df_features.median())

    # Summary statistics
    print(f"\nFeature Summary:")
    print(f"  Total samples: {len(df_features)}")
    print(f"  Total features: {len(df_features.columns)}")
    print(f"  Target distribution:")
    print(f"    Wins (1): {(df_features['target'] == 1).sum()} ({(df_features['target'] == 1).mean():.1%})")
    print(f"    Losses (0): {(df_features['target'] == 0).sum()} ({(df_features['target'] == 0).mean():.1%})")

    # Feature value ranges
    print(f"\nFeature Ranges:")
    numeric_features = df_features.select_dtypes(include=[np.number]).columns
    for feature in numeric_features[:10]:  # Show first 10
        print(f"  {feature:30s}: [{df_features[feature].min():.2f}, {df_features[feature].max():.2f}]")
    if len(numeric_features) > 10:
        print(f"  ... and {len(numeric_features) - 10} more features")

    return df_features


def prepare_datasets(df_features: pd.DataFrame, test_size: float = 0.2, val_size: float = 0.2, random_state: int = 42):
    """
    Prepare train/validation/test datasets

    Args:
        df_features: DataFrame with features
        test_size: Fraction for test set
        val_size: Fraction of remaining data for validation
        random_state: Random seed

    Returns:
        Tuple of (X_train, X_val, X_test, y_train, y_val, y_test, feature_names)
    """
    print("\n" + "="*80)
    print("DATA PREPARATION")
    print("="*80)

    # Separate features and target
    # Exclude target and categorical features
    exclude_cols = ['target', 'market_code']
    feature_cols = [col for col in df_features.columns if col not in exclude_cols]

    X = df_features[feature_cols].values
    y = df_features['target'].values
    feature_names = feature_cols

    print(f"Features shape: {X.shape}")
    print(f"Target shape: {y.shape}")

    # First split: train+val vs test
    X_trainval, X_test, y_trainval, y_test = train_test_split(
        X, y,
        test_size=test_size,
        random_state=random_state,
        stratify=y
    )

    # Second split: train vs val
    val_size_adjusted = val_size / (1 - test_size)  # Adjust for remaining data
    X_train, X_val, y_train, y_val = train_test_split(
        X_trainval, y_trainval,
        test_size=val_size_adjusted,
        random_state=random_state,
        stratify=y_trainval
    )

    # Print splits
    print(f"\nDataset Splits:")
    print(f"  Train:      {len(X_train):4d} samples ({len(y_train[y_train==1])} wins, {len(y_train[y_train==0])} losses)")
    print(f"  Validation: {len(X_val):4d} samples ({len(y_val[y_val==1])} wins, {len(y_val[y_val==0])} losses)")
    print(f"  Test:       {len(X_test):4d} samples ({len(y_test[y_test==1])} wins, {len(y_test[y_test==0])} losses)")

    return X_train, X_val, X_test, y_train, y_val, y_test, feature_names


def train_models(X_train: np.ndarray, y_train: np.ndarray,
                X_val: np.ndarray, y_val: np.ndarray,
                feature_names: List[str],
                model_names: Optional[List[str]] = None,
                version: str = "1") -> MLModelTrainer:
    """
    Train ML models

    Args:
        X_train: Training features
        y_train: Training labels
        X_val: Validation features
        y_val: Validation labels
        feature_names: List of feature names
        model_names: List of models to train (None = all)
        version: Model version

    Returns:
        Trained MLModelTrainer instance
    """
    print("\n" + "="*80)
    print("MODEL TRAINING")
    print("="*80)

    # Initialize trainer
    trainer = MLModelTrainer(config=ML_CONFIG)

    # Train all models
    if model_names is None or 'all' in model_names:
        trainer.train_all_models(X_train, y_train, X_val, y_val, feature_names)
    else:
        # Train specific models
        trainer.feature_names = feature_names

        # Apply preprocessing
        X_train_processed = X_train
        y_train_processed = y_train
        X_val_processed = X_val

        if trainer.scale_features:
            print("\nScaling features...")
            X_train_processed = trainer.scaler.fit_transform(X_train)
            X_val_processed = trainer.scaler.transform(X_val)

        if trainer.balance_classes:
            try:
                from imblearn.over_sampling import SMOTE
                print("\nApplying SMOTE...")
                smote = SMOTE(random_state=42)
                X_train_processed, y_train_processed = smote.fit_resample(X_train_processed, y_train)
                print(f"After SMOTE: {len(X_train_processed)} samples")
            except ImportError:
                print("SMOTE not available, skipping class balancing")

        # Train selected models
        for model_name in model_names:
            if model_name == 'random_forest' or model_name == 'rf':
                trainer.train_random_forest(X_train_processed, y_train_processed, X_val_processed, y_val)
            elif model_name == 'xgboost' or model_name == 'xgb':
                trainer.train_xgboost(X_train_processed, y_train_processed, X_val_processed, y_val)
            elif model_name == 'lightgbm' or model_name == 'lgbm':
                trainer.train_lightgbm(X_train_processed, y_train_processed, X_val_processed, y_val)
            elif model_name == 'neural_network' or model_name == 'nn':
                trainer.train_neural_network(X_train_processed, y_train_processed, X_val_processed, y_val)
            elif model_name == 'ensemble':
                trainer.train_ensemble(X_train_processed, y_train_processed, X_val_processed, y_val)

    # Save models
    trainer.save_models(version=version)

    return trainer


def evaluate_models(trainer: MLModelTrainer, X_test: np.ndarray, y_test: np.ndarray):
    """
    Evaluate all trained models on test set

    Args:
        trainer: Trained MLModelTrainer
        X_test: Test features
        y_test: Test labels
    """
    print("\n" + "="*80)
    print("MODEL EVALUATION ON TEST SET")
    print("="*80)

    # Preprocess test data
    X_test_processed = X_test
    if trainer.scaler:
        X_test_processed = trainer.scaler.transform(X_test)

    results = []

    for model_name, model in trainer.models.items():
        if model is None:
            continue

        print(f"\n{model_name.upper()}:")
        print("-" * 40)

        try:
            # Predictions
            y_pred = model.predict(X_test_processed)
            y_proba = model.predict_proba(X_test_processed)[:, 1]

            # Metrics
            from sklearn.metrics import (
                accuracy_score, precision_score, recall_score, f1_score,
                roc_auc_score, confusion_matrix
            )

            accuracy = accuracy_score(y_test, y_pred)
            precision = precision_score(y_test, y_pred, zero_division=0)
            recall = recall_score(y_test, y_pred, zero_division=0)
            f1 = f1_score(y_test, y_pred, zero_division=0)
            auc = roc_auc_score(y_test, y_proba)

            print(f"  Accuracy:  {accuracy:.4f}")
            print(f"  Precision: {precision:.4f}")
            print(f"  Recall:    {recall:.4f}")
            print(f"  F1 Score:  {f1:.4f}")
            print(f"  AUC-ROC:   {auc:.4f}")

            # Confusion matrix
            cm = confusion_matrix(y_test, y_pred)
            print(f"\n  Confusion Matrix:")
            print(f"    TN: {cm[0,0]:3d}  FP: {cm[0,1]:3d}")
            print(f"    FN: {cm[1,0]:3d}  TP: {cm[1,1]:3d}")

            results.append({
                'model': model_name,
                'accuracy': accuracy,
                'precision': precision,
                'recall': recall,
                'f1': f1,
                'auc': auc
            })

        except Exception as e:
            print(f"  Error evaluating {model_name}: {e}")

    # Summary comparison
    if results:
        print("\n" + "="*80)
        print("MODEL COMPARISON")
        print("="*80)
        df_results = pd.DataFrame(results)
        df_results = df_results.sort_values('auc', ascending=False)
        print(df_results.to_string(index=False))

        # Best model
        best_model = df_results.iloc[0]
        print(f"\nBest Model: {best_model['model']} (AUC: {best_model['auc']:.4f})")

    return results


def generate_training_report(trainer: MLModelTrainer, evaluation_results: List[Dict],
                            feature_names: List[str], version: str):
    """Generate comprehensive training report"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = ML_RESULTS_DIR / f"training_report_v{version}_{timestamp}.json"

    report = {
        'version': version,
        'timestamp': timestamp,
        'configuration': ML_CONFIG,
        'models_trained': list(trainer.models.keys()),
        'num_features': len(feature_names),
        'feature_names': feature_names,
        'evaluation_results': evaluation_results,
        'best_model': max(evaluation_results, key=lambda x: x['auc'])['model'] if evaluation_results else None
    }

    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2, default=str)

    print(f"\nTraining report saved to: {report_path}")

    return report


def main():
    """Main training pipeline"""
    parser = argparse.ArgumentParser(description='Train ML models for Box Strategy')

    parser.add_argument('--data', type=str,
                       help='Path to backtest results JSON file')
    parser.add_argument('--data-dir', type=str, default=str(DATA_DIR),
                       help='Directory containing backtest results (default: results/)')
    parser.add_argument('--models', nargs='+', default=['all'],
                       choices=['all', 'rf', 'random_forest', 'xgb', 'xgboost',
                               'lgbm', 'lightgbm', 'nn', 'neural_network', 'ensemble'],
                       help='Models to train (default: all)')
    parser.add_argument('--version', type=str, default='1',
                       help='Model version (default: 1)')
    parser.add_argument('--test-size', type=float, default=0.2,
                       help='Test set fraction (default: 0.2)')
    parser.add_argument('--val-size', type=float, default=0.2,
                       help='Validation set fraction (default: 0.2)')
    parser.add_argument('--no-gpu', action='store_true',
                       help='Disable GPU acceleration')

    args = parser.parse_args()

    # Print GPU info
    if not args.no_gpu:
        print_gpu_info()

    # Find backtest results file
    if args.data:
        data_file = Path(args.data)
    else:
        # Find most recent multi_market_results file
        results_files = list(Path(args.data_dir).glob('multi_market_results_*.json'))
        if not results_files:
            print(f"ERROR: No backtest results found in {args.data_dir}")
            print("Please run a backtest first using: python run_global_backtest.py --all")
            return
        data_file = max(results_files, key=lambda p: p.stat().st_mtime)
        print(f"Using most recent results file: {data_file.name}")

    if not data_file.exists():
        print(f"ERROR: File not found: {data_file}")
        return

    # Step 1: Load backtest results
    backtest_results = load_backtest_results(data_file)

    # Step 2: Extract features
    engineer = FeatureEngineer(config=ML_CONFIG)
    df_features = extract_all_features(backtest_results, engineer)

    # Step 3: Prepare datasets
    X_train, X_val, X_test, y_train, y_val, y_test, feature_names = prepare_datasets(
        df_features,
        test_size=args.test_size,
        val_size=args.val_size
    )

    # Step 4: Train models
    trainer = train_models(
        X_train, y_train, X_val, y_val,
        feature_names,
        model_names=args.models,
        version=args.version
    )

    # Step 5: Evaluate on test set
    evaluation_results = evaluate_models(trainer, X_test, y_test)

    # Step 6: Generate report
    report = generate_training_report(trainer, evaluation_results, feature_names, args.version)

    print("\n" + "="*80)
    print("TRAINING COMPLETE!")
    print("="*80)
    print(f"Models saved in: {MODELS_DIR}")
    print(f"Results saved in: {ML_RESULTS_DIR}")
    print(f"\nNext steps:")
    print(f"  1. Review training report: {ML_RESULTS_DIR}/training_report_v{args.version}_*.json")
    print(f"  2. Run model evaluation: python ml/model_evaluator.py --version {args.version}")
    print(f"  3. Test with ML backtest: python run_global_backtest.py --all --enable-ml --version {args.version}")


if __name__ == "__main__":
    main()
