"""
FIFA World Cup 2026 — Round 2 Pricing
6-tier model: T1 ELO baseline | T3 form | T4 altitude | T5 absences | T7 motivation
H2H (home/draw/away) + O2.5 markets

Usage:
    cd C:\\Users\\ElliotBladen\\Apps\\BettingEngine
    python WorldCupEngine/scripts/price_rd2.py
"""
import sys
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "data"
sys.path.insert(0, str(ROOT))

from elo_ratings  import ELO
from rd2_fixtures import RD2_FIXTURES
from rd2_team_data import KEY_ABSENCES, GW1_FORM, MOTIVATION

# ── T1 Model constants ────────────────────────────────────────────────────────
BASE_GOALS  = 1.18    # expected goals per team, equal strength, neutral venue
ELO_SCALE   = 0.003   # each ELO point shifts log-attack by 0.3%
DC_RHO      = -0.13   # Dixon-Coles low-score correction factor
MAX_GOALS   = 10      # truncate Poisson at this

# ── T4 Altitude ───────────────────────────────────────────────────────────────
# Goals reduce ~7% per 1000m at altitude (thin air = less running intensity)
ALTITUDE_FACTOR = -0.000067   # per metre; -0.15 at 2250m, -0.10 at 1566m

# ── T2 Tactical — style matchup multiplier ───────────────────────────────────
# High-press vs low-block clash reduces open play ~3%.
# Both high press = more goals.
# Stored as (attack_bonus, against_bonus) — applied to each team's xG
STYLE_HIGH_PRESS = {"Germany", "England", "Netherlands", "France",
                     "Spain", "Portugal", "Belgium", "Norway",
                     "Brazil", "Argentina", "Colombia", "USA",
                     "Japan", "South Korea", "Morocco", "Croatia"}

def t2_tactical(home, away):
    """Returns (home_mult, away_mult) from style matchup."""
    h_press = home in STYLE_HIGH_PRESS
    a_press = away in STYLE_HIGH_PRESS
    if h_press and a_press:
        return 1.04, 1.04   # open game, more goals both ways
    elif h_press and not a_press:
        return 1.02, 0.97   # home presses, away low-blocks
    elif not h_press and a_press:
        return 0.97, 1.02
    else:
        return 0.99, 0.99   # two low-block teams, slightly fewer goals

# ── Dixon-Coles correction ────────────────────────────────────────────────────
def dc_tau(i, j, lam, mu, rho):
    if i == 0 and j == 0: return max(0.0, 1 - lam * mu * rho)
    if i == 0 and j == 1: return max(0.0, 1 + lam * rho)
    if i == 1 and j == 0: return max(0.0, 1 + mu * rho)
    if i == 1 and j == 1: return max(0.0, 1 - rho)
    return 1.0

def poisson_pmf(k, lam):
    return math.exp(-lam) * (lam ** k) / math.factorial(k)

