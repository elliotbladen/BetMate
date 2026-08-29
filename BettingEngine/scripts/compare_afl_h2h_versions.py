#!/usr/bin/env python3
"""Walk-forward comparison and production build for versioned AFL H2H models."""

import argparse
import json
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss
from xgboost import XGBClassifier

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ml.afl.features import FEATURES_H2H_LEGACY, FEATURES_H2H_SHADOW
from ml.afl.h2h_versioned import H2HModelBundle


def classifier():
    return XGBClassifier(
        n_estimators=400, max_depth=5, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8, min_child_weight=3,
        eval_metric='logloss', random_state=42, n_jobs=-1, verbosity=0,
    )


def clean(df, features, require_market=False):
    out = df.copy()
    for col in features + ['home_win', 'season']:
        out[col] = pd.to_numeric(out.get(col), errors='coerce')
    out = out.dropna(subset=['home_win', 'season'])
    if require_market:
        out = out.dropna(subset=['mkt_home_prob_open'])
    out[features] = out[features].fillna(0)
    return out


def fit_bundle(df, name, features, through, calibrated, decay, require_market):
    data = clean(df[df.season <= through], features, require_market)
    if calibrated:
        calibration_year = through
        base = data[data.season < calibration_year]
        cal = data[data.season == calibration_year]
        if base.empty or cal.empty:
            raise ValueError(f'Cannot time-calibrate {name} through {through}')
    else:
        base, cal = data, None

    weights = None
    if decay:
        weights = np.exp(np.linspace(0, decay, len(base)))
    model = classifier()
    model.fit(base[features], base.home_win.astype(int), sample_weight=weights)
    iso = None
    if cal is not None:
        raw = model.predict_proba(cal[features])[:, 1]
        iso = IsotonicRegression(out_of_bounds='clip', y_min=0.001, y_max=0.999)
        iso.fit(raw, cal.home_win.astype(int))
    return H2HModelBundle(name, features, model, iso, require_market, through)


def score_fold(bundle, test):
    usable = clean(test, bundle.feature_names, bundle.requires_market)
    p = bundle.predict_proba(usable[bundle.feature_names])[:, 1]
    y = usable.home_win.astype(int).to_numpy()
    rows = usable.copy()
    rows['model_home_prob'] = p
    rows['model'] = bundle.name
    return rows, {
        'model': bundle.name, 'season': int(usable.season.iloc[0]), 'games': len(y),
        'accuracy': accuracy_score(y, p >= .5),
        'log_loss': log_loss(y, p, labels=[0, 1]),
        'brier': brier_score_loss(y, p),
    }


def closing_roi(predictions, threshold=.07):
    bets = []
    for _, r in predictions.iterrows():
        ho, ao = r.get('h2h_home_close'), r.get('h2h_away_close')
        if pd.isna(ho) or pd.isna(ao) or ho <= 1 or ao <= 1:
            continue
        raw_h, raw_a = 1 / ho, 1 / ao
        market_h = raw_h / (raw_h + raw_a)
        p = r.model_home_prob
        choices = [('home', p - market_h, ho, int(r.home_win) == 1),
                   ('away', (1-p) - (1-market_h), ao, int(r.home_win) == 0)]
        side, edge, odds, won = max(choices, key=lambda x: x[1])
        if edge >= threshold:
            bets.append({
                'model': r.model, 'season': int(r.season), 'date': r.get('date'),
                'home_team': r.get('home_team'), 'away_team': r.get('away_team'),
                'side': side, 'edge': edge, 'odds': odds,
                'profit': odds - 1 if won else -1,
            })
    b = pd.DataFrame(bets)
    if b.empty:
        return b, {'bets': 0, 'profit': 0.0, 'roi': 0.0}
    return b, {'bets': len(b), 'profit': b.profit.sum(), 'roi': b.profit.mean()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--features', type=Path, required=True)
    ap.add_argument('--out-dir', type=Path, default=ROOT/'outputs'/'backtests'/'afl_h2h_versions')
    ap.add_argument('--test-seasons', default='2023,2024,2025')
    ap.add_argument('--production-through', type=int, default=2025)
    args = ap.parse_args()
    out = args.out_dir
    out.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(args.features, low_memory=False).sort_values(['date', 'season'])
    seasons = [int(x) for x in args.test_seasons.split(',')]
    metrics, predictions = [], []
    for year in seasons:
        train = df[df.season < year]
        test = df[df.season == year]
        specs = [
            fit_bundle(train, 'legacy_primary', FEATURES_H2H_LEGACY,
                       year-1, False, 0.0, False),
            fit_bundle(train, 'current_shadow', FEATURES_H2H_SHADOW,
                       year-1, True, 1.5, True),
        ]
        for model in specs:
            rows, result = score_fold(model, test)
            predictions.append(rows)
            metrics.append(result)

    pred = pd.concat(predictions, ignore_index=True)
    metric = pd.DataFrame(metrics)
    roi_rows, bet_frames = [], []
    for model, group in pred.groupby('model'):
        for threshold in (.05, .07, .10, .15, .20):
            bets, result = closing_roi(group, threshold)
            result.update({'model': model, 'threshold': threshold})
            roi_rows.append(result)
            if not bets.empty:
                bets['threshold'] = threshold
                bet_frames.append(bets)
    roi = pd.DataFrame(roi_rows)
    calibration = pred.copy()
    calibration['probability_bin'] = pd.cut(
        calibration.model_home_prob, np.linspace(0, 1, 11), include_lowest=True
    )
    calibration = (calibration.groupby(['model', 'probability_bin'], observed=True)
                   .agg(games=('home_win', 'size'), mean_prediction=('model_home_prob', 'mean'),
                        actual_home_win_rate=('home_win', 'mean')).reset_index())
    calibration['calibration_gap'] = (
        calibration.actual_home_win_rate - calibration.mean_prediction
    )
    pred.to_csv(out/'walk_forward_predictions.csv', index=False)
    metric.to_csv(out/'walk_forward_metrics.csv', index=False)
    calibration.to_csv(out/'walk_forward_calibration.csv', index=False)
    roi.to_csv(out/'closing_roi_thresholds.csv', index=False)
    if bet_frames:
        pd.concat(bet_frames, ignore_index=True).to_csv(out/'closing_roi_bets.csv', index=False)

    models = ROOT/'ml'/'afl'/'results'/'models'
    models.mkdir(parents=True, exist_ok=True)
    legacy = fit_bundle(df, 'legacy_primary', FEATURES_H2H_LEGACY,
                        args.production_through, False, 0.0, False)
    shadow = fit_bundle(df, 'current_shadow', FEATURES_H2H_SHADOW,
                        args.production_through, True, 1.5, True)
    for filename, model in [('h2h_legacy_primary.pkl', legacy),
                            ('h2h_current_shadow.pkl', shadow),
                            ('h2h_model.pkl', legacy)]:
        with open(models/filename, 'wb') as fh:
            pickle.dump(model, fh)
    summary = {'metrics': metric.to_dict('records'), 'closing_roi': roi.to_dict('records')}
    (out/'summary.json').write_text(json.dumps(summary, indent=2))
    print(metric.to_string(index=False, float_format=lambda x: f'{x:.4f}'))
    print('\nEdge versus no-vig closing market')
    print(roi.to_string(index=False, float_format=lambda x: f'{x:.4f}'))


if __name__ == '__main__':
    main()
