"""
scripts/h2h_research_r10.py

NRL R10 2026 — H2H historical situational ROI scanner.

For each R10 matchup, scans historical data for angles where
actual ROI beats market. Reports triple signals (3+ angles at or
above threshold ROI, all matching this week's exact conditions).

Data: data/import/results_2023.csv + results_2025.csv + results_2026_r1_r5.csv
      data/import/odds_2023.csv    + odds_2025.csv    + odds_2026_r1_r5.csv
"""

from __future__ import annotations

import csv
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parent.parent

THRESHOLD_HIGH = 0.20
THRESHOLD_LOW  = 0.10
MIN_SAMPLE     = 8

KNOWN_NEW_MOON   = date(2000, 1, 6)
LUNAR_CYCLE      = 29.530589
MOON_WINDOW_DAYS = 1.5

# Historical CSV names differ from DB canonical names
CSV_TO_DB = {
    "Canterbury Bulldogs":     "Canterbury-Bankstown Bulldogs",
    "Cronulla Sharks":         "Cronulla-Sutherland Sharks",
    "Manly Sea Eagles":        "Manly-Warringah Sea Eagles",
    "North QLD Cowboys":       "North Queensland Cowboys",
    "St. George Illawarra Dragons": "St. George Illawarra Dragons",
}

def canon(name: str) -> str:
    return CSV_TO_DB.get(name, name)


# ─── Moon helpers ────────────────────────────────────────────────────────────

def moon_age(d: date) -> float:
    return ((d - KNOWN_NEW_MOON).days % LUNAR_CYCLE)

def moon_phase(d: date) -> str:
    age = moon_age(d)
    if age <= MOON_WINDOW_DAYS or age >= (LUNAR_CYCLE - MOON_WINDOW_DAYS):
        return "new"
    if abs(age - 14.765) <= MOON_WINDOW_DAYS:
        return "full"
    return "other"


# ─── Data loading ────────────────────────────────────────────────────────────

