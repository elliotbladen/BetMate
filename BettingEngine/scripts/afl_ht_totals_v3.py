"""AFL halftime totals v3.

Keeps the validated five-bin score-state baseline, adds a conservative pregame
prior and capped live process evidence, then prices an empirical conditional
distribution. Deep-stat and pregame weights are forward-calibration priors until
the new snapshot archive is large enough for out-of-sample fitting.
"""
from __future__ import annotations

import csv
import math
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path

PREGAME_PRIOR_WEIGHT = 0.35
MAX_PROCESS_ADJUSTMENT = 4.0
EMPIRICAL_BANDWIDTH = 2.0
RESIDUAL_SD = 19.85
BASELINE_ACCURACY = 0.529
HISTORY_PATH = Path(__file__).resolve().parents[1] / "data" / "inplay" / "afl" / "halftime" / "processed" / "halftime_dataset.csv"


def _bin_h2(first_half_total: float) -> float:
    if first_half_total <= 60:
        return 82.0
    if first_half_total <= 75:
        return 83.0
    if first_half_total <= 88:
        return 85.0
    if first_half_total <= 100:
        return 86.0
    return 89.0


@lru_cache(maxsize=1)
def _history() -> tuple[tuple[float, float], ...]:
    rows: list[tuple[float, float]] = []
    try:
        with HISTORY_PATH.open(newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                try:
                    ht, ft = float(row["ht_total_score"]), float(row["ft_total"])
                    if ft >= ht:
                        rows.append((ht, ft - ht))
                except (KeyError, TypeError, ValueError):
                    continue
    except OSError:
        return ()
    return tuple(rows)


def _conditional_h2(ht_total: float) -> tuple[float, ...]:
    history = _history()
    for radius in (5, 8, 12, 999):
        sample = tuple(h2 for ht, h2 in history if abs(ht - ht_total) <= radius)
        if len(sample) >= 50:
            return sample
    return ()


def _smoothed_over(sample: tuple[float, ...], threshold: float, shift: float) -> float:
    denom = EMPIRICAL_BANDWIDTH * math.sqrt(2)
    return sum(0.5 * math.erfc((threshold - value - shift) / denom) for value in sample) / len(sample)


def _fair_threshold(sample: tuple[float, ...], shift: float) -> float:
    lo, hi = min(sample) + shift - 10, max(sample) + shift + 10
    for _ in range(60):
        mid = (lo + hi) / 2
        if _smoothed_over(sample, mid, shift) > .5:
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


def _combined(stats: dict, stem: str) -> float | None:
    home, away = _number(stats, f"home_{stem}"), _number(stats, f"away_{stem}")
    return None if home is None or away is None else home + away


def _clamp(value: float, limit: float) -> float:
    return max(-limit, min(limit, value))


@dataclass(frozen=True)
class TotalsEstimate:
    model_version: str
    first_half_total: float
    score_state_h2_baseline: float
    pregame_h2_prior: float
    blended_h2_baseline: float
    process_adjustment: float
    injury_adjustment: float
    expected_second_half_total: float
    expected_final_total: float
    fair_final_total: float
    distribution_sample_size: int
    distribution_shift: float
    residual_sd: float
    feature_coverage: float
    quality: str
    adjustments: list[str]

    def probability_over(self, line: float) -> float:
        sample = _conditional_h2(self.first_half_total)
        if sample:
            return _smoothed_over(sample, line - self.first_half_total, self.distribution_shift)
        z = (line - self.fair_final_total) / self.residual_sd
        return .5 * math.erfc(z / math.sqrt(2))

    def market(self, line: float) -> dict:
        over = self.probability_over(line); under = 1 - over
        return {"line": line, "over_probability": round(over, 4),
                "under_probability": round(under, 4), "fair_over_odds": round(1 / over, 2),
                "fair_under_odds": round(1 / under, 2)}

    def to_dict(self) -> dict:
        return asdict(self)


def estimate_totals(stats: dict, pregame_total: float | None, injury_total_adjustment: float = 0.0) -> TotalsEstimate:
    ht_total = float(stats["home_ht_score"]) + float(stats["away_ht_score"])
    score_baseline = _bin_h2(ht_total)
    if pregame_total and pregame_total > 0:
        pregame_h2 = pregame_total * .5
        blended = PREGAME_PRIOR_WEIGHT * pregame_h2 + (1 - PREGAME_PRIOR_WEIGHT) * score_baseline
    else:
        pregame_h2 = blended = score_baseline

    signals: list[float] = []
    notes: list[str] = []

    goals = (_number(stats, "home_goals") or 0) + (_number(stats, "away_goals") or 0)
    behinds = (_number(stats, "home_behinds") or 0) + (_number(stats, "away_behinds") or 0)
    shots = goals + behinds
    if shots > 0:
        expected_shots = ht_total / (1 + 5 * BASELINE_ACCURACY)
        adj = _clamp((shots - expected_shots) * .20, 1.0)
        signals.append(adj); notes.append(f"shot-volume pace {shots:.0f} vs {expected_shots:.1f}: {adj:+.2f}")

    inside50 = _combined(stats, "inside_50s")
    if inside50 is not None:
        adj = _clamp((inside50 - 50) * .08, 1.5)
        signals.append(adj); notes.append(f"combined inside-50s {inside50:.0f}: {adj:+.2f}")

    clearances = _combined(stats, "clearances")
    if clearances is not None:
        adj = _clamp((clearances - 35) * .05, .8)
        signals.append(adj); notes.append(f"combined clearances {clearances:.0f}: {adj:+.2f}")

    coverage = len(signals) / 3
    process = _clamp(sum(signals) * coverage, MAX_PROCESS_ADJUSTMENT)
    injury = _clamp(float(injury_total_adjustment or 0), 5.0)
    h2 = max(45.0, min(125.0, blended + process + injury))
    sample = _conditional_h2(ht_total)
    if sample:
        shift = h2 - sum(sample) / len(sample)
        fair_h2 = _fair_threshold(sample, shift)
    else:
        shift, fair_h2 = 0.0, h2
    quality = "full_forward_calibration" if coverage >= .99 else "partial_forward_calibration" if coverage else "baseline_only"
    return TotalsEstimate(
        model_version="afl_ht_totals_v3_score_state_distribution",
        first_half_total=round(ht_total, 1), score_state_h2_baseline=score_baseline,
        pregame_h2_prior=round(pregame_h2, 2), blended_h2_baseline=round(blended, 2),
        process_adjustment=round(process, 2), injury_adjustment=round(injury, 2),
        expected_second_half_total=round(h2, 2), expected_final_total=round(ht_total + h2, 2),
        fair_final_total=round(ht_total + fair_h2, 2), distribution_sample_size=len(sample),
        distribution_shift=round(shift, 4), residual_sd=RESIDUAL_SD,
        feature_coverage=round(coverage, 2), quality=quality, adjustments=notes,
    )
