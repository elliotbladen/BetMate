"""
FIFA World Cup 2026 — Knockout Stage Monte Carlo Simulation
===========================================================
Run AFTER group stage is complete and bracket.py is filled in.

Usage:
    cd C:\\Users\\ElliotBladen\\Apps\\BettingEngine
    python WorldCupEngine/scripts/simulate_knockout.py
    python WorldCupEngine/scripts/simulate_knockout.py --sims 200000
    python WorldCupEngine/scripts/simulate_knockout.py --target "Brazil"
    python WorldCupEngine/scripts/simulate_knockout.py --market-odds odds.csv

What it does:
    1. Loads the 32-team R32 bracket from data/bracket.py
    2. Simulates N full tournaments using the Dixon-Coles Poisson model
    3. Tracks each team's probability of reaching R16 / QF / SF / Final / Win
    4. Prints a ranked table + flags value vs bookmaker implied odds
"""
import sys
import math
import random
import argparse
import csv
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent / "data"
sys.path.insert(0, str(ROOT))

from elo_ratings import ELO
from bracket    import BRACKET
from r32_team_data import ATTACK_ABSENCES, DEFENCE_ABSENCES
from knockout_context import ALTITUDE_FACTOR, PRESSURE_EDGE_BY_ROUND, VENUE_CONTEXT

# ── Model constants (same as price_rd3.py) ───────────────────────────────
BASE_GOALS = 1.18
ELO_SCALE  = 0.003
DC_RHO     = -0.13
MAX_GOALS  = 10
PENALTIES_HOME_EDGE = 0.02   # slight edge to "home side" in bracket (arbitrary)
K_KNOCKOUT = 40              # ELO K-factor (not used mid-sim, but for reference)

HIGH_PRESS = {
    "Germany", "England", "Netherlands", "France", "Spain",
    "Portugal", "Belgium", "Norway", "Brazil", "Argentina",
    "Colombia", "USA", "Japan", "South Korea", "Morocco",
    "Croatia", "Scotland", "Switzerland", "Uruguay",
}

# Late-round pressure/composure proxy.
# This is deliberately tiny: shootouts in the knockouts are where pressure
# shows up most clearly, and the effect should stay smaller than ELO.
SHOOTOUT_PRESSURE_BONUS = {
    0: 0.000,  # R32
    1: 0.000,  # R16
    2: 0.004,  # QF
    3: 0.007,  # SF
    4: 0.010,  # Final
}


# ── Core probability engine ───────────────────────────────────────────────

def t2_tactical(a, b):
    ha, hb = a in HIGH_PRESS, b in HIGH_PRESS
    if ha and hb:       return 1.04, 1.04
    elif ha and not hb: return 1.02, 0.97
    elif not ha and hb: return 0.97, 1.02
    else:               return 0.99, 0.99


def dc_tau(i, j, lam, mu, rho):
    if i == 0 and j == 0: return max(0, 1 - lam * mu * rho)
    if i == 0 and j == 1: return max(0, 1 + lam * rho)
    if i == 1 and j == 0: return max(0, 1 + mu * rho)
    if i == 1 and j == 1: return max(0, 1 - rho)
    return 1.0


def poisson_pmf(k, lam):
    return math.exp(-lam) * (lam ** k) / math.factorial(k)


def late_round_pressure_edge(round_idx, ea, eb):
    """
    Tiny shootout adjustment for the final rounds.

    Positive means team A gets a small composure edge in penalties.
    The effect grows from QF onward and is capped at a few basis points.
    """
    if ea == eb:
        return 0.0
    base = PRESSURE_EDGE_BY_ROUND.get(round_idx, 0.0)
    return base if ea > eb else -base


def apply_venue_context(lam, mu, a, b, venue=None):
    """
    Apply venue-specific environment adjustments.

    Current numeric effects:
    - altitude reduces both teams' scoring rates
    - host acclimatisation gives a small differential bump
    """
    profile = VENUE_CONTEXT.get(venue or "", {})
    altitude_m = profile.get("altitude_m", 0) or 0
    if altitude_m:
        scale = math.exp(altitude_m * ALTITUDE_FACTOR)
        lam *= scale
        mu *= scale

    host = profile.get("host_team")
    if host == a:
        lam *= 1.02
        mu *= 0.99
    elif host == b:
        lam *= 0.99
        mu *= 1.02

    return lam, mu


def build_score_matrix(ea, eb, a, b, venue=None):
    """Return normalised (score_a, score_b) -> probability dict."""
    diff = ea - eb
    lam  = BASE_GOALS * math.exp( ELO_SCALE * diff / 2)
    mu   = BASE_GOALS * math.exp(-ELO_SCALE * diff / 2)
    ta, tb = t2_tactical(a, b)
    lam *= ta
    mu  *= tb
    lam *= (1.0 + ATTACK_ABSENCES.get(a, 0.0)) * (1.0 + DEFENCE_ABSENCES.get(b, 0.0))
    mu  *= (1.0 + ATTACK_ABSENCES.get(b, 0.0)) * (1.0 + DEFENCE_ABSENCES.get(a, 0.0))
    lam, mu = apply_venue_context(lam, mu, a, b, venue=venue)

    mat, tot = {}, 0.0
    for i in range(MAX_GOALS + 1):
        for j in range(MAX_GOALS + 1):
            p = max(0, poisson_pmf(i, lam) * poisson_pmf(j, mu)
                    * dc_tau(i, j, lam, mu, DC_RHO))
            mat[(i, j)] = p
            tot += p
    return {k: v / tot for k, v in mat.items()}, lam, mu