# ── Full tier pricing ─────────────────────────────────────────────────────────
def price_game(home, away, altitude_m=0):
    # T1: ELO baseline
    elo_home = ELO.get(home, 1500)
    elo_away = ELO.get(away, 1500)
    elo_diff = elo_home - elo_away

    # T4: Altitude adjustment
    alt_adj = altitude_m * ALTITUDE_FACTOR
    base = BASE_GOALS * math.exp(alt_adj)

    lam = base * math.exp( ELO_SCALE * elo_diff / 2)
    mu  = base * math.exp(-ELO_SCALE * elo_diff / 2)

    # T2: Tactical style
    h_t2, a_t2 = t2_tactical(home, away)
    lam *= h_t2
    mu  *= a_t2

    # T3: GW1 form
    lam *= (1.0 + GW1_FORM.get(home, 0.0))
    mu  *= (1.0 + GW1_FORM.get(away, 0.0))

    # T5: Key absences
    lam *= (1.0 + KEY_ABSENCES.get(home, 0.0))
    mu  *= (1.0 + KEY_ABSENCES.get(away, 0.0))

    # T7: Motivation (team's urgency state affects attacking intent)
    lam *= (1.0 + MOTIVATION.get(home, 0.0))
    mu  *= (1.0 + MOTIVATION.get(away, 0.0))

    # Build scoreline matrix
    matrix = {}
    total_prob = 0.0
    for i in range(MAX_GOALS + 1):
        for j in range(MAX_GOALS + 1):
            p = poisson_pmf(i, lam) * poisson_pmf(j, mu) * dc_tau(i, j, lam, mu, DC_RHO)
            p = max(0.0, p)
            matrix[(i, j)] = p
            total_prob += p

    matrix = {k: v / total_prob for k, v in matrix.items()}

    p_home   = sum(p for (i, j), p in matrix.items() if i > j)
    p_draw   = sum(p for (i, j), p in matrix.items() if i == j)
    p_away   = sum(p for (i, j), p in matrix.items() if i < j)
    p_over25 = sum(p for (i, j), p in matrix.items() if i + j >= 3)
    p_btts   = sum(p for (i, j), p in matrix.items() if i >= 1 and j >= 1)
    exp_total = sum((i + j) * p for (i, j), p in matrix.items())

    def fo(p):
        return round(1 / p, 2) if p > 0.001 else 99.0

    return {
        "home":         home,
        "away":         away,
        "elo_home":     elo_home,
        "elo_away":     elo_away,
        "elo_diff":     elo_diff,
        "lam":          round(lam, 3),
        "mu":           round(mu, 3),
        "exp_total":    round(exp_total, 2),
        "p_home":       round(p_home * 100, 1),
        "p_draw":       round(p_draw * 100, 1),
        "p_away":       round(p_away * 100, 1),
        "odds_home":    fo(p_home),
        "odds_draw":    fo(p_draw),
        "odds_away":    fo(p_away),
        "p_over25":     round(p_over25 * 100, 1),
        "odds_over25":  fo(p_over25),
        "p_under25":    round((1 - p_over25) * 100, 1),
        "odds_under25": fo(1 - p_over25),
        "p_btts":       round(p_btts * 100, 1),
    }


