#!/usr/bin/env python3
"""
scripts/price_round27_2026.py

Full 7-tier price-up for the NRL round played 2026-08-27/30 (Broncos v Storm,
Manly v Dragons, Panthers v Bulldogs, Titans v Rabbitohs, Roosters v Dolphins,
Cowboys v Wests Tigers, Warriors v Knights, Eels v Sharks).

LABELLED R27 to match this repo's internal round numbering, which runs one
number ahead of the official NRL round numbers (this repo's "R26" bets,
logged 2026-08-21/22, were actually the official NRL Round 25 games -
Raiders v Broncos, Rabbitohs v Warriors, Dragons v Bulldogs. Confirmed via
lib/researchData.ts commit db63e5c). Built in a session on the OneDrive
BettingEngine copy where data/model.db was empty (never migrated) - every
tier below was reconstructed from live web research + the real production
formulas in pricing/*.py, not pulled from a populated DB. See that session's
handover diary for the full derivation and caveats per tier.

Data sources baked in below:
  T1  ELO: data/import/nrl_2026_full_results_r1_r25.csv (188 games,
      en.wikipedia.org/wiki/2026_NRL_season_results), run through the same
      K=20/start=1500 formula as scripts/bootstrap_elo_2026.py. Single-season
      only - no 2024/2025 carryover (those xlsx files weren't available in
      that session).
  T1  ladder (win_pct/ladder_position/PF/PA): zerotackle.com/nrl/nrl-ladder/
  T2  style stats: data/import/team_style_stats_{a,b,c,d}_2026.csv, refreshed
      this session from Fox Sports screenshots (2026-08-25, ~R25-current) -
      replaces the stale "as at R4" snapshot that was still sitting in this
      file before.
  T3  rest days: derived from the same 188-game results file. Travel: real
      haversine on hardcoded team-base/venue coordinates (TEAM_BASE/VENUE_COORD
      below).
  T4  venue: proxy only - each home team's own 2026 home-game record standing
      in for true per-venue history (no per-game venue tags exist to isolate
      it further). Flagged as blunt/redundant with T1 home advantage in the
      original session - Penrith v Bulldogs is the weakest case since that
      game is at CommBank Stadium, not Penrith's actual home ground.
  T5  injuries: Round 26(official)/"R27" team-list news, bets.com.au +
      ESPN, tier-scored elite=3.0/key=1.5/rotation=0.5 per
      scripts/prepare_round.py's own _INJURY_PTS scale.
  T6  referees: ESPN R26 preview article for appointments, bucket lookup
      from the existing data/import/referee_profiles_2025.csv. Two refs
      (Wyatt Raymond, Nick Pelgrave) aren't in that file -> treated neutral.
  T7  emotional: news-derived flags (star returns, must-win finals context,
      shame_blowout). See EMOTIONAL_FLAGS below for exact sourcing/exclusions
      per game (what was checked and deliberately left out, e.g. Adam
      Reynolds' farewell - team list suggests he's not even selected this
      game).

Usage:
    cd BettingEngine
    python scripts/price_round27_2026.py
"""
import csv
import math
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pricing.tier1_baseline import compute_baseline
from pricing.tier2_matchup import compute_family_a, compute_family_b, compute_family_c, compute_family_d
from pricing.tier3_situational import _haversine_km, compute_situational_adjustments
from pricing.tier4_venue import compute_venue_adjustments
from pricing.tier5_injury import compute_injury_adjustments
from pricing.tier6_referee import compute_referee_adjustments
from pricing.tier7_emotional import compute_emotional_adjustments
from pricing.engine import derive_final_prices

