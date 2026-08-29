from scripts.nrl_ht_totals_v3 import MAX_PROCESS_ADJUSTMENT, estimate_totals


def base_stats():
    return {"home_ht_score": 10, "away_ht_score": 8}


def test_missing_process_stats_uses_baseline_only():
    result = estimate_totals(base_stats(), 44.0)
    assert result.process_adjustment == 0
    assert result.feature_coverage == 0
    assert result.quality == "baseline_only"


def test_high_pace_and_opportunity_raise_total_relative_to_low_state():
    high = {**base_stats(), "home_total_sets": 22, "away_total_sets": 22,
            "home_run_metres": 950, "away_run_metres": 950,
            "home_line_breaks": 4, "away_line_breaks": 4,
            "home_forced_dropouts": 2, "away_forced_dropouts": 2,
            "home_completion_pct": 84, "away_completion_pct": 82,
            "home_missed_tackles": 24, "away_missed_tackles": 24}
    low = {**base_stats(), "home_total_sets": 16, "away_total_sets": 16,
           "home_run_metres": 650, "away_run_metres": 650,
           "home_line_breaks": 1, "away_line_breaks": 1,
           "home_forced_dropouts": 0, "away_forced_dropouts": 0,
           "home_completion_pct": 68, "away_completion_pct": 70,
           "home_missed_tackles": 12, "away_missed_tackles": 12}
    assert estimate_totals(high, 44).fair_final_total > estimate_totals(low, 44).fair_final_total


def test_zero_inside_20_is_missing_not_low_territory():
    stats = {**base_stats(), "home_inside_20_possessions": 0, "away_inside_20_possessions": 0}
    result = estimate_totals(stats, 44)
    assert result.feature_coverage == 0


def test_process_adjustment_is_capped():
    stats = {**base_stats(), "home_total_sets": 100, "away_total_sets": 100,
             "home_all_runs": 500, "away_all_runs": 500,
             "home_run_metres": 5000, "away_run_metres": 5000,
             "home_line_breaks": 50, "away_line_breaks": 50,
             "home_forced_dropouts": 30, "away_forced_dropouts": 30,
             "home_completion_pct": 100, "away_completion_pct": 100,
             "home_missed_tackles": 100, "away_missed_tackles": 100}
    assert estimate_totals(stats, 44).process_adjustment <= MAX_PROCESS_ADJUSTMENT


def test_fair_line_is_distribution_median_not_expected_mean():
    result = estimate_totals({"home_ht_score": 4, "away_ht_score": 4}, 44)
    assert result.distribution_sample_size >= 40
    assert result.fair_final_total != result.expected_final_total
