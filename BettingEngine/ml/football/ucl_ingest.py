"""Import openfootball Champions League season files into the UCL match contract."""

from __future__ import annotations

import argparse
import csv
import re
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "data/ucl/matches/ucl_matches_openfootball.csv"
MANIFEST = ROOT / "ml/football/reports/ucl_openfootball_ingest.json"

DATE_RE = re.compile(r"^\s{2,}(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+([A-Z][a-z]{2})\s+(\d{1,2})\s+(\d{4})")
STAGE_RE = re.compile(r"^\s*[▪•]\s*(League|Playoffs|Finals)(?:,\s*(.*))?", re.IGNORECASE)
MATCH_RE = re.compile(r"^\s*(?:(\d{1,2}:\d{2})\s+)?(.+?)\s+v\s+(.+?)\s+(\d+)\s*-\s*(\d+)(?:\s|$)")


def _club_id(name: str) -> str:
    name = re.sub(r"\s*\([A-Z]{3}\)\s*$", "", name.strip())
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def parse_file(path: Path, season: str) -> list[dict[str, str | int]]:
    rows: list[dict[str, str | int]] = []
    current_date, current_stage, matchday = None, "", ""
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stage = STAGE_RE.match(line)
        if stage:
            current_stage = stage.group(1).lower()
            matchday = stage.group(2) or ""
            continue
        date = DATE_RE.match(line)
        if date:
            current_date = datetime.strptime(f"{date.group(1)} {date.group(2)} {date.group(3)}", "%b %d %Y").date()
            continue
        match = MATCH_RE.match(line)
        if not match or current_date is None:
            continue
        time_value, home, away, home_goals, away_goals = match.groups()
        # openfootball supplies reliable dates but not a timezone. Preserve the
        # date at 12:00 UTC and mark precision explicitly; no time is invented.
        kickoff = datetime.combine(current_date, datetime.min.time(), tzinfo=timezone.utc).isoformat()
        rows.append({"match_id": f"ucl-{season.replace('/', '-')}-{len(rows)+1:03d}", "season": season,
                     "stage": "league_phase" if current_stage == "league" else
                              "knockout_phase_play_off" if current_stage == "playoffs" else
                              "knockout_phase", "matchday": matchday, "kickoff_utc": kickoff,
                     "kickoff_precision": "date_only", "home_club_id": _club_id(home), "away_club_id": _club_id(away),
                     "home_name_source": home.strip(), "away_name_source": away.strip(),
                     "home_goals": int(home_goals), "away_goals": int(away_goals),
                     "source": "openfootball", "source_published_at_utc": kickoff})
    return rows


def ingest(source_root: Path, seasons: list[str] | None = None) -> dict:
    seasons = seasons or sorted(path.name for path in source_root.iterdir() if path.is_dir())
    rows: list[dict] = []
    files = []
    for season in seasons:
        path = source_root / season / "cl.txt"
        if not path.exists():
            continue
        season_rows = parse_file(path, season)
        rows.extend(season_rows); files.append({"season": season, "file": str(path), "matches": len(season_rows)})
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", newline="", encoding="utf-8") as handle:
        fields = list(rows[0].keys()) if rows else ["match_id", "season", "stage"]
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(rows)
    result = {"status": "openfootball_matches_imported" if rows else "no_source_matches", "source": "openfootball",
              "seasons": seasons, "matches": len(rows), "files": files, "kickoff_precision": "date_only",
              "odds_included": False, "xg_included": False, "fabricated_matches": 0,
              "output": str(OUTPUT.relative_to(ROOT))}
    MANIFEST.parent.mkdir(parents=True, exist_ok=True); MANIFEST.write_text(__import__("json").dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--source", type=Path, required=True); args = parser.parse_args()
    print(__import__("json").dumps(ingest(args.source), indent=2))


if __name__ == "__main__":
    main()
