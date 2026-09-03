"""One-time 2025 NFL vault prediction, scoring, and permanent archive.

Run in order only:
    python -m ml.nfl.step5_vault freeze
    python -m ml.nfl.step5_vault predict
    python -m ml.nfl.step5_vault score

Each stage refuses to overwrite its output. Prediction writes no 2025 labels or
market fields. Scoring is a separate irreversible stage.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from math import erf, sqrt
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from .baselines import MARGIN_STATS, _metrics, fit_ridge, model_frame
from .challenger import (
    _classifier,
    _normal_win_probability,
    _probability_metrics,
    _regressor,
    challenger_frame,
)
from .evaluation import grade_spread_against_open, summarise
from .phase3 import CONTINUITY_COLUMNS, QB_COLUMNS


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "ml/nfl/reports/step5_freeze_manifest.json"
PREDICTIONS = ROOT / "data/nfl/predictions/step5_2025_vault_frozen.csv"
PREDICTION_MANIFEST = ROOT / "ml/nfl/reports/step5_prediction_manifest.json"
SCORED_GAMES = ROOT / "data/nfl/predictions/step5_2025_vault_scored.csv"
REPORT = ROOT / "ml/nfl/reports/step5_2025_vault.json"

FROZEN_INPUTS = (
    "ml/nfl/step5_vault.py",
    "ml/nfl/baselines.py",
    "ml/nfl/challenger.py",
    "ml/nfl/personnel.py",
    "ml/nfl/phase3.py",
    "ml/nfl/config.yaml",
    "data/nfl/features/weekly_epa.parquet",
    "data/nfl/features/personnel_context.parquet",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_once(path: Path, content: str) -> None:
    if path.exists():
        raise RuntimeError(f"refusing to overwrite frozen artefact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def freeze() -> dict:
    missing = [relative for relative in FROZEN_INPUTS if not (ROOT / relative).exists()]
    if missing:
        raise FileNotFoundError(f"missing frozen inputs: {missing}")
    manifest = {
        "status": "frozen_before_2025_vault_open",
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "train_through": 2024,
        "vault_season": 2025,
        "vault_prediction_may_be_written_once": True,
        "vault_result_may_be_scored_once": True,
        "staking_enabled": False,
        "files": {relative: _sha256(ROOT / relative) for relative in FROZEN_INPUTS},
    }
    _write_once(MANIFEST, json.dumps(manifest, indent=2) + "\n")
    return manifest


def _verify_freeze() -> dict:
    if not MANIFEST.exists():
        raise RuntimeError("freeze manifest does not exist")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    changed = [
        relative for relative, expected in manifest["files"].items()
        if _sha256(ROOT / relative) != expected
    ]
    if changed:
        raise RuntimeError(f"frozen inputs changed before vault prediction: {changed}")
    return manifest


def _ridge_columns(frame: pd.DataFrame) -> list[str]:
    return [c for c in frame if c.startswith("diff_")] + ["rest_diff", "div_game", "week"]


def predict() -> dict:
    manifest = _verify_freeze()
    if PREDICTIONS.exists() or PREDICTION_MANIFEST.exists():
        raise RuntimeError("2025 vault prediction has already been generated")

    games = pd.read_parquet(ROOT / "data/nfl/features/weekly_epa.parquet")
    personnel = pd.read_parquet(ROOT / "data/nfl/features/personnel_context.parquet")
    development = games[games.season <= 2024].sort_values(["season", "week", "game_id"]).copy()
    vault = games[games.season == 2025].sort_values(["week", "gameday", "game_id"]).copy()
    if len(vault) != 272:
        raise RuntimeError(f"expected 272 vault games, found {len(vault)}")

    base_dev = model_frame(development)
    base_vault = model_frame(vault)
    columns = _ridge_columns(base_dev)
    ridge_margin = fit_ridge(base_dev, development.margin, columns, alpha=25.0)
    total_columns = [c for c in base_dev if c.startswith("sum_")] + [
        "rest_sum", "div_game", "week", "dynamic_kickoff_rule",
        "onside_anytime_when_trailing", "kickoff_touchback_to_35",
        "regular_season_ot_both_possess", "onside_2026_alignment_rule",
    ]
    ridge_total = fit_ridge(base_dev, development.total, total_columns, alpha=25.0)

    # QB + continuity remains an oracle/research shadow because historical rows
    # identify the actual starter. It cannot become an official live price.
    personnel_columns = ["game_id"] + QB_COLUMNS + CONTINUITY_COLUMNS
    dev_pc = development.merge(personnel[personnel_columns], on="game_id", validate="one_to_one")
    vault_pc = vault.merge(personnel[personnel_columns], on="game_id", validate="one_to_one")
    pc_dev = pd.concat([
        model_frame(dev_pc), dev_pc[QB_COLUMNS + CONTINUITY_COLUMNS].astype(float).fillna(0.0)
    ], axis=1)
    pc_vault = pd.concat([
        model_frame(vault_pc), vault_pc[QB_COLUMNS + CONTINUITY_COLUMNS].astype(float).fillna(0.0)
    ], axis=1)
    pc_columns = columns + QB_COLUMNS + CONTINUITY_COLUMNS
    personnel_margin = fit_ridge(pc_dev, dev_pc.margin, pc_columns, alpha=25.0)

    tree_dev = challenger_frame(development)
    tree_vault = challenger_frame(vault)
    tree_margin_model = _regressor().fit(tree_dev, development.margin)
    tree_total_model = _regressor().fit(tree_dev, development.total)

    # Calibrate exclusively on 2024 using models fitted through 2023.
    early = development.season <= 2023
    calibration = development.season == 2024
    calibration_margin_model = _regressor().fit(tree_dev[early], development.loc[early, "margin"])
    calibration_margin = calibration_margin_model.predict(tree_dev[calibration])
    residual_sd = float(np.std(
        development.loc[calibration, "margin"].to_numpy() - calibration_margin, ddof=1
    ))
    direct_base = _classifier().fit(
        tree_dev[early], development.loc[early, "margin"].gt(0).astype(int)
    )
    calibration_raw = direct_base.predict_proba(tree_dev[calibration])[:, 1]
    calibration_logit = np.log(
        np.clip(calibration_raw, 0.001, 0.999) /
        np.clip(1.0 - calibration_raw, 0.001, 0.999)
    )
    platt = LogisticRegression(C=1.0, solver="lbfgs").fit(
        calibration_logit.reshape(-1, 1),
        development.loc[calibration, "margin"].gt(0).astype(int),
    )
    direct_model = _classifier().fit(tree_dev, development.margin.gt(0).astype(int))

    output = vault[["game_id", "season", "week", "gameday", "home_team", "away_team"]].copy()
    output["ridge_margin"] = ridge_margin.predict(base_vault)
    output["ridge_total"] = ridge_total.predict(base_vault)
    output["personnel_oracle_margin"] = personnel_margin.predict(pc_vault)
    output["tree_margin"] = tree_margin_model.predict(tree_vault)
    output["tree_total"] = tree_total_model.predict(tree_vault)
    output["margin_h2h_probability"] = _normal_win_probability(output.tree_margin.to_numpy(), residual_sd)
    raw = direct_model.predict_proba(tree_vault)[:, 1]
    raw_logit = np.log(np.clip(raw, 0.001, 0.999) / np.clip(1.0 - raw, 0.001, 0.999))
    output["direct_h2h_probability"] = platt.predict_proba(raw_logit.reshape(-1, 1))[:, 1]
    output["ridge_fair_home_spread"] = -output.ridge_margin
    output["tree_fair_home_spread"] = -output.tree_margin
    output["prediction_generated_at_utc"] = datetime.now(timezone.utc).isoformat()
    forbidden = {"home_score", "away_score", "margin", "total", "spread_home_close", "total_line_close"}
    if forbidden.intersection(output.columns):
        raise RuntimeError("vault prediction output contains a forbidden label or market field")
    output.to_csv(PREDICTIONS, index=False)
    prediction_manifest = {
        "status": "2025_vault_predictions_frozen_before_scoring",
        "generated_at_utc": output.prediction_generated_at_utc.iloc[0],
        "games": len(output),
        "train_through": 2024,
        "vault_season": 2025,
        "freeze_manifest_sha256": _sha256(MANIFEST),
        "prediction_sha256": _sha256(PREDICTIONS),
        "labels_in_prediction_file": False,
        "staking_enabled": False,
    }
    _write_once(PREDICTION_MANIFEST, json.dumps(prediction_manifest, indent=2) + "\n")
    return prediction_manifest


def _spread_bet_summary(scored: pd.DataFrame, prediction_column: str, threshold: float) -> dict:
    rows = scored.dropna(subset=[prediction_column, "spread_home_open"]).copy()
    fair = rows[prediction_column]
    opener = rows.spread_home_open
    edge = (fair - opener).abs()
    rows = rows[edge >= threshold].copy()
    home_bet = rows[prediction_column] < rows.spread_home_open
    cover_margin = rows.margin + rows.spread_home_open
    result = np.where(
        cover_margin.eq(0), "push",
        np.where((home_bet & cover_margin.gt(0)) | (~home_bet & cover_margin.lt(0)), "win", "loss"),
    )
    wins = int((result == "win").sum())
    losses = int((result == "loss").sum())
    pushes = int((result == "push").sum())
    synthetic_profit = wins * (100.0 / 110.0) - losses
    return {
        "threshold_points": threshold,
        "bets": len(rows), "wins": wins, "losses": losses, "pushes": pushes,
        "win_rate_ex_pushes": wins / (wins + losses) if wins + losses else 0.0,
        "synthetic_roi_at_minus_110": synthetic_profit / len(rows) if len(rows) else 0.0,
        "warning": "synthetic only; exact bookmaker spread prices were not archived",
    }


def score() -> dict:
    _verify_freeze()
    if not PREDICTIONS.exists() or not PREDICTION_MANIFEST.exists():
        raise RuntimeError("frozen vault prediction does not exist")
    if REPORT.exists() or SCORED_GAMES.exists():
        raise RuntimeError("2025 vault has already been scored")
    prediction_manifest = json.loads(PREDICTION_MANIFEST.read_text(encoding="utf-8"))
    if _sha256(PREDICTIONS) != prediction_manifest["prediction_sha256"]:
        raise RuntimeError("frozen vault prediction hash changed before scoring")

    predictions = pd.read_csv(PREDICTIONS)
    games = pd.read_parquet(ROOT / "data/nfl/features/weekly_epa.parquet")
    labels = games[games.season == 2025][[
        "game_id", "home_score", "away_score", "margin", "total",
        "spread_home_open", "spread_home_close", "total_line_open", "total_line_close",
        "h2h_home_close", "h2h_away_close",
    ]]
    scored = predictions.merge(labels, on="game_id", validate="one_to_one")
    scored["home_win"] = scored.margin.gt(0).astype(int)
    market_home = 1.0 / scored.h2h_home_close
    market_away = 1.0 / scored.h2h_away_close
    scored["market_h2h_probability"] = market_home / (market_home + market_away)

    opening_rows = [
        grade_spread_against_open(fair, opening, closing)
        for fair, opening, closing in scored[[
            "tree_fair_home_spread", "spread_home_open", "spread_home_close"
        ]].dropna().itertuples(index=False, name=None)
    ]
    opening_summary = summarise(opening_rows)
    report = {
        "status": "2025_vault_opened_and_permanently_scored",
        "scored_at_utc": datetime.now(timezone.utc).isoformat(),
        "prediction_sha256": prediction_manifest["prediction_sha256"],
        "games": len(scored),
        "training_through": 2024,
        "retuning_after_vault": False,
        "staking_enabled": False,
        "margin": {
            "ridge": _metrics(scored.margin, scored.ridge_margin),
            "personnel_oracle_shadow": _metrics(scored.margin, scored.personnel_oracle_margin),
            "shallow_tree_shadow": _metrics(scored.margin, scored.tree_margin),
            "opening_spread": _metrics(scored.margin, -scored.spread_home_open),
            "closing_spread": _metrics(scored.margin, -scored.spread_home_close),
        },
        "total": {
            "ridge": _metrics(scored.total, scored.ridge_total),
            "shallow_tree_shadow": _metrics(scored.total, scored.tree_total),
            "opening_total": _metrics(scored.total, scored.total_line_open),
            "closing_total": _metrics(scored.total, scored.total_line_close),
        },
        "h2h": {
            "margin_derived": _probability_metrics(scored.home_win, scored.margin_h2h_probability),
            "direct_calibrated_shadow": _probability_metrics(scored.home_win, scored.direct_h2h_probability),
            "closing_market": _probability_metrics(scored.home_win, scored.market_h2h_probability),
        },
        "tree_vs_open_to_close": opening_summary.__dict__,
        "synthetic_opening_spread_bets": {
            "ridge": [_spread_bet_summary(scored, "ridge_fair_home_spread", value) for value in (0.0, 1.0, 2.0, 3.0)],
            "tree_shadow": [_spread_bet_summary(scored, "tree_fair_home_spread", value) for value in (0.0, 1.0, 2.0, 3.0)],
        },
        "opening_line_warning": (
            "Historical opener audit is incomplete. Betting ROI assumes -110 and is diagnostic only, "
            "not evidence of an obtainable historical return."
        ),
        "permanent_decision": "record_result_without_model_tuning",
    }
    scored.to_csv(SCORED_GAMES, index=False)
    _write_once(REPORT, json.dumps(report, indent=2) + "\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("freeze", "predict", "score"))
    args = parser.parse_args()
    result = {"freeze": freeze, "predict": predict, "score": score}[args.action]()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