def run():
    print()
    print("=" * 100)
    print("  FIFA WORLD CUP 2026 — ROUND 2 (MATCHDAY 2) PRICING")
    print("  Tiers: T1 ELO | T2 Tactical | T3 GW1 Form | T4 Altitude | T5 Absences | T7 Motivation")
    print("  Fair odds — no bookmaker margin applied")
    print("=" * 100)

    # ── Full results table ─────────────────────────────────────────────────────
    print()
    print(f"  {'GRP':<4} {'Date':<7} {'Fixture':<38} {'ELO':>5}  {'H%':>5} {'D%':>5} {'A%':>5}  "
          f"{'1':>6} {'X':>6} {'2':>6}  {'O2.5%':>6} {'O2.5':>6}  {'xG':>5}")
    print("  " + "-" * 104)

    already_played = {"Jun 21"}   # mark these clearly

    results = []
    for group, home, away, venue, altitude, date in RD2_FIXTURES:
        r = price_game(home, away, altitude)
        results.append((group, home, away, venue, altitude, date, r))

        played = " *" if date in already_played else "  "
        alt_note = f"[{altitude}m]" if altitude > 200 else ""
        h_name = home[:16]
        a_name = away[:16]
        fixture = f"{h_name} v {a_name} {alt_note}"
        print(f"{played}{group:<4} {date:<7} {fixture:<38} {r['elo_diff']:>+5}  "
              f"{r['p_home']:>5.1f} {r['p_draw']:>5.1f} {r['p_away']:>5.1f}  "
              f"{r['odds_home']:>6.2f} {r['odds_draw']:>6.2f} {r['odds_away']:>6.2f}  "
              f"{r['p_over25']:>6.1f} {r['odds_over25']:>6.2f}  "
              f"{r['exp_total']:>5.2f}")

    print()
    print("  * = already played (priced for reference)")

    # ── Tier contribution summary ──────────────────────────────────────────────
    print()
    print("  ALTITUDE GAMES (T4 adjustment applied)")
    print("  " + "-" * 55)
    for group, home, away, venue, altitude, date, r in results:
        if altitude > 200:
            alt_factor = round(math.exp(altitude * ALTITUDE_FACTOR), 3)
            reduction = round((1 - alt_factor) * 100, 1)
            print(f"  {group}  {home} v {away} @ {venue} ({altitude}m) "
                  f"xG base reduced {reduction}% -> total xG {r['exp_total']:.2f}")

    # ── O2.5 signals ──────────────────────────────────────────────────────────
    print()
    print("  O2.5 SIGNALS (>62% = value OVER / <38% = value UNDER)")
    print("  " + "-" * 65)
    signals = []
    for group, home, away, venue, altitude, date, r in results:
        if r["p_over25"] >= 62.0:
            signals.append((r["p_over25"], "OVER",  group, home, away, r["odds_over25"],  altitude, date))
        elif r["p_over25"] <= 38.0:
            signals.append((r["p_over25"], "UNDER", group, home, away, r["odds_under25"], altitude, date))
    signals.sort(reverse=True, key=lambda x: x[0] if x[1]=="OVER" else 100 - x[0])

    if signals:
        for prob, side, group, home, away, odds, alt, date in signals:
            direction = "O2.5" if side == "OVER" else "U2.5"
            alt_note = f" [{alt}m alt]" if alt > 200 else ""
            print(f"  {group}  {date}  {home} v {away}{alt_note}  "
                  f">>> {direction}  {prob:.1f}%  fair odds {odds:.2f}")
    else:
        print("  No strong signals this round.")

    # ── H2H confidence picks ───────────────────────────────────────────────────
    print()
    print("  H2H CONFIDENCE PICKS (>70% win probability)")
    print("  " + "-" * 65)
    picks = []
    for group, home, away, venue, altitude, date, r in results:
        if r["p_home"] >= 70.0:
            picks.append((r["p_home"], group, home, "to win", away, r["odds_home"], altitude, date))
        elif r["p_away"] >= 70.0:
            picks.append((r["p_away"], group, away, "to win", home, r["odds_away"], altitude, date))
    picks.sort(reverse=True)
    if picks:
        for prob, group, team, label, opponent, odds, alt, date in picks:
            print(f"  {group}  {date}  {team} {label} vs {opponent}  "
                  f"{prob:.1f}%  fair odds {odds:.2f}")
    else:
        print("  None above 70% threshold.")

    # ── Draw probability watch ─────────────────────────────────────────────────
    print()
    print("  DRAW WATCH (>28% draw probability — consider DNB or draw backing)")
    print("  " + "-" * 65)
    for group, home, away, venue, altitude, date, r in results:
        if r["p_draw"] >= 28.0:
            print(f"  {group}  {date}  {home} v {away}  "
                  f"draw {r['p_draw']:.1f}%  @ {r['odds_draw']:.2f}")

    # ── Notes ──────────────────────────────────────────────────────────────────
    print()
    print("  NOTES")
    print("  " + "-" * 65)
    print("  T1: ELO ratings from eloratings.net methodology (late 2025).")
    print("  T2: Style matchup — high press vs low block adjusts xG +/-3%.")
    print("  T3: GW1 form defaults to +4% for expected WC1 winners. Update")
    print("      rd2_team_data.py GW1_FORM with actual results before betting.")
    print("  T4: Altitude — Mexico City 2250m (-15% goals), Guadalajara 1566m (-10%),")
    print("      Monterrey 560m (-4%).")
    print("  T5: KEY_ABSENCES in rd2_team_data.py — fill with confirmed injuries.")
    print("  T7: MOTIVATION in rd2_team_data.py — flag GW1 losers (+5%) and")
    print("      GW1 winners that can afford caution (-2%).")
    print()


if __name__ == "__main__":
    run()
