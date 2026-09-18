"""Compare, calibrate and guard the EPL yellow-card models for Step 4."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit, logit
from sklearn.linear_model import LogisticRegression, PoissonRegressor

from fit_epl_cards_model_step3 import FEATURE_COLUMNS, dispersion, make_features, nb_over_prob

ROOT = Path(__file__).parent
FEATURES = ROOT / "data" / "epl" / "cards" / "epl_cards_context_features_step1_enriched.csv"
OUT = ROOT / "data" / "epl" / "cards" / "epl_cards_step4_calibrated_prices.csv"
REPORT = ROOT / "reports" / "epl_cards_step4_calibration.json"
SEASONS = ["2022/23", "2023/24", "2024/25", "2025/26"]
DEVELOPMENT = SEASONS[:3]
TEST = SEASONS[-1]


def baseline_lambda(frame: pd.DataFrame) -> np.ndarray:
    return (
        frame["ref_yellow_mean_prior"].to_numpy()
        * (frame["home_team_yellow_mean_prior"] + frame["away_team_yellow_mean_prior"]).to_numpy()
        / frame["league_yellow_mean_prior"].clip(lower=0.1).to_numpy()
    )


def fit_glm(train: pd.DataFrame) -> tuple[PoissonRegressor, float]:
    x = make_features(train)
    base = train["league_yellow_mean_prior"].clip(lower=0.1)
    model = PoissonRegressor(alpha=1e-4, max_iter=2000)
    model.fit(x, train["total_yellow_cards"] / base, sample_weight=base)
    lam = model.predict(x) * base.to_numpy()
    return model, dispersion(train["total_yellow_cards"].to_numpy(), lam)


def prices(lam: np.ndarray, alpha: float) -> np.ndarray:
    return np.array([nb_over_prob(float(x), alpha) for x in lam])


def metrics(y: np.ndarray, p: np.ndarray) -> dict[str, float]:
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return {
        "brier": float(np.mean((p - y) ** 2)),
        "log_loss": float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))),
        "mean_probability": float(p.mean()),
        "actual_rate": float(y.mean()),
        "mae_probability": float(np.mean(np.abs(p - y))),
    }


def main() -> None:
    df = pd.read_csv(FEATURES)
    df["over35_result"] = (df["total_yellow_cards"] > 3.5).astype(int)
    oof = []
    # Strict rolling-origin validation inside the development seasons.
    for i, season in enumerate(DEVELOPMENT):
        if i == 0:
            continue
        train = df[df["Season"].isin(DEVELOPMENT[:i])]
        valid = df[df["Season"] == season].copy()
        glm, alpha = fit_glm(train)
        p_base = prices(baseline_lambda(valid), dispersion(
            train["total_yellow_cards"].to_numpy(), baseline_lambda(train)))
        p_glm = prices(glm.predict(make_features(valid)) * valid["league_yellow_mean_prior"].clip(lower=0.1).to_numpy(), alpha)
        valid["baseline_p_over35"] = p_base
        valid["glm_p_over35"] = p_glm
        valid["validation_origin"] = "+".join(DEVELOPMENT[:i])
        oof.append(valid)
    oof_df = pd.concat(oof, ignore_index=True)
    y_oof = oof_df["over35_result"].to_numpy()

    summary = {}
    for model in ("baseline", "glm"):
        summary[model] = metrics(y_oof, oof_df[f"{model}_p_over35"].to_numpy())

    # Platt calibration is fit only on rolling-origin predictions, never on 2025/26.
    calibrators = {}
    for model in ("baseline", "glm"):
        raw = np.clip(oof_df[f"{model}_p_over35"].to_numpy(), 1e-5, 1 - 1e-5)
        cal = LogisticRegression(C=1e6, solver="lbfgs")
        cal.fit(logit(raw).reshape(-1, 1), y_oof)
        calibrated = cal.predict_proba(logit(raw).reshape(-1, 1))[:, 1]
        summary[f"{model}_calibrated"] = metrics(y_oof, calibrated)
        calibrators[model] = cal

    # Select by rolling-origin Brier score, then log loss.
    candidates = ["baseline", "glm"]
    selected = min(candidates, key=lambda m: (summary[m]["brier"], summary[m]["log_loss"]))
    selected_cal = calibrators[selected]

    # Refit the selected raw model on all development seasons and price 2025/26.
    train = df[df["Season"].isin(DEVELOPMENT)]
    test = df[df["Season"] == TEST].copy()
    glm, alpha = fit_glm(train)
    p_base = prices(baseline_lambda(test), dispersion(
        train["total_yellow_cards"].to_numpy(), baseline_lambda(train)))
    p_glm = prices(glm.predict(make_features(test)) * test["league_yellow_mean_prior"].clip(lower=0.1).to_numpy(), alpha)
    test["baseline_p_over35"] = p_base
    test["glm_p_over35"] = p_glm
    raw = test[f"{selected}_p_over35"].to_numpy()
    test["selected_model"] = selected
    test["selected_p_over35_raw"] = raw
    test["selected_p_over35_calibrated"] = selected_cal.predict_proba(logit(np.clip(raw, 1e-5, 1 - 1e-5)).reshape(-1, 1))[:, 1]
    test["selected_p_under35_calibrated"] = 1 - test["selected_p_over35_calibrated"]
    test["ref_sample_ok"] = test["ref_games_prior"] >= 25
    test["probability_guardrail_ok"] = test[["selected_p_over35_calibrated", "selected_p_under35_calibrated"]].max(axis=1) >= 0.57
    test["eligible_for_step5"] = test["ref_sample_ok"] & test["probability_guardrail_ok"]
    test["fair_over35_calibrated"] = 1 / test["selected_p_over35_calibrated"].clip(lower=1e-6)
    test["fair_under35_calibrated"] = 1 / test["selected_p_under35_calibrated"].clip(lower=1e-6)
    keep = ["Season", "Date", "HomeTeam", "AwayTeam", "Referee", "ref_games_prior", "total_yellow_cards",
            "selected_model", "selected_p_over35_raw", "selected_p_over35_calibrated",
            "selected_p_under35_calibrated", "fair_over35_calibrated", "fair_under35_calibrated",
            "ref_sample_ok", "probability_guardrail_ok", "eligible_for_step5"]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    test[keep].to_csv(OUT, index=False)
    report = {
        "oof_seasons": ["2023/24", "2024/25"],
        "held_out_season": TEST,
        "oof_rows": int(len(oof_df)),
        "summary": summary,
        "selected_model": selected,
        "calibration": "Platt logistic map fit on rolling-origin development predictions",
        "guardrails": {"minimum_referee_games": 25, "minimum_side_probability": 0.57},
        "held_out_eligible_rows": int(test["eligible_for_step5"].sum()),
        "held_out_ref_thin_rows": int((~test["ref_sample_ok"]).sum()),
        "output": str(OUT.relative_to(ROOT.parent.parent)),
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