def load_results() -> list[dict]:
    files = [
        "data/import/results_2023.csv",
        "data/import/results_2025.csv",
        "data/import/results_2026_r1_r5.csv",
    ]
    rows = []
    for fpath in files:
        with open(ROOT / fpath, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if not row["match_date"] or not row["home_score"]:
                    continue
                rows.append({
                    "game_date":  date.fromisoformat(row["match_date"]),
                    "season":     int(row["season"]),
                    "round":      int(row["round"]),
                    "home_team":  canon(row["home_team"]),
                    "away_team":  canon(row["away_team"]),
                    "home_score": int(row["home_score"]),
                    "away_score": int(row["away_score"]),
                })
    rows.sort(key=lambda r: r["game_date"])
    return rows


def load_odds() -> dict[tuple, dict]:
    """Returns {(match_date, home_team, away_team): {home_odds, away_odds}}"""
    files = [
        "data/import/odds_2023.csv",
        "data/import/odds_2025.csv",
        "data/import/odds_2026_r1_r5.csv",
    ]
    raw: dict[tuple, dict] = {}
    for fpath in files:
        p = ROOT / fpath
        if not p.exists():
            continue
        with open(p, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("market_type", "").lower() != "h2h":
                    continue
                if row.get("is_closing") != "1" and row.get("is_opening") != "1":
                    continue
                key = (row["match_date"], canon(row["home_team"]), canon(row["away_team"]))
                if key not in raw:
                    raw[key] = {}
                prefer_close = row.get("is_closing") == "1"
                sel = row.get("selection", "").lower()
                if sel in ("home", "away"):
                    k = f"{sel}_odds"
                    if k not in raw[key] or prefer_close:
                        raw[key][k] = float(row["odds"])
    # Rebuild with canonical date keys
    result = {}
    for (dstr, ht, at), odds in raw.items():
        if "home_odds" in odds and "away_odds" in odds:
            result[(date.fromisoformat(dstr), ht, at)] = odds
    return result


def enrich(results: list[dict], odds: dict) -> list[dict]:
    """Merge odds into results, add rest days and moon phase."""
    last_game: dict[str, date] = {}
    enriched = []
    for r in results:
        d = r["game_date"]
        key = (d, r["home_team"], r["away_team"])
        o = odds.get(key)
        if o is None:
            last_game[r["home_team"]] = d
            last_game[r["away_team"]] = d
            continue

        rest_h = (d - last_game[r["home_team"]]).days if r["home_team"] in last_game else None
        rest_a = (d - last_game[r["away_team"]]).days if r["away_team"] in last_game else None

        enriched.append({
            **r,
            "home_odds":  o["home_odds"],
            "away_odds":  o["away_odds"],
            "home_win":   1 if r["home_score"] > r["away_score"] else 0,
            "rest_home":  rest_h,
            "rest_away":  rest_a,
            "moon":       moon_phase(d),
        })
        last_game[r["home_team"]] = d
        last_game[r["away_team"]] = d
    return enriched


# ─── ROI calculation ─────────────────────────────────────────────────────────

def roi(games: list[dict], perspective: str) -> tuple[float, int]:
    """
    ROI for backing `perspective` ('home' or 'away') in these games.
    Returns (roi_decimal, n).
    """
    if not games:
        return (0.0, 0)
    if perspective == "home":
        returns = [g["home_win"] * g["home_odds"] for g in games]
    else:
        returns = [(1 - g["home_win"]) * g["away_odds"] for g in games]
    return (mean(returns) - 1, len(games))


# ─── R10 fixture (hardcoded from DB query) ───────────────────────────────────

R10_FIXTURE = [
    # (game_date, home_team, away_team, rest_home_days, rest_away_days)
    (date(2026, 5, 7),  "Dolphins",                       "Canterbury-Bankstown Bulldogs", 6,  6),
    (date(2026, 5, 8),  "Sydney Roosters",                 "Gold Coast Titans",             6,  6),
    (date(2026, 5, 8),  "North Queensland Cowboys",        "Parramatta Eels",               7,  6),
    (date(2026, 5, 9),  "St. George Illawarra Dragons",    "Newcastle Knights",             14,  6),
    (date(2026, 5, 9),  "South Sydney Rabbitohs",          "Cronulla-Sutherland Sharks",    6,  6),
    (date(2026, 5, 9),  "Manly-Warringah Sea Eagles",      "Brisbane Broncos",               6,  7),
    (date(2026, 5, 10), "Melbourne Storm",                 "Wests Tigers",                   9,  7),
    (date(2026, 5, 10), "Canberra Raiders",                "Penrith Panthers",               8,  7),
]


# ─── Angle scanner ───────────────────────────────────────────────────────────

def scan_angles(
    team: str,
    role: str,          # 'home' or 'away'
    opponent: str,
    game_date: date,
    rest_days: int,
    opp_rest_days: int,
    data: list[dict],
    threshold: float,
) -> list[dict]:
    """
    Scan situational angles for this team/role/opponent/date.
    Returns list of {label, roi, n} for angles that meet threshold and MIN_SAMPLE.
    Only applies angles whose conditions match THIS week's exact situation.
    """
    signals = []
    game_month = game_date.month
    game_moon  = moon_phase(game_date)
    seen_labels: set[str] = set()

    def maybe_add(label: str, subset: list[dict]):
        if label in seen_labels:
            return
        r, n = roi(subset, role)
        if n >= MIN_SAMPLE and r >= threshold:
            signals.append({"label": label, "roi": r, "n": n})
            seen_labels.add(label)

    # Helper: filter by role
    def home_games(d):  return [g for g in d if g["home_team"] == team]
    def away_games(d):  return [g for g in d if g["away_team"] == team]
    def role_games(d):  return home_games(d) if role == "home" else away_games(d)

    all_data = data  # all historical games

    # 1. vs this opponent (same role)
    vs_opp = [g for g in role_games(all_data)
              if (g["away_team"] if role == "home" else g["home_team"]) == opponent]
    maybe_add(f"vs {opponent} ({role})", vs_opp)

    # 2. Month = May (all games, same role)
    in_month = [g for g in role_games(all_data) if g["game_date"].month == game_month]
    maybe_add(f"May games ({role})", in_month)

    # 3. vs this opponent in May
    vs_opp_may = [g for g in vs_opp if g["game_date"].month == game_month]
    maybe_add(f"vs {opponent} in May ({role})", vs_opp_may)

    # 4. Rest angle — only apply if this team has unusual rest this week
    if rest_days >= 12:
        long_rest = [g for g in role_games(all_data)
                     if g[f"rest_{role}"] is not None and g[f"rest_{role}"] >= 12]
        maybe_add(f"after long rest 12+d ({role})", long_rest)

    if rest_days >= 8:
        med_rest = [g for g in role_games(all_data)
                    if g[f"rest_{role}"] is not None and g[f"rest_{role}"] >= 8]
        maybe_add(f"after 8+d rest ({role})", med_rest)

    # 5. Opponent rest angle — only apply if opponent has unusual rest
    opp_role = "away" if role == "home" else "home"
    if opp_rest_days >= 12:
        vs_rested_opp = [g for g in role_games(all_data)
                         if g[f"rest_{opp_role}"] is not None and g[f"rest_{opp_role}"] >= 12]
        maybe_add(f"vs opp with 12+d rest ({role})", vs_rested_opp)

    # 6. Moon phase — only apply if this game actually falls in that window
    if game_moon in ("full", "new"):
        moon_games = [g for g in role_games(all_data) if g["moon"] == game_moon]
        maybe_add(f"{game_moon} moon ({role})", moon_games)
        # moon + month combo
        moon_month = [g for g in moon_games if g["game_date"].month == game_month]
        maybe_add(f"{game_moon} moon in May ({role})", moon_month)

    return signals


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    results = load_results()
    odds    = load_odds()
    data    = enrich(results, odds)

    print(f"  Loaded {len(data)} historical NRL games with odds (2023 + 2025 + 2026 R1-R5)")
    print(f"  Note: no 2024 data in import files")

    # Two-pass: first try 20%, fall back to 10% if no triple signals found anywhere
    for threshold in (THRESHOLD_HIGH, THRESHOLD_LOW):
        label = f"{int(threshold*100)}%"
        all_triples: list[tuple] = []  # (game_label, team, role, signals)

        for gd, home, away, rest_h, rest_a in R10_FIXTURE:
            game_label = f"{home} vs {away}"
            for team, role, opp, rest, opp_rest in [
                (home, "home", away,  rest_h, rest_a),
                (away, "away", home,  rest_a, rest_h),
            ]:
                sigs = scan_angles(team, role, opp, gd, rest, opp_rest, data, threshold)
                if len(sigs) >= 3:
                    all_triples.append((game_label, team, role, sigs))

        W = 90
        print()
        print("=" * W)
        print(f"  NRL R10 2026 — H2H MATRIX  |  threshold={label}  |  min_n={MIN_SAMPLE}")
        print("=" * W)

        if all_triples:
            for game_label, team, role, sigs in all_triples:
                print(f"\n  *** TRIPLE SIGNAL: {team} ({role}) — {game_label} ***")
                for s in sigs:
                    print(f"      {s['label']:55s}  ROI={s['roi']:+.1%}  n={s['n']}")
            print()
            break  # found triples — don't fall back
        else:
            # Show best near-misses (2 signals) at this threshold before trying lower
            near_misses: list[tuple] = []
            for gd, home, away, rest_h, rest_a in R10_FIXTURE:
                game_label = f"{home} vs {away}"
                for team, role, opp, rest, opp_rest in [
                    (home, "home", away,  rest_h, rest_a),
                    (away, "away", home,  rest_a, rest_h),
                ]:
                    sigs = scan_angles(team, role, opp, gd, rest, opp_rest, data, threshold)
                    if len(sigs) == 2:
                        near_misses.append((game_label, team, role, sigs))

            print(f"\n  No triple signals at {label}.")
            if near_misses:
                print(f"  Near-misses (2 signals at {label}):")
                for game_label, team, role, sigs in near_misses:
                    print(f"\n    {team} ({role}) — {game_label}")
                    for s in sigs:
                        print(f"      {s['label']:55s}  ROI={s['roi']:+.1%}  n={s['n']}")

            if threshold == THRESHOLD_LOW:
                print(f"\n  No triple signals found at {label} either. No matrix plays this round.")


if __name__ == "__main__":
    main()
