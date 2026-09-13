#!/usr/bin/env python3
"""NFL player importance v2 — expected SPREAD MOVEMENT, not tiers.

WHAT CHANGED AND WHY (owner review, 2026-09-13)

v1 rated availability, not importance, and got two things badly wrong:

  ❌ Nick Bosa and Fred Warner were missing entirely. v1 scored
     (games_played / team_games) x snap_pct, so a player who MISSED games scored
     low. Bosa played 4 of 18, Warner 7 of 18 - both injured. The formula rated
     injured stars as unimportant, which is exactly backwards for a model whose
     whole purpose is pricing injuries. Same class of error as transfer value
     rating Van Dijk at €5m.

     FIX: role and availability are now SEPARATE fields. Importance is "how much
     does this team lose when he is out", which is a property of his role when fit.
     Durability is recorded alongside it, never multiplied into it.

  ❌ nflverse lists Bosa's position as "DL", which v1 scored 1.2 - the interior
     lineman weight - so the best pass rusher in football was priced as a nose
     tackle. FIX: positions now come from depth_charts.pos_abb, which gives RDE /
     LDE / MLB / RCB / LT, plus pos_rank where 1 = starter.

THE SCALE IS POINTS OF SPREAD, grounded in published oddsmaker figures rather than
invented weights:

    starting QB                        3-7 pts (elite 4 to a touchdown)
    elite edge rusher / shutdown CB    0.5-1.5
    starting OL / top WR               0.5-1
    RB, LB, S                          0-0.5

"Only an injury to a starting QB is going to significantly move the point spread"
outside a handful of skill players - which is why the gap below is deliberately
steep, and why a flat "3 stars per team" was the wrong shape. A team has one player
whose absence is worth 5 points and perhaps two worth ~1. Tiers are DERIVED from
the points, so they inherit that shape instead of imposing a quota.

⚠️ This also answers the owner's modelling note: do NOT apply one injury penalty to
   every "star OUT". Purdy out and Lenoir out are not the same event, and this
   column is the number the shadow model should consume.
"""
from __future__ import annotations

import csv
import io
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

BASE = "https://github.com/nflverse/nflverse-data/releases/download"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Safari/537.36"

# Expected points of spread movement if a FIRST-CHOICE player at this position is
# ruled out. Midpoints of the published ranges above.
POINTS_IF_OUT = {
    "QB": 5.0,
    "RDE": 1.2, "LDE": 1.2, "DE": 1.2, "OLB": 0.9,   # edge rush
    "LT": 1.1,                                        # blindside, protects the QB
    "RCB": 0.9, "LCB": 0.9, "CB": 0.9, "NB": 0.5,     # shutdown corner
    "WR": 0.8, "SWR": 0.5,
    "RT": 0.6, "LG": 0.45, "RG": 0.45, "C": 0.5,
    "TE": 0.5,
    "DT": 0.5, "NT": 0.4,
    "FS": 0.35, "SS": 0.35, "S": 0.35,
    "MLB": 0.35, "WLB": 0.35, "SLB": 0.3, "LB": 0.35,
    "RB": 0.3, "FB": 0.1,
    "K": 0.25, "P": 0.15, "LS": 0.05, "KR": 0.1, "PR": 0.1,
}
DEFAULT_POINTS = 0.3

# A backup's absence costs almost nothing; the cost of HIS absence is not the cost
# of the starter's. Depth rank, not snap count, is the honest signal here.
RANK_FACTOR = {1: 1.0, 2: 0.25, 3: 0.08}
DEFAULT_RANK_FACTOR = 0.04

TIER_3_POINTS = 1.0     # a full point of spread is a genuine market event
TIER_2_POINTS = 0.4


def fetch_csv(url: str) -> list[dict]:
    with urlopen(Request(url, headers={"User-Agent": UA}), timeout=90) as r:
        return list(csv.DictReader(io.StringIO(r.read().decode("utf-8", "ignore"))))


