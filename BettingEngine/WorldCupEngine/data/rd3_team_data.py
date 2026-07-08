# Round 3 team data — T3 form, T5 absences, T7 motivation
# Based on actual group standings after Matchday 2.

KEY_ABSENCES = {
}

# T3: Tournament form — 2 games played, calibrated to points/goals
GW_FORM = {
    # Group A
    "Mexico":          +0.04,   # 6pts, W2, clinical
    "South Korea":     +0.01,   # 3pts, W1 L1
    "Czechia":         -0.01,   # 1pt, D1 L1
    "South Africa":    -0.02,   # 1pt, D1 L1
    # Group B
    "Canada":          +0.04,   # 4pts, W1 D1 — 7 goals scored
    "Switzerland":     +0.02,   # 4pts, W1 D1
    "Bosnia-Herzegovina": -0.01,# 1pt, D1 L1
    "Qatar":           -0.03,   # 1pt, D1 L1 — -6 GD, effectively out
    # Group C
    "Brazil":          +0.02,   # 4pts — conservative style
    "Morocco":         +0.03,   # 4pts — strong defensive record
    "Scotland":        +0.01,   # 3pts, W1 L1
    "Haiti":           -0.04,   # 0pts, L2 — eliminated, low morale
    # Group D
    "USA":             +0.04,   # 6pts, W2 — 6 goals scored
    "Australia":       +0.02,   # 3pts, W1 L1
    "Paraguay":        +0.02,   # 3pts, W1 L1
    "Türkiye":         -0.04,   # 0pts, L2 — eliminated
    "Turkey":          -0.04,
    # Group E
    "Germany":         +0.05,   # 6pts, W2 — 9 goals scored
    "Ivory Coast":     +0.01,   # 3pts, W1 L1
    "Ecuador":         -0.02,   # 1pt, D1 L1
    "Curaçao":         -0.03,   # 1pt, D1 L1 — -6 GD
    "Curacao":         -0.03,
    # Group F
    "Netherlands":     +0.03,   # 4pts, W1 D1 — 7 goals
    "Japan":           +0.03,   # 4pts, W1 D1 — 6 goals
    "Sweden":          +0.01,   # 3pts, W1 L1 — beaten heavily by NED
    "Tunisia":         -0.04,   # 0pts, L2 — eliminated, -8 GD
    # Group G
    "Egypt":           +0.04,   # 4pts, W1 D1
    "Iran":            +0.01,   # 2pts, D2 — solid defensive
    "Belgium":         +0.00,   # 2pts, D2 — 0 goals in last 2 games
    "New Zealand":     -0.02,   # 1pt, D1 L1
    # Group H
    "Spain":           +0.03,   # 4pts, W1 D1
    "Uruguay":         +0.00,   # 2pts, D2 — failing to convert chances
    "Cape Verde":      +0.01,   # 2pts, D2 — punching above weight
    "Saudi Arabia":    -0.02,   # 1pt, D1 L1
    # Group I — R2 complete
    "France":          +0.05,   # 6pts W2, 6 goals scored — in form
    "Norway":          +0.04,   # 6pts W2, Haaland 4 goals in tournament
    "Senegal":         -0.03,   # 0pts L2, eliminated, low morale
    "Iraq":            -0.04,   # 0pts L2, -7 GD, eliminated

    # Group J
    "Argentina":       +0.05,   # 6pts W2, Messi 5 WC goals (all-time record)
    "Algeria":         +0.00,   # 3pts W1 L1 — won vs Jordan only
    "Austria":         +0.01,   # 3pts W1 L1 — beat Jordan, lost to Argentina
    "Jordan":          -0.03,   # 0pts L2, eliminated

    # Group K
    "Portugal":        +0.03,   # 4pts D1 W1, Ronaldo brace vs Uzbekistan
    "Colombia":        +0.04,   # est. 6pts W2 — strong tournament form
    "DR Congo":        -0.01,   # est. 1pt D1 L1
    "Uzbekistan":      -0.04,   # 0pts L2, eliminated

    # Group L
    "England":         +0.03,   # 4pts W1 D1, solid if unspectacular
    "Panama":          -0.04,   # 0pts L2, eliminated, -2 GD
    "Croatia":         +0.01,   # 3pts W1 L1 — won vs Panama, lost to England
    "Ghana":           +0.02,   # 4pts W1 D1 — held England 0-0 impressive
}

