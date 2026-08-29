from scripts.nrl_ht_margin_v3 import MAX_PROCESS_ADJUSTMENT, estimate_margin


def base_stats():
    return {"home_ht_score": 8, "away_ht_score": 8}


def test_missing_process_stats_uses_only_margin_baseline():
    result = estimate_margin(base_stats(), 4.0)
    assert result.baseline_expected_margin == 2.0
    assert result.process_adjustment == 0
    assert result.quality == "baseline_only"


def test_current_score_is_preserved_and_only_remaining_strength_is_added():
    stats = {"home_ht_score": 0, "away_ht_score": 8, "snapshot_game_seconds": 2400}
    result = estimate_margin(stats, -5.3)
    assert result.expected_remaining_pregame_margin == -2.65
    assert result.baseline_expected_margin == -10.65


def test_home_process_dominance_improves_home_margin_and_h2h():
    home_good = {**base_stats(), "home_errors": 2, "away_errors": 7,
                 "home_completion_pct": 85, "away_completion_pct": 69,
                 "home_line_breaks": 5, "away_line_breaks": 1,
                 "home_run_metres": 950, "away_run_metres": 650,
                 "home_missed_tackles": 10, "away_missed_tackles": 25}
    away_good = {**base_stats(), "home_errors": 7, "away_errors": 2,
                 "home_completion_pct": 69, "away_completion_pct": 85,
                 "home_line_breaks": 1, "away_line_breaks": 5,
                 "home_run_metres": 650, "away_run_metres": 950,
                 "home_missed_tackles": 25, "away_missed_tackles": 10}
    h = estimate_margin(home_good, 0)
    a = estimate_margin(away_good, 0)
    assert h.expected_final_margin > a.expected_final_margin
    assert h.home_win_probability > a.home_win_probability


def test_h2h_and_handicap_share_one_distribution():
    result = estimate_margin(base_stats(), 3.0)
    assert result.fair_home_handicap == round(-result.median_final_margin, 1)
    assert abs(result.home_win_probability + result.away_win_probability - 1) < .001
    assert result.home_fair_odds == round(1 / result.home_win_probability, 2)


def test_process_adjustment_is_capped():
    stats = {**base_stats(), "home_errors": 0, "away_errors": 100,
             "home_completion_pct": 100, "away_completion_pct": 0,
             "home_line_breaks": 100, "away_line_breaks": 0,
             "home_run_metres": 10000, "away_run_metres": 0,
             "home_missed_tackles": 0, "away_missed_tackles": 100}
    assert abs(estimate_margin(stats, 0).process_adjustment) <= MAX_PROCESS_ADJUSTMENT
