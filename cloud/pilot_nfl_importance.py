#!/usr/bin/env python3
"""PILOT: rate NFL players 1/2/3 from snap share, the direct analogue of minutes share.

SOURCE: nflverse (github.com/nflverse/nflverse-data), free, public, plain CSV on
GitHub releases - so no bot-blocking, unlike ESPN (403 on every endpoint),
pro-football-reference (403) and nfl.com depth charts (404).

It gives three things this needs, all multi-season:
    snap_counts   offense_snaps / offense_pct / defense_pct / st_pct, PER GAME
    depth_charts  pos_rank - starter vs backup, stated rather than inferred
    injuries      report_status + practice_status, the mandated report, structured

⚠️ WHY NOT CAP HIT. It carries the same age distortion that disqualified transfer
   value for football, plus a worse one: stars on rookie contracts have tiny cap
   hits, so a breakout young quarterback would rate as unimportant. Snap share is
   immune to both - it measures what the coaching staff actually does.

⚠️ SNAP SHARE MUST BE READ PER UNIT. An offensive lineman plays ~100% of offensive
   snaps; a star cornerback plays ~100% of DEFENSIVE snaps; a returner plays almost
   none of either but most special-teams snaps. Comparing a corner's offense_pct to
   a guard's would rate every defender as irrelevant, so each player is measured
   against his own unit.

⚠️ QUARTERBACK IS A SPECIAL CASE and it is not a fudge. It is the one position in
   any code where the backup moves a line by points on his own, and the market
   prices it that way. A starting QB is tier 3 by position.
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

STAR_SNAP_SHARE = 0.75
REGULAR_SNAP_SHARE = 0.35


def fetch_csv(url: str) -> list[dict]:
    with urlopen(Request(url, headers={"User-Agent": UA}), timeout=90) as r:
        return list(csv.DictReader(io.StringIO(r.read().decode("utf-8", "ignore"))))


def _f(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def rate_team(team: str, seasons=(2025, 2026)) -> list[dict]:
    """Snap share across seasons, measured within each player's own unit."""
    rated_on = datetime.now(timezone.utc).date().isoformat()
    rows: list[dict] = []
    for season in seasons:
        try:
            rows.extend(r for r in fetch_csv(f"{BASE}/snap_counts/snap_counts_{season}.csv")
                        if r.get("team") == team and r.get("game_type") == "REG")
        except Exception as exc:
            print(f"  snap_counts {season}: {exc}")

    games = {(r["season"], r["week"]) for r in rows}
    by_player: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        by_player[(r["player"], r["position"])].append(r)

    out = []
    for (player, position), appearances in by_player.items():
        # Which unit is this player's? Whichever he takes most of his snaps on.
        off = sum(_f(a["offense_snaps"]) for a in appearances)
        dfn = sum(_f(a["defense_snaps"]) for a in appearances)
        spt = sum(_f(a["st_snaps"]) for a in appearances)
        unit = "offense" if off >= max(dfn, spt) else ("defense" if dfn >= spt else "special_teams")
        pct_field = {"offense": "offense_pct", "defense": "defense_pct",
                     "special_teams": "st_pct"}[unit]

        # Share of the team's games, times his share of snaps when he did play.
        # Both halves matter: a player who is elite but injured half the year is
        # less relied upon over the window than one who starts every week.
        played = len(appearances)
        mean_pct = sum(_f(a[pct_field]) for a in appearances) / played if played else 0.0
        share = (played / len(games)) * mean_pct if games else 0.0

        out.append({
            "code": "NFL", "team": team, "player": player, "position": position,
            "unit": unit, "games_played": played, "team_games": len(games),
            "mean_snap_pct": round(mean_pct, 3), "snap_share": round(share, 3),
            "rated_on": rated_on,
        })

    for r in out:
        share, position = r["snap_share"], r["position"]
        if position == "QB" and r["mean_snap_pct"] >= 0.5:
            r["tier"] = 3
            r["basis"] = f"starting quarterback ({r['mean_snap_pct']:.0%} of snaps when active)"
        elif share >= STAR_SNAP_SHARE:
            r["tier"] = 3
            r["basis"] = f"plays {share:.0%} of available {r['unit']} snaps"
        elif share >= REGULAR_SNAP_SHARE:
            r["tier"] = 2
            r["basis"] = f"rotation, {share:.0%} of available {r['unit']} snaps"
        else:
            r["tier"] = 1
            r["basis"] = f"fringe, {share:.0%} of available {r['unit']} snaps"
        r["tier_label"] = {1: "not important", 2: "important", 3: "star"}[r["tier"]]
    return out


if __name__ == "__main__":
    everything: list[dict] = []
    for team, name in (("SF", "San Francisco 49ers"), ("JAX", "Jacksonville Jaguars")):
        print(f"\n=== {name} ===", flush=True)
        rated = rate_team(team)
        rated.sort(key=lambda r: (-r["tier"], -r["snap_share"]))
        everything.extend(rated)
        print(f"  {'tier':<5} {'share':<7} {'pos':<5} {'unit':<14} {'gms':<7} player")
        for r in rated[:14]:
            print(f"  {r['tier']:<5} {r['snap_share']:<7.0%} {r['position']:<5} {r['unit']:<14} "
                  f"{r['games_played']}/{r['team_games']:<4} {r['player']}")
        print(f"  ... {len(rated)} players total")
    d = Path("data/player_importance"); d.mkdir(parents=True, exist_ok=True)
    path = d / f"pilot_nfl_{datetime.now(timezone.utc).date().isoformat()}.json"
    path.write_text(json.dumps(everything, indent=2), encoding="utf-8")
    print(f"\nwrote {len(everything)} players -> {path}")
