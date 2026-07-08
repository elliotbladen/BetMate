# pricing/afl_tier4_venue.py
# =============================================================================
# AFL Tier 4 — Venue layer
# =============================================================================
#
# Signals:
#   4A: Team fortress    — team-specific home win rate vs league baseline
#   4B: Venue scoring    — venue total deviation from league average
#
# T1 (rules baseline) uses only ELO and team scoring rates — no venue adjustment.
# T4 is the sole source of venue signals in the pricing stack:
#   - Team × venue interaction (e.g. Geelong specifically at GMHBA)
#   - Venue scoring profile (how a ground affects total points scored)
#
# Positive delta = home team advantage.
# All signals have individual caps; total T4 capped at ±5 pts handicap, ±5 pts totals.
#
# Sources: 2018-2026 Footywire data, min 20 home games at venue.
# League avg home win rate baseline: 56.3%
# =============================================================================

# ── Fortress ratings ──────────────────────────────────────────────────────────
# Derived from: team home win% at this venue vs 56.3% league baseline
# Formula: (win_pct - 0.563) * 20  → ~1 pt per 5% above baseline
# Positive = strong home fortress. Negative = below-average at this venue.
# Only included where n >= 20 games and effect >= 1.0 pt (i.e. ~5% deviation).
#
# (team_name, venue_name): fortress_pts
#
FORTRESS_RATINGS = {
    # Strong fortresses (2018-2026 data, baseline 56-57%)
    ('Sydney Swans',                  'SCG'):                  +3.0,   # 73% win rate — strongest in modern era
    ('Geelong Cats',                  'GMHBA Stadium'):        +3.0,   # 72% win rate (was +4.5, that was pre-2018 era)
    ('Geelong Cats',                  'Kardinia Park'):        +3.0,   # alias
    ('Greater Western Sydney Giants', 'ENGIE Stadium'):        +2.5,   # 69% win rate
    ('Collingwood Magpies',           'MCG'):                  +2.5,   # 69% win rate
    ('Brisbane Lions',                'The Gabba'):            +2.0,   # 67% win rate
    ('Brisbane Lions',                'Gabba'):                +2.0,   # alias
    ('Port Adelaide Power',           'Adelaide Oval'):        +1.5,   # 61-62% win rate
    ('Hawthorn Hawks',                'UTAS Stadium'):         +1.0,   # fortress largely gone — 46.7% recent (was +3.5)
    ('Hawthorn Hawks',                'Blundstone Arena'):     +1.0,   # alias
    # Neutral / shared venues — no team-specific bonus beyond normal home advantage
    # Negative fortresses (team home win rate meaningfully below league baseline)
    ('West Coast Eagles',             'Optus Stadium'):        -3.0,   # 23% home win rate 2022-26 — dire
    ('Gold Coast Suns',               'People First Stadium'): -4.0,   # ~34% home win rate since 2018
}

