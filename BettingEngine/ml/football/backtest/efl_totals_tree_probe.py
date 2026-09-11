#!/usr/bin/env python3
"""One attempt with a tree ensemble: do interactions exist that the linear probe missed?

This is the single follow-up licensed by TOTALS_SIGNAL_PROBE.md's closing caveat
("a tree ensemble might extract interaction effects ... worth one attempt before
closing the question for good"). It is NOT a re-opening of the market-anchored line,
which the vault pre-registration closed. Design is frozen below before running.

Frozen design
  * Same data, same walk-forward, same vault exclusion (2025/26 never loaded) and the
    same market-only baseline as efl_totals_signal_probe.py, so the numbers are
    directly comparable to the published table.
  * The market enters as an XGBoost `base_margin` (= logit of the de-vigged close),
    so the trees can only learn RESIDUAL structure. A tree given the market as an
    ordinary feature has to rediscover it and will look worse for reasons that have
    nothing to do with the hypothesis.
  * Two feature sets, both pre-specified, no grid search:
      A  the same 7 symmetric aggregates the linear probe used (like-for-like).
      B  the 21 raw per-team rolling stats. Symmetric sums are exactly what would
         destroy an interaction, so B is the strongest form of the hypothesis.
  * One hyper-parameter set, deliberately conservative. Rounds are chosen by early
    stopping on the LAST TRAINING SEASON held out; never on the test season.
  * Verdict rule, unchanged from the linear probe: beats market-only in ALL test
    seasons AND pooled improvement significant at p<0.05. Anything less is noise.
"""
from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore", category=FutureWarning)   # sklearn penalty= deprecation

import numpy as np
import pandas as pd
import xgboost as xgb
from scipy.stats import chi2
from sklearn.metrics import log_loss

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from ml.football.backtest.efl_totals_signal_probe import (  # noqa: E402
    FEATURES, TEAM_STATS, TEST_SEASONS, build, fit_predict, load, logit,
)

RAW_FEATURES = (
    [f"{side}_r_{s}" for side in ("home", "away") for s in TEAM_STATS]
    + ["home_rest", "away_rest", "ref_goals"]
)

PARAMS = dict(
    objective="binary:logistic", eval_metric="logloss",
    max_depth=3, eta=0.02, subsample=0.8, colsample_bytree=0.8,
    min_child_weight=20, reg_lambda=5.0, nthread=4,
)
MAX_ROUNDS, EARLY_STOP = 2000, 50
SEED = 20260910


def _dm(frame: pd.DataFrame, cols: list[str], margin: str | None) -> xgb.DMatrix:
    d = xgb.DMatrix(frame[cols].values, label=frame.over25.values, feature_names=cols)
    if margin:
        d.set_base_margin(logit(frame[margin].values))
    return d


def tree_predict(tr: pd.DataFrame, te: pd.DataFrame, cols: list[str],
                 margin: str | None) -> tuple[np.ndarray, int]:
    """Fit with early stopping on the last training season, refit on all of it."""
    seasons = sorted(tr.Season.unique())
    inner_tr = tr[tr.Season != seasons[-1]]
    inner_va = tr[tr.Season == seasons[-1]]
    if len(inner_tr) < 200 or len(inner_va) < 100:      # too little to early-stop
        best = 300
    else:
        b = xgb.train(dict(PARAMS, seed=SEED), _dm(inner_tr, cols, margin), MAX_ROUNDS,
                      evals=[(_dm(inner_va, cols, margin), "va")],
                      early_stopping_rounds=EARLY_STOP, verbose_eval=False)
        best = max(b.best_iteration + 1, 1)
    m = xgb.train(dict(PARAMS, seed=SEED), _dm(tr, cols, margin), best, verbose_eval=False)
    return m.predict(_dm(te, cols, margin)), best


def paired_bootstrap(y, p_a, p_b, n=10000, seed=SEED) -> tuple[float, float, float]:
    """CI on (log-loss A - log-loss B); positive means B is better."""
    eps = 1e-12
    la = -(y * np.log(np.clip(p_a, eps, 1)) + (1 - y) * np.log(np.clip(1 - p_a, eps, 1)))
    lb = -(y * np.log(np.clip(p_b, eps, 1)) + (1 - y) * np.log(np.clip(1 - p_b, eps, 1)))
    d = la - lb
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(d), size=(n, len(d)))
    boot = d[idx].mean(axis=1)
    return float(d.mean()), float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))


def selftest() -> None:
    """A null result is what a broken harness produces. Two checks before believing it.

    1. Zero boosting rounds must reproduce the market EXACTLY. If it does not, the
       base_margin is not wired up and every 'gain' above is measured off a wrong base.
    2. Planting the realised total as a feature must collapse the log-loss. If it does
       not, the trees cannot see their inputs and the null is an artefact.
    """
    d = build(load())
    have = d.mkt_close.notna() & d.mkt_open.notna()
    season = TEST_SEASONS[-1]
    te = d[(d.Season == season) & have]
    tr = d[(d.Date < te.Date.min()) & have]
    y = te.over25.values

    m = xgb.train(dict(PARAMS, seed=SEED), _dm(tr, FEATURES, "mkt_close"), 0)
    p0 = m.predict(_dm(te, FEATURES, "mkt_close"))
    err = float(np.abs(p0 - te.mkt_close.values).max())
    print(f"[1] base_margin wiring: 0 rounds vs market, max abs diff {err:.2e}"
          f"   {'PASS' if err < 1e-6 else 'FAIL'}")

    tr, te = tr.copy(), te.copy()
    tr["planted"], te["planted"] = tr.total.values, te.total.values
    p_plant, _ = tree_predict(tr, te, FEATURES + ["planted"], "mkt_close")
    ll_plant, ll_mkt = log_loss(y, p_plant), log_loss(y, te.mkt_close.values)
    print(f"[2] planted realised total: log-loss {ll_plant:.4f} vs market {ll_mkt:.4f}"
          f"   {'PASS' if ll_plant < 0.25 else 'FAIL'}")


