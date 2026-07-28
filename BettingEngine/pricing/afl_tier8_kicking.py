# pricing/afl_tier8_kicking.py
# =============================================================================
# AFL Tier 8 — Kicking accuracy (set-shot conversion) layer
# =============================================================================
#
# Signal: a team can dominate scoring shots (inside 50s converted into shots on
# goal) and still lose the margin — or vice versa — purely on how straight they
# kick. A pure win/margin-based ELO bakes that conversion noise into the rating
# without ever crediting or debiting the underlying quality separately. This
# tier gives each team a small, capped adjustment based on how far their own
# season-to-date conversion rate (goals / (goals + behinds)) sits from the
# league average.
#
# This is the LIGHTWEIGHT stop-gap version (backlog: "set-shot conversion
# tracker, medium term"). It nudges the current round's price using this
# season's conversion data — it does NOT touch how ELO itself is built from
# history. The deeper fix (feed scoring_shots × 3.70 into the ELO update
# itself instead of raw margin, so bad kicking stops poisoning the rating
# going forward) is banked for the 2026 off-season — see CLAUDE.md backlog
# and memory note project_afl_xscore_elo_endofseason. Do not conflate the two;
# this tier is deliberately small and capped so it can't run away with a price
# while that bigger rebuild is still pending validation.
#
# Formula:
#   adjustment per team = ((team_conversion_pct - league_avg_pct) / 5.0) * PTS_PER_5PCT
#   handicap (home perspective) = home_adj - away_adj
#   totals = home_adj + away_adj
#
# Data: season-to-date goals/behinds per team, read directly from the same
# historical xlsx game_log.py uses (outputs/afl_weekly_review/historical/latest.xlsx).
# No lookahead — only games strictly before the round being priced are counted.
# =============================================================================

from pathlib import Path

import pandas as pd

PTS_PER_5PCT_HCAP = 2.5   # midpoint of the backlog's +/-2-3pt spec
PTS_PER_5PCT_TOTAL = 2.5

T8_HANDICAP_CAP = 4.0
T8_TOTALS_CAP = 4.0

MIN_SHOTS_FOR_SIGNAL = 30   # roughly 4 games worth of scoring shots per team
DEFAULT_LEAGUE_AVG = 52.5   # fallback if the season sample is empty/unavailable

# The historical xlsx uses short club names; the rest of this engine (FIXTURE,
# INJURIES, EMOTIONAL_FLAGS, etc.) uses full names. Normalise on load.
_SHORT_TO_FULL = {
    "Adelaide": "Adelaide Crows",
    "Brisbane": "Brisbane Lions",
    "Carlton": "Carlton Blues",
    "Collingwood": "Collingwood Magpies",
    "Essendon": "Essendon Bombers",
    "Fremantle": "Fremantle Dockers",
    "GWS Giants": "Greater Western Sydney Giants",
    "Geelong": "Geelong Cats",
    "Gold Coast": "Gold Coast Suns",
    "Hawthorn": "Hawthorn Hawks",
    "Melbourne": "Melbourne Demons",
    "North Melbourne": "North Melbourne Kangaroos",
    "Port Adelaide": "Port Adelaide Power",
    "Richmond": "Richmond Tigers",
    "St Kilda": "St Kilda Saints",
    "Sydney": "Sydney Swans",
    "West Coast": "West Coast Eagles",
    "Western Bulldogs": "Western Bulldogs",
}

_cache: dict = {}


