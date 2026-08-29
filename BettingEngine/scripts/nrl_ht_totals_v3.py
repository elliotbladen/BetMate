"""NRL halftime totals v3: empirical score-state distribution + process layers.

The score-state distribution and pre-game prior are historically grounded.
Deep-stat coefficients are conservative forward-calibration weights because the
checked-in historical archive contains no deep halftime stats. Missing fields
are ignored, group adjustments are averaged to avoid double counting, and the
entire live adjustment is reliability-shrunk and capped.
"""
from __future__ import annotations

import csv
import math
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path

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
    except OSError:
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
    return sum(0.5 * math.erfc((threshold - value - shift) / denom) for value in sample) / len(sample)


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


def _combined(stats: dict, stem: str, *, positive: bool = False) -> float | None:
    home, away = _number(stats, f"home_{stem}"), _number(stats, f"away_{stem}")
    if home is None or away is None:
        return None
    total = home + away
    return total if not positive or total > 0 else None


def _clamp(value: float, limit: float) -> float:
    return max(-limit, min(limit, value))


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
            return _smoothed_over(sample, line - self.first_half_total, self.distribution_shift)
        z = (line - self.fair_final_total) / self.residual_sd
        return 0.5 * math.erfc(z / math.sqrt(2.0))

    def market(self, line: float) -> dict:
        over = self.probability_over(line)
        under = 1.0 - over
        return {"line": line, "over_probability": round(over, 4),
                "under_probability": round(under, 4), "fair_over_odds": round(1 / over, 2),
                "fair_under_odds": round(1 / under, 2)}

    def to_dict(self) -> dict:
        return asdict(self)


def estimate_totals(stats: dict, pregame_total: float | None, injury_total_adjustment: float = 0.0) -> TotalsEstimate:
    home, away = float(stats["home_ht_score"]), float(stats["away_ht_score"])
    ht_total, abs_margin = home + away, abs(home - away)
    historical = HIST_INTERCEPT + HIST_HT_TOTAL_COEF * ht_total + HIST_ABS_MARGIN_COEF * abs_margin
    if pregame_total and pregame_total > 0:
        pregame_h2 = pregame_total * H2_SHARE_OF_PREGAME
        blended = PREGAME_PRIOR_WEIGHT * pregame_h2 + (1 - PREGAME_PRIOR_WEIGHT) * historical
    else:
        pregame_h2 = blended = historical

    groups: list[tuple[str, float]] = []
    notes: list[str] = []

    # Pace: average correlated proxies so metres, runs and sets cannot be
    # counted as three independent possessions signals.
    pace: list[float] = []
    for stem, neutral, scale, cap in (("total_sets", 38, 4, 1.5),
                                      ("all_runs", 170, 22, 1.5),
                                      ("run_metres", 1600, 250, 1.5),
                                      ("play_the_balls", 150, 20, 1.5)):
        value = _combined(stats, stem, positive=True)
        if value is not None:
            pace.append(_clamp((value - neutral) / scale, cap))
    if pace:
        adj = sum(pace) / len(pace)
        groups.append(("pace", adj)); notes.append(f"pace ({len(pace)} proxies): {adj:+.2f}")

    # Attacking opportunity: possession value rises materially near the try
    # line. Exact field coordinates are unavailable, so these are transparent
    # proxies rather than a claimed xPoints feed.
    opportunity: list[float] = []
    for stem, neutral, weight, cap in (("inside_20_possessions", 8, .25, 2.0),
                                       ("line_breaks", 4, .35, 1.5),
                                       ("forced_dropouts", 2, .30, 1.2),
                                       ("set_restarts_received", 4, .18, 1.0)):
        value = _combined(stats, stem, positive=stem == "inside_20_possessions")
        if value is not None:
            opportunity.append(_clamp((value - neutral) * weight, cap))
    if opportunity:
        adj = sum(opportunity) / len(opportunity)
        groups.append(("opportunity", adj)); notes.append(f"opportunity ({len(opportunity)} proxies): {adj:+.2f}")

    completion = _combined(stats, "completion_pct", positive=True)
    if completion is not None:
        adj = _clamp((completion / 2 - 76) * .10, 1.25)
        groups.append(("execution", adj)); notes.append(f"average completion {completion / 2:.1f}%: {adj:+.2f}")

    # Defensive stress is directionally useful for later scoring, but receives
    # only a small capped weight pending forward calibration.
    missed = _combined(stats, "missed_tackles")
    if missed is not None:
        adj = _clamp((missed - 36) * .035, .8)
        groups.append(("defensive_stress", adj)); notes.append(f"combined missed tackles {missed:.0f}: {adj:+.2f}")

    coverage = len(groups) / 4
    raw = sum(value for _, value in groups)
    process = _clamp(raw * coverage, MAX_PROCESS_ADJUSTMENT)
    injury = _clamp(float(injury_total_adjustment or 0), 5.0)
    h2 = max(8.0, min(45.0, blended + process + injury))
    sample = _conditional_h2(ht_total)
    if sample:
        shift = h2 - sum(sample) / len(sample)
        fair_h2 = _fair_threshold(sample, shift)
    else:
        shift, fair_h2 = 0.0, h2
    quality = "full_forward_calibration" if coverage >= .75 else "partial_forward_calibration" if coverage else "baseline_only"
    return TotalsEstimate(
        model_version="nrl_ht_totals_v3_process_distribution",
        first_half_total=round(ht_total, 1), historical_h2_baseline=round(historical, 2),
        pregame_h2_prior=round(pregame_h2, 2), blended_h2_baseline=round(blended, 2),
        process_adjustment=round(process, 2), expected_second_half_total=round(h2, 2),
        expected_final_total=round(ht_total + h2, 2), fair_final_total=round(ht_total + fair_h2, 2),
        residual_sd=RESIDUAL_SD, distribution_sample_size=len(sample), distribution_shift=round(shift, 4),
        feature_coverage=round(coverage, 2), quality=quality, adjustments=notes,
    )
