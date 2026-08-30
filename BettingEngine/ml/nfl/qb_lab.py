"""Over-detailed FTN quarterback shadow, isolated from official NFL prices."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

from .baselines import _metrics, fit_ridge, model_frame
from .phase3 import QB_COLUMNS


PRIOR_PLAYS = 100.0
RATE_PRIORS = {
    "catchable": 0.72,
    "interception_worthy": 0.03,
    "qb_fault_sack": 0.04,
    "out_of_pocket": 0.12,
    "under_blitz": 0.30,
    "play_action": 0.24,
    "motion": 0.45,
    "throw_away": 0.04,
    "created_reception": 0.03,
}
ADVANCED_QB_COLUMNS = [f"diff_ftn_{name}_posterior" for name in RATE_PRIORS]


def paid_qb_schema() -> dict[str, list[str]]:
    """Stable adapter contract for later PFF/SIS CSV or API imports."""
    return {
        "identity": ["season", "week", "game_id", "player_id", "captured_at", "provider"],
        "accuracy": ["catchable_rate", "completion_over_expected", "drop_adjusted_accuracy"],
        "decisions": ["turnover_worthy_rate", "throwaway_rate", "big_time_throw_rate"],
        "pressure": ["pressure_rate", "pressure_to_sack_rate", "qb_fault_sack_rate"],
        "context": ["clean_pocket_rate", "blitz_rate", "play_action_rate", "motion_rate"],
    }


def load_ftn_qb_games(ftn_dir: str, pbp_dir: str) -> pd.DataFrame:
    rows = []
    ftn_columns = [
        "nflverse_game_id", "season", "week", "nflverse_play_id",
        "is_motion", "is_play_action", "is_qb_out_of_pocket",
        "is_interception_worthy", "is_throw_away", "is_catchable_ball",
        "is_created_reception", "n_blitzers", "is_qb_fault_sack",
    ]
    pbp_columns = ["game_id", "play_id", "passer_player_id", "posteam", "qb_dropback"]
    for season in range(2022, 2026):
        ftn = pd.read_parquet(Path(ftn_dir) / f"ftn_charting_{season}.parquet", columns=ftn_columns)
        pbp = pd.read_parquet(Path(pbp_dir) / f"play_by_play_{season}.parquet", columns=pbp_columns)
        joined = ftn.merge(
            pbp, left_on=["nflverse_game_id", "nflverse_play_id"],
            right_on=["game_id", "play_id"], how="inner", validate="one_to_one",
        )
        joined = joined[joined.passer_player_id.notna() & joined.qb_dropback.fillna(0).eq(1)].copy()
        joined["under_blitz"] = joined.n_blitzers.fillna(0).gt(0)
        boolean_map = {
            "catchable": "is_catchable_ball",
            "interception_worthy": "is_interception_worthy",
            "qb_fault_sack": "is_qb_fault_sack",
            "out_of_pocket": "is_qb_out_of_pocket",
            "under_blitz": "under_blitz",
            "play_action": "is_play_action",
            "motion": "is_motion",
            "throw_away": "is_throw_away",
            "created_reception": "is_created_reception",
        }
        aggregations = {name: (source, "sum") for name, source in boolean_map.items()}
        aggregations["charted_plays"] = ("qb_dropback", "count")
        game = joined.groupby(
            ["game_id", "season", "week", "posteam", "passer_player_id"], as_index=False
        ).agg(**aggregations)
        rows.append(game)
    return pd.concat(rows, ignore_index=True)


def build_advanced_qb_features(schedules: pd.DataFrame, qb_games: pd.DataFrame) -> pd.DataFrame:
    lookup = {(row.game_id, row.passer_player_id): row for row in qb_games.itertuples(index=False)}
    state = defaultdict(lambda: {"plays": 0.0, **{name: 0.0 for name in RATE_PRIORS}})
    rows = []
    games = schedules[
        schedules.game_type.eq("REG") & schedules.season.between(2022, 2025)
    ].sort_values(["gameday", "game_id"])
    for game in games.itertuples(index=False):
        row = {"game_id": game.game_id, "season": game.season, "week": game.week}
        for side in ("home", "away"):
            player = getattr(game, f"{side}_qb_id")
            player = "" if pd.isna(player) else str(player)
            player_state = state[player]
            denominator = player_state["plays"] + PRIOR_PLAYS
            for name, prior_rate in RATE_PRIORS.items():
                row[f"{side}_ftn_{name}_posterior"] = (
                    player_state[name] + PRIOR_PLAYS * prior_rate
                ) / denominator
            row[f"{side}_ftn_charted_plays"] = player_state["plays"]
        for name in RATE_PRIORS:
            row[f"diff_ftn_{name}_posterior"] = (
                row[f"home_ftn_{name}_posterior"] - row[f"away_ftn_{name}_posterior"]
            )
        row["diff_ftn_charted_plays"] = row["home_ftn_charted_plays"] - row["away_ftn_charted_plays"]
        rows.append(row)
        for side in ("home", "away"):
            player = getattr(game, f"{side}_qb_id")
            player = "" if pd.isna(player) else str(player)
            played = lookup.get((game.game_id, player))
            if played is None or not player:
                continue
            player_state = state[player]
            player_state["plays"] += float(played.charted_plays)
            for name in RATE_PRIORS:
                player_state[name] += float(getattr(played, name))
    return pd.DataFrame(rows)


def build_qb_lab_store(
    schedule_path: str = "data/nfl/schedules/games.csv",
    ftn_dir: str = "data/nfl/ftn_charting",
    pbp_dir: str = "data/nfl/pbp",
    output_path: str = "data/nfl/features/qb_lab_ftn.parquet",
) -> pd.DataFrame:
    schedules = pd.read_csv(schedule_path)
    games = load_ftn_qb_games(ftn_dir, pbp_dir)
    features = build_advanced_qb_features(schedules, games)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    features.to_parquet(output, index=False)
    return features


def evaluate_qb_lab(
    core_path: str = "data/nfl/features/weekly_epa.parquet",
    personnel_path: str = "data/nfl/features/personnel_context.parquet",
    lab_path: str = "data/nfl/features/qb_lab_ftn.parquet",
) -> tuple[pd.DataFrame, dict]:
    core_games = pd.read_parquet(core_path)
    personnel = pd.read_parquet(personnel_path)[["game_id"] + QB_COLUMNS]
    lab = pd.read_parquet(lab_path)
    games = core_games.merge(personnel, on="game_id", validate="one_to_one").merge(
        lab, on=["game_id", "season", "week"], how="inner", validate="one_to_one"
    )
    games = games[games.season.between(2023, 2024)].sort_values(["season", "week", "game_id"]).copy()
    core_design = model_frame(games)
    extras = games[QB_COLUMNS + ADVANCED_QB_COLUMNS].astype(float).fillna(0.0)
    design = pd.concat([core_design, extras], axis=1)
    base = [c for c in core_design if c.startswith("diff_")] + ["rest_diff", "div_game", "week"]
    shuffled = games.groupby("season", group_keys=False)[ADVANCED_QB_COLUMNS].sample(
        frac=1.0, random_state=350
    ).reset_index(drop=True)
    shuffled.index = design.index
    shuffled_columns = []
    for column in ADVANCED_QB_COLUMNS:
        name = f"shuffled_{column}"
        design[name] = shuffled[column].to_numpy()
        shuffled_columns.append(name)
    families = {
        "core": base,
        "core_plus_basic_qb": base + QB_COLUMNS,
        "core_plus_ftn": base + ADVANCED_QB_COLUMNS,
        "core_plus_basic_qb_ftn": base + QB_COLUMNS + ADVANCED_QB_COLUMNS,
        "core_plus_shuffled_ftn": base + shuffled_columns,
    }
    outputs = []
    # FTN begins in 2022: train 2022 history for 2023, then expand through 2023.
    full_core = core_games.merge(personnel, on="game_id", validate="one_to_one").merge(
        lab, on=["game_id", "season", "week"], how="inner", validate="one_to_one"
    ).sort_values(["season", "week", "game_id"])
    full_core_design = model_frame(full_core)
    full_design = pd.concat([
        full_core_design,
        full_core[QB_COLUMNS + ADVANCED_QB_COLUMNS].astype(float).fillna(0.0),
    ], axis=1)
    # Recreate negative-control columns on the complete frame.
    full_shuffled = full_core.groupby("season", group_keys=False)[ADVANCED_QB_COLUMNS].sample(
        frac=1.0, random_state=350
    ).reset_index(drop=True)
    full_shuffled.index = full_design.index
    for column, name in zip(ADVANCED_QB_COLUMNS, shuffled_columns):
        full_design[name] = full_shuffled[column].to_numpy()
    for season in (2023, 2024):
        train = full_core.season < season
        test = full_core.season == season
        fold = full_core.loc[test, ["game_id", "season", "margin", "spread_home_close"]].copy()
        for name, columns in families.items():
            model = fit_ridge(full_design[train], full_core.loc[train, "margin"], columns, alpha=35.0)
            fold[name] = model.predict(full_design[test])
        outputs.append(fold)
    predictions = pd.concat(outputs, ignore_index=True)
    report = {
        "status": "deep_shadow_free_ftn",
        "cost_usd": 0,
        "test_seasons": [2023, 2024],
        "games": len(predictions),
        "vault_2025_predictions": int((predictions.season == 2025).sum()),
        "margin": {name: _metrics(predictions.margin, predictions[name]) for name in families},
        "to_closing_spread": {
            name: _metrics(-predictions.spread_home_close, predictions[name]) for name in families
        },
        "paid_adapter_schema": paid_qb_schema(),
        "limitations": [
            "FTN history begins in 2022, so this is an early small-sample test",
            "historical actual starters provide a research ceiling, not a live availability feed",
            "vendor charting publication timestamps must be archived prospectively",
        ],
    }
    return predictions, report


if __name__ == "__main__":
    store = build_qb_lab_store()
    predictions, report = evaluate_qb_lab()
    predictions.to_csv("data/nfl/predictions/step3_5_qb_lab.csv", index=False)
    Path("ml/nfl/reports/step3_5_qb_lab.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(f"QB lab store: {len(store)} games")
    print(json.dumps(report, indent=2))
