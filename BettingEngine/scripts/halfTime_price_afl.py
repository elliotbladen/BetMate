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

The active margin model preserves the current scoreboard and forecasts only the
remaining margin from pregame strength plus capped live evidence. H2H and
handicap share the same calibrated final-margin distribution.

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
from statistics import NormalDist
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

try:
    from scripts.afl_ht_totals_v3 import estimate_totals
except ModuleNotFoundError:
    from afl_ht_totals_v3 import estimate_totals

# ── Paths ─────────────────────────────────────────────────────────────────────
_ROOT        = Path(__file__).resolve().parent.parent
RESULTS_DIR  = _ROOT / "results"
HALFTIME_DIR = _ROOT / "data" / "afl" / "halfTime"

# ── Model constants ────────────────────────────────────────────────────────────
# Leave-one-season-out audit on 874 matches (2022-2026): the expected second-half
# margin retained 59.7%-63.7% of mapped pregame full-game strength. Current
# scoreboard points never regress away.
REMAINING_MARGIN_SHARE_AT_HT = 0.61

# Empirical second-half margin residual SD after pregame strength, n=874.
AFL_H2_MARGIN_RESIDUAL_SD = 23.93

# Retained only in legacy audit fields while forward comparisons mature. It no
# longer contributes to active H2H or handicap pricing.
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

# ── Stats-adjusted regression constants (v2, 2026-08-08) ─────────────────────
# Research basis:
#   AFL: I50 diff R=0.71 with margin (RStudio AFL analysis), turnovers "count
#        for double" (Wheatley 2018), clearances weakest big stat (~50% stoppage).
#        I50 + contested poss explain 55.2% of margin variance (R²).
#   NBA: Halftime stats predict winner at 84.1% accuracy (Adam et al, Springer 2024).
#        Shooting accuracy H1→H2 correlation = -0.007 (zero persistence, 12,486 shots).
#   AFL conversion: avg 51.4%, volume > accuracy for predicting wins (Wong, Medium).
#
# Process stats (persist H1→H2): I50 diff, clanger diff, clearance diff
# Outcome stats (regress to mean): goal accuracy, pts per I50 entry
#
# The stats-implied margin estimates what the score "should" be from process
# stats alone. The gap vs actual HT margin = luck surplus. This adjusts the
# Bayesian regression factor by ±REGRESSION_ADJUSTMENT_MAX.

# Weights for stats-implied margin (derived from AFL correlation research)
STATS_IMPLIED_I50_WEIGHT = 1.4        # I50 diff R=0.71, strongest non-scoring stat
STATS_IMPLIED_CLANGER_WEIGHT = -1.0   # turnovers count double (Wheatley 2018)
STATS_IMPLIED_CLEARANCE_WEIGHT = 0.5  # weakest big stat, ~50% stoppage base rate

# How much the regression factor can shift based on stats evidence
# Set at 7% based on cross-sport research synthesis (see handover 2026-08-08):
#   - Soccer xG convergence advantage = ~18% over actual goals → 0.45 × 18% ≈ 0.08
#   - Matter of Stats AFL: 0.07 = 29% of natural quarter-to-quarter weight variation (sensible)
#   - NBA close games: stats amplified in tight contests (Brier 0.18 vs 0.25 baseline)
#   - Upgrade path: move to 0.08-0.10 once 50+ live observations validate the weights
REGRESSION_ADJUSTMENT_MAX = 0.07

