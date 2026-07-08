# FIFA World Cup 2026 — Round 3 (Matchday 3) — ALL 24 GAMES (Jun 24-27)
# Groups A-L: ELO fully updated (R1+R2 complete, Groups A-H + I + J + L; K est.)
# Format: (group, team_a, team_b, venue, altitude_m, date)
# Source: CBS Sports / ESPN / FIFA WC2026 schedule

RD3_FIXTURES_12 = [
    # ── June 24 — Groups A, B, C ─────────────────────────────────────────────
    # Group A: Standings — Mexico 6 | SK 3 | Czechia 1 | SA 1
    ("A", "Czechia",          "Mexico",        "Mexico City",   2250, "Jun 24"),  # Mexico qualified
    ("A", "South Africa",     "South Korea",   "Monterrey",      560, "Jun 24"),

    # Group B: Standings — Canada 4 | Switzerland 4 | Bosnia 1 | Qatar 1
    ("B", "Switzerland",      "Canada",        "Vancouver",        0, "Jun 24"),
    ("B", "Bosnia-Herzegovina","Qatar",         "Seattle",          0, "Jun 24"),

    # Group C: Standings — Brazil 4 | Morocco 4 | Scotland 3 | Haiti 0
    ("C", "Scotland",         "Brazil",        "Miami",            0, "Jun 24"),
    ("C", "Morocco",          "Haiti",         "Atlanta",          0, "Jun 24"),  # AC [Mercedes-Benz]

    # ── June 25 — Groups D, E, F ─────────────────────────────────────────────
    # Group D: Standings — USA 6 | Australia 3 | Paraguay 3 | Türkiye 0
    ("D", "Türkiye",          "USA",           "Inglewood",        0, "Jun 25"),  # USA qualified
    ("D", "Paraguay",         "Australia",     "Santa Clara",      0, "Jun 25"),

    # Group E: Standings — Germany 6 | Ivory Coast 3 | Ecuador 1 | Curaçao 1
    ("E", "Ecuador",          "Germany",       "New York",         0, "Jun 25"),  # Germany qualified
    ("E", "Curaçao",          "Ivory Coast",   "Philadelphia",     0, "Jun 25"),

    # Group F: Standings — Netherlands 4 | Japan 4 | Sweden 3 | Tunisia 0
    ("F", "Japan",            "Sweden",        "Dallas",           0, "Jun 25"),  # AC [AT&T Stadium]
    ("F", "Tunisia",          "Netherlands",   "Kansas City",      0, "Jun 25"),

    # ── June 26 — Groups G, H, I, J ──────────────────────────────────────────
    # Group G: Standings — Egypt 4 | Iran 2 | Belgium 2 | New Zealand 1
    ("G", "Egypt",            "Iran",          "Seattle",          0, "Jun 26"),
    ("G", "New Zealand",      "Belgium",       "Vancouver",        0, "Jun 26"),

    # Group H: Standings — Spain 4 | Uruguay 2 | Cape Verde 2 | Saudi Arabia 1
    ("H", "Uruguay",          "Spain",         "Guadalajara",   1566, "Jun 26"),  # altitude
    ("H", "Cape Verde",       "Saudi Arabia",  "Houston",          0, "Jun 26"),  # AC [NRG Stadium]

    # Group I: Standings — France 6 | Norway 6 | Senegal 0 | Iraq 0
    ("I", "Norway",           "France",        "Boston",           0, "Jun 26"),
    ("I", "Senegal",          "Iraq",          "Toronto",          0, "Jun 26"),

    # Group J: Standings — Argentina 6 | Austria 3 (GD 0) | Algeria 3 (GD -2) | Jordan 0
    ("J", "Jordan",           "Argentina",     "Dallas",           0, "Jun 26"),  # AC [AT&T Stadium]
    ("J", "Algeria",          "Austria",       "Kansas City",      0, "Jun 26"),

    # ── June 27 — Groups K, L ────────────────────────────────────────────────
    # Group K: Standings est. — Colombia 6 | Portugal 4 | DR Congo 1 | Uzbekistan 0
    # NOTE: Colombia vs DR Congo (Jun 24 02:00 UTC) ELO estimated — verify result
    ("K", "Portugal",         "Colombia",      "Miami",            0, "Jun 27"),
    ("K", "DR Congo",         "Uzbekistan",    "Guadalajara",   1566, "Jun 27"),  # altitude est.

    # Group L: Standings — England 4 | Ghana 4 | Croatia 3 | Panama 0
    ("L", "Panama",           "England",       "New York",         0, "Jun 27"),
    ("L", "Croatia",          "Ghana",         "Philadelphia",     0, "Jun 27"),
]
