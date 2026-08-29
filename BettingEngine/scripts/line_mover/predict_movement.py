#!/usr/bin/env python3
"""
predict_movement.py — Predict which team will shorten (open → close) for each game.

Phase 1: Rules-based weighted classifier.
Phase 2 (future): XGBoost trained on backfilled 2024-2025 labelled data.

Inputs:
  - ELO from features_afl.csv / model.db (NRL)
  - Injuries from team list ins/outs
  - Ladder positions (scraped or from DB)
  - Historical matchup shortening patterns (from aussportsbetting xlsx)
  - Fixture for the round

Output:
  - data/line_movement/predictions/{sport}_r{round}_{date}.json

Usage:
    python scripts/line_mover/predict_movement.py --sport AFL --round 23 --season 2026
    python scripts/line_mover/predict_movement.py --sport NRL --round 24 --season 2026
"""

import argparse
import csv
import json
import re
import sys
from datetime import datetime, timezone, date
from pathlib import Path

import openpyxl
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = ROOT / "data" / "line_movement"
PREDICTIONS_DIR = DATA_DIR / "predictions"
PREDICTIONS_DIR.mkdir(parents=True, exist_ok=True)
TOTALS_BACKTEST_PATH = ROOT / "outputs" / "line_movement" / "nrl_totals_movement_backtest.json"

# ---------------------------------------------------------------------------
# Feature weights (Phase 1 rules-based)
# ---------------------------------------------------------------------------

WEIGHTS = {
    "injury_differential": 0.25,
    "elo_gap": 0.20,
    "finals_stakes": 0.15,
    "historical_pattern": 0.15,
    "public_bias": 0.10,
    "recent_form": 0.10,
    "venue_fortress": 0.05,
}

TOTALS_WEIGHTS = {
    "historical_totals_pattern": 0.30,
    "combined_injuries": 0.25,
    "weather": 0.20,
    "venue_totals_history": 0.15,
    "scoring_style": 0.10,
}

# Big clubs that attract disproportionate public money
BIG_CLUBS_AFL = {
    "Collingwood Magpies", "Carlton Blues", "Essendon Bombers",
    "Richmond Tigers", "Hawthorn Hawks",
}
BIG_CLUBS_NRL = {
    "South Sydney Rabbitohs", "Sydney Roosters", "Brisbane Broncos",
    "Penrith Panthers", "Canterbury-Bankstown Bulldogs",
}


# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------

def load_afl_elo() -> dict:
    """Load latest AFL ELO from features_afl.csv. Returns {team: elo}."""
    path = ROOT / "ml" / "afl" / "results" / "features_afl.csv"
    if not path.exists():
        return {}
    df = pd.read_csv(path)
    latest = {}
    for _, row in df.iterrows():
        latest[row.get("home_team", "")] = row.get("home_elo", 1500)
        latest[row.get("away_team", "")] = row.get("away_elo", 1500)
    return latest


def load_nrl_elo() -> dict:
    """Load latest NRL ELO from model.db team_stats."""
    import sqlite3
    db_path = ROOT / "data" / "model.db"
    if not db_path.exists():
        return {}
    conn = sqlite3.connect(db_path)
    rows = conn.execute("""
        SELECT t.team_name, ts.elo_rating
        FROM team_stats ts
        JOIN teams t ON ts.team_id = t.team_id
        WHERE t.league = 'NRL'
        ORDER BY ts.as_of_date DESC
    """).fetchall()
    conn.close()
    elo = {}
    for name, rating in rows:
        if name not in elo:
            elo[name] = rating
    return elo


