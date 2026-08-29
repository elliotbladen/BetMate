from scripts.afl_ht_totals_v3 import MAX_PROCESS_ADJUSTMENT, estimate_totals
from scripts.afl_ht_live import extract_halftime_stats


def base_stats():
    return {"home_ht_score": 44, "away_ht_score": 40,
            "home_goals": 6, "home_behinds": 8,
            "away_goals": 6, "away_behinds": 4}


def test_bins_remain_the_score_state_baseline():
    result = estimate_totals(base_stats(), None)
    assert result.score_state_h2_baseline == 85


def test_pregame_total_is_retained_as_a_conservative_prior():
    low = estimate_totals(base_stats(), 150)
    high = estimate_totals(base_stats(), 200)
    assert high.expected_final_total > low.expected_final_total


def test_pace_and_opportunity_raise_total():
    high = {**base_stats(), "home_inside_50s": 32, "away_inside_50s": 31,
            "home_clearances": 21, "away_clearances": 20}
    low = {**base_stats(), "home_inside_50s": 20, "away_inside_50s": 19,
           "home_clearances": 14, "away_clearances": 13,
           "home_goals": 8, "home_behinds": 2, "away_goals": 7, "away_behinds": 2}
    assert estimate_totals(high, 170).expected_final_total > estimate_totals(low, 170).expected_final_total


def test_injury_adjustment_is_applied_once():
    normal = estimate_totals(base_stats(), 170, 0)
    injured = estimate_totals(base_stats(), 170, -3)
    assert injured.expected_final_total == normal.expected_final_total - 3


def test_empirical_fair_line_and_probability_are_available():
    result = estimate_totals(base_stats(), 170)
    assert result.distribution_sample_size >= 50
    market = result.market(result.fair_final_total)
    assert abs(market["over_probability"] - .5) < .01


def test_process_adjustment_is_capped():
    extreme = {**base_stats(), "home_inside_50s": 200, "away_inside_50s": 200,
               "home_clearances": 200, "away_clearances": 200,
               "home_goals": 0, "home_behinds": 100, "away_goals": 0, "away_behinds": 100}
    assert abs(estimate_totals(extreme, 170).process_adjustment) <= MAX_PROCESS_ADJUSTMENT


def test_live_contract_carries_fox_match_id_for_injury_pricing():
    game = {"hteam": "Home", "ateam": "Away", "hgoals": 5, "hbehinds": 5,
            "agoals": 4, "abehinds": 4, "date": "2026-08-15 10:00:00",
            "_round_game_num": 3, "fox_match_id": "AFL20262303"}
    stats = extract_halftime_stats(game, 2026, 23)
    assert stats["fox_match_id"] == "AFL20262303"
