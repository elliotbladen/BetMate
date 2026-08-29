#!/usr/bin/env python3
"""Compare Championship GW1 base engine vs player-shadow-adjusted prices.

Reads GW1 match feeds from cache, builds position-grouped rolling features
from prior seasons, applies the trained ridge model, and prints a side-by-side
comparison with actual results.
"""
from __future__ import annotations

import contextlib
import io
import json
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from scipy.stats import poisson

from ml.football.price_match import price_match
from ml.football.player_layer.train_starter_shadow import (
    ALIASES, ROLLING_STATS, ROLLING_WINDOW, POSITION_GROUPS,
)
from ml.football.player_layer.backfill_espn_player_stats import (
    parse_match, POSITION_MAP,
)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "ml" / "football" / "data" / "championship" / "player_layer"
FEEDS = DATA / "match_feeds"
MODEL_PATH = DATA / "player_shadow.joblib"
OUT = ROOT / "outputs" / "football" / "championship"

# Frozen injuries from the existing GW1 pricing
INJURIES = {
    "Blackburn": ["DM", "AM"],
    "Bristol City": ["CM", "CB", "CB", "AM"], "Millwall": ["GK"],
    "Middlesbrough": ["CM"], "Lincoln": ["ST", "CB"],
    "Norwich": ["ST", "CM", "CM", "AM"], "West Brom": ["ST"],
    "Portsmouth": ["CB", "CB", "CM"], "QPR": ["CB", "CB", "CB", "ST"],
    "Stoke": ["CM", "CB", "CB"],
    "Sheffield United": ["CB"], "Birmingham": ["CB", "CB", "CM"],
}


def load_prior_rolling(season_years: list[int]) -> pd.DataFrame:
    """Load player stats from prior seasons (all leagues), compute final rolling values."""
    frames = []
    for year in season_years:
        # Championship data
        path = DATA / f"player_match_stats_espn_{year}.csv"
        if path.exists():
            frames.append(pd.read_csv(path))
        # Cross-league data (EPL, League One) for promoted/relegated players
        for league in ["epl", "league1"]:
            path = DATA / f"player_match_stats_espn_{league}_{year}.csv"
            if path.exists():
                frames.append(pd.read_csv(path))
    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True)
    df["date"] = pd.to_datetime(df.kickoff, utc=True).dt.strftime("%Y-%m-%d")
    df = df.sort_values(["player_id", "date"])

    for stat in ROLLING_STATS:
        df[f"{stat}_p90"] = np.where(df.minutes > 0, df[stat] / df.minutes * 90, 0.0)

    rolling_cols = [f"{s}_p90" for s in ROLLING_STATS]
    for col in rolling_cols:
        df[f"roll_{col}"] = (
            df.groupby("player_id")[col]
            .transform(lambda x: x.rolling(ROLLING_WINDOW, min_periods=1).mean())
        )
    df["roll_minutes"] = (
        df.groupby("player_id")["minutes"]
        .transform(lambda x: x.rolling(ROLLING_WINDOW, min_periods=1).mean())
    )
    latest = df.sort_values("date").groupby("player_id").last().reset_index()
    return latest


def build_match_features(match_payload: dict, event_id: str,
                         carry_forward: pd.DataFrame,
                         feat_cols: list[str]) -> dict | None:
    """Build position-grouped features for one match from its feed."""
    rows = parse_match(event_id, match_payload)
    if not rows:
        return None

    starters = [r for r in rows if r["starter"]]
    if len(starters) != 22:
        return None

    roll_cols = [f"roll_{s}_p90" for s in ROLLING_STATS] + ["roll_minutes"]
    feature_row = {col: 0.0 for col in feat_cols}

    matched = 0
    for player in starters:
        pid = str(player["player_id"])
        side = player["side"]
        pg = player["position_group"]
        if pg == "SUB":
            continue

        player_carry = carry_forward[carry_forward.player_id.astype(str).eq(pid)]
        if len(player_carry) == 0:
            continue
        matched += 1

        pc = player_carry.iloc[0]
        for col in roll_cols:
            key = f"{side}_{pg}_{col}"
            if key in feature_row:
                feature_row[key] += float(pc.get(col, 0) or 0)
        count_key = f"{side}_{pg}_count"
        if count_key in feature_row:
            feature_row[count_key] += 1

    return feature_row


def poisson_1x2(lam: float, mu: float) -> tuple[float, float, float]:
    """Compute 1X2 probabilities from Poisson lambdas."""
    max_g = 8
    h_probs = poisson.pmf(range(max_g + 1), max(lam, 0.01))
    a_probs = poisson.pmf(range(max_g + 1), max(mu, 0.01))
    matrix = np.outer(h_probs, a_probs)
    p_h = float(np.sum(np.tril(matrix, -1)))
    p_d = float(np.sum(np.diag(matrix)))
    p_a = float(np.sum(np.triu(matrix, 1)))
    t = p_h + p_d + p_a
    return p_h / t, p_d / t, p_a / t


