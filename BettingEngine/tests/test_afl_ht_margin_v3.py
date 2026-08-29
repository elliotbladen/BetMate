from scripts.halfTime_price_afl import (
    AFL_H2_MARGIN_RESIDUAL_SD,
    REMAINING_MARGIN_SHARE_AT_HT,
    margin_win_prob,
    price_halftime,
)


def stats(home=50, away=60):
    return {"home_team": "Home", "away_team": "Away", "season": 2026,
            "round": 1, "home_goals": 7, "home_behinds": 8,
            "away_goals": 9, "away_behinds": 6,
            "home_ht_score": home, "away_ht_score": away}


def test_scoreboard_is_preserved_and_only_remaining_strength_is_added():
    result = price_halftime(stats(), {"rules_margin": 20, "rules_total": 170})
    assert result.expected_remaining_pregame_margin == round(20 * REMAINING_MARGIN_SHARE_AT_HT, 2)
    assert result.ht_expected_margin == round(-10 + 20 * REMAINING_MARGIN_SHARE_AT_HT, 2)


def test_h2h_probability_uses_calibrated_margin_uncertainty():
    result = margin_win_prob(0)
    assert abs(result["home_win"] - result["away_win"]) < .001
    assert AFL_H2_MARGIN_RESIDUAL_SD > 20


def test_accuracy_does_not_project_unvalidated_first_half_trend():
    result = price_halftime(stats(), {"rules_margin": 0, "rules_total": 170})
    assert result.accuracy_adjustment == 0
