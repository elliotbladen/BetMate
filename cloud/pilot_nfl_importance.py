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

# ── Positional value ─────────────────────────────────────────────────────────
# Snap share alone says WHO IS ON THE FIELD, not who matters. An offensive guard
# plays ~100% of snaps by definition, which is why the first version rated Dominick
# Puni above Christian McCaffrey and produced ELEVEN stars per team.
#
# NFL positional value is one of the better-established findings in the sport's
# analytics: quarterback dwarfs everything, then premium pass rusher / left tackle /
# WR1 / CB1, then the rest, with running back and off-ball linebacker long known to
# be devalued relative to how they are talked about. These weights encode that
# ordering. They are deliberately visible and tunable rather than buried in a score.
POSITION_VALUE = {
    "QB": 5.0,
    "DE": 1.8, "EDGE": 1.8, "OLB": 1.5,
    "LT": 1.6, "T": 1.5, "OT": 1.5,
    "WR": 1.5,
    "CB": 1.4, "DB": 1.3,
    "DT": 1.2, "DL": 1.2, "NT": 1.0,
    "TE": 1.0, "S": 1.0, "FS": 1.0, "SS": 1.0,
    "LB": 0.9, "ILB": 0.85, "MLB": 0.85,
    "C": 0.85, "G": 0.8, "OL": 0.8, "OG": 0.8,
    "RB": 0.8, "FB": 0.4,
    "K": 0.3, "P": 0.3, "LS": 0.2,
}
DEFAULT_POSITION_VALUE = 0.8

# A backup quarterback's value is contingent on the starter's absence - a different
# quantity from the starter's own importance, and not a star's.
BACKUP_QB_VALUE = 0.8

# A specialist playing 80% of special-teams snaps is not a star. Measuring each
# player inside his own unit was right for offence vs defence and badly wrong here -
# it promoted Luke Gifford, a special-teamer, to tier 3.
SPECIAL_TEAMS_FACTOR = 0.3

# The owner's constraint: at most 2-3 stars per team, or the tier means nothing for
# a market study. Scarcity is the whole point of the rating.
MAX_STARS_PER_TEAM = 3
STAR_SCORE_FLOOR = 0.55      # a bad team does not get 3 stars by default
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

    # The starting quarterback is the one taking most offensive snaps - NOT every QB
    # over a threshold. Identify him BEFORE scoring, because the 5.0 quarterback
    # premium belongs to the job, not to the position group: a backup's value is
    # contingent on the starter being absent, which is a different quantity
    # entirely. Scoring both alike put Mac Jones - a backup covering an injury - in
    # a star slot alongside the man he was covering for.
    qbs = [r for r in out if r["position"] == "QB"]
    starter_qb = max(qbs, key=lambda r: r["snap_share"]) if qbs else None

    # ── Score = availability x positional value ──────────────────────────────
    for r in out:
        pos_value = POSITION_VALUE.get(r["position"], DEFAULT_POSITION_VALUE)
        if r["position"] == "QB" and r is not starter_qb:
            pos_value = BACKUP_QB_VALUE
        unit_factor = SPECIAL_TEAMS_FACTOR if r["unit"] == "special_teams" else 1.0
        r["position_value"] = pos_value
        r["score"] = round(r["snap_share"] * pos_value * unit_factor, 3)

    # ── Tier by RANK, not by threshold ───────────────────────────────────────
    # The owner's constraint is scarcity: 2-3 stars per team. A fixed cut-off cannot
    # deliver that - it gave 11 - because it has no idea how many players cleared it.
    # Ranking does, and it removes cliff edges: nobody drops a tier for being one
    # percentage point short, which is how Alisson was demoted in the football pilot.
    ranked = sorted(out, key=lambda r: -r["score"])
    stars: list[dict] = []
    if starter_qb and starter_qb["score"] >= STAR_SCORE_FLOOR:
        stars.append(starter_qb)                 # QB first: he is the position
    for r in ranked:
        if len(stars) >= MAX_STARS_PER_TEAM:
            break
        if r is starter_qb or r["score"] < STAR_SCORE_FLOOR:
            continue
        stars.append(r)
    star_ids = {id(r) for r in stars}

    for r in out:
        if id(r) in star_ids:
            r["tier"] = 3
            r["basis"] = (f"starting QB, score {r['score']}" if r is starter_qb
                          else f"top-{MAX_STARS_PER_TEAM} score {r['score']} "
                               f"({r['snap_share']:.0%} snaps x {r['position']} value {r['position_value']})")
        elif r["snap_share"] >= REGULAR_SNAP_SHARE and r["unit"] != "special_teams":
            r["tier"] = 2
            r["basis"] = f"regular, {r['snap_share']:.0%} of {r['unit']} snaps, score {r['score']}"
        elif r["position"] == "QB" and r["snap_share"] >= 0.15:
            r["tier"] = 2
            r["basis"] = "backup quarterback - matters only if the starter goes down"
        else:
            r["tier"] = 1
            r["basis"] = f"fringe/specialist, score {r['score']}"
        r["tier_label"] = {1: "not important", 2: "important", 3: "star"}[r["tier"]]
    return out


if __name__ == "__main__":
    everything: list[dict] = []
    for team, name in (("SF", "San Francisco 49ers"), ("JAX", "Jacksonville Jaguars")):
        print(f"\n=== {name} ===", flush=True)
        rated = rate_team(team)
        rated.sort(key=lambda r: (-r["tier"], -r["score"]))
        everything.extend(rated)
        print(f"  {'tier':<5} {'score':<7} {'share':<7} {'pos':<5} {'unit':<14} {'gms':<7} player")
        for r in rated[:14]:
            print(f"  {r['tier']:<5} {r['score']:<7.2f} {r['snap_share']:<7.0%} {r['position']:<5} "
                  f"{r['unit']:<14} {r['games_played']}/{r['team_games']:<4} {r['player']}")
        print(f"  ... {len(rated)} players total")
    d = Path("data/player_importance"); d.mkdir(parents=True, exist_ok=True)
    path = d / f"pilot_nfl_{datetime.now(timezone.utc).date().isoformat()}.json"
    path.write_text(json.dumps(everything, indent=2), encoding="utf-8")
    print(f"\nwrote {len(everything)} players -> {path}")
