"""
Isotonic regression calibration for model probabilities.

Why needed:
  The raw Poisson model gives P(over25) avg = 0.491 while actual EPL rate = 0.554.
  This is Poisson overdispersion — real football has more variance than a Poisson
  assumes. Isotonic calibration maps model probabilities to observed frequencies
  without changing the ranking (it only adjusts the magnitude).

Usage:
    cal = TotalsCalibrator()
    cal.fit(train_df)                    # fit on training seasons
    p_over_cal = cal.transform(p_over)   # apply to test predictions

Also calibrates H2H (home/draw/away) probabilities using the same method.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression


class TotalsCalibrator:
    """Calibrates over/under probabilities via isotonic regression."""

    def __init__(self):
        self.iso_over:  IsotonicRegression | None = None
        self.p_min = 0.0
        self.p_max = 1.0

    def fit(self, p_model: np.ndarray, y_actual: np.ndarray) -> "TotalsCalibrator":
        """
        p_model  : model's raw P(over25) per match (array)
        y_actual : 1 if over25 occurred, 0 otherwise (array)
        """
        self.iso_over = IsotonicRegression(out_of_bounds="clip")
        self.iso_over.fit(p_model, y_actual)
        self.p_min = float(p_model.min())
        self.p_max = float(p_model.max())
        return self

    def transform(self, p_model: float | np.ndarray) -> float | np.ndarray:
        if self.iso_over is None:
            return p_model
        scalar = np.isscalar(p_model)
        arr = np.atleast_1d(np.array(p_model, dtype=float))
        cal = self.iso_over.predict(arr)
        cal = np.clip(cal, 0.01, 0.99)
        return float(cal[0]) if scalar else cal


class H2HCalibrator:
    """Calibrates home/draw/away probabilities jointly via isotonic regression."""

    def __init__(self):
        self.iso_home: IsotonicRegression | None = None
        self.iso_draw: IsotonicRegression | None = None
        self.iso_away: IsotonicRegression | None = None

    def fit(
        self,
        p_home: np.ndarray,
        p_draw: np.ndarray,
        p_away: np.ndarray,
        results: np.ndarray,          # array of "H", "D", "A"
    ) -> "H2HCalibrator":
        y_h = (results == "H").astype(float)
        y_d = (results == "D").astype(float)
        y_a = (results == "A").astype(float)

        self.iso_home = IsotonicRegression(out_of_bounds="clip").fit(p_home, y_h)
        self.iso_draw = IsotonicRegression(out_of_bounds="clip").fit(p_draw, y_d)
        self.iso_away = IsotonicRegression(out_of_bounds="clip").fit(p_away, y_a)
        return self

    def transform(
        self,
        p_home: float,
        p_draw: float,
        p_away: float,
    ) -> tuple[float, float, float]:
        if self.iso_home is None:
            return p_home, p_draw, p_away

        arr_h = np.atleast_1d(np.array([p_home]))
        arr_d = np.atleast_1d(np.array([p_draw]))
        arr_a = np.atleast_1d(np.array([p_away]))

        ch = float(np.clip(self.iso_home.predict(arr_h)[0], 0.01, 0.99))
        cd = float(np.clip(self.iso_draw.predict(arr_d)[0], 0.01, 0.99))
        ca = float(np.clip(self.iso_away.predict(arr_a)[0], 0.01, 0.99))

        # Re-normalise to sum to 1
        total = ch + cd + ca
        return ch / total, cd / total, ca / total


def build_calibrators_from_results(
    results_df: pd.DataFrame,
) -> tuple[TotalsCalibrator, H2HCalibrator]:
    """
    Build calibrators from a backtest results DataFrame.
    results_df must have: p_home, p_draw, p_away, p_over25, result, actual_over25
    """
    tc = TotalsCalibrator()
    tc.fit(
        p_model=results_df["model_p_over25"].values,
        y_actual=results_df["actual_over25"].values,
    )

    hc = H2HCalibrator()
    hc.fit(
        p_home=results_df["p_home"].values,
        p_draw=results_df["p_draw"].values,
        p_away=results_df["p_away"].values,
        results=results_df["result"].values,
    )
    return tc, hc


def calibrate_and_report(
    results_df: pd.DataFrame,
    train_seasons: list[str],
    test_season: str,
) -> pd.DataFrame:
    """
    Fit calibrators on train_seasons, apply to test_season rows.
    Returns results_df with additional calibrated probability columns.
    """
    train = results_df[results_df["season"].isin(train_seasons)].copy()
    test  = results_df[results_df["season"] == test_season].copy()

    if train.empty or test.empty:
        return results_df

    # Totals calibration
    tc = TotalsCalibrator()
    tc.fit(
        p_model=train["p_over25"].values,
        y_actual=train["actual_over25"].values,
    )
    test["p_over25_cal"]  = tc.transform(test["p_over25"].values)
    test["p_under25_cal"] = 1.0 - test["p_over25_cal"]

    # H2H calibration
    hc = H2HCalibrator()
    hc.fit(
        p_home=train["p_home"].values,
        p_draw=train["p_draw"].values,
        p_away=train["p_away"].values,
        results=train["result"].values,
    )
    cal_probs = [hc.transform(r["p_home"], r["p_draw"], r["p_away"])
                 for _, r in test.iterrows()]
    test["p_home_cal"] = [p[0] for p in cal_probs]
    test["p_draw_cal"] = [p[1] for p in cal_probs]
    test["p_away_cal"] = [p[2] for p in cal_probs]

    return test


def fit_and_save(
    results_csv: Path,
    out_path: Path,
) -> None:
    """
    Fit calibrators on 2021/22 + 2022/23, validate on 2023/24.
    Saves a JSON calibration report with before/after RPS.
    """
    from ml.epl.backtest.walk_forward import rps as rps_fn

    df = pd.read_csv(results_csv)
    print(f"Loaded {len(df)} backtest rows across seasons: {df['season'].unique()}")

    seasons = sorted(df["season"].unique())
    results = []

    for i, test_s in enumerate(seasons):
        train_seasons = [s for s in seasons if s != test_s]
        train = df[df["season"].isin(train_seasons)]
        test  = df[df["season"] == test_s].copy()

        if len(train) < 100 or len(test) < 100:
            continue

        # --- Totals calibration ---
        tc = TotalsCalibrator()
        tc.fit(train["p_over25"].values, train["actual_over25"].values)
        test["p_over25_cal"] = tc.transform(test["p_over25"].values)

        # --- H2H calibration ---
        hc = H2HCalibrator()
        hc.fit(train["p_home"].values, train["p_draw"].values,
               train["p_away"].values, train["result"].values)
        cal_h2h = np.array([hc.transform(r["p_home"], r["p_draw"], r["p_away"])
                            for _, r in test.iterrows()])
        test["p_home_cal"] = cal_h2h[:, 0]
        test["p_draw_cal"] = cal_h2h[:, 1]
        test["p_away_cal"] = cal_h2h[:, 2]

        # --- RPS before/after ---
        rps_before = np.mean([rps_fn(r["p_home"], r["p_draw"], r["p_away"], r["result"])
                              for _, r in test.iterrows()])
        rps_after  = np.mean([rps_fn(r["p_home_cal"], r["p_draw_cal"], r["p_away_cal"], r["result"])
                              for _, r in test.iterrows()])

        actual_over = (test["actual_over25"] == 1).mean()
        raw_over    = test["p_over25"].mean()
        cal_over    = test["p_over25_cal"].mean()

        print(f"\n{test_s}:")
        print(f"  RPS:        {rps_before:.4f} → {rps_after:.4f}  ({(rps_after-rps_before)*1000:+.1f}mRPS)")
        print(f"  P(over25):  raw={raw_over:.3f}  cal={cal_over:.3f}  actual={actual_over:.3f}")

        results.append({
            "season": test_s,
            "rps_before": round(rps_before, 4),
            "rps_after":  round(rps_after, 4),
            "p_over25_raw": round(raw_over, 3),
            "p_over25_cal": round(cal_over, 3),
            "p_over25_actual": round(actual_over, 3),
        })

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved calibration report to {out_path}")


if __name__ == "__main__":
    results_csv = Path(__file__).parent.parent / "data" / "clv" / "backtest_results.csv"
    out_path    = Path(__file__).parent.parent / "data" / "clv" / "calibration_report.json"
    fit_and_save(results_csv, out_path)
