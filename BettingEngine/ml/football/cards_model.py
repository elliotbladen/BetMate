"""Championship total-cards model (bookings market).

Predicts expected total cards (yellow + red count) per match and converts to
fair odds for over/under lines (2.5 / 3.5 / 4.5 / 5.5).

Structure: two Poisson GLMs (home cards, away cards). Features, all
expanding-window pre-match (leak-free), shrunk n/(n+k):
  ref_dev     referee's total-cards/gm deviation from expanding league mean
  taker_dev   that side's venue-specific cards/gm deviation (own discipline)
  drawer_dev  opponent's tendency to draw cards from the other side
Tail probabilities via negative binomial (dispersion fitted on train residuals).

Validation: walk-forward, test seasons 2021/22-2024/25, train = everything prior.
Baselines: (a) league mean only, (b) league + ref only.

Usage:
  python ml/football/cards_model.py                      # walk-forward backtest
  python ml/football/cards_model.py --price --home "Leeds" --away "Millwall" --ref "O Langford"
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import PoissonRegressor

ROOT = Path(__file__).parent
REFS_CSV = ROOT / "data" / "championship" / "refs" / "refs_matches.csv"

K_REF = 30       # shrinkage for referee tendency
K_TEAM = 15      # shrinkage for team tendencies (venue-specific, smaller n)
TEST_SEASONS = ["2021/22", "2022/23", "2023/24", "2024/25"]
LINES = [2.5, 3.5, 4.5, 5.5]
FEATS = ["ref_dev", "taker_dev", "drawer_dev"]


def _expanding_dev(df, group_col, val_col, league_col, k):
    """Shrunk deviation of a group's expanding mean from the expanding league mean."""
    g = df.groupby(group_col)[val_col]
    mean = g.transform(lambda s: s.expanding().mean().shift(1))
    n = df.groupby(group_col).cumcount()
    w = n / (n + k)
    return ((mean - df[league_col]) * w).fillna(0).values


def load_matches() -> pd.DataFrame:
    df = pd.read_csv(REFS_CSV, parse_dates=["Date"]).sort_values("Date").reset_index(drop=True)
    df["home_cards"] = df["HY"].fillna(0) + df["HR"].fillna(0)
    df["away_cards"] = df["AY"].fillna(0) + df["AR"].fillna(0)
    df["total_cards"] = df["home_cards"] + df["away_cards"]
    # League baselines are recency-weighted (EWM, halflife ~quarter season): card
    # rates regime-shift (COVID season 2.94/gm, 2021/22+ jumped to ~3.9/gm) and a
    # slow baseline under-prices every over. Ref/team devs are relative, so they
    # stay meaningful while the level adapts.
    HL = 150
    df["lg_total"] = df["total_cards"].ewm(halflife=HL).mean().shift(1)
    df["lg_home"] = df["home_cards"].ewm(halflife=HL).mean().shift(1)
    df["lg_away"] = df["away_cards"].ewm(halflife=HL).mean().shift(1)
    df["ref_dev"] = _expanding_dev(df, "Referee", "total_cards", "lg_total", K_REF)
    # venue-specific own-discipline (taker) and cards-drawn-from-opponent (drawer)
    df["h_taker_dev"] = _expanding_dev(df, "HomeTeam", "home_cards", "lg_home", K_TEAM)
    df["a_taker_dev"] = _expanding_dev(df, "AwayTeam", "away_cards", "lg_away", K_TEAM)
    df["h_drawer_dev"] = _expanding_dev(df, "HomeTeam", "away_cards", "lg_away", K_TEAM)
    df["a_drawer_dev"] = _expanding_dev(df, "AwayTeam", "home_cards", "lg_home", K_TEAM)
    return df.dropna(subset=["lg_total"])


