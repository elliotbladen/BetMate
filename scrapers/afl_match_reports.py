"""
scrapers/afl_match_reports.py

Scrapes the Fox Sports AFL Round Report Card and individual game report pages.
Extracts injury mentions per team from post-game write-ups.

Why Fox Sports instead of footywire/AFL.com.au:
  - Fox Sports is server-rendered (no JS required)
  - Report Card posted Monday afternoon, covers every team
  - Individual game pages available immediately after each game
  - AFL.com.au/footywire injury lists don't update until Tue/Wed training

Output:
  data/afl/injuries/processed/new-this-week.json   (same format as NRL diff)
  data/afl/injuries/processed/latest-injuries.json (updated with newly found players)
  data/afl/injuries/logs/match_reports.log

Usage:
  uv run --with requests --with beautifulsoup4 python scrapers/afl_match_reports.py
  uv run --with requests --with beautifulsoup4 python scrapers/afl_match_reports.py --round 12
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from datetime import datetime, date, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT          = Path(__file__).resolve().parents[1]
BASE_DIR      = ROOT / "data" / "afl" / "injuries"
PROCESSED_DIR = BASE_DIR / "processed"
LOG_DIR       = BASE_DIR / "logs"
LOG_PATH      = LOG_DIR / "match_reports.log"

DEFAULT_ROUND_ONE_THURSDAY = "2026-03-06"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
}

# Fox Sports section headers -> Odds API team names
FOX_TEAM_MAP: dict[str, str] = {
    "ADELAIDE":                  "Adelaide Crows",
    "ADELAIDE CROWS":            "Adelaide Crows",
    "BRISBANE":                  "Brisbane Lions",
    "BRISBANE LIONS":            "Brisbane Lions",
    "CARLTON":                   "Carlton Blues",
    "CARLTON BLUES":             "Carlton Blues",
    "COLLINGWOOD":               "Collingwood Magpies",
    "COLLINGWOOD MAGPIES":       "Collingwood Magpies",
    "ESSENDON":                  "Essendon Bombers",
    "ESSENDON BOMBERS":          "Essendon Bombers",
    "FREMANTLE":                 "Fremantle Dockers",
    "FREMANTLE DOCKERS":         "Fremantle Dockers",
    "GEELONG":                   "Geelong Cats",
    "GEELONG CATS":              "Geelong Cats",
    "GOLD COAST":                "Gold Coast Suns",
    "GOLD COAST SUNS":           "Gold Coast Suns",
    "GWS":                       "Greater Western Sydney Giants",
    "GWS GIANTS":                "Greater Western Sydney Giants",
    "GREATER WESTERN SYDNEY":    "Greater Western Sydney Giants",
    "HAWTHORN":                  "Hawthorn Hawks",
    "HAWTHORN HAWKS":            "Hawthorn Hawks",
    "MELBOURNE":                 "Melbourne Demons",
    "MELBOURNE DEMONS":          "Melbourne Demons",
    "NORTH MELBOURNE":           "North Melbourne Kangaroos",
    "NORTH MELBOURNE KANGAROOS": "North Melbourne Kangaroos",
    "PORT ADELAIDE":             "Port Adelaide Power",
    "PORT ADELAIDE POWER":       "Port Adelaide Power",
    "RICHMOND":                  "Richmond Tigers",
    "RICHMOND TIGERS":           "Richmond Tigers",
    "ST KILDA":                  "St Kilda Saints",
    "ST KILDA SAINTS":           "St Kilda Saints",
    "SYDNEY":                    "Sydney Swans",
    "SYDNEY SWANS":              "Sydney Swans",
    "WEST COAST":                "West Coast Eagles",
    "WEST COAST EAGLES":         "West Coast Eagles",
    "WESTERN BULLDOGS":          "Western Bulldogs",
    "BULLDOGS":                  "Western Bulldogs",
}

# Injury-related keywords that flag a sentence as worth extracting
INJURY_RE = re.compile(
    r'\b(injur\w*|hamstring|knee|ankle|concuss\w*|subbed off|medical sub|substitut\w*|'
    r'miss(?:ing|ed)|out for|left the field|didn\'t return|failed to finish|calf|'
    r'shoulder|quad|groin|rib|fractur\w*|strain\w*|soreness|went down|'
    r'managed his|managing\b|late withdrawal|withdrew)\b',
    re.I,
)

# Known non-injury "miss" contexts to skip
SKIP_RE = re.compile(
    r'\b(miss(?:ing|ed) (?:a )?(?:shot|chance|goal|kick|target|tackle|the ball|mark|handball))\b',
    re.I,
)

# Resting / load management — not real injuries
REST_RE = re.compile(r'\b(rested|load management|managed\s+(?:his|her|their)\s+workload)\b', re.I)

# Proper noun pattern for potential player names (First Last, or First Second Last)
PROPER_NOUN_RE = re.compile(
    r'\b([A-Z][a-z]+(?:-[A-Z][a-z]+)?(?:\s+[A-Z][a-z]+(?:-[A-Z][a-z]+)?){1,2})\b'
)

# Words that look like proper nouns but are not player names
NON_PLAYER_WORDS = {
    "Fox Sports", "AFL Round", "Round", "The Crows", "The Lions", "The Blues",
    "The Magpies", "The Bombers", "The Dockers", "The Cats", "The Suns",
    "The Giants", "The Hawks", "The Demons", "The Kangaroos", "The Power",
    "The Tigers", "The Saints", "The Swans", "The Eagles", "The Bulldogs",
    "Report Card", "Match Centre", "Kayo Sports",
    "Sam Mitchell", "Chris Fagan", "Ross Lyon", "Michael Voss", "Dean Solomon",
    "Ken Hinkley", "Damien Hardwick", "Adam Simpson", "Luke Beveridge",
    "Craig McRae", "Simon Goodwin", "Alastair Clarkson", "David Noble",
    "West Coast", "Gold Coast", "Port Adelaide", "North Melbourne",
    "Greater Western", "New South",
}

# Single-word team nicknames that sometimes appear as prefixes before player names
# e.g. "Lion Lachie Neale" → should strip "Lion" to get "Lachie Neale"
TEAM_NICKNAME_PREFIXES = {
    "Lion", "Bomber", "Roo", "Kangaroo", "Magpie", "Cat", "Dog", "Bulldog",
    "Hawk", "Demon", "Saint", "Swan", "Eagle", "Tiger", "Crow", "Docker",
    "Giant", "Sun", "Power", "Pie",
}

# Sentence patterns that mean the player named is from the OPPONENT, not the current section team.
# These cross-team mentions should be skipped to avoid wrong team attribution.
OPPOSING_MENTION_RE = re.compile(
    r'\b(against|opponent|rival|other|missing|without)\b.{0,60}',
    re.I
)

# Injury type keywords to extract from sentence context
INJURY_TYPE_WORDS = [
    "hamstring", "knee", "ankle", "concussion", "calf", "shoulder",
    "quad", "groin", "rib", "foot", "wrist", "back", "hip", "head knock",
    "fracture", "strain", "soreness", "achilles", "collarbone",
]

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
# Round inference
# ---------------------------------------------------------------------------

def infer_round(round_one_thursday: str) -> int:
    ref   = datetime.strptime(round_one_thursday, "%Y-%m-%d").date()
    today = datetime.now().date()
    if today < ref:
        return 1
    return (today - ref).days // 7 + 1


def latest_completed_afl_round(year: int = 2026) -> int:
    """Ask Squiggle for the highest round number that has completed games."""
    try:
        r = requests.get(
            f"https://api.squiggle.com.au/?q=games;year={year}",
            headers=HEADERS, timeout=10,
        )
        games = r.json().get("games", [])
        completed = [g["round"] for g in games if g.get("complete") == 100]
        if completed:
            return max(completed)
    except Exception as exc:
        log.warning("Squiggle round lookup failed: %s", exc)
    return infer_round(DEFAULT_ROUND_ONE_THURSDAY) - 1


# ---------------------------------------------------------------------------
# Fetching
# ---------------------------------------------------------------------------

def fetch(url: str) -> str | None:
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()
        return r.text
    except Exception as exc:
        log.warning("Fetch failed %s -- %s", url, exc)
        return None


def find_report_card_url(round_number: int) -> str | None:
    """
    Scrapes Fox Sports AFL front page looking for the Round N Report Card article.
    """
    html = fetch("https://www.foxsports.com.au/afl")
    if not html:
        return None
    soup = BeautifulSoup(html, "html.parser")
    pattern = re.compile(rf"round-{round_number}.*report-card|report-card.*round-{round_number}", re.I)
    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        if pattern.search(href):
            return href
    return None


def find_game_report_urls(round_number: int) -> list[str]:
    """
    Finds individual game report (live blog) URLs for the round.
    These are available immediately after each game.
    """
    html = fetch("https://www.foxsports.com.au/afl")
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    pattern = re.compile(rf"round-{round_number}.*(live-scores|live-score|match-report|news-story)", re.I)
    urls = set()
    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        if "foxsports.com.au/afl" in href and pattern.search(href):
            urls.add(href)
    return list(urls)


# ---------------------------------------------------------------------------
# Article parsing
# ---------------------------------------------------------------------------

def split_into_team_sections(text: str) -> dict[str, str]:
    """
    Splits the article body into per-team sections using ALL CAPS headers.
    Returns {odds_api_team_name: section_text}.
    """
    # Identify ALL CAPS lines that match known team names
    sections: dict[str, str] = {}
    current_team: str | None = None
    current_lines: list[str] = []

    for line in text.split("\n"):
        stripped = line.strip()
        upper = stripped.upper()
        if upper in FOX_TEAM_MAP and stripped.isupper() and len(stripped) < 35:
            # Save previous section
            if current_team and current_lines:
                sections[current_team] = " ".join(current_lines)
            current_team = FOX_TEAM_MAP[upper]
            current_lines = []
        elif current_team:
            current_lines.append(stripped)

    if current_team and current_lines:
        sections[current_team] = " ".join(current_lines)

    return sections


def extract_injury_type(sentence: str) -> str:
    """Best-effort injury type extraction from sentence text."""
    low = sentence.lower()
    for word in INJURY_TYPE_WORDS:
        if word in low:
            return word.title()
    if re.search(r'\bconcuss', low):
        return "Concussion"
    if re.search(r'\bmedical sub', low):
        return "Medical substitution"
    if re.search(r'\bleft the field|didn\'t return|failed to finish', low):
        return "Unknown"
    return "Unknown"


def extract_players_from_sentence(sentence: str) -> list[str]:
    """Extract candidate player names (proper noun pairs) from a sentence."""
    candidates = []
    for m in PROPER_NOUN_RE.finditer(sentence):
        name = m.group(1).strip()
        # Strip leading team nickname prefix (e.g. "Lion Lachie Neale" -> "Lachie Neale")
        parts = name.split()
        if parts and parts[0] in TEAM_NICKNAME_PREFIXES:
            parts = parts[1:]
            name = " ".join(parts)
        # Must be at least two words after stripping
        if len(parts) < 2:
            continue
        # Filter out known non-player phrases
        if name in NON_PLAYER_WORDS:
            continue
        # Skip if it's a known organisation/city
        if any(w in name for w in ("AFL", "Fox", "Kayo", "AEST", "Aest")):
            continue
        candidates.append(name)
    return candidates


def extract_injuries_from_section(team: str, section_text: str, round_number: int) -> list[dict]:
    """
    Extract injury records from a team section's text.
    Returns list of injury dicts compatible with the team news format.
    """
    records = []
    scraped_at = datetime.now(timezone.utc).isoformat()

    # Split into sentences
    sentences = re.split(r'(?<=[.!?])\s+', section_text)

    for sentence in sentences:
        if len(sentence) < 20:
            continue
        if not INJURY_RE.search(sentence):
            continue
        if SKIP_RE.search(sentence):
            continue
        if REST_RE.search(sentence):
            continue
        # Skip sentences about the OPPONENT being without a player —
        # "against a Dockers outfit that was missing X" → X belongs to Fremantle, not current team
        if re.search(r'\b(against|opponent)\b.{0,100}\bmissing\b', sentence, re.I):
            continue

        players = extract_players_from_sentence(sentence)
        injury_type = extract_injury_type(sentence)

        # Truncate sentence for notes
        note_sentence = sentence[:200].strip()

        # Determine if in-game vs pre-game mention
        in_game = bool(re.search(
            r'\b(went down|left the field|didn\'t return|failed to finish|subbed off|medical sub|substitut\w*|in the (first|second|third|fourth) quarter|at half.?time|Q[1-4])\b',
            sentence, re.I
        ))
        status = "out" if in_game else "doubtful"

        if players:
            for player in players:
                records.append({
                    "season":     2026,
                    "round":      round_number,
                    "team":       team,
                    "player":     player,
                    "status":     status,
                    "notes":      f"{injury_type} | Source: {note_sentence}",
                    "scraped_at": scraped_at,
                    "source":     "fox_sports_report",
                })
        else:
            # No player name found but sentence has injury content — log it
            records.append({
                "season":     2026,
                "round":      round_number,
                "team":       team,
                "player":     "UNKNOWN — review required",
                "status":     "out",
                "notes":      f"{injury_type} | Source: {note_sentence}",
                "scraped_at": scraped_at,
                "source":     "fox_sports_report",
            })

    return records


def parse_article(html: str, round_number: int) -> list[dict]:
    """Parse a Fox Sports article and extract all injury records."""
    soup = BeautifulSoup(html, "html.parser")
    article = (
        soup.find("article") or
        soup.find("div", class_=re.compile(r"article|story|content", re.I))
    )
    text = article.get_text(separator="\n", strip=True) if article else soup.get_text()

    sections = split_into_team_sections(text)
    log.info("Found %d team sections in article", len(sections))

    all_records: list[dict] = []
    for team, section_text in sections.items():
        records = extract_injuries_from_section(team, section_text, round_number)
        if records:
            log.info("  %s: %d injury mentions", team, len(records))
        all_records.extend(records)

    return all_records


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def write_outputs(records: list[dict], round_number: int) -> None:
    scraped_at = datetime.now(timezone.utc).isoformat()
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    # Load existing baseline to diff against
    latest_path = PROCESSED_DIR / "latest-injuries.json"
    known: list[dict] = []
    if latest_path.exists():
        try:
            known = json.loads(latest_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    known_keys = {(r["team"], r["player"]) for r in known}

    # Filter to genuinely new players (not UNKNOWN records for baseline)
    new_injuries = [
        r for r in records
        if (r["team"], r["player"]) not in known_keys
        and r["player"] != "UNKNOWN — review required"
    ]

    # Write new-this-week.json (same format as NRL diff output)
    diff_path = PROCESSED_DIR / "new-this-week.json"
    diff_path.write_text(
        json.dumps({
            "scraped_at": scraped_at,
            "source":     "fox_sports_match_reports",
            "new":        new_injuries,
            "worsened":   [],
            "cleared":    [],
        }, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    log.info("Wrote new-this-week.json -- %d new injuries", len(new_injuries))

    # Write round-specific archive
    round_dir = PROCESSED_DIR / "2026"
    round_dir.mkdir(parents=True, exist_ok=True)
    (round_dir / f"round-{round_number}-match-report-injuries.json").write_text(
        json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    setup_logging()

    p = argparse.ArgumentParser(description="Scrape AFL injury mentions from Fox Sports match reports")
    p.add_argument("--round", dest="round_number", type=int, default=0)
    p.add_argument("--round-one-thursday", default=DEFAULT_ROUND_ONE_THURSDAY)
    p.add_argument("--url", help="Override article URL (for testing)")
    args = p.parse_args()

    round_number = args.round_number or latest_completed_afl_round()
    log.info("AFL match report scraper  round=%d", round_number)

    all_records: list[dict] = []

    if args.url:
        # Manual URL override for testing
        html = fetch(args.url)
        if html:
            records = parse_article(html, round_number)
            all_records.extend(records)
    else:
        # 1. Try Report Card first (most comprehensive — covers all teams)
        rc_url = find_report_card_url(round_number)
        if rc_url:
            log.info("Report Card: %s", rc_url)
            html = fetch(rc_url)
            if html:
                records = parse_article(html, round_number)
                all_records.extend(records)
                log.info("Report Card: %d injury mentions", len(records))
        else:
            log.warning("No Report Card found for round %d — falling back to individual game pages", round_number)

        # 2. Supplement with individual game pages
        game_urls = find_game_report_urls(round_number)
        log.info("Found %d individual game pages", len(game_urls))
        seen_players: set[tuple] = {(r["team"], r["player"]) for r in all_records}
        for url in game_urls:
            html = fetch(url)
            if not html:
                continue
            records = parse_article(html, round_number)
            # Only add players not already found in Report Card
            new_from_game = [r for r in records if (r["team"], r["player"]) not in seen_players]
            all_records.extend(new_from_game)
            seen_players.update((r["team"], r["player"]) for r in new_from_game)

    log.info("Total injury mentions extracted: %d", len(all_records))

    # Deduplicate by (team, player) — keep first occurrence
    seen: set[tuple] = set()
    deduped: list[dict] = []
    for r in all_records:
        key = (r["team"], r["player"])
        if key not in seen:
            seen.add(key)
            deduped.append(r)

    # Print summary
    print(f"\n{'='*52}")
    print(f"  AFL MATCH REPORT INJURIES -- Round {round_number}")
    print(f"{'='*52}")
    if not deduped:
        print("  No injury mentions found.")
    else:
        by_team: dict[str, list[dict]] = {}
        for r in deduped:
            by_team.setdefault(r["team"], []).append(r)
        for team in sorted(by_team):
            print(f"\n  {team}")
            for r in by_team[team]:
                inj = r["notes"].split(" | Source:")[0]
                print(f"    {r['player']}  [{inj}]")

    write_outputs(deduped, round_number)
    log.info("Done.")
    sys.exit(0)


if __name__ == "__main__":
    main()
