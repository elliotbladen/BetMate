#!/usr/bin/env python3
"""Pooled with-or-without-you across three seasons, for Liverpool, Chelsea, Real Madrid.

THE QUESTION, as the owner put it: find the team's record when a player plays, and
its record when he does not. That is INFLUENCE, and it is the only measure that sees
a Van Dijk or a Rodri - players whose own output is near zero but whose absence has
repeatedly collapsed a title-winning side. Strikers are already handled by output;
this exists for midfielders and defenders.

WHY POOLED ACROSS SEASONS. A single season cannot answer it. Van Dijk tore his ACL in
October 2020 so he has barely any "with" games that year; Rodri's 2024/25 gives only
five. Pooling three seasons accumulates enough absences for the sample to mean
something.

⚠️ RAW WOWY IS USELESS AND MUST BE GUARDED. Run raw on one season it reported
   Benjamin Woodburn (+1.29) and Issa Kaboré (+1.16) as the most influential players
   at Liverpool and City. They appeared in one to three games, their side happened to
   win, so their "with" record was a perfect 3.00. Substitutes also come on when a
   team is ALREADY winning, which biases them upward a second time. Hence:

     * a minimum of MIN_GAMES_WITHOUT absences before a figure is reported at all
     * a minimum of MIN_GAMES_WITH appearances, so a one-game cameo cannot rate
     * shrinkage toward zero by sample size, the same treatment that fixed the
       quarterback backup problem

⚠️ STILL CONFOUNDED BY FIXTURE DIFFICULTY. Opponent strength is not adjusted for. A
   player who missed a run of easy games looks worthless and one who missed a run of
   hard ones looks irreplaceable. Treat this as evidence, never proof.
"""
from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wowy import _get, BASE, season_matches            # noqa: E402

SEASONS = ("2023/2024", "2024/2025", "2025/2026")
CLUBS = [
    (8650, "Liverpool", 47),
    (8455, "Chelsea", 47),
    (8633, "Real Madrid", 87),      # LaLiga
]

MIN_GAMES_WITHOUT = 8      # below this the "without" average is noise
MIN_GAMES_WITH = 15
SHRINK_PRIOR = 10          # pseudo-games pulling the delta toward zero


def position_groups(team_id: int) -> dict[str, str]:
    payload = _get(f"{BASE}/teams?id={team_id}")
    out = {}
    for group in (payload.get("squad") or {}).get("squad") or []:
        if group.get("title") == "coach":
            continue
        for member in group.get("members", []):
            out[str(member.get("id"))] = group.get("title")
    return out


def collect(team_id: int, league_id: int, season: str):
    """One season: who played each match, and what the result was."""
    played: dict[str, set] = defaultdict(set)
    results: dict[str, tuple[int, int]] = {}
    names: dict[str, str] = {}

    for m in season_matches(league_id, season, team_id):
        mid = str(m["id"])
        try:
            details = _get(f"{BASE}/matchDetails?matchId={mid}")
        except Exception:
            continue
        lineup = (details.get("content") or {}).get("lineup") or {}
        side = "homeTeam" if str((m.get("home") or {}).get("id")) == str(team_id) else "awayTeam"
        team = lineup.get(side) or {}
        starters = team.get("starters") or []
        if not starters:
            continue                      # no lineup archived; skip rather than guess
        for player in starters:
            pid = str(player.get("id"))
            played[pid].add(mid)
            names[pid] = player.get("name") or ""

        score = ((m.get("status") or {}).get("scoreStr") or "").split("-")
        if len(score) != 2:
            continue
        try:
            hs, aws = int(score[0].strip()), int(score[1].strip())
        except ValueError:
            continue
        gf, ga = (hs, aws) if side == "homeTeam" else (aws, hs)
        results[mid] = (3 if gf > ga else 1 if gf == ga else 0, gf - ga)
    return played, results, names


if __name__ == "__main__":
    everything = []
    for team_id, team_name, league_id in CLUBS:
        print(f"\n=== {team_name} — {', '.join(SEASONS)} ===", flush=True)
        groups = position_groups(team_id)
        all_played: dict[str, set] = defaultdict(set)
        all_results: dict[str, tuple[int, int]] = {}
        all_names: dict[str, str] = {}
        for season in SEASONS:
            played, results, names = collect(team_id, league_id, season)
            print(f"  {season}: {len(results)} matches with archived lineups", flush=True)
            for pid, mids in played.items():
                all_played[pid] |= mids
            all_results.update(results)
            all_names.update(names)

        rows = []
        for pid, mids in all_played.items():
            on = [all_results[i] for i in all_results if i in mids]
            off = [all_results[i] for i in all_results if i not in mids]
            if len(on) < MIN_GAMES_WITH or len(off) < MIN_GAMES_WITHOUT:
                continue
            ppg_on = sum(p for p, _ in on) / len(on)
            ppg_off = sum(p for p, _ in off) / len(off)
            gd_on = sum(g for _, g in on) / len(on)
            gd_off = sum(g for _, g in off) / len(off)
            raw = ppg_on - ppg_off
            # Shrink by how many absences the estimate rests on. Eight missed games
            # is a thin base for a claim about a footballer's influence.
            shrunk = raw * (len(off) / (len(off) + SHRINK_PRIOR))
            rows.append({
                "team": team_name, "player": all_names.get(pid, pid), "player_id": pid,
                "position_group": groups.get(pid, "left the club"),
                "games_with": len(on), "games_without": len(off),
                "ppg_with": round(ppg_on, 2), "ppg_without": round(ppg_off, 2),
                "ppg_delta_raw": round(raw, 2), "ppg_delta_shrunk": round(shrunk, 2),
                "gd_with": round(gd_on, 2), "gd_without": round(gd_off, 2),
                "gd_delta": round(gd_on - gd_off, 2),
                "seasons": list(SEASONS),
                "rated_on": datetime.now(timezone.utc).date().isoformat(),
            })
        rows.sort(key=lambda r: -r["ppg_delta_shrunk"])
        everything.extend(rows)

        print(f"\n  {'player':<24} {'pos':<12} {'with':<13} {'without':<13} {'raw':<7} shrunk")
        for r in rows[:14]:
            print(f"  {r['player']:<24} {r['position_group'][:11]:<12} "
                  f"{r['ppg_with']:.2f} ({r['games_with']:>3})  "
                  f"{r['ppg_without']:.2f} ({r['games_without']:>3})  "
                  f"{r['ppg_delta_raw']:>+6.2f}  {r['ppg_delta_shrunk']:>+6.2f}")

    d = Path("data/player_importance"); d.mkdir(parents=True, exist_ok=True)
    p = d / f"wowy_3season_{datetime.now(timezone.utc).date().isoformat()}.json"
    p.write_text(json.dumps(everything, indent=2), encoding="utf-8")
    print(f"\nwrote {len(everything)} qualifying players -> {p}")
