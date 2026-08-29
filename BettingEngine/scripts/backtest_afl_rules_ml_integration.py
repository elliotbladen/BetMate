#!/usr/bin/env python3
"""Test leakage-safe ways to integrate archived AFL rules and ML probabilities."""

import argparse
import glob
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss

ROOT = Path(__file__).resolve().parents[1]


def logit(p):
    p = np.clip(np.asarray(p, float), .01, .99)
    return np.log(p / (1-p))


def load_archived(results_glob, history):
    frames = []
    for path in glob.glob(str(results_glob)):
        d = pd.read_csv(path, low_memory=False)
        needed = {'season', 'round_number', 'game_date', 'home_team', 'away_team',
                  'rules_home_prob', 'ml_h2h'}
        if needed.issubset(d.columns):
            frames.append(d[list(needed)].copy())
    pred = pd.concat(frames, ignore_index=True)
    for c in ['season', 'round_number', 'rules_home_prob', 'ml_h2h']:
        pred[c] = pd.to_numeric(pred[c], errors='coerce')
    pred['game_date'] = pd.to_datetime(pred.game_date)

    hist = pd.read_csv(history, low_memory=False)
    hist['game_date'] = pd.to_datetime(hist.date)
    cols = ['season', 'game_date', 'home_team', 'away_team', 'home_win',
            'mkt_home_prob_open', 'h2h_home_close', 'h2h_away_close']
    hist = hist[cols].copy()
    hist['season'] = pd.to_numeric(hist.season, errors='coerce')
    # Some archived price-ups store UTC fixture dates one calendar day earlier
    # than the historical-results workbook. Match the same teams/season to the
    # nearest date, with a strict 2-day ceiling.
    candidates = pred.reset_index(names='prediction_id').merge(
        hist, on=['season', 'home_team', 'away_team'], how='left', suffixes=('', '_actual'))
    candidates['date_gap'] = (candidates.game_date-candidates.game_date_actual).abs().dt.days
    out = (candidates[candidates.date_gap.le(2)].sort_values(['prediction_id', 'date_gap'])
           .drop_duplicates('prediction_id').drop(columns=['game_date_actual', 'date_gap']))
    return out.dropna(subset=['rules_home_prob', 'ml_h2h', 'home_win']).sort_values(
        ['round_number', 'game_date', 'home_team'])


def add_candidates(d):
    out = d.copy()
    out['rules_only'] = out.rules_home_prob
    out['ml_only'] = out.ml_h2h
    out['market_open'] = out.mkt_home_prob_open
    for rw in (.25, .50, .75):
        out[f'blend_rules_{int(rw*100)}'] = rw*out.rules_home_prob + (1-rw)*out.ml_h2h
    agree = (out.rules_home_prob >= .5) == (out.ml_h2h >= .5)
    out['agreement_gate'] = np.where(
        agree, .5*out.rules_home_prob + .5*out.ml_h2h, out.mkt_home_prob_open
    )
    return out


def walk_forward_meta(d, min_rounds=5):
    features = ['rules_home_prob', 'ml_h2h', 'mkt_home_prob_open']
    pred = pd.Series(np.nan, index=d.index)
    coefficients = []
    rounds = sorted(d.round_number.unique())
    for test_round in rounds:
        prior_rounds = [r for r in rounds if r < test_round]
        if len(prior_rounds) < min_rounds:
            continue
        train = d[d.round_number.isin(prior_rounds)].dropna(subset=features + ['home_win'])
        test = d[d.round_number.eq(test_round)].dropna(subset=features)
        if train.home_win.nunique() < 2 or test.empty:
            continue
        Xtr = np.column_stack([logit(train[c]) for c in features] + [
            np.abs(logit(train.rules_home_prob)-logit(train.ml_h2h))])
        Xte = np.column_stack([logit(test[c]) for c in features] + [
            np.abs(logit(test.rules_home_prob)-logit(test.ml_h2h))])
        model = LogisticRegression(C=.25, max_iter=2000)
        model.fit(Xtr, train.home_win.astype(int))
        pred.loc[test.index] = model.predict_proba(Xte)[:, 1]
        coefficients.append({
            'test_round': test_round, 'training_games': len(train),
            'rules_logit': model.coef_[0][0], 'ml_logit': model.coef_[0][1],
            'market_logit': model.coef_[0][2], 'disagreement': model.coef_[0][3],
            'intercept': model.intercept_[0],
        })
    return pred, pd.DataFrame(coefficients)