# T7: Motivation — elimination stakes, Matchday 3
# Scale: +0.07 = must-win/desperate, 0.0 = neutral, -0.05 = qualified/rotating
MOTIVATION = {
    # Group A
    "Mexico":          -0.05,   # Qualified — will rotate squad
    "South Korea":     +0.03,   # Need win or draw + SA slips
    "Czechia":         +0.06,   # Must win to have any chance
    "South Africa":    +0.06,   # Must win to have any chance
    # Group B
    "Canada":          -0.02,   # Win or draw advances
    "Switzerland":     -0.02,   # Win or draw advances
    "Bosnia-Herzegovina": +0.06,# Must win
    "Qatar":           +0.00,   # Effectively eliminated, nothing to play for
    # Group C
    "Brazil":          -0.02,   # Advance with draw
    "Morocco":         +0.02,   # Win to be safe, draw risky
    "Scotland":        +0.07,   # Must beat Brazil — huge stakes
    "Haiti":           +0.00,   # Eliminated
    # Group D
    "USA":             -0.05,   # Qualified — rotating
    "Australia":       +0.05,   # Must win vs Paraguay
    "Paraguay":        +0.05,   # Must win vs Australia
    "Türkiye":         +0.00,   # Eliminated
    "Turkey":          +0.00,
    # Group E
    "Germany":         -0.04,   # Qualified — rotating
    "Ivory Coast":     +0.05,   # Must win to qualify
    "Ecuador":         +0.03,   # Long shot, still fighting
    "Curaçao":         +0.00,   # Effectively eliminated
    "Curacao":         +0.00,
    # Group F
    "Netherlands":     -0.02,   # Advance almost certain
    "Japan":           -0.02,   # Advance almost certain
    "Sweden":          +0.06,   # Must win to qualify
    "Tunisia":         +0.00,   # Eliminated
    # Group G
    "Egypt":           -0.02,   # 4pts, can draw and advance
    "Iran":            +0.05,   # 2pts, needs win
    "Belgium":         +0.05,   # 2pts, needs win
    "New Zealand":     +0.04,   # 1pt, needs miracle
    # Group H
    "Spain":           -0.03,   # 4pts, draw likely enough
    "Uruguay":         +0.05,   # 2pts, needs win vs Spain
    "Cape Verde":      +0.04,   # 2pts, needs win vs Saudi
    "Saudi Arabia":    +0.06,   # 1pt, must win
    # Group I — R2 complete
    "France":          -0.04,   # 6pts, qualified — rotating squad
    "Norway":          -0.02,   # 6pts, qualified — Haaland may rest
    "Senegal":         +0.00,   # 0pts, eliminated — nothing to play for
    "Iraq":            +0.00,   # 0pts, eliminated

    # Group J
    "Argentina":       -0.05,   # 6pts, qualified — rotating (Messi may rest)
    "Algeria":         +0.06,   # 3pts (GD -2), must win AND Austria must slip to advance
    "Austria":         +0.03,   # 3pts (GD 0), draw likely enough — in 2nd on GD
    "Jordan":          +0.00,   # 0pts, eliminated

    # Group K (Colombia vs DRC result est. — Colombia 6pts, Portugal 4pts)
    "Portugal":        +0.02,   # 4pts, win seals top spot; draw may be enough
    "Colombia":        -0.03,   # est. 6pts, qualified — some rotation possible
    "DR Congo":        +0.05,   # est. 1pt, needs result vs Uzbekistan to stay alive as 3rd
    "Uzbekistan":      +0.00,   # 0pts, eliminated

    # Group L
    "England":         -0.04,   # 4pts, draw vs Panama enough — resting key players
    "Panama":          +0.00,   # 0pts, eliminated — pride only
    "Croatia":         +0.06,   # 3pts, must beat Ghana (win only)
    "Ghana":           -0.02,   # 4pts, draw vs Croatia advances — cautious approach
}
