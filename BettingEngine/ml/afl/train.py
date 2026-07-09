#!/usr/bin/env python3
"""
ml/afl/train.py

Train AFL margin / total / H2H ML models.
Default training window: 2022-2023 (modern-rule era, set by game_log.py --min-year).
Validate on 2024. Test (backtest) on 2025.

Models:
    1. margin_model     → XGBoost regressor → predicts home_margin
    2. total_model      → XGBoost regressor → predicts total_score
    3. h2h_model        → XGBoost classifier → predicts home_win (1/0)

sample_weight: exponential decay across training data (oldest → 1x, newest → e^decay x).
season_year feature: lets the model learn the upward scoring trend within the era.

Output:
    ml/afl/results/models/   — saved model files (.pkl)
    ml/afl/results/metrics.txt

USAGE
-----
    python3 ml/afl/train.py
    python3 ml/afl/train.py --features ml/afl/results/features_afl.csv
    python3 ml/afl/train.py --decay 1.5   (default; 1.5 = newest game weighted ~4.5x oldest)
"""

import argparse
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import (
    accuracy_score, brier_score_loss, log_loss,
    mean_absolute_error, root_mean_squared_error
)

try:
    import xgboost as xgb
    HAS_XGB = True
except ImportError:
    HAS_XGB = False
    print('WARNING: xgboost not installed — falling back to RandomForest')
    from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier

ROOT        = Path(__file__).resolve().parent.parent.parent
FEATURES    = ROOT / 'ml' / 'afl' / 'results' / 'features_afl.csv'
MODELS_DIR  = ROOT / 'ml' / 'afl' / 'results' / 'models'
METRICS_OUT = ROOT / 'ml' / 'afl' / 'results' / 'metrics.txt'

# ---------------------------------------------------------------------------
# Feature columns fed to the models — SHARED with scripts/prepare_afl_round.py
# via ml/afl/features.py. Never redefine locally (2026-07-09 shadow incident).
# ---------------------------------------------------------------------------
try:
    from ml.afl.features import FEATURES_MARGIN_TOTAL, FEATURES_H2H
except ImportError:   # run as a script (python ml\afl\train.py) — package root not on sys.path
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    from ml.afl.features import FEATURES_MARGIN_TOTAL, FEATURES_H2H

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def load_data(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path, low_memory=False)
    # fill empty strings → NaN
    df.replace('', np.nan, inplace=True)
    return df