# Accuracy trend weight — how much of H1 accuracy carries into H2.
# Logic: if a team is kicking 70% in H1, project them to continue at 70% in H2.
# If kicking 40%, they'll continue at 40%. Trend persists, no regression to mean.
# H2 shot count estimated from H1 shots (same game pace).
# Each shot at accuracy `a` vs baseline `b` = 5*(a-b) pts difference per shot.
# Weight of 1.0 = full trend continuation. Reduce if you want partial regression.
# NOTE (calibration 2026-06-19): 875-game AFL backtest shows accuracy trend has near-zero
# historical predictive power (corr = -0.04 with H2 margin).
# UPDATE (2026-08-08): NBA research confirms — shooting accuracy H1→H2 correlation =
# -0.007 across 12,486 shots (Adam et al, Springer 2024). Accuracy is noise, not signal.
# Reduced from 1.0 to 0.15 — retains a small situational lens (wet/dry) without
# letting unsustainable accuracy dominate the price (was producing -38.5pt adjustments
# in stat-dominant-but-inaccurate scenarios, overwhelming all other model signals).
ACCURACY_TREND_WEIGHT = 0.0

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


# ── In-game injury detection (Fox Sports match centre) ───────────────────────
# At halftime, a full AFL quarter is ~30 mins, so ~55-60 mins of game clock have
# passed. Any player with minutes_played significantly below this threshold likely
# went off injured during the first half. We use a conservative cutoff.
#
# Threshold: if a player has played less than 40% of the maximum minutes_played
# on their team, they are flagged as a likely in-game injury. This handles
# variable game clocks and the interchange bench (who rotate but still accumulate
# ~70-80% of max minutes in a normal game).
INJURY_MINUTES_RATIO = 0.40

# Fox Sports position_code → T5 injury position mapping
FOX_POSITION_TO_T5 = {
    "RCK": "ruck",
    "CHF": "key_forward",
    "FF":  "key_forward",
    "HF":  "small_forward",
    "FP":  "small_forward",
    "FB":  "key_defender",
    "CHB": "key_defender",
    "HB":  "key_defender",
    "BP":  "key_defender",
    "CEN": "midfielder",
    "RR":  "midfielder",
    "ROV": "midfielder",
    "WNG": "winger",
    "INT": "utility",
}

# Default quality for in-game injuries — we can't assess quality live, so use
# 'good' as middle ground (not the conservative 'average' — if a player starts
# in the best 22, they're at least 'good' level at their position).
INGAME_INJURY_QUALITY = "good"

# T5 impact table (imported from the pre-game T5 module)
# Duplicated here to avoid circular imports and keep the HT script self-contained.
INGAME_IMPACT_TABLE = {
    ("key_forward",  "good"):    (-3.0, -2.0),
    ("key_forward",  "average"): (-2.0, -1.5),
    ("ruck",         "good"):    (-2.0, -1.0),
    ("ruck",         "average"): (-1.0, -0.5),
    ("key_defender", "good"):    (-1.5, +1.0),
    ("key_defender", "average"): (-0.5, +0.5),
    ("midfielder",   "good"):    (-1.5, -0.5),
    ("midfielder",   "average"): (-0.5, -0.5),
    ("small_forward","good"):    (-1.0, -0.5),
    ("small_forward","average"): (-0.5,  0.0),
    ("winger",       "good"):    (-1.0, -0.5),
    ("winger",       "average"): (-0.5,  0.0),
    ("utility",      "good"):    (-1.0, -0.5),
    ("utility",      "average"): (-0.5,  0.0),
}

# Cap on in-game injury handicap adjustment per team
INGAME_INJURY_CAP = 5.0


