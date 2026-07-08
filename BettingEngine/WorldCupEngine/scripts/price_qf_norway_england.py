"""
FIFA World Cup 2026 — Quarterfinal: Norway vs England
Saturday July 11, Miami Stadium (Hard Rock Stadium) — neutral venue, sea level.

ELO chained forward from post-group-stage baseline through the actual
knockout results (source: FIFA/Sky Sports/ESPN match reports, confirmed via
web search 2026-07-06):
  Norway:  beat Ivory Coast 2-1 (R32, Dallas) -> beat Brazil 2-1 (R16, East Rutherford)
  England: beat DR Congo   2-1 (R32, Atlanta) -> beat Mexico  3-2 (R16, Estadio Azteca)

T1 ELO | T2 Tactical | T5 Absences | T7 Knockout motivation | T9 pressure (ET/pens)

Usage:
    cd C:\\Users\\ElliotBladen\\Apps\\BettingEngine
    python WorldCupEngine/scripts/price_qf_norway_england.py
"""
import sys
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "outputs"
sys.path.insert(0, str(DATA))

from elo_ratings import ELO
from knockout_context import PRESSURE_EDGE_BY_ROUND

K = 40  # house convention — same K used for group stage in elo_ratings.py


def expected(ra, rb):
    return 1 / (1 + 10 ** ((rb - ra) / 400))


def elo_update(ra, rb, result_a):
    ea = expected(ra, rb)
    return ra + K * (result_a - ea), rb + K * ((1 - result_a) - (1 - ea))


# ── Chain ELO through R32 and R16 knockout results ───────────────────────
nor_pre, civ_pre = ELO["Norway"], ELO["Ivory Coast"]
nor_r32, civ_r32 = elo_update(nor_pre, civ_pre, 1.0)  # Norway 2-1 Ivory Coast

eng_pre, cod_pre = ELO["England"], ELO["DR Congo"]
eng_r32, cod_r32 = elo_update(eng_pre, cod_pre, 1.0)  # England 2-1 DR Congo

bra_pre = ELO["Brazil"]
nor_r16, bra_r16 = elo_update(nor_r32, bra_pre, 1.0)  # Norway 2-1 Brazil

mex_pre = ELO["Mexico"]
eng_r16, mex_r16 = elo_update(eng_r32, mex_pre, 1.0)  # England 3-2 Mexico

NOR = round(nor_r16)
ENG = round(eng_r16)

print()
print("  ELO chain (K={}, no MOV/home adjustment — house convention):".format(K))
print("    Norway   {} -> R32 {} (beat Ivory Coast) -> R16 {} (beat Brazil)".format(
    round(nor_pre), round(nor_r32), NOR))
print("    England  {} -> R32 {} (beat DR Congo)    -> R16 {} (beat Mexico)".format(
    round(eng_pre), round(eng_r32), ENG))

# ── Pricing engine (same constants as rest of WorldCupEngine) ────────────
HIGH_PRESS = {"Germany", "England", "Netherlands", "France", "Spain",
              "Portugal", "Belgium", "Norway", "Brazil", "Argentina",
              "Colombia", "USA", "Japan", "South Korea", "Morocco",
              "Croatia", "Scotland", "Switzerland", "Uruguay"}

BASE_GOALS = 1.18
ELO_SCALE = 0.003
DC_RHO = -0.13
MAX_GOALS = 10


def t2_tactical(a, b):
    ha, hb = a in HIGH_PRESS, b in HIGH_PRESS
    if ha and hb:
        return 1.04, 1.04
    elif ha and not hb:
        return 1.02, 0.97
    elif not ha and hb:
        return 0.97, 1.02
    else:
        return 0.99, 0.99


def dc_tau(i, j, lam, mu, rho):
    if i == 0 and j == 0:
        return max(0, 1 - lam * mu * rho)
    if i == 0 and j == 1:
        return max(0, 1 + lam * rho)
    if i == 1 and j == 0:
        return max(0, 1 + mu * rho)
    if i == 1 and j == 1:
        return max(0, 1 - rho)
    return 1.0


def poisson_pmf(k, lam):
    return math.exp(-lam) * (lam ** k) / math.factorial(k)


