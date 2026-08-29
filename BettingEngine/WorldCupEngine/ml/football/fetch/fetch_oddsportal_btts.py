#!/usr/bin/env python3
"""
Scrape historical BTTS closing odds from OddsPortal for EPL / Championship.

OddsPortal does NOT track Pinnacle for BTTS. Best available sharp references are:
  - bet365    (large, reasonably efficient, widely used as CLV reference)
  - BetInAsia (Asian handicap book, highest payout — sharpest available here)

Output: data/{league}/btts/oddsportal_btts.csv
Columns: season, date, home_team, away_team, op_match_url,
         btts_yes_b365, btts_no_b365, btts_yes_asian, btts_no_asian

Join with existing match CSV on (date, home_team, away_team) to get btts_result
from FTHG/FTAG. That join is done in backtest/btts_backtest.py, not here.

Usage:
    cd BettingEngine/
    python3 WorldCupEngine/ml/football/fetch/fetch_oddsportal_btts.py
    python3 WorldCupEngine/ml/football/fetch/fetch_oddsportal_btts.py --league championship
    python3 WorldCupEngine/ml/football/fetch/fetch_oddsportal_btts.py --seasons 2023/24 2022/23

Resume: already-scraped op_match_url rows are skipped automatically.

Setup (one-time):
    pip install playwright
    playwright install chromium
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright, Page

_WCE_ROOT = Path(__file__).resolve().parents[3]   # → WorldCupEngine/
sys.path.insert(0, str(_WCE_ROOT))

from ml.football.league_config import load_league

# ── OddsPortal slug map ───────────────────────────────────────────────────────

LEAGUE_SLUGS = {
    "epl":          "football/england/premier-league",
    "championship": "football/england/championship",
}

# Bookmakers to extract (in priority order for each column)
B365_NAMES  = {"bet365"}
ASIAN_NAMES = {"BetInAsia", "Pinnacle"}   # Pinnacle included in case it appears

BASE_URL    = "https://www.oddsportal.com"
WAIT_SEC    = 8      # seconds to wait after navigation for async odds to render
RETRY_MAX   = 2


# ── Season → OddsPortal archive URL ──────────────────────────────────────────

def season_to_op_url(season: str, league_slug: str) -> str:
    """
    '2023/24' → 'https://www.oddsportal.com/football/england/premier-league-2023-2024/results/'
    Current season uses the base slug (no year suffix).
    """
    parts = season.split("/")
    year1 = int(parts[0])
    year2 = year1 + 1
    return f"{BASE_URL}/{league_slug}-{year1}-{year2}/results/"


# ── Results page scraping ─────────────────────────────────────────────────────

def _parse_date_str(raw: str) -> str:
    """'26 May 2025' → '2025-05-26'"""
    m = re.match(
        r"(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{4})",
        raw.strip(), re.I
    )
    if not m:
        return ""
    day, mon, yr = m.groups()
    months = {"jan":1,"feb":2,"mar":3,"apr":4,"may":5,"jun":6,
              "jul":7,"aug":8,"sep":9,"oct":10,"nov":11,"dec":12}
    return f"{yr}-{months[mon.lower()]:02d}-{int(day):02d}"


def _scrape_one_results_page(page: Page) -> list[tuple[str, str, str, str]]:
    """
    Extract matches from the currently loaded OddsPortal results page.
    Returns list of (op_match_url, home_team, away_team, date_str).

    Strategy:
    1. Extract all dates from page text in order (they appear as "DD Mon YYYY" lines).
    2. Extract all eventRow matches.
    3. Assign dates by tracking which date header precedes each batch of matches.
       OddsPortal groups matches by date, most recent first.
    """
    # Step 1: Get all match rows
    rows = page.query_selector_all(".eventRow")

    # Step 2: Get the full page text to extract dates in order
    full_text = page.inner_text("body")

    # Build ordered list of (text_position, date_str) from the page text
    date_positions: list[tuple[int, str]] = []
    for m in re.finditer(
        r"\b(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{4})\b",
        full_text, re.I
    ):
        ds = _parse_date_str(m.group(0))
        if ds:
            date_positions.append((m.start(), ds))
    # Deduplicate consecutive same dates
    seen = set()
    unique_dates = []
    for pos, ds in date_positions:
        if ds not in seen:
            seen.add(ds)
            unique_dates.append(ds)

    # Step 3: Match each eventRow to a date by position in the page
    # Each match row's inner text contains home/away team names —
    # find that text in the page to estimate its position relative to date headers.
    matches: list[tuple[str, str, str, str]] = []
    date_idx = 0  # which date group we're currently in

    for row in rows:
        name_els = row.query_selector_all(".participant-name")
        if len(name_els) < 2:
            continue

        link_el = row.query_selector("a")
        if not link_el:
            continue
        href = link_el.get_attribute("href") or ""
        if "#" not in href:
            continue

        home = name_els[0].inner_text().strip()
        away = name_els[1].inner_text().strip()
        full_url = BASE_URL + href if href.startswith("/") else href

        # Estimate position of this match in page text to find its date
        match_text = f"{home}"
        pos = full_text.find(match_text)
        if pos >= 0 and date_positions:
            # Find the last date header that appears before this match
            applicable = [d for p, d in date_positions if p < pos]
            current_date = applicable[-1] if applicable else (unique_dates[0] if unique_dates else "")
        else:
            current_date = unique_dates[date_idx] if unique_dates else ""

        matches.append((full_url, home, away, current_date))

    return matches


def get_match_urls_from_results(page: Page, season_url: str) -> list[tuple[str, str, str, str]]:
    """
    Scrape all match rows from a season results page — handles numbered pagination.
    OddsPortal is a Vue SPA: pagination changes via hash (#/page/2/).
    We set the hash directly via JS on the already-loaded page to trigger SPA routing.
    Returns list of (op_match_url, home_team, away_team, date_str).
    """
    # Load page 1
    page.goto(season_url, timeout=30_000)
    page.wait_for_load_state("networkidle", timeout=15_000)
    time.sleep(WAIT_SEC)

    all_matches: list[tuple[str, str, str, str]] = []
    seen_urls: set[str] = set()

    def collect_page():
        for row in _scrape_one_results_page(page):
            if row[0] not in seen_urls:
                seen_urls.add(row[0])
                all_matches.append(row)

    collect_page()
    print(f"    Page 1: {len(all_matches)} matches so far")

    # Navigate to subsequent pages by setting the hash (SPA routing)
    page_num = 2
    while True:
        # Set hash via JS — triggers Vue router without a full page reload.
        # window.location.hash stores value WITHOUT leading '#', so we omit it.
        page.evaluate(f"window.location.hash = '/page/{page_num}/'")
        page.wait_for_load_state("networkidle", timeout=15_000)
        time.sleep(WAIT_SEC)

        before = len(all_matches)
        collect_page()

        if len(all_matches) == before:
            break   # no new matches — past last page
        print(f"    Page {page_num}: {len(all_matches)} matches so far")
        page_num += 1

    return all_matches


# ── Match BTTS scraping ───────────────────────────────────────────────────────

def _extract_btts_row(row_text: str) -> tuple[str, str] | None:
    """Extract (yes_odds, no_odds) from a bookmaker row text."""
    odds = re.findall(r"\b[12]\.\d{2}\b", row_text)
    if len(odds) >= 2:
        return odds[0], odds[1]
    return None


def scrape_btts_odds(page: Page, match_url: str) -> dict | None:
    """
    Navigate to a match H2H URL, switch to BTTS tab, extract closing odds.
    Returns dict with btts_yes_b365, btts_no_b365, btts_yes_asian, btts_no_asian
    or None on failure.
    """
    for attempt in range(RETRY_MAX):
        try:
            page.goto(match_url, timeout=30_000)
            time.sleep(WAIT_SEC)

            # Open 'More' market tab to reveal BTTS option
            more_btns = page.locator("button").filter(has_text="More").all()
            for btn in more_btns:
                if btn.is_visible():
                    btn.click()
                    time.sleep(1)
                    break

            # Click 'Both Teams to Score'
            page.evaluate("""
                const els = document.querySelectorAll('a, div, span, li');
                for (const el of els) {
                    if (el.textContent.trim() === 'Both Teams to Score') {
                        el.click();
                        break;
                    }
                }
            """)
            time.sleep(WAIT_SEC)

            # Extract bookmaker rows
            rows = page.query_selector_all("[class*='border-b']")
            b365_yes = b365_no = asian_yes = asian_no = None

            for row in rows:
                text = row.inner_text().strip().replace("\n", " ")
                # Identify bookmaker name
                name_part = re.split(r"\b[12]\.\d{2}\b", text)[0]
                name = re.sub(r"CLAIM BONUS|\|", "", name_part).strip()

                odds = _extract_btts_row(text)
                if odds is None:
                    continue

                if any(n.lower() in name.lower() for n in B365_NAMES):
                    b365_yes, b365_no = odds

                if any(n.lower() in name.lower() for n in {n.lower() for n in ASIAN_NAMES}):
                    asian_yes, asian_no = odds

            if b365_yes is not None or asian_yes is not None:
                return {
                    "btts_yes_b365":  b365_yes,
                    "btts_no_b365":   b365_no,
                    "btts_yes_asian": asian_yes,
                    "btts_no_asian":  asian_no,
                }

            print(f"    No target bookmaker odds found (attempt {attempt+1})")
        except Exception as e:
            print(f"    Error scraping {match_url}: {e} (attempt {attempt+1})")
        time.sleep(3)

    return None



# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape OddsPortal BTTS closing odds")
    parser.add_argument("--league",   default="epl",    help="League config key")
    parser.add_argument("--seasons",  nargs="*",        help="Seasons to scrape e.g. '2023/24 2022/23'")
    args = parser.parse_args()

    cfg    = load_league(args.league)
    slug   = LEAGUE_SLUGS.get(args.league)
    if slug is None:
        print(f"No OddsPortal slug for league '{args.league}'. Add it to LEAGUE_SLUGS.")
        return

    out_dir = cfg.data_dir / "btts"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_csv = out_dir / "oddsportal_btts.csv"

    # Load already-scraped URLs for resume
    scraped_urls: set[str] = set()
    if out_csv.exists():
        with open(out_csv, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                scraped_urls.add(row.get("op_match_url", ""))
        print(f"Resuming — {len(scraped_urls)} URLs already scraped")

    fieldnames = [
        "season", "date", "home_team", "away_team", "op_match_url",
        "btts_yes_b365", "btts_no_b365", "btts_yes_asian", "btts_no_asian",
    ]

    seasons = args.seasons or cfg.test_seasons  # default to backtest seasons
    # For full training set, override: pass all feature_seasons
    if args.seasons is None:
        seasons = sorted(set(cfg.test_seasons + cfg.feature_seasons))
        print(f"No --seasons specified. Scraping all: {seasons}")

    write_header = not out_csv.exists()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )
        page = ctx.new_page()

        with open(out_csv, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if write_header:
                writer.writeheader()

            for season in seasons:
                season_url = season_to_op_url(season, slug)
                print(f"\n{'='*60}")
                print(f"Season {season}: {season_url}")

                matches = get_match_urls_from_results(page, season_url)
                print(f"  Found {len(matches)} matches")

                new_count = skip_count = err_count = 0

                for i, (match_url, home, away, raw_date) in enumerate(matches):
                    # Dedup key: URL without market suffix in hash
                    if "#" in match_url:
                        url_no_hash, hash_raw = match_url.split("#", 1)
                        base_url = f"{url_no_hash}#{hash_raw.split(':')[0]}"
                    else:
                        base_url = match_url

                    if base_url in scraped_urls or match_url in scraped_urls:
                        skip_count += 1
                        continue

                    print(f"  [{i+1}/{len(matches)}] {home} vs {away} ... ", end="", flush=True)

                    # Build BTTS URL: strip any existing market suffix from hash
                    if "#" in match_url:
                        url_no_hash, hash_raw = match_url.split("#", 1)
                        clean_hash = hash_raw.split(":")[0]   # remove :1X2;2 if present
                        btts_url   = f"{url_no_hash}#{clean_hash}:bts;2"
                    else:
                        btts_url = match_url

                    odds = scrape_btts_odds(page, btts_url)
                    if odds is None:
                        err_count += 1
                        print("NO ODDS")
                        scraped_urls.add(base_url)
                        # Write a blank row so we don't re-try endlessly
                        writer.writerow({
                            "season": season, "date": raw_date, "home_team": home,
                            "away_team": away, "op_match_url": base_url,
                            "btts_yes_b365": "", "btts_no_b365": "",
                            "btts_yes_asian": "", "btts_no_asian": "",
                        })
                        f.flush()
                        continue

                    row = {
                        "season":        season,
                        "date":          raw_date,
                        "home_team":     home,
                        "away_team":     away,
                        "op_match_url":  base_url,
                        "btts_yes_b365":  odds["btts_yes_b365"] or "",
                        "btts_no_b365":   odds["btts_no_b365"]  or "",
                        "btts_yes_asian": odds["btts_yes_asian"] or "",
                        "btts_no_asian":  odds["btts_no_asian"]  or "",
                    }
                    writer.writerow(row)
                    f.flush()
                    scraped_urls.add(base_url)
                    new_count += 1

                    b365_str  = f"b365={odds['btts_yes_b365']}/{odds['btts_no_b365']}" if odds["btts_yes_b365"] else "no-b365"
                    asian_str = f"asian={odds['btts_yes_asian']}/{odds['btts_no_asian']}" if odds["btts_yes_asian"] else "no-asian"
                    print(f"{b365_str}  {asian_str}")

                print(f"  Season done — {new_count} new, {skip_count} skipped, {err_count} errors")

        browser.close()

    print(f"\nSaved to {out_csv}")


if __name__ == "__main__":
    main()
