"""
lib/scraper/nrl_bvi.py

Scrapes the NRL Betting Value Index from aussportstipping.com and saves it
as JSON so BetMate can badge and filter games by team value.

Tiers (17 teams split into thirds):
  value   — top 6   (green)
  neutral — mid 5   (grey)
  fade    — bottom 6 (red)

Output:
  data/nrl/bvi/processed/latest-bvi.json

Usage:
  uv run --with requests --with beautifulsoup4 python lib/scraper/nrl_bvi.py
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
OUT_DIR = ROOT / "data" / "nrl" / "bvi" / "processed"
OUT     = OUT_DIR / "latest-bvi.json"
URL     = "https://www.aussportstipping.com/sports/nrl/betting_value_index/"
LOOKBACK_YEARS = 1

# Canonical names must match keys in lib/teams.ts NRL_TEAMS exactly
TEAM_MAP: dict[str, str] = {
    "Broncos":                      "Brisbane Broncos",
    "Brisbane Broncos":             "Brisbane Broncos",
    "Brisbane":                     "Brisbane Broncos",
    "Raiders":                      "Canberra Raiders",
    "Canberra Raiders":             "Canberra Raiders",
    "Canberra":                     "Canberra Raiders",
    "Bulldogs":                     "Canterbury Bulldogs",
    "Canterbury Bulldogs":          "Canterbury Bulldogs",
    "Canterbury-Bankstown Bulldogs":"Canterbury Bulldogs",
    "Canterbury":                   "Canterbury Bulldogs",
    "Sharks":                       "Cronulla Sutherland Sharks",
    "Cronulla Sutherland Sharks":   "Cronulla Sutherland Sharks",
    "Cronulla-Sutherland Sharks":   "Cronulla Sutherland Sharks",
    "Cronulla":                     "Cronulla Sutherland Sharks",
    "Dolphins":                     "Dolphins",
    "Titans":                       "Gold Coast Titans",
    "Gold Coast Titans":            "Gold Coast Titans",
    "Gold Coast":                   "Gold Coast Titans",
    "Sea Eagles":                   "Manly Warringah Sea Eagles",
    "Manly Warringah Sea Eagles":   "Manly Warringah Sea Eagles",
    "Manly-Warringah Sea Eagles":   "Manly Warringah Sea Eagles",
    "Manly":                        "Manly Warringah Sea Eagles",
    "Storm":                        "Melbourne Storm",
    "Melbourne Storm":              "Melbourne Storm",
    "Melbourne":                    "Melbourne Storm",
    "Warriors":                     "New Zealand Warriors",
    "New Zealand Warriors":         "New Zealand Warriors",
    "NZ Warriors":                  "New Zealand Warriors",
    "Knights":                      "Newcastle Knights",
    "Newcastle Knights":            "Newcastle Knights",
    "Newcastle":                    "Newcastle Knights",
    "Cowboys":                      "North Queensland Cowboys",
    "North Queensland Cowboys":     "North Queensland Cowboys",
    "North Queensland":             "North Queensland Cowboys",
    "Eels":                         "Parramatta Eels",
    "Parramatta Eels":              "Parramatta Eels",
    "Parramatta":                   "Parramatta Eels",
    "Panthers":                     "Penrith Panthers",
    "Penrith Panthers":             "Penrith Panthers",
    "Penrith":                      "Penrith Panthers",
    "Rabbitohs":                    "South Sydney Rabbitohs",
    "South Sydney Rabbitohs":       "South Sydney Rabbitohs",
    "South Sydney":                 "South Sydney Rabbitohs",
    "Dragons":                      "St George Illawarra Dragons",
    "St George Illawarra Dragons":  "St George Illawarra Dragons",
    "St. George Illawarra Dragons": "St George Illawarra Dragons",
    "St George Illawarra":          "St George Illawarra Dragons",
    "Roosters":                     "Sydney Roosters",
    "Sydney Roosters":              "Sydney Roosters",
    "Sydney":                       "Sydney Roosters",
    "Tigers":                       "Wests Tigers",
    "Wests Tigers":                 "Wests Tigers",
    "Wests":                        "Wests Tigers",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)


def _parse_dollar(s: str) -> float | None:
    if s.startswith("$"):
        try:
            return float(s[1:].replace(",", ""))
        except ValueError:
            pass
    return None


def scrape() -> list[dict]:
    now   = datetime.now(timezone.utc)
    start = now.replace(year=now.year - LOOKBACK_YEARS)
    log.info("Fetching NRL BVI from %s (1-year window: %s → %s)", URL, start.date(), now.date())
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
    resp = session.post(
        URL,
        timeout=20,
        headers={"Referer": "https://www.aussportstipping.com/"},
        data={
            "start_day":   f"{start.day:02d}",
            "start_month": f"{start.month:02d}",
            "start_year":  f"{start.year}",
            "end_day":     f"{now.day:02d}",
            "end_month":   f"{now.month:02d}",
            "end_year":    f"{now.year}",
        },
    )
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    text = soup.get_text(separator="\n")
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    rows = []
    for i, line in enumerate(lines):
        canonical = TEAM_MAP.get(line)
        if not canonical:
            continue

        fav_profit: float | None = None
        und_profit: float | None = None
        pct:        float | None = None
        mode: str | None = None

        for j in range(i + 1, min(i + 14, len(lines))):
            ln = lines[j]
            if TEAM_MAP.get(ln):
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

    seen: set[str] = set()
    unique = []
    for r in rows:
        if r["name"] not in seen:
            seen.add(r["name"])
            unique.append(r)

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

    now = datetime.now(timezone.utc)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "updated": now.isoformat(),
        "source":  URL,
        "date_range": {
            "start": now.replace(year=now.year - LOOKBACK_YEARS).date().isoformat(),
            "end":   now.date().isoformat(),
        },
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
    push("nrl_bvi", payload)


if __name__ == "__main__":
    main()
