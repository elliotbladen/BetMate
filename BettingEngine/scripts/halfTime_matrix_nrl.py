#!/usr/bin/env python3
"""
BettingEngine/scripts/halfTime_matrix_nrl.py

NRL Half-Time Anomaly Matrix.

Scores each game at half time across 5 anomaly signals.
When multiple signals align in the same direction, flags a confluence.
Output mirrors the T9 pre-game matrix — same pattern, different timing.

Anomaly signals:
  1. ETxP Divergence    — inside-20 possessions vs actual score (strongest)
  2. Error Rate         — error differential vs league average
  3. Restart Inflation  — first-half restarts won't continue in second half
  4. Conversion Luck    — missed conversions are random, will regress
  5. Pre-game Prior     — does the scoreline align with or contradict the model?

Composite score >= 6: strong signal (multiple anomalies align)
Composite score 3-5:  moderate signal
Composite score < 3:  noise / neutral

Usage:
    python scripts/halfTime_matrix_nrl.py --round 14
    python scripts/halfTime_matrix_nrl.py --file path/to/stats.json
    python scripts/halfTime_matrix_nrl.py --round 14 --push   # push to Supabase
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
ENGINE_ROOT  = Path(__file__).resolve().parent.parent
BETMATE_ROOT = Path(os.environ.get("BETMATE_ROOT", ENGINE_ROOT.parent))
HALFTIME_DIR = BETMATE_ROOT / "data" / "nrl" / "halfTime"
OUTPUT_JSON  = ENGINE_ROOT / "outputs" / "nrl_halftime_matrix_latest.json"

# Supabase key for push
SUPABASE_KEY = "nrl_halftime_matrix"

# ── Thresholds (calibrate once 50+ observations collected) ───────────────────
ETXP_PTS_PER_POSSESSION    = 0.80   # expected points per inside-20 possession
ETXP_SIGNAL_THRESHOLD      = 6.0    # ETxP divergence (pts) to flag as signal
ETXP_STRONG_THRESHOLD      = 10.0

NRL_AVG_ERRORS_PER_40MIN   = 5.5    # league average errors per team per half
ERROR_SIGNAL_THRESHOLD     = 2      # extra errors vs average to flag
ERROR_STRONG_THRESHOLD     = 4

RESTART_SIGNAL_THRESHOLD   = 3      # restart advantage to flag
RESTART_STRONG_THRESHOLD   = 5

CONVERSION_MISS_THRESHOLD  = 2      # missed conversions to flag (2 pts each = 4 pts owed)
BASELINE_CONVERSION_RATE   = 0.75

PREGAME_CONTRADICTION_PTS  = 8.0    # pre-game vs HT score divergence to flag

# ── Signal weights for composite score ────────────────────────────────────────
SIGNAL_WEIGHTS = {
    "etxp":        3,   # strongest — field position is real
    "error":       2,   # strong — errors predict scoring
    "restart":     2,   # strong — restarts don't continue in 2H
    "conversion":  1,   # moderate — luck signal
    "pregame":     1,   # tiebreaker — model says something different
}


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class AnomalySignal:
    name: str
    direction: str          # "HOME" | "AWAY" | "NEUTRAL"
    weight: int
    magnitude: float
    description: str


@dataclass
class HalfTimeAnomaly:
    home_team: str
    away_team: str
    season: int
    round: int
    game_date: str
    analysed_at: str
    ht_score: str           # e.g. "12-6"
    ht_margin: int

    signals: list[AnomalySignal]
    composite_score: float
    composite_direction: str    # "HOME" | "AWAY" | "NEUTRAL"
    strength: str               # "STRONG" | "MODERATE" | "WEAK" | "NEUTRAL"

    # Human-readable summary
    headline: str
    notes: list[str]


# ── Individual signal detectors ───────────────────────────────────────────────

def signal_etxp(stats: dict) -> AnomalySignal:
    """
    ETxP Divergence: inside-20 possessions vs actual score.
    Strong field position dominance not reflected in score = anomaly.
    """
    home_in20 = stats.get("home_inside_20_possessions", 0)
    away_in20 = stats.get("away_inside_20_possessions", 0)
    home_score = stats.get("home_ht_score", 0)
    away_score = stats.get("away_ht_score", 0)

    etxp_home = home_in20 * ETXP_PTS_PER_POSSESSION
    etxp_away = away_in20 * ETXP_PTS_PER_POSSESSION
    etxp_diff = etxp_home - etxp_away          # positive = home "deserves" more
    actual_diff = home_score - away_score
    divergence = etxp_diff - actual_diff        # positive = home underperforming score

    if home_in20 == 0 and away_in20 == 0:
        return AnomalySignal("etxp", "NEUTRAL", SIGNAL_WEIGHTS["etxp"], 0, "No inside-20 data provided.")

    if abs(divergence) < ETXP_SIGNAL_THRESHOLD:
        return AnomalySignal(
            "etxp", "NEUTRAL", SIGNAL_WEIGHTS["etxp"], abs(divergence),
            f"ETxP divergence {divergence:+.1f} pts — within noise threshold.",
        )

    direction = "HOME" if divergence > 0 else "AWAY"
    beneficiary = stats["home_team"] if divergence > 0 else stats["away_team"]
    strength_desc = "STRONG" if abs(divergence) >= ETXP_STRONG_THRESHOLD else "moderate"

    return AnomalySignal(
        "etxp", direction, SIGNAL_WEIGHTS["etxp"], abs(divergence),
        f"ETxP {strength_desc}: {beneficiary} field position exceeds score by {abs(divergence):.1f} pts "
        f"(inside-20: {home_in20} vs {away_in20}, score: {home_score}-{away_score}).",
    )


def signal_error(stats: dict) -> AnomalySignal:
    """
    Error rate anomaly: team making many more errors than average.
    High-error team tends to regress (give fewer errors in 2H).
    """
    home_errors = stats.get("home_errors", 0)
    away_errors = stats.get("away_errors", 0)

    if home_errors == 0 and away_errors == 0:
        return AnomalySignal("error", "NEUTRAL", SIGNAL_WEIGHTS["error"], 0, "No error data provided.")

    error_diff = away_errors - home_errors  # positive = away had more errors (good for home)

    if abs(error_diff) < ERROR_SIGNAL_THRESHOLD:
        return AnomalySignal(
            "error", "NEUTRAL", SIGNAL_WEIGHTS["error"], abs(error_diff),
            f"Error differential {error_diff:+d} — within noise ({home_errors} vs {away_errors}).",
        )

    direction = "HOME" if error_diff > 0 else "AWAY"
    # Identify which team had excess errors
    if error_diff > 0:
        culprit = stats["away_team"]
        excess = away_errors - NRL_AVG_ERRORS_PER_40MIN
    else:
        culprit = stats["home_team"]
        excess = home_errors - NRL_AVG_ERRORS_PER_40MIN

    strength_desc = "STRONG" if abs(error_diff) >= ERROR_STRONG_THRESHOLD else "moderate"

    return AnomalySignal(
        "error", direction, SIGNAL_WEIGHTS["error"], abs(error_diff),
        f"Error {strength_desc}: {culprit} made {abs(error_diff)} more errors than opponent "
        f"({home_errors} vs {away_errors}, avg {NRL_AVG_ERRORS_PER_40MIN:.1f}/half). "
        f"Expect partial regression in 2H.",
    )


def signal_restart(stats: dict) -> AnomalySignal:
    """
    Set restart inflation: restarts drop from 3.6 → 0.5 in second half.
    First-half restart advantages won't be repeated.
    """
    home_restarts = stats.get("home_set_restarts_received", 0)
    away_restarts = stats.get("away_set_restarts_received", 0)

    if home_restarts == 0 and away_restarts == 0:
        return AnomalySignal("restart", "NEUTRAL", SIGNAL_WEIGHTS["restart"], 0, "No restart data provided.")

    restart_diff = home_restarts - away_restarts  # positive = home benefited

    if abs(restart_diff) < RESTART_SIGNAL_THRESHOLD:
        return AnomalySignal(
            "restart", "NEUTRAL", SIGNAL_WEIGHTS["restart"], abs(restart_diff),
            f"Restart differential {restart_diff:+d} — within noise.",
        )

    # The BENEFICIARY's lead is inflated — signal points to OTHER team recovering
    direction = "AWAY" if restart_diff > 0 else "HOME"
    inflated = stats["home_team"] if restart_diff > 0 else stats["away_team"]
    strength_desc = "STRONG" if abs(restart_diff) >= RESTART_STRONG_THRESHOLD else "moderate"

    return AnomalySignal(
        "restart", direction, SIGNAL_WEIGHTS["restart"], abs(restart_diff),
        f"Restart {strength_desc}: {inflated} benefited from {abs(restart_diff)} more set restarts in 1H "
        f"({home_restarts} vs {away_restarts}). 2H averages only 0.5 restarts total — this advantage evaporates.",
    )


def signal_conversion(stats: dict) -> AnomalySignal:
    """
    Conversion luck: missed conversions are random and will regress.
    Team that missed multiple conversions is trailing by more than they 'deserve'.
    """
    home_tries = stats.get("home_tries", 0)
    away_tries = stats.get("away_tries", 0)
    home_conv  = stats.get("home_conversions_made", 0)
    away_conv  = stats.get("away_conversions_made", 0)

    if home_tries == 0 and away_tries == 0:
        return AnomalySignal("conversion", "NEUTRAL", SIGNAL_WEIGHTS["conversion"], 0, "No try/conversion data provided.")

    home_expected = home_tries * BASELINE_CONVERSION_RATE
    away_expected = away_tries * BASELINE_CONVERSION_RATE
    home_missed = home_expected - home_conv   # positive = home missed more than expected
    away_missed = away_expected - away_conv

    net_missed_diff = home_missed - away_missed   # positive = home was unluckier

    if abs(net_missed_diff) < 0.9:   # ~1 conversion miss difference
        return AnomalySignal(
            "conversion", "NEUTRAL", SIGNAL_WEIGHTS["conversion"], abs(net_missed_diff),
            f"Conversion: H {home_conv}/{home_tries} tries, A {away_conv}/{away_tries} tries — within noise.",
        )

    if abs(home_missed) >= CONVERSION_MISS_THRESHOLD and home_missed > away_missed:
        unlucky = stats["home_team"]
        pts_owed = home_missed * 2
        direction = "HOME"
    elif abs(away_missed) >= CONVERSION_MISS_THRESHOLD and away_missed > home_missed:
        unlucky = stats["away_team"]
        pts_owed = away_missed * 2
        direction = "AWAY"
    else:
        return AnomalySignal(
            "conversion", "NEUTRAL", SIGNAL_WEIGHTS["conversion"], abs(net_missed_diff),
            f"Conversion differential small — neutral.",
        )

    return AnomalySignal(
        "conversion", direction, SIGNAL_WEIGHTS["conversion"], pts_owed,
        f"Conversion luck: {unlucky} 'owed' ~{pts_owed:.0f} pts from missed conversions "
        f"(scored {home_conv if direction == 'HOME' else away_conv}/"
        f"{home_tries if direction == 'HOME' else away_tries} tries). "
        f"Scoreline understates their actual performance.",
    )


def signal_pregame(stats: dict, pregame: dict | None) -> AnomalySignal:
    """
    Pre-game contradiction: does the HT score agree or disagree with the model?
    Model had them winning by 7, trailing by 6 = 13-point divergence = flag.
    """
    if not pregame:
        return AnomalySignal("pregame", "NEUTRAL", SIGNAL_WEIGHTS["pregame"], 0, "No pre-game data.")

    try:
        pg_hcap = float(pregame.get("fair_hcap_line", 0))
    except (TypeError, ValueError):
        return AnomalySignal("pregame", "NEUTRAL", SIGNAL_WEIGHTS["pregame"], 0, "Pre-game hcap unreadable.")

    ht_margin = stats.get("home_ht_score", 0) - stats.get("away_ht_score", 0)
    # The expected HT margin is roughly half the pre-game margin (games are roughly even per half)
    expected_ht_margin = pg_hcap / 2
    divergence = ht_margin - expected_ht_margin   # positive = home overperforming model

    if abs(divergence) < PREGAME_CONTRADICTION_PTS:
        return AnomalySignal(
            "pregame", "NEUTRAL", SIGNAL_WEIGHTS["pregame"], abs(divergence),
            f"Pre-game: HT margin {ht_margin:+d} vs expected ~{expected_ht_margin:+.1f} — in range.",
        )

    # Home is overperforming → model says AWAY will recover
    direction = "AWAY" if divergence > 0 else "HOME"
    overdog = stats["home_team"] if divergence > 0 else stats["away_team"]

    return AnomalySignal(
        "pregame", direction, SIGNAL_WEIGHTS["pregame"], abs(divergence),
        f"Pre-game contradiction: {overdog} leads by {abs(divergence):.1f} pts more than model expected "
        f"(model hcap {pg_hcap:+.1f}, HT margin {ht_margin:+d}). Model says regression likely.",
    )


# ── Composite scoring ─────────────────────────────────────────────────────────

def composite(signals: list[AnomalySignal]) -> tuple[float, str]:
    """
    Score signals toward HOME or AWAY.
    Returns (composite_score, direction).
    """
    home_score = sum(s.weight for s in signals if s.direction == "HOME")
    away_score = sum(s.weight for s in signals if s.direction == "AWAY")

    if home_score > away_score:
        return home_score, "HOME"
    elif away_score > home_score:
        return away_score, "AWAY"
    else:
        return max(home_score, away_score), "NEUTRAL"


def classify_strength(score: float) -> str:
    if score >= 6:
        return "STRONG"
    elif score >= 3:
        return "MODERATE"
    elif score >= 2:
        return "WEAK"
    return "NEUTRAL"


# ── Main analysis function ────────────────────────────────────────────────────

def analyse(stats: dict, pregame: dict | None = None) -> HalfTimeAnomaly:
    """Run all signals and produce the composite anomaly result."""
    home = stats["home_team"]
    away = stats["away_team"]
    ht_home = stats.get("home_ht_score", 0)
    ht_away = stats.get("away_ht_score", 0)
    ht_margin = ht_home - ht_away

    signals = [
        signal_etxp(stats),
        signal_error(stats),
        signal_restart(stats),
        signal_conversion(stats),
        signal_pregame(stats, pregame),
    ]

    score, direction = composite(signals)
    strength = classify_strength(score)

    # Build notes list (only actionable signals)
    notes = [s.description for s in signals if s.direction != "NEUTRAL"]

    # Headline
    if strength == "NEUTRAL":
        headline = f"No significant anomalies — scoreline reflects game state."
    else:
        beneficiary = home if direction == "HOME" else away
        laggard = away if direction == "HOME" else home
        headline = (
            f"{strength} anomaly signal — {beneficiary} looks better than {ht_home}-{ht_away} suggests. "
            f"Second half may favour {beneficiary}."
        )

    return HalfTimeAnomaly(
        home_team=home,
        away_team=away,
        season=stats["season"],
        round=stats["round"],
        game_date=stats.get("game_date", ""),
        analysed_at=datetime.now(timezone.utc).isoformat(),
        ht_score=f"{ht_home}-{ht_away}",
        ht_margin=ht_margin,
        signals=signals,
        composite_score=score,
        composite_direction=direction,
        strength=strength,
        headline=headline,
        notes=notes,
    )


def print_anomaly(a: HalfTimeAnomaly) -> None:
    badge = {"STRONG": "⚡⚡⚡", "MODERATE": "⚡⚡", "WEAK": "⚡", "NEUTRAL": "—"}
    print(f"\n{'='*65}")
    print(f"HALF-TIME ANOMALY MATRIX  {badge.get(a.strength, '')}  {a.strength}")
    print(f"{a.home_team} vs {a.away_team}  |  HT: {a.ht_score}  |  R{a.round} {a.season}")
    print(f"{'='*65}")
    print(f"\n  {a.headline}\n")
    print(f"  Composite score: {a.composite_score:.0f}  Direction: {a.composite_direction}")
    print(f"\n  --- Individual Signals ---")
    for s in a.signals:
        arrow = "HOME ▲" if s.direction == "HOME" else ("AWAY ▲" if s.direction == "AWAY" else "  —  ")
        print(f"  [{s.name.upper():12s}] {arrow}  wt={s.weight}  mag={s.magnitude:.1f}")
        print(f"    {s.description}")
    print(f"{'='*65}\n")


# ── Supabase push ─────────────────────────────────────────────────────────────

def push_to_supabase(anomalies: list[HalfTimeAnomaly]) -> None:
    try:
        sys.path.insert(0, str(ENGINE_ROOT))
        from utils.supabase_push import push as _sb_push, load_env as _load_env
        _load_env()
        payload = [asdict(a) for a in anomalies]
        _sb_push(SUPABASE_KEY, {"games": payload, "generated_at": datetime.now(timezone.utc).isoformat()})
        print(f"Pushed {len(anomalies)} anomalies → Supabase key '{SUPABASE_KEY}'")
    except Exception as exc:
        print(f"Supabase push failed: {exc}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def load_pregame_for(home: str, away: str) -> dict | None:
    """Load pre-game pricing row. Reuses halfTime_price_nrl logic."""
    try:
        sys.path.insert(0, str(ENGINE_ROOT / "scripts"))
        from halfTime_price_nrl import load_pregame_row
        return load_pregame_row(home, away)
    except ImportError:
        return None


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="NRL half-time anomaly matrix")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--file",  type=Path, help="Path to a single HT stats JSON")
    src.add_argument("--round", type=int,  help="Process all HT stats for this round")
    p.add_argument("--push",   action="store_true", help="Push results to Supabase")
    p.add_argument("--save",   action="store_true", help="Save output JSON locally")
    return p.parse_args()


def files_for_round(round_num: int) -> list[Path]:
    round_dir = HALFTIME_DIR / f"R{round_num:02d}"
    if not round_dir.exists():
        return []
    # Exclude pricing files — only stats files
    return [f for f in round_dir.glob("*.json") if "_pricing" not in f.name]


def main() -> None:
    args = parse_args()
    anomalies: list[HalfTimeAnomaly] = []

    if args.file:
        paths = [args.file]
    else:
        paths = files_for_round(args.round)
        if not paths:
            print(f"No half-time stats found for round {args.round}.")
            print(f"Run scrapers/nrl_halftime_stats.py --round {args.round} --manual first.")
            return

    for path in paths:
        stats = json.loads(path.read_text(encoding="utf-8"))
        pregame = load_pregame_for(stats["home_team"], stats["away_team"])
        anomaly = analyse(stats, pregame)
        print_anomaly(anomaly)
        anomalies.append(anomaly)

    if args.save or args.push:
        OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_JSON.write_text(
            json.dumps(
                {"generated_at": datetime.now(timezone.utc).isoformat(),
                 "games": [asdict(a) for a in anomalies]},
                indent=2, ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        print(f"Saved → {OUTPUT_JSON}")

    if args.push:
        push_to_supabase(anomalies)

    # Summary
    flagged = [a for a in anomalies if a.strength in ("STRONG", "MODERATE")]
    if flagged:
        print(f"\n{'='*40}")
        print(f"FLAGGED GAMES ({len(flagged)})")
        for a in flagged:
            print(f"  {a.strength:8s}  {a.composite_direction}  {a.home_team} vs {a.away_team}  HT:{a.ht_score}")
        print(f"{'='*40}\n")


if __name__ == "__main__":
    main()
