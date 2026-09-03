#!/usr/bin/env python3
"""Price official NRL Round 27 (3-6 September 2026).

This deliberately reuses the production seven-tier implementation in
price_round27_2026.py, replacing its stale official-R26 snapshot with the
completed R26 results, official R27 fixture, team-list availability and refs.
"""
from __future__ import annotations

import csv
from pathlib import Path

import price_round27_2026 as model

ROOT = Path(__file__).resolve().parent.parent

R26 = [
    (26, "2026-08-27", "Brisbane Broncos", 20, "Melbourne Storm", 46),
    (26, "2026-08-28", "Manly-Warringah Sea Eagles", 44, "St. George Illawarra Dragons", 10),
    (26, "2026-08-28", "Penrith Panthers", 24, "Canterbury-Bankstown Bulldogs", 10),
    (26, "2026-08-29", "Gold Coast Titans", 22, "South Sydney Rabbitohs", 42),
    (26, "2026-08-29", "Sydney Roosters", 12, "Dolphins", 26),
    (26, "2026-08-29", "North Queensland Cowboys", 24, "Wests Tigers", 10),
    (26, "2026-08-30", "New Zealand Warriors", 46, "Newcastle Knights", 32),
    (26, "2026-08-30", "Parramatta Eels", 38, "Cronulla-Sutherland Sharks", 18),
]
for rnd, dt, home, hs, away, aws in R26:
    model.MATCHES.append({"round": rnd, "match_date": dt, "home_team": home,
                          "home_score": hs, "away_team": away, "away_score": aws})

# Official ladder order entering R27. W/L/PF/PA are rebuilt from played games;
# ladder position retains bye points and is therefore supplied explicitly.
POSITIONS = {
    "Penrith Panthers": 1, "New Zealand Warriors": 2, "Dolphins": 3,
    "Sydney Roosters": 4, "Cronulla-Sutherland Sharks": 5,
    "South Sydney Rabbitohs": 6, "Newcastle Knights": 7,
    "North Queensland Cowboys": 8, "Manly-Warringah Sea Eagles": 9,
    "Canterbury-Bankstown Bulldogs": 10, "Melbourne Storm": 11,
    "Canberra Raiders": 12, "Parramatta Eels": 13, "Brisbane Broncos": 14,
    "Wests Tigers": 15, "Gold Coast Titans": 16,
    "St. George Illawarra Dragons": 17,
}


def rebuild_ladder():
    out = {}
    for team, pos in POSITIONS.items():
        games = [m for m in model.MATCHES if team in (m["home_team"], m["away_team"])]
        wins = sum((m["home_team"] == team and m["home_score"] > m["away_score"]) or
                   (m["away_team"] == team and m["away_score"] > m["home_score"])
                   for m in games)
        pf = sum(m["home_score"] if m["home_team"] == team else m["away_score"] for m in games)
        pa = sum(m["away_score"] if m["home_team"] == team else m["home_score"] for m in games)
        out[team] = (len(games), wins, len(games) - wins, pf, pa, pos)
    return out


model.LADDER = rebuild_ladder()
model.ELO = model.compute_elo(model.MATCHES)
model.T2_HOME_CAP = 3.0
model.T2_AWAY_CAP = 3.0
model.T2_NET_CAP = 3.0
model.T2_DIRECTIONAL_CAP = True

