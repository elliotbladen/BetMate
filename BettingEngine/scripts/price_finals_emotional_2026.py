#!/usr/bin/env python3
"""
scripts/price_finals_emotional_2026.py

Emotional tier for the 2026 finals — NRL Finals Week 1 (T7) and AFL Semi Finals (T6).

Calls the production tier functions:
    pricing.tier7_emotional.compute_emotional_adjustments  (NRL, config/tiers.yaml)
    pricing.afl_tier6_emotional.compute_t6                 (AFL, AFL_T6_CONFIG)

Nothing is hand-calculated: every number below comes out of those functions.

FLAG EVIDENCE
-------------
Each flag records why it fired. Flags that were considered and REJECTED are
listed in REJECTED so the audit trail shows what was deliberately not applied.

Run:  python3 scripts/price_finals_emotional_2026.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pricing.tier7_emotional import compute_emotional_adjustments
from pricing.afl_tier6_emotional import compute_t6

NRL_T7_CONFIG = yaml.safe_load((ROOT / "config/tiers.yaml").read_text())["tier7_emotional"]


def flag(ftype: str, strength: str = "normal", player: str | None = None, notes: str = "") -> dict:
    return {"flag_type": ftype, "flag_strength": strength, "player_name": player, "notes": notes}


# ── NRL Finals Week 1 ────────────────────────────────────────────────────────
# must_win applied ONLY to sudden-death elimination finals. Qualifying finals
# carry a double chance, so the desperation premium does not apply there.
NRL_GAMES = [
    {
        "label": "QF1", "home": "Penrith Panthers", "away": "Sydney Roosters",
        "home_flags": [],
        "away_flags": [flag("shame_blowout", "normal",
                            notes="Lost 20-50 to Souths in R27 = exactly 30 pts, meets the 30+ NRL threshold")],
    },
    {
        "label": "QF2", "home": "New Zealand Warriors", "away": "Dolphins",
        "home_flags": [], "away_flags": [],
    },
    {
        "label": "EF1", "home": "Cronulla Sharks", "away": "North QLD Cowboys",
        "home_flags": [flag("must_win", "normal", notes="Sudden-death elimination final")],
        "away_flags": [flag("must_win", "normal", notes="Sudden-death elimination final")],
    },
    {
        "label": "EF2", "home": "South Sydney Rabbitohs", "away": "Newcastle Knights",
        "home_flags": [flag("must_win", "normal", notes="Sudden-death elimination final")],
        "away_flags": [flag("must_win", "normal", notes="Sudden-death elimination final")],
    },
]

# ── AFL Semi Finals ──────────────────────────────────────────────────────────
AFL_GAMES = [
    {
        "label": "SF1", "home": "Fremantle Dockers", "away": "Geelong Cats",
        "home_flags": [flag("must_win", "normal", notes="Sudden-death semi final")],
        "away_flags": [flag("must_win", "normal", notes="Sudden-death semi final")],
    },
    {
        "label": "SF2", "home": "Brisbane Lions", "away": "Adelaide Crows",
        "home_flags": [flag("must_win", "normal", notes="Sudden-death semi final")],
        "away_flags": [flag("must_win", "normal", notes="Sudden-death semi final")],
    },
]

REJECTED = [
    ("NRL EF1", "North QLD Cowboys", "shame_blowout",
     "Lost by 20 to Canberra in R27. NRL threshold is 30+. WAS APPLIED in the 6 Sep run — invalid."),
    ("NRL EF2", "South Sydney Rabbitohs", "star_return (Latrell Mitchell)",
     "Latrell returned in R27 and scored in the 50-20 win. This is not his return game. "
     "WAS APPLIED in the 6 Sep run — stale by one round."),
    ("NRL EF2", "South Sydney Rabbitohs", "personal_tragedy (Jai Arrow)",
     "Arrow's forced retirement is genuine adversity, but his 100th/final game was R27. "
     "Peak emotional event has passed; config rates this flag's evidence quality as 'None'. Left neutral."),
    ("NRL QF2", "Dolphins", "star_return (Cobbo, Nikorima)",
     "Both were RESTED in R27, not returning from a long absence. Does not meet the flag definition."),
    ("AFL SF1", "Fremantle Dockers", "shame_blowout",
     "Lost QF by 32. AFL threshold is 60+ (10 goals). Deliberately not applied."),
    ("AFL SF2", "Brisbane Lions", "shame_blowout",
     "Lost QF by 53. Under the 60+ AFL threshold despite the poor performance narrative."),
    ("AFL SF1", "Fremantle Dockers", "star_return (Sean Darcy)",
     "Recalled for the semi, but absent from the current injury list and no verifiable 6+ week "
     "injury absence. Selection recall, not a star return."),
]


def run() -> None:
    print("=" * 78)
    print("NRL FINALS WEEK 1 — TIER 7 EMOTIONAL   (config/tiers.yaml :: tier7_emotional)")
    print("=" * 78)
    print(f"{'Game':<6}{'Home':<24}{'Away':<24}{'T7 hcp':>8}{'T7 tot':>8}")
    nrl_out = []
    for g in NRL_GAMES:
        r = compute_emotional_adjustments(g["home_flags"], g["away_flags"], NRL_T7_CONFIG)
        nrl_out.append((g, r))
        print(f"{g['label']:<6}{g['home']:<24}{g['away']:<24}"
              f"{r['handicap_delta']:>+8.2f}{r['totals_delta']:>+8.2f}")
    print("\n(positive handicap = home emotional edge)")

    print()
    print("=" * 78)
    print("AFL SEMI FINALS — TIER 6 EMOTIONAL   (pricing/afl_tier6_emotional.AFL_T6_CONFIG)")
    print("=" * 78)
    print(f"{'Game':<6}{'Home':<24}{'Away':<24}{'T6 hcp':>8}{'T6 tot':>8}")
    afl_out = []
    for g in AFL_GAMES:
        r = compute_t6(g["home_flags"], g["away_flags"])
        afl_out.append((g, r))
        print(f"{g['label']:<6}{g['home']:<24}{g['away']:<24}"
              f"{r['t6_handicap']:>+8.2f}{r['t6_totals']:>+8.2f}")

    print()
    print("=" * 78)
    print("FLAGS FIRED")
    print("=" * 78)
    for g, _ in nrl_out + afl_out:
        fired = [(g["home"], f) for f in g["home_flags"]] + [(g["away"], f) for f in g["away_flags"]]
        if not fired:
            print(f"  {g['label']}: none")
            continue
        for team, f in fired:
            print(f"  {g['label']} {team:<24} {f['flag_type']:<17} ({f['flag_strength']}) — {f['notes']}")

    print()
    print("=" * 78)
    print("CONSIDERED AND REJECTED")
    print("=" * 78)
    for game, team, ftype, why in REJECTED:
        print(f"  {game} {team} — {ftype}\n      {why}")


if __name__ == "__main__":
    run()