# ---------------------------------------------------------------------------
# Config (real values from config/tiers.yaml, not code defaults)
# ---------------------------------------------------------------------------
T1_CFG = {
    'league_avg_total': 47.0, 'home_advantage_points': 3.5, 'recent_form_games': 5,
    'form_recency_weighted': False, 'form_weight_points': 2.5, 'margin_std_dev': 12.0,
    'elo_weight': 0.3, 'points_per_elo_point': 0.08, 'elo_gap_dampener_threshold': 150,
    'elo_gap_dampener_factor': 0.75, 'default_elo': 1500.0,
    'min_games_for_home_advantage': 14, 'team_ha_max_delta': 2.0,
    'prior_season_weight': 0.70, 'pfpa_max_weight': 0.70, 'pfpa_shrink_full_games': 10,
    'pyth_floor_ceiling_max_deviation': 0.25, 'pyth_floor_ceiling_gp_threshold': 8,
    'season_quality_scale': 24.0, 'season_quality_correction_weight': 0.2,
    'season_quality_win_weight': 0.6, 'season_quality_ladder_weight': 0.4,
    'season_quality_num_teams': 16, 'attack_season_weight': 0.7, 'defence_season_weight': 0.7,
    'defence_attack_bias': 0.05, 'pythagorean_exponent': 1.9, 'pythagorean_scale': 50.0,
    'totals_conservative_bias': 0.5, 'close_call_class_lean_threshold': 6.0,
    'close_call_class_lean_pts': 0.5, 'form_outcome_weight': 0.4, 'form_margin_weight': 0.2,
    'form_scoring_weight': 0.2, 'form_conceding_weight': 0.2, 'form_margin_norm': 20.0,
    'form_scoring_norm': 12.0, 'form_conceding_norm': 12.0, 'season_quality_weight': 0.75,
    'form_balance_weight': 1.0,
}
T3_CFG = {
    'tier3_situational': {
        'enabled': True, 'max_home_points_delta': 3.0, 'max_away_points_delta': 3.0,
        'rest': {
            'enabled': True, 'short_max_days': 6, 'normal_max_days': 9, 'long_max_days': 13,
            'cap': 2.0,
            'matrix': {
                'short_vs_short': 0.0, 'short_vs_normal': -1.0, 'short_vs_long': -1.5, 'short_vs_bye': -2.0,
                'normal_vs_short': 1.0, 'normal_vs_normal': 0.0, 'normal_vs_long': -1.0, 'normal_vs_bye': -1.5,
                'long_vs_short': 1.5, 'long_vs_normal': 1.0, 'long_vs_long': 0.0, 'long_vs_bye': -1.0,
                'bye_vs_short': 2.0, 'bye_vs_normal': 1.5, 'bye_vs_long': 1.0, 'bye_vs_bye': 0.0,
            },
        },
        'travel': {'enabled': True, 'scale': 1.1, 'cap': 2.0},
        'compound': {'enabled': True, 'threshold_km': 500, 'delta': -0.5, 'cap': 0.5},
    }
}
T4_CFG = {'handicap_clamp': 1.5, 'totals_clamp': 2.0}
T5_CFG = {'handicap_clamp': 3.0, 'totals_threshold': 2.5, 'totals_rate': -0.3, 'totals_cap': -3.0}
T6_CFG = {'shrink': 1.0, 'handicap_clamp': 1.5, 'totals_whistle_heavy': -2.0,
          'totals_flow_heavy': 2.0, 'totals_neutral': 0.0, 'totals_clamp': 2.0}
