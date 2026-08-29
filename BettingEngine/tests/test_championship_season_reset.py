from datetime import datetime

import pandas as pd

from ml.football.price_match import _reset_new_team_dc_ratings, fmt_clv


def test_returning_team_old_rating_is_reset_to_neutral():
    df = pd.DataFrame({"Season": ["2025/26"], "HomeTeam": ["Blackburn"], "AwayTeam": ["Preston"]})
    ratings = {"attack": {"Wolves": 1.4}, "defence": {"Wolves": .7}, "home_adv": {"Wolves": 1.3}}
    got = _reset_new_team_dc_ratings(ratings, df, ["Wolves"], datetime(2026, 8, 14))
    assert got["attack"]["Wolves"] == got["defence"]["Wolves"] == got["home_adv"]["Wolves"] == 1.0


def test_value_label_requires_market_price_longer_than_model_price():
    assert "VALUE" in fmt_clv(2.0, 2.2)
    assert "VALUE" not in fmt_clv(2.2, 2.0)
