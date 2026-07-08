# Knockout context layer for World Cup 2026 pricing.
#
# This file keeps the round-specific non-ELO adjustments in one place:
# - environment: altitude / host acclimatisation / venue context
# - pressure: late-round shootout composure
# Future factors (recovery, referee, set pieces, keeper quality) can be
# attached here once a verified input layer exists.

ALTITUDE_FACTOR = -0.000067

VENUE_CONTEXT = {
    "Boston Stadium": {"altitude_m": 0, "host_team": None},
    "Dallas Stadium": {"altitude_m": 0, "host_team": None},
    "Los Angeles Stadium": {"altitude_m": 0, "host_team": None},
    "Mexico City Stadium": {"altitude_m": 2250, "host_team": "Mexico"},
    "Miami Stadium": {"altitude_m": 0, "host_team": None},
    "Monterrey Stadium": {"altitude_m": 0, "host_team": None},
    "New York/New Jersey Stadium": {"altitude_m": 0, "host_team": None},
    "San Francisco Bay Stadium": {"altitude_m": 0, "host_team": "USA"},
    "Seattle Stadium": {"altitude_m": 0, "host_team": None},
    "Toronto Stadium": {"altitude_m": 0, "host_team": None},
    "BC Place Vancouver": {"altitude_m": 0, "host_team": None},
}

# Late-round pressure/composure proxy. Very small by design.
PRESSURE_EDGE_BY_ROUND = {
    0: 0.000,  # R32
    1: 0.000,  # R16
    2: 0.004,  # QF
    3: 0.007,  # SF
    4: 0.010,  # Final
}

# Hooks for future tier work. Kept neutral until a verified input layer exists.
RECOVERY_EDGE_BY_ROUND = {0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0}
REFEREE_EDGE = {}
SET_PIECE_EDGE = {}
KEEPER_EDGE = {}
