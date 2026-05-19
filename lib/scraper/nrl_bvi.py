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

ROOT    = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "data" / "nrl" / "bvi" / "processed"
OUT     = OUT_DIR / "latest-bvi.json"
URL     = "https://www.aussportstipping.com/sports/nrl/betting_value_index/"

TEAM_MAP: dict[str, str] = {
    "Broncos":                       "Brisbane Broncos",
    "Brisbane Broncos":              "Brisbane Broncos",
    "Brisbane":                      "Brisbane Broncos",
    "Raiders":                       "Canberra Raiders",
    "Canberra Raiders":              "Canberra Raiders",
    "Canberra":                      "Canberra Raiders",
    "Bulldogs":                      "Canterbury-Bankstown Bulldogs",
    "Canterbury-Bankstown Bulldogs": "Canterbury-Bankstown Bulldogs",
    "Canterbury":                    "Canterbury-Bankstown Bulldogs",
    "Sharks":                        "Cronulla-Sutherland Sharks",
    "Cronulla-Sutherland Sharks":    "Cronulla-Sutherland Sharks",
    "Cronulla":                      "Cronulla-Sutherland Sharks",
    "Dolphins":                      "Dolphins",
    "Titans":                        "Gold Coast Titans",
    "Gold Coast Titans":             "Gold Coast Titans",
    "Gold Coast":                    "Gold Coast Titans",
    "Sea Eagles":                    "Manly-Warringah Sea Eagles",
    "Manly-Warringah Sea Eagles":    "Manly-Warringah Sea Eagles",
    "Manly":                         "Manly-Warringah Sea Eagles",
    "Storm":                         "Melbourne Storm",
    "Melbourne Storm":               "Melbourne Storm",
    "Melbourne":                     "Melbourne Storm",
    "Warriors":                      "New Zealand Warriors",
    "New Zealand Warriors":          "New Zealand Warriors",
    "NZ Warriors":                   "New Zealand Warriors",
    "Knights":                       "Newcastle Knights",
    "Newcastle Knights":             "Newcastle Knights",
    "Newcastle":                     "Newcastle Knights",
    "Cowboys":                       "North Queensland Cowboys",
    "North Queensland Cowboys":      "North Queensland Cowboys",
    "North Queensland":              "North Queensland Cowboys",
    "Eels":                          "Parramatta Eels",
    "Parramatta Eels":               "Parramatta Eels",
    "Parramatta":                    "Parramatta Eels",
    "Panthers":                      "Penrith Panthers",
    "Penrith Panthers":              "Penrith Panthers",
    "Penrith":                       "Penrith Panthers",
    "Rabbitohs":                     "South Sydney Rabbitohs",
    "South Sydney Rabbitohs":        "South Sydney Rabbitohs",
    "South Sydney":                  "South Sydney Rabbitohs",
    "Dragons":                       "St. George Illawarra Dragons",
    "St. George Illawarra Dragons":  "St. George Illawarra Dragons",
    "St George Illawarra":           "St. George Illawarra Dragons",
    "Dragons":                       "St. George Illawarra Dragons",
    "Roosters":                      "Sydney Roosters",
    "Sydney Roosters":               "Sydney Roosters",
    "Sydney":                        "Sydney Roosters",
    "Tigers":                        "Wests Tigers",
    "Wests Tigers":                  "Wests Tigers",
    "Wests":                         "Wests Tigers",
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
    log.info("Fetching NRL BVI from %s", URL)
    resp = requests.get(URL, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
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


if __name__ == "__main__":
    main()