def load_historical_movements(sport: str) -> dict:
    """
    Load open→close H2H movements from aussportsbetting xlsx.
    Returns {(home_short, away_short): {"home_shortened": int, "away_shortened": int, "total": int,
                                         "totals_down": int, "totals_up": int}}
    """
    if sport == "AFL":
        xlsx_path = ROOT / "outputs" / "afl_weekly_review" / "historical" / "latest.xlsx"
    else:
        xlsx_path = ROOT / "outputs" / "nrl_weekly_review" / "historical" / "latest.xlsx"

    if not xlsx_path.exists():
        return {}

    df = pd.read_excel(xlsx_path, header=1)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df[df["Date"] >= "2024-01-01"]

    matchup_data = {}
    for _, row in df.iterrows():
        home = str(row.get("Home Team", "")).strip()
        away = str(row.get("Away Team", "")).strip()
        if not home or not away:
            continue

        # Normalize to short names for matching
        home_short = home.split()[-1] if home else ""
        away_short = away.split()[-1] if away else ""
        key = tuple(sorted([home_short, away_short]))

        if key not in matchup_data:
            matchup_data[key] = {
                "home_shortened": 0, "away_shortened": 0, "total": 0,
                "totals_down": 0, "totals_up": 0, "games": [],
            }

        try:
            ho = float(row.get("Home Odds Open", 0))
            hc = float(row.get("Home Odds Close", 0))
            ao = float(row.get("Away Odds Open", 0))
            ac = float(row.get("Away Odds Close", 0))
            if ho <= 0 or hc <= 0 or ao <= 0 or ac <= 0:
                continue
        except (TypeError, ValueError):
            continue

        matchup_data[key]["total"] += 1

        home_shortened = hc < ho
        away_shortened = ac < ao

        if home_shortened and not away_shortened:
            # Figure out which team shortened based on our key
            if home_short == key[0]:
                matchup_data[key]["home_shortened"] += 1
            else:
                matchup_data[key]["away_shortened"] += 1
        elif away_shortened and not home_shortened:
            if away_short == key[0]:
                matchup_data[key]["home_shortened"] += 1
            else:
                matchup_data[key]["away_shortened"] += 1

        # Totals
        try:
            to_val = float(row.get("Total Score Open", 0))
            tc = float(row.get("Total Score Close", 0))
            if to_val > 0 and tc > 0:
                if tc < to_val:
                    matchup_data[key]["totals_down"] += 1
                elif tc > to_val:
                    matchup_data[key]["totals_up"] += 1
        except (TypeError, ValueError):
            pass

        matchup_data[key]["games"].append({
            "date": str(row.get("Date", ""))[:10],
            "home": home, "away": away,
            "ho": ho, "hc": hc, "ao": ao, "ac": ac,
        })

    return matchup_data


def load_team_lists(sport: str) -> dict:
    """Load latest scraped team lists."""
    path = DATA_DIR / "team_lists" / f"{sport.lower()}_latest.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}


def load_availability_forecast(sport: str, season: int, rnd: int) -> dict:
    path = DATA_DIR / "availability" / f"{sport.lower()}_latest.json"
    payload = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    if payload.get("season") != season or payload.get("round") != rnd:
        return {}
    return payload


def load_afl_injuries(season: int, rnd: int) -> list[dict]:
    """Load the maintained AFL injury feed for the requested round."""
    path = ROOT.parent / "data" / "afl" / "injuries" / "processed" / str(season) / f"round-{rnd}-injuries.json"
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return []
    return payload if isinstance(payload, list) else []


def load_ladder(sport: str) -> dict:
    """Load ladder positions. Returns {team_name: position}."""
    # Try to read from a cached ladder file
    path = DATA_DIR / f"{sport.lower()}_ladder.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}


# ---------------------------------------------------------------------------
# Feature scoring functions
# ---------------------------------------------------------------------------

def _selection_name_matches(short_name: str, full_name: str) -> bool:
    """Match Footywire initials (M Bontempelli) to the maintained full name."""
    short = re.findall(r"[a-z]+", short_name.lower())
    full = re.findall(r"[a-z]+", full_name.lower())
    if not short or not full:
        return False
    if short[-1] != full[-1]:
        return False
    if len(short) > 2:
        return [part[0] for part in short] == [part[0] for part in full]
    return len(short[0]) > 1 or short[0][0] == full[0][0]