def _fetch_fox_player_stats(match_id: str) -> dict | None:
    """Fetch player stats from Fox Sports match centre.

    Returns dict with 'team_A' and 'team_B' player lists, or None on failure.
    match_id format: AFL{year}{round:02d}{game:02d}
    """
    try:
        import requests as _req
    except ImportError:
        print("  [injury] requests not installed — skipping Fox Sports scrape")
        return None

    url = f"https://www.foxsports.com.au/afl/match-centre/{match_id}/playerstats"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    }

    try:
        resp = _req.get(url, headers=headers, timeout=15)
        if resp.status_code != 200:
            print(f"  [injury] Fox Sports returned {resp.status_code} for {match_id}")
            return None
    except Exception as exc:
        print(f"  [injury] Fox Sports fetch failed: {exc}")
        return None

    # Extract the core-match-centre fisoBoot JSON from the page.
    # The JSON contains deeply nested braces so we find the assignment and
    # read to the next </script> tag, then strip the trailing semicolon.
    marker = "window.fisoBoot['core-match-centre']['"
    idx = resp.text.find(marker)
    if idx < 0:
        print("  [injury] Could not find match centre data in Fox Sports page")
        return None

    # Find the '=' after the key
    eq_idx = resp.text.find("]=", idx)
    if eq_idx < 0:
        print("  [injury] Could not find match centre data in Fox Sports page")
        return None
    json_start = eq_idx + 2

    # Find the closing </script>
    script_end = resp.text.find("</script>", json_start)
    if script_end < 0:
        print("  [injury] Could not find end of match centre data")
        return None

    json_text = resp.text[json_start:script_end].rstrip().rstrip(";")

    try:
        data = json.loads(json_text)
    except json.JSONDecodeError:
        print("  [injury] Failed to parse Fox Sports JSON")
        return None

    # Navigate to player stats widget
    try:
        widgets = data["hydration"]["page"]["content"]["widgets"]
        ps_key = [k for k in widgets if "playerStats" in k]
        if not ps_key:
            print("  [injury] No playerStats widget found")
            return None
        ps_data = widgets[ps_key[0]]["playerStats$"]
        return {
            "team_A": ps_data["team_A"],
            "team_B": ps_data["team_B"],
        }
    except (KeyError, TypeError) as exc:
        print(f"  [injury] Failed to navigate player stats: {exc}")
        return None


def detect_ingame_injuries(
    match_id: str,
    home_team: str,
    away_team: str,
) -> dict:
    """Detect players who likely went off injured during the first half.

    Returns {
        'home_injuries': [{'name': str, 'position': str, 'position_code': str,
                           'minutes': int, 'max_minutes': int}],
        'away_injuries': [...],
        'source': 'foxsports' | 'unavailable',
    }
    """
    result = {
        "home_injuries": [],
        "away_injuries": [],
        "source": "unavailable",
    }

    player_data = _fetch_fox_player_stats(match_id)
    if not player_data:
        return result

    result["source"] = "foxsports"

    for side, team_key, team_name in [
        ("home_injuries", "team_A", home_team),
        ("away_injuries", "team_B", away_team),
    ]:
        team = player_data[team_key]
        players = team.get("players", [])
        if not players:
            continue

        # Find the max minutes on this team — the benchmark for "full game"
        max_mins = max(
            (p.get("stats", {}).get("minutes_played", 0) for p in players),
            default=0,
        )
        if max_mins <= 0:
            continue

        threshold = max_mins * INJURY_MINUTES_RATIO

        for p in players:
            mins = p.get("stats", {}).get("minutes_played", 0)
            pos_code = p.get("position_code", "INT")
            position = p.get("position", "Unknown")

            # Skip interchange players — they naturally have fewer minutes
            # Only flag non-interchange players with very low minutes
            if pos_code == "INT":
                continue

            if mins < threshold:
                result[side].append({
                    "name": p.get("full_name", p.get("short_name", "Unknown")),
                    "position": position,
                    "position_code": pos_code,
                    "minutes": mins,
                    "max_minutes": max_mins,
                })

    return result


def _ingame_injury_adjustment(injuries: list[dict]) -> tuple[float, float]:
    """Calculate handicap and total adjustment for in-game injuries.

    Returns (handicap_adj, totals_adj) — both from the injured team's perspective
    (negative handicap = team weakened, negative total = fewer points expected).
    """
    if not injuries:
        return 0.0, 0.0

    total_hcap = 0.0
    total_tots = 0.0

    for inj in injuries:
        pos_code = inj.get("position_code", "INT")
        t5_pos = FOX_POSITION_TO_T5.get(pos_code, "utility")
        quality = INGAME_INJURY_QUALITY

        impact = INGAME_IMPACT_TABLE.get((t5_pos, quality))
        if not impact:
            impact = INGAME_IMPACT_TABLE.get((t5_pos, "average"), (-0.5, 0.0))

        total_hcap += impact[0]
        total_tots += impact[1]

    # Cap adjustments
    total_hcap = max(-INGAME_INJURY_CAP, total_hcap)
    total_tots = max(-INGAME_INJURY_CAP, min(INGAME_INJURY_CAP, total_tots))

    return total_hcap, total_tots


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


