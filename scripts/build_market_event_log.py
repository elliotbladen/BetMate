"""
scripts/build_market_event_log.py

Builds a unified, timestamped log of "market-moving events" — injury news,
emotional flags, team news — by scanning the dated archives each scraper
already writes. This is the causal side of the line-movement tagging system:
paired against data/odds_movements/deltas/*.csv (see compute_snapshot_deltas.py)
and joined by tag_odds_movements.py.

Sources (per sport):
  data/{sport}/injuries/processed/{season}/round-*-injuries.json   (per-player, has scraped_at)
  data/{sport}/emotional/processed/{season}/round-*.json           (per-flag, file-level scraped_at)
  data/{sport}/team-news/archive/{season}/*.json                   (added by this project — see
                                                                     update_team_news_injuries.py patch)

Output:
  data/market_events/{season}_events.csv
  Columns: scraped_at, sport, event_type, team, player, detail

Usage:
  uv run python scripts/build_market_event_log.py --season 2026
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIELDNAMES = ["scraped_at", "sport", "event_type", "team", "player", "detail"]


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def collect_injury_events(sport: str, season: int) -> list[dict]:
    events = []
    base = ROOT / "data" / sport.lower() / "injuries" / "processed" / str(season)
    if not base.exists():
        return events
    for path in sorted(base.glob("round-*-injuries.json")):
        records = load_json(path)
        if not isinstance(records, list):
            continue
        for r in records:
            scraped_at = r.get("scraped_at")
            if not scraped_at:
                continue
            events.append({
                "scraped_at": scraped_at,
                "sport": sport.upper(),
                "event_type": "injury",
                "team": r.get("team", ""),
                "player": r.get("player", ""),
                "detail": f"{r.get('status','')}: {r.get('notes', r.get('injury',''))}".strip(),
            })
    return events


def collect_emotional_events(sport: str, season: int) -> list[dict]:
    events = []
    base = ROOT / "data" / sport.lower() / "emotional" / "processed" / str(season)
    if not base.exists():
        return events
    import datetime as _dt
    for path in sorted(base.glob("round-*.json")):
        payload = load_json(path)
        flags = payload if isinstance(payload, list) else (payload or {}).get("flags", [])
        if not flags:
            continue
        # file-level scraped_at fallback if payload is a dict with metadata;
        # otherwise fall back to the file's mtime (plain-list archives, like
        # the current emotional round files, don't embed a timestamp).
        file_scraped_at = (payload or {}).get("scraped_at") if isinstance(payload, dict) else None
        if not file_scraped_at:
            file_scraped_at = _dt.datetime.fromtimestamp(
                path.stat().st_mtime, tz=_dt.timezone.utc
            ).isoformat()
        for f in flags:
            scraped_at = f.get("scraped_at") or file_scraped_at
            if not scraped_at:
                continue
            events.append({
                "scraped_at": scraped_at,
                "sport": sport.upper(),
                "event_type": f"emotional_{f.get('flag_type','flag')}",
                "team": f.get("team", ""),
                "player": f.get("player_name", ""),
                "detail": f"{f.get('flag_strength','')}: {f.get('notes','')}".strip(),
            })
    return events


def collect_team_news_events(sport: str, season: int) -> list[dict]:
    """team-news 'teams' is a dict keyed by team name -> {status, items: [...]}."""
    import datetime as _dt
    events = []
    base = ROOT / "data" / sport.lower() / "team-news" / "archive" / str(season)
    if not base.exists():
        return events
    for path in sorted(base.glob("*.json")):
        payload = load_json(path)
        if not isinstance(payload, dict):
            continue
        scraped_at = payload.get("updated_at") or payload.get("updated") or payload.get("scraped_at")
        if not scraped_at:
            scraped_at = _dt.datetime.fromtimestamp(
                path.stat().st_mtime, tz=_dt.timezone.utc
            ).isoformat()
        for team, entry in (payload.get("teams") or {}).items():
            for item in entry.get("items", []):
                events.append({
                    "scraped_at": scraped_at,
                    "sport": sport.upper(),
                    "event_type": f"team_news_{item.get('type','other')}",
                    "team": team,
                    "player": item.get("player", ""),
                    "detail": item.get("detail", ""),
                })
    return events


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--season", type=int, default=2026)
    args = ap.parse_args()

    all_events = []
    for sport in ("nrl", "afl"):
        all_events += collect_injury_events(sport, args.season)
        all_events += collect_emotional_events(sport, args.season)
        all_events += collect_team_news_events(sport, args.season)

    all_events.sort(key=lambda e: e["scraped_at"])

    out_dir = ROOT / "data" / "market_events"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{args.season}_events.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDNAMES)
        w.writeheader()
        w.writerows(all_events)

    print(f"Wrote {len(all_events)} events -> {out_path}")
    by_type: dict[str, int] = {}
    for e in all_events:
        by_type[e["event_type"]] = by_type.get(e["event_type"], 0) + 1
    for k, v in sorted(by_type.items()):
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
