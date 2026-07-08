"""
FIFA World Cup 2026 — Round 3 (Matchday 3) Pricing — Jun 24-26 (18 games)
6 tiers: T1 ELO (R1+R2 updated) | T2 Tactical | T3 Form | T4 Altitude | T5 Absences | T7 Motivation
Groups A-H: ELO fully updated. Group I: R1 only (R2 result pending).

Usage:
    cd C:\\Users\\ElliotBladen\\Apps\\BettingEngine
    python WorldCupEngine/scripts/price_rd3.py
"""
import sys
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "data"
sys.path.insert(0, str(ROOT))

from elo_ratings   import ELO
from rd3_fixtures  import RD3_FIXTURES_12
from rd3_team_data import KEY_ABSENCES, GW_FORM, MOTIVATION

BASE_GOALS      = 1.18
ELO_SCALE       = 0.003
DC_RHO          = -0.13
MAX_GOALS       = 10
ALTITUDE_FACTOR = -0.000067

HIGH_PRESS = {"Germany", "England", "Netherlands", "France", "Spain",
              "Portugal", "Belgium", "Norway", "Brazil", "Argentina",
              "Colombia", "USA", "Japan", "South Korea", "Morocco",
              "Croatia", "Scotland", "Switzerland", "Uruguay"}

AC_VENUES = {"Atlanta": "Mercedes-Benz Stadium", "Dallas": "AT&T Stadium",
             "Houston": "NRG Stadium"}

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

def price_game(a, b, altitude_m=0):
    ea, eb   = ELO.get(a, 1500), ELO.get(b, 1500)
    diff     = ea - eb
    base     = BASE_GOALS * math.exp(altitude_m * ALTITUDE_FACTOR)
    lam      = base * math.exp( ELO_SCALE * diff / 2)
    mu       = base * math.exp(-ELO_SCALE * diff / 2)
    ta, tb   = t2_tactical(a, b)
    lam *= ta * (1 + GW_FORM.get(a, 0)) * (1 + KEY_ABSENCES.get(a, 0)) * (1 + MOTIVATION.get(a, 0))
    mu  *= tb * (1 + GW_FORM.get(b, 0)) * (1 + KEY_ABSENCES.get(b, 0)) * (1 + MOTIVATION.get(b, 0))

    mat, tot = {}, 0.0
    for i in range(MAX_GOALS + 1):
        for j in range(MAX_GOALS + 1):
            p = max(0, poisson_pmf(i, lam) * poisson_pmf(j, mu) * dc_tau(i, j, lam, mu, DC_RHO))
            mat[(i, j)] = p; tot += p
    mat = {k: v / tot for k, v in mat.items()}

    pa   = sum(p for (i, j), p in mat.items() if i > j)
    pd   = sum(p for (i, j), p in mat.items() if i == j)
    pb   = sum(p for (i, j), p in mat.items() if i < j)
    po25 = sum(p for (i, j), p in mat.items() if i + j >= 3)
    xg   = sum((i + j) * p for (i, j), p in mat.items())

    fo = lambda p: round(1 / p, 2) if p > 0.001 else 99.0
    return {"ea": ea, "eb": eb, "diff": diff, "xg": round(xg, 2),
            "pa": round(pa*100,1), "pd": round(pd*100,1), "pb": round(pb*100,1),
            "oa": fo(pa), "ox": fo(pd), "ob": fo(pb),
            "po25": round(po25*100,1), "oo25": fo(po25),
            "pu25": round((1-po25)*100,1), "ou25": fo(1-po25)}