def margin_win_prob(expected_final_margin: float) -> dict[str, float]:
    """Price win/draw/loss from the calibrated remaining-margin uncertainty."""
    normal = NormalDist(mu=expected_final_margin, sigma=AFL_H2_MARGIN_RESIDUAL_SD)
    away = normal.cdf(-0.5)
    not_home = normal.cdf(0.5)
    draw = max(0.0, not_home - away)
    home = max(0.0001, 1.0 - not_home)
    away = max(0.0001, away)
    decisive = home + away
    return {
        "home_win": round(home / decisive, 4),
        "away_win": round(away / decisive, 4),
        "draw": round(draw, 4),
    }


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

    # Stats-adjusted regression (v2)
    stats_implied_margin: float
    stats_regression_adj: float
    regression_factor_used: float
    expected_remaining_pregame_margin: float
    margin_model_version: str
    margin_residual_sd: float

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

    # Active totals distribution audit
    totals_model_version: str = ""
    totals_score_state_h2_baseline: float = 0.0
    totals_pregame_h2_prior: float = 0.0
    totals_blended_h2_baseline: float = 0.0
    totals_process_adjustment: float = 0.0
    totals_fair_line: float = 0.0
    totals_distribution_sample_size: int = 0
    totals_feature_coverage: float = 0.0
    totals_quality: str = ""
    totals_adjustments: list[str] = field(default_factory=list)

    # In-game injuries (Fox Sports match centre)
    ingame_home_injuries: list[dict] = field(default_factory=list)
    ingame_away_injuries: list[dict] = field(default_factory=list)
    ingame_injury_source: str = "unavailable"
    ingame_injury_hcap_adj: float = 0.0
    ingame_injury_total_adj: float = 0.0

    # Signal
    signal_strength: str = ""
    signal_direction: str = ""
    signal_notes: list[str] = field(default_factory=list)


