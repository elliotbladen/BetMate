#!/usr/bin/env python3
"""
scripts/score_nrl_ml_vs_rules.py

Score the production NRL ML shadow against the rules engine over a season.

Reads the rebuilt feature table (scripts/build_nrl_features.py), runs the
production models on it, joins to the rules engine's own round pricing CSVs —
which were written before each round was played — and reports margin, H2H,
handicap and totals side by side.

The ML is deliberately run WITHOUT tier overlays, matching how the shadow is
actually deployed (`ml_adj_* == ml_raw_*` in ml_shadow_predictions). The rules
column carries the full T1-T10 stack. That asymmetry is real and is reported.

USAGE
-----
    python scripts/score_nrl_ml_vs_rules.py --season 2026
"""
from __future__ import annotations

import argparse
import glob
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from ml.nrl.features import PREMARKET_FEATURES
from ml.nrl.models import margin_to_home_win_probability

FEATS = ROOT / 'ml' / 'nrl' / 'results' / 'features_nrl_extended.csv'
MODELS = ROOT / 'ml' / 'models'


def load_rules(season: int) -> pd.DataFrame:
    rows = []
    for f in sorted(glob.glob(str(ROOT / 'results' / f'r*_pricing_{season}.csv'))):
        d = pd.read_csv(f, encoding='latin-1')
        need = {'date', 'home_team', 'away_team', 'final_margin', 'final_total'}
        if not need.issubset(d.columns):
            continue
        keep = ['date', 'home_team', 'away_team', 'final_margin', 'final_total', 'round']
        rows.append(d[[c for c in keep if c in d.columns]])
    out = pd.concat(rows, ignore_index=True)
    return out.drop_duplicates(subset=['date', 'home_team', 'away_team'], keep='last')


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--season', type=int, default=2026)
    args = ap.parse_args()

    f = pd.read_csv(FEATS)
    f = f[(f.season == args.season) & f.actual_margin.notna()].copy()
    X = f[PREMARKET_FEATURES].apply(pd.to_numeric, errors='coerce')

    margin_b = joblib.load(MODELS / 'margin_model_v20260812.joblib')
    total_m = joblib.load(MODELS / 'total_model_v20260812.joblib')
    h2h_b = joblib.load(MODELS / 'h2h_model_v20260812.joblib')

    f['ml_margin'] = margin_b.predict(X)
    f['ml_total'] = total_m.predict(X)
    f['ml_h2h_clf'] = h2h_b.predict_proba(X)[:, 1]
    f['ml_h2h_from_margin'] = margin_to_home_win_probability(
        f.ml_margin.to_numpy(float), margin_b.residual_scale)

    rules = load_rules(args.season)
    m = f.merge(rules, on=['date', 'home_team', 'away_team'], how='inner')
    print(f'ML scored on {len(f)} {args.season} games; '
          f'{len(m)} also have a rules price -> head-to-head sample n={len(m)}\n')
    if not len(m):
        return

    act = m.actual_margin.to_numpy(float)
    tot = m.actual_total.to_numpy(float)
    y = (act > 0).astype(int)

    print(f"{'MARGIN':24s}{'bias':>8s}{'MAE':>8s}{'RMSE':>8s}{'sign acc':>10s}")
    series = {'Rules (T1-T10)': m.final_margin.to_numpy(float),
              'ML (no tiers)': m.ml_margin.to_numpy(float)}
    for w in (0.25, 0.5, 0.75):
        series[f'Blend {int(w*100)}% ML'] = (1 - w) * m.final_margin.to_numpy(float) + w * m.ml_margin.to_numpy(float)
    for k, v in series.items():
        e = v - act
        print(f'{k:24s}{e.mean():+8.2f}{np.abs(e).mean():8.2f}'
              f'{np.sqrt((e**2).mean()):8.2f}{(((v>0)==(act>0)).mean()*100):9.1f}%')

    print(f"\n{'TOTALS':24s}{'bias':>8s}{'MAE':>8s}{'RMSE':>8s}")
    tseries = {'Rules (T1-T10)': m.final_total.to_numpy(float),
               'ML (no tiers)': m.ml_total.to_numpy(float)}
    for w in (0.25, 0.5, 0.75):
        tseries[f'Blend {int(w*100)}% ML'] = (1 - w) * m.final_total.to_numpy(float) + w * m.ml_total.to_numpy(float)
    for k, v in tseries.items():
        e = v - tot
        print(f'{k:24s}{e.mean():+8.2f}{np.abs(e).mean():8.2f}{np.sqrt((e**2).mean()):8.2f}')

    def ll(p):
        p = np.clip(p, 1e-6, 1 - 1e-6)
        return -np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))

    print(f"\n{'H2H':24s}{'acc':>8s}{'logloss':>10s}{'brier':>9s}")
    for k, p in [('ML classifier', m.ml_h2h_clf.to_numpy(float)),
                 ('ML margin->prob', m.ml_h2h_from_margin.to_numpy(float))]:
        print(f'{k:24s}{(((p>0.5).astype(int)==y).mean()*100):7.1f}%{ll(p):10.4f}{np.mean((p-y)**2):9.4f}')
    print(f'   (rules H2H probability is not stored in the pricing CSVs — '
          f'rules sign accuracy above is the comparable figure)')

    out = ROOT / 'outputs' / 'results' / f'nrl_ml_vs_rules_{args.season}.csv'
    out.parent.mkdir(parents=True, exist_ok=True)
    m.to_csv(out, index=False)
    print(f'\nSaved joined rows -> {out}')


if __name__ == '__main__':
    main()
