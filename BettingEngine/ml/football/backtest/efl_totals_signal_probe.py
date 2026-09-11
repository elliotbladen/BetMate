#!/usr/bin/env python3
"""Go/no-go probe: is there ANY beatable O/U 2.5 signal in the Championship?

Question this answers, before anyone rebuilds a totals model:
  does a pre-match feature set carry information the closing line does not?

Design
  * Strictly pre-match features. Every rolling stat is computed over a team's OWN
    prior matches and shifted, so the match being predicted never sees itself.
  * Walk-forward by season: train only on seasons strictly before the test season.
  * Two baselines: the de-vigged CLOSING line (the thing to beat) and the OPENING
    line (what you could actually have bet into).
  * Three models: features only, market only (a pure recalibration of the market),
    and market + features (the incremental-information test that matters).
  * 2025/26 is the sealed vault and is never touched here.

Verdict rule: features add value only if `market + features` beats `market only`
out-of-sample on log-loss, consistently across test seasons -- not once.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import chi2
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

MATCHES = ROOT / "ml/football/data/championship/matches/championship_matches.csv"
BACKTEST = ROOT / "ml/football/data/championship/clv/backtest_results.csv"
VAULT = "2025/26"
TEST_SEASONS = ["2021/22", "2022/23", "2023/24", "2024/25"]
WINDOW, MIN_PRIOR = 10, 5

# per-team per-match quantities that get rolled forward
TEAM_STATS = ["gf", "ga", "sf", "sa", "stf", "sta", "cf", "ca", "match_total"]


def load() -> pd.DataFrame:
    df = pd.read_csv(MATCHES, low_memory=False, parse_dates=["Date"])
    df = df[df.Season != VAULT]
    df = df[df.FTR.isin(["H", "D", "A"])].sort_values("Date").reset_index(drop=True)
    df["match_id"] = np.arange(len(df))
    df["total"] = df.FTHG + df.FTAG
    df["over25"] = (df.total > 2.5).astype(int)
    # de-vigged market probabilities (Pinnacle is the only totals source pre-2026/27)
    for tag, o, u in (("open", "P>2.5", "P<2.5"), ("close", "PC>2.5", "PC<2.5")):
        io, iu = 1 / df[o], 1 / df[u]
        df[f"mkt_{tag}"] = io / (io + iu)
    return df


def team_long(df: pd.DataFrame) -> pd.DataFrame:
    """One row per (match, team) carrying that team's own match quantities."""
    home = pd.DataFrame({
        "match_id": df.match_id, "Date": df.Date, "team": df.HomeTeam, "side": "home",
        "gf": df.FTHG, "ga": df.FTAG, "sf": df.HS, "sa": df.AS,
        "stf": df.HST, "sta": df.AST, "cf": df.HC, "ca": df.AC,
        "match_total": df.total})
    away = pd.DataFrame({
        "match_id": df.match_id, "Date": df.Date, "team": df.AwayTeam, "side": "away",
        "gf": df.FTAG, "ga": df.FTHG, "sf": df.AS, "sa": df.HS,
        "stf": df.AST, "sta": df.HST, "cf": df.AC, "ca": df.HC,
        "match_total": df.total})
    return pd.concat([home, away], ignore_index=True).sort_values(["team", "Date"])


def rolling_features(df: pd.DataFrame) -> pd.DataFrame:
    long = team_long(df)
    g = long.groupby("team", sort=False)
    for s in TEAM_STATS:
        # shift(1) first: the current match must not be in its own feature
        long[f"r_{s}"] = g[s].transform(
            lambda x: x.shift(1).rolling(WINDOW, min_periods=MIN_PRIOR).mean())
    long["n_prior"] = g.cumcount()
    long["rest"] = g["Date"].transform(lambda x: x.diff().dt.days).clip(upper=21)

    keep = ["match_id", "side", "n_prior", "rest"] + [f"r_{s}" for s in TEAM_STATS]
    wide = long[keep].pivot(index="match_id", columns="side")
    wide.columns = [f"{side}_{col}" for col, side in wide.columns]
    out = df.set_index("match_id").join(wide)

    # referee goals/game from that referee's PRIOR matches only
    out = out.sort_values("Date")
    ref = out.groupby("Referee", sort=False)["total"]
    out["ref_goals"] = ref.transform(lambda x: x.shift(1).expanding().mean())
    return out.reset_index()


FEATURES = [
    "exp_goals_sum", "exp_shots_sum", "exp_sot_sum", "exp_corners_sum",
    "recent_total_sum", "rest_min", "ref_goals",
]


def build(df: pd.DataFrame) -> pd.DataFrame:
    d = rolling_features(df)
    # symmetric "how many goals should this fixture produce" style aggregates
    d["exp_goals_sum"] = d.home_r_gf + d.home_r_ga + d.away_r_gf + d.away_r_ga
    d["exp_shots_sum"] = d.home_r_sf + d.home_r_sa + d.away_r_sf + d.away_r_sa
    d["exp_sot_sum"] = d.home_r_stf + d.home_r_sta + d.away_r_stf + d.away_r_sta
    d["exp_corners_sum"] = d.home_r_cf + d.home_r_ca + d.away_r_cf + d.away_r_ca
    d["recent_total_sum"] = d.home_r_match_total + d.away_r_match_total
    d["rest_min"] = d[["home_rest", "away_rest"]].min(axis=1)
    ok = (d.home_n_prior >= MIN_PRIOR) & (d.away_n_prior >= MIN_PRIOR)
    return d[ok & d[FEATURES].notna().all(axis=1)].copy()


