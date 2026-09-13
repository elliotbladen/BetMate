#!/usr/bin/env python3
"""Football star rating: 2 = a Van Dijk / Rodri / Mbappé. 1 = everyone else.

A 2 must clear BOTH tests. Every approach that failed on this project failed by
using only one of them:

  IS HE FIRST CHOICE?   minutes per appearance, and appearances made. A star plays
                        the whole game whenever he is fit. This is the manager's
                        revealed valuation and it is immune to age and fee.

  IS HE ELITE?          season rating against the 85th percentile of his position
                        group ACROSS THE LEAGUE - not his own squad. Squad-relative
                        would crown the best player at a relegation club.

WHY NOT THE ALTERNATIVES, all tested on live data during this build:

  ❌ MARKET VALUE. Measures resale price and collapses with age: Van Dijk €5m,
     Alisson €12m, while both play every available minute. It rated the owner's two
     canonical stars "not important".

  ❌ WITH-OR-WITHOUT-YOU. The right idea - influence, not output - and fatally
     blocked by availability bias: the best players never miss. Over THREE pooled
     seasons Van Dijk still missed too few games to measure at all, and the top of
     every list was a backup goalkeeper (Kelleher +0.51, Petrovic +0.43) who played
     the games the first choice missed and happened to win them. Real Madrid's list
     led with Nacho and Joselu. Rodri showed up only because an ACL cost him 33
     matches, which is not a basis for a rating system.

  ❌ MINUTES ALONE. Promotes every durable full-back to star.
  ❌ RATING ALONE. Football ratings are compressed (6.5-8.5 covers a league), so it
     cannot separate a good squad player from an irreplaceable one.

Ratings are stamped `rated_on` and written to a dated file. They are never
rewritten: a player who breaks out in March must not retroactively become a star in
an October injury being studied.
"""
from __future__ import annotations

import json
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

BASE = "https://www.fotmob.com/api/data"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

ELITE_PERCENTILE = 85          # of his position group, league-wide
MIN_MINUTES_PER_APP = 70       # he finishes matches; not a rotation option
MIN_APPEARANCE_SHARE = 0.30    # enough evidence, but tolerant of a long injury

_last = 0.0


def _get(url: str) -> dict:
    global _last
    wait = 1.0 - (time.monotonic() - _last)
    if wait > 0:
        time.sleep(wait)
    with urlopen(Request(url, headers={"User-Agent": UA, "Accept": "application/json"}),
                 timeout=30) as r:
        _last = time.monotonic()
        return json.loads(r.read())


def clubs(league_id: int) -> list[tuple[int, str]]:
    payload = _get(f"{BASE}/leagues?id={league_id}")
    found: list[tuple[int, str]] = []

    def walk(node):
        if isinstance(node, dict):
            if "id" in node and "name" in node and "played" in node:
                found.append((int(node["id"]), node["name"]))
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(payload.get("table") or [])
    return list(dict.fromkeys(found))


def squad(team_id: int) -> list[dict]:
    payload = _get(f"{BASE}/teams?id={team_id}")
    out = []
    for group in (payload.get("squad") or {}).get("squad") or []:
        if group.get("title") == "coach":
            continue
        for member in group.get("members", []):
            member["position_group"] = group.get("title")
            out.append(member)
    return out


def league_rating_bar(league_id: int) -> dict[str, float]:
    """85th-percentile season rating per position group, across the whole league."""
    by_group: dict[str, list[float]] = {}
    for team_id, name in clubs(league_id):
        try:
            for member in squad(team_id):
                rating = member.get("rating")
                if rating:
                    by_group.setdefault(member["position_group"], []).append(float(rating))
        except Exception as exc:
            print(f"    {name}: {str(exc)[:50]}", file=sys.stderr)
    bar = {}
    for group, values in by_group.items():
        values.sort()
        idx = min(len(values) - 1, int(len(values) * ELITE_PERCENTILE / 100))
        bar[group] = values[idx]
        print(f"    {group:<14} n={len(values):<4} median={statistics.median(values):.2f} "
              f"p{ELITE_PERCENTILE}={values[idx]:.2f}")
    return bar


