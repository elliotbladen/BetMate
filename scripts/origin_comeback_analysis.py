"""
scripts/origin_comeback_analysis.py

Fetches NRL match data (halftime + final scores) for Origin period games
(June–July) over 2023–2026 and calculates comeback win rates.

Usage:
    uv run --with requests --with beautifulsoup4 python scripts/origin_comeback_analysis.py
"""
from __future__ import annotations

import html
import json
import re
import time
from dataclasses import dataclass, field
from datetime import datetime

import requests

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/html, */*",
    "Accept-Language": "en-AU,en;q=0.9",
    "Referer": "https://www.nrl.com/draw/",
    "Origin": "https://www.nrl.com",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
})
# Seed the session with NRL.com cookies
HEADERS = SESSION.headers  # alias for compat
NRL_DRAW_API = "https://www.nrl.com/draw/data/?competition=111&season={s}&round={r}"
NRL_BASE = "https://www.nrl.com"
SEASONS = [2023, 2024, 2025, 2026]
# Origin is typically R12–R21. Scan only these rounds to avoid 108 requests.
ROUND_RANGE = range(11, 23)


@dataclass
class GameResult:
    season: int
    round: int
    date: str
    home: str
    away: str
    ht_home: int
    ht_away: int
    ft_home: int
    ft_away: int


def fetch_fixtures(season: int, round_num: int) -> list[dict]:
    url = NRL_DRAW_API.format(s=season, r=round_num)
    for attempt in range(3):
        try:
            if attempt > 0:
                time.sleep(5)
            r = SESSION.get(url, timeout=20)
            if r.status_code != 200:
                print(f"  HTTP {r.status_code} R{round_num}")
                return []
            if not r.text.strip():
                print(f"  Empty response R{round_num} (attempt {attempt+1})")
                time.sleep(3)
                continue
            # Print first 50 chars on first attempt to diagnose non-JSON
            if r.text[:1] not in ('{', '['):
                print(f"  Non-JSON response R{round_num}: {r.text[:100]}")
                time.sleep(3)
                continue
            return [f for f in r.json().get("fixtures", []) if f.get("type") == "Match"]
        except Exception as exc:
            print(f"  API error R{round_num} (attempt {attempt+1}): {exc}")
            time.sleep(3)
    return []


def is_origin_period(date_str: str) -> bool:
    """Return True if game is in June or July (State of Origin window)."""
    try:
        d = datetime.fromisoformat(date_str)
        return d.month in (6, 7)
    except Exception:
        return False


def get_game_date(fixture: dict) -> str:
    clock = fixture.get("clock", {})
    kick = clock.get("kickOffTimeLong", "")
    try:
        return datetime.fromisoformat(kick.replace("Z", "+00:00")).strftime("%Y-%m-%d")
    except Exception:
        return ""


def fetch_halftime_scores(mc_url: str) -> tuple[int, int]:
    """
    Fetch match centre page and extract halfTimeScore for home + away team.
    Returns (home_ht, away_ht) or (-1, -1) on failure.
    """
    try:
        r = SESSION.get(mc_url, timeout=20)
        r.raise_for_status()
        text = r.text

        # The page has HTML-entity-encoded JSON: &quot;halfTimeScore&quot;:NN
        # Decode entities and find all halfTimeScore values in order (home first)
        decoded = html.unescape(text)

        values = [int(m) for m in re.findall(r'"halfTimeScore"\s*:\s*(\d+)', decoded)]

        if len(values) >= 2:
            # First occurrence = home, second = away (matches page order)
            return values[0], values[1]
        return -1, -1
    except Exception as exc:
        print(f"    Halftime fetch error: {exc}")
        return -1, -1


def run() -> None:
    results: list[GameResult] = []

    # Seed session with NRL.com cookies first
    print("Seeding session with NRL.com cookies...")
    try:
        SESSION.get("https://www.nrl.com/draw/", timeout=15)
        time.sleep(2)
    except Exception as e:
        print(f"  Warning: seed failed: {e}")

    for season in SEASONS:
        print(f"\n=== Season {season} ===")
        for rnd in ROUND_RANGE:
            time.sleep(1)  # rate limit between round requests
            fixtures = fetch_fixtures(season, rnd)
            if not fixtures:
                continue

            # Check first fixture date to see if this round overlaps Origin window
            sample_date = get_game_date(fixtures[0])
            if not sample_date:
                continue

            try:
                month = datetime.fromisoformat(sample_date).month
            except Exception:
                continue

            # Only process rounds that fall in June–July
            if month not in (6, 7):
                continue

            print(f"  R{rnd} ({sample_date}) — {len(fixtures)} games")

            for f in fixtures:
                home_team = f.get("homeTeam", {}).get("nickName", "?")
                away_team = f.get("awayTeam", {}).get("nickName", "?")
                ft_home = int(f.get("homeTeam", {}).get("score", 0) or 0)
                ft_away = int(f.get("awayTeam", {}).get("score", 0) or 0)
                game_date = get_game_date(f)

                # Skip games with no final score (not yet played)
                if ft_home == 0 and ft_away == 0:
                    continue

                mc_path = f.get("matchCentreUrl", "")
                if not mc_path:
                    continue

                mc_url = NRL_BASE + mc_path
                ht_home, ht_away = fetch_halftime_scores(mc_url)
                time.sleep(0.4)  # polite rate limit

                if ht_home == -1:
                    print(f"    SKIP (no HT data): {home_team} vs {away_team}")
                    continue

                print(f"    {home_team} {ht_home}-{ht_away} {away_team} HT → {ft_home}-{ft_away} FT")

                results.append(GameResult(
                    season=season, round=rnd, date=game_date,
                    home=home_team, away=away_team,
                    ht_home=ht_home, ht_away=ht_away,
                    ft_home=ft_home, ft_away=ft_away,
                ))

    # ── Analysis ──────────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"TOTAL GAMES WITH HT DATA: {len(results)}")
    print(f"{'='*60}\n")

    if not results:
        print("No data to analyse.")
        return

    # Filter: team trailing by 1-10 points at halftime
    for team_type in ("home", "away"):
        print(f"\n--- {team_type.upper()} TEAM trailing by 1-10 pts at HT ---")

        trailing = []
        for g in results:
            if team_type == "home":
                deficit = g.ht_away - g.ht_home  # positive = home trailing
                won = g.ft_home > g.ft_away
            else:
                deficit = g.ht_home - g.ht_away  # positive = away trailing
                won = g.ft_away > g.ft_home

            if 1 <= deficit <= 10:
                trailing.append((g, won))

        if not trailing:
            print("  No games found.")
            continue

        wins = sum(1 for _, w in trailing if w)
        total = len(trailing)
        pct = wins / total * 100

        print(f"  Games trailing by 1-10 at HT: {total}")
        print(f"  Came back to win:              {wins}")
        print(f"  Comeback win rate:             {pct:.1f}%")

        # Breakdown by deficit band
        print(f"\n  Breakdown by deficit:")
        for band_lo, band_hi in [(1, 4), (5, 6), (7, 8), (9, 10)]:
            band = [(g, w) for g, w in trailing
                    if band_lo <= (g.ht_away - g.ht_home if team_type == "home" else g.ht_home - g.ht_away) <= band_hi]
            if band:
                bw = sum(1 for _, w in band if w)
                bp = bw / len(band) * 100
                print(f"    {band_lo}-{band_hi} pts down: {bw}/{len(band)} = {bp:.0f}%")

    # Combined (either team)
    print(f"\n--- EITHER TEAM trailing by 1-10 pts at HT (combined) ---")
    combined = []
    for g in results:
        for team_type in ("home", "away"):
            if team_type == "home":
                deficit = g.ht_away - g.ht_home
                won = g.ft_home > g.ft_away
            else:
                deficit = g.ht_home - g.ht_away
                won = g.ft_away > g.ft_home
            if 1 <= deficit <= 10:
                combined.append((team_type, deficit, won))

    wins = sum(1 for _, _, w in combined if w)
    total = len(combined)
    pct = wins / total * 100 if total else 0
    print(f"  Total trailing half-times: {total}")
    print(f"  Comeback wins:             {wins}")
    print(f"  Overall rate:              {pct:.1f}%")

    print(f"\nDone. Seasons: {SEASONS}, Period: June-July (Origin window)")


if __name__ == "__main__":
    run()
