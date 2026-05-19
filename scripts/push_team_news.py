"""
scripts/push_team_news.py

Manually push team news JSON files to Supabase after editing them.
Run this after updating data/nrl/team-news/latest.json or
data/afl/team-news/latest.json.

Usage:
  uv run --with requests python scripts/push_team_news.py
  uv run --with requests python scripts/push_team_news.py --sport NRL
  uv run --with requests python scripts/push_team_news.py --sport AFL
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib" / "scraper"))

from supabase_push import push  # noqa: E402


def push_sport(sport: str) -> bool:
    sport = sport.upper()
    if sport == "NRL":
        path = ROOT / "data" / "nrl" / "team-news" / "latest.json"
        key = "team_news_nrl"
    elif sport == "AFL":
        path = ROOT / "data" / "afl" / "team-news" / "latest.json"
        key = "team_news_afl"
    else:
        print(f"Unknown sport: {sport}")
        return False

    if not path.exists():
        print(f"File not found: {path}")
        return False

    data = json.loads(path.read_text(encoding="utf-8"))
    ok = push(key, data)
    if ok:
        print(f"Pushed {sport} team news → Supabase key={key}")
    else:
        print(f"Push failed for {sport} (check SUPABASE_SERVICE_ROLE_KEY in .env.local)")
    return ok


def main() -> None:
    p = argparse.ArgumentParser(description="Push team news JSON to Supabase")
    p.add_argument("--sport", choices=["NRL", "AFL", "nrl", "afl", "ALL"], default="ALL")
    args = p.parse_args()

    sports = ["NRL", "AFL"] if args.sport.upper() == "ALL" else [args.sport.upper()]
    for sport in sports:
        push_sport(sport)


if __name__ == "__main__":
    main()
