#!/usr/bin/env python3
"""Train and walk-forward test independent NRL margin/H2H XGBoost shadows."""

import argparse
import json
import pickle
import joblib
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss, mean_absolute_error
from xgboost import XGBClassifier, XGBRegressor

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ml.nrl.features import PREMARKET_FEATURES
from ml.nrl.models import (
    H2HShadowBundle,
    MarginShadowBundle,
    margin_to_home_win_probability,
)


def margin_estimator():
    return XGBRegressor(
        n_estimators=1200, max_depth=3, learning_rate=.025, min_child_weight=12,
        subsample=.8, colsample_bytree=.8, reg_alpha=.2, reg_lambda=2,
        objective='reg:pseudohubererror', random_state=42, n_jobs=-1, verbosity=0,
    )


def h2h_estimator():
    return XGBClassifier(
        n_estimators=800, max_depth=3, learning_rate=.025, min_child_weight=12,
        subsample=.8, colsample_bytree=.8, reg_alpha=.2, reg_lambda=2,
        eval_metric='logloss', random_state=42, n_jobs=-1, verbosity=0,
    )


def total_estimator():
    return XGBRegressor(
        n_estimators=800, max_depth=3, learning_rate=.025, min_child_weight=12,
        subsample=.8, colsample_bytree=.8, reg_alpha=.2, reg_lambda=2,
        objective='reg:squarederror', random_state=42, n_jobs=-1, verbosity=0,
    )


def clean(df):
    out=df.copy()
    for c in PREMARKET_FEATURES+['season','actual_margin','home_win']:
        out[c]=pd.to_numeric(out.get(c),errors='coerce')
    return out.dropna(subset=['season','actual_margin','home_win']).sort_values('date')


def fit(train, through, version):
    calibration_year=through
    base=train[train.season<calibration_year]
    cal=train[train.season.eq(calibration_year)]
    if base.empty or cal.empty: raise ValueError('Need an independent calibration season')
    X=base[PREMARKET_FEATURES]
    margin=margin_estimator(); margin.fit(X,base.actual_margin)
    classifier=h2h_estimator(); classifier.fit(X,base.home_win.astype(int))
    raw=classifier.predict_proba(cal[PREMARKET_FEATURES])[:,1]
    calibrator=LogisticRegression(C=1.0).fit(raw.reshape(-1,1),cal.home_win.astype(int))
    residual_scale=float(np.std(cal.actual_margin-margin.predict(cal[PREMARKET_FEATURES]),ddof=1))
    return (
        MarginShadowBundle(PREMARKET_FEATURES,margin,through,version,residual_scale),
        H2HShadowBundle(PREMARKET_FEATURES,classifier,calibrator,through,version),
    )


def evaluate(margin,h2h,test,season):
    X=test[PREMARKET_FEATURES]; mp=margin.predict(X)
    classifier_hp=h2h.predict_proba(X)[:,1]
    hp=margin_to_home_win_probability(mp,margin.residual_scale)
    y=test.home_win.astype(int)
    rows=test[['season','date','home_team','away_team','actual_margin','home_win']].copy()
    rows['ml_margin']=mp
    rows['ml_home_prob']=hp
    rows['classifier_home_prob']=classifier_hp
    metrics={'season':season,'games':len(test),'margin_mae':mean_absolute_error(test.actual_margin,mp),
             'h2h_accuracy':accuracy_score(y,hp>=.5),'brier':brier_score_loss(y,hp),
             'log_loss':log_loss(y,hp,labels=[0,1]),'residual_scale':margin.residual_scale}
    return rows,metrics


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--features',type=Path,default=ROOT/'ml/nrl/results/features_nrl.csv')
    ap.add_argument('--out-dir',type=Path,default=ROOT/'ml/nrl/results')
    ap.add_argument('--production-through',type=int,default=2025)
    args=ap.parse_args(); args.out_dir.mkdir(parents=True,exist_ok=True)
    d=clean(pd.read_csv(args.features,low_memory=False))
    predictions=[]; metrics=[]
    for season in (2024,2025):
        version=f'nrl_premarket_shadow_test_{season}'
        margin,h2h=fit(d[d.season<season],season-1,version)
        rows,result=evaluate(margin,h2h,d[d.season.eq(season)],season)
        predictions.append(rows); metrics.append(result)
    pd.concat(predictions).to_csv(args.out_dir/'walk_forward_predictions.csv',index=False)
    pd.DataFrame(metrics).to_csv(args.out_dir/'walk_forward_metrics.csv',index=False)

    version=f'nrl_premarket_shadow_v1_through_{args.production_through}'
    margin,h2h=fit(d[d.season<=args.production_through],args.production_through,version)
    models=args.out_dir/'models'; models.mkdir(parents=True,exist_ok=True)
    for name,model in [('margin_premarket.pkl',margin),('h2h_premarket.pkl',h2h)]:
        with open(models/name,'wb') as f: pickle.dump(model,f)
    # Compatibility artifacts for the existing round shadow runner. These are
    # the same independent bundles, not the historical tier-overlaid models.
    compat=ROOT/'ml'/'models'; compat.mkdir(parents=True,exist_ok=True)
    joblib.dump(margin,compat/'margin_model_v20260812.joblib')
    joblib.dump(h2h,compat/'h2h_model_v20260812.joblib')
    # Totals are explicitly research-only; the runner requires a third object
    # for display, so train a standalone regressor without rule overlays.
    total=total_estimator()
    base=d[d.season<args.production_through]
    total.fit(base[PREMARKET_FEATURES],pd.to_numeric(base.actual_total,errors='coerce'))
    joblib.dump(total,compat/'total_model_v20260812.joblib')
    manifest={'model_version':version,'trained_through':args.production_through,
              'features':PREMARKET_FEATURES,'market_features':False,
              'calibration':'sigmoid on final training season'}
    (models/'manifest.json').write_text(json.dumps(manifest,indent=2))
    print(pd.DataFrame(metrics).to_string(index=False,float_format=lambda x:f'{x:.4f}'))
    print(f'Saved production bundles to {models}')


if __name__=='__main__': main()
