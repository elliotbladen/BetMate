"""Fit and price the EPL yellow-card O/U 3.5 models for Step 3."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import PoissonRegressor

ROOT = Path(__file__).parent
FEATURES = ROOT / "data" / "epl" / "cards" / "epl_cards_context_features_step1_enriched.csv"
OUT = ROOT / "data" / "epl" / "cards" / "epl_cards_step3_prices.csv"
REPORT = ROOT / "reports" / "epl_cards_step3_model.json"

DEVELOPMENT = {"2022/23", "2023/24", "2024/25"}
TEST = "2025/26"
FEATURE_COLUMNS = [
    "ref_dev", "team_dev", "drawn_dev", "foul_dev", "venue_dev",
    "blocked_shots_volume", "crosses_volume", "box_shot_volume",
    "box_touch_volume", "possession_balance", "shot_on_target_volume",
    "starter_rating_volume", "starter_count_volume",
]


def nb_over_prob(lam: float, alpha: float, line: float = 3.5) -> float:
    if alpha <= 1e-9:
        return float(1.0 - stats.poisson.cdf(int(line), lam))
    r = 1.0 / alpha
    p = r / (r + lam)
    return float(1.0 - stats.nbinom.cdf(int(line), r, p))


def dispersion(y: np.ndarray, lam: np.ndarray) -> float:
    return float(max(np.mean(((y - lam) ** 2 - lam) / np.maximum(lam, 1e-9) ** 2), 0.0))


def make_features(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame(index=df.index)
    lg = df["league_yellow_mean_prior"]
    out["ref_dev"] = df["ref_yellow_mean_prior"] - lg
    out["team_dev"] = (df["home_team_yellow_mean_prior"] + df["away_team_yellow_mean_prior"]) - lg
    out["drawn_dev"] = (df["home_cards_drawn_mean_prior"] + df["away_cards_drawn_mean_prior"]) - lg
    out["foul_dev"] = (df["home_fouls_mean_prior"] + df["away_fouls_mean_prior"]) - df["league_fouls_mean_prior"]
    out["venue_dev"] = (df["home_yellow_home_mean_prior"] + df["away_yellow_away_mean_prior"]) - lg
    out["blocked_shots_volume"] = df["home_blocked_shots_prior"] + df["away_blocked_shots_prior"]
    out["crosses_volume"] = df["home_accurate_crosses_n_prior"] + df["away_accurate_crosses_n_prior"]
    out["box_shot_volume"] = df["home_shots_inside_box_prior"] + df["away_shots_inside_box_prior"]
    out["box_touch_volume"] = df["home_touches_opp_box_prior"] + df["away_touches_opp_box_prior"]
    out["possession_balance"] = df["home_possession_prior"] - df["away_possession_prior"]
    out["shot_on_target_volume"] = df["home_shots_on_target_prior"] + df["away_shots_on_target_prior"]
    out["starter_rating_volume"] = df["home_starter_rating_mean_prior"] + df["away_starter_rating_mean_prior"]
    out["starter_count_volume"] = df["home_starter_count_prior"] + df["away_starter_count_prior"]
    return out[FEATURE_COLUMNS].fillna(0.0)


def main() -> None:
    df = pd.read_csv(FEATURES)
    df["baseline_lambda"] = (
        df["ref_yellow_mean_prior"]
        * (df["home_team_yellow_mean_prior"] + df["away_team_yellow_mean_prior"])
        / df["league_yellow_mean_prior"].clip(lower=0.1)
    )
    dev = df["Season"].isin(DEVELOPMENT)
    train = df.loc[dev].copy()
    X_train = make_features(train)
    X_all = make_features(df)
    base_train = train["league_yellow_mean_prior"].clip(lower=0.1)
    # Poisson regression estimates multiplicative deviation around the prior league
    # level. Weighting by the offset gives the same interpretation as a log-link GLM.
    model = PoissonRegressor(alpha=1e-4, max_iter=2000)
    model.fit(X_train, train["total_yellow_cards"] / base_train, sample_weight=base_train)
    df["glm_lambda"] = model.predict(X_all) * df["league_yellow_mean_prior"].clip(lower=0.1)
    train_lam = df.loc[dev, "glm_lambda"].to_numpy()
    alpha = dispersion(train["total_yellow_cards"].to_numpy(), train_lam)
    for prefix in ["baseline", "glm"]:
        df[f"{prefix}_p_over35"] = [nb_over_prob(float(l), alpha) for l in df[f"{prefix}_lambda"]]
        df[f"{prefix}_p_under35"] = 1.0 - df[f"{prefix}_p_over35"]
        df[f"{prefix}_fair_over35"] = 1.0 / df[f"{prefix}_p_over35"].clip(lower=1e-6)
        df[f"{prefix}_fair_under35"] = 1.0 / df[f"{prefix}_p_under35"].clip(lower=1e-6)
    df["model_used"] = "glm"
    df["out_of_sample_2025_26"] = df["Season"].eq(TEST)
    keep = [
        "Season", "Date", "HomeTeam", "AwayTeam", "Referee", "ref_games_prior",
        "total_yellow_cards", "total_red_cards", "baseline_lambda", "glm_lambda",
        "baseline_p_over35", "baseline_p_under35", "baseline_fair_over35", "baseline_fair_under35",
        "glm_p_over35", "glm_p_under35", "glm_fair_over35", "glm_fair_under35",
        "model_used", "out_of_sample_2025_26",
    ]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df[keep].to_csv(OUT, index=False)
    report = {
        "development_seasons": sorted(DEVELOPMENT),
        "out_of_sample_season": TEST,
        "development_rows": int(dev.sum()),
        "out_of_sample_rows": int((~dev).sum()),
        "line": 3.5,
        "distribution": "negative_binomial",
        "dispersion_alpha": alpha,
        "glm_coefficients": dict(zip(FEATURE_COLUMNS, model.coef_.tolist())),
        "mean_lambdas": {
            "baseline_development": float(df.loc[dev, "baseline_lambda"].mean()),
            "glm_development": float(df.loc[dev, "glm_lambda"].mean()),
            "baseline_2025_26": float(df.loc[~dev, "baseline_lambda"].mean()),
            "glm_2025_26": float(df.loc[~dev, "glm_lambda"].mean()),
        },
        "outputs": str(OUT.relative_to(ROOT.parent.parent)),
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
