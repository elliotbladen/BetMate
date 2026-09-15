#!/usr/bin/env python3
"""With-or-without-you: a team's record when a player plays, versus when he does not.

This measures INFLUENCE rather than contribution, which is the distinction that
breaks every output-based rating. Van Dijk and Rodri do not lift a team's goal rate
when they play - they are not supposed to - but their absence has repeatedly
collapsed title-winning sides. Goals, ratings and market value all miss that
entirely; the record without them is the only thing that sees it.

METHOD, per team-season:
    leagues?id={league}&season={season}   -> /fixtures/allMatches, historical ids
    matchDetails?matchId={id}             -> both lineups AND the result
One call per match covers the whole squad, so a season costs ~38 calls and yields a
with/without split for every player at once - not 38 calls per player.

⚠️ THE AVAILABILITY BIAS IS REAL AND MUST BE REPORTED, NOT HIDDEN. The best players
   are the ones who never miss: Van Dijk played 39 of 39 in the last year, so his
   "without" sample there is zero. WOWY only says anything in seasons where the
   player actually missed games, which is why this is run over the ACL seasons and
   why the sample size is printed beside every figure. A WOWY computed on two
   missed matches is noise wearing a number.

⚠️ IT IS ALSO CONFOUNDED BY FIXTURE DIFFICULTY. A player who misses a run of easy
   games looks worthless; one who misses a cup run against the best sides looks
   irreplaceable. Opponent strength is not adjusted for here, so treat a single
   season as evidence, never proof.
"""
from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
from urllib.request import Request, urlopen

BASE = "https://www.fotmob.com/api/data"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
_last = 0.0


def _get(url: str) -> dict:
    global _last
    wait = 0.9 - (time.monotonic() - _last)
    if wait > 0:
        time.sleep(wait)
    with urlopen(Request(url, headers={"User-Agent": UA, "Accept": "application/json"}),
                 timeout=30) as r:
        _last = time.monotonic()
        return json.loads(r.read())


def season_matches(league_id: int, season: str, team_id: int) -> list[dict]:
    payload = _get(f"{BASE}/leagues?id={league_id}&season={season.replace('/', '%2F')}")
    allm = (payload.get("fixtures") or {}).get("allMatches") or []
    out = []
    for m in allm:
        home, away = m.get("home") or {}, m.get("away") or {}
        # ⚠️ Historical league payloads give ids as STRINGS ("9879"), unlike the
        # team endpoint which gives ints. Comparing an int against them matched
        # nothing and returned an empty season without any error.
        if str(team_id) not in (str(home.get("id")), str(away.get("id"))):
            continue
        if not (m.get("status") or {}).get("finished"):
            continue
        out.append(m)
    return out


def wowy(league_id: int, season: str, team_id: int, team_name: str) -> dict:
    matches = season_matches(league_id, season, team_id)
    played_by: dict[str, set] = defaultdict(set)
    results: dict[int, tuple[int, int]] = {}     # match id -> (points, goal diff)
    names: dict[str, str] = {}

    for m in matches:
        mid = m["id"]
        try:
            details = _get(f"{BASE}/matchDetails?matchId={mid}")
        except Exception:
            continue
        lineup = (details.get("content") or {}).get("lineup") or {}
        side = "homeTeam" if str((m.get("home") or {}).get("id")) == str(team_id) else "awayTeam"
        team = lineup.get(side) or {}
        for player in (team.get("starters") or []):
            pid = str(player.get("id"))
            played_by[pid].add(mid)
            names[pid] = player.get("name") or ""
        # Substitutes count as having played - the question is availability, not
        # whether he started, and a fit bench player is not an absence.
        for group in (team.get("subs") or []):
            pid = str(group.get("id"))
            if pid and pid != "None":
                played_by[pid].add(mid)
                names.setdefault(pid, group.get("name") or "")

        # The historical payload carries the result in status.scoreStr ("0 - 3"),
        # not as home.score / away.score.
        score = ((m.get("status") or {}).get("scoreStr") or "").split("-")
        if len(score) != 2:
            continue
        try:
            hs, aws = int(score[0].strip()), int(score[1].strip())
        except ValueError:
            continue
        gf, ga = (hs, aws) if side == "homeTeam" else (aws, hs)
        results[mid] = (3 if gf > ga else 1 if gf == ga else 0, gf - ga)

    total = len(results)
    out = []
    for pid, played in played_by.items():
        on = [results[i] for i in results if i in played]
        off = [results[i] for i in results if i not in played]
        if not on or not off:
            continue
        ppg_on = sum(p for p, _ in on) / len(on)
        ppg_off = sum(p for p, _ in off) / len(off)
        gd_on = sum(g for _, g in on) / len(on)
        gd_off = sum(g for _, g in off) / len(off)
        out.append({
            "player": names.get(pid, pid), "player_id": pid,
            "games_with": len(on), "games_without": len(off),
            "ppg_with": round(ppg_on, 2), "ppg_without": round(ppg_off, 2),
            "ppg_delta": round(ppg_on - ppg_off, 2),
            "gd_with": round(gd_on, 2), "gd_without": round(gd_off, 2),
            "gd_delta": round(gd_on - gd_off, 2),
        })
    return {"team": team_name, "season": season, "matches": total,
            "players": sorted(out, key=lambda r: -r["ppg_delta"])}


if __name__ == "__main__":
    CASES = [
        (47, "2020/2021", 8650, "Liverpool"),     # Van Dijk ACL season
        (47, "2024/2025", 8456, "Manchester City"),  # Rodri ACL season
    ]
    for league, season, tid, name in CASES:
        print(f"\n=== {name} {season} ===", flush=True)
        res = wowy(league, season, tid, name)
        print(f"  {res['matches']} league matches with lineup data")
        print(f"  {'player':<24} {'with':<12} {'without':<12} {'PPG delta':<10} GD delta")
        for r in res["players"][:10]:
            if r["games_without"] < 3:
                continue
            print(f"  {r['player']:<24} {r['ppg_with']:.2f} ({r['games_with']:>2})   "
                  f"{r['ppg_without']:.2f} ({r['games_without']:>2})   "
                  f"{r['ppg_delta']:>+6.2f}     {r['gd_delta']:>+5.2f}")
