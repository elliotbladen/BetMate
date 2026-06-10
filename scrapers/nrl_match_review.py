"""
scrapers/nrl_match_review.py

Runs every Monday at 09:30 via Task Scheduler.
Captures two things from the weekend just gone:
  1. NRL Match Review Committee charges — parsed from NRL.com judiciary article
     (__NEXT_DATA__ JSON embedded in page) + RLZ weekly article search
  2. Fresh injuries — diff of current NRL casualty ward vs previous saved state

Outputs:
  data/nrl/match-review/latest.json             <- overwritten each run
  data/nrl/match-review/YYYY/round-N.json       <- permanent archive
  data/nrl/match-review/logs/scrape.log

Usage:
  uv run --with requests --with beautifulsoup4 python scrapers/nrl_match_review.py
  uv run --with requests --with beautifulsoup4 python scrapers/nrl_match_review.py --season 2026 --round 13
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT         = Path(__file__).resolve().parents[1]
BASE_DIR     = ROOT / "data" / "nrl" / "match-review"
INJURIES_DIR = ROOT / "data" / "nrl" / "injuries" / "processed"
LOG_DIR      = BASE_DIR / "logs"
LOG_PATH     = LOG_DIR / "scrape.log"

DEFAULT_ROUND_ONE_MONDAY = "2026-03-02"
TIMEOUT = 30

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "en-AU,en;q=0.9",
}

log = logging.getLogger(__name__)


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


def infer_round(round_one_monday: str) -> int:
    monday = datetime.strptime(round_one_monday, "%Y-%m-%d").date()
    today  = datetime.now().date()
    if today < monday:
        return 1
    return (today - monday).days // 7 + 1


def fetch_html(url: str) -> str | None:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        return resp.text
    except Exception as exc:
        log.warning("Fetch failed %s -- %s", url, exc)
        return None


def extract_next_data(html: str) -> dict:
    """Extract __NEXT_DATA__ JSON embedded in NRL.com Next.js pages."""
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
    if not m:
        return {}
    try:
        return json.loads(m.group(1))
    except Exception as exc:
        log.warning("Failed to parse __NEXT_DATA__: %s", exc)
        return {}


def flatten_text(obj, results=None) -> list[str]:
    """Recursively pull all string values from a nested JSON object."""
    if results is None:
        results = []
    if isinstance(obj, str) and len(obj.strip()) > 3:
        results.append(obj.strip())
    elif isinstance(obj, dict):
        for v in obj.values():
            flatten_text(v, results)
    elif isinstance(obj, list):
        for item in obj:
            flatten_text(item, results)
    return results


# ── Judiciary charges ─────────────────────────────────────────────────────────

def parse_judiciary_from_next_data(data: dict, target_round: int) -> list[dict]:
    """
    Finds the article body in __NEXT_DATA__ JSON and extracts charge rows
    for the target round section.
    """
    scraped_at = datetime.now(timezone.utc).isoformat()
    texts = flatten_text(data)

    # Find lines that look like charge entries
    # Typical format: "Player Name | Team | Grade N Description | $X fine or N games"
    charges: list[dict] = []
    in_round_section = False

    for line in texts:
        # Detect section headings for the target round
        if re.search(rf'\bRound\s*{target_round}\b', line, re.I):
            in_round_section = True
            continue
        # Stop at next round's section heading
        m = re.search(r'\bRound\s*(\d+)\b', line, re.I)
        if m and in_round_section and int(m.group(1)) != target_round:
            in_round_section = False

        if not in_round_section:
            continue

        # Skip lines that are too short or are just headings
        if len(line) < 20:
            continue

        # Lines with charge-like patterns: player names + grade/fine/suspension keywords
        if re.search(r'[Gg]rade|[Ff]ine|[Ss]uspension|[Bb]an|[Mm]atch|[Ww]eek|[Pp]lea', line):
            parts = [p.strip() for p in re.split(r'\s{2,}|\|', line) if p.strip()]
            charges.append({
                "round":      target_round,
                "player":     parts[0] if parts else "",
                "team":       parts[1] if len(parts) > 1 else "",
                "offence":    parts[2] if len(parts) > 2 else "",
                "penalty":    " | ".join(parts[3:]) if len(parts) > 3 else "",
                "raw":        line[:400],
                "scraped_at": scraped_at,
            })

    log.info("__NEXT_DATA__ judiciary: %d charge rows for Round %d", len(charges), target_round)
    return charges


def parse_judiciary_from_html(html: str, target_round: int) -> list[dict]:
    """
    Fallback: scan raw article HTML for charge patterns.
    Works when content is server-rendered in the HTML (not JS-injected).
    """
    soup = BeautifulSoup(html, "html.parser")
    scraped_at = datetime.now(timezone.utc).isoformat()
    charges: list[dict] = []
    in_section = False

    article_body = soup.find("article") or soup.find("div", class_=re.compile(r'article|content|body', re.I)) or soup

    for el in article_body.find_all(["h2", "h3", "h4", "p", "li", "tr"]):
        text = el.get_text(separator=" | ", strip=True)
        if not text:
            continue

        if re.search(rf'\bRound\s*{target_round}\b', text, re.I):
            in_section = True
            continue
        m = re.search(r'\bRound\s*(\d+)\b', text, re.I)
        if m and in_section and int(m.group(1)) != target_round:
            in_section = False

        if not in_section:
            continue

        if re.search(r'[Gg]rade|[Ff]ine|[Ss]uspension|[Bb]an|[Mm]atch\s+ban|[Pp]lea', text) and len(text) > 20:
            parts = [p.strip() for p in re.split(r'\s{2,}|\|', text) if p.strip()]
            if parts:
                charges.append({
                    "round":      target_round,
                    "player":     parts[0],
                    "team":       parts[1] if len(parts) > 1 else "",
                    "offence":    parts[2] if len(parts) > 2 else "",
                    "penalty":    " | ".join(parts[3:]) if len(parts) > 3 else "",
                    "raw":        text[:400],
                    "scraped_at": scraped_at,
                })

    log.info("HTML judiciary fallback: %d charge rows for Round %d", len(charges), target_round)
    return charges


def scrape_judiciary(season: int, round_number: int) -> list[dict]:
    url = (
        f"https://www.nrl.com/news/{season}/01/01/"
        f"nrl-judiciary-report-{season}/"
    )
    log.info("Fetching judiciary: %s", url)
    html = fetch_html(url)
    if not html:
        log.warning("Judiciary page unavailable")
        return []

    # Try __NEXT_DATA__ first (NRL.com is Next.js)
    data = extract_next_data(html)
    if data:
        charges = parse_judiciary_from_next_data(data, round_number)
        if charges:
            return charges

    # Fallback to HTML parsing
    return parse_judiciary_from_html(html, round_number)


# ── Fresh injuries via diff ───────────────────────────────────────────────────

def load_saved_injuries(round_number: int, season: int) -> set[tuple]:
    """
    Load previously saved injury records for the round BEFORE the target.
    Returns a set of (team, player) tuples representing who was already injured.
    """
    prev_round = round_number - 1
    candidates = [
        INJURIES_DIR / str(season) / f"round-{prev_round}-injuries.json",
        INJURIES_DIR / "latest-injuries.json",
    ]
    for path in candidates:
        if path.exists():
            try:
                records = json.loads(path.read_text(encoding="utf-8"))
                result = {(r.get("team", ""), r.get("player", "")) for r in records}
                log.info("Loaded %d prior injury records from %s", len(result), path.name)
                return result
            except Exception as exc:
                log.warning("Failed to load %s: %s", path, exc)
    log.warning("No prior injury file found — all injuries will appear as 'fresh'")
    return set()


def scrape_current_injuries(season: int, round_number: int) -> list[dict]:
    """Fetch and parse the NRL.com casualty ward — same source as nrl_injuries.py."""
    url = (
        f"https://www.nrl.com/news/{season}/01/01/"
        f"nrl-casualty-ward-how-your-club-is-shaping-heading-into-{season}/"
    )
    log.info("Fetching casualty ward: %s", url)
    html = fetch_html(url)
    if not html:
        log.warning("Casualty ward unavailable")
        return []

    # Try __NEXT_DATA__ first
    data = extract_next_data(html)
    texts = flatten_text(data) if data else []

    # Fall back to HTML scraping (same logic as nrl_injuries.py)
    soup = BeautifulSoup(html, "html.parser")
    scraped_at = datetime.now(timezone.utc).isoformat()
    records: list[dict] = []

    TEAM_MAP = {
        "broncos": "Brisbane Broncos", "raiders": "Canberra Raiders",
        "bulldogs": "Canterbury-Bankstown Bulldogs", "sharks": "Cronulla-Sutherland Sharks",
        "dolphins": "Dolphins", "titans": "Gold Coast Titans",
        "sea eagles": "Manly-Warringah Sea Eagles", "storm": "Melbourne Storm",
        "knights": "Newcastle Knights", "warriors": "New Zealand Warriors",
        "cowboys": "North Queensland Cowboys", "eels": "Parramatta Eels",
        "panthers": "Penrith Panthers", "rabbitohs": "South Sydney Rabbitohs",
        "dragons": "St. George Illawarra Dragons", "roosters": "Sydney Roosters",
        "wests tigers": "Wests Tigers", "tigers": "Wests Tigers",
    }

    current_team = None
    for el in soup.find_all(["h2", "h3", "h4", "li"]):
        if el.name in ("h2", "h3", "h4"):
            txt = el.get_text(strip=True).lower()
            current_team = TEAM_MAP.get(txt)
            continue
        if el.name == "li" and current_team:
            txt = el.get_text(strip=True)
            m = re.match(r"^(.+?)\s*\((.+)\)$", txt)
            if not m:
                continue
            player = m.group(1).strip()
            inner  = m.group(2).strip()
            if "," in inner:
                lc = inner.rfind(",")
                injury      = inner[:lc].strip()
                return_info = inner[lc + 1:].strip()
            else:
                injury      = inner
                return_info = "TBC"
            records.append({
                "team":        current_team,
                "player":      player,
                "injury":      injury,
                "return_info": return_info,
                "scraped_at":  scraped_at,
            })

    log.info("Casualty ward: %d total injury records", len(records))
    return records


def find_fresh_injuries(current: list[dict], prior_set: set[tuple]) -> list[dict]:
    """Return records in current that weren't in prior_set (team, player)."""
    fresh = []
    for rec in current:
        key = (rec.get("team", ""), rec.get("player", ""))
        if key not in prior_set:
            fresh.append(rec)
    log.info("Fresh injuries (not in prior state): %d", len(fresh))
    return fresh


