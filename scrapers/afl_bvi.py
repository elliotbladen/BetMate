"""
lib/scraper/afl_bvi.py

Scrapes the AFL Betting Value Index from aussportstipping.com and saves it
as JSON so BetMate can badge and filter games by team value.

Tiers (18 teams split into thirds):
  value   — top 6   (green)
  neutral — mid 6   (grey, hidden when filter is on)
  fade    — bottom 6 (red)

Output:
  data/afl/bvi/processed/latest-bvi.json

Usage:
  uv run --with requests --with beautifulsoup4 python lib/scraper/afl_bvi.py
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT    = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "afl" / "bvi" / "processed"
OUT     = OUT_DIR / "latest-bvi.json"
URL     = "https://www.aussportstipping.com/sports/afl/betting_value_index/"

# Map every name variant the site might use → canonical Odds API name
TEAM_MAP: dict[str, str] = {
    "Adelaide":                       "Adelaide Crows",
    "Adelaide Crows":                 "Adelaide Crows",
    "Brisbane":                       "Brisbane Lions",
    "Brisbane Lions":                 "Brisbane Lions",
    "Carlton":                        "Carlton Blues",
    "Carlton Blues":                  "Carlton Blues",
    "Collingwood":                    "Collingwood Magpies",
    "Collingwood Magpies":            "Collingwood Magpies",
    "Essendon":                       "Essendon Bombers",
    "Essendon Bombers":               "Essendon Bombers",
    "Fremantle":                      "Fremantle Dockers",
    "Fremantle Dockers":              "Fremantle Dockers",
    "Geelong":                        "Geelong Cats",
    "Geelong Cats":                   "Geelong Cats",
    "Gold Coast":                     "Gold Coast Suns",
    "Gold Coast Suns":                "Gold Coast Suns",
    "GWS":                            "Greater Western Sydney Giants",
    "GWS Giants":                     "Greater Western Sydney Giants",
    "Greater Western Sydney":         "Greater Western Sydney Giants",
    "Greater Western Sydney Giants":  "Greater Western Sydney Giants",
    "Hawthorn":                       "Hawthorn Hawks",
    "Hawthorn Hawks":                 "Hawthorn Hawks",
    "Melbourne":                      "Melbourne Demons",
    "Melbourne Demons":               "Melbourne Demons",
    "North Melbourne":                "North Melbourne Kangaroos",
    "North Melbourne Kangaroos":      "North Melbourne Kangaroos",
    "Port Adelaide":                  "Port Adelaide Power",
    "Port Adelaide Power":            "Port Adelaide Power",
    "Richmond":                       "Richmond Tigers",
    "Richmond Tigers":                "Richmond Tigers",
    "St Kilda":                       "St Kilda Saints",
    "St Kilda Saints":                "St Kilda Saints",
    "Sydney":                         "Sydney Swans",
    "Sydney Swans":                   "Sydney Swans",
    "West Coast":                     "West Coast Eagles",
    "West Coast Eagles":              "West Coast Eagles",
    "Western Bulldogs":               "Western Bulldogs",
    "Bulldogs":                       "Western Bulldogs",
    "Doggies":                        "Western Bulldogs",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)


def _parse_dollar(s: str) -> float | None:
    """Parse a $-prefixed value like '$2.60' or '$-2.13'."""
    if s.startswith("$"):
        try:
            return float(s[1:].replace(",", ""))
        except ValueError:
            pass
    return None


def scrape() -> list[dict]:
    """Fetch BVI page and return [{name, fav_profit, und_profit, score, rank}] sorted rank asc.

    Actual page text structure per team:
        TeamName
        Fav:
        $<fav_profit>
        <games>
        <profit_pct>%
        Und:
        $<und_profit>
        All:
        $<all_profit>

    We capture Fav ($) and Und ($) for per-game role-aware badging, and
    Profit (%) as the overall ranking score.
    """
    log.info("Fetching BVI from %s", URL)
    hdrs = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-AU,en;q=0.9",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }
    session = requests.Session()
    session.verify = False
    session.headers.update(hdrs)
    session.get("https://www.aussportstipping.com/", timeout=20)
    resp = session.get(URL, headers={"Referer": "https://www.aussportstipping.com/"}, timeout=20)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    rows = []

    text = soup.get_text(separator="\n")
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    for i, line in enumerate(lines):
        canonical = TEAM_MAP.get(line)
        if canonical:
            fav_profit: float | None = None
            und_profit: float | None = None
            pct:        float | None = None
            mode: str | None = None  # 'fav' or 'und'

            for j in range(i + 1, min(i + 14, len(lines))):
                ln = lines[j]

                if TEAM_MAP.get(ln):      # hit the next team — stop
                    break
                if ln == "Fav:":
                    mode = "fav"
                elif ln == "Und:":
                    mode = "und"
                elif ln.startswith("$"):
                    val = _parse_dollar(ln)
                    if val is not None:
                        if mode == "fav" and fav_profit is None:
                            fav_profit = val
                        elif mode == "und" and und_profit is None:
                            und_profit = val
                elif ln.endswith("%") and pct is None:
                    try:
                        pct = float(ln.replace("%", "").replace(",", ""))
                    except ValueError:
                        pass

                if fav_profit is not None and und_profit is not None and pct is not None:
                    break

            if fav_profit is not None and und_profit is not None and pct is not None:
                rows.append({
                    "name":       canonical,
                    "fav_profit": fav_profit,
                    "und_profit": und_profit,
                    "raw_score":  pct,
                })

    # Deduplicate (keep first occurrence)
    seen: set[str] = set()
    unique = []
    for r in rows:
        if r["name"] not in seen:
            seen.add(r["name"])
            unique.append(r)

    # Sort by Profit % descending — highest = most value
    unique.sort(key=lambda x: x["raw_score"], reverse=True)
    for rank, r in enumerate(unique, 1):
        r["rank"] = rank

    return unique


def assign_tiers(rows: list[dict]) -> list[dict]:
    n = len(rows)
    third = max(1, n // 3)
    for r in rows:
        rank = r["rank"]
        if rank <= third:
            r["tier"] = "value"
        elif rank <= third * 2:
            r["tier"] = "neutral"
        else:
            r["tier"] = "fade"
    return rows


def main() -> None:
    rows = scrape()

    if len(rows) < 6:
        log.error("Only %d teams found — page structure may have changed. Aborting.", len(rows))
        sys.exit(1)

    rows = assign_tiers(rows)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "updated": datetime.now(timezone.utc).isoformat(),
        "source": URL,
        "teams": {
            r["name"]: {
                "rank":       r["rank"],
                "score":      round(r["raw_score"], 2),
                "tier":       r["tier"],
                "fav_profit": round(r["fav_profit"], 2),
                "und_profit": round(r["und_profit"], 2),
            }
            for r in rows
        },
    }
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    log.info("Wrote %d teams to %s", len(rows), OUT)
    for r in rows:
        log.info("  %2d. %-35s fav=%+.2f  und=%+.2f  [%s]",
                 r["rank"], r["name"], r["fav_profit"], r["und_profit"], r["tier"])

    from supabase_push import push  # noqa: PLC0415
    push("afl_bvi", payload)


if __name__ == "__main__":
    main()
