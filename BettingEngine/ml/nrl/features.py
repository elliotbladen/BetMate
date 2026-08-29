"""Single feature contract for the independent NRL pre-market shadow."""

# Numeric, point-in-time features available in both the historical builder and
# live round database. String rest classes are deliberately excluded.
PREMARKET_FEATURES = [
    'elo_diff', 'home_elo_win_prob', 'elo_predicted_margin',
    'home_rest_days', 'away_rest_days', 'rest_diff',
    'home_had_bye', 'away_had_bye',
    'home_prev_margin', 'away_prev_margin',
    'home_off_big_win', 'home_off_big_loss',
    'away_off_big_win', 'away_off_big_loss',
    'home_win_streak', 'away_win_streak',
    'home_loss_streak', 'away_loss_streak',
    'home_travel_km', 'away_travel_km', 'travel_diff',
    'is_neutral_venue', 'venue_avg_total', 'venue_home_win_pct',
    'ref_total_diff', 'ref_penalty_rate', 'ref_home_bias', 'ref_home_win_pct',
    'rain_mm', 'wind_kmh', 'wind_gusts_kmh', 'temp_c',
]