def _f(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def rate_team(team: str, depth: list[dict], snaps: list[dict]) -> list[dict]:
    rated_on = datetime.now(timezone.utc).date().isoformat()

    # Latest depth-chart entry per player: the roster as it stands now.
    latest: dict[str, dict] = {}
    for row in depth:
        if row.get("team") != team:
            continue
        name = row.get("player_name")
        if not name:
            continue
        if name not in latest or (row.get("dt") or "") > (latest[name].get("dt") or ""):
            latest[name] = row

    by_player: dict[str, list[dict]] = defaultdict(list)
    for row in snaps:
        if row.get("team") == team and row.get("game_type") == "REG":
            by_player[row["player"]].append(row)
    team_games = len({(r["season"], r["week"]) for r in snaps
                      if r.get("team") == team and r.get("game_type") == "REG"})

    out = []
    for name, row in latest.items():
        pos = (row.get("pos_abb") or "").upper()
        try:
            rank = int(row.get("pos_rank") or 99)
        except ValueError:
            rank = 99

        apps = by_player.get(name, [])
        played = len(apps)
        # Role when FIT - the mean share of snaps in games he actually appeared in.
        # Availability is reported separately and never multiplied in.
        if apps:
            off = sum(_f(a["offense_snaps"]) for a in apps)
            dfn = sum(_f(a["defense_snaps"]) for a in apps)
            field = "offense_pct" if off >= dfn else "defense_pct"
            role = sum(_f(a[field]) for a in apps) / played
        else:
            role = 0.0

        base = POINTS_IF_OUT.get(pos, DEFAULT_POINTS)
        factor = RANK_FACTOR.get(rank, DEFAULT_RANK_FACTOR)

        # A BACKUP quarterback is not a small quarterback. The 5.0 base is the cost
        # of losing the STARTER; applying a rank discount to it still left Mac Jones
        # at 1.20 and therefore a "star". The honest question is what the market does
        # when THIS player is ruled out, and for a QB2 the answer is almost nothing -
        # the QB3 only ever plays if the starter is also gone. Priced as the
        # insurance policy it is.
        if pos == "QB" and rank >= 2:
            base, factor = 0.2, 1.0
        # Snap role only MODULATES, between 0.7x and 1.0x, so that a rotational
        # edge rusher (Bosa plays ~63% of snaps by design) is not punished for how
        # his position is used. v1 let this term dominate and lost him entirely.
        modulation = 0.7 + 0.3 * min(role / 0.85, 1.0) if role else 0.7
        points = round(base * factor * modulation, 2)

        tier = 3 if points >= TIER_3_POINTS else (2 if points >= TIER_2_POINTS else 1)
        out.append({
            "code": "NFL", "team": team, "player": name, "position": pos,
            "depth_rank": rank, "role_snap_pct": round(role, 3),
            "games_played": played, "team_games": team_games,
            "availability": round(played / team_games, 3) if team_games else None,
            "points_if_out": points, "tier": tier,
            "tier_label": {1: "not important", 2: "important", 3: "star"}[tier],
            "basis": f"{pos} depth-rank {rank}, plays {role:.0%} of snaps when fit",
            "rated_on": rated_on,
        })
    return out


if __name__ == "__main__":
    depth = fetch_csv(f"{BASE}/depth_charts/depth_charts_2026.csv")
    snaps: list[dict] = []
    for season in (2025, 2026):
        snaps += fetch_csv(f"{BASE}/snap_counts/snap_counts_{season}.csv")

    everything = []
    for team, label in (("SF", "San Francisco 49ers"), ("JAX", "Jacksonville Jaguars")):
        rated = [r for r in rate_team(team, depth, snaps) if r["depth_rank"] <= 3]
        rated.sort(key=lambda r: -r["points_if_out"])
        everything.extend(rated)
        print(f"\n=== {label} ===")
        print(f"  {'pts':<6} {'tier':<5} {'pos':<5} {'rk':<3} {'snap%':<7} {'avail':<7} player")
        for r in rated[:12]:
            print(f"  {r['points_if_out']:<6.2f} {r['tier']:<5} {r['position']:<5} {r['depth_rank']:<3} "
                  f"{r['role_snap_pct']:<7.0%} {str(r['availability'] or '-'):<7} {r['player']}")
        stars = [r['player'] for r in rated if r['tier'] == 3]
        print(f"  tier 3 ({len(stars)}): {', '.join(stars) or 'none'}")

    d = Path("data/player_importance"); d.mkdir(parents=True, exist_ok=True)
    p = d / f"nfl_v2_{datetime.now(timezone.utc).date().isoformat()}.json"
    p.write_text(json.dumps(everything, indent=2), encoding="utf-8")
    print(f"\nwrote {len(everything)} players -> {p}")