def main() -> None:
    d = build(load())
    have = d.mkt_close.notna() & d.mkt_open.notna()
    print(f"Usable rows {len(d)}  |  with open+close totals odds {int(have.sum())}"
          f"  |  vault 2025/26 excluded at load")
    print(f"Feature set A: {len(FEATURES)} aggregates   B: {len(RAW_FEATURES)} raw per-team\n")

    rows, pooled = [], []
    for season in TEST_SEASONS:
        te = d[(d.Season == season) & have]
        tr = d[(d.Date < te.Date.min()) & d.mkt_close.notna() & d.mkt_open.notna()]
        if len(te) == 0 or len(tr) < 300:
            print(f"  {season}: insufficient training rows ({len(tr)}) - skipped")
            continue
        y = te.over25.values

        p_mkt, _ = fit_predict(tr, te, [], "mkt_close")             # the baseline to beat
        p_lin, _ = fit_predict(tr, te, FEATURES, "mkt_close")       # published linear result
        p_a, na = tree_predict(tr, te, FEATURES, "mkt_close")
        p_b, nb = tree_predict(tr, te, RAW_FEATURES, "mkt_close")
        p_bare, _ = tree_predict(tr, te, RAW_FEATURES, None)        # trees with no market

        rows.append({"season": season, "n": len(te), "actual": y.mean(),
                     "ll_close": log_loss(y, te.mkt_close.values),
                     "ll_mkt": log_loss(y, p_mkt), "ll_lin": log_loss(y, p_lin),
                     "ll_treeA": log_loss(y, p_a), "ll_treeB": log_loss(y, p_b),
                     "ll_bare": log_loss(y, p_bare), "rounds_A": na, "rounds_B": nb})
        pooled.append(pd.DataFrame({"y": y, "mkt": p_mkt, "lin": p_lin,
                                    "treeA": p_a, "treeB": p_b, "bare": p_bare}))

    r = pd.DataFrame(rows)
    print("=== Walk-forward log-loss (lower is better) ===")
    print(f"{'season':<9}{'n':>5}{'actual':>8}{'CLOSE':>9}{'mktcal':>9}{'mkt+lin':>9}"
          f"{'treeA':>9}{'treeB':>9}{'trees-only':>12}{'  A gain':>10}{'B gain':>9}")
    for _, x in r.iterrows():
        print(f"{x.season:<9}{x.n:>5.0f}{x.actual:>8.3f}{x.ll_close:>9.4f}{x.ll_mkt:>9.4f}"
              f"{x.ll_lin:>9.4f}{x.ll_treeA:>9.4f}{x.ll_treeB:>9.4f}{x.ll_bare:>12.4f}"
              f"{x.ll_mkt-x.ll_treeA:>+10.5f}{x.ll_mkt-x.ll_treeB:>+9.5f}")
    print(f"\nboosting rounds chosen by early stopping: A {list(r.rounds_A)}  B {list(r.rounds_B)}")

    P = pd.concat(pooled, ignore_index=True)
    ll = {k: log_loss(P.y, P[k]) for k in ("mkt", "lin", "treeA", "treeB", "bare")}
    print(f"\nPooled out-of-sample n={len(P)}")
    print(f"  market-only        {ll['mkt']:.5f}   <- the baseline")
    for k, label in (("lin", "market+linear   "), ("treeA", "market+treeA (agg)"),
                     ("treeB", "market+treeB (raw)"), ("bare", "trees only, no mkt")):
        gain = ll["mkt"] - ll[k]
        print(f"  {label} {ll[k]:.5f}   gain {gain:+.5f}"
              f"{'' if gain > 0 else '   (worse)'}")

    print()
    for k in ("treeA", "treeB"):
        mean, lo, hi = paired_bootstrap(P.y.values, P.mkt.values, P[k].values)
        lr = 2 * len(P) * (ll["mkt"] - ll[k])
        print(f"  {k}: mean per-row gain {mean:+.5f}  95% CI [{lo:+.5f}, {hi:+.5f}]"
              f"   LR chi2 p={chi2.sf(max(lr, 0), len(FEATURES if k=='treeA' else RAW_FEATURES)):.4f}")

    ok = {k: int((r[f"ll_{k}"] < r.ll_mkt).sum()) for k in ("treeA", "treeB")}
    print(f"\n  beat market-only in: treeA {ok['treeA']}/{len(r)} seasons,"
          f"  treeB {ok['treeB']}/{len(r)} seasons")
    win = any(ok[k] == len(r) and
              chi2.sf(max(2 * len(P) * (ll['mkt'] - ll[k]), 0),
                      len(FEATURES if k == 'treeA' else RAW_FEATURES)) < 0.05
              for k in ("treeA", "treeB"))
    print("\nVERDICT: " + ("a tree ensemble DOES find incremental signal"
                           if win else
                           "NO incremental signal - interactions are not the missing piece"))

    out = ROOT / "outputs/football/championship/_research"
    out.mkdir(parents=True, exist_ok=True)
    r.to_csv(out / "totals_tree_probe.csv", index=False)
    print(f"\nwrote {out/'totals_tree_probe.csv'}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true",
                    help="verify the harness can see signal before trusting a null")
    a = ap.parse_args()
    selftest() if a.selftest else main()
