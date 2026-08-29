"""Coherent NRL halftime margin engine for both H2H and handicap.

One predictive final-margin distribution is produced. Handicap is its median
with betting sign convention; H2H is the probability mass either side of zero.
Deep-stat weights are conservative forward-calibration priors because the
historical halftime archive does not contain those fields.
"""
from __future__ import annotations

import csv
import math
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path

MAX_PROCESS_ADJUSTMENT = 5.0
EMPIRICAL_BANDWIDTH = 1.5
HISTORY_PATH = Path(__file__).resolve().parents[1] / "data" / "inplay" / "nrl" / "halftime" / "processed" / "halftime_dataset.csv"


def _number(stats: dict, key: str) -> float | None:
    value = stats.get(key)
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _diff(stats: dict, stem: str, *, away_is_bad: bool = False) -> float | None:
    home, away = _number(stats, f"home_{stem}"), _number(stats, f"away_{stem}")
    if home is None or away is None:
        return None
    return away - home if away_is_bad else home - away


def _clamp(value: float, limit: float) -> float:
    return max(-limit, min(limit, value))


@lru_cache(maxsize=1)
def _history() -> tuple[tuple[float, float, float], ...]:
    rows: list[tuple[float, float, float]] = []
    try:
        with HISTORY_PATH.open(newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                try:
                    ht_margin = float(row["ht_home_score"]) - float(row["ht_away_score"])
                    ht_total = float(row["ht_total_score"])
                    ft_margin = float(row["ft_home_score"]) - float(row["ft_away_score"])
                    rows.append((ht_margin, ht_total, ft_margin - ht_margin))
                except (KeyError, TypeError, ValueError):
                    continue
    except OSError:
        return ()
    return tuple(rows)


def _conditional_h2_margin(ht_margin: float, ht_total: float) -> tuple[float, ...]:
    history = _history()
    for margin_radius, total_radius in ((3, 5), (6, 8), (10, 12), (999, 999)):
        sample = tuple(h2 for margin, total, h2 in history
                       if abs(margin - ht_margin) <= margin_radius and abs(total - ht_total) <= total_radius)
        if len(sample) >= 40:
            return sample
    return ()


def _smoothed_cdf(sample: tuple[float, ...], threshold: float, shift: float) -> float:
    denom = EMPIRICAL_BANDWIDTH * math.sqrt(2)
    return sum(0.5 * math.erfc(((value + shift) - threshold) / denom) for value in sample) / len(sample)


def _quantile(sample: tuple[float, ...], shift: float, probability: float) -> float:
    lo, hi = min(sample) + shift - 10, max(sample) + shift + 10
    for _ in range(60):
        mid = (lo + hi) / 2
        if _smoothed_cdf(sample, mid, shift) < probability:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


@dataclass(frozen=True)
class MarginEstimate:
    model_version: str
    elapsed_game_fraction: float
    expected_remaining_pregame_margin: float
    baseline_expected_margin: float
    process_adjustment: float
    expected_final_margin: float
    median_final_margin: float
    fair_home_handicap: float
    home_win_probability: float
    away_win_probability: float
    draw_probability: float
    home_fair_odds: float
    away_fair_odds: float
    distribution_sample_size: int
    feature_coverage: float
    quality: str
    adjustments: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def estimate_margin(stats: dict, pregame_margin: float) -> MarginEstimate:
    home_score = float(stats["home_ht_score"])
    away_score = float(stats["away_ht_score"])
    ht_margin, ht_total = home_score - away_score, home_score + away_score
    # Points already scored cannot regress away. Pregame margin describes the
    # expected full-game scoring differential, so only its time-proportional
    # remaining component is added to the current scoreboard margin.
    elapsed_seconds = _number(stats, "snapshot_game_seconds")
    if elapsed_seconds is None:
        elapsed_seconds = 2400.0
    elapsed_fraction = max(0.0, min(1.0, elapsed_seconds / 4800.0))
    expected_remaining_pregame = pregame_margin * (1.0 - elapsed_fraction)
    baseline = ht_margin + expected_remaining_pregame

    groups: list[tuple[str, float]] = []
    notes: list[str] = []

    execution: list[float] = []
    error_diff = _diff(stats, "errors", away_is_bad=True)
    if error_diff is not None:
        execution.append(_clamp(error_diff * .45, 1.8))
    completion_diff = _diff(stats, "completion_pct")
    if completion_diff is not None:
        execution.append(_clamp(completion_diff * .07, 1.4))
    if execution:
        adj = sum(execution) / len(execution)
        groups.append(("execution", adj)); notes.append(f"execution ({len(execution)} proxies): {adj:+.2f}")

    opportunity: list[float] = []
    for stem, weight, cap in (("inside_20_possessions", .30, 1.8),
                              ("line_breaks", .45, 1.8),
                              ("forced_dropouts", .30, 1.2),
                              ("set_restarts_received", .20, 1.0)):
        value = _diff(stats, stem)
        if value is not None and not (stem == "inside_20_possessions" and
                                      _number(stats, "home_inside_20_possessions") == 0 and
                                      _number(stats, "away_inside_20_possessions") == 0):
            opportunity.append(_clamp(value * weight, cap))
    if opportunity:
        adj = sum(opportunity) / len(opportunity)
        groups.append(("opportunity", adj)); notes.append(f"opportunity ({len(opportunity)} proxies): {adj:+.2f}")

    physical: list[float] = []
    for stem, divisor, cap, bad in (("run_metres", 220, 1.4, False),
                                    ("tackle_breaks", 3, 1.2, False),
                                    ("missed_tackles", 7, 1.2, True)):
        value = _diff(stats, stem, away_is_bad=bad)
        if value is not None:
            physical.append(_clamp(value / divisor, cap))
    if physical:
        adj = sum(physical) / len(physical)
        groups.append(("physical", adj)); notes.append(f"physical/defensive ({len(physical)} proxies): {adj:+.2f}")

    # Correct first-half kicking variance toward a 75% conversion expectation.
    ht, at = _number(stats, "home_tries"), _number(stats, "away_tries")
    hc, ac = _number(stats, "home_conversions_made"), _number(stats, "away_conversions_made")
    if None not in (ht, at, hc, ac):
        kicking = _clamp(((ht * .75 - hc) - (at * .75 - ac)) * 2, 2.0)
        groups.append(("conversion_luck", kicking)); notes.append(f"conversion regression: {kicking:+.2f}")

    coverage = len(groups) / 4
    process = _clamp(sum(value for _, value in groups) * coverage, MAX_PROCESS_ADJUSTMENT)
    expected = baseline + process

    sample = _conditional_h2_margin(ht_margin, ht_total)
    if sample:
        target_h2_mean = expected - ht_margin
        shift = target_h2_mean - sum(sample) / len(sample)
        final_sample = tuple(ht_margin + value for value in sample)
        median = _quantile(final_sample, shift, .5)
        p_loss = _smoothed_cdf(final_sample, -0.5, shift)
        p_not_win = _smoothed_cdf(final_sample, 0.5, shift)
        p_draw = max(0.0, p_not_win - p_loss)
        p_home = max(0.001, 1 - p_not_win)
        p_away = max(0.001, p_loss)
    else:
        sd = 12.0
        median = expected
        p_away = 0.5 * math.erfc(expected / (sd * math.sqrt(2)))
        p_draw = 0.03
        p_home = max(.001, 1 - p_away - p_draw)
    # Conditional on a decisive H2H result; NRL regular-season draws are a
    # separate market outcome and are reported independently for audit.
    decisive = p_home + p_away
    h2h_home, h2h_away = p_home / decisive, p_away / decisive
    quality = "full_forward_calibration" if coverage >= .75 else "partial_forward_calibration" if coverage else "baseline_only"
    rounded_median = round(median, 2)
    return MarginEstimate(
        model_version="nrl_ht_margin_v3_remaining_margin_distribution",
        elapsed_game_fraction=round(elapsed_fraction, 4),
        expected_remaining_pregame_margin=round(expected_remaining_pregame, 2),
        baseline_expected_margin=round(baseline, 2), process_adjustment=round(process, 2),
        expected_final_margin=round(expected, 2), median_final_margin=rounded_median,
        fair_home_handicap=round(-rounded_median, 1), home_win_probability=round(h2h_home, 4),
        away_win_probability=round(h2h_away, 4), draw_probability=round(p_draw, 4),
        home_fair_odds=round(1 / h2h_home, 2), away_fair_odds=round(1 / h2h_away, 2),
        distribution_sample_size=len(sample), feature_coverage=round(coverage, 2),
        quality=quality, adjustments=notes,
    )