def rate_club(team_id: int, team_name: str, league_id: int, bar: dict[str, float]) -> list[dict]:
    rated_on = datetime.now(timezone.utc).date().isoformat()
    members = squad(team_id)

    team_matches: set = set()
    per_player: dict[int, list[dict]] = {}
    for member in members:
        pid = member.get("id")
        try:
            payload = _get(f"{BASE}/playerData?id={pid}")
            matches = [m for m in (payload.get("recentMatches") or [])
                       if m.get("leagueId") == league_id and m.get("teamId") == team_id]
        except Exception:
            matches = []
        per_player[pid] = matches
        team_matches |= {m["id"] for m in matches}

    total = len(team_matches)
    rows = []
    for member in members:
        pid = member.get("id")
        matches = per_player.get(pid, [])
        apps = len(matches)
        minutes = sum(m.get("minutesPlayed") or 0 for m in matches)
        mpa = (minutes / apps) if apps else 0.0
        app_share = (apps / total) if total else 0.0
        rating = member.get("rating")
        group = member.get("position_group")
        threshold = bar.get(group)

        first_choice = mpa >= MIN_MINUTES_PER_APP and app_share >= MIN_APPEARANCE_SHARE
        elite = bool(rating and threshold and float(rating) >= threshold)
        star = first_choice and elite

        rows.append({
            "team": team_name, "player": member.get("name"), "player_id": pid,
            "position_group": group, "season_rating": rating,
            "league_p85": round(threshold, 2) if threshold else None,
            "appearances": apps, "team_matches": total,
            "appearance_share": round(app_share, 2),
            "minutes_per_appearance": round(mpa, 1),
            "first_choice": first_choice, "elite": elite,
            "stars": 2 if star else 1,
            "basis": (f"{mpa:.0f} min/app over {apps}/{total} matches, "
                      f"rating {rating or '-'} vs {group} league p85 "
                      f"{round(threshold,2) if threshold else '-'}"),
            "rated_on": rated_on, "source": "fotmob",
        })
    return rows


CLUBS = [(8650, "Liverpool", 47), (8455, "Chelsea", 47), (8633, "Real Madrid", 87)]

if __name__ == "__main__":
    bars: dict[int, dict[str, float]] = {}
    for league_id, label in ((47, "Premier League"), (87, "LaLiga")):
        print(f"\nleague rating bars — {label}:", flush=True)
        bars[league_id] = league_rating_bar(league_id)

    everything = []
    for team_id, name, league_id in CLUBS:
        print(f"\n=== {name} ===", flush=True)
        rows = rate_club(team_id, name, league_id, bars[league_id])
        rows.sort(key=lambda r: (-r["stars"], -(r["season_rating"] or 0)))
        everything.extend(rows)
        stars = [r for r in rows if r["stars"] == 2]
        print(f"  {'★':<3} {'rating':<7} {'p85':<6} {'min/app':<8} {'apps':<7} {'pos':<12} player")
        for r in rows[:12]:
            print(f"  {r['stars']:<3} {str(r['season_rating'] or '-'):<7} "
                  f"{str(r['league_p85'] or '-'):<6} {r['minutes_per_appearance']:<8.0f} "
                  f"{r['appearances']}/{r['team_matches']:<4} "
                  f"{str(r['position_group'] or '-'):<12} {r['player']}")
        print(f"  2-STAR ({len(stars)}): {', '.join(r['player'] for r in stars) or 'none'}")

    d = Path("data/player_importance"); d.mkdir(parents=True, exist_ok=True)
    p = d / f"football_stars_{datetime.now(timezone.utc).date().isoformat()}.json"
    p.write_text(json.dumps(everything, indent=2), encoding="utf-8")
    print(f"\nwrote {len(everything)} players -> {p}")