def logit(p):
    p = np.clip(np.asarray(p, dtype=float), 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def fit_predict(tr, te, cols, market: str | None):
    def design(f):
        parts = []
        if market:
            parts.append(logit(f[market]).reshape(-1, 1))
        if cols:
            parts.append(f[cols].values)
        return np.hstack(parts)
    mu = tr[cols].mean() if cols else None
    sd = tr[cols].std().replace(0, 1) if cols else None
    def norm(f):
        f = f.copy()
        if cols:
            f[cols] = (f[cols] - mu) / sd
        return f
    m = LogisticRegression(penalty="l2", C=1.0, max_iter=5000)
    m.fit(design(norm(tr)), tr.over25.values)
    return m.predict_proba(design(norm(te)))[:, 1], m


def main() -> None:
    raw = load()
    d = build(raw)
    print(f"Usable rows after burn-in: {len(d)}  ({d.Season.min()} - {d.Season.max()})")
    have_odds = d.mkt_close.notna() & d.mkt_open.notna()
    print(f"  ... with both opening and closing totals odds: {int(have_odds.sum())}")

    prod = pd.read_csv(BACKTEST)
    prod["Date"] = pd.to_datetime(prod.date)
    prod_key = prod.set_index([prod.Date, prod.home, prod.away]).model_over25

    rows, pooled = [], []
    for season in TEST_SEASONS:
        te = d[(d.Season == season) & have_odds]
        tr_feat = d[d.Date < te.Date.min()]                       # all history for features
        tr_mkt = tr_feat[tr_feat.mkt_close.notna() & tr_feat.mkt_open.notna()]
        if len(te) == 0 or len(tr_mkt) < 300:
            print(f"  {season}: insufficient training rows ({len(tr_mkt)}) - skipped")
            continue
        y = te.over25.values

        p_feat, _ = fit_predict(tr_feat, te, FEATURES, None)
        p_mkt, _ = fit_predict(tr_mkt, te, [], "mkt_close")
        p_both, _ = fit_predict(tr_mkt, te, FEATURES, "mkt_close")

        # production D-C + isotonic, where the backtest file covers this match
        key = pd.MultiIndex.from_arrays([te.Date, te.HomeTeam, te.AwayTeam])
        p_prod = pd.Series(1.0 / prod_key.reindex(key).values, index=te.index)

        entry = {"season": season, "n": len(te), "train_mkt": len(tr_mkt),
                 "train_feat": len(tr_feat),
                 "actual_over": y.mean(),
                 "ll_close": log_loss(y, te.mkt_close.values),
                 "ll_open": log_loss(y, te.mkt_open.values),
                 "ll_feat": log_loss(y, p_feat),
                 "ll_mkt": log_loss(y, p_mkt),
                 "ll_both": log_loss(y, p_both),
                 "br_close": brier_score_loss(y, te.mkt_close.values),
                 "br_both": brier_score_loss(y, p_both),
                 "ll_prod": (log_loss(y[p_prod.notna().values], p_prod.dropna().values)
                             if p_prod.notna().sum() > 20 else np.nan),
                 "prod_n": int(p_prod.notna().sum())}
        rows.append(entry)
        pooled.append(pd.DataFrame({"y": y, "mkt": p_mkt, "both": p_both,
                                    "close": te.mkt_close.values}))

    r = pd.DataFrame(rows)
    print("\n=== Walk-forward, log-loss (lower is better) ===")
    print(f"{'season':<9}{'n':>5}{'actual':>8}{'CLOSE':>9}{'open':>8}{'feats':>8}"
          f"{'mktcal':>8}{'mkt+ft':>8}{'prod D-C':>10}{'  ft adds?':>11}")
    for _, x in r.iterrows():
        gain = x.ll_mkt - x.ll_both
        print(f"{x.season:<9}{x.n:>5.0f}{x.actual_over:>8.3f}{x.ll_close:>9.4f}{x.ll_open:>8.4f}"
              f"{x.ll_feat:>8.4f}{x.ll_mkt:>8.4f}{x.ll_both:>8.4f}"
              f"{x.ll_prod:>10.4f}{gain:>+11.5f}")

    P = pd.concat(pooled, ignore_index=True)
    ll_mkt, ll_both = log_loss(P.y, P.mkt), log_loss(P.y, P.both)
    lr = 2 * len(P) * (ll_mkt - ll_both)
    print(f"\nPooled out-of-sample n={len(P)}")
    print(f"  market-only   log-loss {ll_mkt:.5f}")
    print(f"  market+feats  log-loss {ll_both:.5f}    gain {ll_mkt-ll_both:+.5f}")
    print(f"  LR chi2({len(FEATURES)}) = {max(lr,0):.2f}, p = {chi2.sf(max(lr,0), len(FEATURES)):.4f}")
    print(f"  closing line  log-loss {log_loss(P.y, P['close']):.5f}  <- the bar")

    seasons_better = int((r.ll_both < r.ll_mkt).sum())
    print(f"\n  features improved on market-only in {seasons_better}/{len(r)} test seasons")
    print("\nVERDICT: " + (
        "features carry incremental signal - worth building a totals model"
        if seasons_better == len(r) and chi2.sf(max(lr, 0), len(FEATURES)) < 0.05 else
        "NO reliable incremental signal over the closing line"))
    out = ROOT / "outputs/football/championship/_research"
    out.mkdir(parents=True, exist_ok=True)
    r.to_csv(out / "totals_signal_probe.csv", index=False)
    print(f"\nwrote {out/'totals_signal_probe.csv'}")


if __name__ == "__main__":
    main()