def side_frames(df):
    """Per-side design matrices: (features, target, league_base)."""
    home = pd.DataFrame({
        "ref_dev": df["ref_dev"] / 2, "taker_dev": df["h_taker_dev"],
        "drawer_dev": df["a_drawer_dev"], "y": df["home_cards"], "base": df["lg_home"]})
    away = pd.DataFrame({
        "ref_dev": df["ref_dev"] / 2, "taker_dev": df["a_taker_dev"],
        "drawer_dev": df["h_drawer_dev"], "y": df["away_cards"], "base": df["lg_away"]})
    return home, away


def fit_side(frame) -> PoissonRegressor:
    m = PoissonRegressor(alpha=1e-4, max_iter=1000)
    X = frame[FEATS].values
    # offset via sample-weighted trick: model multiplicative deviation around base
    m.fit(X, frame["y"].values / frame["base"].values,
          sample_weight=frame["base"].values)
    return m

def predict_side(m, frame) -> np.ndarray:
    return m.predict(frame[FEATS].values) * frame["base"].values


def nb_over_prob(lam: float, alpha: float, line: float) -> float:
    """P(total cards > line) under negative binomial with mean lam, var lam + alpha*lam^2."""
    if alpha <= 1e-6:
        return float(1 - stats.poisson.cdf(int(line), lam))
    r = 1.0 / alpha
    p = r / (r + lam)
    return float(1 - stats.nbinom.cdf(int(line), r, p))


def fit_dispersion(y: np.ndarray, lam: np.ndarray) -> float:
    """Method-of-moments NB dispersion alpha (>=0)."""
    return float(max(np.mean(((y - lam) ** 2 - lam) / lam**2), 0.0))


def walk_forward(df: pd.DataFrame) -> pd.DataFrame:
    out = []
    for season in TEST_SEASONS:
        tr = df[df["Season"] < season]
        te = df[df["Season"] == season].copy()
        h_tr, a_tr = side_frames(tr)
        h_te, a_te = side_frames(te)
        mh, ma = fit_side(h_tr), fit_side(a_tr)
        te["lam"] = predict_side(mh, h_te) + predict_side(ma, a_te)
        # baselines get the same recency-tracked league level, so differences
        # isolate ref/team feature skill rather than level-tracking
        te["lam_naive"] = te["lg_total"]
        te["lam_ref"] = te["lg_total"] + te["ref_dev"]
        # dispersion from train residuals of the full model
        lam_tr = predict_side(mh, h_tr) + predict_side(ma, a_tr)
        te["alpha"] = fit_dispersion(tr["total_cards"].values, lam_tr)
        out.append(te)
    return pd.concat(out)


def evaluate(wf: pd.DataFrame):
    print(f"=== WALK-FORWARD BACKTEST ({TEST_SEASONS[0]}–{TEST_SEASONS[-1]}, "
          f"n={len(wf)}) ===\n")
    print("Expected-cards MAE (lower = better):")
    for name, col in [("naive league avg", "lam_naive"), ("+ ref only", "lam_ref"),
                      ("full model (ref+teams)", "lam")]:
        mae = (wf["total_cards"] - wf[col]).abs().mean()
        print(f"  {name:<24} {mae:.3f}")

    print("\nOver/Under probability quality — Brier score (lower = better):")
    print(f"  {'line':<6} {'naive':>8} {'+ref':>8} {'full':>8}   base rate")
    for line in LINES:
        y = (wf["total_cards"] > line).astype(int)
        rows = []
        for col in ["lam_naive", "lam_ref", "lam"]:
            p = np.array([nb_over_prob(l, a, line)
                          for l, a in zip(wf[col], wf["alpha"])])
            rows.append(((p - y) ** 2).mean())
        print(f"  O{line:<5} {rows[0]:>8.4f} {rows[1]:>8.4f} {rows[2]:>8.4f}   {y.mean():.1%}")

    # calibration of the full model at 3.5 and 4.5
    for line in [3.5, 4.5]:
        y = (wf["total_cards"] > line).astype(int)
        p = np.array([nb_over_prob(l, a, line) for l, a in zip(wf["lam"], wf["alpha"])])
        print(f"\nCalibration, Over {line} (full model):")
        bins = pd.qcut(p, 5, duplicates="drop")
        tab = pd.DataFrame({"pred": p, "actual": y}).groupby(bins, observed=True).agg(
            n=("actual", "size"), predicted=("pred", "mean"), actual=("actual", "mean"))
        print(tab.round(3).to_string())

    print("\nSample fair odds from the last test season (5 most extreme matches):")
    last = wf[wf["Season"] == TEST_SEASONS[-1]].copy()
    ext = last.reindex((last["lam"] - last["lam"].mean()).abs().sort_values().index[-5:])
    for _, r in ext.iterrows():
        probs = {L: nb_over_prob(r["lam"], r["alpha"], L) for L in LINES}
        odds = " | ".join(f"O{L}: {1/p:.2f}/{1/(1-p):.2f}" for L, p in probs.items())
        print(f"  {r['Date'].date()} {r['HomeTeam']} v {r['AwayTeam']} (ref {r['Referee']}, "
              f"exp cards {r['lam']:.2f}, actual {int(r['total_cards'])})")
        print(f"    {odds}")


