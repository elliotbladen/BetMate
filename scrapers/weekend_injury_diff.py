"""
scrapers/weekend_injury_diff.py

Monday morning injury diff.
Loads the stored latest-injuries.json (what we knew BEFORE the weekend),
scrapes fresh, and reports only players that are NEW to the list.

Also surfaces:
  - Status escalations  (doubtful -> out)
  - Recoveries          (was listed, no longer appears)

Outputs:
  data/nrl/injuries/processed/new-this-week.json   (NRL diff result)
  data/afl/injuries/processed/new-this-week.json   (AFL diff result)
  data/nrl/injuries/processed/latest-injuries.json (updated full list)
  data/afl/injuries/processed/latest-injuries.json (updated full list)

Usage:
  uv run --with requests --with beautifulsoup4 python scrapers/weekend_injury_diff.py
  uv run --with requests --with beautifulsoup4 python scrapers/weekend_injury_diff.py --sport NRL
  uv run --with requests --with beautifulsoup4 python scrapers/weekend_injury_diff.py --sport AFL
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Make sibling scrapers importable
sys.path.insert(0, str(Path(__file__).resolve().parent))

import nrl_injuries as nrl
import afl_injuries as afl

LOG_DIR  = ROOT / "data" / "injuries" / "logs"
LOG_PATH = LOG_DIR / "weekend_diff.log"

log = logging.getLogger(__name__)


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
# Diff helpers
# ---------------------------------------------------------------------------

def load_known(latest_path: Path) -> list[dict]:
    if not latest_path.exists():
        log.info("No prior injury file at %s -- all injuries will be treated as new", latest_path)
        return []
    try:
        data = json.loads(latest_path.read_text(encoding="utf-8"))
        log.info("Loaded %d known injuries from %s", len(data), latest_path)
        return data
    except Exception as exc:
        log.warning("Could not read %s -- %s", latest_path, exc)
        return []


def build_index(records: list[dict]) -> dict[tuple[str, str], str]:
    """(team, player) -> status"""
    return {(r["team"], r["player"]): r.get("status", "out") for r in records}


# Keywords that indicate a player is resting, not injured.
# These should never appear in team news — they'll be back next round.
_REST_KEYWORDS = {"rested", "rest", "managed", "load management"}

def is_resting(record: dict) -> bool:
    notes  = record.get("notes", "").lower()
    injury = notes.split(" | return:")[0].strip() if " | return:" in notes else notes.strip()
    return injury in _REST_KEYWORDS


def compute_diff(
    known: list[dict],
    fresh: list[dict],
) -> tuple[list[dict], list[dict], list[dict]]:
    """
    Returns:
      new_injuries   -- players absent from known entirely (excluding rested)
      worse          -- players in known as 'doubtful' but now 'out' (excluding rested)
      cleared        -- players in known but absent from fresh (recovered/returned)
    """
    # Strip resting players before diffing — they are not injuries
    fresh = [r for r in fresh if not is_resting(r)]

    known_idx = build_index(known)
    fresh_idx  = build_index(fresh)

    new_injuries = [
        r for r in fresh
        if (r["team"], r["player"]) not in known_idx
    ]

    worse = [
        {**r, "previous_status": "doubtful"}
        for r in fresh
        if known_idx.get((r["team"], r["player"])) == "doubtful"
        and r.get("status") == "out"
    ]

    cleared = [
        r for r in known
        if (r["team"], r["player"]) not in fresh_idx
    ]

    return new_injuries, worse, cleared


# ---------------------------------------------------------------------------
# Console summary
# ---------------------------------------------------------------------------

def print_summary(
    sport: str,
    new_injuries: list[dict],
    worse: list[dict],
    cleared: list[dict],
) -> None:
    today = datetime.now().strftime("%A %Y-%m-%d")
    bar = "=" * 52

    print(f"\n{bar}")
    print(f"  {sport} INJURY UPDATE -- {today}")
    print(bar)

    if not new_injuries and not worse and not cleared:
        print("  No changes since last scrape.\n")
        return

    # ---- New injuries ----
    if new_injuries:
        print(f"\n  NEW ({len(new_injuries)} players)")
        print("  " + "-" * 48)
        _print_group(new_injuries, prefix="[NEW]")

    # ---- Status escalations ----
    if worse:
        print(f"\n  WORSENED ({len(worse)} players — was doubtful, now out)")
        print("  " + "-" * 48)
        _print_group(worse, prefix="[WORSE]")

    # ---- Recoveries ----
    if cleared:
        print(f"\n  RETURNED / CLEARED ({len(cleared)} players)")
        print("  " + "-" * 48)
        _print_group(cleared, prefix="[BACK]")

    total_flag = len(new_injuries) + len(worse)
    print(f"\n  {total_flag} new/worsened  |  {len(cleared)} cleared\n")


def _print_group(records: list[dict], prefix: str) -> None:
    teams: dict[str, list[str]] = {}
    for r in records:
        teams.setdefault(r["team"], []).append(r)

    for team in sorted(teams):
        print(f"\n  {team}")
        for r in teams[team]:
            status = r.get("status", "out").upper()
            notes  = r.get("notes", "")
            print(f"    {prefix}  {r['player']}  [{status}]  {notes}")


# ---------------------------------------------------------------------------
# Per-sport runners
# ---------------------------------------------------------------------------

def write_diff_json(path: Path, new_injuries: list[dict], worse: list[dict], cleared: list[dict]) -> None:
    path.write_text(
        json.dumps(
            {
                "scraped_at": datetime.now(timezone.utc).isoformat(),
                "new":        new_injuries,
                "worsened":   worse,
                "cleared":    cleared,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    log.info("Wrote diff to %s", path)


def run_nrl(season: int, round_number: int) -> None:
    log.info("--- NRL injury diff  season=%d  round=%d ---", season, round_number)

    latest_path = ROOT / "data" / "nrl" / "injuries" / "processed" / "latest-injuries.json"
    known = load_known(latest_path)

    url  = nrl.nrl_casualty_url(season)
    html = nrl.fetch_html(url)
    if not html:
        log.error("NRL: fetch failed -- %s", url)
        print("\n[NRL] ERROR: Could not fetch the casualty ward page. Skipping NRL diff.")
        return

    fresh = nrl.parse_nrl_casualty_ward(html, season, round_number)
    log.info("NRL: scraped %d fresh records", len(fresh))

    new_injuries, worse, cleared = compute_diff(known, fresh)

    diff_path = latest_path.parent / "new-this-week.json"
    write_diff_json(diff_path, new_injuries, worse, cleared)

    # Update full latest + round-specific file
    nrl.write_outputs(fresh, html, season, round_number, url)

    print_summary("NRL", new_injuries, worse, cleared)


def run_afl(season: int, round_number: int) -> None:
    log.info("--- AFL injury diff  season=%d  round=%d ---", season, round_number)

    latest_path = ROOT / "data" / "afl" / "injuries" / "processed" / "latest-injuries.json"
    known = load_known(latest_path)

    html = afl.fetch_html(afl.URL)
    if not html:
        log.error("AFL: fetch failed -- %s", afl.URL)
        print("\n[AFL] ERROR: Could not fetch the footywire injury page. Skipping AFL diff.")
        return

    fresh = afl.parse_injuries(html, season, round_number)
    log.info("AFL: scraped %d fresh records", len(fresh))

    new_injuries, worse, cleared = compute_diff(known, fresh)

    diff_path = latest_path.parent / "new-this-week.json"
    write_diff_json(diff_path, new_injuries, worse, cleared)

    # Update full latest + round-specific file
    afl.write_outputs(fresh, html, season, round_number)

    print_summary("AFL", new_injuries, worse, cleared)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    setup_logging()

    p = argparse.ArgumentParser(
        description="Monday injury diff — show only new injuries since last scrape"
    )
    p.add_argument("--sport", choices=["NRL", "AFL", "both"], default="both",
                   help="Which sport to diff (default: both)")
    p.add_argument("--season", type=int, default=2026)
    p.add_argument("--nrl-round", type=int, default=0,
                   help="Override NRL round (default: inferred from date)")
    p.add_argument("--afl-round", type=int, default=0,
                   help="Override AFL round (default: inferred from date)")
    p.add_argument("--nrl-round-one-monday", default="2026-03-02")
    p.add_argument("--afl-round-one-thursday", default="2026-03-06")
    args = p.parse_args()

    nrl_round = args.nrl_round or nrl.infer_round(args.nrl_round_one_monday)
    afl_round = args.afl_round or afl.infer_round(args.afl_round_one_thursday)

    log.info("weekend_injury_diff  sport=%s  nrl_round=%d  afl_round=%d",
             args.sport, nrl_round, afl_round)

    if args.sport in ("NRL", "both"):
        run_nrl(args.season, nrl_round)

    if args.sport in ("AFL", "both"):
        run_afl(args.season, afl_round)

    log.info("Done.")


if __name__ == "__main__":
    main()
