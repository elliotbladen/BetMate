#!/usr/bin/env python3
"""
BettingEngine/scripts/halfTime_price_nrl.py

NRL half-time pricing model.

Takes:
  - Half-time stats JSON (from scrapers/nrl_halftime_stats.py)
  - Pre-game pricing row (from results/r{nn}_pricing_2026.csv)

Produces:
  - Updated H2H odds, handicap line, and totals line for the second half
  - Written to data/nrl/halfTime/R{nn}/YYYY-MM-DD_{game}_pricing.json

The model applies a Bayesian update:
  - Pre-game estimates are the prior (team strength, expected margin, expected total)
  - Half-time score state is the evidence
  - Regression factor controls how much the prior survives vs the HT evidence

Usage:
    python scripts/halfTime_price_nrl.py --file path/to/halftime_stats.json
    python scripts/halfTime_price_nrl.py --round 14 --home Cronulla --away Manly
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import random
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

try:
    from scripts.nrl_ht_totals_v3 import estimate_totals
    from scripts.nrl_ht_margin_v3 import estimate_margin
except ModuleNotFoundError:  # direct execution from scripts/
    from nrl_ht_totals_v3 import estimate_totals
    from nrl_ht_margin_v3 import estimate_margin

# ── Paths ─────────────────────────────────────────────────────────────────────
ENGINE_ROOT  = Path(__file__).resolve().parent.parent
BETMATE_ROOT = Path(os.environ.get("BETMATE_ROOT", ENGINE_ROOT.parent))
RESULTS_DIR  = ENGINE_ROOT / "results"
HALFTIME_DIR = BETMATE_ROOT / "data" / "nrl" / "halfTime"

# ── Model constants ────────────────────────────────────────────────────────────
# How much the pre-game prior survives at half time (1.0 = ignore HT score, 0.0 = fully trust HT)
# Swartz et al. (2022, Annals of Applied Statistics) — NRL in-game win probability paper:
# at halftime (50% elapsed), pre-game prior retains ~50-60% weight. Using 0.55 (55% pre-game).
# Previously 0.50 — nudged up slightly as pre-game model is strong (63% accuracy, 13.7pt MAE).
REGRESSION_FACTOR = 0.55

# Average NRL second-half total (points scored by both teams in 40 min)
# Research: avg total/game 2022-2025 = 43-47 pts. H2 scores slightly more than H1 due to
# garbage-time scoring. H1 avg ~21-22 pts, H2 avg ~23-25 pts (47/53 split approx).
# Using 23.5 as H2 baseline (slightly above H1 average of 21-22).
AVG_SECOND_HALF_TOTAL = 23.5

# Correction factors — how first-half total predicts second-half total
# H2 averages slightly more than H1 due to garbage-time scoring in close-to-decided games.
# Regression to mean applies: high H1 → lower H2, low H1 → higher H2.
SECOND_HALF_TOTAL_BY_FIRST = {
    # first_half_total → expected second_half_total
    (0,  10): 26.0,   # very low H1 → strong regression up
    (11, 16): 24.5,   # below average
    (17, 22): 23.5,   # average range
    (23, 28): 22.0,   # above average → regression down
    (29, 99): 20.0,   # high scoring H1 → meaningful regression
}

# NRL average conversion rate (league average kicker)
# Research: Super League study 76.7% (768/1001 tries converted, PMC11581272).
# NRL inferred 73-76% from scoring structure. Specialist kickers 78-85%, non-specialists 60-70%.
# Using 0.75 — well supported across multiple sources.
BASELINE_CONVERSION_RATE = 0.75

# Points per extra error vs average
# Research: teams with fewer errors win ~77.5% of games (Rugby League Eye Test 2025).
# Net completion rate vs margin R²=0.23 (Maroon Observer). Tries from errors ~25% of all tries.
# At ~4.5 tries/game total (~45pts), 25% from errors = ~11pts/game from error forcing.
# With ~8 errors/team/game, each error = ~11/8 = ~1.4 pts expected value swing.
# Raised from 1.2 → 1.4 (research supports higher end of 1.0-1.5 range).
POINTS_PER_ERROR_DIFF = 1.4

# Error adjustment regression factor — dampens the raw error adj before applying to margin.
# The 1.4 pts/error figure is a full-game correlation, not a direct causal scoring equation.
# H2 error rates also regress to mean — a 4-error H1 gap won't persist at the same rate.
# Applying 45% regression keeps the directional signal without overriding the Bayesian prior.
ERROR_REGRESSION_FACTOR = 0.45

# Set restart points value — research-backed
# Rugby League Eye Test (May 2026): single restart = 1.24 expected pts vs 0.52 for normal set.
# Net incremental value = 0.72 pts per restart received.
# H1/H2 split: 61% of all restarts occur in H1, only 39% in H2 (structural, not random).
# So H2 restart rate ≈ 39/61 = 64% of H1 rate. Deflation factor = 1 - 0.64 = 0.36 (not 0.80).
# Updated: previously used 80% deflation which was too aggressive.
RESTART_NET_PTS = 0.72         # incremental pts per restart received vs normal set
RESTART_H2_DEFLATION = 0.36   # how much of H1 restart advantage disappears in H2

# Conversion adjustment cap — research shows each kick is near-independent (no regression).
# Capping the conversion adjustment to avoid noise from small samples (1-2 kicks).
# Max adjustment = 2 pts (1 missed conversion) — beyond that it's noise.
CONVERSION_ADJ_CAP = 2.0

# ── Stats-adjusted regression constants (v2, 2026-08-08) ─────────────────────
# Research basis (754 NRL games, 2022-2026):
#   - NRL H2 is 2.5x more volatile than AFL relative to game size (37.7% vs 15.4%)
#   - HT margin → FT margin R=0.371 (AFL R=0.667) — HT score is a weak predictor
#   - Regression factor sensitivity is 6x FLATTER than AFL (±0.10 → 0.09 MAE vs 0.56)
#   - 34% comeback rate (AFL 26%) — leads are less reliable
#   - Optimal regression factor is 0.50 (current 0.55 is close)
#
# Process stats that persist H1→H2 in NRL:
#   - Errors: #1 NRL predictor, 77.5% win rate for fewer-error team, ~25% of tries
#     from forced errors. Reflects discipline/quality, partially persists.
#   - Inside 20 possessions: territorial dominance (NRL equivalent of AFL I50s).
#     0.8 pts expected value per entry (Rugby League Eye Test).
#   - Set restarts received: discipline/referee pattern signal. 0.72 pts net per restart.
#
# Cap set at 5% (not AFL's 7%) because:
#   1. Regression factor sensitivity is 6x flatter — adjustments barely move MAE
#   2. NRL H2 is structurally noisier (17.5 std on 46-pt game)
#   3. Errors/restarts already used as additive adjustments — lower cap avoids double-count
#   4. No empirical NRL process stat persistence data to validate larger cap
#   5. Proportionally equivalent: NRL 5% on 0.55 ≈ AFL 7% on 0.45 (both ~9% of base)

# Weights for stats-implied margin (derived from existing NRL research in this model)
STATS_IMPLIED_ERROR_WEIGHT = 1.4       # matches POINTS_PER_ERROR_DIFF — strongest NRL stat
STATS_IMPLIED_IN20_WEIGHT = 0.8        # matches ETxP value — territorial dominance
STATS_IMPLIED_RESTART_WEIGHT = 0.7     # close to RESTART_NET_PTS — discipline signal

# How much the regression factor can shift based on stats evidence
# 5% for NRL (see rationale above). Range: 0.50–0.60 (clamped 0.30–0.70).
REGRESSION_ADJUSTMENT_MAX = 0.05

# Minimum stats-implied margin to trigger dynamic regression (noise filter)
# NRL scoring is lower than AFL, so threshold is lower (AFL uses 2.0)
STATS_IMPLIED_THRESHOLD = 1.5

# Signal strength scaling — full signal at 6+ pts implied margin
# (roughly: 3 fewer errors + 2 more in-20s = 3×1.4 + 2×0.8 = 5.8)
STATS_IMPLIED_SCALE = 6.0

# ── In-game injury impact (NRL positions → T5-style adjustment) ──────────────
# NRL match centre positions mapped to impact tiers. Spine players (fullback,
# halfback, five-eighth, hooker) are the most impactful losses mid-game.
# Second row / lock are key forwards. Props rotate heavily so mid-game loss
# is less damaging. Values are (handicap_adj, totals_adj) per player out.
# Quality assumed "good" — if they start in the 1-13, they're at least that.
NRL_INGAME_IMPACT = {
    "Fullback":     (-3.0, -1.5),
    "Halfback":     (-2.5, -1.0),
    "Five-Eighth":  (-2.5, -1.0),
    "Hooker":       (-2.0, -1.0),
    "Centre":       (-1.5, -0.5),
    "Winger":       (-1.0, -0.5),
    "Lock":         (-1.5, -0.5),
    "2nd Row":      (-1.5, -0.5),
    "Prop":         (-1.0, -0.5),
    "Interchange":  (-0.5,  0.0),
}
INGAME_INJURY_CAP = 5.0

# Simulation runs for win probability calculation
SIM_RUNS = 20_000

RANDOM_SEED = 42


# ── Pre-game pricing loader ───────────────────────────────────────────────────

def _round_num_from_path(p: Path) -> int:
    """Extract round number from filenames like r15_pricing_2026.csv."""
    import re
    m = re.match(r"r(\d+)", p.stem)
    return int(m.group(1)) if m else 0


def _latest_pricing_csv() -> Path | None:
    seen = set()
    candidates = []
    for p in (
        list(RESULTS_DIR.glob("r*_*pricing*_2026.csv")) +
        list(RESULTS_DIR.glob("r*_pricing_2026.csv"))
    ):
        if p not in seen:
            seen.add(p)
            candidates.append(p)
    candidates.sort(key=_round_num_from_path, reverse=True)
    return candidates[0] if candidates else None


def _safe_float(val, default: float = 0.0) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def load_pregame_row(home: str, away: str) -> dict | None:
    """Find the pre-game pricing row for a specific matchup."""
    csv_path = _latest_pricing_csv()
    if not csv_path:
        print("No NRL pricing CSV found.")
        return None

    home_l = home.lower()
    away_l = away.lower()

    with open(csv_path, newline="", encoding="cp1252", errors="replace") as f:
        for row in csv.DictReader(f):
            h = row.get("home_team", "").lower()
            a = row.get("away_team", "").lower()
            if (home_l in h or h in home_l) and (away_l in a or a in away_l):
                return row
            if (away_l in h or h in away_l) and (home_l in a or a in home_l):
                # Flipped — return but note it
                row["_flipped"] = True
                return row

    print(f"No pre-game row found for {home} vs {away} in {csv_path.name}")
    return None


# ── Second half total estimator ───────────────────────────────────────────────

def expected_second_half_total(first_half_total: int) -> float:
    """Estimate second-half total based on first-half actual (regression to mean)."""
    for (lo, hi), expected in SECOND_HALF_TOTAL_BY_FIRST.items():
        if lo <= first_half_total <= hi:
            return expected
    return AVG_SECOND_HALF_TOTAL


# ── Win probability via simulation ────────────────────────────────────────────

def simulate_win_prob(
    ht_margin: int,
    home_2h_mean: float,
    away_2h_mean: float,
    runs: int = SIM_RUNS,
) -> dict[str, float]:
    """
    Monte Carlo simulation of second-half scoring.
    Returns P(home_win), P(away_win), P(draw) based on final score.

    Scoring in each half modelled as Poisson process per 2-point scoring unit.
    NRL scores come in chunks of 2 (field goal), 4 (penalty goal), 6 (try + miss), 8 (converted try).
    Simplified: model each team's second-half score as Normal(mean, std) with std = sqrt(mean) * 1.4
    (overdispersed vs pure Poisson — NRL scoring is bursty).
    """
    rng = random.Random(RANDOM_SEED)
    home_wins = away_wins = draws = 0
    std_factor = 1.4  # overdispersion factor vs Poisson sqrt

    home_std = max(math.sqrt(home_2h_mean) * std_factor, 2.0)
    away_std = max(math.sqrt(away_2h_mean) * std_factor, 2.0)

    for _ in range(runs):
        # Sample second-half scores (floored at 0, rounded to nearest 2)
        h2 = max(0, round(rng.gauss(home_2h_mean, home_std) / 2) * 2)
        a2 = max(0, round(rng.gauss(away_2h_mean, away_std) / 2) * 2)
        final = ht_margin + h2 - a2
        if final > 0:
            home_wins += 1
        elif final < 0:
            away_wins += 1
        else:
            draws += 1

    return {
        "home_win": round(home_wins / runs, 4),
        "away_win": round(away_wins / runs, 4),
        "draw":     round(draws / runs, 4),
    }


def prob_to_odds(p: float) -> float:
    """Convert probability to decimal odds (no margin applied)."""
    if p <= 0:
        return 99.0
    return round(1.0 / p, 2)


# ── Core pricing function ─────────────────────────────────────────────────────

@dataclass
class HalfTimePricing:
    home_team: str
    away_team: str
    season: int
    round: int
    game_date: str
    priced_at: str

    # Input
    ht_home_score: int
    ht_away_score: int
    ht_margin: int                 # positive = home leading

    # Pre-game prior
    pregame_fair_hcap: float       # positive = home favoured
    pregame_fair_total: float
    pregame_home_prob: float

    # Second half estimates
    second_half_expected_total: float
    second_half_home_expected: float
    second_half_away_expected: float

    # Adjustments applied
    error_adjustment: float        # points added to expected margin
    conversion_adjustment: float   # points from missed conversion luck
    restart_adjustment: float      # removes first-half restart inflation

    # Stats-adjusted regression (v2)
    stats_implied_margin: float
    stats_regression_adj: float
    regression_factor_used: float

    # Output
    ht_expected_margin: float      # positive = home expected to win
    ht_expected_total: float
    ht_home_win_prob: float
    ht_away_win_prob: float
    ht_home_odds: float
    ht_away_odds: float
    ht_hcap_line: float            # from home perspective (negative = home giving points)
    ht_total_line: float

    # Active totals model audit trail
    totals_model_version: str
    totals_historical_h2_baseline: float
    totals_pregame_h2_prior: float
    totals_blended_h2_baseline: float
    totals_process_adjustment: float
    totals_fair_line: float
    totals_distribution_sample_size: int
    totals_feature_coverage: float
    totals_quality: str
    totals_adjustments: list[str]

    # Coherent H2H/handicap margin model audit trail
    margin_model_version: str
    margin_elapsed_game_fraction: float
    margin_expected_remaining_pregame: float
    margin_baseline: float
    margin_process_adjustment: float
    margin_median: float
    margin_distribution_sample_size: int
    margin_feature_coverage: float
    margin_quality: str
    margin_adjustments: list[str]

    # In-game injuries
    ingame_home_injuries: list[dict]
    ingame_away_injuries: list[dict]
    ingame_injury_hcap_adj: float
    ingame_injury_total_adj: float
    ingame_injury_sources: list[str]

    # Sin bins / send-offs
    sin_bins: list[dict]

    # Signal
    signal_strength: str           # "strong" | "moderate" | "weak" | "neutral"
    signal_direction: str          # "HOME" | "AWAY" | "NEUTRAL"
    signal_notes: list[str]


def price_halftime(stats: dict, pregame: dict | None) -> HalfTimePricing:
    """
    Main half-time pricing function.

    stats: HalfTimeStats dict (from nrl_halftime_stats.py)
    pregame: Pre-game pricing row dict (from BettingEngine pricing CSV)
    """
    home = stats["home_team"]
    away = stats["away_team"]
    ht_home = stats["home_ht_score"]
    ht_away = stats["away_ht_score"]
    ht_margin = ht_home - ht_away
    first_half_total = ht_home + ht_away

    # ── Pre-game prior ─────────────────────────────────────────────────────────
    if pregame:
        # fair_hcap_line uses betting convention: negative = home giving points = home winning
        # ht_margin uses natural convention: positive = home winning
        # Negate so both use the same sign convention in the Bayesian blend
        pg_hcap  = -_safe_float(pregame.get("fair_hcap_line", 0))
        pg_total = _safe_float(pregame.get("fair_total_line", 44.0))
        pg_h_odds = _safe_float(pregame.get("fair_home_odds", 2.0))
        pg_a_odds = _safe_float(pregame.get("fair_away_odds", 2.0))
        pg_home_prob = (1 / pg_h_odds) if pg_h_odds > 0 else 0.5
    else:
        # No pre-game data — use neutral priors
        pg_hcap = 0.0
        pg_total = 44.0
        pg_home_prob = 0.5
        print("WARNING: No pre-game pricing found. Using neutral priors.")

    # ── Extract process stats for stats-implied margin ──────────────────────────
    home_errors = _safe_float(stats.get("home_errors", 0))
    away_errors = _safe_float(stats.get("away_errors", 0))
    home_in20 = _safe_float(stats.get("home_inside_20_possessions", 0))
    away_in20 = _safe_float(stats.get("away_inside_20_possessions", 0))
    home_restarts = _safe_float(stats.get("home_set_restarts_received", 0))
    away_restarts = _safe_float(stats.get("away_set_restarts_received", 0))

    # ── Stats-implied margin (process stats only) ────────────────────────────
    # Estimates structural dominance from stats that persist H1→H2.
    # Positive = home is structurally dominant.
    error_diff = away_errors - home_errors   # positive = home fewer errors (good)
    in20_diff = home_in20 - away_in20        # positive = home more in-20 entries (good)
    restart_diff = home_restarts - away_restarts  # positive = home more restarts (good)

    stats_implied_margin = (
        error_diff   * STATS_IMPLIED_ERROR_WEIGHT +
        in20_diff    * STATS_IMPLIED_IN20_WEIGHT +
        restart_diff * STATS_IMPLIED_RESTART_WEIGHT
    )

    # ── Dynamic regression factor ────────────────────────────────────────────
    # Compare stats evidence vs pre-game prior direction.
    # If stats back the prior → trust the prior MORE (raise factor)
    # If stats oppose the prior → trust live evidence MORE (lower factor)
    regression = REGRESSION_FACTOR
    stats_regression_adj = 0.0

    have_process_stats = any([home_errors, away_errors, home_in20, away_in20,
                              home_restarts, away_restarts])

    if have_process_stats and abs(stats_implied_margin) >= STATS_IMPLIED_THRESHOLD:
        stats_backs_prior = (
            (stats_implied_margin > 0 and pg_hcap > 0) or
            (stats_implied_margin < 0 and pg_hcap < 0)
        )

        signal_strength = min(abs(stats_implied_margin) / STATS_IMPLIED_SCALE, 1.0)
        raw_adj = REGRESSION_ADJUSTMENT_MAX * signal_strength

        if stats_backs_prior:
            stats_regression_adj = raw_adj
        else:
            stats_regression_adj = -raw_adj

        regression = max(0.30, min(0.70, REGRESSION_FACTOR + stats_regression_adj))

    # ── Bayesian update: expected final margin ─────────────────────────────────
    # Weighted blend of HT evidence and pre-game prior
    expected_final_margin = (
        ht_margin * (1 - regression) +
        pg_hcap   * regression
    )
    # ── Error adjustment ───────────────────────────────────────────────────────
    error_adj = error_diff * POINTS_PER_ERROR_DIFF * ERROR_REGRESSION_FACTOR

    # ── Set restart inflation removal ──────────────────────────────────────────
    # H1 restarts inflate the home/away margin; only 64% of H1 restart frequency repeats in H2.
    # So 36% of H1 restart advantage (RESTART_H2_DEFLATION) won't carry forward — subtract it.
    # RESTART_NET_PTS = 0.72 pts net per restart (Rugby League Eye Test: 1.24 vs 0.52 normal set).
    restart_advantage = (home_restarts - away_restarts) * RESTART_NET_PTS * RESTART_H2_DEFLATION
    restart_adj = -restart_advantage  # subtract what was restart-inflated

    # ── Conversion luck adjustment ─────────────────────────────────────────────
    home_tries = _safe_float(stats.get("home_tries", 0))
    away_tries = _safe_float(stats.get("away_tries", 0))
    home_conv  = _safe_float(stats.get("home_conversions_made", 0))
    away_conv  = _safe_float(stats.get("away_conversions_made", 0))

    # Expected conversions at baseline rate
    home_expected_conv = home_tries * BASELINE_CONVERSION_RATE
    away_expected_conv = away_tries * BASELINE_CONVERSION_RATE

    # Points "owed" from missed conversions (2 pts each)
    home_conv_luck = (home_conv - home_expected_conv) * 2   # negative = missed, owed points
    away_conv_luck = (away_conv - away_expected_conv) * 2
    conversion_adj = away_conv_luck - home_conv_luck  # net adj in home team's favour
    conversion_adj = max(-CONVERSION_ADJ_CAP, min(CONVERSION_ADJ_CAP, conversion_adj))

    # ── In-game injury detection ──────────────────────────────────────────────
    # Layer 1: NRL API interchange events with injury keywords
    api_injuries = stats.get("ingame_injuries", [])
    # Layer 2: Manual overrides (user drops a JSON file mid-game)
    manual_injuries = stats.get("manual_injuries", [])

    # Merge, deduplicating by player name (manual overrides win if both exist)
    seen_names: set[str] = set()
    all_injuries: list[dict] = []
    for inj in manual_injuries:
        key = inj.get("name", "").lower()
        if key and key not in seen_names:
            seen_names.add(key)
            all_injuries.append(inj)
    for inj in api_injuries:
        key = inj.get("name", "").lower()
        if key and key not in seen_names:
            seen_names.add(key)
            all_injuries.append(inj)

    home_injuries = [inj for inj in all_injuries if inj.get("side") == "home"]
    away_injuries = [inj for inj in all_injuries if inj.get("side") == "away"]
    injury_sources = sorted(set(inj.get("source", "nrl_api") for inj in all_injuries)) if all_injuries else []

    home_inj_hcap = sum(NRL_INGAME_IMPACT.get(inj["position"], (-0.5, 0.0))[0] for inj in home_injuries)
    home_inj_tots = sum(NRL_INGAME_IMPACT.get(inj["position"], (-0.5, 0.0))[1] for inj in home_injuries)
    away_inj_hcap = sum(NRL_INGAME_IMPACT.get(inj["position"], (-0.5, 0.0))[0] for inj in away_injuries)
    away_inj_tots = sum(NRL_INGAME_IMPACT.get(inj["position"], (-0.5, 0.0))[1] for inj in away_injuries)

    # Home injuries hurt home (negative hcap), away injuries help home (positive hcap)
    ingame_injury_hcap = max(-INGAME_INJURY_CAP, min(INGAME_INJURY_CAP, home_inj_hcap - away_inj_hcap))
    ingame_injury_total = max(-INGAME_INJURY_CAP, min(INGAME_INJURY_CAP, home_inj_tots + away_inj_tots))

    # ── Sin bin / send-off detection ─────────────────────────────────────────
    sin_bins = stats.get("sin_bins", [])

    # ── Combined expected margin ───────────────────────────────────────────────
    total_adj = error_adj + restart_adj + conversion_adj
    # One final-margin distribution is the single source of truth for H2H and
    # handicap. The legacy component calculations above remain in output as
    # diagnostics during the forward comparison period.
    margin_model = estimate_margin(stats, pg_hcap)
    ht_expected_margin = margin_model.expected_final_margin + ingame_injury_hcap

    # ── Second half total estimate (v3) ───────────────────────────────────────
    totals_model = estimate_totals(stats, pg_total, ingame_injury_total)
    sh_total = totals_model.expected_second_half_total
    ht_expected_total_final = totals_model.expected_final_total

    # Split second half between teams by pre-game attack proportion
    # Use margin → home team proportion of total
    if pg_total > 0:
        # Home team pre-game expected total based on margin + total
        home_pregame_score = (pg_total + pg_hcap) / 2
        away_pregame_score = (pg_total - pg_hcap) / 2
        home_attack_ratio = home_pregame_score / pg_total if pg_total > 0 else 0.5
    else:
        home_attack_ratio = 0.5

    home_attack_ratio = max(0.3, min(0.7, home_attack_ratio))  # guardrail
    sh_home = sh_total * home_attack_ratio
    sh_away = sh_total * (1 - home_attack_ratio)

    home_win_prob = margin_model.home_win_probability
    away_win_prob = margin_model.away_win_probability
    ht_home_odds = margin_model.home_fair_odds
    ht_away_odds = margin_model.away_fair_odds

    # Median of the same distribution used by H2H probability.
    ht_hcap = margin_model.fair_home_handicap
    # Betting line is the 50/50 point of the predictive distribution, not its
    # right-skewed expected mean.
    ht_total = round(totals_model.fair_final_total, 1)

    # ── Signal classification ──────────────────────────────────────────────────
    notes: list[str] = []
    adj_magnitude = abs(margin_model.process_adjustment)

    # ETxP signal (home_in20/away_in20 already extracted above)
    have_in20 = _safe_float(stats.get("home_inside_20_possessions", 0)) > 0 or _safe_float(
        stats.get("away_inside_20_possessions", 0)
    ) > 0
    if have_in20:
        etxp_diff = (home_in20 - away_in20) * 0.8   # ~0.8 pts per inside-20 possession
        etxp_vs_score = etxp_diff - ht_margin
        if abs(etxp_vs_score) >= 6:
            leader = home if etxp_vs_score > 0 else away
            notes.append(f"ETxP divergence {etxp_vs_score:+.1f} pts (field position favours {leader})")

    if abs(error_adj) >= 2:
        better = home if error_adj > 0 else away
        notes.append(f"Error adj {error_adj:+.1f} pts ({better} had fewer errors)")

    if abs(restart_adj) >= 2:
        inflated = home if restart_advantage > 0 else away
        notes.append(f"Restart inflation adj {restart_adj:+.1f} pts (deflating {inflated} first-half advantage)")

    if abs(conversion_adj) >= 2:
        unlucky = home if conversion_adj > 0 else away
        notes.append(f"Conversion luck adj {conversion_adj:+.1f} pts ({unlucky} missed conversions)")

    for inj in home_injuries:
        src = f" [{inj.get('source', 'nrl_api')}]" if inj.get("source") == "manual" else ""
        notes.append(f"IN-GAME INJURY: {home} — {inj['name']} ({inj['position']}) off at {inj['minute']}min [{inj['title']}]{src}")
    for inj in away_injuries:
        src = f" [{inj.get('source', 'nrl_api')}]" if inj.get("source") == "manual" else ""
        notes.append(f"IN-GAME INJURY: {away} — {inj['name']} ({inj['position']}) off at {inj['minute']}min [{inj['title']}]{src}")
    if ingame_injury_hcap != 0:
        notes.append(f"Injury hcap adj {ingame_injury_hcap:+.1f} pts (home perspective)")
    for sb in sin_bins:
        team = home if sb.get("side") == "home" else away
        sb_type = "SEND-OFF" if sb.get("type") == "send_off" else "SIN BIN"
        notes.append(f"{sb_type}: {team} — {sb['name']} ({sb['position']}) at {sb['minute']}min")

    if adj_magnitude >= 4:
        strength = "strong"
    elif adj_magnitude >= 2:
        strength = "moderate"
    elif adj_magnitude >= 0.75:
        strength = "weak"
    else:
        strength = "neutral"

    direction = "NEUTRAL"
    if margin_model.process_adjustment >= 0.75:
        direction = "HOME"
    elif margin_model.process_adjustment <= -0.75:
        direction = "AWAY"

    return HalfTimePricing(
        home_team=home,
        away_team=away,
        season=stats["season"],
        round=stats["round"],
        game_date=stats.get("game_date", ""),
        priced_at=datetime.now(timezone.utc).isoformat(),
        ht_home_score=ht_home,
        ht_away_score=ht_away,
        ht_margin=ht_margin,
        pregame_fair_hcap=pg_hcap,
        pregame_fair_total=pg_total,
        pregame_home_prob=pg_home_prob,
        second_half_expected_total=sh_total,
        second_half_home_expected=sh_home,
        second_half_away_expected=sh_away,
        error_adjustment=round(error_adj, 2),
        conversion_adjustment=round(conversion_adj, 2),
        restart_adjustment=round(restart_adj, 2),
        stats_implied_margin=round(stats_implied_margin, 2),
        stats_regression_adj=round(stats_regression_adj, 4),
        regression_factor_used=round(regression, 4),
        ht_expected_margin=round(ht_expected_margin, 2),
        ht_expected_total=ht_expected_total_final,
        ht_home_win_prob=home_win_prob,
        ht_away_win_prob=away_win_prob,
        ht_home_odds=ht_home_odds,
        ht_away_odds=ht_away_odds,
        ht_hcap_line=ht_hcap,
        ht_total_line=ht_total,
        totals_model_version=totals_model.model_version,
        totals_historical_h2_baseline=totals_model.historical_h2_baseline,
        totals_pregame_h2_prior=totals_model.pregame_h2_prior,
        totals_blended_h2_baseline=totals_model.blended_h2_baseline,
        totals_process_adjustment=totals_model.process_adjustment,
        totals_fair_line=totals_model.fair_final_total,
        totals_distribution_sample_size=totals_model.distribution_sample_size,
        totals_feature_coverage=totals_model.feature_coverage,
        totals_quality=totals_model.quality,
        totals_adjustments=totals_model.adjustments,
        margin_model_version=margin_model.model_version,
        margin_elapsed_game_fraction=margin_model.elapsed_game_fraction,
        margin_expected_remaining_pregame=margin_model.expected_remaining_pregame_margin,
        margin_baseline=margin_model.baseline_expected_margin,
        margin_process_adjustment=margin_model.process_adjustment,
        margin_median=margin_model.median_final_margin,
        margin_distribution_sample_size=margin_model.distribution_sample_size,
        margin_feature_coverage=margin_model.feature_coverage,
        margin_quality=margin_model.quality,
        margin_adjustments=margin_model.adjustments,
        ingame_home_injuries=home_injuries,
        ingame_away_injuries=away_injuries,
        ingame_injury_hcap_adj=round(ingame_injury_hcap, 2),
        ingame_injury_total_adj=round(ingame_injury_total, 2),
        ingame_injury_sources=injury_sources,
        sin_bins=sin_bins,
        signal_strength=strength,
        signal_direction=direction,
        signal_notes=notes,
    )


def print_pricing(p: HalfTimePricing) -> None:
    print(f"\n{'='*65}")
    print(f"HALF-TIME PRICING — {p.home_team} vs {p.away_team}")
    print(f"{'='*65}")
    print(f"  HT Score:       {p.home_team} {p.ht_home_score} – {p.ht_away_score} {p.away_team}")
    print(f"  HT Margin:      {p.ht_margin:+d} (home perspective)")
    print(f"  Pre-game hcap:  {p.pregame_fair_hcap:+.1f}")
    print(f"\n  --- Second Half Estimates ---")
    print(f"  2H expected total: {p.second_half_expected_total:.1f} pts")
    print(f"  2H home expected:  {p.second_half_home_expected:.1f} pts")
    print(f"  2H away expected:  {p.second_half_away_expected:.1f} pts")
    print(f"\n  --- Adjustments ---")
    print(f"  Error adj:         {p.error_adjustment:+.1f}")
    print(f"  Conversion adj:    {p.conversion_adjustment:+.1f}")
    print(f"  Restart adj:       {p.restart_adjustment:+.1f}")
    print(f"\n  --- Legacy Margin Diagnostics (not active pricing) ---")
    print(f"  Stats-implied margin: {p.stats_implied_margin:+.1f} (errors + in-20s + restarts)")
    if p.stats_regression_adj != 0:
        direction = "backs prior" if p.stats_regression_adj > 0 else "opposes prior"
        print(f"  Stats vs prior:       {direction} -> regression {p.regression_factor_used:.2f} "
              f"(base {REGRESSION_FACTOR:.2f} {p.stats_regression_adj:+.4f})")
    else:
        print(f"  Legacy regression:    {p.regression_factor_used:.2f} (diagnostic only)")
    if p.ingame_home_injuries or p.ingame_away_injuries:
        source_label = ", ".join(p.ingame_injury_sources) if p.ingame_injury_sources else "nrl_api"
        print(f"\n  --- In-Game Injuries (source: {source_label}) ---")
        for inj in p.ingame_home_injuries:
            impact = NRL_INGAME_IMPACT.get(inj["position"], (-0.5, 0.0))
            tag = " [MANUAL]" if inj.get("source") == "manual" else ""
            print(f"  {p.home_team:20s}  {inj['name']:25s} ({inj['position']:15s}) off {inj['minute']}min  hcap {impact[0]:+.1f}{tag}")
        for inj in p.ingame_away_injuries:
            impact = NRL_INGAME_IMPACT.get(inj["position"], (-0.5, 0.0))
            tag = " [MANUAL]" if inj.get("source") == "manual" else ""
            print(f"  {p.away_team:20s}  {inj['name']:25s} ({inj['position']:15s}) off {inj['minute']}min  hcap {impact[0]:+.1f}{tag}")
        print(f"  Net injury hcap adj: {p.ingame_injury_hcap_adj:+.1f} (home perspective)")
        print(f"  Net injury total adj: {p.ingame_injury_total_adj:+.1f}")
    if p.sin_bins:
        print(f"\n  --- Sin Bins / Send-Offs ---")
        for sb in p.sin_bins:
            team = p.home_team if sb.get("side") == "home" else p.away_team
            sb_type = "SEND-OFF" if sb.get("type") == "send_off" else "SIN BIN"
            print(f"  {sb_type}: {team} — {sb['name']} ({sb['position']}) at {sb['minute']}min")
    print(f"\n  --- Updated Prices ---")
    print(f"  Expected final margin: {p.ht_expected_margin:+.1f} (home)")
    print(f"  Win prob:         {p.home_team} {p.ht_home_win_prob:.1%} / {p.away_team} {p.ht_away_win_prob:.1%}")
    print(f"  Fair H2H odds:    {p.home_team} {p.ht_home_odds} / {p.away_team} {p.ht_away_odds}")
    print(f"  HT Hcap line:     {p.ht_hcap_line:+.1f} (home)")
    print(f"  Margin model:     {p.margin_model_version} "
          f"({p.margin_quality}, coverage {p.margin_feature_coverage:.0%})")
    print(f"  Remaining prior: {p.margin_expected_remaining_pregame:+.1f} "
          f"({1 - p.margin_elapsed_game_fraction:.0%} of pregame margin)")
    print(f"  Margin base/live: {p.margin_baseline:+.1f} / {p.margin_process_adjustment:+.1f}; "
          f"median {p.margin_median:+.1f}; empirical n={p.margin_distribution_sample_size}")
    for adjustment in p.margin_adjustments:
        print(f"    • {adjustment}")
    print(f"  HT Total line:    {p.ht_total_line:.1f}")
    print(f"  Expected total:   {p.ht_expected_total:.1f} (mean; not the betting line)")
    print(f"  Totals model:     {p.totals_model_version} "
          f"({p.totals_quality}, coverage {p.totals_feature_coverage:.0%})")
    print(f"  Totals H2 base:   historical {p.totals_historical_h2_baseline:.1f} / "
          f"pregame {p.totals_pregame_h2_prior:.1f} / blended {p.totals_blended_h2_baseline:.1f}")
    print(f"  Totals process:   {p.totals_process_adjustment:+.1f}")
    print(f"  Distribution:     empirical n={p.totals_distribution_sample_size}; "
          f"50/50 line {p.totals_fair_line:.1f}")
    for adjustment in p.totals_adjustments:
        print(f"    • {adjustment}")
    print(f"\n  --- Signal ---")
    print(f"  Strength:   {p.signal_strength.upper()}")
    print(f"  Direction:  {p.signal_direction}")
    for note in p.signal_notes:
        print(f"  • {note}")
    print(f"{'='*65}\n")


# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="NRL half-time pricing model")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--file", type=Path, help="Path to half-time stats JSON")
    src.add_argument("--round", type=int, help="Auto-find latest HT stats for this round")
    p.add_argument("--home", type=str, help="Home team (with --round)")
    p.add_argument("--away", type=str, help="Away team (with --round)")
    p.add_argument("--save", action="store_true", help="Save pricing output to JSON")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    # Load stats
    if args.file:
        stats_path = args.file
    else:
        # Find latest stats file for the round + teams
        round_dir = HALFTIME_DIR / f"R{args.round:02d}"
        if not round_dir.exists():
            print(f"No half-time data for round {args.round} — run nrl_halftime_stats.py first.")
            return
        candidates = list(round_dir.glob("*.json"))
        if not candidates:
            print(f"No JSON files in {round_dir}")
            return
        if args.home and args.away:
            home_n = args.home.split()[-1].lower()
            away_n = args.away.split()[-1].lower()
            candidates = [c for c in candidates if home_n in c.name and away_n in c.name]
        candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        if not candidates:
            print("No matching stats file found.")
            return
        stats_path = candidates[0]

    stats = json.loads(stats_path.read_text(encoding="utf-8"))
    print(f"Loaded stats: {stats_path.name}")

    # Load pre-game pricing
    pregame = load_pregame_row(stats["home_team"], stats["away_team"])

    # Price
    pricing = price_halftime(stats, pregame)
    print_pricing(pricing)

    # Save
    if args.save:
        out_name = stats_path.stem + "_pricing.json"
        out_path = stats_path.parent / out_name
        out_path.write_text(
            json.dumps(asdict(pricing), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"Saved pricing → {out_path}")


if __name__ == "__main__":
    main()