def price_halftime(stats: dict, pregame: dict | None, match_id: str | None = None) -> HalfTimePricingAFL:
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

        # Use primary (hybrid) model as prior, fallback to rules then ML
        pg_margin  = _safe_float(pregame.get("primary_margin", pregame.get("rules_margin", pregame.get("ml_margin", 0))))
        pg_total   = _safe_float(pregame.get("primary_total", pregame.get("rules_total", pregame.get("ml_total", 168.0))))
        pg_h_odds  = _safe_float(pregame.get("primary_home_odds", pregame.get("rules_home_odds", 2.0)))
        pg_a_odds  = _safe_float(pregame.get("primary_away_odds", pregame.get("rules_away_odds", 2.0)))
        pg_home_prob = (1 / pg_h_odds) if pg_h_odds > 1 else _safe_float(pregame.get("primary_home_prob", pregame.get("rules_home_prob", 0.5)))

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

    # ── Extract live stats early (needed for stats-implied regression) ───────
    home_i50 = stats.get("home_inside_50s")
    away_i50 = stats.get("away_inside_50s")
    home_clr = stats.get("home_clearances")
    away_clr = stats.get("away_clearances")
    home_clg = stats.get("home_clangers")
    away_clg = stats.get("away_clangers")

    have_stats = all(v is not None for v in [home_i50, away_i50, home_clr, away_clr, home_clg, away_clg])

    # ── Stats-implied margin (process stats only — persist H1→H2) ────────────
    # This estimates what the margin "should" be if outcome luck (accuracy) were
    # removed and only structural dominance remained.
    if have_stats:
        i50_diff     = home_i50 - away_i50
        clanger_diff = home_clg - away_clg   # positive = home has MORE clangers (bad)
        clear_diff   = home_clr - away_clr

        stats_implied_margin = (
            i50_diff     * STATS_IMPLIED_I50_WEIGHT +
            clanger_diff * STATS_IMPLIED_CLANGER_WEIGHT +
            clear_diff   * STATS_IMPLIED_CLEARANCE_WEIGHT
        )
    else:
        stats_implied_margin = 0.0
        i50_diff = clanger_diff = clear_diff = 0

    # ── Dynamic regression factor ─────────────────────────────────────────────
    # Compare stats evidence vs pre-game prior direction.
    # If stats back the pre-game favourite → trust the prior MORE (raise factor)
    # If stats oppose the pre-game favourite → trust live evidence MORE (lower factor)
    # Neutral/no-stats → default factor
    regression = REGRESSION_FACTOR
    stats_regression_adj = 0.0

    if have_stats and abs(stats_implied_margin) >= 2.0:
        # Do stats and prior agree on direction?
        stats_backs_prior = (
            (stats_implied_margin > 0 and pg_margin > 0) or
            (stats_implied_margin < 0 and pg_margin < 0)
        )

        # Scale adjustment by strength of stats signal (cap at ±MAX)
        signal_strength = min(abs(stats_implied_margin) / 15.0, 1.0)
        raw_adj = REGRESSION_ADJUSTMENT_MAX * signal_strength

        if stats_backs_prior:
            # Stats confirm the pre-game model — trust the prior more
            stats_regression_adj = raw_adj
        else:
            # Stats oppose the pre-game model — trust live evidence more
            stats_regression_adj = -raw_adj

        regression = max(0.20, min(0.65, REGRESSION_FACTOR + stats_regression_adj))

    # ── Remaining-margin update ───────────────────────────────────────────────
    # Preserve the points already scored. Only forecast the remaining half from
    # pregame strength; the 0.61 share is fitted out of sample on 2022-2026.
    expected_remaining_pregame = pg_margin * REMAINING_MARGIN_SHARE_AT_HT
    expected_final_margin = ht_margin + expected_remaining_pregame

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
    if have_stats:
        i50_adj      = (home_i50 - away_i50) * PTS_PER_I50_DIFF
        clearance_adj = (home_clr - away_clr) * PTS_PER_CLEARANCE_DIFF
        clanger_adj  = (away_clg - home_clg) * PTS_PER_CLANGER_DIFF
        stats_adj    = max(-STATS_ADJ_CAP, min(STATS_ADJ_CAP, i50_adj + clearance_adj + clanger_adj))
    else:
        i50_adj = clearance_adj = clanger_adj = stats_adj = 0.0

    # ── In-game injury detection ─────────────────────────────────────────────
    ingame_injury_hcap = 0.0
    ingame_injury_total = 0.0
    injury_data = {"home_injuries": [], "away_injuries": [], "source": "unavailable"}

    if match_id:
        injury_data = detect_ingame_injuries(match_id, home, away)
        if injury_data["home_injuries"] or injury_data["away_injuries"]:
            # Home injuries: weaken home team (negative hcap for home)
            home_hcap, home_tots = _ingame_injury_adjustment(injury_data["home_injuries"])
            # Away injuries: weaken away team (positive hcap for home perspective)
            away_hcap, away_tots = _ingame_injury_adjustment(injury_data["away_injuries"])

            # Net effect on home margin: home injuries hurt home, away injuries help home
            ingame_injury_hcap = home_hcap - away_hcap
            ingame_injury_total = home_tots + away_tots

    # ── Combined expected margin ───────────────────────────────────────────────
    ht_expected_margin = expected_final_margin + accuracy_adj + stats_adj + ingame_injury_hcap

    # ── Second half total estimate ─────────────────────────────────────────────
    totals_model = estimate_totals(stats, pg_total, ingame_injury_total)
    sh_total = totals_model.expected_second_half_total
    ht_expected_final_total = totals_model.expected_final_total

    # Split second half using the model's expected H2 scoring differential.
    # The model already calculated ht_expected_margin (final margin after all
    # adjustments). The expected H2 differential = expected_final - ht_margin.
    # This ensures the simulation is CONSISTENT with the model's own output —
    # if stats say Melbourne should be gaining ground, the H2 split reflects that.
    expected_h2_diff = ht_expected_margin - ht_margin
    sh_home = max(25.0, min(65.0, (sh_total + expected_h2_diff) / 2))
    sh_away = max(25.0, min(65.0, (sh_total - expected_h2_diff) / 2))

    # ── Price the same final-margin distribution ───────────────────────────────
    probs = margin_win_prob(ht_expected_margin)
    home_win_prob = probs["home_win"]
    away_win_prob = probs["away_win"]

    ht_home_odds = prob_to_odds(home_win_prob)
    ht_away_odds = prob_to_odds(away_win_prob)

    ht_hcap = round(-ht_expected_margin, 1)
    ht_total = round(totals_model.fair_final_total, 1)

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

    # In-game injury notes
    for inj in injury_data["home_injuries"]:
        t5_pos = FOX_POSITION_TO_T5.get(inj["position_code"], "utility")
        notes.append(
            f"IN-GAME INJURY: {home} — {inj['name']} ({inj['position']}) "
            f"only {inj['minutes']}min/{inj['max_minutes']}min max → {t5_pos} out"
        )
    for inj in injury_data["away_injuries"]:
        t5_pos = FOX_POSITION_TO_T5.get(inj["position_code"], "utility")
        notes.append(
            f"IN-GAME INJURY: {away} — {inj['name']} ({inj['position']}) "
            f"only {inj['minutes']}min/{inj['max_minutes']}min max → {t5_pos} out"
        )

    total_adj = accuracy_adj + stats_adj + ingame_injury_hcap
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
        stats_implied_margin=round(stats_implied_margin, 2),
        stats_regression_adj=round(stats_regression_adj, 4),
        regression_factor_used=round(regression, 4),
        expected_remaining_pregame_margin=round(expected_remaining_pregame, 2),
        margin_model_version="afl_ht_margin_v3_remaining_margin_distribution",
        margin_residual_sd=AFL_H2_MARGIN_RESIDUAL_SD,
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
        totals_model_version=totals_model.model_version,
        totals_score_state_h2_baseline=totals_model.score_state_h2_baseline,
        totals_pregame_h2_prior=totals_model.pregame_h2_prior,
        totals_blended_h2_baseline=totals_model.blended_h2_baseline,
        totals_process_adjustment=totals_model.process_adjustment,
        totals_fair_line=totals_model.fair_final_total,
        totals_distribution_sample_size=totals_model.distribution_sample_size,
        totals_feature_coverage=totals_model.feature_coverage,
        totals_quality=totals_model.quality,
        totals_adjustments=totals_model.adjustments,
        ingame_home_injuries=injury_data["home_injuries"],
        ingame_away_injuries=injury_data["away_injuries"],
        ingame_injury_source=injury_data["source"],
        ingame_injury_hcap_adj=round(ingame_injury_hcap, 2),
        ingame_injury_total_adj=round(ingame_injury_total, 2),
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
    print(f"\n  --- Legacy Regression Diagnostics (not active pricing) ---")
    print(f"  Stats-implied margin: {p.stats_implied_margin:+.1f} (process stats only)")
    if p.stats_regression_adj != 0:
        direction = "backs prior" if p.stats_regression_adj > 0 else "opposes prior"
        print(f"  Stats vs prior:       {direction} → regression {p.regression_factor_used:.2f} "
              f"(base {REGRESSION_FACTOR:.2f} {p.stats_regression_adj:+.4f})")
    else:
        print(f"  Regression factor:    {p.regression_factor_used:.2f} (default — stats neutral or unavailable)")
    # In-game injuries
    if p.ingame_injury_source == "foxsports":
        print(f"\n  --- In-Game Injuries (Fox Sports) ---")
        if p.ingame_home_injuries or p.ingame_away_injuries:
            for inj in p.ingame_home_injuries:
                t5 = FOX_POSITION_TO_T5.get(inj["position_code"], "utility")
                print(f"  {p.home_team:15s}  {inj['name']:25s} ({inj['position']:20s}) "
                      f"{inj['minutes']:3d}/{inj['max_minutes']:3d} min → {t5}")
            for inj in p.ingame_away_injuries:
                t5 = FOX_POSITION_TO_T5.get(inj["position_code"], "utility")
                print(f"  {p.away_team:15s}  {inj['name']:25s} ({inj['position']:20s}) "
                      f"{inj['minutes']:3d}/{inj['max_minutes']:3d} min → {t5}")
            print(f"  Injury hcap adj:  {p.ingame_injury_hcap_adj:+.1f} (home perspective)")
            print(f"  Injury total adj: {p.ingame_injury_total_adj:+.1f}")
        else:
            print(f"  No in-game injuries detected")
    else:
        print(f"\n  --- In-Game Injuries ---")
        print(f"  Fox Sports data unavailable (no match ID or fetch failed)")
    print(f"\n  --- Second Half Estimates ---")
    print(f"  2H expected total: {p.second_half_expected_total:.1f} pts")
    print(f"  2H home expected:  {p.second_half_home_expected:.1f} pts")
    print(f"  2H away expected:  {p.second_half_away_expected:.1f} pts")
    print(f"\n  --- Updated Prices ---")
    print(f"  Margin model:          {p.margin_model_version}")
    print(f"  Remaining prior:       {p.expected_remaining_pregame_margin:+.1f} "
          f"({REMAINING_MARGIN_SHARE_AT_HT:.0%} of pregame margin)")
    print(f"  Margin residual SD:    {p.margin_residual_sd:.1f}")
    print(f"  Expected final margin: {p.ht_expected_margin:+.1f} (home)")
    print(f"  Expected final total:  {p.ht_expected_final_total:.1f}")
    print(f"  Win prob:  {p.home_team} {p.ht_home_win_prob:.1%} / {p.away_team} {p.ht_away_win_prob:.1%}")
    print(f"  Fair odds: {p.home_team} {p.ht_home_odds} / {p.away_team} {p.ht_away_odds}")
    print(f"  HT Hcap:   {p.ht_hcap_line:+.1f} (home)")
    print(f"  HT Total:  {p.ht_total_line:.1f}")
    print(f"  Totals model: {p.totals_model_version} "
          f"({p.totals_quality}, coverage {p.totals_feature_coverage:.0%})")
    print(f"  Totals H2: bins {p.totals_score_state_h2_baseline:.1f} / "
          f"pregame {p.totals_pregame_h2_prior:.1f} / blended {p.totals_blended_h2_baseline:.1f}")
    print(f"  Totals live: {p.totals_process_adjustment:+.1f}; empirical "
          f"n={p.totals_distribution_sample_size}; fair line {p.totals_fair_line:.1f}")
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
    p = argparse.ArgumentParser(description="AFL half-time pricing model")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--file", type=Path, help="Path to half-time stats JSON")
    src.add_argument("--round", type=int, help="Auto-find latest HT stats for this round")
    src.add_argument("--live", action="store_true",
                     help="Fetch live HT scores from Squiggle + FootyWire stats, then price")
    p.add_argument("--home", type=str, help="Home team (with --round or --live)")
    p.add_argument("--away", type=str, help="Away team (with --round or --live)")
    p.add_argument("--match-id", type=str,
                   help="Fox Sports match ID (e.g. AFL20262203) for in-game injury scrape")
    p.add_argument("--game-num", type=int,
                   help="Game number within the round (1-9) — auto-builds match ID")
    p.add_argument("--save", action="store_true", help="Save pricing output to JSON")
    return p.parse_args()


