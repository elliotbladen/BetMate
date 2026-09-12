#!/usr/bin/env python3
"""Point-in-time player importance (tier 1 / 2 / 3) — DESIGN NOTES.

⚠️ STATUS: the market-value approach in this file's first version is REJECTED and
   the scoring below is being rebuilt. Read the rejection before reusing any of it.

PURPOSE. Stamp every injured player captured by the team-news collector with an
importance tier, so that at season end we can ask:
  1. how far does the market move when a tier 3 goes down, versus a tier 1?
  2. does OUR engine move the same amount - i.e. do we price injuries correctly?
The second is the more valuable question: it scores us, not just the market.

❌ MARKET VALUE IS DISQUALIFIED. Measured 2026-09-13 on the two players the owner
   named as the definition of a tier 3:

       Virgil van Dijk   €5m    started 4/4, played 360 of 360 minutes, rating 7.47
       Alisson Becker    €12m   played 4/4, 360 of 360 minutes, rating 6.85
       Florian Wirtz     €94m   started 4/4, 332 minutes, rating 7.38

   Transfer value collapses with age. Van Dijk and Alisson are mid-thirties, so a
   value-based rubric rates both TIER 1 "not important" while they play every
   single minute. It failed on the exact cases it had to get right. It also
   produced ZERO tier 3s for Liverpool - an evenly expensive squad flattens any
   share-of-squad measure - while giving Manchester City one, purely because
   Haaland is an outlier within his own squad.

   The deeper problem: market value measures RESALE PRICE, not reliance.

✅ WHAT TO USE INSTEAD

   1. MINUTES SHARE (primary, cheap, always available).
      minutes played / minutes available. This is the manager's revealed
      valuation - he picks the players he cannot do without, every week, whatever
      their age or resale value. Van Dijk and Alisson both score 100%.
      Source: playerData -> mainLeague.stats -> minutes_played, started, matches.

   2. WITH-OR-WITHOUT-YOU (the impact measure, owner's suggestion).
      Team points-per-game and goal difference in matches the player started
      versus matches he missed. This is the only signal that measures what his
      ABSENCE costs, which is exactly the quantity the market is pricing.
      Source: walk each team's season fixtures via matchDetails - one call returns
      both teams' lineups AND the result, so a whole league season is ~380 calls
      for the EPL, ~550 for the Championship, ~190 for the UCL.
      ⚠️ Needs a minimum sample of matches missed before it means anything, and it
      is confounded by fixture difficulty - a player who missed a run of easy
      games will look worthless. Opponent-adjust, or require a sample floor and
      treat it as a modifier on minutes share rather than a standalone score.

   3. CAPTAINCY (playerData.isCaptain) - a direct leadership marker.

   4. POSITION. A first-choice goalkeeper and an NFL starting quarterback are
      structurally more important than their other numbers suggest. The NFL case
      is the strongest in any code: the QB is the one position where the backup
      changes the line by points on his own.

⚠️ POINT IN TIME. A rating is stamped with `rated_on` and never rewritten. If a
   squad player breaks through in March and we relabel him a star, then look back
   at his October injury, we would "discover" the market ignored a star - when he
   was not one yet and the market was right. Every rebuild writes a NEW dated file.

NFL. Market value has no equivalent; cap hit is the nearest and carries the SAME
age/contract distortion plus a worse one - stars on rookie contracts have tiny cap
hits. Use snap share (the minutes-share analogue) and starter status. Spotrac is
server-rendered and parseable (li/div, not tables); nfl.com depth charts 404 and
pro-football-reference 403s.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

BASE = "https://www.fotmob.com/api/data"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

LEAGUES = {"EPL": 47, "EFL": 48, "UCL": 42}

# Share of the squad's total starter market value.
STAR_SHARE = 0.105        # ~1 in 9.5 of the XI's value sitting in one player
IMPORTANT_SHARE = 0.055
MIN_RATED_PLAYERS = 8     # below this, a squad's shares are too noisy to trust

MIN_INTERVAL = 1.2
_last = 0.0


@dataclass
class PlayerRating:
    code: str
    team_id: int
    team_name: str
    source_player_id: str
    player_name: str
    position_group: str | None
    tier: int
    tier_label: str
    market_value: int | None
    squad_value_share: float | None
    season_rating: float | None
    basis: str                 # WHY this tier - never leave a rating unexplained
    rated_on: str              # the date this rating was true. Never overwritten.
    source: str = "fotmob"

    def to_dict(self) -> dict:
        return asdict(self)


def _get(url: str) -> dict:
    global _last
    wait = MIN_INTERVAL - (time.monotonic() - _last)
    if wait > 0:
        time.sleep(wait)
    with urlopen(Request(url, headers={"User-Agent": UA, "Accept": "application/json"}),
                 timeout=30) as r:
        _last = time.monotonic()
        return json.loads(r.read())


def clubs(code: str) -> list[tuple[int, str]]:
    """Clubs in a competition, from the league table."""
    payload = _get(f"{BASE}/leagues?id={LEAGUES[code]}")
    found: list[tuple[int, str]] = []

    def walk(node):
        if isinstance(node, dict):
            if "id" in node and "name" in node and "played" in node:
                found.append((node["id"], node["name"]))
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(payload.get("table") or [])
    return list(dict.fromkeys(found))


def squad(team_id: int) -> list[dict]:
    """Full roster with form. NOTE: carries no market value - that is lineup-only."""
    payload = _get(f"{BASE}/teams?id={team_id}")
    groups = (payload.get("squad") or {}).get("squad") or []
    out = []
    for group in groups:
        title = group.get("title")
        if title == "coach":
            continue
        for member in group.get("members", []):
            member["position_group"] = title
            out.append(member)
    return out


def market_values(team_id: int, lookback_fixtures: int = 6) -> dict[str, int]:
    """Map player id -> market value, harvested from recent lineup payloads.

    Market value appears ONLY in matchDetails lineups, never in the squad payload -
    verified across Coventry, Manchester United and Manchester City, where squad
    marketValue was null for every one of 85 players while the XI had it for all 11.
    So we walk recent fixtures and accumulate. Players who never made a matchday
    squad end with no value, which is itself weak evidence they are tier 1.
    """
    payload = _get(f"{BASE}/teams?id={team_id}")
    fixtures = (payload.get("fixtures") or {}).get("allFixtures", {}).get("fixtures", [])
    played = [f for f in fixtures if (f.get("status") or {}).get("finished")][-lookback_fixtures:]
    values: dict[str, int] = {}
    for fixture in played:
        try:
            details = _get(f"{BASE}/matchDetails?matchId={fixture['id']}")
        except Exception:
            continue
        lineup = (details.get("content") or {}).get("lineup") or {}
        for side in ("homeTeam", "awayTeam"):
            team = lineup.get(side) or {}
            if team.get("id") != team_id:
                continue
            for group in ("starters", "unavailable"):
                for player in team.get(group) or []:
                    mv = player.get("marketValue")
                    if mv:
                        values[str(player["id"])] = int(mv)
    return values


def assign_tiers(code: str, team_id: int, team_name: str,
                 members: list[dict], values: dict[str, int], rated_on: str) -> list[PlayerRating]:
    """Tier a squad. Shares are computed against THIS squad, never across leagues."""
    known = [v for v in values.values() if v]
    total = sum(known)
    enough = len(known) >= MIN_RATED_PLAYERS and total > 0

    out: list[PlayerRating] = []
    for member in members:
        pid = str(member.get("id"))
        mv = values.get(pid)
        share = (mv / total) if (enough and mv) else None
        group = member.get("position_group")
        rating = member.get("rating")

        if share is not None and share >= STAR_SHARE:
            tier, basis = 3, f"market value is {share:.1%} of squad"
        elif share is not None and share >= IMPORTANT_SHARE:
            tier, basis = 2, f"market value is {share:.1%} of squad"
        elif share is not None:
            tier, basis = 1, f"market value is {share:.1%} of squad"
        elif mv:
            tier, basis = 1, "market value known but squad coverage too thin to compare"
        else:
            # Never appeared in a matchday XI or absence list in the lookback.
            tier, basis = 1, "no market value seen in recent squads"

        # Keepers: transfer value understates how much a first choice matters.
        if group == "keepers" and tier < 2 and mv:
            tier, basis = 2, basis + "; goalkeeper floor applied"

        out.append(PlayerRating(
            code=code, team_id=team_id, team_name=team_name,
            source_player_id=pid, player_name=member.get("name", ""),
            position_group=group, tier=tier,
            tier_label={1: "not important", 2: "important", 3: "star"}[tier],
            market_value=mv, squad_value_share=round(share, 5) if share else None,
            season_rating=rating, basis=basis, rated_on=rated_on,
        ))
    return out


def build(codes=("EPL",), out_dir: Path = Path("data/player_importance")) -> Path:
    rated_on = datetime.now(timezone.utc).date().isoformat()
    rows: list[dict] = []
    for code in codes:
        for team_id, team_name in clubs(code):
            try:
                members = squad(team_id)
                values = market_values(team_id)
                rows.extend(r.to_dict() for r in
                            assign_tiers(code, team_id, team_name, members, values, rated_on))
                tiers = [r["tier"] for r in rows if r["team_id"] == team_id]
                print(f"  {code} {team_name:<26} n={len(members):<3} valued={len(values):<3} "
                      f"3s={tiers.count(3)} 2s={tiers.count(2)} 1s={tiers.count(1)}")
            except Exception as exc:
                print(f"  {code} {team_name:<26} FAILED: {str(exc)[:60]}")

    out_dir.mkdir(parents=True, exist_ok=True)
    # Dated filename: a rebuild never overwrites an earlier view of the world.
    path = out_dir / f"player_importance_{rated_on}.json"
    path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    return path


if __name__ == "__main__":
    import sys
    codes = tuple(sys.argv[1:]) or ("EPL",)
    path = build(codes)
    data = json.loads(path.read_text())
    print(f"\nwrote {len(data)} players -> {path}")
    for tier in (3, 2, 1):
        print(f"  tier {tier}: {sum(1 for r in data if r['tier'] == tier)}")
