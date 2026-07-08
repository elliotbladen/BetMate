# FIFA World Cup 2026 — R32 Bracket
# Fill in BRACKET after group stage is complete (Jun 27).
# Order matters: index 0 vs 1, 2 vs 3, 4 vs 5 ... 30 vs 31
# Winners of slots 0-1 meet in R16, then R16 winners meet in QF, etc.
# The bracket is split into two halves — teams in the same half can only
# meet in the Final.
#
# HOW TO FILL IN:
#   Replace each None with the actual team name string (must match ELO key).
#   The bracket structure below follows the FIFA 2026 pre-draw seeding pods.
#   Group winners are labelled W-X, runners-up R-X, best-thirds T-X.
#
# FIFA 2026 R32 bracket grouping (4 pods of 8, winners of each pod = 2 QF spots):
#
#   POD 1 (slots  0- 7): Groups A/B/C winners + associated runners-up/3rds
#   POD 2 (slots  8-15): Groups D/E/F winners + associated runners-up/3rds
#   POD 3 (slots 16-23): Groups G/H/I winners + associated runners-up/3rds
#   POD 4 (slots 24-31): Groups J/K/L winners + associated runners-up/3rds
#
# Semi-final matchups: Pod1-winner vs Pod2-winner, Pod3-winner vs Pod4-winner

# R32 bracket from image — Jun 24 2026 after group stage complete
#
# STRUCTURE: slots 0v1, 2v3 ... winners meet in R16. Then R16 pairs → QF pairs → SF → Final.
# LEFT HALF  (slots  0-15): one side of bracket → meet in one SF
# RIGHT HALF (slots 16-31): other side          → meet in other SF
#
# R3 ELO notes baked into elo_ratings.py:
#   Scotland beat Brazil  (+31 / -31)
#   Sweden   beat Japan   (+19 / -19)
#   Brazil / Japan qualify as best 3rd-place teams
#
# Uncertain slots marked with # est.

BRACKET = [
    # ── LEFT HALF ────────────────────────────────────────────────────────
    # Quarter 1 — Germany / France section  [HARDEST per user]
    "Germany",        # slot  0  )  R32 game 1
    "Scotland",       # slot  1  )
    "France",         # slot  2  )  R32 game 2  → R16 vs game-1 winner
    "Sweden",         # slot  3  )
    "South Korea",    # slot  4  )  R32 game 3
    "Switzerland",    # slot  5  )
    "Netherlands",    # slot  6  )  R32 game 4  → R16 vs game-3 winner → QF vs Q1
    "Morocco",        # slot  7  )

    # Quarter 2 — Spain / USA section  [EASIEST per user for Spain]
    "DR Congo",       # slot  8  )  R32 game 5
    "Ghana",          # slot  9  )
    "Spain",          # slot 10  )  R32 game 6  → R16 vs game-5 winner
    "Austria",        # slot 11  )
    "USA",            # slot 12  )  R32 game 7
    "Algeria",        # slot 13  )
    "Egypt",          # slot 14  )  R32 game 8  → R16 vs game-7 winner → QF vs Q2
    "Czechia",        # slot 15  )  # est. — flag partially visible

    # ── RIGHT HALF ───────────────────────────────────────────────────────
    # Quarter 3 — Brazil / Mexico section  [MEDIUM per user]
    "Brazil",         # slot 16  )  R32 game 9   (qualified as best 3rd)
    "Japan",          # slot 17  )               (qualified as best 3rd)
    "Ivory Coast",    # slot 18  )  R32 game 10  → R16 vs game-9 winner
    "Norway",         # slot 19  )
    "Mexico",         # slot 20  )  R32 game 11
    "Cabo Verde",     # slot 21  )
    "England",        # slot 22  )  R32 game 12  → R16 vs game-11 winner → QF vs Q3
    "Portugal",       # slot 23  )

    # Quarter 4 — Argentina / Canada section  [EASY per user for Argentina]
    "Argentina",      # slot 24  )  R32 game 13
    "Uruguay",        # slot 25  )
    "Iran",           # slot 26  )  R32 game 14  → R16 vs game-13 winner  # est.
    "Australia",      # slot 27  )
    "Canada",         # slot 28  )  R32 game 15
    "Belgium",        # slot 29  )
    "Colombia",       # slot 30  )  R32 game 16  → R16 vs game-15 winner → QF vs Q4
    "Paraguay",       # slot 31  )
]

# ── EXAMPLE (fill these in after group stage) ─────────────────────────────
# BRACKET = [
#     "Mexico",        # slot  0
#     "South Korea",   # slot  1
#     "Canada",        # slot  2
#     "Switzerland",   # slot  3
#     ...
# ]