def _fetch_live_stats() -> list[dict]:
    """Fetch all halftime games from Squiggle, enrich with FootyWire stats."""
    try:
        import requests as _req
    except ImportError:
        print("ERROR: requests not installed")
        return []

    # Import FootyWire enrichment from afl_ht_live
    try:
        from scripts.afl_ht_live import enrich_with_live_stats, extract_halftime_stats
    except ImportError:
        # Try relative import if run from BettingEngine root
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "afl_ht_live", _ROOT / "scripts" / "afl_ht_live.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        enrich_with_live_stats = mod.enrich_with_live_stats
        extract_halftime_stats = mod.extract_halftime_stats

    # Find current season/round from Squiggle
    from datetime import date
    year = date.today().year
    print(f"Fetching live AFL games from Squiggle ({year})...")

    # Try rounds 1-30 in reverse to find the current round with halftime games
    for rnd in range(30, 0, -1):
        url = f"https://api.squiggle.com.au/?q=games;year={year};round={rnd}"
        try:
            resp = _req.get(url, headers={
                "User-Agent": "BetMate/1.0 (elliot@betmate.au)"}, timeout=10)
            games = resp.json().get("games", [])
        except Exception:
            continue

        ht_games = [g for g in games if (g.get("complete") or 0) == 50]
        if ht_games:
            print(f"  Found {len(ht_games)} game(s) at halftime in Round {rnd}")
            results = []
            for g in ht_games:
                stats = extract_halftime_stats(g, year, rnd)
                stats = enrich_with_live_stats(stats)
                results.append(stats)
            return results

        # If this round has any games in progress or completed today, it's current
        today = date.today().isoformat()
        active = [g for g in games if str(g.get("date", ""))[:10] == today]
        if active:
            print(f"  Round {rnd} is today but no games at halftime right now")
            return []

    print("  No halftime games found")
    return []


