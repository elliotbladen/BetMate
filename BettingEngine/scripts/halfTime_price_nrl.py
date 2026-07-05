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

# ── Paths ─────────────────────────────────────────────────────────────────────
ENGINE_ROOT  = Path(__file__).resolve().parent.parent
BETMATE_ROOT = Path(os.environ.get("BETMATE_ROOT", ENGINE_ROOT.parent))
RESULTS_DIR  = ENGINE_ROOT / "results"
HALFTIME_DIR = BETMATE_ROOT / "data" / "nrl" / "halfTime"

# ── Model constants ────────────────────────────────────────────────────────────
# How much the pre-game prior survives at half time (1.0 = ignore HT score, 0.0 = fully trust HT)
# Applied to the H2 projection only — H1 points are already locked in and banked.
# NRL is continuous, high-contact rugby league (similar to AFL): at halftime the score state
# is highly informative. Lowered from 0.55 → 0.25 (75% weight to H1 evidence, 25% pre-game).
REGRESSION_FACTOR = 0.25

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

# Run metres — dominance in ball-in-play metres predicts H2 scoring momentum
# Research: run metres per game ~1100-1300 total; difference >200m strongly correlates
# with territory control and subsequent scoring. ~0.012 pts per metre diff, capped at 12 pts.
PTS_PER_RUN_METRES_DIFF = 0.012
RUN_METRES_ADJ_CAP = 12.0

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
    run_metres_adjustment: float   # run metres dominance → H2 scoring momentum

    # Output
    ht_expected_margin: float      # positive = home expected to win
    ht_expected_total: float
    ht_home_win_prob: float
    ht_away_win_prob: float
    ht_home_odds: float
    ht_away_odds: float
    ht_hcap_line: float            # from home perspective (negative = home giving points)
    ht_total_line: float

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

    # ── Bayesian update: expected final margin ─────────────────────────────────
    # H1 points are locked in — only the H2 is uncertain. Project H2 margin and bank H1.
    # Pre-game handicap is a full-game estimate; halve it for H2 prior.
    pg_h2_hcap = pg_hcap / 2
    expected_h2_margin = (
        ht_margin   * (1 - REGRESSION_FACTOR) +
        pg_h2_hcap  * REGRESSION_FACTOR
    )
    expected_final_margin = ht_margin + expected_h2_margin

    # ── Error adjustment ───────────────────────────────────────────────────────
    home_errors = stats.get("home_errors", 0)
    away_errors = stats.get("away_errors", 0)
    error_diff = away_errors - home_errors   # positive = home had fewer errors (good for home)
    error_adj = error_diff * POINTS_PER_ERROR_DIFF * ERROR_REGRESSION_FACTOR

    # ── Set restart inflation removal ──────────────────────────────────────────
    # H1 restarts inflate the home/away margin; only 64% of H1 restart frequency repeats in H2.
    # So 36% of H1 restart advantage (RESTART_H2_DEFLATION) won't carry forward — subtract it.
    # RESTART_NET_PTS = 0.72 pts net per restart (Rugby League Eye Test: 1.24 vs 0.52 normal set).
    home_restarts = stats.get("home_set_restarts_received", 0)
    away_restarts = stats.get("away_set_restarts_received", 0)
    restart_advantage = (home_restarts - away_restarts) * RESTART_NET_PTS * RESTART_H2_DEFLATION
    restart_adj = -restart_advantage  # subtract what was restart-inflated

    # ── Conversion luck adjustment ─────────────────────────────────────────────
    home_tries = stats.get("home_tries", 0)
    away_tries = stats.get("away_tries", 0)
    home_conv  = stats.get("home_conversions_made", 0)
    away_conv  = stats.get("away_conversions_made", 0)

    # Expected conversions at baseline rate
    home_expected_conv = home_tries * BASELINE_CONVERSION_RATE
    away_expected_conv = away_tries * BASELINE_CONVERSION_RATE

    # Points "owed" from missed conversions (2 pts each)
    home_conv_luck = (home_conv - home_expected_conv) * 2   # negative = missed, owed points
    away_conv_luck = (away_conv - away_expected_conv) * 2
    conversion_adj = away_conv_luck - home_conv_luck  # net adj in home team's favour
    conversion_adj = max(-CONVERSION_ADJ_CAP, min(CONVERSION_ADJ_CAP, conversion_adj))

    # ── Run metres adjustment ───────────────────────────────────────────────────
    home_run_metres = stats.get("home_run_metres", 0) or 0
    away_run_metres = stats.get("away_run_metres", 0) or 0
    if home_run_metres > 0 or away_run_metres > 0:
        run_metres_diff = home_run_metres - away_run_metres
        run_metres_adj = run_metres_diff * PTS_PER_RUN_METRES_DIFF
        run_metres_adj = max(-RUN_METRES_ADJ_CAP, min(RUN_METRES_ADJ_CAP, run_metres_adj))
    else:
        run_metres_adj = 0.0

    # ── Combined expected margin ───────────────────────────────────────────────
    total_adj = error_adj + restart_adj + conversion_adj + run_metres_adj
    ht_expected_margin = expected_final_margin + total_adj

    # ── Second half total estimate ─────────────────────────────────────────────
    sh_total = expected_second_half_total(first_half_total)
    ht_expected_total_final = first_half_total + sh_total

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

    # ── Simulate second half ───────────────────────────────────────────────────
    probs = simulate_win_prob(ht_margin, sh_home, sh_away)
    home_win_prob = probs["home_win"]
    away_win_prob = probs["away_win"]

    # Final odds (no margin — fair prices)
    ht_home_odds = prob_to_odds(home_win_prob)
    ht_away_odds = prob_to_odds(away_win_prob)

    # Handicap line (from home perspective, at full time)
    ht_hcap = round(-ht_expected_margin, 1)  # negative = home giving points
    ht_total = round(ht_expected_total_final, 1)

    # ── Signal classification ──────────────────────────────────────────────────
    notes: list[str] = []
    adj_magnitude = abs(total_adj)

    # ETxP signal
    home_in20 = stats.get("home_inside_20_possessions", 0)
    away_in20 = stats.get("away_inside_20_possessions", 0)
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

    if abs(run_metres_adj) >= 2:
        dominant = home if run_metres_adj > 0 else away
        notes.append(f"Run metres adj {run_metres_adj:+.1f} pts ({dominant} dominating territory, diff={home_run_metres - away_run_metres:+d}m)")

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
        run_metres_adjustment=round(run_metres_adj, 2),
        ht_expected_margin=round(ht_expected_margin, 2),
        ht_expected_total=ht_expected_total_final,
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
    print(f"  Run metres adj:    {p.run_metres_adjustment:+.1f}")
    print(f"\n  --- Updated Prices ---")
    print(f"  Expected final margin: {p.ht_expected_margin:+.1f} (home)")
    print(f"  Win prob:         {p.home_team} {p.ht_home_win_prob:.1%} / {p.away_team} {p.ht_away_win_prob:.1%}")
    print(f"  Fair H2H odds:    {p.home_team} {p.ht_home_odds} / {p.away_team} {p.ht_away_odds}")
    print(f"  HT Hcap line:     {p.ht_hcap_line:+.1f} (home)")
    print(f"  HT Total line:    {p.ht_total_line:.1f}")
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