def load_conversion_rates(xlsx_path: Path, season: int, as_of_date: str) -> dict:
    """
    Season-to-date goal-kicking conversion rate per team, using every game
    strictly before `as_of_date` in `season`. No lookahead.

    Returns:
        {team_name: {'conversion_pct': float, 'shots': int}, ...,
         '_league_avg': float, '_min_shots': int}
    """
    cache_key = (str(xlsx_path), season, as_of_date)
    if cache_key in _cache:
        return _cache[cache_key]

    if not Path(xlsx_path).exists():
        rates = {'_league_avg': DEFAULT_LEAGUE_AVG, '_min_shots': MIN_SHOTS_FOR_SIGNAL}
        _cache[cache_key] = rates
        return rates

    df = pd.read_excel(xlsx_path, header=1)
    df['Date'] = pd.to_datetime(df['Date'])
    cutoff = pd.Timestamp(as_of_date)
    df = df[(df['Date'].dt.year == season) & (df['Date'] < cutoff)]

    goals: dict = {}
    behinds: dict = {}
    for _, row in df.iterrows():
        for side in ('Home', 'Away'):
            team_raw = row.get(f'{side} Team')
            g = row.get(f'{side} Goals')
            b = row.get(f'{side} Behinds')
            if team_raw is None or pd.isna(g) or pd.isna(b):
                continue
            team = _SHORT_TO_FULL.get(team_raw, team_raw)
            goals[team] = goals.get(team, 0) + g
            behinds[team] = behinds.get(team, 0) + b

    rates: dict = {}
    total_g, total_b = 0, 0
    for team in goals:
        g, b = goals[team], behinds.get(team, 0)
        shots = g + b
        if shots <= 0:
            continue
        rates[team] = {'conversion_pct': g / shots * 100.0, 'shots': int(shots)}
        total_g += g
        total_b += b

    league_avg = (total_g / (total_g + total_b) * 100.0) if (total_g + total_b) > 0 else DEFAULT_LEAGUE_AVG
    rates['_league_avg'] = league_avg
    rates['_min_shots'] = MIN_SHOTS_FOR_SIGNAL

    _cache[cache_key] = rates
    return rates


def compute_t8(home: str, away: str, rates: dict) -> dict:
    league_avg = rates.get('_league_avg', DEFAULT_LEAGUE_AVG)
    min_shots = rates.get('_min_shots', MIN_SHOTS_FOR_SIGNAL)

    def team_adj(team):
        info = rates.get(team)
        if not info or info['shots'] < min_shots:
            return 0.0, (info['conversion_pct'] if info else None), (info['shots'] if info else 0)
        delta_pct = info['conversion_pct'] - league_avg
        adj = (delta_pct / 5.0) * PTS_PER_5PCT_HCAP
        return adj, info['conversion_pct'], info['shots']

    home_adj, home_pct, home_shots = team_adj(home)
    away_adj, away_pct, away_shots = team_adj(away)

    net_handicap = home_adj - away_adj
    net_totals = home_adj + away_adj

    net_handicap = max(-T8_HANDICAP_CAP, min(T8_HANDICAP_CAP, net_handicap))
    net_totals = max(-T8_TOTALS_CAP, min(T8_TOTALS_CAP, net_totals))

    if home_pct is not None and away_pct is not None:
        note = (f"{home} conv {home_pct:.1f}% ({home_shots} shots) vs "
                f"{away} conv {away_pct:.1f}% ({away_shots} shots), league avg {league_avg:.1f}%")
    else:
        note = "insufficient season-to-date shot sample for one or both teams — T8 neutral"

    return {
        't8_handicap': round(net_handicap, 2),
        't8_totals': round(net_totals, 2),
        'home_conversion_pct': round(home_pct, 1) if home_pct is not None else None,
        'away_conversion_pct': round(away_pct, 1) if away_pct is not None else None,
        'home_shots': home_shots,
        'away_shots': away_shots,
        'league_avg_pct': round(league_avg, 1),
        'note': note,
        'signals': [{
            'signal': '8_kicking',
            'home_adj': round(home_adj, 2),
            'away_adj': round(away_adj, 2),
            'net_hdcp': round(net_handicap, 2),
            'net_tot': round(net_totals, 2),
            'applied': net_handicap != 0.0 or net_totals != 0.0,
            'note': note,
        }],
    }
