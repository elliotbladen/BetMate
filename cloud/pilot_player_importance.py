#!/usr/bin/env python3
"""PILOT: rate one club's players 1/2/3 from minutes share, with WOWY where it exists.

Run on a handful of clubs so the owner can eyeball the output against his own
judgement BEFORE ~2,300 API calls go into the full build. A rubric that disagrees
with an expert's read of his own team is wrong, however defensible the arithmetic.

METHOD - and why, since the obvious approach already failed once:

  RANKER = MINUTES SHARE. minutes played / minutes available in league matches.
  This is the manager's revealed valuation, re-expressed every week. It is immune
  to age and to resale value - the trap that rated Van Dijk (€5m) and Alisson
  (€12m) as "not important" while both played every available minute.

  QUALITY SPLIT = season rating, compared WITHIN the squad and WITHIN the position
  group. A goalkeeper's 6.85 and a forward's 7.4 are not on the same scale, so
  comparing a keeper to a striker on raw rating would bury every Alisson.

  WOWY = reported, never used to rank. Van Dijk played 39 of 39, so his "without"
  sample is zero - the availability bias means the best players are the hardest to
  measure by absence. It is shown here because it is the study metric the whole
  database exists to feed, and because a large negative delta is confirmation.

Everything is stamped `rated_on` and written to a dated file. Ratings are never
rewritten: a player who breaks out in March must not retroactively become a star in
an October injury we are measuring.
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

STAR_MINUTES = 0.70        # plays essentially every week
REGULAR_MINUTES = 0.35     # a real part of the rotation
MIN_TEAM_MATCHES = 5       # below this, shares are noise

_last = 0.0


def _get(url: str) -> dict:
    global _last
    wait = 1.1 - (time.monotonic() - _last)
    if wait > 0:
        time.sleep(wait)
    with urlopen(Request(url, headers={"User-Agent": UA, "Accept": "application/json"}),
                 timeout=30) as r:
        _last = time.monotonic()
        return json.loads(r.read())


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


def player_history(player_id: int) -> list[dict]:
    """League matches this player appeared in, over FotMob's ~1 year window."""
    payload = _get(f"{BASE}/playerData?id={player_id}")
    return payload.get("recentMatches") or [], bool(payload.get("isCaptain"))


def rate_club(team_id: int, team_name: str, code: str, league_id: int) -> list[dict]:
    rated_on = datetime.now(timezone.utc).date().isoformat()
    members = squad(team_id)

    histories: dict[int, tuple[list[dict], bool]] = {}
    team_matches: dict[int, dict] = {}     # match id -> result, from any player's history
    for member in members:
        pid = member.get("id")
        try:
            matches, captain = player_history(pid)
        except Exception:
            matches, captain = [], False
        histories[pid] = (matches, captain)
        for m in matches:
            if m.get("leagueId") == league_id and m.get("teamId") == team_id:
                team_matches[m["id"]] = m

    # The union of every player's appearances IS the team's match list - no separate
    # fixtures call needed, and it cannot include a match the club did not play.
    played_count = len(team_matches)
    available_minutes = played_count * 90

    rows = []
    for member in members:
        pid = member.get("id")
        matches, captain = histories[pid]
        league = [m for m in matches if m.get("leagueId") == league_id and m.get("teamId") == team_id]
        minutes = sum(m.get("minutesPlayed") or 0 for m in league)
        share = (minutes / available_minutes) if available_minutes else None

        # WOWY over the same window: results in matches he played vs the rest.
        def points(m):
            gf, ga = ((m["homeScore"], m["awayScore"]) if m.get("isHomeTeam")
                      else (m["awayScore"], m["homeScore"]))
            return (3 if gf > ga else 1 if gf == ga else 0), gf - ga

        played_ids = {m["id"] for m in league}
        on = [points(m) for m in team_matches.values() if m["id"] in played_ids]
        off = [points(m) for m in team_matches.values() if m["id"] not in played_ids]
        ppg_on = round(sum(p for p, _ in on) / len(on), 2) if on else None
        ppg_off = round(sum(p for p, _ in off) / len(off), 2) if off else None

        rows.append({
            "code": code, "team": team_name, "player_id": pid,
            "player": member.get("name"), "position_group": member.get("position_group"),
            "captain": captain, "season_rating": member.get("rating"),
            "league_minutes": minutes, "minutes_share": round(share, 3) if share is not None else None,
            "matches_played": len(league), "team_matches": played_count,
            "wowy_ppg_with": ppg_on, "wowy_ppg_without": ppg_off,
            "wowy_games_without": len(off),
            "rated_on": rated_on,
        })

    # Quality is judged inside the position group, so keepers are not measured
    # against forwards on a scale that was never comparable.
    for group in {r["position_group"] for r in rows}:
        peers = [r["season_rating"] for r in rows
                 if r["position_group"] == group and r["season_rating"]]
        median = statistics.median(peers) if peers else None
        for r in rows:
            if r["position_group"] != group:
                continue
            share, rating = r["minutes_share"], r["season_rating"]
            if played_count < MIN_TEAM_MATCHES or share is None:
                r["tier"], r["basis"] = 1, "insufficient data"
            elif share >= STAR_MINUTES and median and rating and rating >= median:
                r["tier"] = 3
                r["basis"] = f"plays {share:.0%} of minutes, rating {rating} at/above {group} median {median}"
            elif share >= STAR_MINUTES:
                r["tier"] = 2
                r["basis"] = f"plays {share:.0%} of minutes but rating below {group} median"
            elif share >= REGULAR_MINUTES:
                r["tier"] = 2
                r["basis"] = f"rotation player, {share:.0%} of minutes"
            else:
                r["tier"] = 1
                r["basis"] = f"fringe, {share:.0%} of minutes"
            if r["captain"] and r["tier"] < 3 and share and share >= REGULAR_MINUTES:
                r["tier"], r["basis"] = 3, r["basis"] + "; club captain"
            r["tier_label"] = {1: "not important", 2: "important", 3: "star"}[r["tier"]]
    return rows


if __name__ == "__main__":
    CLUBS = [(8650, "Liverpool", "EPL", 47), (8455, "Chelsea", "EPL", 47),
             (8633, "Real Madrid", "UCL", 42)]
    out: list[dict] = []
    for tid, name, code, lid in CLUBS:
        print(f"\n=== {name} ===", flush=True)
        rows = rate_club(tid, name, code, lid)
        rows.sort(key=lambda r: (-r["tier"], -(r["minutes_share"] or 0)))
        out.extend(rows)
        print(f"  {'tier':<5} {'mins%':<7} {'rating':<7} {'W/O':<5} {'pos':<12} player")
        for r in rows[:16]:
            ms = f"{r['minutes_share']:.0%}" if r["minutes_share"] is not None else "-"
            wo = f"{r['wowy_games_without']}" if r["wowy_games_without"] is not None else "-"
            print(f"  {r['tier']:<5} {ms:<7} {str(r['season_rating'] or '-'):<7} {wo:<5} "
                  f"{str(r['position_group'] or '-'):<12} {r['player']}")
    d = Path("data/player_importance"); d.mkdir(parents=True, exist_ok=True)
    path = d / f"pilot_{datetime.now(timezone.utc).date().isoformat()}.json"
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nwrote {len(out)} players -> {path}")
