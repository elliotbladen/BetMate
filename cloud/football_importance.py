#!/usr/bin/env python3
"""Football player importance — expected GOALS of supremacy lost if the player is OUT.

The NFL model scores points of spread. Football lines are in goals, so the scale is
different and the NFL numbers cannot be reused. Anchors, from published movement:

  * Haaland ruled out v Brentford moved City from 1.30 to 1.55 - implied win
    probability 76.9% -> 64.5%, a 12.4 point drop, which for a heavy favourite is
    roughly half a goal of supremacy. That is the ceiling case: the best striker in
    the league.
  * Rodri's ACL shifted the title market within hours - a holding midfielder, not a
    forward, which is why midfield is not discounted here.
  * Teams show a 20-30% scoring deficit when their crucial forward is missing.

Tier thresholds are set proportionally to the owner's NFL scheme. There, 3.0 of a
~7-point ceiling is a star, i.e. a bit under half the maximum. Here the ceiling is
~0.55 goals, so:

    >= 0.30 goals  -> 3  star
    0.05 - 0.30    -> 2  important
    < 0.05         -> 1  not important

⚠️ WHAT THIS MODEL REFUSES TO USE, both learned the hard way on this project:

  MARKET VALUE. It measures resale price, not reliance, and collapses with age.
  Van Dijk shows at €5m and Alisson at €12m while both play every available minute.
  A value-based rubric rated the owner's two named examples "not important".

  AVAILABILITY. An earlier NFL version multiplied role by games played, so Nick
  Bosa (4 of 18, injured) scored low. A model for pricing injuries must not penalise
  players for having been injured. Role is measured over games he PLAYED; durability
  is reported separately and never multiplied in.
"""
from __future__ import annotations

import json
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

BASE = "https://www.fotmob.com/api/data"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

TIER_3_GOALS = 0.30
TIER_2_GOALS = 0.05

# Goals of supremacy lost when the FIRST-CHOICE player in this group is out, at
# average quality for the group. Quality then scales it.
BASE_GOALS = {
    "attackers": 0.30,      # the Haaland case sets the ceiling once quality is applied
    "midfielders": 0.24,    # Rodri moved a title market; midfield is not discounted
    "keepers": 0.22,        # the Alisson case - low resale value, high reliance
    "defenders": 0.18,
}
DEFAULT_BASE = 0.18

# Quality multiplier bounds. A squad striker is not Mbappé; the same position can be
# worth three times as much depending on who fills it.
QUALITY_FLOOR, QUALITY_CEILING = 0.45, 1.85

MIN_INTERVAL = 1.1
_last = 0.0


def _get(url: str) -> dict:
    global _last
    wait = MIN_INTERVAL - (time.monotonic() - _last)
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


