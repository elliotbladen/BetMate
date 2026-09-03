"""Step 8B live T2/T3 shadow inputs and model-derived contributions."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from .baselines import fit_ridge, model_frame
from .phase3 import CONTINUITY_COLUMNS, INJURY_COLUMNS, QB_COLUMNS


ROOT = Path(__file__).resolve().parents[2]
FEATURES = ROOT / "data/nfl/features/weekly_epa.parquet"
PERSONNEL = ROOT / "data/nfl/features/personnel_context.parquet"
SCHEDULES = ROOT / "data/nfl/schedules/games.csv"
PREDICTIONS = ROOT / "data/nfl/predictions/2026_week01_paper_frozen.csv"
MODEL = ROOT / "ml/nfl/reports/step8_live_tier_model.json"
TEMPLATE = ROOT / "data/nfl/live_tiers/2026_week01_input_template.json"
EASTERN = ZoneInfo("America/New_York")


def _parse_aware(value: str, name: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True)
class LiveTierInput:
    game_id: str
    as_of_utc: datetime
    kickoff_at_utc: datetime
    source_timestamps: dict[str, datetime]
    home_starter_probability: float | None
    away_starter_probability: float | None

    def validate(self) -> None:
        if not self.game_id:
            raise ValueError("game_id is required")
        if self.as_of_utc.tzinfo is None or self.kickoff_at_utc.tzinfo is None:
            raise ValueError("as_of and kickoff must be timezone-aware")
        if self.as_of_utc >= self.kickoff_at_utc:
            raise ValueError("live tier input must be frozen before kickoff")
        late = [name for name, stamp in self.source_timestamps.items() if stamp > self.as_of_utc]
        if late:
            raise ValueError(f"sources newer than as_of: {', '.join(sorted(late))}")
        for side, probability in (("home", self.home_starter_probability), ("away", self.away_starter_probability)):
            if probability is not None and not 0.0 <= probability <= 1.0:
                raise ValueError(f"{side} starter probability must be between zero and one")


def validate_record(record: dict) -> list[str]:
    errors: list[str] = []
    try:
        sources = {
            name: _parse_aware(stamp, f"source_timestamps.{name}")
            for name, stamp in record.get("source_timestamps", {}).items() if stamp
        }
        item = LiveTierInput(
            game_id=str(record.get("game_id", "")),
            as_of_utc=_parse_aware(record["as_of_utc"], "as_of_utc"),
            kickoff_at_utc=_parse_aware(record["kickoff_at_utc"], "kickoff_at_utc"),
            source_timestamps=sources,
            home_starter_probability=record.get("home", {}).get("qb", {}).get("starter_probability"),
            away_starter_probability=record.get("away", {}).get("qb", {}).get("starter_probability"),
        )
        item.validate()
    except (KeyError, TypeError, ValueError) as exc:
        errors.append(str(exc))
    for side in ("home", "away"):
        qb = record.get(side, {}).get("qb", {})
        if qb.get("starter_probability") is not None:
            for required in ("starter_id", "backup_id", "starter_profile", "backup_profile"):
                if not qb.get(required):
                    errors.append(f"{side}.qb.{required} is required when starter probability is supplied")
    return errors


def _model_payload() -> dict:
    personnel = pd.read_parquet(PERSONNEL).drop(
        columns=["season", "week", "home_team", "away_team", "roof", "surface"]
    )
    games = pd.read_parquet(FEATURES).merge(personnel, on="game_id", how="left", validate="one_to_one")
    development = games[games.season.le(2024)].copy()
    core = model_frame(development)
    extras = development[QB_COLUMNS + INJURY_COLUMNS + CONTINUITY_COLUMNS].astype(float).fillna(0.0)
    design = pd.concat([core, extras], axis=1)
    base = [column for column in core if column.startswith("diff_")] + ["rest_diff", "div_game", "week"]
    columns = base + QB_COLUMNS + INJURY_COLUMNS + CONTINUITY_COLUMNS
    model = fit_ridge(design, development.margin, columns, alpha=25.0)
    coefficient = dict(zip(model.columns, model.coefficients[1:]))
    mean = dict(zip(model.columns, model.mean))
    scale = dict(zip(model.columns, model.scale))
    return {
        "status": "shadow_only_trained_through_2024",
        "training_games": len(development), "alpha": 25.0,
        "columns": list(model.columns), "mean": mean, "scale": scale,
        "standardized_coefficient": coefficient,
        "tier_columns": {"t2_qb": QB_COLUMNS, "t2_availability_diagnostic": INJURY_COLUMNS, "t3_continuity": CONTINUITY_COLUMNS},
        "application": {
            "t2_qb": "shadow_contribution_only",
            "t2_availability": "diagnostic_no_points",
            "t3_continuity": "shadow_contribution_only",
            "staking_enabled": False,
            "caps_frozen": False,
        },
    }


def train_model() -> dict:
    if MODEL.exists():
        raise RuntimeError(f"refusing to overwrite shadow model: {MODEL}")
    payload = _model_payload()
    MODEL.parent.mkdir(parents=True, exist_ok=True)
    MODEL.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def _kickoff(row: pd.Series) -> str:
    local = datetime.fromisoformat(f"{row.gameday}T{row.gametime}").replace(tzinfo=EASTERN)
    return local.astimezone(timezone.utc).isoformat()


def prepare_template() -> dict:
    if TEMPLATE.exists():
        raise RuntimeError(f"refusing to overwrite live input template: {TEMPLATE}")
    predictions = pd.read_csv(PREDICTIONS)
    schedule = pd.read_csv(SCHEDULES)
    games = predictions.merge(
        schedule[["game_id", "gameday", "gametime"]], on=["game_id", "gameday", "gametime"], validate="one_to_one"
    )
    records = []
    for row in games.itertuples(index=False):
        side = {
            "qb": {
                "starter_id": None, "backup_id": None, "starter_probability": None,
                "starter_profile": None, "backup_profile": None,
            },
            "availability": {
                "injury_burden": None, "players_out": None,
                "players_questionable": None, "injury_report_rows": None,
            },
            "continuity": {
                "weekly_roster_continuity": None, "returning_roster_share": None,
                "returning_ol_share": None, "returning_receiver_share": None,
            },
        }
        kickoff = datetime.fromisoformat(f"{row.gameday}T{row.gametime}").replace(tzinfo=EASTERN).astimezone(timezone.utc)
        records.append({
            "game_id": row.game_id, "home_team": row.home_team, "away_team": row.away_team,
            "kickoff_at_utc": kickoff.isoformat(), "as_of_utc": None,
            "source_timestamps": {"qb": None, "injuries": None, "roster": None},
            "home": json.loads(json.dumps(side)), "away": json.loads(json.dumps(side)),
            "status": "unresolved_no_adjustment",
        })
    payload = {
        "season": 2026, "week": 1, "mode": "shadow", "staking_enabled": False,
        "instructions": "Populate only from timestamped sources; null means unresolved and produces no adjustment.",
        "games": records,
    }
    TEMPLATE.parent.mkdir(parents=True, exist_ok=True)
    TEMPLATE.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return {"status": "template_created", "games": len(records), "resolved_games": 0, "path": str(TEMPLATE.relative_to(ROOT))}


def validate_file(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    results = []
    for record in payload.get("games", []):
        errors = validate_record(record)
        results.append({"game_id": record.get("game_id", ""), "valid": not errors, "errors": errors})
    return {
        "status": "valid" if results and all(row["valid"] for row in results) else "invalid_or_unresolved",
        "games": len(results), "valid_games": sum(row["valid"] for row in results), "results": results,
        "staking_enabled": False,
    }


def _mixed_profile(qb: dict) -> dict[str, float]:
    probability = float(qb["starter_probability"])
    starter, backup = qb["starter_profile"], qb["backup_profile"]
    fields = (
        "qb_epa_posterior", "qb_success_posterior", "qb_sack_rate_posterior",
        "qb_turnover_rate_posterior", "qb_scramble_rate_posterior", "qb_prior_dropbacks",
    )
    values = {}
    for field in fields:
        values[field] = probability * float(starter[field]) + (1.0 - probability) * float(backup[field])
    values["qb_change"] = float(qb.get("qb_change_probability", 0.0))
    return values


def _contribution(values: dict[str, float], columns: list[str], model: dict) -> float:
    return float(sum(
        ((float(values[column]) - float(model["mean"][column])) / float(model["scale"][column]))
        * float(model["standardized_coefficient"][column])
        for column in columns
    ))


def score_file(path: Path) -> dict:
    validation = validate_file(path)
    if validation["status"] != "valid":
        return {**validation, "status": "unresolved_no_shadow_score"}
    model = json.loads(MODEL.read_text(encoding="utf-8"))
    payload = json.loads(path.read_text(encoding="utf-8"))
    predictions = pd.read_csv(PREDICTIONS).set_index("game_id")
    rows = []
    for record in payload["games"]:
        game_id = record["game_id"]
        home_qb, away_qb = _mixed_profile(record["home"]["qb"]), _mixed_profile(record["away"]["qb"])
        values = {f"diff_{field}": home_qb[field] - away_qb[field] for field in home_qb}
        for raw in ("weekly_roster_continuity", "returning_roster_share", "returning_ol_share", "returning_receiver_share"):
            values[f"diff_{raw}"] = (
                float(record["home"]["continuity"][raw]) - float(record["away"]["continuity"][raw])
            )
        t2 = _contribution(values, model["tier_columns"]["t2_qb"], model)
        t3 = _contribution(values, model["tier_columns"]["t3_continuity"], model)
        base_spread = float(predictions.loc[game_id, "ridge_fair_home_spread"])
        rows.append({
            "game_id": game_id, "as_of_utc": record["as_of_utc"],
            "t1_fair_home_spread": base_spread,
            "t2_qb_shadow_margin_points": t2,
            "t3_continuity_shadow_margin_points": t3,
            "combined_shadow_fair_home_spread_uncapped": base_spread - t2 - t3,
            "availability_points_applied": 0.0,
            "caps_frozen": False, "official_price_changed": False,
            "staking_enabled": False,
        })
    return {"status": "shadow_scored_unapproved_uncapped", "games": len(rows), "rows": rows, "staking_enabled": False}


def main() -> None:
    parser = argparse.ArgumentParser(description="NFL Step 8B live tier shadow")
    parser.add_argument("action", choices=("train-shadow-model", "prepare-week-one-template", "validate-file", "score-file"))
    parser.add_argument("--input", type=Path)
    args = parser.parse_args()
    if args.action == "train-shadow-model":
        result = train_model()
    elif args.action == "prepare-week-one-template":
        result = prepare_template()
    elif args.action == "validate-file":
        if not args.input:
            parser.error("--input is required")
        result = validate_file(args.input)
    else:
        if not args.input:
            parser.error("--input is required")
        result = score_file(args.input)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
