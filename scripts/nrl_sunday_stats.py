"""
NRL match stats report — extracts team stats from match centre pages.
Reports lucky/unlucky signals based on stats vs result.

Usage: uv run --with requests python scripts/nrl_sunday_stats.py
"""
from __future__ import annotations

import html
import json
import re
import time
from datetime import datetime

import requests

SEASON = 2026
ROUND = 15
NRL_BASE = "https://www.nrl.com"

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/json,*/*",
    "Accept-Language": "en-AU,en;q=0.9",
    "Referer": "https://www.nrl.com/draw/",
    "Origin": "https://www.nrl.com",
})


def seed():
    SESSION.get("https://www.nrl.com/draw/", timeout=15)
    time.sleep(2)


def fetch_round(season: int, rnd: int) -> list[dict]:
    url = f"{NRL_BASE}/draw/data/?competition=111&season={season}&round={rnd}"
    for _ in range(3):
        try:
            r = SESSION.get(url, timeout=20)
            if r.status_code == 200 and r.text.strip() and r.text[0] in "{[":
                return [f for f in r.json().get("fixtures", []) if f.get("type") == "Match"]
        except Exception as e:
            print(f"  API error: {e}")
        time.sleep(3)
    return []


def extract_bracket(text: str, start: int) -> str:
    """Extract a complete JSON object starting at text[start] (must be '{')."""
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return ""


def parse_stats(page: str) -> dict[str, tuple[float, float]] | None:
    """
    Find the stats.groups blob in the page and return a dict of
    {stat_title: (home_value, away_value)}.
    """
    # Find the outer container that has topPerformers AND groups
    marker = '"stats":{"topPerformers":'
    idx = page.find(marker)
    if idx == -1:
        return None

    # Back up to the opening { of the stats object
    stats_start = page.rfind("{", 0, idx + len(marker))
    if stats_start == -1:
        return None

    blob = extract_bracket(page, stats_start)
    if not blob:
        return None

    try:
        data = json.loads(blob)
    except Exception:
        return None

    # blob IS the stats object ({"topPerformers":..., "groups":...})
    groups = data.get("groups", [])

    result: dict[str, tuple[float, float]] = {}
    for group in groups:
        for stat in group.get("stats", []):
            title = stat.get("title", "")
            hv = stat.get("homeValue", {})
            av = stat.get("awayValue", {})
            h = hv.get("value")
            a = av.get("value")
            if h is not None and a is not None:
                result[title] = (float(h), float(a))

    return result if result else None


def get_match_date(fixture: dict) -> str:
    kick = fixture.get("clock", {}).get("kickOffTimeLong", "")
    try:
        return datetime.fromisoformat(kick.replace("Z", "+00:00")).strftime("%a %d %b")
    except Exception:
        return "?"


def get_ht_score(page: str) -> tuple[int, int]:
    vals = re.findall(r'"halfTimeScore"\s*:\s*(\d+)', page)
    if len(vals) >= 2:
        return int(vals[0]), int(vals[1])
    return 0, 0


def analyse_game(mc_path: str, home: str, away: str, score_h: int, score_a: int, date: str) -> None:
    mc_url = NRL_BASE + mc_path
    print(f"\n{'='*65}")
    print(f"  {date}  |  {home} {score_h} – {score_a} {away}")
    print(f"{'='*65}")

    try:
        r = SESSION.get(mc_url, timeout=25)
        r.raise_for_status()
        page = html.unescape(r.text)
    except Exception as e:
        print(f"  Could not fetch: {e}")
        return

    ht_h, ht_a = get_ht_score(page)
    if ht_h or ht_a:
        print(f"  HT: {home} {ht_h} – {ht_a} {away}")

    stats = parse_stats(page)
    if not stats:
        print("  No team stats found.")
        return

    # Key stats to display (in order)
    DISPLAY = [
        "Possession %",
        "Completion Rate",
        "All Run Metres",
        "Errors",
        "Missed Tackles",
        "Penalty Goals",
        "Penalties Conceded",
        "Line Breaks",
        "Line Break Assists",
        "Try Assists",
        "Tries Scored",
        "Kick Metres",
        "All Runs",
    ]

    found_display = {k: v for k, v in stats.items() if k in DISPLAY}
    # Also include any stats we found but didn't list
    others = {k: v for k, v in stats.items() if k not in DISPLAY}

    print(f"\n  {'Stat':<26} {home:<20} {away:<20}")
    print(f"  {'-'*66}")
    for label in DISPLAY:
        if label in stats:
            h, a = stats[label]
            hstr = f"{h:.0f}" if h == int(h) else f"{h:.1f}"
            astr = f"{a:.0f}" if a == int(a) else f"{a:.1f}"
            leader = ""
            if label in ("Possession %", "Completion Rate", "All Run Metres", "Line Breaks"):
                if h > a:
                    hstr += " *"
                elif a > h:
                    astr += " *"
            print(f"  {label:<26} {hstr:<20} {astr:<20}")

    # Lucky / unlucky analysis
    home_won = score_h > score_a
    away_won = score_a > score_h

    lucky: dict[str, list[str]] = {home: [], away: []}
    unlucky: dict[str, list[str]] = {home: [], away: []}

    def flag(stat: str, higher_is_better: bool = True) -> None:
        """Flag lucky (won with worse stat) and unlucky (lost with better stat)."""
        if stat not in stats:
            return
        h, a = stats[stat]
        if h == a:
            return

        home_better = (h > a) if higher_is_better else (h < a)
        away_better = not home_better

        h_str = f"{h:.0f}" if h == int(h) else f"{h:.1f}"
        a_str = f"{a:.0f}" if a == int(a) else f"{a:.1f}"

        # Unlucky: had better stat but lost
        if home_better and away_won:
            unlucky[home].append(f"better {stat} ({h_str} vs {a_str}) but lost")
        if away_better and home_won:
            unlucky[away].append(f"better {stat} ({a_str} vs {h_str}) but lost")

        # Lucky: won despite having WORSE stat
        if not home_better and home_won:
            lucky[home].append(f"won with less {stat} ({h_str} vs {a_str})")
        if not away_better and away_won:
            lucky[away].append(f"won with less {stat} ({a_str} vs {h_str})")

    def flag_bad_stat(stat: str) -> None:
        """Higher value = worse (errors, missed tackles, penalties)."""
        if stat not in stats:
            return
        h, a = stats[stat]
        if h == a:
            return
        h_str = f"{h:.0f}" if h == int(h) else f"{h:.1f}"
        a_str = f"{a:.0f}" if a == int(a) else f"{a:.1f}"

        if h > a and home_won:
            lucky[home].append(f"won despite more {stat} ({h_str} vs {a_str})")
        if a > h and away_won:
            lucky[away].append(f"won despite more {stat} ({a_str} vs {h_str})")
        if h < a and away_won:
            unlucky[home].append(f"fewer {stat} ({h_str}) but lost")
        if a < h and home_won:
            unlucky[away].append(f"fewer {stat} ({a_str}) but lost")

    flag("Possession %")
    flag("Completion Rate")
    flag("All Run Metres")
    flag("Line Breaks")
    flag("Try Assists")
    flag_bad_stat("Errors")
    flag_bad_stat("Missed Tackles")
    flag_bad_stat("Penalties Conceded")

    print(f"\n  LUCKY:")
    has = False
    for team in [home, away]:
        for s in lucky[team]:
            print(f"    ++ {team}: {s}")
            has = True
    if not has:
        print("    (no significant lucky signals)")

    print(f"\n  UNLUCKY:")
    has = False
    for team in [home, away]:
        for s in unlucky[team]:
            print(f"    -- {team}: {s}")
            has = True
    if not has:
        print("    (no significant unlucky signals)")


def main():
    print(f"NRL {SEASON} Round {ROUND} — Stats & Lucky/Unlucky Report")
    print("=" * 65)
    seed()

    fixtures = fetch_round(SEASON, ROUND)
    completed = [
        f for f in fixtures
        if f.get("homeTeam", {}).get("score") is not None
        and f.get("awayTeam", {}).get("score") is not None
        and str(f.get("homeTeam", {}).get("score", "")).strip() not in ("", "None")
    ]
    print(f"\n{len(completed)} completed games in Round {ROUND}")

    for f in completed:
        home = f.get("homeTeam", {}).get("nickName", "?")
        away = f.get("awayTeam", {}).get("nickName", "?")
        score_h = int(f.get("homeTeam", {}).get("score", 0) or 0)
        score_a = int(f.get("awayTeam", {}).get("score", 0) or 0)
        mc = f.get("matchCentreUrl", "")
        date = get_match_date(f)
        if mc:
            time.sleep(1.5)
            analyse_game(mc, home, away, score_h, score_a, date)

    print("\n\nDone.")


if __name__ == "__main__":
    main()