def _verified_injury_changes(team: str, team_lists: dict, injuries: list[dict]) -> dict:
    entry = (team_lists.get("teams") or {}).get(team, {})
    listed = [row for row in injuries if row.get("team") == team]

    def matched(players: list[str]) -> list[str]:
        return [
            player for player in players
            if any(_selection_name_matches(player, row.get("player", "")) for row in listed)
        ]

    return {
        "injury_outs": matched(entry.get("outs", [])),
        "returning_ins": matched(entry.get("ins", [])),
    }


def score_injury_differential(
    home_team: str, away_team: str, team_lists: dict,
    injuries: list[dict] | None = None,
) -> float:
    """
    Score based on injury differential from team list ins/outs.
    Positive = home team advantage (opponent has more outs) → home shortens.
    Range: -1.0 to +1.0
    """
    if injuries:
        home = _verified_injury_changes(home_team, team_lists, injuries)
        away = _verified_injury_changes(away_team, team_lists, injuries)
        home_net = len(home["injury_outs"]) - len(home["returning_ins"])
        away_net = len(away["injury_outs"]) - len(away["returning_ins"])
        return max(-1.0, min(1.0, (away_net - home_net) / 5.0))

    teams = team_lists.get("teams", {})

    home_outs = 0
    away_outs = 0

    # Try to match team names (fuzzy)
    for team_name, data in teams.items():
        if any(w in team_name.lower() for w in home_team.lower().split()[-1:]):
            home_outs = len(data.get("outs", []))
        if any(w in team_name.lower() for w in away_team.lower().split()[-1:]):
            away_outs = len(data.get("outs", []))

    diff = away_outs - home_outs  # positive = away has more outs = home advantage
    # Cap at ±10 outs differential, normalize to -1..+1
    return max(-1.0, min(1.0, diff / 10.0))


def score_projected_availability(home_team: str, away_team: str, forecast: dict) -> float:
    teams = forecast.get("teams", {})
    home = float(teams.get(home_team, {}).get("expected_absence_points", 0.0))
    away = float(teams.get(away_team, {}).get("expected_absence_points", 0.0))
    return max(-1.0, min(1.0, (away - home) / 6.0))


def score_elo_gap(home_elo: float, away_elo: float) -> float:
    """
    Score based on ELO gap. Positive = home stronger → home shortens.
    Range: -1.0 to +1.0
    """
    gap = home_elo - away_elo
    # Cap at ±500 ELO gap, normalize
    return max(-1.0, min(1.0, gap / 500.0))


def score_finals_stakes(home_pos: int, away_pos: int) -> float:
    """
    Score based on finals implications.
    Team fighting for top 8 vs eliminated → fighting team shortens.
    Positive = home has more at stake → home shortens.
    Range: -1.0 to +1.0
    """
    if home_pos == 0 or away_pos == 0:
        return 0.0

    # Positions 1-10 are finals contenders (wildcard system), 11+ are out
    home_contender = home_pos <= 10
    away_contender = away_pos <= 10

    if home_contender and not away_contender:
        return 0.6  # Home has more stake
    elif away_contender and not home_contender:
        return -0.6

    # Both contending — team in more precarious position has more at stake
    if home_contender and away_contender:
        # Team closer to cutoff (positions 7-10) has more desperation
        home_desp = max(0, home_pos - 6) / 4.0  # 0 for pos 1-6, up to 1.0 for pos 10
        away_desp = max(0, away_pos - 6) / 4.0
        return (away_desp - home_desp) * 0.4  # Slight lean toward more desperate team

    return 0.0


def score_historical_pattern(home_team: str, away_team: str, movements: dict) -> float:
    """
    Score based on historical open→close pattern for this matchup.
    Positive = home historically shortens more → predict home shortens.
    Range: -1.0 to +1.0
    """
    home_short = home_team.split()[-1]
    away_short = away_team.split()[-1]
    key = tuple(sorted([home_short, away_short]))

    data = movements.get(key)
    if not data or data["total"] < 2:
        return 0.0

    # Determine which side of the key is "home" for this game
    if home_short == key[0]:
        home_count = data["home_shortened"]
        away_count = data["away_shortened"]
    else:
        home_count = data["away_shortened"]
        away_count = data["home_shortened"]

    total = data["total"]
    if total == 0:
        return 0.0

    home_pct = home_count / total
    away_pct = away_count / total

    return max(-1.0, min(1.0, (home_pct - away_pct) * 2.0))


