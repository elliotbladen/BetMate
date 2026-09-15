#!/usr/bin/env python3
"""NFL player importance — expected points of spread movement if the player is OUT.

Tiers, set by the owner 2026-09-13:
    >= 3.0 pts  -> 3  star
    0.2 - 3.0   -> 2  important
    < 0.2       -> 1  not important

WHY POINTS AND NOT A QUOTA. Published oddsmaker figures put a starting quarterback
at 3-7 points and essentially everyone else at 0-1.5, so there is nothing at all
between the QB and the next man on any roster - measured here as a void between
5.00 and 1.17. A fixed "3 stars per team" imposes a shape the sport does not have.
The points column is the useful output; tiers are derived from it.

⚠️ THE QUARTERBACK NUMBER IS THE WHOLE MODEL. He is worth ~4x the next most
   important player, so his figure matters more than every other position combined.
   It is NOT a flat 5.0 per starter - that would make all 32 starters 3-star and
   lose the "only a VERY good quarterback" distinction the owner asked for.

   The quantity that moves a line is the GAP between the starter and whoever
   replaces him: "depending on the quality gap between the starter and backup, a
   quarterback change can move the spread by 3 to 7 points... when a team with a
   competent backup loses their starter, the shift is smaller, typically 2 to 4."

   So: points = value(starter QBR) - value(backup QBR), floored and capped.

⚠️ QBR MUST BE VOLUME-FILTERED. The raw ESPN file rates any player who threw a
   pass: Ty Johnson (a running back), DJ Moore and Breece Hall all show QBR 100 off
   trick plays. Without a qb_plays floor they would outrank every real starter.

⚠️ ROLE AND AVAILABILITY ARE SEPARATE. An earlier version multiplied role by games
   played, which rated Nick Bosa (4 of 18 games, injured) and Fred Warner (7 of 18)
   as unimportant - a model for pricing injuries penalising players for being
   injured. Importance is a property of the role when fit; durability is reported
   beside it and never multiplied in.

⚠️ POSITIONS COME FROM DEPTH CHARTS, not snap counts. nflverse types Bosa as "DL",
   which scored him as an interior lineman - the best pass rusher in football priced
   as a nose tackle. depth_charts.pos_abb gives RDE / LDE / LT / RCB / MLB, and
   pos_rank gives starter status independently of current injury.
"""
from __future__ import annotations

import csv
import io
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

BASE = "https://github.com/nflverse/nflverse-data/releases/download"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Safari/537.36"

TIER_3_POINTS = 3.0
TIER_2_POINTS = 0.2

# Points of spread lost if the FIRST-CHOICE player here is ruled out.
POINTS_IF_OUT = {
    "RDE": 1.2, "LDE": 1.2, "DE": 1.2, "OLB": 0.9,
    "LT": 1.1, "RT": 0.6, "LG": 0.45, "RG": 0.45, "C": 0.5,
    "RCB": 0.9, "LCB": 0.9, "CB": 0.9, "NB": 0.5,
    "WR": 0.8, "SWR": 0.5, "TE": 0.5,
    "DT": 0.5, "NT": 0.4,
    "FS": 0.35, "SS": 0.35, "S": 0.35,
    "MLB": 0.35, "WLB": 0.35, "SLB": 0.3, "LB": 0.35,
    "RB": 0.3, "FB": 0.1,
    "K": 0.25, "P": 0.15, "LS": 0.05, "KR": 0.1, "PR": 0.1,
}
DEFAULT_POINTS = 0.3
RANK_FACTOR = {1: 1.0, 2: 0.25, 3: 0.08}
DEFAULT_RANK_FACTOR = 0.04

MIN_QB_PLAYS = 60           # excludes trick-play "quarterbacks"
# Empirical-Bayes shrinkage toward replacement level, by sample size. Tyler Huntley
# posted QBR 80.8 off 103 plays - better than every genuine starter in the league -
# which collapsed Baltimore's quarterback swing to the floor, because his backup
# looked elite. A 103-play QBR is not a 671-play QBR and must not be read as one.
# Same treatment the referee cards matrix uses for thin samples.
QBR_PRIOR_PLAYS = 90
REPLACEMENT_QBR = 40.0      # an unproven backup is assumed replacement level
PROVEN_BACKUP_PLAYS = 400   # a real starter's workload, not relief appearances
QB_SWING_CAP = 7.0


def fetch_csv(url: str) -> list[dict]:
    with urlopen(Request(url, headers={"User-Agent": UA}), timeout=120) as r:
        return list(csv.DictReader(io.StringIO(r.read().decode("utf-8", "ignore"))))


