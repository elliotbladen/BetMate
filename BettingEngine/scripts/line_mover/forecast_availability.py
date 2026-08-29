#!/usr/bin/env python3
"""Build the Monday projected-team availability input for line movement.

This is deliberately a forecast: it converts the information available after
the weekend into P(player misses the next game) and expected absence points.
Tuesday/Thursday team lists remain a later confirmation input.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BETMATE_ROOT = ROOT.parent
OUT_DIR = ROOT / "data" / "line_movement" / "availability"

TIER_POINTS = {"elite": 3.0, "key": 2.0, "rotation": 0.75, "depth": 0.35}


def miss_probability(record: dict, target_round: int) -> float:
    """Rules-v1 probability based only on information known at forecast time."""
    text = " ".join(str(record.get(k, "")) for k in
                    ("status", "notes", "injury", "return_info", "returning", "type", "raw")).lower()
    if any(x in text for x in ("season", "indefinite", "surgery", "ruled out", "suspended", "ban")):
        return 0.98
    round_match = re.search(r"return:\s*round\s*(\d+)|round\s*(\d+)", text)
    if round_match:
        return 0.95 if int(next(x for x in round_match.groups() if x)) > target_round else 0.25
    weeks = re.search(r"(\d+)\s*(?:-|to)?\s*(\d+)?\s*weeks?", text)
    if weeks:
        return 0.95 if int(weeks.group(1)) >= 1 else 0.45
    if any(x in text for x in ("failed hia", "category 1", "concussion")):
        return 0.82
    if any(x in text for x in ("did not return", "scans", "hamstring", "calf", "knee", "shoulder")):
        return 0.72
    if any(x in text for x in ("test", "doubtful", "tbc", "injury_watch", "head knock", "ankle")):
        return 0.58
    if record.get("status") == "out":
        return 0.80
    return 0.45


def player_points(record: dict, sport: str) -> float:
    tier = str(record.get("importance_tier", "")).lower()
    if tier in TIER_POINTS:
        return TIER_POINTS[tier]
    role = str(record.get("role") or record.get("position") or "").lower()
    if sport == "NRL" and any(x in role for x in ("half", "hooker", "fullback", "five")):
        return 2.25
    # Until a complete player-value table is available, do not pretend every
    # unnamed AFL player is a star. This prior is learned/calibrated later.
    return 1.0


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None


def source_records(sport: str, season: int, target_round: int) -> list[dict]:
    base = BETMATE_ROOT / "data" / sport.lower()
    records: list[dict] = []
    latest = load_json(base / "injuries" / "processed" / "latest-injuries.json")
    if isinstance(latest, list):
        records.extend(latest)
    diff = load_json(base / "injuries" / "processed" / "new-this-week.json")
    if isinstance(diff, dict):
        for key in ("new", "worsened"):
            records.extend(x for x in diff.get(key, []) if isinstance(x, dict))
    if sport == "NRL":
        review = load_json(base / "match-review" / "latest.json")
        if isinstance(review, dict):
            records.extend(review.get("fresh_injuries", []))
            records.extend(review.get("charges", []))
        scout = load_json(base / "scout" / "postgame" / "processed" / "latest.json")
        if isinstance(scout, dict):
            records.extend(scout.get("signals", []))
    return records


def build_forecast(sport: str, season: int, target_round: int) -> dict:
    candidates = source_records(sport, season, target_round)
    merged: dict[tuple[str, str], dict] = {}
    for row in candidates:
        team = str(row.get("team") or ((row.get("teams") or [""])[0])).strip()
        player = str(row.get("player") or "").strip()
        if not team or not player or player.lower().startswith("unknown"):
            continue
        p = miss_probability(row, target_round)
        pts = player_points(row, sport)
        key = (team.casefold(), player.casefold())
        item = {
            "team": team, "player": player,
            "miss_probability": round(p, 3),
            "player_points": round(pts, 2),
            "expected_absence_points": round(p * pts, 3),
            "classification": "likely_out" if p >= .75 else "doubtful" if p >= .5 else "probable",
            "evidence": str(row.get("notes") or row.get("raw") or row.get("injury") or "")[:500],
        }
        if key not in merged or item["miss_probability"] > merged[key]["miss_probability"]:
            merged[key] = item
    players = sorted(merged.values(), key=lambda x: (-x["expected_absence_points"], x["team"], x["player"]))
    teams: dict[str, dict] = {}
    for player in players:
        team = teams.setdefault(player["team"], {"expected_absence_points": 0.0, "players": []})
        team["players"].append(player)
        team["expected_absence_points"] += player["expected_absence_points"]
    for team in teams.values():
        team["expected_absence_points"] = round(team["expected_absence_points"], 3)
    return {
        "sport": sport, "season": season, "round": target_round,
        "stage": "MONDAY_FORECAST", "forecast_at": datetime.now(timezone.utc).isoformat(),
        "model_version": "availability_rules_v1",
        "players": players, "teams": teams,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sport", required=True, choices=("AFL", "NRL"))
    ap.add_argument("--season", type=int, default=2026)
    ap.add_argument("--round", type=int, required=True)
    args = ap.parse_args()
    payload = build_forecast(args.sport, args.season, args.round)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    dated = OUT_DIR / f"{args.sport.lower()}_r{args.round}_{datetime.now():%Y-%m-%d}_monday.json"
    dated.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (OUT_DIR / f"{args.sport.lower()}_latest.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Saved {dated}: {len(payload['players'])} projected player absences")


if __name__ == "__main__":
    main()