def main() -> None:
    args = parse_args()

    if args.live:
        # Live mode: fetch from Squiggle + FootyWire, price all HT games
        all_stats = _fetch_live_stats()
        if not all_stats:
            print("No games at halftime right now.")
            return

        # Filter to specific game if --home/--away given
        if args.home and args.away:
            h, a = args.home.lower(), args.away.lower()
            filtered = [s for s in all_stats
                        if h in s["home_team"].lower() or s["home_team"].lower().split()[-1] in h
                        if a in s["away_team"].lower() or s["away_team"].lower().split()[-1] in a]
            if filtered:
                all_stats = filtered

        for stats in all_stats:
            pregame = load_pregame_row(stats["home_team"], stats["away_team"])

            match_id = args.match_id
            if not match_id and args.game_num:
                match_id = f"AFL{stats.get('season', 2026)}{stats.get('round', 0):02d}{args.game_num:02d}"

            pricing = price_halftime(stats, pregame, match_id=match_id)
            print_pricing(pricing)

            if args.save:
                round_dir = HALFTIME_DIR / f"R{stats['round']:02d}"
                round_dir.mkdir(parents=True, exist_ok=True)
                home_nick = stats["home_team"].split()[-1].lower()
                away_nick = stats["away_team"].split()[-1].lower()
                game_date = stats.get("game_date", datetime.now().strftime("%Y-%m-%d"))
                out_path = round_dir / f"{game_date}_{home_nick}_vs_{away_nick}_pricing.json"
                out_path.write_text(
                    json.dumps(asdict(pricing), indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
                print(f"Saved pricing → {out_path}")
        return

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

    # Build Fox Sports match ID for in-game injury scrape
    match_id = getattr(args, "match_id", None)
    if not match_id and getattr(args, "game_num", None):
        season = stats.get("season", 2026)
        rnd = stats.get("round", 0)
        match_id = f"AFL{season}{rnd:02d}{args.game_num:02d}"
    if not match_id:
        # Try to read from stats JSON (footywire_mid or match_id field)
        match_id = stats.get("fox_match_id")

    if match_id:
        print(f"Fox Sports match ID: {match_id}")

    pricing = price_halftime(stats, pregame, match_id=match_id)
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