def _f(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def qb_points(starter_qbr: float, backup_qbr: float | None, backup_plays: float) -> float:
    """Points of spread lost if THIS starting quarterback is ruled out.

    ⚠️ DO NOT compute this as starter-minus-backup. It is the theoretically right
       quantity and it is not computable from available data: relief-appearance QBR
       does not predict starting performance. Tyler Huntley shrank to 60.1 off 157
       relief snaps against Lamar Jackson's 65.1 off 1,760 - so subtracting the
       backup erased an MVP, and Baltimore came out at the 1.5 floor. Backups get
       favourable spots, small samples and garbage time; the number is biased up.

    So the starter is valued directly, against the published range of 3-7 points,
    which is what oddsmaker quarterback rankings do. QBR 50 (a weak starter) -> 3.0,
    QBR 75 (elite) -> 7.0.

    A backup discount applies ONLY where the backup is a proven starter in his own
    right - real volume, not relief work - and is capped at one point, because even
    a good replacement costs continuity and game plan.
    """
    points = 3.0 + (starter_qbr - 50.0) * (4.0 / 25.0)
    if backup_qbr is not None and backup_plays >= PROVEN_BACKUP_PLAYS:
        points -= min(1.0, max(0.0, (backup_qbr - 50.0) * (4.0 / 25.0)))
    return round(min(QB_SWING_CAP, max(2.0, points)), 2)


# Recency weights. A 2024 season still says something about a quarterback; a 2020
# one says almost nothing. Without a window this wide, Jayden Daniels, Kyler Murray,
# Kirk Cousins and Deshaun Watson all fell through to a default, because their last
# qualifying season predates 2025.
SEASON_WEIGHTS = {"2026": 1.0, "2025": 0.85, "2024": 0.5, "2023": 0.25}


def load_qbr() -> dict[tuple[str, str], float]:
    """(first initial, surname) -> recency-weighted, sample-shrunk QBR.

    Keyed on the PLAYER, not the team: keying by team lost every quarterback who
    changed club, and lost Stafford outright because the QBR file says "LAR" while
    the depth charts say "LA".

    ⚠️ Surname is the LAST WHITESPACE TOKEN, not a split on ".". Splitting on the dot
       turned "C.J. Stroud" into surname "j. stroud" and silently dropped every
       two-initial quarterback - Stroud among them - into the default bucket.
    """
    agg: dict[tuple[str, str], list[tuple[float, float]]] = {}
    for row in fetch_csv(f"{BASE}/espn_data/qbr_season_level.csv"):
        weight = SEASON_WEIGHTS.get(row.get("season", ""))
        if weight is None or row.get("season_type") != "Regular":
            continue
        plays = _f(row.get("qb_plays"))
        if plays < MIN_QB_PLAYS:
            continue
        name = (row.get("name_short") or "").strip()
        if " " not in name:
            continue
        parts = name.split()
        key = (parts[0][:1].lower(), parts[-1].lower())
        agg.setdefault(key, []).append((_f(row.get("qbr_total")), plays * weight))

    out: dict[tuple[str, str], float] = {}
    for key, samples in agg.items():
        total = sum(w for _, w in samples)
        mean = sum(q * w for q, w in samples) / total if total else REPLACEMENT_QBR
        # Shrink toward replacement by sample size. A 103-play QBR is not a 671-play
        # QBR: Tyler Huntley posted 80.8 off 103 plays, better than any real starter,
        # which collapsed Baltimore's swing to the floor because his backup looked
        # elite. The prior is deliberately light so a genuine full-season starter is
        # barely moved - an earlier prior of 300 dragged Josh Allen below star level.
        out[key] = ((mean * total + REPLACEMENT_QBR * QBR_PRIOR_PLAYS) / (total + QBR_PRIOR_PLAYS),
                    sum(w for _, w in samples))
    return out


def rate_team(team: str, depth: list[dict], snaps: list[dict],
              qbr: dict[tuple[str, str], float]) -> list[dict]:
    rated_on = datetime.now(timezone.utc).date().isoformat()

    latest: dict[str, dict] = {}
    for row in depth:
        if row.get("team") != team or not row.get("player_name"):
            continue
        name = row["player_name"]
        if name not in latest or (row.get("dt") or "") > (latest[name].get("dt") or ""):
            latest[name] = row

    by_player: dict[str, list[dict]] = defaultdict(list)
    for row in snaps:
        if row.get("team") == team and row.get("game_type") == "REG":
            by_player[row["player"]].append(row)
    team_games = len({(r["season"], r["week"]) for r in snaps
                      if r.get("team") == team and r.get("game_type") == "REG"})

    def qbr_for(player_name: str):
        parts = player_name.split()
        if len(parts) < 2:
            return None, 0.0
        return qbr.get((parts[0][:1].lower(), parts[-1].lower()), (None, 0.0))

    qbs = sorted((r for r in latest.values() if (r.get("pos_abb") or "").upper() == "QB"),
                 key=lambda r: _f(r.get("pos_rank") or 99))
    starter = qbs[0] if qbs else None
    backup = qbs[1] if len(qbs) > 1 else None
    starter_qbr, _ = qbr_for(starter["player_name"]) if starter else (None, 0.0)
    backup_qbr, backup_plays = qbr_for(backup["player_name"]) if backup else (None, 0.0)

    if starter_qbr is not None:
        qb_pts = qb_points(starter_qbr, backup_qbr, backup_plays)
        qb_note = f"QBR {starter_qbr:.1f}"
        if backup_qbr is not None and backup_plays >= PROVEN_BACKUP_PLAYS:
            qb_note += f", proven backup QBR {backup_qbr:.1f}"
    else:
        qb_pts, qb_note = 3.0, "no qualifying QBR; weak-starter value assumed"

    out = []
    for name, row in latest.items():
        pos = (row.get("pos_abb") or "").upper()
        try:
            rank = int(row.get("pos_rank") or 99)
        except ValueError:
            rank = 99

        apps = by_player.get(name, [])
        played = len(apps)
        if apps:
            off = sum(_f(a["offense_snaps"]) for a in apps)
            dfn = sum(_f(a["defense_snaps"]) for a in apps)
            field = "offense_pct" if off >= dfn else "defense_pct"
            role = sum(_f(a[field]) for a in apps) / played
        else:
            role = 0.0

        if pos == "QB" and rank == 1:
            points, basis = qb_pts, f"starting quarterback, {qb_note}"
        elif pos == "QB":
            # A backup's OWN absence costs almost nothing: the third-stringer plays
            # only if the starter is gone too. Priced as the insurance it is.
            points, basis = 0.2, "backup quarterback - matters only if the starter is out"
        else:
            base = POINTS_IF_OUT.get(pos, DEFAULT_POINTS)
            factor = RANK_FACTOR.get(rank, DEFAULT_RANK_FACTOR)
            modulation = 0.7 + 0.3 * min(role / 0.85, 1.0) if role else 0.7
            points = round(base * factor * modulation, 2)
            basis = f"{pos} depth-rank {rank}, {role:.0%} of snaps when fit"

        tier = 3 if points >= TIER_3_POINTS else (2 if points >= TIER_2_POINTS else 1)
        out.append({
            "code": "NFL", "team": team, "player": name, "position": pos,
            "depth_rank": rank, "role_snap_pct": round(role, 3),
            "games_played": played, "team_games": team_games,
            "availability": round(played / team_games, 3) if team_games else None,
            "points_if_out": points, "tier": tier,
            "tier_label": {1: "not important", 2: "important", 3: "star"}[tier],
            "basis": basis, "rated_on": rated_on, "source": "nflverse",
        })
    return out


TEAMS = ["ARI","ATL","BAL","BUF","CAR","CHI","CIN","CLE","DAL","DEN","DET","GB","HOU",
         "IND","JAX","KC","LA","LAC","LV","MIA","MIN","NE","NO","NYG","NYJ","PHI","PIT",
         "SEA","SF","TB","TEN","WAS"]

if __name__ == "__main__":
    print("loading nflverse depth charts, snap counts and QBR ...", flush=True)
    depth = fetch_csv(f"{BASE}/depth_charts/depth_charts_2026.csv")
    snaps: list[dict] = []
    for season in (2025, 2026):
        snaps += fetch_csv(f"{BASE}/snap_counts/snap_counts_{season}.csv")
    qbr = load_qbr()
    print(f"  depth {len(depth):,} rows | snaps {len(snaps):,} | QBR {len(qbr)} qualifying\n", flush=True)

    everything: list[dict] = []
    print(f"  {'team':<5} {'stars':<6} {'QB':<22} {'pts':<6} other 3-star")
    for team in TEAMS:
        rated = rate_team(team, depth, snaps, qbr)
        everything.extend(rated)
        stars = sorted((r for r in rated if r["tier"] == 3), key=lambda r: -r["points_if_out"])
        qb = next((r for r in rated if r["position"] == "QB" and r["depth_rank"] == 1), None)
        others = ", ".join(f"{r['player']} ({r['position']} {r['points_if_out']})"
                           for r in stars if r is not qb) or "-"
        print(f"  {team:<5} {len(stars):<6} {(qb['player'] if qb else '-'):<22} "
              f"{(qb['points_if_out'] if qb else 0):<6.2f} {others}", flush=True)

    d = Path("data/player_importance"); d.mkdir(parents=True, exist_ok=True)
    path = d / f"nfl_importance_{datetime.now(timezone.utc).date().isoformat()}.json"
    path.write_text(json.dumps(everything, indent=2), encoding="utf-8")
    from collections import Counter
    c = Counter(r["tier"] for r in everything)
    print(f"\n{len(everything)} players -> {path}")
    print(f"  tier 3 (star): {c[3]}   tier 2 (important): {c[2]}   tier 1: {c[1]}")