T7_CFG = {
    'enabled': True, 'max_home_points_delta': 2.5, 'max_away_points_delta': 2.5,
    'max_totals_delta': 1.5,
    'strength_multipliers': {'minor': 0.5, 'normal': 1.0, 'major': 1.5},
    'flag_margin_pts': {
        'milestone': 0.8, 'new_coach': 1.2, 'star_return': 1.5, 'shame_blowout': 1.0,
        'origin_boost': 0.6, 'farewell': 0.5, 'personal_tragedy': 1.5,
        'rivalry_derby': 0.3, 'must_win': 0.8,
    },
    'flag_totals_pts': {
        'milestone': 0.3, 'new_coach': 0.0, 'star_return': 0.5, 'shame_blowout': 0.5,
        'origin_boost': 0.2, 'farewell': 0.2, 'personal_tragedy': 0.0,
        'rivalry_derby': 0.5, 'must_win': 0.3,
    },
}
TIER2_FAMILY_CFG = {}  # no explicit config sections -> production code defaults
# Current NRL T2 policy (2026-09-02): at most 3 expected-score points per
# team, with a further 50% reduction when T2 reinforces the T1 direction.
T2_HOME_CAP = 3.0
T2_AWAY_CAP = 3.0
T2_NET_CAP = 3.0
T2_DIRECTIONAL_CAP = True

# ---------------------------------------------------------------------------
# 188-game 2026 results (R1-R25) -> ELO input
# ---------------------------------------------------------------------------
RESULTS_CSV = ROOT / "data" / "import" / "nrl_2026_full_results_r1_r25.csv"

with open(RESULTS_CSV, newline="", encoding="utf-8") as fh:
    MATCHES = [
        {
            'round': int(row['round']), 'match_date': row['match_date'],
            'home_team': row['home_team'], 'home_score': int(row['home_score']),
            'away_team': row['away_team'], 'away_score': int(row['away_score']),
        }
        for row in csv.DictReader(fh)
    ]

STARTING_ELO = 1500.0
K_FACTOR = 20.0


def expected_score(r_a, r_b):
    return 1.0 / (1.0 + 10.0 ** ((r_b - r_a) / 400.0))


def compute_elo(matches):
    ratings = {}
    for m in matches:
        for team in (m['home_team'], m['away_team']):
            ratings.setdefault(team, STARTING_ELO)
    for m in matches:
        h, a = m['home_team'], m['away_team']
        r_h, r_a = ratings[h], ratings[a]
        hs, aws = m['home_score'], m['away_score']
        e_h = expected_score(r_h, r_a)
        e_a = 1.0 - e_h
        if hs > aws:
            s_h, s_a = 1.0, 0.0
        elif hs < aws:
            s_h, s_a = 0.0, 1.0
        else:
            s_h, s_a = 0.5, 0.5
        ratings[h] = r_h + K_FACTOR * (s_h - e_h)
        ratings[a] = r_a + K_FACTOR * (s_a - e_a)
    return ratings


ELO = compute_elo(MATCHES)

# ---------------------------------------------------------------------------
# Ladder after Round 25 (source: zerotackle.com/nrl/nrl-ladder/)
# ---------------------------------------------------------------------------
LADDER = {
    "New Zealand Warriors":            (22, 16, 6, 651, 356, 1),
    "Penrith Panthers":                (22, 16, 6, 621, 327, 2),
    "Sydney Roosters":                 (22, 16, 6, 587, 425, 3),
    "Dolphins":                        (22, 15, 7, 612, 474, 4),
    "Cronulla-Sutherland Sharks":      (22, 14, 8, 634, 461, 5),
    "Newcastle Knights":               (23, 14, 9, 601, 545, 6),
    "South Sydney Rabbitohs":          (22, 12, 10, 602, 539, 7),
    "North Queensland Cowboys":        (22, 12, 10, 514, 592, 8),
    "Canterbury-Bankstown Bulldogs":   (22, 11, 11, 446, 478, 9),
    "Manly-Warringah Sea Eagles":      (22, 10, 12, 549, 483, 10),
    "Melbourne Storm":                 (22, 9, 13, 524, 536, 11),
    "Canberra Raiders":                (23, 10, 13, 531, 596, 12),
    "Parramatta Eels":                 (22, 8, 14, 437, 636, 13),
    "Wests Tigers":                    (22, 8, 14, 425, 637, 14),
    "Brisbane Broncos":                (22, 7, 15, 417, 611, 15),
    "Gold Coast Titans":               (22, 6, 16, 435, 597, 16),
    "St. George Illawarra Dragons":    (22, 4, 18, 358, 651, 17),
}