def rate_club(team_id: int, team_name: str, code: str, league_id: int) -> list[dict]:
    rated_on = datetime.now(timezone.utc).date().isoformat()
    members = squad(team_id)

    histories: dict[int, list[dict]] = {}
    captains: dict[int, bool] = {}
    team_matches: dict[int, dict] = {}
    for member in members:
        pid = member.get("id")
        try:
            payload = _get(f"{BASE}/playerData?id={pid}")
            matches = payload.get("recentMatches") or []
            captains[pid] = bool(payload.get("isCaptain"))
        except Exception:
            matches, captains[pid] = [], False
        histories[pid] = matches
        for m in matches:
            if m.get("leagueId") == league_id and m.get("teamId") == team_id:
                team_matches[m["id"]] = m

    played_count = len(team_matches)
    available = played_count * 90

    rows = []
    for member in members:
        pid = member.get("id")
        league = [m for m in histories.get(pid, [])
                  if m.get("leagueId") == league_id and m.get("teamId") == team_id]
        minutes = sum(m.get("minutesPlayed") or 0 for m in league)
        role = (minutes / available) if available else 0.0

        # WOWY over the same window. Reported, never used to rank: the best players
        # are the ones who never miss, so their "without" sample is empty by
        # definition - Van Dijk played 39 of 39. Availability bias makes it useless
        # as a ranker and valuable as the study metric.
        def points(m):
            gf, ga = ((m["homeScore"], m["awayScore"]) if m.get("isHomeTeam")
                      else (m["awayScore"], m["homeScore"]))
            return (3 if gf > ga else 1 if gf == ga else 0)
        played_ids = {m["id"] for m in league}
        off = [points(m) for m in team_matches.values() if m["id"] not in played_ids]
        on = [points(m) for m in team_matches.values() if m["id"] in played_ids]

        rows.append({
            "code": code, "team": team_name, "player_id": pid,
            "player": member.get("name"), "position_group": member.get("position_group"),
            "captain": captains.get(pid, False), "season_rating": member.get("rating"),
            "league_minutes": minutes, "role_share": round(role, 3),
            "matches_played": len(league), "team_matches": played_count,
            "wowy_ppg_with": round(sum(on) / len(on), 2) if on else None,
            "wowy_ppg_without": round(sum(off) / len(off), 2) if off else None,
            "wowy_games_without": len(off),
            "rated_on": rated_on, "source": "fotmob",
        })

    # Quality is judged inside the position group. A keeper's 6.85 and a forward's
    # 7.4 were never on the same scale, and comparing them buries every Alisson.
    for group in {r["position_group"] for r in rows}:
        peers = [r["season_rating"] for r in rows
                 if r["position_group"] == group and r["season_rating"]]
        median = statistics.median(peers) if peers else None
        for r in rows:
            if r["position_group"] != group:
                continue
            base = BASE_GOALS.get(group, DEFAULT_BASE)
            rating = r["season_rating"]
            if median and rating:
                # Rating differences in football are compressed - 6.5 to 8.0 covers
                # the whole league - so a small ratio is amplified before clamping.
                quality = 1.0 + (rating - median) / max(median, 1.0) * 6.0
            else:
                quality = 0.85
            quality = max(QUALITY_FLOOR, min(QUALITY_CEILING, quality))
            goals = base * r["role_share"] * quality
            if r["captain"]:
                goals *= 1.10
            r["quality_mult"] = round(quality, 2)
            r["goals_if_out"] = round(goals, 3)
            r["tier"] = (3 if goals >= TIER_3_GOALS else 2 if goals >= TIER_2_GOALS else 1)
            r["tier_label"] = {1: "not important", 2: "important", 3: "star"}[r["tier"]]
            r["basis"] = (f"{group} playing {r['role_share']:.0%} of minutes, "
                          f"rating {rating or '-'} vs group median {median or '-'}"
                          + (", captain" if r["captain"] else ""))
    return rows


CLUBS = [(8650, "Liverpool", "EPL", 47), (8455, "Chelsea", "EPL", 47),
         (8633, "Real Madrid", "UCL", 42)]

if __name__ == "__main__":
    everything: list[dict] = []
    for tid, name, code, lid in CLUBS:
        print(f"\n=== {name} ===", flush=True)
        rows = rate_club(tid, name, code, lid)
        rows.sort(key=lambda r: -r["goals_if_out"])
        everything.extend(rows)
        print(f"  {'goals':<7} {'tier':<5} {'mins':<6} {'rtg':<6} {'qual':<6} {'pos':<12} player")
        for r in rows[:10]:
            print(f"  {r['goals_if_out']:<7.3f} {r['tier']:<5} {r['role_share']:<6.0%} "
                  f"{str(r['season_rating'] or '-'):<6} {r['quality_mult']:<6.2f} "
                  f"{str(r['position_group'] or '-'):<12} {r['player']}")
        stars = [r["player"] for r in rows if r["tier"] == 3]
        print(f"  STARS ({len(stars)}): {', '.join(stars) or 'none'}")

    d = Path("data/player_importance"); d.mkdir(parents=True, exist_ok=True)
    p = d / f"football_importance_{datetime.now(timezone.utc).date().isoformat()}.json"
    p.write_text(json.dumps(everything, indent=2), encoding="utf-8")
    print(f"\nwrote {len(everything)} players -> {p}")