def price_game(a, ea, b, eb, atk_a=0.0, def_a=0.0, atk_b=0.0, def_b=0.0,
               mot_a=0.0, mot_b=0.0):
    diff = ea - eb
    lam = BASE_GOALS * math.exp(ELO_SCALE * diff / 2)
    mu = BASE_GOALS * math.exp(-ELO_SCALE * diff / 2)
    ta, tb = t2_tactical(a, b)
    lam *= ta * (1 + atk_a) * (1 + def_b) * (1 + mot_a)
    mu *= tb * (1 + atk_b) * (1 + def_a) * (1 + mot_b)

    mat, tot = {}, 0.0
    for i in range(MAX_GOALS + 1):
        for j in range(MAX_GOALS + 1):
            p = max(0, poisson_pmf(i, lam) * poisson_pmf(j, mu) * dc_tau(i, j, lam, mu, DC_RHO))
            mat[(i, j)] = p
            tot += p
    mat = {k: v / tot for k, v in mat.items()}

    pa = sum(p for (i, j), p in mat.items() if i > j)
    pd = sum(p for (i, j), p in mat.items() if i == j)
    pb = sum(p for (i, j), p in mat.items() if i < j)
    po25 = sum(p for (i, j), p in mat.items() if i + j >= 3)
    xg = sum((i + j) * p for (i, j), p in mat.items())
    top = sorted(mat.items(), key=lambda x: -x[1])[:12]

    # QF pressure edge from knockout_context.py — ELO-weighted ET/pens split
    pressure = PRESSURE_EDGE_BY_ROUND.get(2, 0.0)  # round idx 2 = QF
    pen_a = 0.5 + (ea - eb) / 4000 + (pressure if ea > eb else -pressure)
    pen_a = max(0.35, min(0.65, pen_a))
    pw_a = pa + pd * pen_a
    pw_b = pb + pd * (1 - pen_a)

    fo = lambda p: round(1 / p, 2) if p > 0.001 else 99.0

    return {
        "diff": diff, "lam": round(lam, 3), "mu": round(mu, 3), "xg": round(xg, 2),
        "pa": round(pa * 100, 1), "pd": round(pd * 100, 1), "pb": round(pb * 100, 1),
        "oa": fo(pa), "ox": fo(pd), "ob": fo(pb),
        "po25": round(po25 * 100, 1), "oo25": fo(po25), "ou25": fo(1 - po25),
        "pw_a": round(pw_a * 100, 1), "pw_b": round(pw_b * 100, 1),
        "ow_a": fo(pw_a), "ow_b": fo(pw_b),
        "pen_a": round(pen_a * 100, 1),
        "scorelines": top,
    }


# ── T5 absences (confirmed via web search 2026-07-06) ────────────────────
# Norway: fully fit squad, no injuries/suspensions (Ryerson recovered).
# England: right side of defence has been threadbare all tournament and got
#   worse in the Mexico game —
#     - Reece James: hamstring, ruled out since R32
#     - Tino Livramento: calf, replaced in squad pre-tournament
#     - Jarell Quansah: SUSPENDED for QF (red card vs Mexico) — on top of the
#       ankle knock that already cost him the R32 game. Same practical
#       effect (unavailable), so kept in the defence-absence bucket.
#     - Djed Spence: only remaining specialist cover, was "unfit to start"
#       vs Mexico before appearing as a sub — undercooked, not a like-for-like
#       replacement.
#   -> bumped defence absence from the R32 value (+0.05) to +0.06 for the QF:
#      third game in, position is more depleted, not less.
# Bukayo Saka: managed off early vs Mexico with an Achilles concern —
#   flagged as a doubt, not a confirmed absence. Small attack trim (-0.02)
#   rather than treating him as out, since he may well start.
r = price_game(
    "Norway", NOR,
    "England", ENG,
    atk_a=0.00, def_a=0.00,      # Norway: fully fit
    atk_b=-0.02, def_b=0.06,     # England: Saka doubt, right-back crisis
    mot_a=0.02,                  # Norway: first-ever QF, historic underdog energy
    mot_b=0.01,                  # England: experienced knockout side, standard focus
)

print()
print("=" * 72)
print("  FIFA WORLD CUP 2026 — QUARTERFINAL")
print("  Norway vs England — Sat Jul 11, Miami Stadium (neutral, sea level)")
print("  T1 ELO + T2 Tactical + T5 Absences + T7 Motivation + pressure/pens")
print("=" * 72)
print()
print("  Norway ELO: {}  |  England ELO: {}  |  Diff: {:+d}".format(NOR, ENG, r["diff"]))
print("  xGoals:     Norway {:.3f}  —  England {:.3f}  (xG total: {})".format(r["lam"], r["mu"], r["xg"]))
print()
print("  -- 90-MINUTE RESULT --------------------------------------------")
print("  Norway win     {:5.1f}%   @  {:5.2f}".format(r["pa"], r["oa"]))
print("  Draw           {:5.1f}%   @  {:5.2f}".format(r["pd"], r["ox"]))
print("  England win    {:5.1f}%   @  {:5.2f}".format(r["pb"], r["ob"]))
print()
print("  -- OVER / UNDER 2.5 GOALS ----------------------------------------")
print("  Over 2.5       {:5.1f}%   @  {:5.2f}".format(r["po25"], r["oo25"]))
print("  Under 2.5      {:5.1f}%   @  {:5.2f}".format(100 - r["po25"], r["ou25"]))
print()
print("  -- ADVANCE TO SF (inc. ET + pens if 90min draw, pens split {:.1f}/{:.1f}) --".format(
    r["pen_a"], 100 - r["pen_a"]))
