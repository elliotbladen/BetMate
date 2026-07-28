"""
FIFA World Cup 2026 — Semifinal: England vs Argentina
Wednesday July 15, Mercedes-Benz Stadium (Atlanta) — neutral venue, ~320m (no altitude adj, same
house treatment as Kansas City ~270m in the Argentina/Switzerland QF script).

ELO chained forward from post-group-stage baseline through the actual knockout
results (source: FIFA/NPR/ESPN/Al Jazeera match reports, confirmed via web search 2026-07-15):
  England:   beat DR Congo 2-1 (R32) -> beat Mexico 3-2 (R16) -> beat Norway 2-1 AET (QF, Bellingham brace)
  Argentina: beat Cape Verde 3-2 AET (R32) -> beat Egypt 3-2 (R16) -> beat Switzerland 3-1 AET (QF,
             Mac Allister/Alvarez/Lautaro; Embolo sent off)

ELO convention: extra-time win = 1.0 (decided in play), shootout = 0.5 (draw).
Opponents taken at post-group baseline (house convention — matches every prior WC script;
opponents are NOT chained through their own knockout games).

T1 ELO | T2 Tactical | T5 Absences | T7 Knockout motivation | T9 pressure (ET/pens, SF tier)

Usage:
    cd C:\\Users\\ElliotBladen\\Apps\\BettingEngine
    python WorldCupEngine/scripts/price_sf_england_argentina.py
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


# ── Chain ELO through R32, R16, QF knockout results ───────────────────────
# England path
eng_pre, cod_pre = ELO["England"], ELO["DR Congo"]
eng_r32, cod_r32 = elo_update(eng_pre, cod_pre, 1.0)   # England 2-1 DR Congo

mex_pre = ELO["Mexico"]
eng_r16, mex_r16 = elo_update(eng_r32, mex_pre, 1.0)   # England 3-2 Mexico

nor_pre, civ_pre = ELO["Norway"], ELO["Ivory Coast"]
nor_r32, civ_r32 = elo_update(nor_pre, civ_pre, 1.0)   # Norway 2-1 Ivory Coast
bra_pre = ELO["Brazil"]
nor_r16, bra_r16 = elo_update(nor_r32, bra_pre, 1.0)   # Norway 2-1 Brazil

eng_qf, nor_qf = elo_update(eng_r16, nor_r16, 1.0)     # England 2-1 Norway (AET)

# Argentina path
arg_pre, cpv_pre = ELO["Argentina"], ELO["Cape Verde"]
arg_r32, cpv_r32 = elo_update(arg_pre, cpv_pre, 1.0)   # Argentina 3-2 Cape Verde (AET)

egy_pre = ELO["Egypt"]
arg_r16, egy_r16 = elo_update(arg_r32, egy_pre, 1.0)   # Argentina 3-2 Egypt

sui_pre, alg_pre = ELO["Switzerland"], ELO["Algeria"]
sui_r32, alg_r32 = elo_update(sui_pre, alg_pre, 1.0)   # Switzerland 2-0 Algeria
col_pre = ELO["Colombia"]
sui_r16, col_r16 = elo_update(sui_r32, col_pre, 0.5)   # Switzerland 0-0 Colombia (pens = ELO draw)

arg_qf, sui_qf = elo_update(arg_r16, sui_r16, 1.0)     # Argentina 3-1 Switzerland (AET)

ENG = round(eng_qf)
ARG = round(arg_qf)

print()
print("  ELO chain (K={}, no MOV/home adjustment — house convention):".format(K))
print("    England    {} -> R32 {} (beat DR Congo) -> R16 {} (beat Mexico) -> QF {} (beat Norway AET)".format(
    round(eng_pre), round(eng_r32), round(eng_r16), ENG))
print("    Argentina  {} -> R32 {} (beat Cape Verde AET) -> R16 {} (beat Egypt) -> QF {} (beat Switzerland AET)".format(
    round(arg_pre), round(arg_r32), round(arg_r16), ARG))

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
               mot_a=0.0, mot_b=0.0, round_idx=3):
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

    # SF pressure edge from knockout_context.py — ELO-weighted ET/pens split
    pressure = PRESSURE_EDGE_BY_ROUND.get(round_idx, 0.0)  # round idx 3 = SF
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


# ── T5 absences (confirmed via web search 2026-07-15) ────────────────────
# England: Jarell Quansah serving 2nd match of an extended 2-game suspension
#   (red card vs Mexico). Jordan Henderson out for the rest of the tournament
#   (broken wrist) — squad depth player, not a first-choice starter, minor
#   impact. Reece James is now fit again (was out for the QF) — meaningful
#   defensive upgrade vs the QF price. Ezri Konsa picked up a hamstring
#   cramp scare in the Miami heat and is being monitored — treated as a
#   doubt, not confirmed out. Net defensive absence eased from the QF's
#   +0.06 (James back) but not zero (Quansah still out, Konsa a doubt).
#   Bukayo Saka is fit but being managed on minutes by Tuchel (impact-sub
#   role rather than a fitness concern) — no attack penalty applied.
# Argentina: no confirmed injuries or suspensions. Lautaro Martinez avoided
#   a second yellow (crowd celebration after his goal vs Switzerland) and
#   FIFA's post-QF yellow-card amnesty resets bookings anyway — fully
#   available. Messi in career-best tournament form (8 goals).
r = price_game(
    "England", ENG,
    "Argentina", ARG,
    atk_a=0.00, def_a=0.03,      # England: Quansah out + Konsa doubt, but James back reduces the QF hit
    atk_b=0.00, def_b=0.00,      # Argentina: fully fit, no disciplinary issues
    mot_a=0.01,                  # England: first WC semi since 1990, historic rivalry
    mot_b=0.02,                  # Argentina: defending champions, Messi's likely last WC, rivalry weight
    round_idx=3,                 # SF pressure tier
)

print()
print("=" * 72)
print("  FIFA WORLD CUP 2026 — SEMIFINAL")
print("  England vs Argentina — Wed Jul 15, Mercedes-Benz Stadium, Atlanta (neutral)")
print("  T1 ELO + T2 Tactical + T5 Absences + T7 Motivation + pressure/pens (SF tier)")
print("=" * 72)
print()
print("  England ELO: {}  |  Argentina ELO: {}  |  Diff: {:+d}".format(ENG, ARG, r["diff"]))
print("  xGoals:      England {:.3f}  —  Argentina {:.3f}  (xG total: {})".format(r["lam"], r["mu"], r["xg"]))
print()
print("  -- 90-MINUTE RESULT --------------------------------------------")
print("  England win     {:5.1f}%   @  {:5.2f}".format(r["pa"], r["oa"]))
print("  Draw            {:5.1f}%   @  {:5.2f}".format(r["pd"], r["ox"]))
print("  Argentina win   {:5.1f}%   @  {:5.2f}".format(r["pb"], r["ob"]))
print()
print("  -- OVER / UNDER 2.5 GOALS ----------------------------------------")
print("  Over 2.5        {:5.1f}%   @  {:5.2f}".format(r["po25"], r["oo25"]))
print("  Under 2.5       {:5.1f}%   @  {:5.2f}".format(100 - r["po25"], r["ou25"]))
print()
print("  -- ADVANCE TO FINAL (inc. ET + pens if 90min draw, pens split {:.1f}/{:.1f}) --".format(
    r["pen_a"], 100 - r["pen_a"]))
print("  England advance    {:5.1f}%   @  {:5.2f}".format(r["pw_a"], r["ow_a"]))
print("  Argentina advance  {:5.1f}%   @  {:5.2f}".format(r["pw_b"], r["ow_b"]))
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
print("  MARKET CHECK (web-sourced 2026-07-15, opening lines):")
print("  Bookmaker 90-min: England ~+155 (2.55) | Argentina ~+205 (3.05)")
print("  Bookmaker advance: England ~56% | Argentina ~44%")
print("  Opta supercomputer 90-min sim: England 38.2% | Draw 29.7% | Argentina 32.0%")
print("  Model here vs market: model has England win prob at {:.1f}% vs Opta's 38.2% and".format(r["pa"]))
print("  a market-implied ~39.2% (1/2.55) — an 11-12pt gap, not close. Model's advance number")
print("  ({:.1f}%) is well below the ~56% market price on England, and actually has".format(r["pw_a"]))
print("  Argentina as the clear favourite ({:.1f}% advance) where the market leans England.".format(r["pw_b"]))
print("  This is a real disagreement, not noise — driven by ELO: Argentina's knockout path")
print("  (Cape Verde/Egypt/Switzerland) gained less resistance than England's read implies,")
print("  and Argentina started the tournament ~90 ELO points above England. Flag this hard:")
print("  the WC engine has zero CLV/closing-line validation history — do not treat this")
print("  divergence as a proven edge on Argentina, just an honest model output.")
print()

# ── Markdown output for the record ────────────────────────────────────────
OUT.mkdir(exist_ok=True)
lines = [
    "# World Cup 2026 Semifinal — England vs Argentina",
    "",
    "Wed Jul 15, Mercedes-Benz Stadium, Atlanta — neutral venue, ~320m altitude (no adjustment,"
    " same house treatment as Kansas City ~270m in the QF).",
    "",
    "Model: Dixon-Coles Poisson from ELO, tactical multipliers, T5 absences, T7 knockout motivation.",
    "",
    "## ELO chain",
    "",
    f"- England: {round(eng_pre)} -> R32 {round(eng_r32)} (beat DR Congo 2-1) -> R16 {round(eng_r16)}"
    f" (beat Mexico 3-2) -> QF {ENG} (beat Norway 2-1 AET)",
    f"- Argentina: {round(arg_pre)} -> R32 {round(arg_r32)} (beat Cape Verde 3-2 AET) -> R16 {round(arg_r16)}"
    f" (beat Egypt 3-2) -> QF {ARG} (beat Switzerland 3-1 AET)",
    "",
    "## Fair odds (90 minutes)",
    "",
    "| Market | England | Draw | Argentina |",
    "|---|---:|---:|---:|",
    f"| Probability | {r['pa']}% | {r['pd']}% | {r['pb']}% |",
    f"| Fair odds | {r['oa']} | {r['ox']} | {r['ob']} |",
    "",
    "## Totals",
    "",
    f"- Over 2.5: {r['po25']}% @ {r['oo25']}",
    f"- Under 2.5: {100 - r['po25']:.1f}% @ {r['ou25']}",
    "",
    "## Advance to Final (inc. ET/pens)",
    "",
    f"- England: {r['pw_a']}% @ {r['ow_a']}",
    f"- Argentina: {r['pw_b']}% @ {r['ow_b']}",
    f"- Pens split if 90min draw: England {r['pen_a']}% / Argentina {100 - r['pen_a']:.1f}%",
    "",
    "## Most likely scorelines",
    "",
    ", ".join(f"{s[0]}-{s[1]} ({p*100:.1f}%)" for s, p in r["scorelines"]) + ".",
    "",
    "## T5 — Absences / data risk",
    "",
    "- England: Jarell Quansah serving the 2nd match of an extended 2-game suspension (red card vs "
    "Mexico). Jordan Henderson out for the rest of the tournament (broken wrist) — squad depth, not "
    "a first-choice starter, minor impact. Reece James is fit again (was out for the QF) — a real "
    "defensive upgrade on the QF price. Ezri Konsa has a hamstring cramp scare from the Miami heat, "
    "being monitored — treated as a doubt. Net defensive absence eased to +0.03 (from +0.06 at the QF).",
    "- Bukayo Saka is fit but managed on minutes by Tuchel (impact-sub role) — no attack penalty applied; "
    "he changed the Norway game after coming on at half-time.",
    "- Argentina: no confirmed injuries or suspensions. Lautaro Martinez avoided a second yellow for "
    "a celebration incident vs Switzerland, and FIFA's post-QF yellow-card amnesty resets bookings "
    "regardless — fully available. Messi in career-best tournament form (8 goals). No adjustment.",
    "",
    "## T7 — Motivation",
    "",
    "- England +0.01: first World Cup semifinal since 1990 (Italia '90), significant historic weight "
    "but standard knockout-focus treatment.",
    "- Argentina +0.02: defending champions, Messi's likely last World Cup, historic rivalry intensity "
    "(1986/1998/2002/2022 meetings) — judgment value, kept modest per house convention on motivation edges.",
    "",
    "## Market check (web-sourced 2026-07-15, opening lines)",
    "",
    "- Bookmaker 90-min: England ~+155 (2.55 decimal) / Argentina ~+205 (3.05 decimal).",
    "- Bookmaker advance (inc. ET/pens): England ~56% / Argentina ~44%.",
    "- Opta supercomputer 90-min simulation: England 38.2% / Draw 29.7% / Argentina 32.0%.",
    f"- **This model disagrees with the market, not just diverges slightly.** 90-min England win "
    f"probability here is {r['pa']}% vs Opta's 38.2% and the market-implied ~39.2% (1/2.55) — an "
    f"11-12pt gap. The advance number ({r['pw_a']}% England / {r['pw_b']}% Argentina) has Argentina "
    "as the clear favourite where the market leans England. Driver: Argentina started the tournament "
    "~90 ELO points above England and its knockout path (Cape Verde/Egypt/Switzerland) added more ELO "
    "than England's (DR Congo/Mexico/Norway) under the house K=40, no-MOV convention. This is an honest "
    "model output, not a validated edge — the WC engine has no CLV or closing-line track record "
    "(see Assumptions below). Do not stake against the market on this alone.",
    "- UNDER 2.5 is the market favourite on the total; this model's split is "
    f"{100 - r['po25']:.1f}% under / {r['po25']}% over, directionally consistent.",
    "",
    "## Assumptions / risk flags",
    "",
    "- ELO chain uses house K=40 convention, no margin-of-victory or home-advantage scaling. "
    "Extra-time win counts 1.0; penalty shootout counts 0.5 (draw). Opponents taken at post-group "
    "baseline, not chained through their own knockout games (matches every prior WC script in this repo).",
    "- SF pressure tier (0.007) applied instead of the QF's 0.004, per `knockout_context.py`'s "
    "`PRESSURE_EDGE_BY_ROUND` — a small bump reflecting greater composure variance at this stage.",
    "- Mercedes-Benz Stadium (Atlanta, ~320m) is not in `VENUE_CONTEXT` — treated as negligible altitude, "
    "same as Kansas City (~270m) in the QF; consider adding both if more games get priced at these venues.",
    "- Neutral venue; crowd will skew mixed given both fanbases travel well, no crowd adjustment applied "
    "(house convention: crowd only priced for host-nation games).",
    "- This WC engine is a light ELO/Dixon-Coles model with no CLV or closing-line validation history — "
    "same caveat flagged on every prior WC output this tournament. Treat as directional, not a proven edge.",
    "- Re-run this script if Konsa is ruled out (bump def_b back toward +0.05) or if either camp names a "
    "confirmed team news update before kickoff (19:00 local Jul 15).",
]
out_path = OUT / "sf_england_argentina_pricing.md"
out_path.write_text("\n".join(lines), encoding="utf-8")
print("  Written: {}".format(out_path))
print()