def main() -> None:
    if not MODEL_PATH.exists():
        print("No trained model. Run: python -m ml.football.player_layer.train_starter_shadow")
        return

    model_data = joblib.load(MODEL_PATH)
    ridge = model_data["model"]
    feat_cols = model_data["feature_cols"]
    cap = model_data["cap"]

    print("Loading prior-season rolling stats...")
    carry = load_prior_rolling([2023, 2024, 2025])
    print(f"  {len(carry)} players with carry-forward stats\n")

    # Find GW1 matches from cached feeds
    gw1_feeds = []
    for f in sorted(FEEDS.glob("*.json")):
        with open(f) as fh:
            data = json.load(fh)
        header = data.get("header", {}).get("competitions", [{}])[0]
        match_date = header.get("date", "")[:10]
        if "2026-08-14" <= match_date <= "2026-08-17":
            competitors = {c.get("homeAway"): c for c in header.get("competitors", [])}
            if "home" in competitors and "away" in competitors:
                gw1_feeds.append((f.stem, data, competitors))

    print(f"Championship 2026/27 GW1 — {len(gw1_feeds)} matches")
    print(f"Base engine vs player-shadow comparison\n")
    print(f"{'Match':35s} {'Score':>6s} | {'Base H':>6s} {'D':>5s} {'A':>5s} {'xG':>10s} | "
          f"{'Adj H':>6s} {'D':>5s} {'A':>5s} {'xG':>10s} | {'dH':>6s} {'dA':>6s}"
          )
    print("-" * 120)

    results = []
    total_base_ll = total_adj_ll = 0.0
    n_scored = 0

    for event_id, payload, competitors in gw1_feeds:
        home_raw = competitors["home"]["team"]["displayName"]
        away_raw = competitors["away"]["team"]["displayName"]
        home = ALIASES.get(home_raw, home_raw)
        away = ALIASES.get(away_raw, away_raw)
        actual_h = int(competitors["home"].get("score", 0))
        actual_a = int(competitors["away"].get("score", 0))

        # Base engine
        with contextlib.redirect_stdout(io.StringIO()):
            base = price_match(home, away, as_of=datetime(2026, 8, 14),
                               league="championship", matchweek=1,
                               injuries_home=INJURIES.get(home, []),
                               injuries_away=INJURIES.get(away, []))

        # Player shadow
        features = build_match_features(payload, event_id, carry, feat_cols)
        if features is not None:
            x = np.array([[features.get(c, 0.0) for c in feat_cols]])
            delta = np.clip(ridge.predict(x), -cap, cap)[0]
        else:
            delta = np.array([0.0, 0.0])

        adj_lam = base["lambda_home"] + delta[0]
        adj_mu = base["lambda_away"] + delta[1]

        base_ph, base_pd, base_pa = poisson_1x2(base["lambda_home"], base["lambda_away"])
        adj_ph, adj_pd, adj_pa = poisson_1x2(adj_lam, adj_mu)

        # Log loss for comparison
        if actual_h > actual_a:
            outcome_idx = 0
        elif actual_h == actual_a:
            outcome_idx = 1
        else:
            outcome_idx = 2
        base_probs = [base_ph, base_pd, base_pa]
        adj_probs = [adj_ph, adj_pd, adj_pa]
        total_base_ll += -np.log(max(base_probs[outcome_idx], 1e-12))
        total_adj_ll += -np.log(max(adj_probs[outcome_idx], 1e-12))
        n_scored += 1

        match_str = f"{home} vs {away}"
        score_str = f"{actual_h}-{actual_a}"
        print(f"{match_str:35s} {score_str:>6s} | "
              f"{1/base_ph:6.2f} {1/base_pd:5.2f} {1/base_pa:5.2f} "
              f"{base['lambda_home']:4.2f}-{base['lambda_away']:4.2f} | "
              f"{1/adj_ph:6.2f} {1/adj_pd:5.2f} {1/adj_pa:5.2f} "
              f"{adj_lam:4.2f}-{adj_mu:4.2f} | "
              f"{delta[0]:+.3f} {delta[1]:+.3f}")

        results.append({
            "home": home, "away": away,
            "actual_h": actual_h, "actual_a": actual_a,
            "base_lambda": round(base["lambda_home"], 4),
            "base_mu": round(base["lambda_away"], 4),
            "adj_lambda": round(float(adj_lam), 4),
            "adj_mu": round(float(adj_mu), 4),
            "delta_h": round(float(delta[0]), 4),
            "delta_a": round(float(delta[1]), 4),
            "base_fair_h": round(1/base_ph, 3),
            "base_fair_d": round(1/base_pd, 3),
            "base_fair_a": round(1/base_pa, 3),
            "adj_fair_h": round(1/adj_ph, 3),
            "adj_fair_d": round(1/adj_pd, 3),
            "adj_fair_a": round(1/adj_pa, 3),
        })

    if n_scored:
        print(f"\n{'Log loss (lower=better)':35s} Base: {total_base_ll/n_scored:.4f}  "
              f"Player-adjusted: {total_adj_ll/n_scored:.4f}  "
              f"Delta: {(total_base_ll-total_adj_ll)/n_scored:+.4f}")

    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "gw1_player_shadow_comparison.json"
    path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nSaved: {path}")


if __name__ == "__main__":
    main()
