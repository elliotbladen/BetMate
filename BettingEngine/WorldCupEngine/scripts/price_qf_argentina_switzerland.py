"""
FIFA World Cup 2026 — Quarterfinal: Argentina vs Switzerland
Saturday July 11, Kansas City Stadium (Arrowhead) — neutral venue, ~270m (no altitude adj).

ELO chained forward from post-group-stage baseline through the actual
knockout results (source: ESPN/Al Jazeera/Yahoo/CBS match reports, confirmed
via web search 2026-07-08):
  Argentina:   beat Cape Verde 3-2 AET (R32) -> beat Egypt 3-2 (R16, from 2-0 down)
  Switzerland: beat Algeria 2-0 (R32)        -> 0-0 Colombia, won 4-3 on pens (R16)

ELO convention: extra-time win = 1.0 (decided in play), shootout = 0.5 (draw).
Opponents taken at post-group baseline (house convention — matches the
Norway/England QF script; opponents are NOT chained through their own R32).

T1 ELO | T2 Tactical | T5 Absences | T7 Knockout motivation | T9 pressure (ET/pens)

Usage:
    cd C:\\Users\\ElliotBladen\\Apps\\BettingEngine
    python WorldCupEngine/scripts/price_qf_argentina_switzerland.py
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
arg_pre, cpv_pre = ELO["Argentina"], ELO["Cape Verde"]
arg_r32, cpv_r32 = elo_update(arg_pre, cpv_pre, 1.0)   # Argentina 3-2 Cape Verde (AET)

egy_pre = ELO["Egypt"]
arg_r16, egy_r16 = elo_update(arg_r32, egy_pre, 1.0)   # Argentina 3-2 Egypt

sui_pre, alg_pre = ELO["Switzerland"], ELO["Algeria"]
sui_r32, alg_r32 = elo_update(sui_pre, alg_pre, 1.0)   # Switzerland 2-0 Algeria

col_pre = ELO["Colombia"]
sui_r16, col_r16 = elo_update(sui_r32, col_pre, 0.5)   # Switzerland 0-0 Colombia (won pens = ELO draw)

ARG = round(arg_r16)
SUI = round(sui_r16)

print()
print("  ELO chain (K={}, no MOV/home adjustment — house convention):".format(K))
print("    Argentina   {} -> R32 {} (beat Cape Verde AET) -> R16 {} (beat Egypt)".format(
    round(arg_pre), round(arg_r32), ARG))
print("    Switzerland {} -> R32 {} (beat Algeria)        -> R16 {} (0-0 Colombia, pens)".format(
    round(sui_pre), round(sui_r32), SUI))

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
        "diff": round(diff), "lam": round(lam, 3), "mu": round(mu, 3), "xg": round(xg, 2),
        "pa": round(pa * 100, 1), "pd": round(pd * 100, 1), "pb": round(pb * 100, 1),
        "oa": fo(pa), "ox": fo(pd), "ob": fo(pb),
        "po25": round(po25 * 100, 1), "oo25": fo(po25), "ou25": fo(1 - po25),
        "pw_a": round(pw_a * 100, 1), "pw_b": round(pw_b * 100, 1),
        "ow_a": fo(pw_a), "ow_b": fo(pw_b),
        "pen_a": round(pen_a * 100, 1),
        "scorelines": top,
    }


# ── T5 absences (confirmed via web search 2026-07-08) ────────────────────
# Argentina: effectively fully fit. Facundo Medina's R32 scare was cramps/
#   exhaustion, not structural. No suspensions (yellow accumulation resets
#   at the QF; no reds in either knockout game).
# Switzerland: genuinely banged up after 120 minutes vs Colombia —
#     - Johan Manzambi: knee, ruled OUT of the R16 — no fitness update yet,
#       treated as out for the QF (-0.02 attack)
#     - Breel Embolo: subbed off vs Colombia with a possible injury — doubt,
#       not confirmed out (-0.02 attack)
#     - Silvan Widmer: hip/thigh, bench-only since the group stage (+0.02
#       opponent-facing defensive absence)
#     - Aebischer / Sow / Vargas all carrying knocks after the extra-time
#       shift — folded into the above rather than double-counted; flagged.
r = price_game(
    "Argentina", ARG,
    "Switzerland", SUI,
    atk_a=0.00, def_a=0.00,      # Argentina: fully fit
    atk_b=-0.04, def_b=0.02,     # Switzerland: Manzambi out + Embolo doubt; Widmer hip
    mot_a=0.01,                  # Argentina: defending champs, standard knockout focus
    mot_b=0.02,                  # Switzerland: first QF since 1954 — historic underdog energy
)

print()
print("=" * 72)
print("  FIFA WORLD CUP 2026 — QUARTERFINAL")
print("  Argentina vs Switzerland — Sat Jul 11, Kansas City Stadium (neutral)")
print("  T1 ELO + T2 Tactical + T5 Absences + T7 Motivation + pressure/pens")
print("=" * 72)
print()
print("  Argentina ELO: {}  |  Switzerland ELO: {}  |  Diff: {:+d}".format(ARG, SUI, r["diff"]))
print("  xGoals:     Argentina {:.3f}  —  Switzerland {:.3f}  (xG total: {})".format(
    r["lam"], r["mu"], r["xg"]))
print()
print("  -- 90-MINUTE RESULT --------------------------------------------")
print("  Argentina win    {:5.1f}%   @  {:5.2f}".format(r["pa"], r["oa"]))
print("  Draw             {:5.1f}%   @  {:5.2f}".format(r["pd"], r["ox"]))
print("  Switzerland win  {:5.1f}%   @  {:5.2f}".format(r["pb"], r["ob"]))
print()
print("  -- OVER / UNDER 2.5 GOALS ----------------------------------------")
print("  Over 2.5         {:5.1f}%   @  {:5.2f}".format(r["po25"], r["oo25"]))
print("  Under 2.5        {:5.1f}%   @  {:5.2f}".format(100 - r["po25"], r["ou25"]))
print()
print("  -- ADVANCE TO SF (inc. ET + pens if 90min draw, pens split {:.1f}/{:.1f}) --".format(
    r["pen_a"], 100 - r["pen_a"]))
print("  Argentina advance   {:5.1f}%   @  {:5.2f}".format(r["pw_a"], r["ow_a"]))
print("  Switzerland advance {:5.1f}%   @  {:5.2f}".format(r["pw_b"], r["ow_b"]))
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
print("  NOTE: Switzerland's T5 hit (Manzambi out, Embolo doubtful, Widmer")
print("  NOTE: restricted, three more carrying knocks) plus 120min + pens on")
print("  NOTE: Jul 7 is the biggest non-ELO lever here. Both teams played Jul 7")
print("  NOTE: so calendar rest is equal — but the Swiss shift was 30min longer.")
print("  NOTE: Recovery tier is held neutral per house convention (no verified")
print("  NOTE: input layer); treat the Swiss price as the optimistic end.")
print("  NOTE: Kansas City is not in VENUE_CONTEXT — ~270m altitude, no adj.")
print("  NOTE: Crowd will skew heavily Argentine; model does not price crowd")
print("  NOTE: for non-host nations. Re-run if Embolo/Manzambi passed fit")
print("  NOTE: (atk_b=-0.02) or both confirmed out (atk_b=-0.05).")
print()

# ── Markdown output for the record ────────────────────────────────────────
OUT.mkdir(exist_ok=True)
lines = [
    "# World Cup 2026 Quarterfinal — Argentina vs Switzerland",
    "",
    "Sat Jul 11, Kansas City Stadium (Arrowhead) — neutral venue, ~270m altitude (no adjustment).",
    "",
    "Model: Dixon-Coles Poisson from ELO, tactical multipliers, T5 absences, T7 knockout motivation.",
    "",
    "## ELO chain",
    "",
    f"- Argentina: {round(arg_pre)} -> R32 {round(arg_r32)} (beat Cape Verde 3-2 AET) -> R16 {ARG} (beat Egypt 3-2)",
    f"- Switzerland: {round(sui_pre)} -> R32 {round(sui_r32)} (beat Algeria 2-0) -> R16 {SUI} (0-0 Colombia, won 4-3 pens = ELO draw)",
    "",
    "## Fair odds (90 minutes)",
    "",
    "| Market | Argentina | Draw | Switzerland |",
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
    f"- Argentina: {r['pw_a']}% @ {r['ow_a']}",
    f"- Switzerland: {r['pw_b']}% @ {r['ow_b']}",
    f"- Pens split if 90min draw: Argentina {r['pen_a']}% / Switzerland {100 - r['pen_a']:.1f}%",
    "",
    "## Most likely scorelines",
    "",
    ", ".join(f"{s[0]}-{s[1]} ({p*100:.1f}%)" for s, p in r["scorelines"]) + ".",
    "",
    "## T5 — Absences / data risk",
    "",
    "- Argentina: effectively fully fit. Medina's R32 knock was cramps/exhaustion, not structural. "
    "No suspensions (yellow accumulation resets at the QF; no reds in either knockout game). No adjustment.",
    "- Switzerland: Johan Manzambi (knee) ruled out of the R16 with no update since — treated as out. "
    "Breel Embolo subbed off vs Colombia with a possible injury — doubt (-0.02). Silvan Widmer (hip/thigh) "
    "bench-only since the group stage (+0.02 defensive absence). Aebischer, Sow and Vargas all carrying "
    "knocks after 120 minutes — flagged, not separately priced.",
    "- Re-price: atk_b=-0.02 if Embolo and Manzambi are both passed fit; atk_b=-0.05 if both are confirmed out.",
    "",
    "## T7 — Motivation",
    "",
    "- Switzerland +0.02: first World Cup quarterfinal since 1954 — historic underdog energy.",
    "- Argentina +0.01: defending champions, experienced knockout side; Messi on 8 tournament goals.",
    "",
    "## Assumptions / risk flags",
    "",
    "- ELO chain uses house K=40 convention, no margin-of-victory or home-advantage scaling. "
    "Extra-time win counts 1.0; penalty shootout counts 0.5 (draw). Opponents taken at post-group "
    "baseline, not chained through their own knockout games (matches the Norway/England QF script).",
    "- Both teams last played Jul 7 (equal calendar rest), but Switzerland went 120 minutes plus a "
    "shootout while Argentina finished in 90. Recovery tier held neutral per house convention "
    "(RECOVERY_EDGE_BY_ROUND has no verified input layer) — the Swiss price is therefore the "
    "optimistic end of the range.",
    "- Kansas City Stadium is not in VENUE_CONTEXT (~270m — negligible, no altitude adjustment). "
    "Neutral venue for both; crowd will skew heavily Argentine but the model does not price crowd "
    "for non-host nations.",
    "- Re-run this script when Switzerland's matchday squad news lands (Embolo/Manzambi).",
]
out_path = OUT / "qf_argentina_switzerland_pricing.md"
out_path.write_text("\n".join(lines), encoding="utf-8")
print("  Written: {}".format(out_path))
print()