# ── Main ──────────────────────────────────────────────────────────────────────

def scrape_and_save(season: int, round_number: int) -> dict:
    result = {
        "season":          season,
        "round":           round_number,
        "scraped_at":      datetime.now(timezone.utc).isoformat(),
        "charges":         [],
        "fresh_injuries":  [],
        "all_injuries":    [],
    }

    # 1. Judiciary charges
    result["charges"] = scrape_judiciary(season, round_number)

    # 2. Fresh injuries via diff
    prior_set = load_saved_injuries(round_number, season)
    current   = scrape_current_injuries(season, round_number)
    result["all_injuries"]   = current
    result["fresh_injuries"] = find_fresh_injuries(current, prior_set)

    # Write outputs
    versioned_dir = BASE_DIR / str(season)
    versioned_dir.mkdir(parents=True, exist_ok=True)
    archive_path = versioned_dir / f"round-{round_number}.json"
    archive_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    BASE_DIR.mkdir(parents=True, exist_ok=True)
    latest_path = BASE_DIR / "latest.json"
    latest_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    log.info("Saved %s", latest_path)
    log.info("Saved %s", archive_path)
    return result


def print_summary(result: dict) -> None:
    r = result["round"]
    print(f"\n{'='*60}")
    print(f"  NRL Match Review — Round {r} ({result['season']})")
    print(f"{'='*60}")

    charges = result.get("charges", [])
    print(f"\n--- Judiciary Charges ({len(charges)}) ---")
    if charges:
        for c in charges:
            print(f"  {c.get('player','?'):<28} {c.get('team',''):<32} {c.get('offence','')}")
            if c.get("penalty"):
                print(f"    Penalty: {c['penalty']}")
    else:
        print("  None found (check judiciary page manually if expected)")

    fresh = result.get("fresh_injuries", [])
    print(f"\n--- Fresh Injuries — new since R{r-1} ({len(fresh)}) ---")
    if fresh:
        for inj in fresh:
            print(f"  {inj.get('team','?'):<32} {inj.get('player',''):<28} {inj.get('injury','')} ({inj.get('return_info','')})")
    else:
        print("  None detected (or no prior state to diff against)")

    print(f"\nSaved  -> data/nrl/match-review/latest.json")
    print(f"Archive-> data/nrl/match-review/{result['season']}/round-{r}.json")


def main() -> None:
    setup_logging()
    p = argparse.ArgumentParser(
        description="Monday scraper: NRL MRC judiciary charges + fresh injury diff"
    )
    p.add_argument("--season",           type=int, default=2026)
    p.add_argument("--round",            dest="round_number", type=int, default=0)
    p.add_argument("--round-one-monday", default=DEFAULT_ROUND_ONE_MONDAY)
    args = p.parse_args()

    round_number = args.round_number or infer_round(args.round_one_monday)
    log.info("Season=%d Round=%d", args.season, round_number)

    result = scrape_and_save(args.season, round_number)
    print_summary(result)
    sys.exit(0)


if __name__ == "__main__":
    main()
