# FIFA World Cup 2026 — Round 2 (Matchday 2) fixtures
# Format: (group, home, away, venue, altitude_m, date)
# Source: ESPN WC2026 schedule / FIFA official draw
# Altitude venues: Mexico City ~2250m, Guadalajara ~1566m, Monterrey/Guadalupe ~560m

RD2_FIXTURES = [
    # ── Group G / H (June 21 — already played) ──────────────────────────────
    ("G", "Spain",               "Saudi Arabia",    "Dallas",          0,    "Jun 21"),
    ("G", "Uruguay",             "Cape Verde",      "Miami",           0,    "Jun 21"),
    ("H", "Belgium",             "Iran",            "New York",        0,    "Jun 21"),
    ("H", "New Zealand",         "Egypt",           "Vancouver",       0,    "Jun 21"),

    # ── Group I / J (June 22) ────────────────────────────────────────────────
    ("J", "Argentina",           "Austria",         "Dallas",          0,    "Jun 22"),
    ("I", "France",              "Iraq",            "Philadelphia",    0,    "Jun 22"),
    ("I", "Norway",              "Senegal",         "New York",        0,    "Jun 22"),
    ("J", "Jordan",              "Algeria",         "Santa Clara",     0,    "Jun 22"),

    # ── Group K / L (June 23) ────────────────────────────────────────────────
    ("K", "Portugal",            "Uzbekistan",      "Houston",         0,    "Jun 23"),
    ("L", "England",             "Ghana",           "Boston",          0,    "Jun 23"),
    ("L", "Panama",              "Croatia",         "Toronto",         0,    "Jun 23"),
    ("K", "Colombia",            "Congo DR",        "Guadalajara",  1566,    "Jun 23"),

    # ── Group A / B / C (June 24) ────────────────────────────────────────────
    ("B", "Bosnia-Herzegovina",  "Qatar",           "Seattle",         0,    "Jun 24"),
    ("B", "Switzerland",         "Canada",          "Vancouver",       0,    "Jun 24"),
    ("C", "Morocco",             "Haiti",           "Atlanta",         0,    "Jun 24"),
    ("C", "Brazil",              "Scotland",        "Miami",           0,    "Jun 24"),
    ("A", "Mexico",              "Czechia",         "Mexico City",  2250,    "Jun 24"),
    ("A", "South Korea",         "South Africa",    "Monterrey",     560,    "Jun 24"),

    # ── Group D / E / F (June 25) ────────────────────────────────────────────
    ("E", "Curacao",             "Ivory Coast",     "Philadelphia",    0,    "Jun 25"),
    ("E", "Germany",             "Ecuador",         "New York",        0,    "Jun 25"),
    ("F", "Sweden",              "Japan",           "Dallas",          0,    "Jun 25"),
    ("F", "Netherlands",         "Tunisia",         "Kansas City",     0,    "Jun 25"),
    ("D", "Australia",           "Paraguay",        "Santa Clara",     0,    "Jun 25"),
    ("D", "USA",                 "Türkiye",         "Inglewood",       0,    "Jun 25"),
]
