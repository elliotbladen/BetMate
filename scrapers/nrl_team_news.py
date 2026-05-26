# /// script
# dependencies = ["tzdata", "requests"]
# ///
"""
lib/scraper/nrl_team_news.py

Auto-generates the injuries section of data/nrl/team-news/latest.json
from data/nrl/injuries/processed/latest-injuries.json.

Rules:
  - Injury records from latest-injuries.json  → auto-generated (replaced each run)
  - Records where notes contain "suspended"   → skipped (handled manually)
  - Existing suspension items in latest.json  → preserved as-is
  - Teams with no injuries or suspensions     → omitted from output

Writes data/nrl/team-news/latest.json then pushes to Supabase key 'team_news_nrl'.

Usage:
  uv run python lib/scraper/nrl_team_news.py
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT          = Path(__file__).resolve().parents[1]
INJURIES_PATH = ROOT / "data" / "nrl" / "injuries" / "processed" / "latest-injuries.json"
TEAM_NEWS_PATH = ROOT / "data" / "nrl" / "team-news" / "latest.json"
LOCAL_TZ      = ZoneInfo("Australia/Sydney")

TIER_TO_SEVERITY: dict[str, str] = {
    "spine":    "high",
    "key":      "high",
    "starter":  "medium",
    "rotation": "low",
}


def _load_env() -> None:
    env_file = ROOT / ".env.local"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


def _severity(tier: str) -> str:
    return TIER_TO_SEVERITY.get(tier.lower(), "low")


def _status(items: list[dict]) -> str:
    sevs = {i.get("severity", "low") for i in items}
    if "high" in sevs:
        return "alert"
    if "medium" in sevs:
        return "monitor"
    return "monitor" if items else "clear"


def _detail(notes: str) -> str:
    """'knee | Return: Round 13'  →  'Knee — return R13'"""
    parts = [p.strip() for p in notes.split("|")]
    label = parts[0].capitalize()
    if len(parts) > 1:
        ret = parts[1].replace("Return:", "").strip()
        ret = ret.replace("Round ", "R")
        return f"{label} — return {ret}"
    return label


def main() -> None:
    _load_env()

    if not INJURIES_PATH.exists():
        print(f"No injuries file at {INJURIES_PATH} — nothing to do")
        sys.exit(0)

    injuries: list[dict] = json.loads(INJURIES_PATH.read_text(encoding="utf-8"))
    if not injuries:
        print("Injuries file is empty — nothing to do")
        sys.exit(0)

    current_round  = injuries[0].get("round", 0)
    current_season = injuries[0].get("season", 2026)

    # Group injury records by team, skipping suspensions (stay manual)
    by_team: dict[str, list[dict]] = {}
    for rec in injuries:
        if "suspended" in rec.get("notes", "").lower():
            continue
        team = rec.get("team", "").strip()
        if not team:
            continue
        by_team.setdefault(team, []).append(rec)

    # Load existing team news to preserve manual suspension items
    existing_teams: dict[str, dict] = {}
    if TEAM_NEWS_PATH.exists():
        existing = json.loads(TEAM_NEWS_PATH.read_text(encoding="utf-8"))
        existing_teams = existing.get("teams", {})

    # Build merged output
    new_teams: dict[str, dict] = {}
    all_teams = sorted(set(by_team) | set(existing_teams))

    for team in all_teams:
        suspensions = [
            i for i in existing_teams.get(team, {}).get("items", [])
            if i.get("type") == "suspension"
        ]
        injuries_items = [
            {
                "type":     "injury",
                "player":   rec["player"],
                "detail":   _detail(rec.get("notes", "")),
                "severity": _severity(rec.get("importance_tier", "rotation")),
            }
            for rec in by_team.get(team, [])
        ]
        combined = suspensions + injuries_items
        if not combined:
            continue
        new_teams[team] = {"status": _status(combined), "items": combined}

    output = {
        "sport":   "NRL",
        "round":   current_round,
        "season":  current_season,
        "updated": datetime.now(LOCAL_TZ).strftime("%Y-%m-%d"),
        "teams":   new_teams,
    }

    TEAM_NEWS_PATH.parent.mkdir(parents=True, exist_ok=True)
    TEAM_NEWS_PATH.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")

    inj_count  = sum(sum(1 for i in v["items"] if i["type"] == "injury")      for v in new_teams.values())
    sus_count  = sum(sum(1 for i in v["items"] if i["type"] == "suspension")   for v in new_teams.values())
    print(f"Written {TEAM_NEWS_PATH}")
    print(f"  Round {current_round} | Teams: {len(new_teams)} | Injuries: {inj_count} | Suspensions preserved: {sus_count}")

    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from supabase_push import push  # noqa: PLC0415
        push("team_news_nrl", output)
    except Exception as exc:
        print(f"Supabase push failed: {exc}")


if __name__ == "__main__":
    main()