# ── Venue scoring profiles ────────────────────────────────────────────────────
# Season-adjusted residual totals deviation per venue (2018-2026 regular season).
# Method: residual = game_total - season_avg[year] (removes year-to-year drift)
# Blend: 70% recent-3yr + 30% all-time (falls back to all-time if n_recent < 8)
# Clamped at +-10 pts. Data source: local aussportsbetting AFL xlsx, 3474 games.
# Script: scripts/_build_afl_venue_profiles.py
#
# Key surprises vs old 30%-scaled guesses:
#   UTAS Stadium:         -1.5 → -10.0  (7x too small — Hawthorn rebuild effect real)
#   Optus Stadium:        -0.9 → -7.8   (Perth grounds heavily under league avg)
#   Adelaide Oval:        -0.9 → -4.2   (direction same but 4x stronger)
#   MCG:                  0.0  → -3.9   (large shared venue, under-scores)
#   ENGIE Stadium:        +2.0 → +8.7   (GWS home — highest non-Darwin scorer)
#   GMHBA Stadium:        +1.5 → +6.0   (Geelong home — strong over-scorer)
#   SCG:                  +0.5 → +5.4   (Sydney indoor-ish venue, high scoring)
#   Marvel Stadium:       +1.9 → +4.5   (enclosed venue, counter-intuitively high)
#   The Gabba:            -1.0 → +2.4   (direction FLIP — Brisbane offensive era)
#   People First Stadium: -4.6 → +2.0   (direction FLIP — Gold Coast open-air, attacking)
#
VENUE_SCORING_PROFILE = {
    # Under-scoring venues
    'UTAS Stadium':           -10.0,   # n=33 (10 recent); Launceston — Hawthorn rebuild confounded
    'Blundstone Arena':       -10.0,   # alias
    'Optus Stadium':           -7.8,   # n=185 (58 recent); Perth — dry conditions + defensive teams
    'Adelaide Oval':           -4.2,   # n=205 (71 recent); Adelaide — wind off river affects kicking
    'MCG':                     -3.9,   # n=355 (121 recent); huge open stadium, lower scoring
    # Roughly neutral
    'Manuka Oval':             +0.7,   # n=22 (7 recent); Canberra — limited sample, use all-time only
    'People First Stadium':    +2.0,   # n=114 (23 recent); Gold Coast — open-air, attacking style
    'Ninja Stadium':           +2.3,   # n=28 (7 recent); Ballarat — limited sample
    'The Gabba':               +2.4,   # n=113 (28 recent); Brisbane Lions offensive era (was -1.0)
    'Gabba':                   +2.4,   # alias
    # Over-scoring venues
    'Marvel Stadium':          +4.5,   # n=338 (110 recent); enclosed — traps humid air, consistent over
    'Marvel':                  +4.5,   # alias
    'Docklands':               +4.5,   # alias
    'SCG':                     +5.4,   # n=90 (29 recent); compact + fast surface = high scoring
    'GMHBA Stadium':           +6.0,   # n=75 (25 recent); Geelong — cats attack, loyal crowd
    'Kardinia Park':           +6.0,   # alias
    'ENGIE Stadium':           +8.7,   # n=65 (20 recent); GWS home — highest-scoring non-Darwin ground
    # Remote/hot venues — data-thin, use conservative estimates
    'TIO Stadium':             +7.0,   # n=17 all-time; Darwin — heat produces frenetic play; +10 was too aggressive for 1 2026 game
    'Cazalys Stadium':         -3.0,   # Cairns — small n, hot, conservative estimate
    'Traeger Park':            -3.0,   # Alice Springs — thin air, heat, conservative estimate
}

# Caps
T4_HANDICAP_CAP = 5.0
T4_TOTALS_CAP   = 10.0


# ── Signal functions ──────────────────────────────────────────────────────────

def signal_4a_fortress(home: str, away: str, venue: str) -> dict:
    """
    Team-specific fortress adjustment.
    Looks up home team's record at this venue vs league baseline.
    Positive = home team has a proven fortress here.
    """
    home_pts = FORTRESS_RATINGS.get((home, venue), 0.0)
    away_pts = FORTRESS_RATINGS.get((away, venue), 0.0)

    # If away team has a fortress here, that's a home-team disadvantage
    pts = home_pts - away_pts
    pts = max(-T4_HANDICAP_CAP, min(T4_HANDICAP_CAP, pts))

    notes = []
    if home_pts != 0.0:
        notes.append(f'{home.split()[-1]} fortress ({home_pts:+.1f})')
    if away_pts != 0.0:
        notes.append(f'{away.split()[-1]} away at own fortress ({away_pts:+.1f})')

    return {
        'signal':    '4A_fortress',
        'home_pts':  home_pts,
        'away_pts':  away_pts,
        'pts':       round(pts, 2),
        'note':      ' | '.join(notes),
        'applied':   pts != 0.0,
    }


def signal_4b_venue_scoring(venue: str) -> dict:
    """
    Residual venue scoring profile — totals adjustment only.
    Positive = higher scoring venue. Negative = lower scoring.
    """
    pts = VENUE_SCORING_PROFILE.get(venue, 0.0)
    pts = max(-T4_TOTALS_CAP, min(T4_TOTALS_CAP, pts))

    return {
        'signal':  '4B_venue_scoring',
        'venue':   venue,
        'pts':     round(pts, 2),
        'applied': pts != 0.0,
    }


# ── Master function ───────────────────────────────────────────────────────────

def compute_t4(home: str, away: str, venue: str) -> dict:
    """
    Compute all T4 venue signals and return combined result.

    Returns:
        t4_handicap : float  — total handicap adjustment (home perspective)
        t4_totals   : float  — totals adjustment (venue scoring profile)
        signals     : list   — per-signal breakdown for audit
    """
    s4a = signal_4a_fortress(home, away, venue)
    s4b = signal_4b_venue_scoring(venue)

    t4_handicap = max(-T4_HANDICAP_CAP, min(T4_HANDICAP_CAP, s4a['pts']))
    t4_totals   = max(-T4_TOTALS_CAP,   min(T4_TOTALS_CAP,   s4b['pts']))

    return {
        't4_handicap': round(t4_handicap, 2),
        't4_totals':   round(t4_totals,   2),
        'signals':     [s4a, s4b],
    }