def run():
    results = [(g, a, b, v, alt, dt, price_game(a, b, alt))
               for g, a, b, v, alt, dt in RD3_FIXTURES_12]

    print()
    print("=" * 112)
    print("  FIFA WORLD CUP 2026 — ROUND 3 (JUN 24-27) — 24 GAMES (ALL GROUPS)")
    print("  T1 ELO (all groups R1+R2) | T2 Tactical | T3 Form | T4 Altitude | T5 Absences | T7 Motivation")
    print("  All games neutral venue. Fair odds — no margin.")
    print("  NOTE: Group K Colombia ELO estimated (Colombia vs DRC Jun 24 UTC — verify result)")
    print("=" * 112)

    # ── Main table ─────────────────────────────────────────────────────────────
    print()
    print(f"  {'GRP':<4}{'Date':<7}{'Team A':<20}{'Team B':<20}{'ELO':>5}"
          f"{'A%':>6}{'D%':>6}{'B%':>6}"
          f"{'1':>7}{'X':>7}{'2':>7}"
          f"{'O2.5%':>7}{'O2.5':>7}{'xG':>6}")
    print("  " + "-" * 108)

    last_date = None
    for g, a, b, v, alt, dt, r in results:
        if dt != last_date:
            if last_date is not None:
                print()
            last_date = dt

        tags = ""
        if alt > 0:        tags += f"[{alt}m] "
        if v in AC_VENUES: tags += "[AC] "
        if g == "K":       tags += "[DRC ELO est.] "

        print(f"  {g:<4}{dt:<7}{a:<20}{b:<20}{r['diff']:>+5}"
              f"{r['pa']:>6.1f}{r['pd']:>6.1f}{r['pb']:>6.1f}"
              f"{r['oa']:>7.2f}{r['ox']:>7.2f}{r['ob']:>7.2f}"
              f"{r['po25']:>7.1f}{r['oo25']:>7.2f}{r['xg']:>6.2f}  {tags}")

    # ── O2.5 signals ──────────────────────────────────────────────────────────
    print()
    print("  O2.5 SIGNALS (>62% OVER  /  <38% UNDER)")
    print("  " + "-" * 75)
    sigs = []
    for g, a, b, v, alt, dt, r in results:
        if r["po25"] >= 62:  sigs.append((r["po25"], "O2.5", g, a, b, r["oo25"], alt, dt))
        elif r["po25"] <= 38: sigs.append((r["po25"], "U2.5", g, a, b, r["ou25"], alt, dt))
    sigs.sort(reverse=True, key=lambda x: x[0] if x[1]=="O2.5" else 100-x[0])
    if sigs:
        for prob, label, g, a, b, odds, alt, dt in sigs:
            at = f" [{alt}m]" if alt else ""
            print(f"  {g}  {dt}  {a} v {b}{at}  >>> {label}  {prob:.1f}%  @ {odds:.2f}")
    else:
        print("  None above threshold this round.")

    # ── H2H confidence ────────────────────────────────────────────────────────
    print()
    print("  H2H CONFIDENCE PICKS (>62% win probability)")
    print("  " + "-" * 75)
    picks = []
    for g, a, b, v, alt, dt, r in results:
        if r["pa"] >= 62:   picks.append((r["pa"], g, a, b, r["oa"], dt))
        elif r["pb"] >= 62: picks.append((r["pb"], g, b, a, r["ob"], dt))
    picks.sort(reverse=True)
    if picks:
        for prob, g, team, opp, odds, dt in picks:
            print(f"  {g}  {dt}  {team} to win vs {opp}  {prob:.1f}%  @ {odds:.2f}")
    else:
        print("  None above 62%.")

    # ── Draw watch ────────────────────────────────────────────────────────────
    print()
    print("  DRAW WATCH (>30% — often signals tactical group-stage game)")
    print("  " + "-" * 75)
    for g, a, b, v, alt, dt, r in results:
        if r["pd"] >= 30:
            print(f"  {g}  {dt}  {a} v {b}  draw {r['pd']:.1f}%  @ {r['ox']:.2f}")

    # ── Group context ─────────────────────────────────────────────────────────
    print()
    print("  GROUP STANDINGS ENTERING R3")
    print("  " + "-" * 75)
    standings = [
        ("A", "Mexico 6pts | South Korea 3 | Czechia 1 | South Africa 1"),
        ("B", "Canada 4pts | Switzerland 4 | Bosnia 1 | Qatar 1"),
        ("C", "Brazil 4pts | Morocco 4 | Scotland 3 | Haiti 0"),
        ("D", "USA 6pts | Australia 3 | Paraguay 3 | Turkiye 0"),
        ("E", "Germany 6pts | Ivory Coast 3 | Ecuador 1 | Curacao 1"),
        ("F", "Netherlands 4pts | Japan 4 | Sweden 3 | Tunisia 0"),
        ("G", "Egypt 4pts | Iran 2 | Belgium 2 | New Zealand 1"),
        ("H", "Spain 4pts | Uruguay 2 | Cape Verde 2 | Saudi Arabia 1"),
        ("I", "France 6pts | Norway 6 | Senegal 0 | Iraq 0"),
        ("J", "Argentina 6pts | Austria 3 (GD 0) | Algeria 3 (GD -2) | Jordan 0"),
        ("K", "Colombia est.6pts* | Portugal 4 | DR Congo est.1* | Uzbekistan 0  (*Colombia/DRC R2 estimated)"),
        ("L", "England 4pts | Ghana 4 | Croatia 3 | Panama 0"),
    ]
    for g, s in standings:
        print(f"  {g}: {s}")

    # ── AC and altitude ───────────────────────────────────────────────────────
    print()
    print("  VENUE NOTES")
    print("  " + "-" * 75)
    for g, a, b, v, alt, dt, r in results:
        notes = []
        if alt > 0:
            red = round((1 - math.exp(alt * ALTITUDE_FACTOR)) * 100, 1)
            notes.append(f"altitude {alt}m -> xG reduced {red}% -> total {r['xg']:.2f}")
        if v in AC_VENUES:
            notes.append(f"air-conditioned ({AC_VENUES[v]})")
        if notes:
            print(f"  {g}  {a} v {b}: {' | '.join(notes)}")

    print()
    print("  NOTE: Group K Colombia vs DR Congo (Jun 24 02:00 UTC) result not confirmed.")
    print("        Colombia win assumed in ELO. Verify result and re-run if DRC won/drew.")
    print("        All other groups (A-L) fully updated through R2.")
    print()


if __name__ == "__main__":
    run()
