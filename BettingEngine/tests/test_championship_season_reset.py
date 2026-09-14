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


def _season_frame(rounds: int = 6):
    """A synthetic 2026/27 season. Wolves score freely; Bolton concede freely.

    dc_fit needs 50 matches before it will fit at all, so the frame carries
    `rounds` x 10 fixtures — mirroring a real Championship round of 12.
    """
    rows = [{"Season": "2025/26", "Date": datetime(2026, 3, 1),
             "HomeTeam": "Blackburn", "AwayTeam": "Preston",
             "home_xg": 1.0, "away_xg": 1.0}]
    filler = ["Preston", "Blackburn", "Derby", "Norwich", "Stoke", "Swansea",
              "Watford", "QPR", "Millwall", "Cardiff", "Hull", "Coventry",
              "Luton", "Oxford", "Portsmouth", "Sunderland"]
    for r in range(rounds):
        day = datetime(2026, 8, 8 + r * 3)
        rows.append({"Season": "2026/27", "Date": day,
                     "HomeTeam": "Wolves", "AwayTeam": filler[r % len(filler)],
                     "home_xg": 3.0, "away_xg": 0.0})
        rows.append({"Season": "2026/27", "Date": day,
                     "HomeTeam": "Bolton", "AwayTeam": filler[(r + 1) % len(filler)],
                     "home_xg": 0.0, "away_xg": 3.0})
        for i in range(0, len(filler) - 1, 2):
            rows.append({"Season": "2026/27", "Date": day,
                         "HomeTeam": filler[i], "AwayTeam": filler[i + 1],
                         "home_xg": 1.3, "away_xg": 1.1})
    return pd.DataFrame(rows)


def _ratings_stub():
    return {"attack": {"Wolves": 1.4}, "defence": {"Wolves": .7}, "home_adv": {"Wolves": 1.3}}


def test_shrunk_mode_keeps_current_season_evidence():
    df = _season_frame()
    got = _reset_new_team_dc_ratings(_ratings_stub(), df, ["Wolves"], datetime(2026, 9, 11),
                                     mode="shrunk_current_season", shrink_games=6.0)
    # Wolves scored heavily all season, so attack must land above league average —
    # the whole point of the mode. The flat reset would have returned exactly 1.0.
    assert got["new_team_reset_mode"] == "shrunk_current_season"
    assert got["attack"]["Wolves"] > 1.0
    # Six games against a prior of six => the current-season fit carries half the weight.
    assert got["reset_override"]["Wolves"]["games"] == 6
    assert got["reset_override"]["Wolves"]["weight"] == 0.5
    # home_adv has no per-team estimate from three home games and stays neutral.
    assert got["home_adv"]["Wolves"] == 1.0


def test_shrunk_mode_falls_back_before_the_season_starts():
    """August, before a ball is kicked: nothing to fit, so stay at league average."""
    df = _season_frame()
    df = df[df["Season"] == "2025/26"]
    got = _reset_new_team_dc_ratings(_ratings_stub(), df, ["Wolves"], datetime(2026, 8, 1),
                                     mode="shrunk_current_season")
    assert got["attack"]["Wolves"] == 1.0
    assert got["new_team_reset_mode"] == "league_average"


def test_shrunk_mode_falls_back_until_the_season_can_be_fitted():
    """Under dc_fit's 50-match floor (~round 5) the mode is silently inactive.

    This is a real limitation, not a quirk: for the opening month of a season the
    engine still rates promoted and relegated clubs at exactly league average.
    """
    df = _season_frame(rounds=2)          # 10 current-season matches, well under 50
    got = _reset_new_team_dc_ratings(_ratings_stub(), df, ["Wolves"], datetime(2026, 8, 20),
                                     mode="shrunk_current_season")
    assert got["attack"]["Wolves"] == 1.0
    assert got["new_team_reset_mode"] == "league_average"