def price_match(home: str, away: str, ref: str):
    df = load_matches()
    h_all, a_all = side_frames(df)
    mh, ma = fit_side(h_all), fit_side(a_all)
    lam_tr = predict_side(mh, h_all) + predict_side(ma, a_all)
    alpha = fit_dispersion(df["total_cards"].values, lam_tr)

    def latest_dev(col_group, col_val, col_lg, k, key):
        sub = df[df[col_group] == key]
        if sub.empty:
            return 0.0, 0
        n = len(sub)
        dev = sub[col_val].mean() - df[col_lg].iloc[-1]
        return dev * n / (n + k), n

    ref_dev, n_ref = latest_dev("Referee", "total_cards", "lg_total", K_REF, ref)
    ht, n_h = latest_dev("HomeTeam", "home_cards", "lg_home", K_TEAM, home)
    at, n_a = latest_dev("AwayTeam", "away_cards", "lg_away", K_TEAM, away)
    hd, _ = latest_dev("HomeTeam", "away_cards", "lg_away", K_TEAM, home)
    ad, _ = latest_dev("AwayTeam", "home_cards", "lg_home", K_TEAM, away)

    hrow = pd.DataFrame({"ref_dev": [ref_dev / 2], "taker_dev": [ht], "drawer_dev": [ad],
                         "base": [df["lg_home"].iloc[-1]]})
    arow = pd.DataFrame({"ref_dev": [ref_dev / 2], "taker_dev": [at], "drawer_dev": [hd],
                         "base": [df["lg_away"].iloc[-1]]})
    lam = (predict_side(mh, hrow) + predict_side(ma, arow)).item()
    print(f"{home} v {away} | ref {ref} (n={n_ref}, dev {ref_dev:+.2f})")
    print(f"  home discipline n={n_h}, away discipline n={n_a}")
    print(f"  expected total cards: {lam:.2f}  (league avg {df['lg_total'].iloc[-1]:.2f})")
    print(f"  {'line':<6} {'P(over)':>8} {'fair over':>10} {'fair under':>11}")
    for L in LINES:
        p = nb_over_prob(lam, alpha, L)
        print(f"  O{L:<5} {p:>8.1%} {1/p:>10.2f} {1/(1-p):>11.2f}")
    print("\n⚠ data ends 2024/25 (vault rule) — refresh before live use; add ~6-10% "
          "market vig on top of fair odds before calling anything value.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--price", action="store_true")
    ap.add_argument("--home"), ap.add_argument("--away"), ap.add_argument("--ref")
    args = ap.parse_args()
    if args.price:
        price_match(args.home, args.away, args.ref)
    else:
        df = load_matches()
        print(f"loaded {len(df)} matches | total cards mean "
              f"{df['total_cards'].mean():.2f} var {df['total_cards'].var():.2f} "
              f"(overdispersion {'yes' if df['total_cards'].var()/df['total_cards'].mean()>1.1 else 'mild'})\n")
        evaluate(walk_forward(df))


if __name__ == "__main__":
    main()