def team_stats(name: str) -> dict:
    gp, w, l, pf, pa, pos = LADDER[name]
    return {
        'games_played': gp, 'wins': w, 'losses': l, 'win_pct': w / gp,
        'ladder_position': pos, 'points_for_avg': pf / gp, 'points_against_avg': pa / gp,
        'elo_rating': ELO[name],
    }


# ---------------------------------------------------------------------------
# Style stats (Tier 2) - loaded from the refreshed data/import CSVs
# ---------------------------------------------------------------------------
FAMILY_FILES = {
    "a": ("team_style_stats_a_2026.csv", ["completion_rate", "kick_metres_pg", "errors_pg", "penalties_pg"]),
    "b": ("team_style_stats_b_2026.csv", ["lb_pg", "tb_pg", "mt_pg", "lbc_pg"]),
    "c": ("team_style_stats_c_2026.csv", ["run_metres_pg"]),
    "d": ("team_style_stats_d_2026.csv", ["fdo_pg", "krm_pg"]),
}


def load_style_stats() -> dict:
    merged = {}
    for _, (fname, cols) in FAMILY_FILES.items():
        with open(ROOT / "data" / "import" / fname, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                team = row["team"].strip()
                merged.setdefault(team, {})
                for c in cols:
                    v = row.get(c)
                    if v is None or v == "":
                        continue
                    val = float(v)
                    if c == "completion_rate" and val > 1.0:
                        val = val / 100.0
                    merged[team][c] = val
    return merged


def compute_norms(style_by_team: dict) -> dict:
    cols = ("lb_pg", "tb_pg", "mt_pg", "lbc_pg",
            "completion_rate", "kick_metres_pg", "errors_pg", "penalties_pg",
            "run_metres_pg", "fdo_pg", "krm_pg")
    norms = {}
    for col in cols:
        vals = [d[col] for d in style_by_team.values() if col in d]
        if len(vals) >= 2:
            avg = sum(vals) / len(vals)
            std = math.sqrt(sum((v - avg) ** 2 for v in vals) / len(vals))
            norms[col] = (avg, max(std, 1e-6))
        else:
            norms[col] = (0.0, 1.0)
    return norms


# ---------------------------------------------------------------------------
# Geography (Tier 3 travel)
# ---------------------------------------------------------------------------
TEAM_BASE = {
    "Brisbane Broncos":              (-27.4698, 153.0251),
    "Melbourne Storm":               (-37.8136, 144.9631),
    "Manly-Warringah Sea Eagles":    (-33.7969, 151.2848),
    "St. George Illawarra Dragons":  (-34.4278, 150.8931),
    "Penrith Panthers":              (-33.7511, 150.6942),
    "Canterbury-Bankstown Bulldogs": (-33.9137, 151.0850),
    "Gold Coast Titans":             (-28.0653, 153.3702),
    "South Sydney Rabbitohs":        (-33.8930, 151.2044),
    "Sydney Roosters":               (-33.8879, 151.2251),
    "Dolphins":                      (-27.2270, 153.1133),
    "North Queensland Cowboys":      (-19.2590, 146.8169),
    "Wests Tigers":                  (-33.8730, 151.0900),
    "New Zealand Warriors":          (-36.8485, 174.7633),
    "Newcastle Knights":             (-32.9283, 151.7817),
    "Parramatta Eels":               (-33.8007, 151.0169),
    "Cronulla-Sutherland Sharks":    (-34.0287, 151.1544),
}
VENUE_COORD = {
    "Suncorp Stadium":                (-27.4858, 153.0389),
    "4 Pines Park":                   (-33.7969, 151.2848),
    "CommBank Stadium":               (-33.8007, 151.0169),
    "Cbus Super Stadium":             (-28.0653, 153.3702),
    "Allianz Stadium":                (-33.8879, 151.2251),
    "Queensland Country Bank Stadium": (-19.2830, 146.8169),
    "Go Media Stadium":               (-36.9151, 174.7902),
}

FIXTURE = [
    ("Brisbane Broncos", "Melbourne Storm", "Suncorp Stadium", "2026-08-27"),
    ("Manly-Warringah Sea Eagles", "St. George Illawarra Dragons", "4 Pines Park", "2026-08-28"),
    ("Penrith Panthers", "Canterbury-Bankstown Bulldogs", "CommBank Stadium", "2026-08-28"),
    ("Gold Coast Titans", "South Sydney Rabbitohs", "Cbus Super Stadium", "2026-08-29"),
    ("Sydney Roosters", "Dolphins", "Allianz Stadium", "2026-08-29"),
    ("North Queensland Cowboys", "Wests Tigers", "Queensland Country Bank Stadium", "2026-08-29"),
    ("New Zealand Warriors", "Newcastle Knights", "Go Media Stadium", "2026-08-30"),
    ("Parramatta Eels", "Cronulla-Sutherland Sharks", "CommBank Stadium", "2026-08-30"),
]

# ---------------------------------------------------------------------------
# Referees (Tier 6) - ESPN R26 preview article; bucket from existing
# data/import/referee_profiles_2025.csv
# ---------------------------------------------------------------------------
REF_BUCKET = {
    "Ashley Klein": "whistle_heavy", "Chris Butler": "whistle_heavy",
    "Grant Atkins": "flow_heavy", "Peter Gough": "flow_heavy",
    "Gerard Sutton": "neutral", "Adam Gee": "neutral", "Todd Smith": "neutral",
    "Ziggy Przeklasa-Adamski": "neutral", "Liam Kennedy": "neutral", "Gavin Badger": "neutral",
}
REF_ASSIGNMENT = {
    ("Brisbane Broncos", "Melbourne Storm"): "Wyatt Raymond",
    ("Manly-Warringah Sea Eagles", "St. George Illawarra Dragons"): "Nick Pelgrave",
    ("Penrith Panthers", "Canterbury-Bankstown Bulldogs"): "Gerard Sutton",
    ("Gold Coast Titans", "South Sydney Rabbitohs"): "Liam Kennedy",
    ("Sydney Roosters", "Dolphins"): "Todd Smith",
    ("North Queensland Cowboys", "Wests Tigers"): "Grant Atkins",
    ("New Zealand Warriors", "Newcastle Knights"): "Adam Gee",
    ("Parramatta Eels", "Cronulla-Sutherland Sharks"): "Ashley Klein",
}

# ---------------------------------------------------------------------------
# Injuries (Tier 5) - bets.com.au/ESPN team-list news;
# elite=3.0/key=1.5/rotation=0.5 per scripts/prepare_round.py's own scale
# ---------------------------------------------------------------------------
INJURY_OUTS = {
    "Brisbane Broncos": 0.0, "Melbourne Storm": 0.5,
    "Manly-Warringah Sea Eagles": 1.5, "St. George Illawarra Dragons": 1.5,
    "Penrith Panthers": 1.5, "Canterbury-Bankstown Bulldogs": 0.5,
    "Gold Coast Titans": 1.5, "South Sydney Rabbitohs": 0.0,
    "Sydney Roosters": 3.0, "Dolphins": 0.0,
    "North Queensland Cowboys": 0.0, "Wests Tigers": 1.5,
    "New Zealand Warriors": 1.5, "Newcastle Knights": 5.0,
    "Parramatta Eels": 0.0, "Cronulla-Sutherland Sharks": 0.5,
}

# ---------------------------------------------------------------------------
# Emotional flags (Tier 7) - news-sourced, not fabricated. See exclusions in
# the module docstring above for what was checked and left out.
# ---------------------------------------------------------------------------
EMOTIONAL_FLAGS = {
    ("Brisbane Broncos", "Melbourne Storm"): {
        'home': [],
        'away': [
            {'flag_type': 'star_return', 'flag_strength': 'normal',
             'player_name': 'Jahrome Hughes', 'notes': 'back from 3-game hamstring absence'},
            {'flag_type': 'milestone', 'flag_strength': 'minor',
             'player_name': 'Eli Katoa', 'notes': '100th NRL game overall (round attribution uncertain)'},
        ],
    },
    ("Manly-Warringah Sea Eagles", "St. George Illawarra Dragons"): {
        'home': [
            {'flag_type': 'must_win', 'flag_strength': 'normal',
             'notes': 'Manly finals long-shot - must win + needs results elsewhere'},
        ],
        'away': [
            {'flag_type': 'shame_blowout', 'flag_strength': 'normal',
             'notes': 'Lost 14-44 to Bulldogs last round (exactly 30pt margin)'},
        ],
    },
    ("Penrith Panthers", "Canterbury-Bankstown Bulldogs"): {
        'home': [],
        'away': [
            {'flag_type': 'must_win', 'flag_strength': 'major',
             'notes': 'Bulldogs outside longshot finals chance, must win + needs help'},
        ],
    },
    ("Gold Coast Titans", "South Sydney Rabbitohs"): {
        'home': [],
        'away': [
            {'flag_type': 'must_win', 'flag_strength': 'normal',
             'notes': 'Rabbitohs (7th) defending a top-8 spot in the last round'},
            {'flag_type': 'star_return', 'flag_strength': 'major',
             'player_name': 'Latrell Mitchell', 'notes': 'back after 12 games out (back/nerve issue)'},
        ],
    },
    ("Sydney Roosters", "Dolphins"): {
        'home': [
            {'flag_type': 'star_return', 'flag_strength': 'normal',
             'player_name': 'James Tedesco', 'notes': 'captain, back from 3-game ankle absence'},
        ],
        'away': [],
    },
    ("North Queensland Cowboys", "Wests Tigers"): {
        'home': [
            {'flag_type': 'must_win', 'flag_strength': 'normal',
             'notes': 'Cowboys (8th) defending the last finals spot'},
            {'flag_type': 'star_return', 'flag_strength': 'normal',
             'player_name': 'Tom Dearden', 'notes': 'captain, back from 4-game ankle absence'},
            {'flag_type': 'star_return', 'flag_strength': 'normal',
             'player_name': 'Jeremiah Nanai', 'notes': 'back from hamstring injury'},
        ],
        'away': [],
    },
    ("New Zealand Warriors", "Newcastle Knights"): {'home': [], 'away': []},
    ("Parramatta Eels", "Cronulla-Sutherland Sharks"): {'home': [], 'away': []},
}


# ---------------------------------------------------------------------------
# Venue (Tier 4) - home team's own 2026 home-game record as a proxy for true
# per-venue history (no per-game venue tags exist in the 188-game file to
# isolate it further). See module docstring for the Penrith/CommBank caveat.
# ---------------------------------------------------------------------------
def _home_record(team: str):
    home_games = [m for m in MATCHES if m['home_team'] == team]
    n = len(home_games)
    if n < 3:
        return 0.0, 0.0, n
    margin_avg = sum(m['home_score'] - m['away_score'] for m in home_games) / n
    total_avg = sum(m['home_score'] + m['away_score'] for m in home_games) / n
    return margin_avg, total_avg, n


HOME_RECORD = {team: _home_record(team) for team in LADDER}


def last_game_date(team: str) -> date:
    played = [date.fromisoformat(m['match_date']) for m in MATCHES
              if m['home_team'] == team or m['away_team'] == team]
    return max(played)


def rest_days(team: str, kickoff: str) -> int:
    return (date.fromisoformat(kickoff) - last_game_date(team)).days


def travel_km(team: str, venue: str) -> float:
    base = TEAM_BASE[team]
    ven = VENUE_COORD[venue]
    return _haversine_km(base[0], base[1], ven[0], ven[1])


def price_game(home, away, venue, kickoff, style_by_team, norms):
    hs, as_ = team_stats(home), team_stats(away)

    t1 = compute_baseline(hs, as_, {}, T1_CFG)
    t1_home, t1_away = t1['baseline_home_points'], t1['baseline_away_points']

    hst, ast = style_by_team[home], style_by_team[away]
    fa = compute_family_a(hst, ast, norms, TIER2_FAMILY_CFG)
    fc = compute_family_c(hst, ast, norms, TIER2_FAMILY_CFG)
    fd = compute_family_d(hst, ast, norms, TIER2_FAMILY_CFG,
                           home_2a_delta=fa['home_delta'], away_2a_delta=fa['away_delta'])
    fb = compute_family_b(hst, ast, norms, TIER2_FAMILY_CFG)
    raw_home_t2 = fa['home_delta'] + fb['home_delta'] + fc['home_delta'] + fd['home_delta']
    raw_away_t2 = fa['away_delta'] + fb['away_delta'] + fc['away_delta'] + fd['away_delta']
    raw_totals_t2 = (fa.get('totals_delta', 0.0) + fb.get('totals_delta', 0.0)
                     + fc.get('totals_delta', 0.0) + fd.get('totals_delta', 0.0))
    totals_t2 = max(-3.0, min(3.0, raw_totals_t2))
    home_cap, away_cap, net_cap = T2_HOME_CAP, T2_AWAY_CAP, T2_NET_CAP
    t2_net_raw = raw_home_t2 - raw_away_t2
    same_direction = ((t1_home - t1_away > 0 and t2_net_raw > 0) or
                      (t1_home - t1_away < 0 and t2_net_raw < 0))
    if T2_DIRECTIONAL_CAP and same_direction:
        home_cap *= 0.5
        away_cap *= 0.5
        net_cap *= 0.5
    scale_t2 = 1.0
    if abs(raw_home_t2) > home_cap and raw_home_t2 != 0.0:
        scale_t2 = min(scale_t2, home_cap / abs(raw_home_t2))
    if abs(raw_away_t2) > away_cap and raw_away_t2 != 0.0:
        scale_t2 = min(scale_t2, away_cap / abs(raw_away_t2))
    if abs(t2_net_raw) > net_cap and t2_net_raw != 0.0:
        scale_t2 = min(scale_t2, net_cap / abs(t2_net_raw))
    t2_home, t2_away = raw_home_t2 * scale_t2, raw_away_t2 * scale_t2

    h_rest = rest_days(home, kickoff)
    a_rest = rest_days(away, kickoff)
    h_km = travel_km(home, venue)
    a_km = travel_km(away, venue)
    context = {
        'home_rest_days': h_rest, 'away_rest_days': a_rest,
        'home_travel_km': h_km, 'away_travel_km': a_km,
    }
    t3 = compute_situational_adjustments(context, T3_CFG)
    t3_home, t3_away = t3['home_delta_capped'], t3['away_delta_capped']
    totals_t3 = t3['totals_delta']

    home_margin_edge, home_total_avg, home_n = HOME_RECORD[home]
    away_venue_edge = 0.0
    venue_total_edge = (home_total_avg - T1_CFG['league_avg_total']) if home_n >= 3 else 0.0
    t4 = compute_venue_adjustments(
        home_team_id=home, away_team_id=away, venue_id=venue,
        home_venue_edge=home_margin_edge, away_venue_edge=away_venue_edge,
        venue_total_edge=venue_total_edge, config=T4_CFG,
    )

    t5 = compute_injury_adjustments(INJURY_OUTS[home], INJURY_OUTS[away], T5_CFG)

    ref_name = REF_ASSIGNMENT[(home, away)]
    bucket = REF_BUCKET.get(ref_name, "neutral")
    t6 = compute_referee_adjustments(0.0, 0.0, bucket, T6_CFG)

    flags = EMOTIONAL_FLAGS[(home, away)]
    t7 = compute_emotional_adjustments(flags['home'], flags['away'], T7_CFG)

    final_home = t1_home + t2_home + t3_home
    final_away = t1_away + t2_away + t3_away
    final_margin = ((final_home - final_away) + t4['handicap_delta'] + t5['handicap_delta']
                     + t6['handicap_delta'] + t7['handicap_delta'])
    raw_final_total = (t1['baseline_total'] + totals_t2 + totals_t3 + t4['totals_delta']
                        + t5['totals_delta'] + t6['totals_delta'] + t7['totals_delta'])
    final_total = max(30.0, min(70.0, raw_final_total))
    pred_home = round((final_total + final_margin) / 2.0, 1)
    pred_away = round((final_total - final_margin) / 2.0, 1)

    prices = derive_final_prices(pred_home, pred_away, T1_CFG)

    return {
        'season': 2026, 'round_label': 'R27 (internal) / official R26',
        'home': home, 'away': away, 'venue': venue, 'date': kickoff,
        'home_elo': round(ELO[home], 1), 'away_elo': round(ELO[away], 1),
        'home_rest_days': h_rest, 'away_rest_days': a_rest,
        'home_travel_km': round(h_km, 0), 'away_travel_km': round(a_km, 0),
        'referee': ref_name, 'ref_bucket': bucket,
        't1_margin': round(t1_home - t1_away, 2),
        't2_hcap': round(t2_home - t2_away, 2), 't2_totals': round(totals_t2, 2),
        't3_hcap': round(t3_home - t3_away, 2), 't3_totals': round(totals_t3, 2),
        't4_hcap': t4['handicap_delta'], 't4_totals': t4['totals_delta'],
        'home_ground_margin_avg': round(home_margin_edge, 2), 'home_ground_n': home_n,
        't5_hcap': t5['handicap_delta'], 't5_totals': t5['totals_delta'],
        't6_hcap': t6['handicap_delta'], 't6_totals': t6['totals_delta'],
        't7_hcap': t7['handicap_delta'], 't7_totals': t7['totals_delta'],
        't7_home_flags': ';'.join(f['flag_type'] for f in flags['home']),
        't7_away_flags': ';'.join(f['flag_type'] for f in flags['away']),
        'pred_home': pred_home, 'pred_away': pred_away,
        'final_margin': round(final_margin, 2), 'final_total': round(final_total, 2),
        'fair_home_odds': prices['fair_home_odds'], 'fair_away_odds': prices['fair_away_odds'],
        'fair_handicap_line': prices['fair_handicap_line'], 'fair_total_line': prices['fair_total_line'],
    }


def main():
    style_by_team = load_style_stats()
    norms = compute_norms(style_by_team)

    print("ELO ratings after Round 25 (2026, single-season, K=20, start=1500):")
    for name, elo in sorted(ELO.items(), key=lambda x: -x[1]):
        print(f"  {name:<32} {elo:>7.1f}  ({elo-1500:+.1f})")

    results = [price_game(h, a, v, d, style_by_team, norms) for h, a, v, d in FIXTURE]

    print(f"\n{'Home':<28}{'Away':<28}{'Pred':<12}{'Margin':>8}{'Total':>8}{'Odds(H/A)':>16}{'Line':>8}")
    for r in results:
        pred = f"{r['pred_home']}-{r['pred_away']}"
        odds = f"{r['fair_home_odds']}/{r['fair_away_odds']}"
        print(f"{r['home']:<28}{r['away']:<28}{pred:<12}{r['final_margin']:>8.2f}"
              f"{r['final_total']:>8.1f}{odds:>16}{r['fair_handicap_line']:>8.1f}")

    out_path = ROOT / "results" / "r27_pricing_2026.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(results[0].keys()))
        w.writeheader()
        w.writerows(results)
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()