def score_public_bias(home_team: str, away_team: str, sport: str) -> float:
    """
    Score based on public betting bias (big clubs attract more money).
    Positive = home is bigger club → home shortens from public money.
    Range: -1.0 to +1.0
    """
    big_clubs = BIG_CLUBS_AFL if sport == "AFL" else BIG_CLUBS_NRL

    home_big = home_team in big_clubs
    away_big = away_team in big_clubs

    if home_big and not away_big:
        return 0.3
    elif away_big and not home_big:
        return -0.3
    return 0.0


def score_recent_form(home_elo: float, away_elo: float) -> float:
    """
    Proxy for recent form using ELO (which captures form implicitly).
    Teams on winning streaks attract public recency bias.
    Range: -1.0 to +1.0
    """
    gap = home_elo - away_elo
    # Large ELO gaps suggest dominant recent form → public piles on
    return max(-1.0, min(1.0, gap / 400.0)) * 0.5


def score_venue_fortress(home_team: str) -> float:
    """Known fortress venues give a slight home shortening lean."""
    fortresses = {
        "Fremantle Dockers": 0.3,    # Optus Stadium
        "Brisbane Lions": 0.3,       # The Gabba
        "Port Adelaide Power": 0.2,  # Adelaide Oval
        "Geelong Cats": 0.3,         # GMHBA Stadium
        "Melbourne Storm": 0.3,      # AAMI Park
        "Penrith Panthers": 0.3,     # BlueBet Stadium
    }
    return fortresses.get(home_team, 0.0)


def score_totals_history(home_team: str, away_team: str, movements: dict) -> float:
    """
    Historical totals direction for this matchup.
    Positive = historically goes UNDERS → predict unders.
    Range: -1.0 to +1.0
    """
    home_short = home_team.split()[-1]
    away_short = away_team.split()[-1]
    key = tuple(sorted([home_short, away_short]))

    data = movements.get(key)
    if not data or data["total"] < 2:
        return 0.0

    down = data.get("totals_down", 0)
    up = data.get("totals_up", 0)
    total = down + up
    if total == 0:
        return 0.0

    return max(-1.0, min(1.0, (down - up) / total))


# ---------------------------------------------------------------------------
# Main prediction
# ---------------------------------------------------------------------------

def predict_game(
    home_team: str, away_team: str, sport: str,
    home_elo: float, away_elo: float,
    home_pos: int, away_pos: int,
    movements: dict, team_lists: dict, injuries: list[dict] | None = None,
    availability_forecast: dict | None = None,
) -> dict:
    """Run the rules-based classifier for a single game."""

    scores = {
        "injury_differential": (
            score_projected_availability(home_team, away_team, availability_forecast)
            if availability_forecast else
            score_injury_differential(home_team, away_team, team_lists, injuries)
        ),
        "elo_gap": score_elo_gap(home_elo, away_elo),
        "finals_stakes": score_finals_stakes(home_pos, away_pos),
        "historical_pattern": score_historical_pattern(home_team, away_team, movements),
        "public_bias": score_public_bias(home_team, away_team, sport),
        "recent_form": score_recent_form(home_elo, away_elo),
        "venue_fortress": score_venue_fortress(home_team),
    }

    # Weighted sum → positive = home shortens, negative = away shortens
    weighted_sum = sum(scores[k] * WEIGHTS[k] for k in WEIGHTS)

    # Confidence = |weighted_sum| scaled to 0-100%
    confidence = min(100, abs(weighted_sum) * 150)

    if weighted_sum > 0:
        shortens = home_team
        direction = "HOME"
    else:
        shortens = away_team
        direction = "AWAY"

    # Totals prediction
    totals_score = score_totals_history(home_team, away_team, movements)
    if totals_score > 0.1:
        totals_pred = "UNDERS"
    elif totals_score < -0.1:
        totals_pred = "OVERS"
    else:
        totals_pred = "EVEN"

    result = {
        "home_team": home_team,
        "away_team": away_team,
        "prediction": shortens,
        "direction": direction,
        "confidence": round(confidence, 1),
        "weighted_score": round(weighted_sum, 4),
        "feature_scores": {k: round(v, 4) for k, v in scores.items()},
        "totals_prediction": totals_pred,
        "totals_score": round(totals_score, 4),
        "totals_confidence": None,
        "totals_model_status": "HISTORICAL_LEAN_ONLY",
    }
    if injuries:
        result["verified_injury_changes"] = {
            "home": _verified_injury_changes(home_team, team_lists, injuries),
            "away": _verified_injury_changes(away_team, team_lists, injuries),
        }
    if availability_forecast:
        result["projected_availability"] = {
            "home": availability_forecast.get("teams", {}).get(home_team, {}),
            "away": availability_forecast.get("teams", {}).get(away_team, {}),
        }
    return result


