"""
scripts/update_team_news_injuries.py

Populates the team news injury section from this weekend's NEW injuries only.
Source: data/{sport}/injuries/processed/new-this-week.json (diff output)

- Takes the 'new' and 'worsened' arrays — players that appeared fresh this weekend
- Replaces all "type: injury" items in team news with just those players
- Preserves all "type: suspension" items (manually maintained)
- Pushes to Supabase (team_news_nrl / team_news_afl)

Usage:
  uv run --with requests python scripts/update_team_news_injuries.py
  uv run --with requests python scripts/update_team_news_injuries.py --sport NRL
  uv run --with requests python scripts/update_team_news_injuries.py --sport AFL
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, date, timezone
from pathlib import Path

import requests

ROOT     = Path(__file__).resolve().parents[1]
ENV      = ROOT / ".env.local"
LOG_DIR  = ROOT / "data" / "injuries" / "logs"
LOG_PATH = LOG_DIR / "team_news_update.log"

log = logging.getLogger(__name__)

SEVERITY_MAP = {"elite": "high", "key": "medium", "rotation": "low"}

NRL_ROUND_ONE_MONDAY   = "2026-03-02"
AFL_ROUND_ONE_THURSDAY = "2026-03-06"

# NRL injury scraper uses official names (hyphens/periods).
# UI lookup keys must match the Odds API names exactly.
NRL_NAME_TO_ODDS_API: dict[str, str] = {
    "Canterbury-Bankstown Bulldogs": "Canterbury Bulldogs",
    "Cronulla-Sutherland Sharks":    "Cronulla Sutherland Sharks",
    "Manly-Warringah Sea Eagles":    "Manly Warringah Sea Eagles",
    "St. George Illawarra Dragons":  "St George Illawarra Dragons",
}


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def setup_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(LOG_PATH, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
        force=True,
    )


# ---------------------------------------------------------------------------
# Env + Supabase
# ---------------------------------------------------------------------------

def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    if not ENV.exists():
        return env
    for line in ENV.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def push_to_supabase(env: dict, key: str, data: dict) -> bool:
    url     = env.get("NEXT_PUBLIC_SUPABASE_URL", "").rstrip("/")
    api_key = env.get("SUPABASE_SERVICE_ROLE_KEY") or env.get("NEXT_PUBLIC_SUPABASE_ANON_KEY", "")
    if not url or not api_key:
        log.warning("Supabase credentials not found — skipping push")
        return False
    headers = {
        "apikey": api_key,
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates",
    }
    try:
        r = requests.post(
            f"{url}/rest/v1/betmate_data_store",
            headers=headers,
            json={"key": key, "data": data},
            timeout=15,
        )
        if r.status_code in (200, 201):
            log.info("Pushed %s to Supabase (%d)", key, r.status_code)
            return True
        log.error("Supabase push failed %s: %d %s", key, r.status_code, r.text[:200])
        return False
    except Exception as exc:
        log.error("Supabase push exception %s: %s", key, exc)
        return False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def normalise_nrl_team(name: str) -> str:
    return NRL_NAME_TO_ODDS_API.get(name, name)


def infer_round(round_one: str) -> int:
    ref   = datetime.strptime(round_one, "%Y-%m-%d").date()
    today = datetime.now().date()
    if today < ref:
        return 1
    return (today - ref).days // 7 + 1


def format_detail(notes: str, worsened: bool = False) -> str:
    """'Knee | Return: Round 15' -> 'Knee — return Round 15'"""
    prefix = "Was doubtful — now out. " if worsened else ""
    if " | Return: " in notes:
        injury, ret = notes.split(" | Return: ", 1)
        ret = ret.strip()
        if not ret or ret.upper() in ("TBC", "INDEFINITE", ""):
            return f"{prefix}{injury.strip()} — return TBC"
        return f"{prefix}{injury.strip()} — return {ret}"
    return f"{prefix}{notes.strip()}" if notes.strip() else "Injury — return TBC"


def injury_to_item(record: dict, worsened: bool = False) -> dict:
    tier     = record.get("importance_tier", "rotation")
    severity = SEVERITY_MAP.get(tier, "low")
    if record.get("status") == "doubtful" and severity == "high":
        severity = "medium"
    return {
        "type":     "injury",
        "player":   record["player"],
        "detail":   format_detail(record.get("notes", ""), worsened=worsened),
        "severity": severity,
    }


def compute_team_status(items: list[dict]) -> str:
    for item in items:
        if item.get("severity") in ("high", "medium"):
            return "alert"
    return "monitor"


# ---------------------------------------------------------------------------
# Core rebuild — weekend batch only
# ---------------------------------------------------------------------------

def rebuild_from_weekend(
    sport: str,
    new_injuries: list[dict],
    worsened: list[dict],
    current_news: dict,
    round_number: int,
    season: int,
) -> dict:
    """
    Build team news from ONLY this weekend's new/worsened injuries.
    Suspensions in current_news are preserved.
    Old injury items are dropped — replaced by this weekend's batch.
    """
    # All weekend records combined, tagged
    weekend_items_by_team: dict[str, list[dict]] = {}
    for r in new_injuries:
        team = r["team"]
        weekend_items_by_team.setdefault(team, []).append(injury_to_item(r, worsened=False))
    for r in worsened:
        team = r["team"]
        weekend_items_by_team.setdefault(team, []).append(injury_to_item(r, worsened=True))

    # Collect all team names that matter: teams with weekend injuries + teams that have suspensions
    all_teams: set[str] = set(weekend_items_by_team.keys())
    for team, data in current_news.get("teams", {}).items():
        if any(i.get("type") == "suspension" for i in data.get("items", [])):
            all_teams.add(team)

    teams_out: dict[str, dict] = {}
    for team in sorted(all_teams):
        suspensions = [
            i for i in current_news.get("teams", {}).get(team, {}).get("items", [])
            if i.get("type") == "suspension"
        ]
        injury_items = weekend_items_by_team.get(team, [])
        items = injury_items + suspensions
        if not items:
            continue
        teams_out[team] = {
            "status": compute_team_status(items),
            "items":  items,
        }

    log.info(
        "%s team news (weekend batch): %d teams, %d fresh injuries",
        sport, len(teams_out),
        sum(len(v) for v in weekend_items_by_team.values()),
    )

    return {
        "sport":      sport,
        "round":      round_number,
        "season":     season,
        "updated":    date.today().isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "teams":      teams_out,
    }


# ---------------------------------------------------------------------------
# Per-sport runner
# ---------------------------------------------------------------------------

def run_sport(
    sport: str,
    diff_path: Path,
    news_path: Path,
    supabase_key: str,
    round_number: int,
    season: int,
    env: dict,
) -> None:
    log.info("--- %s team news (weekend injuries)  round=%d ---", sport, round_number)

    if not diff_path.exists():
        log.error("%s: diff file not found: %s — run weekend_injury_diff.py first", sport, diff_path)
        return

    diff = json.loads(diff_path.read_text(encoding="utf-8"))
    new_injuries: list[dict] = diff.get("new", [])
    worsened:     list[dict] = diff.get("worsened", [])
    log.info("%s: %d new, %d worsened this weekend", sport, len(new_injuries), len(worsened))

    # Normalise NRL team names to Odds API format
    if sport == "NRL":
        for r in new_injuries + worsened:
            r["team"] = normalise_nrl_team(r["team"])

    # Load current news to preserve any suspension items
    current_news: dict = {}
    if news_path.exists():
        try:
            current_news = json.loads(news_path.read_text(encoding="utf-8"))
            if sport == "NRL" and "teams" in current_news:
                current_news["teams"] = {
                    normalise_nrl_team(k): v
                    for k, v in current_news["teams"].items()
                }
        except Exception as exc:
            log.warning("Could not read %s: %s", news_path, exc)

    updated = rebuild_from_weekend(
        sport, new_injuries, worsened, current_news, round_number, season
    )

    news_path.parent.mkdir(parents=True, exist_ok=True)
    news_path.write_text(json.dumps(updated, indent=2, ensure_ascii=False), encoding="utf-8")
    log.info("Wrote %s", news_path)

    # Dated archive copy -- latest.json gets overwritten every run, but the
    # market-event log (build_market_event_log.py) needs a timestamped history
    # of every update to know when team news actually changed.
    archive_dir = ROOT / "data" / sport.lower() / "team-news" / "archive" / str(season)
    archive_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
    archive_path = archive_dir / f"r{round_number}_{stamp}.json"
    archive_path.write_text(json.dumps(updated, indent=2, ensure_ascii=False), encoding="utf-8")
    log.info("Archived %s", archive_path)

    push_to_supabase(env, supabase_key, updated)

    total = len(new_injuries) + len(worsened)
    if total == 0:
        print(f"\n  {sport}: no new weekend injuries this round.")
    else:
        alert_teams = [t for t, d in updated["teams"].items() if d["status"] == "alert"]
        print(f"\n  {sport}: {total} weekend injuries across {len(updated['teams'])} teams")
        if alert_teams:
            print(f"  Alert teams: {', '.join(alert_teams)}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    setup_logging()
    p = argparse.ArgumentParser(description="Update team news with this weekend's fresh injuries")
    p.add_argument("--sport", choices=["NRL", "AFL", "both"], default="both")
    p.add_argument("--season", type=int, default=2026)
    p.add_argument("--nrl-round", type=int, default=0)
    p.add_argument("--afl-round", type=int, default=0)
    args = p.parse_args()

    env       = load_env()
    nrl_round = args.nrl_round or infer_round(NRL_ROUND_ONE_MONDAY)
    afl_round = args.afl_round or infer_round(AFL_ROUND_ONE_THURSDAY)

    if args.sport in ("NRL", "both"):
        run_sport(
            sport        = "NRL",
            diff_path    = ROOT / "data/nrl/injuries/processed/new-this-week.json",
            news_path    = ROOT / "data/nrl/team-news/latest.json",
            supabase_key = "team_news_nrl",
            round_number = nrl_round,
            season       = args.season,
            env          = env,
        )

    if args.sport in ("AFL", "both"):
        run_sport(
            sport        = "AFL",
            diff_path    = ROOT / "data/afl/injuries/processed/new-this-week.json",
            news_path    = ROOT / "data/afl/team-news/latest.json",
            supabase_key = "team_news_afl",
            round_number = afl_round,
            season       = args.season,
            env          = env,
        )

    log.info("Done.")


if __name__ == "__main__":
    main()
