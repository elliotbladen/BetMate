"""
ml/afl/features.py

SINGLE SOURCE OF TRUTH for AFL model feature columns.

Both ml/afl/train.py (training) and scripts/prepare_afl_round.py (deploy/shadow)
import these lists. Never redefine them locally — the 2026-07-09 incident, where
the Jul 5 split-feature retrain changed the contract and the deploy script kept
its own stale copy, silently killed the ML shadow for a full pricing run.

If you add/remove/reorder a feature here, retrain AND re-price in the same
session. XGBoost validates feature names + order at predict time, and
prepare_afl_round.load_models() hard-fails if a pickle disagrees with these lists.
"""

# Margin + total regressors (38 features — includes EMA form + market prob)
FEATURES_MARGIN_TOTAL = [
    # Era signal — lets model learn scoring trend across seasons
    'season_year',

    # ELO
    'elo_diff',
    'elo_win_prob',

    # Rest/travel
    'home_rest_days',
    'away_rest_days',
    'rest_diff',
    'home_travel_km',
    'away_travel_km',
    'travel_diff_km',

    # Home form
    'home_win_pct',
    'home_avg_margin',
    'home_last_margin',
    'home_off_big_win',
    'home_off_big_loss',
    'home_win_streak',
    'home_loss_streak',

    # Away form
    'away_win_pct',
    'away_avg_margin',
    'away_last_margin',
    'away_off_big_win',
    'away_off_big_loss',
    'away_win_streak',
    'away_loss_streak',

    # EMA form (recency-weighted, opponent-adjusted)
    'home_ema_win_pct',
    'home_ema_margin',
    'home_opp_adj_margin',
    'away_ema_win_pct',
    'away_ema_margin',
    'away_opp_adj_margin',
    'ema_margin_diff',
    'opp_adj_margin_diff',

    # Form diffs
    'form_win_pct_diff',
    'form_margin_diff',

    # Venue
    'venue_games',
    'venue_avg_total',
    'venue_home_win_pct',

    # Flags
    'is_final',

    # Market signal — opening implied probability (NaN → filled with elo_win_prob)
    'mkt_home_prob_open',
]

# H2H classifier (30 features — original form set, no EMA; EMA hurt binary accuracy)
FEATURES_H2H = [
    # Era signal
    'season_year',

    # ELO
    'elo_diff',
    'elo_win_prob',

    # Rest/travel
    'home_rest_days',
    'away_rest_days',
    'rest_diff',
    'home_travel_km',
    'away_travel_km',
    'travel_diff_km',

    # Home form
    'home_win_pct',
    'home_avg_margin',
    'home_last_margin',
    'home_off_big_win',
    'home_off_big_loss',
    'home_win_streak',
    'home_loss_streak',

    # Away form
    'away_win_pct',
    'away_avg_margin',
    'away_last_margin',
    'away_off_big_win',
    'away_off_big_loss',
    'away_win_streak',
    'away_loss_streak',

    # Form diffs
    'form_win_pct_diff',
    'form_margin_diff',

    # Venue
    'venue_games',
    'venue_avg_total',
    'venue_home_win_pct',

    # Flags
    'is_final',

    # Market signal
    'mkt_home_prob_open',
]