model.VENUE_COORD.update({
    "Accor Stadium": (-33.8472, 151.0634),
    "Ocean Protect Stadium": (-34.0381, 151.1416),
    "WIN Stadium": (-34.4278, 150.8931),
})
model.TEAM_BASE["Canberra Raiders"] = (-35.2809, 149.1300)
model.FIXTURE = [
    ("Canterbury-Bankstown Bulldogs", "Brisbane Broncos", "Accor Stadium", "2026-09-03"),
    ("Gold Coast Titans", "Dolphins", "Cbus Super Stadium", "2026-09-04"),
    ("South Sydney Rabbitohs", "Sydney Roosters", "Allianz Stadium", "2026-09-04"),
    ("New Zealand Warriors", "Manly-Warringah Sea Eagles", "Go Media Stadium", "2026-09-05"),
    ("North Queensland Cowboys", "Canberra Raiders", "Queensland Country Bank Stadium", "2026-09-05"),
    ("Cronulla-Sutherland Sharks", "Melbourne Storm", "Ocean Protect Stadium", "2026-09-05"),
    ("St. George Illawarra Dragons", "Parramatta Eels", "WIN Stadium", "2026-09-06"),
    ("Penrith Panthers", "Wests Tigers", "CommBank Stadium", "2026-09-06"),
]
model.REF_ASSIGNMENT = {
    ("Canterbury-Bankstown Bulldogs", "Brisbane Broncos"): "Grant Atkins",
    ("Gold Coast Titans", "Dolphins"): "Wyatt Raymond",
    ("South Sydney Rabbitohs", "Sydney Roosters"): "Adam Gee",
    ("New Zealand Warriors", "Manly-Warringah Sea Eagles"): "Gerard Sutton",
    ("North Queensland Cowboys", "Canberra Raiders"): "TBC",
    ("Cronulla-Sutherland Sharks", "Melbourne Storm"): "Todd Smith",
    ("St. George Illawarra Dragons", "Parramatta Eels"): "Liam Kennedy",
    ("Penrith Panthers", "Wests Tigers"): "Ashley Klein",
}

# Production importance scale: elite 3.0, key 1.5, rotation 0.5. The pricing
# tier itself clamps a match adjustment to +/-3, preventing rotation stacking.
model.INJURY_OUTS = {
    "Canterbury-Bankstown Bulldogs": 1.5, "Brisbane Broncos": 0.5,
    "Gold Coast Titans": 0.5, "Dolphins": 1.5,
    "South Sydney Rabbitohs": 0.5, "Sydney Roosters": 10.0,
    "New Zealand Warriors": 3.0, "Manly-Warringah Sea Eagles": 0.0,
    "North Queensland Cowboys": 2.5, "Canberra Raiders": 3.5,
    "Cronulla-Sutherland Sharks": 7.0, "Melbourne Storm": 0.0,
    "St. George Illawarra Dragons": 0.0, "Parramatta Eels": 0.0,
    "Penrith Panthers": 2.0, "Wests Tigers": 0.5,
}

model.EMOTIONAL_FLAGS = {game[:2]: {"home": [], "away": []} for game in model.FIXTURE}
model.EMOTIONAL_FLAGS[("South Sydney Rabbitohs", "Sydney Roosters")]["home"] = [
    {"flag_type": "milestone", "flag_strength": "normal", "player_name": "Jai Arrow",
     "notes": "100th Rabbitohs game"},
    {"flag_type": "rivalry_derby", "flag_strength": "normal", "notes": "traditional rivalry"},
]
model.EMOTIONAL_FLAGS[("New Zealand Warriors", "Manly-Warringah Sea Eagles")]["home"] = [
    {"flag_type": "must_win", "flag_strength": "normal", "notes": "minor premiership race"},
]
model.EMOTIONAL_FLAGS[("Penrith Panthers", "Wests Tigers")]["home"] = [
    {"flag_type": "must_win", "flag_strength": "normal", "notes": "minor premiership race"},
]
model.EMOTIONAL_FLAGS[("Cronulla-Sutherland Sharks", "Melbourne Storm")]["home"] = [
    {"flag_type": "shame_blowout", "flag_strength": "normal", "notes": "38-18 loss in R26"},
]
model.HOME_RECORD = {team: model._home_record(team) for team in model.LADDER}


def main():
    styles = model.load_style_stats()
    norms = model.compute_norms(styles)
    rows = [model.price_game(*game, styles, norms) for game in model.FIXTURE]
    for row in rows:
        row["round_label"] = "official R27 (final regular-season round)"

    out = ROOT / "results" / "nrl_r27_official_pricing_2026.csv"
    with out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    for r in rows:
        print(f"{r['home']} v {r['away']}: {r['pred_home']}-{r['pred_away']}  "
              f"margin {r['final_margin']:+.2f}, total {r['final_total']:.1f}, "
              f"fair {r['fair_home_odds']:.3f}/{r['fair_away_odds']:.3f}")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