print("  Norway advance  {:5.1f}%   @  {:5.2f}".format(r["pw_a"], r["ow_a"]))
print("  England advance {:5.1f}%   @  {:5.2f}".format(r["pw_b"], r["ow_b"]))
print()
print("  -- MOST LIKELY SCORELINES ----------------------------------------")
sc = r["scorelines"]
for idx in range(0, min(12, len(sc)), 2):
    s1, p1 = sc[idx]
    if idx + 1 < len(sc):
        s2, p2 = sc[idx + 1]
        print("  {:>4}-{:<2}   {:>6.2f}%   |   {:>4}-{:<2}   {:>6.2f}%".format(
            s1[0], s1[1], p1 * 100, s2[0], s2[1], p2 * 100))
    else:
        print("  {:>4}-{:<2}   {:>6.2f}%".format(s1[0], s1[1], p1 * 100))
print()
print("  NOTE: England carries a real T5 defensive hit (James out, Quansah")
print("  NOTE: suspended, Livramento already out pre-tournament) — this is")
print("  NOTE: the single biggest lever in this price versus a straight ELO")
print("  NOTE: read. Saka fitness is a doubt, not confirmed out — re-run with")
print("  NOTE: atk_b=0.00 if he's passed fit, closer to -0.04 if he doesn't start.")
print("  NOTE: Both squads fully rested (no midweek travel/altitude carryover —")
print("  NOTE: Mexico game was at altitude, Miami is sea level).")
print()

# ── Markdown output for the record ────────────────────────────────────────
OUT.mkdir(exist_ok=True)
lines = [
    "# World Cup 2026 Quarterfinal — Norway vs England",
    "",
    "Sat Jul 11, Miami Stadium (Hard Rock Stadium) — neutral venue, sea level.",
    "",
    "Model: Dixon-Coles Poisson from ELO, tactical multipliers, T5 absences, T7 knockout motivation.",
    "",
    "## ELO chain",
    "",
    f"- Norway: {round(nor_pre)} -> R32 {round(nor_r32)} (beat Ivory Coast 2-1) -> R16 {NOR} (beat Brazil 2-1)",
    f"- England: {round(eng_pre)} -> R32 {round(eng_r32)} (beat DR Congo 2-1) -> R16 {ENG} (beat Mexico 3-2)",
    "",
    "## Fair odds (90 minutes)",
    "",
    "| Market | Norway | Draw | England |",
    "|---|---:|---:|---:|",
    f"| Probability | {r['pa']}% | {r['pd']}% | {r['pb']}% |",
    f"| Fair odds | {r['oa']} | {r['ox']} | {r['ob']} |",
    "",
    "## Totals",
    "",
    f"- Over 2.5: {r['po25']}% @ {r['oo25']}",
    f"- Under 2.5: {100 - r['po25']:.1f}% @ {r['ou25']}",
    "",
    "## Advance to SF (inc. ET/pens)",
    "",
    f"- Norway: {r['pw_a']}% @ {r['ow_a']}",
    f"- England: {r['pw_b']}% @ {r['ow_b']}",
    f"- Pens split if 90min draw: Norway {r['pen_a']}% / England {100 - r['pen_a']:.1f}%",
    "",
    "## Most likely scorelines",
    "",
    ", ".join(f"{s[0]}-{s[1]} ({p*100:.1f}%)" for s, p in r["scorelines"]) + ".",
    "",
    "## T5 — Absences / data risk",
    "",
    "- Norway: fully fit squad, no injuries or suspensions (Ryerson recovered). No adjustment.",
    "- England: Reece James (hamstring, out since R32), Tino Livramento (calf, replaced pre-tournament), "
    "Jarell Quansah (suspended for QF — red card vs Mexico, on top of the ankle knock that cost him R32). "
    "Djed Spence is the only specialist cover and was undercooked coming off the bench vs Mexico. "
    "Defence absence bumped to +0.06 (from +0.05 at R32) — the position has degraded, not recovered.",
    "- Bukayo Saka: Achilles doubt, subbed early vs Mexico. Treated as a doubt (-0.02 attack), not confirmed out. "
    "Re-price with atk_b=0.00 if passed fit, or -0.04 if ruled out.",
    "",
    "## T7 — Motivation",
    "",
    "- Norway +0.02: first-ever World Cup quarterfinal in the federation's history — underdog energy.",
    "- England +0.01: experienced knockout side, standard tournament focus.",
    "",
    "## Assumptions / risk flags",
    "",
    "- ELO chain uses house K=40 convention (matches group-stage methodology in `elo_ratings.py`), "
    "no margin-of-victory or home-advantage scaling.",
    "- Miami Stadium is sea-level and neutral for both sides — no altitude or host-nation adjustment "
    "(contrast with England's Azteca altitude game against Mexico).",
    "- Re-run this script if Saka's fitness is confirmed either way before matchday.",
]
out_path = OUT / "qf_norway_england_pricing.md"
out_path.write_text("\n".join(lines), encoding="utf-8")
print("  Written: {}".format(out_path))
print()
