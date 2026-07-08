#!/usr/bin/env python3
"""
BettingEngine/scripts/halfTime_price_afl.py

AFL half-time pricing model.

Takes:
  - Halftime stats JSON (from afl_ht_live.py — goals/behinds at half)
  - Pre-game pricing row (from results/r{nn}_afl_2026.csv)

Produces:
  - Updated H2H odds, handicap line, and total for the second half
  - Written to data/afl/halfTime/R{nn}/YYYY-MM-DD_{game}_pricing.json

The model applies a Bayesian update:
  - Pre-game estimates are the prior (team strength, expected margin, expected total)
  - Half-time score state is the evidence
  - REGRESSION_FACTOR controls how much the prior survives vs the HT evidence

AFL-specific adjustments:
  - Accuracy correction: if a team is shooting below/above their normal accuracy,
    some of the score differential is "luck" that may not persist in the second half
  - Score shot differential: if we can infer how many shots each team had, we can
    estimate whether the HT margin under/overstates actual dominance

Usage:
    python scripts/halfTime_price_afl.py --file path/to/halftime_stats.json
    python scripts/halfTime_price_afl.py --round 14 --home Melbourne --away Essendon
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
_ROOT        = Path(__file__).resolve().parent.parent
RESULTS_DIR  = _ROOT / "results"
HALFTIME_DIR = _ROOT / "data" / "afl" / "halfTime"

# ── Model constants ────────────────────────────────────────────────────────────
# AFL halftime regression factor — slightly higher than NRL (AFL is more continuous,
# halftime scores are a stronger predictor of final result than NRL)
# Start at 0.45 — re-calibrate once we have 50+ halftime observations in 2026.
REGRESSION_FACTOR = 0.45

# AFL average scoring per half — calibrated on 875 games (2022-2026): avg FT 167.5 → H2 avg 84.9
AVG_HALF_SCORE = 85.0

# League-average AFL kicking accuracy (goals / (goals + behinds))
# Calibrated on 875-game dataset (2022-2026): 2022=0.534, 2023=0.523, 2024=0.532, 2025=0.528, 2026=0.531
BASELINE_ACCURACY = 0.529

# ── Live stats adjustment constants ──────────────────────────────────────────
# NOTE: These weights are research-estimated, not regression-fitted.
# The 875-game historical dataset does not contain per-quarter team stats (inside 50s,
# clearances, clangers), so we cannot run a direct calibration regression.
# These will be calibrated once we accumulate 50+ live-scraped halftime observations.
#
# Inside 50s: best single non-score predictor (R²~55% with contested poss).
# Weight is small because score already reflects most territorial dominance.
PTS_PER_I50_DIFF = 0.4

# Clearances: controls first possession from stoppages — predicts H2 tempo.
PTS_PER_CLEARANCE_DIFF = 0.3

# Clangers: unforced turnovers creating easy opponent scores (like NRL errors).
PTS_PER_CLANGER_DIFF = 0.5

# Cap on total stats adjustment — stats are secondary to the score signal.
# In extreme cases (e.g. 10+ I50 differential) this prevents stats swamping Bayesian blend.
STATS_ADJ_CAP = 6.0

# Accuracy trend weight — how much of H1 accuracy carries into H2.
# Logic: if a team is kicking 70% in H1, project them to continue at 70% in H2.
# If kicking 40%, they'll continue at 40%. Trend persists, no regression to mean.
# H2 shot count estimated from H1 shots (same game pace).
# Each shot at accuracy `a` vs baseline `b` = 5*(a-b) pts difference per shot.
# Weight of 1.0 = full trend continuation. Reduce if you want partial regression.
# NOTE (calibration 2026-06-19): 875-game backtest shows accuracy trend has near-zero
# historical predictive power (corr = -0.04 with H2 margin). Retained at 1.0 per
# user preference (situational signals like wet/dry conditions may carry more weight
# than the population average suggests). Treat as a qualitative lens, not a strong edge.
ACCURACY_TREND_WEIGHT = 1.0

# Standard deviation multiplier for scoring distribution (AFL is more Gaussian than NRL)
STD_FACTOR = 1.2

# Simulation runs
SIM_RUNS    = 20_000
RANDOM_SEED = 42

# Second half total by first half total — calibrated on 875 AFL games (2022-2026)
# Key finding: H2 scoring INCREASES with H1 scoring — high-scoring teams stay high-scoring.
# No regression to mean. Actual data (n=875):
#   H1 <60:    n=104, avg H2=82.1  → 82.0
#   H1 61-75:  n=206, avg H2=83.3  → 83.0
#   H1 76-88:  n=244, avg H2=84.6  → 85.0
#   H1 89-100: n=173, avg H2=86.0  → 86.0
#   H1 101+:   n=148, avg H2=88.5  → 89.0
SECOND_HALF_BY_FIRST = {
    # (first_half_total_range): expected second_half_total
    (0,   60): 82.0,   # very low scoring H1 → still ~82 in H2
    (61,  75): 83.0,
    (76,  88): 85.0,   # near average (actual avg 84.6)
    (89, 100): 86.0,
    (101, 999): 89.0,  # high scoring H1 → H2 even higher (actual avg 88.5)
}


# ── Pre-game pricing loader ───────────────────────────────────────────────────

def _round_num_from_path(p: Path) -> int:
    m = re.match(r"r(\d+)", p.stem)
    return int(m.group(1)) if m else 0


def _latest_afl_pricing_csv() -> Path | None:
    candidates = []
    seen = set()
    for pattern in ["r*_afl_2026.csv", "r*_afl_pricing_2026.csv", "r*_pricing_afl_2026.csv"]:
        for p in RESULTS_DIR.glob(pattern):
            if p not in seen:
                seen.add(p)
                candidates.append(p)
    # Also check data/pricing/afl/
    pricing_dir = _ROOT / "data" / "pricing" / "afl"
    if pricing_dir.exists():
        for p in pricing_dir.glob("AFL_PRICING_*.csv"):
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


BETMATE_AFL_URL = "https://betmate.au/api/afl-predictions"


def _short(s: str) -> str:
    return s.lower().split()[-1] if s else ""


def _teams_match(h: str, a: str, home: str, away: str) -> bool:
    home_l, away_l = home.lower(), away.lower()
    home_s, away_s = _short(home), _short(away)
    return (
        (home_l in h or h in home_l or _short(h) == home_s) and
        (away_l in a or a in away_l or _short(a) == away_s)
    )


def _load_from_betmate(home: str, away: str) -> dict | None:
    """Pull pre-game lines from betmate.au/api/afl-predictions (live posted lines)."""
    try:
        import requests as _req
        r = _req.get(BETMATE_AFL_URL, timeout=10)
        r.raise_for_status()
        predictions = r.json().get("predictions", r.json() if isinstance(r.json(), list) else [])
    except Exception as exc:
        print(f"  betmate.au unavailable: {exc}")
        return None

    for p in predictions:
        h = str(p.get("home_team", p.get("homeTeam", ""))).lower()
        a = str(p.get("away_team", p.get("awayTeam", ""))).lower()
        flipped = False
        if not _teams_match(h, a, home, away):
            if _teams_match(a, h, home, away):
                flipped = True
            else:
                continue

        # Reconstruct a row dict compatible with price_halftime expectations
        home_score = _safe_float(p.get("home_score", p.get("homeScore", p.get("predHomeScore", 0))))
        away_score = _safe_float(p.get("away_score", p.get("awayScore", p.get("predAwayScore", 0))))
        margin     = _safe_float(p.get("margin", home_score - away_score))
        total      = _safe_float(p.get("total", home_score + away_score))

        if flipped:
            margin = -margin

        row = {
            "home_team":        home if not flipped else away,
            "away_team":        away if not flipped else home,
            "rules_margin":     margin,
            "rules_total":      total,
            "rules_home_odds":  "",
            "rules_away_odds":  "",
            "rules_home_prob":  "",
            "_source":          "betmate.au",
            "_flipped":         flipped,
        }
        print(f"  betmate.au: margin={margin:+.1f}  total={total:.1f}")
        return row

    print(f"  betmate.au: no match found for {home} vs {away}")
    return None


def load_pregame_row(home: str, away: str) -> dict | None:
    # 1. Try betmate.au (live posted lines — preferred on game day)
    row = _load_from_betmate(home, away)
    if row:
        return row

    # 2. Fall back to local CSV
    csv_path = _latest_afl_pricing_csv()
    if not csv_path:
        print("No AFL pricing CSV found in results/ or data/pricing/afl/")
        return None

    home_l = home.lower()
    away_l = away.lower()
    home_s = _short(home)
    away_s = _short(away)

    with open(csv_path, newline="", encoding="utf-8", errors="replace") as f:
        for row in csv.DictReader(f):
            h = row.get("home_team", "").lower()
            a = row.get("away_team", "").lower()
            if _teams_match(h, a, home, away):
                return row
            if _teams_match(a, h, home, away):
                row["_flipped"] = True
                return row

    print(f"No pre-game row found for {home} vs {away} in {csv_path.name}")
    return None


# ── Second half total estimator ───────────────────────────────────────────────

def expected_second_half_total(first_half_total: int) -> float:
    for (lo, hi), expected in SECOND_HALF_BY_FIRST.items():
        if lo <= first_half_total <= hi:
            return expected
    return AVG_HALF_SCORE


# ── Win probability via simulation ────────────────────────────────────────────

def simulate_win_prob(
    ht_margin: int,
    home_2h_mean: float,
    away_2h_mean: float,
    runs: int = SIM_RUNS,
) -> dict[str, float]:
    """
    Monte Carlo: model second-half AFL scoring as Normal distribution.
    AFL scores are fairly Gaussian around team strength — overdispersion
    is lower than NRL due to continuous play style.
    """
    rng = random.Random(RANDOM_SEED)
    home_wins = away_wins = draws = 0

    home_std = max(math.sqrt(home_2h_mean) * STD_FACTOR, 5.0)
    away_std = max(math.sqrt(away_2h_mean) * STD_FACTOR, 5.0)

    for _ in range(runs):
        h2 = max(0, round(rng.gauss(home_2h_mean, home_std)))
        a2 = max(0, round(rng.gauss(away_2h_mean, away_std)))
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
    if p <= 0:
        return 99.0
    return round(1.0 / p, 2)


# ── Core pricing ──────────────────────────────────────────────────────────────

@dataclass
class HalfTimePricingAFL:
    home_team: str
    away_team: str
    season: int
    round: int
    game_date: str
    priced_at: str
    venue: str

    # Input
    ht_home_score: int
    ht_away_score: int
    ht_home_goals: int
    ht_home_behinds: int
    ht_away_goals: int
    ht_away_behinds: int
    ht_margin: int

    # Pre-game prior
    pregame_fair_hcap: float
    pregame_fair_total: float
    pregame_home_prob: float

    # Adjustments
    accuracy_adjustment: float
    i50_adjustment: float
    clearance_adjustment: float
    clanger_adjustment: float
    stats_adjustment: float     # i50 + clearances + clangers, capped

    # Live stats (None if FootyWire unavailable)
    home_inside_50s: int | None
    away_inside_50s: int | None
    home_clearances: int | None
    away_clearances: int | None
    home_clangers: int | None
    away_clangers: int | None

    # Second half estimates
    second_half_expected_total: float
    second_half_home_expected: float
    second_half_away_expected: float

    # Output
    ht_expected_margin: float
    ht_expected_final_total: float
    ht_home_win_prob: float
    ht_away_win_prob: float
    ht_home_odds: float
    ht_away_odds: float
    ht_hcap_line: float
    ht_total_line: float

    # Signal
    signal_strength: str
    signal_direction: str
    signal_notes: list[str]


def price_halftime(stats: dict, pregame: dict | None) -> HalfTimePricingAFL:
    home = stats["home_team"]
    away = stats["away_team"]

    ht_home_goals   = int(stats.get("home_goals", 0))
    ht_home_behinds = int(stats.get("home_behinds", 0))
    ht_away_goals   = int(stats.get("away_goals", 0))
    ht_away_behinds = int(stats.get("away_behinds", 0))

    ht_home = int(stats.get("home_ht_score", ht_home_goals * 6 + ht_home_behinds))
    ht_away = int(stats.get("away_ht_score", ht_away_goals * 6 + ht_away_behinds))
    ht_margin = ht_home - ht_away
    first_half_total = ht_home + ht_away

    # ── Pre-game prior ─────────────────────────────────────────────────────────
    if pregame:
        flipped = pregame.get("_flipped", False)

        # Use rules model as primary prior (more stable than ML for HT repricing)
        pg_margin  = _safe_float(pregame.get("rules_margin", pregame.get("ml_margin", 0)))
        pg_total   = _safe_float(pregame.get("rules_total", pregame.get("ml_total", 168.0)))
        pg_h_odds  = _safe_float(pregame.get("rules_home_odds", 2.0))
        pg_a_odds  = _safe_float(pregame.get("rules_away_odds", 2.0))
        pg_home_prob = (1 / pg_h_odds) if pg_h_odds > 1 else _safe_float(pregame.get("rules_home_prob", 0.5))

        if flipped:
            # Game was stored as away vs home — invert margin and probabilities
            pg_margin = -pg_margin
            pg_home_prob = 1 - pg_home_prob
            pg_h_odds, pg_a_odds = pg_a_odds, pg_h_odds
    else:
        pg_margin    = 0.0
        pg_total     = 168.0
        pg_home_prob = 0.5
        pg_h_odds    = 2.0
        pg_a_odds    = 2.0
        print("WARNING: No pre-game pricing found. Using neutral priors.")

    # ── Bayesian update ────────────────────────────────────────────────────────
    # Blend actual HT margin with pregame expected margin
    expected_final_margin = (
        ht_margin   * (1 - REGRESSION_FACTOR) +
        pg_margin   * REGRESSION_FACTOR
    )

    # ── Accuracy adjustment ────────────────────────────────────────────────────
    # Trend continues: project each team's H2 scoring using their H1 accuracy.
    # If kicking 70% in H1, they'll kick 70% in H2. No regression to mean.
    # Each shot at accuracy `a` vs baseline `b` = 5*(a-b) pts difference per shot.
    # H2 shot count estimated as equal to H1 shots (same game pace).
    home_shots = ht_home_goals + ht_home_behinds
    away_shots = ht_away_goals + ht_away_behinds

    home_actual_acc = (ht_home_goals / home_shots) if home_shots > 0 else BASELINE_ACCURACY
    away_actual_acc = (ht_away_goals / away_shots) if away_shots > 0 else BASELINE_ACCURACY

    # Expected H2 pts above/below baseline for each team based on their H1 accuracy trend
    home_acc_adj = home_shots * 5 * (home_actual_acc - BASELINE_ACCURACY) * ACCURACY_TREND_WEIGHT
    away_acc_adj = away_shots * 5 * (away_actual_acc - BASELINE_ACCURACY) * ACCURACY_TREND_WEIGHT

    # Net adjustment in home team's favour (positive = home benefits from accuracy trend)
    accuracy_adj = home_acc_adj - away_acc_adj

    # ── Live stats adjustments (inside 50s, clearances, clangers) ─────────────
    home_i50 = stats.get("home_inside_50s")
    away_i50 = stats.get("away_inside_50s")
    home_clr = stats.get("home_clearances")
    away_clr = stats.get("away_clearances")
    home_clg = stats.get("home_clangers")
    away_clg = stats.get("away_clangers")

    have_stats = all(v is not None for v in [home_i50, away_i50, home_clr, away_clr, home_clg, away_clg])

    if have_stats:
        i50_adj      = (home_i50 - away_i50) * PTS_PER_I50_DIFF
        clearance_adj = (home_clr - away_clr) * PTS_PER_CLEARANCE_DIFF
        clanger_adj  = (away_clg - home_clg) * PTS_PER_CLANGER_DIFF
        stats_adj    = max(-STATS_ADJ_CAP, min(STATS_ADJ_CAP, i50_adj + clearance_adj + clanger_adj))
    else:
        i50_adj = clearance_adj = clanger_adj = stats_adj = 0.0

    # ── Combined expected margin ───────────────────────────────────────────────
    ht_expected_margin = expected_final_margin + accuracy_adj + stats_adj

    # ── Second half total estimate ─────────────────────────────────────────────
    sh_total = expected_second_half_total(first_half_total)
    ht_expected_final_total = first_half_total + sh_total

    # Split second half by pregame attack ratio
    if pg_total > 0:
        home_pregame_pts = (pg_total + pg_margin) / 2
        away_pregame_pts = (pg_total - pg_margin) / 2
        home_attack_ratio = home_pregame_pts / pg_total
    else:
        home_attack_ratio = 0.5

    home_attack_ratio = max(0.35, min(0.65, home_attack_ratio))
    sh_home = sh_total * home_attack_ratio
    sh_away = sh_total * (1 - home_attack_ratio)

    # ── Simulate second half ───────────────────────────────────────────────────
    probs = simulate_win_prob(ht_margin, sh_home, sh_away)
    home_win_prob = probs["home_win"]
    away_win_prob = probs["away_win"]

    ht_home_odds = prob_to_odds(home_win_prob)
    ht_away_odds = prob_to_odds(away_win_prob)

    ht_hcap = round(-ht_expected_margin, 1)
    ht_total = round(ht_expected_final_total, 1)

    # ── Signal ────────────────────────────────────────────────────────────────
    notes: list[str] = []

    if home_shots >= 3 and abs(home_actual_acc - BASELINE_ACCURACY) >= 0.1:
        trend = "above" if home_actual_acc > BASELINE_ACCURACY else "below"
        notes.append(
            f"Home accuracy {home_actual_acc:.0%} ({ht_home_goals}.{ht_home_behinds}) "
            f"— {trend} avg {BASELINE_ACCURACY:.0%}, trend projected to continue in 2H"
        )
    if away_shots >= 3 and abs(away_actual_acc - BASELINE_ACCURACY) >= 0.1:
        trend = "above" if away_actual_acc > BASELINE_ACCURACY else "below"
        notes.append(
            f"Away accuracy {away_actual_acc:.0%} ({ht_away_goals}.{ht_away_behinds}) "
            f"— {trend} avg {BASELINE_ACCURACY:.0%}, trend projected to continue in 2H"
        )

    score_vs_pregame = ht_margin - (pg_margin / 2)
    if abs(score_vs_pregame) >= 12:
        leader = home if score_vs_pregame > 0 else away
        notes.append(
            f"HT margin {ht_margin:+d} vs pregame expected {pg_margin/2:+.1f} "
            f"— {leader} {abs(score_vs_pregame):.0f} pts ahead of model"
        )

    total_adj = accuracy_adj + stats_adj
    adj_magnitude = abs(total_adj)

    if adj_magnitude >= 6:
        strength = "strong"
    elif adj_magnitude >= 3:
        strength = "moderate"
    elif adj_magnitude >= 1.5:
        strength = "weak"
    else:
        strength = "neutral"

    direction = "NEUTRAL"
    if total_adj >= 1.5:
        direction = "HOME"
    elif total_adj <= -1.5:
        direction = "AWAY"

    return HalfTimePricingAFL(
        home_team=home,
        away_team=away,
        season=stats["season"],
        round=stats["round"],
        game_date=stats.get("game_date", ""),
        priced_at=datetime.now(timezone.utc).isoformat(),
        venue=stats.get("venue", ""),
        ht_home_score=ht_home,
        ht_away_score=ht_away,
        ht_home_goals=ht_home_goals,
        ht_home_behinds=ht_home_behinds,
        ht_away_goals=ht_away_goals,
        ht_away_behinds=ht_away_behinds,
        ht_margin=ht_margin,
        pregame_fair_hcap=pg_margin,
        pregame_fair_total=pg_total,
        pregame_home_prob=pg_home_prob,
        accuracy_adjustment=round(accuracy_adj, 2),
        i50_adjustment=round(i50_adj, 2),
        clearance_adjustment=round(clearance_adj, 2),
        clanger_adjustment=round(clanger_adj, 2),
        stats_adjustment=round(stats_adj, 2),
        home_inside_50s=home_i50,
        away_inside_50s=away_i50,
        home_clearances=home_clr,
        away_clearances=away_clr,
        home_clangers=home_clg,
        away_clangers=away_clg,
        second_half_expected_total=sh_total,
        second_half_home_expected=round(sh_home, 1),
        second_half_away_expected=round(sh_away, 1),
        ht_expected_margin=round(ht_expected_margin, 2),
        ht_expected_final_total=ht_total,
        ht_home_win_prob=home_win_prob,
        ht_away_win_prob=away_win_prob,
        ht_home_odds=ht_home_odds,
        ht_away_odds=ht_away_odds,
        ht_hcap_line=ht_hcap,
        ht_total_line=ht_total,
        signal_strength=strength,
        signal_direction=direction,
        signal_notes=notes,
    )


def print_pricing(p: HalfTimePricingAFL) -> None:
    print(f"\n{'='*65}")
    print(f"AFL HALF-TIME PRICING — {p.home_team} vs {p.away_team}")
    print(f"{'='*65}")
    print(f"  HT Score:       {p.home_team} {p.ht_home_goals}.{p.ht_home_behinds} ({p.ht_home_score}) "
          f"– {p.ht_away_goals}.{p.ht_away_behinds} ({p.ht_away_score}) {p.away_team}")
    print(f"  HT Margin:      {p.ht_margin:+d} (home perspective)")
    print(f"  Pre-game hcap:  {p.pregame_fair_hcap:+.1f}")
    print(f"  Venue:          {p.venue}")
    print(f"\n  --- Adjustments ---")
    print(f"  Accuracy adj:   {p.accuracy_adjustment:+.1f}")
    if p.home_inside_50s is not None:
        print(f"  Inside 50s:     {p.home_team.split()[-1]} {p.home_inside_50s} / {p.away_team.split()[-1]} {p.away_inside_50s}  → {p.i50_adjustment:+.1f}")
        print(f"  Clearances:     {p.home_team.split()[-1]} {p.home_clearances} / {p.away_team.split()[-1]} {p.away_clearances}  → {p.clearance_adjustment:+.1f}")
        print(f"  Clangers:       {p.home_team.split()[-1]} {p.home_clangers} / {p.away_team.split()[-1]} {p.away_clangers}  → {p.clanger_adjustment:+.1f}")
        print(f"  Stats adj:      {p.stats_adjustment:+.1f}  (capped ±{STATS_ADJ_CAP:.0f})")
    else:
        print(f"  Live stats:     unavailable (FootyWire offline) — score + accuracy only")
    print(f"\n  --- Second Half Estimates ---")
    print(f"  2H expected total: {p.second_half_expected_total:.1f} pts")
    print(f"  2H home expected:  {p.second_half_home_expected:.1f} pts")
    print(f"  2H away expected:  {p.second_half_away_expected:.1f} pts")
    print(f"\n  --- Updated Prices ---")
    print(f"  Expected final margin: {p.ht_expected_margin:+.1f} (home)")
    print(f"  Expected final total:  {p.ht_expected_final_total:.1f}")
    print(f"  Win prob:  {p.home_team} {p.ht_home_win_prob:.1%} / {p.away_team} {p.ht_away_win_prob:.1%}")
    print(f"  Fair odds: {p.home_team} {p.ht_home_odds} / {p.away_team} {p.ht_away_odds}")
    print(f"  HT Hcap:   {p.ht_hcap_line:+.1f} (home)")
    print(f"  HT Total:  {p.ht_total_line:.1f}")
    print(f"\n  --- Signal ---")
    print(f"  Strength:   {p.signal_strength.upper()}")
    print(f"  Direction:  {p.signal_direction}")
    for note in p.signal_notes:
        print(f"  • {note}")
    print(f"{'='*65}\n")


# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="AFL half-time pricing model")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--file", type=Path, help="Path to half-time stats JSON")
    src.add_argument("--round", type=int, help="Auto-find latest HT stats for this round")
    p.add_argument("--home", type=str, help="Home team (with --round)")
    p.add_argument("--away", type=str, help="Away team (with --round)")
    p.add_argument("--save", action="store_true", help="Save pricing output to JSON")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    if args.file:
        stats_path = args.file
    else:
        round_dir = HALFTIME_DIR / f"R{args.round:02d}"
        if not round_dir.exists():
            print(f"No half-time data for AFL round {args.round} — run afl_ht_live.py first.")
            return
        candidates = list(round_dir.glob("*_stats.json"))
        if not candidates:
            print(f"No stats JSON in {round_dir}")
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

    pregame = load_pregame_row(stats["home_team"], stats["away_team"])

    pricing = price_halftime(stats, pregame)
    print_pricing(pricing)

    if args.save:
        out_name = stats_path.stem.replace("_stats", "") + "_pricing.json"
        out_path = stats_path.parent / out_name
        out_path.write_text(
            json.dumps(asdict(pricing), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"Saved pricing → {out_path}")


if __name__ == "__main__":
    main()
