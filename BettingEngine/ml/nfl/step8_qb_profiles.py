"""Build prior-only QB profiles and apply reviewed live starter probabilities."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .personnel import QB_PRIOR_DROPBACKS, load_qb_game_stats
from .step8_live_tiers import ROOT, TEMPLATE, _parse_aware


PBP = ROOT / "data/nfl/pbp"
ROSTERS = ROOT / "data/nfl/rosters"
PROFILES = ROOT / "data/nfl/live_tiers/qb_profiles_through_2025.csv"
REVIEW = ROOT / "data/nfl/live_tiers/2026_week01_qb_review.csv"
ENRICHED = ROOT / "data/nfl/live_tiers/2026_week01_qb_enriched.json"
REVIEW_FIELDS = [
    "game_id", "as_of_utc", "source", "source_published_at_utc",
    "home_starter_id", "home_backup_id", "home_starter_probability",
    "away_starter_id", "away_backup_id", "away_starter_probability", "reviewer_notes",
]


def build_profiles() -> dict:
    if PROFILES.exists():
        raise RuntimeError(f"refusing to overwrite QB profiles: {PROFILES}")
    games = load_qb_game_stats(str(PBP), range(2014, 2026))
    profiles = games.groupby("passer_player_id", as_index=False).agg(
        qb_prior_dropbacks=("dropbacks", "sum"), qb_epa_sum=("qb_epa_sum", "sum"),
        qb_successes=("qb_successes", "sum"), sacks=("sacks", "sum"),
        interceptions=("interceptions", "sum"), scrambles=("scrambles", "sum"),
        last_season=("season", "max"),
    )
    denominator = profiles.qb_prior_dropbacks + QB_PRIOR_DROPBACKS
    profiles["qb_epa_posterior"] = profiles.qb_epa_sum / denominator
    profiles["qb_success_posterior"] = profiles.qb_successes / denominator
    profiles["qb_sack_rate_posterior"] = profiles.sacks / denominator
    profiles["qb_turnover_rate_posterior"] = profiles.interceptions / denominator
    profiles["qb_scramble_rate_posterior"] = profiles.scrambles / denominator

    roster_files = sorted(ROSTERS.glob("roster_weekly_*.parquet"))
    roster = pd.concat([
        pd.read_parquet(path, columns=["season", "week", "team", "position", "gsis_id", "full_name"])
        for path in roster_files
    ], ignore_index=True)
    roster = roster[roster.position.eq("QB") & roster.gsis_id.notna()].sort_values(["season", "week"])
    latest = roster.drop_duplicates("gsis_id", keep="last")[["gsis_id", "full_name", "team"]]
    profiles = profiles.merge(latest, left_on="passer_player_id", right_on="gsis_id", how="left")
    profiles = profiles.rename(columns={"passer_player_id": "player_id", "team": "last_roster_team"})
    profiles = profiles[[
        "player_id", "full_name", "last_roster_team", "last_season", "qb_prior_dropbacks",
        "qb_epa_posterior", "qb_success_posterior", "qb_sack_rate_posterior",
        "qb_turnover_rate_posterior", "qb_scramble_rate_posterior",
    ]].sort_values(["last_season", "qb_prior_dropbacks"], ascending=[False, False])
    PROFILES.parent.mkdir(parents=True, exist_ok=True)
    profiles.to_csv(PROFILES, index=False)
    return {
        "status": "profiles_created", "players": len(profiles),
        "through_season": 2025, "named_players": int(profiles.full_name.notna().sum()),
        "path": str(PROFILES.relative_to(ROOT)),
    }


def prepare_review() -> dict:
    if REVIEW.exists():
        raise RuntimeError(f"refusing to overwrite QB review: {REVIEW}")
    template = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    REVIEW.parent.mkdir(parents=True, exist_ok=True)
    with REVIEW.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=REVIEW_FIELDS)
        writer.writeheader()
        for game in template["games"]:
            writer.writerow({"game_id": game["game_id"]})
    return {"status": "review_template_created", "games": len(template["games"]), "resolved_games": 0,
            "path": str(REVIEW.relative_to(ROOT))}


def _profile_lookup() -> dict[str, dict]:
    frame = pd.read_csv(PROFILES).fillna("")
    fields = [
        "qb_epa_posterior", "qb_success_posterior", "qb_sack_rate_posterior",
        "qb_turnover_rate_posterior", "qb_scramble_rate_posterior", "qb_prior_dropbacks",
    ]
    return {str(row.player_id): {field: float(getattr(row, field)) for field in fields}
            for row in frame.itertuples(index=False)}


def apply_review(review_path: Path) -> dict:
    if ENRICHED.exists():
        raise RuntimeError(f"refusing to overwrite enriched QB file: {ENRICHED}")
    template = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    reviews = pd.read_csv(review_path, dtype=str).fillna("")
    if reviews.game_id.duplicated().any():
        raise ValueError("QB review contains duplicate game_id")
    by_game = reviews.set_index("game_id").to_dict("index")
    profiles = _profile_lookup()
    errors, resolved = [], 0
    for game in template["games"]:
        review = by_game.get(game["game_id"], {})
        if not review or not review.get("as_of_utc"):
            continue
        try:
            as_of = _parse_aware(review["as_of_utc"], "as_of_utc")
            published = _parse_aware(review["source_published_at_utc"], "source_published_at_utc")
            kickoff = _parse_aware(game["kickoff_at_utc"], "kickoff_at_utc")
            if published > as_of:
                raise ValueError("source published after review cutoff")
            if as_of >= kickoff:
                raise ValueError("QB review is not pre-kickoff")
            if not review.get("source"):
                raise ValueError("source is required")
            for side in ("home", "away"):
                starter, backup = review[f"{side}_starter_id"], review[f"{side}_backup_id"]
                if starter not in profiles or backup not in profiles:
                    raise ValueError(f"{side} starter or backup is missing from historical profiles")
                probability = float(review[f"{side}_starter_probability"])
                if not 0.0 <= probability <= 1.0:
                    raise ValueError(f"{side} starter probability outside zero to one")
                game[side]["qb"].update({
                    "starter_id": starter, "backup_id": backup,
                    "starter_probability": probability, "qb_change_probability": None,
                    "starter_profile": profiles[starter], "backup_profile": profiles[backup],
                })
            game["as_of_utc"] = as_of.isoformat()
            game["source_timestamps"]["qb"] = published.isoformat()
            game["qb_source"] = review["source"]
            game["qb_reviewer_notes"] = review.get("reviewer_notes", "")
            game["status"] = "qb_resolved_continuity_pending"
            resolved += 1
        except (KeyError, TypeError, ValueError) as exc:
            errors.append({"game_id": game["game_id"], "error": str(exc)})
    if errors:
        return {"status": "review_rejected", "archived": False, "errors": errors}
    if resolved == 0:
        return {"status": "review_unresolved", "archived": False, "games": len(template["games"]),
                "qb_resolved_games": 0}
    template["qb_review_source"] = review_path.name
    ENRICHED.write_text(json.dumps(template, indent=2) + "\n", encoding="utf-8")
    return {"status": "qb_review_applied", "games": len(template["games"]), "qb_resolved_games": resolved,
            "continuity_resolved_games": 0, "path": str(ENRICHED.relative_to(ROOT))}


def main() -> None:
    parser = argparse.ArgumentParser(description="NFL Step 8 QB profile/review workflow")
    parser.add_argument("action", choices=("build-profiles", "prepare-review", "apply-review"))
    parser.add_argument("--input", type=Path)
    args = parser.parse_args()
    if args.action == "build-profiles":
        result = build_profiles()
    elif args.action == "prepare-review":
        result = prepare_review()
    else:
        if not args.input:
            parser.error("--input is required")
        result = apply_review(args.input)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
