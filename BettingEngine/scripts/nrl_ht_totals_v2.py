"""NRL halftime totals model v2.

The historical component is fitted on the checked-in 2022-2025 halftime
dataset. Live process coefficients are deliberately conservative and capped:
the archive has no historical deep-stat coverage yet, so they are shadow
weights to be recalibrated as forward observations mature.
"""
from __future__ import annotations

import math
import csv
from functools import lru_cache
from dataclasses import asdict, dataclass
from pathlib import Path

# 2022-2025 ridge fit: target = second-half points, n=637.
HIST_INTERCEPT = 29.1543
HIST_HT_TOTAL_COEF = -0.25668
HIST_ABS_MARGIN_COEF = 0.01076
H2_SHARE_OF_PREGAME = 0.53
PREGAME_PRIOR_WEIGHT = 0.40
RESIDUAL_SD = 11.4
MAX_PROCESS_ADJUSTMENT = 4.0
EMPIRICAL_BANDWIDTH = 2.0
HISTORY_PATH = Path(__file__).resolve().parents[1] / "data" / "inplay" / "nrl" / "halftime" / "processed" / "halftime_dataset.csv"


@lru_cache(maxsize=1)
def _history() -> tuple[tuple[float, float], ...]:
    rows: list[tuple[float, float]] = []
    try:
        with HISTORY_PATH.open(newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                try:
                    if int(float(row.get("year") or 9999)) > 2025:
                        continue
                    ht = float(row["ht_total_score"])
                    ft = float(row["ft_total"])
                    if ht >= 0 and ft >= ht:
                        rows.append((ht, ft - ht))
                except (KeyError, TypeError, ValueError):
                    continue
    except (OSError, KeyError, TypeError, ValueError):
        return ()
    return tuple(rows)


def _conditional_h2(first_half_total: float) -> tuple[float, ...]:
    history = _history()
    for radius in (2, 4, 6, 10, 999):
        sample = tuple(h2 for ht, h2 in history if abs(ht - first_half_total) <= radius)
        if len(sample) >= 40:
            return sample
    return ()


def _smoothed_over(sample: tuple[float, ...], threshold: float, shift: float) -> float:
    if not sample:
        return 0.5
    denom = EMPIRICAL_BANDWIDTH * math.sqrt(2.0)
    return sum(0.5 * math.erfc((threshold - (value + shift)) / denom) for value in sample) / len(sample)


def _fair_threshold(sample: tuple[float, ...], shift: float) -> float:
    if not sample:
        return 0.0
    lo, hi = min(sample) + shift - 10, max(sample) + shift + 10
    for _ in range(60):
        mid = (lo + hi) / 2
        if _smoothed_over(sample, mid, shift) > 0.5:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def _number(stats: dict, key: str) -> float | None:
    value = stats.get(key)
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


@dataclass(frozen=True)
class TotalsEstimate:
    model_version: str
    first_half_total: float
    historical_h2_baseline: float
    pregame_h2_prior: float
    blended_h2_baseline: float
    process_adjustment: float
    expected_second_half_total: float
    expected_final_total: float
    fair_final_total: float
    residual_sd: float
    distribution_sample_size: int
    distribution_shift: float
    feature_coverage: float
    quality: str
    adjustments: list[str]

    def probability_over(self, line: float) -> float:
        sample = _conditional_h2(self.first_half_total)
        if sample:
            threshold = line - self.first_half_total
            return _smoothed_over(sample, threshold, self.distribution_shift)
        z = (line - self.fair_final_total) / self.residual_sd
        return 0.5 * math.erfc(z / math.sqrt(2.0))

    def market(self, line: float) -> dict:
        p_over = self.probability_over(line)
        p_under = 1.0 - p_over
        return {
            "line": line,
            "over_probability": round(p_over, 4),
            "under_probability": round(p_under, 4),
            "fair_over_odds": round(1 / p_over, 2),
            "fair_under_odds": round(1 / p_under, 2),
        }

    def to_dict(self) -> dict:
        return asdict(self)


def estimate_totals(stats: dict, pregame_total: float | None) -> TotalsEstimate:
    home = float(stats["home_ht_score"])
    away = float(stats["away_ht_score"])
    ht_total = home + away
    abs_margin = abs(home - away)

    historical = (
        HIST_INTERCEPT
        + HIST_HT_TOTAL_COEF * ht_total
        + HIST_ABS_MARGIN_COEF * abs_margin
    )
    if pregame_total and pregame_total > 0:
        pregame_h2 = pregame_total * H2_SHARE_OF_PREGAME
        blended = PREGAME_PRIOR_WEIGHT * pregame_h2 + (1 - PREGAME_PRIOR_WEIGHT) * historical
    else:
        pregame_h2 = historical
        blended = historical

    adjustments: list[str] = []
    raw_adjustment = 0.0
    available = 0
    expected = 4

    # Combined metres are a pace proxy. Around 1,600m is a neutral NRL half.
    hm = _number(stats, "home_run_metres")
    am = _number(stats, "away_run_metres")
    if hm is not None and am is not None and hm + am > 0:
        available += 1
        adj = max(-1.5, min(1.5, ((hm + am) - 1600.0) / 250.0))
        raw_adjustment += adj
        adjustments.append(f"combined run metres {hm + am:.0f}: {adj:+.2f}")

    # Completion reflects whether possessions are becoming genuine attacking
    # sets. Keep the weight small because low completion can regress or persist.
    hc = _number(stats, "home_completion_pct")
    ac = _number(stats, "away_completion_pct")
    if hc is not None and ac is not None and hc + ac > 0:
        available += 1
        avg_completion = (hc + ac) / 2
        adj = max(-1.25, min(1.25, (avg_completion - 76.0) * 0.12))
        raw_adjustment += adj
        adjustments.append(f"average completion {avg_completion:.1f}%: {adj:+.2f}")

    # Repeat sets are direct additional attacking opportunities. Centre at four
    # combined per half and use only a fraction of published possession EPV.
    hr = _number(stats, "home_set_restarts_received")
    ar = _number(stats, "away_set_restarts_received")
    if hr is not None and ar is not None:
        available += 1
        adj = max(-1.25, min(1.25, ((hr + ar) - 4.0) * 0.22))
        raw_adjustment += adj
        adjustments.append(f"combined set restarts {hr + ar:.0f}: {adj:+.2f}")

    # Inside-20 counts are the preferred territory signal. Zero/zero is treated
    # as unavailable because the current NRL feed/parser often omits the stat.
    hi = _number(stats, "home_inside_20_possessions")
    ai = _number(stats, "away_inside_20_possessions")
    if hi is not None and ai is not None and hi + ai > 0:
        available += 1
        adj = max(-2.0, min(2.0, ((hi + ai) - 8.0) * 0.25))
        raw_adjustment += adj
        adjustments.append(f"combined inside-20 possessions {hi + ai:.0f}: {adj:+.2f}")

    coverage = available / expected
    # Reliability shrinkage prevents sparse snapshots receiving full weight.
    process = max(-MAX_PROCESS_ADJUSTMENT, min(MAX_PROCESS_ADJUSTMENT, raw_adjustment * coverage))
    h2 = max(8.0, min(45.0, blended + process))
    sample = _conditional_h2(ht_total)
    if sample:
        sample_mean = sum(sample) / len(sample)
        distribution_shift = h2 - sample_mean
        fair_h2 = _fair_threshold(sample, distribution_shift)
    else:
        distribution_shift = 0.0
        fair_h2 = h2
    quality = "full" if coverage >= 0.75 else "partial" if coverage > 0 else "baseline_only"
    return TotalsEstimate(
        model_version="nrl_ht_totals_v2_empirical_distribution",
        first_half_total=round(ht_total, 1),
        historical_h2_baseline=round(historical, 2),
        pregame_h2_prior=round(pregame_h2, 2),
        blended_h2_baseline=round(blended, 2),
        process_adjustment=round(process, 2),
        expected_second_half_total=round(h2, 2),
        expected_final_total=round(ht_total + h2, 2),
        fair_final_total=round(ht_total + fair_h2, 2),
        residual_sd=RESIDUAL_SD,
        distribution_sample_size=len(sample),
        distribution_shift=round(distribution_shift, 4),
        feature_coverage=round(coverage, 2),
        quality=quality,
        adjustments=adjustments,
    )
