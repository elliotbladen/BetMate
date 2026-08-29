from scripts.nrl_ht_totals_v2 import estimate_totals


def test_process_stats_change_same_score_total():
    base = {"home_ht_score": 4, "away_ht_score": 6}
    fast = {
        **base,
        "home_run_metres": 900,
        "away_run_metres": 900,
        "home_completion_pct": 82,
        "away_completion_pct": 82,
        "home_set_restarts_received": 4,
        "away_set_restarts_received": 4,
        "home_inside_20_possessions": 6,
        "away_inside_20_possessions": 6,
    }
    slow = {
        **base,
        "home_run_metres": 650,
        "away_run_metres": 650,
        "home_completion_pct": 68,
        "away_completion_pct": 68,
        "home_set_restarts_received": 1,
        "away_set_restarts_received": 1,
        "home_inside_20_possessions": 2,
        "away_inside_20_possessions": 2,
    }
    assert estimate_totals(fast, 46).expected_final_total > estimate_totals(slow, 46).expected_final_total


def test_missing_zero_inside_20_is_not_treated_as_real_zero():
    stats = {
        "home_ht_score": 0,
        "away_ht_score": 8,
        "home_inside_20_possessions": 0,
        "away_inside_20_possessions": 0,
    }
    result = estimate_totals(stats, 50.1)
    assert result.quality == "baseline_only"
    assert result.process_adjustment == 0


def test_probability_and_fair_odds_are_coherent():
    result = estimate_totals({"home_ht_score": 8, "away_ht_score": 8}, 46)
    market = result.market(result.fair_final_total)
    assert abs(market["over_probability"] - 0.5) < 0.002
    assert abs(market["under_probability"] - 0.5) < 0.002
    assert abs(market["fair_over_odds"] - 2.0) < 0.02
    assert abs(market["fair_under_odds"] - 2.0) < 0.02


def test_right_skew_keeps_mean_separate_from_fair_line_for_low_half():
    result = estimate_totals({"home_ht_score": 0, "away_ht_score": 8}, 50.1)
    assert result.expected_final_total > result.fair_final_total
    assert result.distribution_sample_size >= 40


def test_process_adjustment_is_capped():
    extreme = {
        "home_ht_score": 0,
        "away_ht_score": 0,
        "home_run_metres": 5000,
        "away_run_metres": 5000,
        "home_completion_pct": 100,
        "away_completion_pct": 100,
        "home_set_restarts_received": 50,
        "away_set_restarts_received": 50,
        "home_inside_20_possessions": 50,
        "away_inside_20_possessions": 50,
    }
    assert estimate_totals(extreme, 46).process_adjustment == 4.0