def apply_totals_validation(predictions: list[dict], sport: str) -> None:
    """Expose confidence only after the time-split model passes acceptance."""
    if sport != "NRL" or not TOTALS_BACKTEST_PATH.exists():
        return
    try:
        report = json.loads(TOTALS_BACKTEST_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    approved = bool(report.get("approved_for_live_confidence"))
    for prediction in predictions:
        prediction["totals_model_status"] = "VALIDATED" if approved else "INSUFFICIENT_EVIDENCE"
        prediction["totals_backtest_accuracy"] = report.get("test", {}).get("accuracy")
        prediction["totals_baseline_accuracy"] = report.get("test", {}).get("majority_baseline_accuracy")


def load_fixture(sport: str, season: int, rnd: int) -> list:
    """Load fixture from the round prep CSV or pricing CSV."""
    if sport == "AFL":
        fixture_path = ROOT / "outputs" / "afl_round_prep" / f"r{rnd}_{season}" / f"fixture_r{rnd}_{season}.csv"
        if fixture_path.exists():
            games = []
            with open(fixture_path) as f:
                for row in csv.DictReader(f):
                    games.append({
                        "home_team": row["home_team"].strip(),
                        "away_team": row["away_team"].strip(),
                    })
            return games
        # Monday prices often appear before round prep is created. The odds
        # snapshot is then the fixture authority; only future AFL games are used.
        odds_path = ROOT.parent / "data" / "odds_snapshots" / "latest.csv"
        if odds_path.exists():
            now = datetime.now(timezone.utc)
            games = {}
            with odds_path.open(encoding="utf-8-sig") as f:
                for row in csv.DictReader(f):
                    if str(row.get("sport", "")).upper() != "AFL":
                        continue
                    try:
                        kickoff = datetime.fromisoformat(row["commence_time"].replace("Z", "+00:00"))
                    except (KeyError, ValueError):
                        continue
                    if kickoff <= now:
                        continue
                    key = (row.get("home_team", "").strip(), row.get("away_team", "").strip())
                    if all(key):
                        games[key] = {"home_team": key[0], "away_team": key[1]}
            if games:
                return list(games.values())
    else:
        # NRL — read from model.db
        import sqlite3
        db_path = ROOT / "data" / "model.db"
        if db_path.exists():
            conn = sqlite3.connect(db_path)
            rows = conn.execute("""
                SELECT t1.team_name, t2.team_name
                FROM matches m
                JOIN teams t1 ON m.home_team_id = t1.team_id
                JOIN teams t2 ON m.away_team_id = t2.team_id
                WHERE m.season = ? AND m.round_number = ? AND m.sport = 'NRL'
                ORDER BY m.match_date
            """, (season, rnd)).fetchall()
            conn.close()
            return [{"home_team": r[0], "away_team": r[1]} for r in rows]
    return []


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sport", required=True, choices=["NRL", "AFL"])
    parser.add_argument("--round", type=int, required=True)
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument("--stage", choices=("monday", "confirmation"), default="confirmation")
    args = parser.parse_args()

    sport = args.sport
    rnd = args.round
    season = args.season

    print(f"\n{'='*70}")
    print(f"  LINE MOVEMENT PREDICTOR — {sport} R{rnd} {season}")
    print(f"{'='*70}\n")

    # Load data
    print("Loading data...")
    if sport == "AFL":
        elo = load_afl_elo()
    else:
        elo = load_nrl_elo()

    movements = load_historical_movements(sport)
    team_lists = load_team_lists(sport)
    availability_forecast = load_availability_forecast(sport, season, rnd) if args.stage == "monday" else {}
    injuries = load_afl_injuries(season, rnd) if sport == "AFL" else []
    ladder = load_ladder(sport)

    fixture = load_fixture(sport, season, rnd)
    if not fixture:
        print(f"ERROR: No fixture found for {sport} R{rnd} {season}")
        sys.exit(1)

    print(f"  ELO data: {len(elo)} teams")
    print(f"  Historical matchups: {len(movements)} pairs")
    print(f"  Team lists: {len(team_lists.get('teams', {}))} teams with ins/outs")
    print(f"  Verified injury records: {len(injuries)}")
    print(f"  Projected availability: {len(availability_forecast.get('players', []))} players")
    print(f"  Ladder: {len(ladder)} teams")
    print(f"  Fixture: {len(fixture)} games")
    print()

    # Run predictions
    predictions = []
    for game in fixture:
        home = game["home_team"]
        away = game["away_team"]

        home_elo = elo.get(home, 1500)
        away_elo = elo.get(away, 1500)
        home_pos = ladder.get(home, 0)
        away_pos = ladder.get(away, 0)

        pred = predict_game(
            home, away, sport,
            home_elo, away_elo,
            home_pos, away_pos,
            movements, team_lists, injuries, availability_forecast,
        )
        predictions.append(pred)
    apply_totals_validation(predictions, sport)

    # Print results
    print(f"{'Game':<50} {'Shortens':<25} {'Conf':>6}  {'Totals':>8}")
    print("-" * 95)
    for p in predictions:
        game_label = f"{p['home_team'].split()[-1]} vs {p['away_team'].split()[-1]}"
        conf_str = f"{p['confidence']:.0f}%"
        print(f"  {game_label:<48} {p['prediction'].split()[-1]:<25} {conf_str:>6}  {p['totals_prediction']:>8}")

    print()

    # Feature breakdown
    print("Feature breakdown:")
    print(f"  {'Game':<30} {'Injury':>7} {'ELO':>7} {'Finals':>7} {'Hist':>7} {'Public':>7} {'Form':>7} {'Venue':>7} {'TOTAL':>7}")
    print("  " + "-" * 78)
    for p in predictions:
        game_label = f"{p['home_team'].split()[-1]} v {p['away_team'].split()[-1]}"
        fs = p["feature_scores"]
        print(f"  {game_label:<30} {fs['injury_differential']:>+.3f} {fs['elo_gap']:>+.3f} "
              f"{fs['finals_stakes']:>+.3f} {fs['historical_pattern']:>+.3f} "
              f"{fs['public_bias']:>+.3f} {fs['recent_form']:>+.3f} "
              f"{fs['venue_fortress']:>+.3f} {p['weighted_score']:>+.4f}")

    # Save predictions
    output = {
        "sport": sport,
        "season": season,
        "round": rnd,
        "predicted_at": datetime.now(timezone.utc).isoformat(),
        "stage": "MONDAY_FORECAST" if args.stage == "monday" else "TEAM_LIST_CONFIRMATION",
        "model_version": "rules_v1.2_projected_availability",
        "predictions": predictions,
    }

    date_str = datetime.now().strftime("%Y-%m-%d")
    stage_suffix = "_monday" if args.stage == "monday" else "_confirmation"
    filename = f"{sport.lower()}_r{rnd}_{date_str}{stage_suffix}.json"
    out_path = PREDICTIONS_DIR / filename
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)

    latest_path = PREDICTIONS_DIR / f"{sport.lower()}_latest.json"
    with open(latest_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nPredictions saved: {out_path}")
    print(f"Latest pointer: {latest_path}")


if __name__ == "__main__":
    main()