def win_prob_90(ea, eb, a, b):
    """Return (p_a_wins_90, p_draw_90, p_b_wins_90)."""
    mat, _, _ = build_score_matrix(ea, eb, a, b)
    pa = sum(p for (i, j), p in mat.items() if i > j)
    pd = sum(p for (i, j), p in mat.items() if i == j)
    pb = sum(p for (i, j), p in mat.items() if i < j)
    return pa, pd, pb


def sample_winner(a, b, elo_cache, round_idx=0):
    """
    Sample knockout winner from one game.
    Uses 90-min Poisson model; draws go to ET/pens with
    slight ELO-weighted edge for the stronger team.
    Returns winning team name.
    """
    ea = elo_cache.get(a, ELO.get(a, 1500))
    eb = elo_cache.get(b, ELO.get(b, 1500))

    pa, pd, pb = win_prob_90(ea, eb, a, b)

    r = random.random()
    if r < pa:
        return a                   # Team A wins in 90 min
    elif r < pa + pb:
        return b                   # Team B wins in 90 min
    else:
        # Draw -> ET/penalties: ELO-weighted 50/50 with small bias
        pen_a = 0.5 + (ea - eb) / 4000   # e.g. +100 ELO = 52.5% pens
        pen_a += late_round_pressure_edge(round_idx, ea, eb)
        pen_a = max(0.35, min(0.65, pen_a))
        return a if random.random() < pen_a else b


def simulate_one_tournament(bracket, elo_cache):
    """
    Simulate one full tournament from R32 to Final.
    Returns dict: team -> furthest round reached
    (0=R32, 1=R16, 2=QF, 3=SF, 4=Final, 5=Winner)
    """
    teams = list(bracket)   # 32 teams, paired 0v1, 2v3, ...
    progress = {t: 0 for t in teams}   # all start at R32

    round_names = ["R32", "R16", "QF", "SF", "Final", "Winner"]

    for rnd in range(5):   # R32→R16→QF→SF→Final = 5 rounds
        next_round = []
        for i in range(0, len(teams), 2):
            a, b = teams[i], teams[i + 1]
            winner = sample_winner(a, b, elo_cache, rnd)
            loser  = b if winner == a else a
            progress[winner] = rnd + 1   # advance to next round
            next_round.append(winner)
        teams = next_round

    # The last team standing is the winner
    if teams:
        progress[teams[0]] = 5

    return progress


def run_simulation(bracket, n_sims=100_000):
    """Run N simulations, return cumulative advancement counts."""
    elo_cache = dict(ELO)   # snapshot — don't modify during sim

    counts = defaultdict(lambda: [0] * 6)   # team -> [R32, R16, QF, SF, Final, Win]

    for _ in range(n_sims):
        result = simulate_one_tournament(bracket, elo_cache)
        for team, reached in result.items():
            for rnd in range(reached + 1):
                counts[team][rnd] += 1

    # Convert to probabilities
    probs = {}
    for team, cnt in counts.items():
        probs[team] = [c / n_sims for c in cnt]

    return probs


# ── Value finder ──────────────────────────────────────────────────────────

def decimal_to_implied(odd):
    return 1.0 / odd if odd > 1.0 else None


def find_value(probs, market_odds, threshold=0.05):
    """
    Compare MC probabilities to market implied odds.
    Returns list of (team, market, edge%) sorted by edge descending.
    market_odds: dict of team -> {"sf": 5.0, "final": 9.0, "win": 18.0}
    """
    value_plays = []
    round_keys = {3: "sf", 4: "final", 5: "win"}

    for team, p_list in probs.items():
        if team not in market_odds:
            continue
        for rnd_idx, mkt_key in round_keys.items():
            if mkt_key not in market_odds[team]:
                continue
            mkt_odd = market_odds[team][mkt_key]
            implied = decimal_to_implied(mkt_odd)
            if implied is None:
                continue
            model_p = p_list[rnd_idx]
            edge = model_p - implied
            if edge > threshold:
                fair_odd = round(1 / model_p, 2) if model_p > 0 else 99.0
                value_plays.append({
                    "team": team,
                    "market": mkt_key.upper(),
                    "model_p": round(model_p * 100, 1),
                    "implied_p": round(implied * 100, 1),
                    "edge_pct": round(edge * 100, 1),
                    "mkt_odd": mkt_odd,
                    "fair_odd": fair_odd,
                })

    return sorted(value_plays, key=lambda x: -x["edge_pct"])


# ── Output ────────────────────────────────────────────────────────────────

