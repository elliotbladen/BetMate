"""Prepare auditable 2026 QB candidates and Week 1 continuity from nflverse."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .step8_live_tiers import ROOT, TEMPLATE


ROSTER_2025 = ROOT / "data/nfl/rosters/roster_weekly_2025.parquet"
ROSTER_2026 = ROOT / "data/nfl/rosters/roster_weekly_2026.parquet"
DEPTH_2026 = ROOT / "data/nfl/live_tiers/depth_charts_2026.parquet"
PROFILES = ROOT / "data/nfl/live_tiers/qb_profiles_through_2025.csv"
CANDIDATES = ROOT / "data/nfl/live_tiers/2026_week01_qb_candidates.csv"
CONTINUITY = ROOT / "data/nfl/live_tiers/2026_week01_continuity_precut_diagnostic.json"
SOURCE_MANIFEST = ROOT / "ml/nfl/reports/step8_live_source_manifest.json"
SOURCE_URLS = {
    "roster": "https://github.com/nflverse/nflverse-data/releases/download/weekly_rosters/roster_weekly_2026.parquet",
    "depth_chart": "https://github.com/nflverse/nflverse-data/releases/download/depth_charts/depth_charts_2026.parquet",
    "injuries": "https://github.com/nflverse/nflverse-data/releases/download/injuries/injuries_2026.parquet",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _unit(position: str) -> str:
    if position == "OL":
        return "ol"
    if position in {"WR", "TE"}:
        return "receiver"
    return "other"


def _active_sets(frame: pd.DataFrame) -> tuple[dict[str, set[str]], dict[tuple[str, str], set[str]]]:
    active = frame[frame.status.isin(["ACT", "INA"]) & frame.gsis_id.notna()].copy()
    active["unit"] = active.position.map(_unit)
    teams = {team: set(group.gsis_id.astype(str)) for team, group in active.groupby("team")}
    units = {(team, unit): set(group.gsis_id.astype(str)) for (team, unit), group in active.groupby(["team", "unit"])}
    return teams, units


def prepare() -> dict:
    for path in (ROSTER_2025, ROSTER_2026, DEPTH_2026, PROFILES, TEMPLATE):
        if not path.exists():
            raise RuntimeError(f"required live source is missing: {path}")
    if any(path.exists() for path in (CANDIDATES, CONTINUITY, SOURCE_MANIFEST)):
        raise RuntimeError("refusing to overwrite prepared Step 8 live-source artefacts")
    observed_at = datetime.now(timezone.utc)
    template = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    teams = {game[side + "_team"] for game in template["games"] for side in ("home", "away")}

    depth = pd.read_parquet(DEPTH_2026)
    qb = depth[depth.pos_abb.eq("QB")].copy()
    latest_stamp = str(qb.dt.max())
    qb = qb[qb.dt.eq(latest_stamp)].sort_values(["team", "pos_rank", "pos_slot"])
    qb = qb[qb.team.isin(teams) & qb.pos_rank.isin([1, 2])]
    profiles = set(pd.read_csv(PROFILES, dtype={"player_id": str}).player_id)
    candidate_rows = []
    for game in template["games"]:
        for side in ("home", "away"):
            team = game[f"{side}_team"]
            rows = qb[qb.team.eq(team)].sort_values("pos_rank")
            candidate_rows.append({
                "game_id": game["game_id"], "side": side, "team": team,
                "depth_chart_as_of_utc": latest_stamp,
                "qb1_name": rows.iloc[0].player_name if len(rows) >= 1 else "",
                "qb1_id": rows.iloc[0].gsis_id if len(rows) >= 1 else "",
                "qb1_profile_available": bool(len(rows) >= 1 and rows.iloc[0].gsis_id in profiles),
                "qb2_name": rows.iloc[1].player_name if len(rows) >= 2 else "",
                "qb2_id": rows.iloc[1].gsis_id if len(rows) >= 2 else "",
                "qb2_profile_available": bool(len(rows) >= 2 and rows.iloc[1].gsis_id in profiles),
                "starter_probability": "", "review_status": "requires_injury_and_starter_review",
            })
    CANDIDATES.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(candidate_rows).to_csv(CANDIDATES, index=False)

    prior = pd.read_parquet(ROSTER_2025)
    final_week = prior[prior.game_type.eq("REG")].week.max()
    prior = prior[prior.week.eq(final_week)]
    current = pd.read_parquet(ROSTER_2026)
    current = current[current.week.eq(current.week.max())]
    current_active_count = int(current.status.isin(["ACT", "INA"]).sum())
    average_active_roster = current_active_count / len(teams)
    continuity_qualifies = average_active_roster <= 60.0
    prior_teams, prior_units = _active_sets(prior)
    current_teams, current_units = _active_sets(current)
    continuity_by_team = {}
    for team in teams:
        now, old = current_teams.get(team, set()), prior_teams.get(team, set())
        def share(unit: str | None = None) -> float | None:
            current_set = now if unit is None else current_units.get((team, unit), set())
            prior_set = old if unit is None else prior_units.get((team, unit), set())
            return len(current_set & prior_set) / len(current_set) if current_set else None
        continuity_by_team[team] = {
            "weekly_roster_continuity": 0.0,
            "returning_roster_share": share(), "returning_ol_share": share("ol"),
            "returning_receiver_share": share("receiver"),
            "week_one_weekly_continuity_encoding": "not_applicable_encoded_zero_as_in_training",
        }
    for game in template["games"]:
        game["as_of_utc"] = observed_at.isoformat()
        game["source_timestamps"]["roster"] = observed_at.isoformat()
        game["home"]["continuity"] = continuity_by_team[game["home_team"]]
        game["away"]["continuity"] = continuity_by_team[game["away_team"]]
        game["continuity_qualifies"] = continuity_qualifies
        game["status"] = (
            "continuity_resolved_qb_and_injuries_pending" if continuity_qualifies
            else "precut_continuity_diagnostic_do_not_score"
        )
    template["continuity_source"] = SOURCE_URLS["roster"]
    template["continuity_observed_at_utc"] = observed_at.isoformat()
    CONTINUITY.write_text(json.dumps(template, indent=2) + "\n", encoding="utf-8")

    manifest = {
        "status": "depth_available_roster_precut_injuries_not_yet_published",
        "observed_at_utc": observed_at.isoformat(), "depth_chart_as_of_utc": latest_stamp,
        "sources": SOURCE_URLS,
        "sha256": {"roster_2026": _sha256(ROSTER_2026), "depth_charts_2026": _sha256(DEPTH_2026),
                   "qb_candidates": _sha256(CANDIDATES), "continuity_snapshot": _sha256(CONTINUITY)},
        "games": len(template["games"]), "teams": len(teams), "injury_rows": 0,
        "average_active_roster": average_active_roster,
        "continuity_qualifies": continuity_qualifies,
        "continuity_reason": (
            "comparable_post_cut_roster" if continuity_qualifies
            else "precut_roster_exceeds_60_active_players_per_team"
        ),
        "staking_enabled": False,
    }
    SOURCE_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    SOURCE_MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("prepare",))
    parser.parse_args()
    print(json.dumps(prepare(), indent=2))


if __name__ == "__main__":
    main()
