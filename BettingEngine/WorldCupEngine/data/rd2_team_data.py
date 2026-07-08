# Round 2 team-level data for tiers T3, T5, T7
# Fill in after GW1 results and injury news are known.
# adj values are goal-rate multipliers applied to that team's lambda/mu.

# ── T5: Key absences ─────────────────────────────────────────────────────────
# Format: team → cumulative goal-rate impact (negative = weaker attack/defence)
# e.g. -0.08 means 8% fewer goals expected (elite forward missing)
KEY_ABSENCES = {
    # Fill after team news confirmed pre-matchday.
    # Examples:
    # "France":    -0.04,   # if Mbappe doubtful
    # "Brazil":    -0.06,   # if Vinicius doubtful
}

# ── T3: GW1 Form (fill after results are in) ──────────────────────────────────
# +0.04 = team won GW1, slight confidence boost
# -0.04 = team lost GW1, slight confidence hit
# 0.00  = drew GW1 or no data
GW1_FORM = {
    "Spain":                +0.04,
    "Uruguay":              +0.04,
    "Belgium":              +0.04,
    "France":               +0.04,
    "Argentina":            +0.04,
    "Portugal":              0.00,   # drew 1-1 vs DR Congo R1
    "England":              +0.04,   # won 4-2 vs Croatia R1
    "Germany":              +0.04,
    "Netherlands":          +0.04,
    "Brazil":               +0.04,
    "USA":                  +0.04,
    "South Korea":          +0.04,
    "Morocco":              +0.04,
    "Colombia":             +0.04,   # won 3-1 vs Uzbekistan R1
    "Norway":               +0.04,
    # Group K R1 results
    "DR Congo":              0.00,   # drew 1-1 vs Portugal R1 (positive as underdog)
    "Congo DR":              0.00,
    "Uzbekistan":           -0.04,   # lost 1-3 vs Colombia R1
    # Group L R1 results
    "Ghana":                +0.04,   # won 1-0 vs Panama R1
    "Croatia":              -0.04,   # lost 2-4 vs England R1
    "Panama":               -0.04,   # lost 0-1 vs Ghana R1
}

# ── T7: Motivation (GW2 context) ─────────────────────────────────────────────
# Baseline for GW2: mild. Teams that lost GW1 are under pressure (+5% goal rate).
# Teams that won GW1 may be slightly cautious (-2%).
# Format: team → attack-rate multiplier
# GW1 losers should get +0.05, GW1 winners -0.02, draws 0.0
MOTIVATION = {
    # Group K R2 (Jun 23)
    "Portugal":             +0.04,   # 1pt after draw — needs win to stay on track
    "Uzbekistan":           +0.06,   # 0pts, must win
    "Colombia":             -0.02,   # 3pts, comfortable
    "DR Congo":             +0.03,   # 1pt, needs a result
    "Congo DR":             +0.03,
    # Group L R2 (Jun 23)
    "England":              -0.02,   # 3pts, comfortable
    "Ghana":                -0.02,   # 3pts, comfortable
    "Croatia":              +0.06,   # 0pts, must win
    "Panama":               +0.06,   # 0pts, must win
}

# Default fall-through: 0.0 (no adjustment)