def print_results(probs, n_sims, target=None):
    round_labels = ["R32", "R16", "QF ", "SF ", "FIN", "WIN"]

    # Sort by SF probability descending
    ranked = sorted(probs.items(), key=lambda x: -x[1][3])

    print()
    print("=" * 90)
    print("  FIFA WORLD CUP 2026 — KNOCKOUT MONTE CARLO  ({:,} simulations)".format(n_sims))
    print("  T1 ELO | T2 Tactical | All games neutral venue | ET/pens: ELO-weighted")
    print("=" * 90)
    print()
    print("  {:<22}  {:>6}  {:>6}  {:>6}  {:>6}  {:>6}  {:>6}  {:>7}".format(
        "Team", "R32%", "R16%", "QF%", "SF%", "FIN%", "WIN%", "Fair SF"))
    print("  " + "-" * 80)

    for team, p in ranked:
        if target and target.lower() not in team.lower():
            if p[3] < 0.01:   # hide tiny-probability teams unless targeted
                continue

        fair_sf = round(1 / p[3], 2) if p[3] > 0.001 else 99.0
        marker = " ◄" if target and target.lower() in team.lower() else ""

        print("  {:<22}  {:>5.1f}%  {:>5.1f}%  {:>5.1f}%  {:>5.1f}%  {:>5.1f}%  {:>5.1f}%  {:>7.2f}{}".format(
            team,
            p[0]*100, p[1]*100, p[2]*100, p[3]*100, p[4]*100, p[5]*100,
            fair_sf, marker))

    print()


def print_value(value_plays):
    if not value_plays:
        print("  No value plays above threshold.")
        return

    print("  VALUE PLAYS (model prob > market implied by >5%)")
    print("  " + "-" * 75)
    print("  {:<22}  {:>8}  {:>8}  {:>8}  {:>7}  {:>8}".format(
        "Team", "Market", "Model%", "Implied%", "Edge%", "MktOdd"))
    print("  " + "-" * 75)
    for v in value_plays:
        print("  {:<22}  {:>8}  {:>7.1f}%  {:>7.1f}%  {:>6.1f}%  {:>8.2f}".format(
            v["team"], v["market"], v["model_p"], v["implied_p"],
            v["edge_pct"], v["mkt_odd"]))
    print()


# ── Main ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="WC2026 Knockout MC Simulation")
    parser.add_argument("--sims",         type=int,   default=100_000)
    parser.add_argument("--target",       type=str,   default=None,
                        help="Highlight a specific team (e.g. 'Brazil')")
    parser.add_argument("--market-odds",  type=str,   default=None,
                        help="CSV file: team,market,odd  (market = sf/final/win)")
    parser.add_argument("--value-threshold", type=float, default=0.05,
                        help="Min edge to flag as value (default 0.05)")
    args = parser.parse_args()

    # Validate bracket
    if any(t is None for t in BRACKET):
        missing = sum(1 for t in BRACKET if t is None)
        print()
        print("  ERROR: {} bracket slots are still None.".format(missing))
        print("  Fill in data/bracket.py with the actual R32 draw before running.")
        print()
        print("  Quick test: running with a SAMPLE bracket (top ELO teams)...")
        print()
        # Demo mode — fill with top ELO teams for illustration
        demo_teams = sorted(ELO.items(), key=lambda x: -x[1])[:32]
        demo_bracket = [t[0] for t in demo_teams]
        bracket_to_use = demo_bracket
    else:
        bracket_to_use = BRACKET

    print()
    print("  Running {:,} simulations...".format(args.sims))
    probs = run_simulation(bracket_to_use, args.sims)

    print_results(probs, args.sims, target=args.target)

    # Load market odds if provided
    market_odds = {}
    if args.market_odds:
        try:
            with open(args.market_odds, newline="") as f:
                for row in csv.DictReader(f):
                    team = row["team"]
                    mkt  = row["market"].lower()
                    odd  = float(row["odd"])
                    if team not in market_odds:
                        market_odds[team] = {}
                    market_odds[team][mkt] = odd
            value_plays = find_value(probs, market_odds, args.value_threshold)
            print_value(value_plays)
        except FileNotFoundError:
            print("  WARNING: market odds file '{}' not found.".format(args.market_odds))
    else:
        print("  TIP: Pass --market-odds odds.csv to auto-find value.")
        print("       CSV format:  team,market,odd")
        print("       Markets:     sf / final / win")
        print()

    # If target team specified, print their path probabilities
    if args.target:
        matches = [t for t in probs if args.target.lower() in t.lower()]
        if matches:
            team = matches[0]
            p    = probs[team]
            print()
            print("  PATH ANALYSIS: {}".format(team))
            print("  " + "-" * 50)
            labels = ["R32 (given)", "R16", "QF", "SF", "Final", "Winner"]
            for i, (lbl, prob) in enumerate(zip(labels, p)):
                fair = round(1/prob, 2) if prob > 0.001 else 99.0
                cond = prob/p[i-1] if i > 0 and p[i-1] > 0 else 1.0
                print("  {:<12} {:>6.1f}%  @ fair {:>6.2f}  (cond. {:.1f}% per round)".format(
                    lbl, prob*100, fair, cond*100))
            print()


if __name__ == "__main__":
    main()