def metrics(d, candidates):
    rows = []
    for name in candidates:
        z = d.dropna(subset=[name, 'home_win'])
        p = np.clip(z[name].to_numpy(float), .001, .999)
        y = z.home_win.astype(int).to_numpy()
        rows.append({
            'candidate': name, 'games': len(z), 'rounds': z.round_number.nunique(),
            'accuracy': accuracy_score(y, p >= .5), 'brier': brier_score_loss(y, p),
            'log_loss': log_loss(y, p, labels=[0, 1]),
        })
    return pd.DataFrame(rows).sort_values('brier')


def roi(d, candidates, threshold=.07):
    rows = []
    for name in candidates:
        bets = []
        for _, r in d.dropna(subset=[name, 'h2h_home_close', 'h2h_away_close']).iterrows():
            ih, ia = 1/r.h2h_home_close, 1/r.h2h_away_close
            mh = ih/(ih+ia)
            p = r[name]
            home_edge, away_edge = p-mh, (1-p)-(1-mh)
            if max(home_edge, away_edge) < threshold:
                continue
            home = home_edge >= away_edge
            won = bool(r.home_win) if home else not bool(r.home_win)
            odds = r.h2h_home_close if home else r.h2h_away_close
            bets.append(odds-1 if won else -1)
        rows.append({'candidate': name, 'threshold': threshold, 'bets': len(bets),
                     'profit': sum(bets), 'roi': np.mean(bets) if bets else np.nan})
    return pd.DataFrame(rows).sort_values('roi', ascending=False)


def round_bootstrap(d, candidates, repeats=5000):
    rng = np.random.default_rng(42)
    rounds = d.round_number.unique()
    base = 'rules_only'
    rows = []
    for name in candidates:
        z = d.dropna(subset=[base, name, 'home_win'])
        candidate_rounds = z.round_number.unique()
        by_round = []
        for r in candidate_rounds:
            q = z[z.round_number.eq(r)]
            y = q.home_win.to_numpy(float)
            by_round.append((
                np.square(q[name].to_numpy(float)-y).sum(),
                np.square(q[base].to_numpy(float)-y).sum(), len(q),
            ))
        by_round = np.asarray(by_round, float)
        diffs = []
        for _ in range(repeats):
            sample = by_round[rng.integers(0, len(by_round), len(by_round))].sum(axis=0)
            diffs.append((sample[0]-sample[1])/sample[2])
        rows.append({'candidate': name, 'brier_delta_vs_rules': np.mean(diffs),
                     'ci_low': np.quantile(diffs, .025), 'ci_high': np.quantile(diffs, .975)})
    return pd.DataFrame(rows).sort_values('brier_delta_vs_rules')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--results-glob', default=str(ROOT/'results'/'r*_afl_2026.csv'))
    ap.add_argument('--history', type=Path,
                    default=ROOT/'outputs'/'backtests'/'afl_features_2009_2026.csv')
    ap.add_argument('--out-dir', type=Path,
                    default=ROOT/'outputs'/'backtests'/'afl_rules_ml_integration')
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    data = add_candidates(load_archived(args.results_glob, args.history))
    data['walk_forward_meta'] , coefs = walk_forward_meta(data)
    candidates = ['rules_only', 'ml_only', 'market_open', 'blend_rules_25',
                  'blend_rules_50', 'blend_rules_75', 'agreement_gate', 'walk_forward_meta']
    result = metrics(data, candidates)
    returns = roi(data, candidates)
    uncertainty = round_bootstrap(data, candidates)
    common = data[data.walk_forward_meta.notna()].copy()
    common_result = metrics(common, candidates)
    common_returns = roi(common, candidates)
    data.to_csv(args.out_dir/'game_predictions.csv', index=False)
    result.to_csv(args.out_dir/'metrics.csv', index=False)
    returns.to_csv(args.out_dir/'closing_roi_7pp.csv', index=False)
    uncertainty.to_csv(args.out_dir/'round_bootstrap.csv', index=False)
    common_result.to_csv(args.out_dir/'meta_window_metrics.csv', index=False)
    common_returns.to_csv(args.out_dir/'meta_window_closing_roi_7pp.csv', index=False)
    coefs.to_csv(args.out_dir/'meta_coefficients.csv', index=False)
    print(f'Usable archived games: {len(data)} across {data.round_number.nunique()} rounds')
    print('\nProbability quality\n', result.to_string(index=False, float_format=lambda x:f'{x:.4f}'))
    print('\n7pp edge vs closing market\n', returns.to_string(index=False, float_format=lambda x:f'{x:.4f}'))
    print('\nRound-cluster bootstrap (negative improves on rules)\n',
          uncertainty.to_string(index=False, float_format=lambda x:f'{x:.4f}'))
    print('\nSame evaluation window as walk-forward meta\n',
          common_result.to_string(index=False, float_format=lambda x:f'{x:.4f}'))


if __name__ == '__main__':
    main()