def prep_numeric(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce')
    return df


def make_model_regressor(n_estimators=400):
    if HAS_XGB:
        return xgb.XGBRegressor(
            n_estimators=n_estimators,
            max_depth=5,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            min_child_weight=3,
            random_state=42,
            n_jobs=-1,
            verbosity=0,
        )
    else:
        return RandomForestRegressor(n_estimators=200, max_depth=10, random_state=42, n_jobs=-1)


def make_model_classifier(n_estimators=400):
    if HAS_XGB:
        return xgb.XGBClassifier(
            n_estimators=n_estimators,
            max_depth=5,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            min_child_weight=3,
            use_label_encoder=False,
            eval_metric='logloss',
            random_state=42,
            n_jobs=-1,
            verbosity=0,
        )
    else:
        return RandomForestClassifier(n_estimators=200, max_depth=10, random_state=42, n_jobs=-1)


# ---------------------------------------------------------------------------
# Training + evaluation
# ---------------------------------------------------------------------------

def train_and_evaluate(df: pd.DataFrame, feature_cols: list[str], target: str,
                       model_type: str, label: str, decay: float = 1.5) -> tuple:
    """
    Returns (fitted_model, metrics_dict, val_predictions, test_predictions)
    model_type: 'reg' | 'cls'
    decay: exponential decay exponent for sample_weight. 1.5 → newest game weighted
           e^1.5 ≈ 4.5x vs oldest. Training data must be sorted chronologically
           (guaranteed by game_log.py which sorts by date).
    """
    df = df.copy()

    # ensure all feature cols exist
    for c in feature_cols:
        if c not in df.columns:
            df[c] = np.nan

    df = prep_numeric(df, feature_cols + [target])

    # split
    train = df[df['split'] == 'train'].copy()
    val   = df[df['split'] == 'validate'].copy()
    test  = df[df['split'] == 'test'].copy()

    # drop rows missing target
    train = train.dropna(subset=[target])
    val   = val.dropna(subset=[target])
    test  = test.dropna(subset=[target])

    X_train = train[feature_cols].copy()
    y_train = train[target]
    X_val   = val[feature_cols].copy()
    y_val   = val[target]
    X_test  = test[feature_cols].copy()
    y_test  = test[target]

    # Smart imputation: mkt_home_prob_open NaN → fall back to elo_win_prob
    # (avoids 0 as imputed probability which would corrupt EV calc)
    for X in (X_train, X_val, X_test):
        if 'mkt_home_prob_open' in X.columns and 'elo_win_prob' in X.columns:
            X['mkt_home_prob_open'] = X['mkt_home_prob_open'].fillna(X['elo_win_prob'])

    X_train = X_train.fillna(0)
    X_val   = X_val.fillna(0)
    X_test  = X_test.fillna(0)

    # Exponential time-decay weights — upweights recent games within training window
    n = len(X_train)
    sample_weight = np.exp(np.linspace(0, decay, n))  # 1.0 (oldest) → e^decay (newest)

    print(f'\n--- {label} ---')
    print(f'  Train: {len(X_train)}, Val: {len(X_val)}, Test: {len(X_test)}')
    print(f'  sample_weight decay={decay:.1f} (newest/oldest ratio: {np.exp(decay):.1f}x)')

    if model_type == 'reg':
        model = make_model_regressor()
    else:
        model = make_model_classifier()
        y_train = y_train.astype(int)
        y_val   = y_val.astype(int)
        y_test  = y_test.astype(int)

    model.fit(X_train, y_train, sample_weight=sample_weight)

    # Isotonic calibration — fixes raw XGBoost probability overconfidence
    # (the cause of the inverted EV signal: high-EV bets → negative ROI).
    # Prefer fitting on a held-out val set (cv='prefit'); fall back to
    # 5-fold CV within training data when no val set exists.
    has_val = len(X_val) > 0
    if model_type == 'cls':
        if has_val:
            calibrator = CalibratedClassifierCV(model, cv='prefit', method='isotonic')
            calibrator.fit(X_val, y_val)
            print('  Calibration: isotonic regression on val set')
        else:
            # No separate val split — use 5-fold CV calibration within training.
            # Random folds (not time-ordered) introduce minor leakage risk but
            # calibration is low-stakes vs using raw logit output with known bias.
            calibrator = CalibratedClassifierCV(model, cv=5, method='isotonic')
            calibrator.fit(X_train, y_train, sample_weight=sample_weight)
            print('  Calibration: isotonic regression via 5-fold CV on training data')
        model = calibrator

    if model_type == 'reg':
        test_pred = model.predict(X_test)
        test_mae  = mean_absolute_error(y_test, test_pred)
        test_rmse = root_mean_squared_error(y_test, test_pred)
        test_dir  = np.mean(np.sign(test_pred) == np.sign(y_test))
        if has_val:
            val_pred  = model.predict(X_val)
            val_mae   = mean_absolute_error(y_val, val_pred)
            val_rmse  = root_mean_squared_error(y_val, val_pred)
            val_dir   = np.mean(np.sign(val_pred) == np.sign(y_val))
            print(f'  Val  MAE={val_mae:.2f}  RMSE={val_rmse:.2f}  DirAcc={val_dir:.3f}')
        else:
            val_pred, val_mae, val_rmse, val_dir = np.array([]), None, None, None
            print('  Val  (no validate split)')
        print(f'  Test MAE={test_mae:.2f}  RMSE={test_rmse:.2f}  DirAcc={test_dir:.3f}')
        metrics = {
            'val_mae':      round(val_mae, 3) if val_mae is not None else None,
            'test_mae':     round(test_mae, 3),
            'val_rmse':     round(val_rmse, 3) if val_rmse is not None else None,
            'test_rmse':    round(test_rmse, 3),
            'val_dir_acc':  round(float(val_dir), 4) if val_dir is not None else None,
            'test_dir_acc': round(float(test_dir), 4),
        }
    else:
        test_pred_cls = model.predict(X_test)
        test_prob     = model.predict_proba(X_test)[:, 1]
        test_acc      = accuracy_score(y_test, test_pred_cls)
        test_ll       = log_loss(y_test, test_prob)
        test_brier    = brier_score_loss(y_test, test_prob)
        if has_val:
            val_pred_cls  = model.predict(X_val)
            val_prob      = model.predict_proba(X_val)[:, 1]
            val_acc       = accuracy_score(y_val, val_pred_cls)
            val_ll        = log_loss(y_val, val_prob)
            val_brier     = brier_score_loss(y_val, val_prob)
            print(f'  Val  Acc={val_acc:.4f}  LogLoss={val_ll:.4f}  Brier={val_brier:.4f}')
        else:
            val_prob  = np.array([])
            val_acc   = val_ll = val_brier = None
            print('  Val  (no validate split)')
        print(f'  Test Acc={test_acc:.4f}  LogLoss={test_ll:.4f}  Brier={test_brier:.4f}')
        metrics = {
            'val_acc':      round(val_acc, 4)   if val_acc   is not None else None,
            'test_acc':     round(test_acc, 4),
            'val_logloss':  round(val_ll, 4)    if val_ll    is not None else None,
            'test_logloss': round(test_ll, 4),
            'val_brier':    round(val_brier, 4) if val_brier is not None else None,
            'test_brier':   round(test_brier, 4),
        }
        val_pred  = val_prob
        test_pred = test_prob

    # feature importances
    if hasattr(model, 'feature_importances_'):
        fi = sorted(zip(feature_cols, model.feature_importances_),
                    key=lambda x: -x[1])
        print('  Top-10 features:')
        for fname, imp in fi[:10]:
            print(f'    {fname:<30} {imp:.4f}')

    return model, metrics, val_pred, test_pred


def save_model(model, name: str, models_dir: Path):
    models_dir.mkdir(parents=True, exist_ok=True)
    path = models_dir / f'{name}.pkl'
    with open(path, 'wb') as f:
        pickle.dump(model, f)
    print(f'  Saved → {path}')
    return path


def write_metrics(all_metrics: dict, out: Path):
    lines = ['AFL ML — Training Metrics\n', '=' * 50 + '\n']
    for label, m in all_metrics.items():
        lines.append(f'\n{label}:\n')
        for k, v in m.items():
            lines.append(f'  {k}: {v}\n')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(''.join(lines))
    print(f'\nMetrics saved → {out}')


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--features', default=str(FEATURES))
    parser.add_argument('--decay', default=1.5, type=float,
                        help='Exponential decay exponent for sample_weight. '
                             '1.5 (default) = newest game weighted ~4.5x oldest. '
                             '0 = uniform weights.')
    args = parser.parse_args()

    csv_path = Path(args.features)
    if not csv_path.exists():
        print(f'ERROR: features CSV not found: {csv_path}')
        print('Run  python3 ml/afl/game_log.py  first.')
        return

    df = load_data(csv_path)
    print(f'Loaded {len(df)} rows from {csv_path.name}')
    print(f'Splits: {df["split"].value_counts().to_dict()}')
    print(f'Training seasons: {sorted(df[df["split"] == "train"]["season"].unique())}')

    all_metrics = {}

    # ── 1. Margin model ──────────────────────────────────────────────────────
    margin_model, margin_metrics, val_margin, test_margin = train_and_evaluate(
        df, FEATURES_MARGIN_TOTAL, 'home_margin', 'reg', 'Margin Model (home_margin)',
        decay=args.decay)
    save_model(margin_model, 'margin_model', MODELS_DIR)
    all_metrics['margin_model'] = margin_metrics

    # ── 2. Total model ───────────────────────────────────────────────────────
    total_model, total_metrics, val_total, test_total = train_and_evaluate(
        df, FEATURES_MARGIN_TOTAL, 'total_score', 'reg', 'Total Model (total_score)',
        decay=args.decay)
    save_model(total_model, 'total_model', MODELS_DIR)
    all_metrics['total_model'] = total_metrics

    # ── 3. H2H classifier ───────────────────────────────────────────────────
    h2h_model, h2h_metrics, val_h2h, test_h2h = train_and_evaluate(
        df, FEATURES_H2H, 'home_win', 'cls', 'H2H Classifier (home_win)',
        decay=args.decay)
    save_model(h2h_model, 'h2h_model', MODELS_DIR)
    all_metrics['h2h_model'] = h2h_metrics

    write_metrics(all_metrics, METRICS_OUT)

    # ── Summary ──────────────────────────────────────────────────────────────
    print('\n' + '=' * 55)
    print('AFL ML Training Complete')
    print(f'  Training window: {sorted(df[df["split"] == "train"]["season"].unique())}')
    print(f'  sample_weight decay: {args.decay}')
    print(f'  Margin MAE   (test 2025): {margin_metrics["test_mae"]} pts')
    print(f'  Margin DirAcc(test 2025): {margin_metrics["test_dir_acc"]:.1%}')
    print(f'  Total  MAE   (test 2025): {total_metrics["test_mae"]} pts')
    print(f'  H2H Accuracy (test 2025): {h2h_metrics["test_acc"]:.1%}')
    print()
    print('Next step:')
    print('  python3 ml/afl/backtest_2025.py')
    print('=' * 55)


if __name__ == '__main__':
    main()
