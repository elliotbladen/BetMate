"""
FIFA World Cup 2026 — Quarterfinal: France vs Morocco
Thursday July 9, Boston Stadium (Gillette, Foxborough) — neutral venue, sea level.

ELO chained forward from post-group-stage baseline through the actual
knockout results (source: FIFA/ESPN/UEFA match reports, confirmed via
web search 2026-07-08):
  France:  beat Sweden 3-0 (R32) -> beat Paraguay 1-0 (R16, Mbappe pen)
  Morocco: 1-1 Netherlands, won 3-2 pens (R32) -> beat Canada 3-0 (R16)

ELO convention: extra-time win = 1.0, shootout = 0.5 (draw). Opponents at
post-group baseline (house convention — matches the other QF scripts).

Includes ASIAN HANDICAP pricing (Morocco +1 / +1.5 / +2 / +2.5) computed
directly from the Dixon-Coles score matrix.

T1 ELO | T2 Tactical | T5 Absences | T7 Knockout motivation | T9 pressure (ET/pens)

Usage:
    cd C:\\Users\\ElliotBladen\\Apps\\BettingEngine
    python WorldCupEngine/scripts/price_qf_france_morocco.py
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
fra_pre, swe_pre = ELO["France"], ELO["Sweden"]
fra_r32, swe_r32 = elo_update(fra_pre, swe_pre, 1.0)   # France 3-0 Sweden

par_pre = ELO["Paraguay"]
fra_r16, par_r16 = elo_update(fra_r32, par_pre, 1.0)   # France 1-0 Paraguay

mar_pre, ned_pre = ELO["Morocco"], ELO["Netherlands"]
mar_r32, ned_r32 = elo_update(mar_pre, ned_pre, 0.5)   # Morocco 1-1 NED (won pens = ELO draw)

can_pre = ELO["Canada"]
mar_r16, can_r16 = elo_update(mar_r32, can_pre, 1.0)   # Morocco 3-0 Canada

FRA = round(fra_r16)
MAR = round(mar_r16)

print()
print("  ELO chain (K={}, no MOV/home adjustment — house convention):".format(K))
print("    France  {} -> R32 {} (beat Sweden 3-0)          -> R16 {} (beat Paraguay 1-0)".format(
    round(fra_pre), round(fra_r32), FRA))
print("    Morocco {} -> R32 {} (1-1 NED, pens = ELO draw) -> R16 {} (beat Canada 3-0)".format(
    round(mar_pre), round(mar_r32), MAR))

# ── Pricing engine (same constants as rest of WorldCupEngine) ────────────
HIGH_PRESS = {"Germany", "England", "Netherlands", "France", "Spain",
              "Portugal", "Belgium", "Norway", "Brazil", "Argentina",
              "Colombia", "USA", "Japan", "South Korea", "Morocco",
              "Croatia", "Scotland", "Switzerland", "Uruguay"}

BASE_GOALS = 1.18
ELO_SCALE = 0.003
DC_RHO = -0.13
MAX_GOALS = 10

# Share of a match's goals scored before halftime. Empirical league/WC range
# is 44-46% (second halves run hotter: fatigue, chasing, subs). No house
# constant existed for this — 0.45 adopted 2026-07-08, flag for review.
FIRST_HALF_GOAL_SHARE = 0.45


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


def build_matrix(lam, mu):
    mat, tot = {}, 0.0
    for i in range(MAX_GOALS + 1):
        for j in range(MAX_GOALS + 1):
            p = max(0, poisson_pmf(i, lam) * poisson_pmf(j, mu) * dc_tau(i, j, lam, mu, DC_RHO))
            mat[(i, j)] = p
            tot += p
    return {k: v / tot for k, v in mat.items()}


def price_game(a, ea, b, eb, atk_a=0.0, def_a=0.0, atk_b=0.0, def_b=0.0,
               mot_a=0.0, mot_b=0.0):
    diff = ea - eb
    lam = BASE_GOALS * math.exp(ELO_SCALE * diff / 2)
    mu = BASE_GOALS * math.exp(-ELO_SCALE * diff / 2)
    ta, tb = t2_tactical(a, b)
    lam *= ta * (1 + atk_a) * (1 + def_b) * (1 + mot_a)
    mu *= tb * (1 + atk_b) * (1 + def_a) * (1 + mot_b)

    mat = build_matrix(lam, mu)

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
        "matrix": mat,
    }


def handicap_underdog(mat, line):
    """Asian handicap for team B (underdog) at +line, from A's perspective.

    Margin M = goals_A - goals_B. B +line wins if M < line, pushes if
    M == line (whole lines only), loses if M > line.
    Returns (p_win, p_push, p_lose, fair_odds_excl_push) for the B side,
    plus the fair odds for the A side (A -line) for reference.
    """
    p_win = sum(p for (i, j), p in mat.items() if (i - j) < line)
    p_push = sum(p for (i, j), p in mat.items() if (i - j) == line)
    p_lose = 1.0 - p_win - p_push
    act = p_win + p_lose  # action excluding push
    fair_b = act / p_win if p_win > 0 else 999.0
    fair_a = act / p_lose if p_lose > 0 else 999.0
    return p_win, p_push, p_lose, fair_b, fair_a


# ── T5 absences (confirmed via web search 2026-07-08) ────────────────────
# France:
#   - Aurelien Tchouameni: OUT (injury) — first-choice defensive midfield
#     anchor. Kone/Rabiot expected pairing. Structural defensive hit (+0.03
#     opponent-facing) — France's shield in front of the back four.
#   - Marcus Thuram: OUT (injury) — rotation forward; front line still has
#     Mbappe/Dembele/Olise/Barcola. Marginal (-0.01 attack).
# Morocco:
#   - Ismael Saibari: hamstring, withdrawn early vs Canada — doubt, not
#     confirmed out (-0.02 attack). Rahimi likely starts if he misses.
#   - Chadi Riad: CB fitness doubt after making way last game (+0.02
#     opponent-facing defensive absence if restricted).
r = price_game(
    "France", FRA,
    "Morocco", MAR,
    atk_a=-0.01, def_a=0.03,     # France: Thuram out (marginal), Tchouameni out (real)
    atk_b=-0.02, def_b=0.02,     # Morocco: Saibari doubt, Riad doubt
    mot_a=0.01,                  # France: standard tournament focus
    mot_b=0.02,                  # Morocco: 2022 SF revenge arc, 2nd straight QF, Boston diaspora crowd
)

print()
print("=" * 72)
print("  FIFA WORLD CUP 2026 — QUARTERFINAL")
print("  France vs Morocco — Thu Jul 9, Boston Stadium (neutral, sea level)")
print("  T1 ELO + T2 Tactical + T5 Absences + T7 Motivation + pressure/pens")
print("=" * 72)
print()
print("  France ELO: {}  |  Morocco ELO: {}  |  Diff: {:+d}".format(FRA, MAR, r["diff"]))
print("  xGoals:     France {:.3f}  —  Morocco {:.3f}  (xG total: {})".format(
    r["lam"], r["mu"], r["xg"]))
print()
print("  -- 90-MINUTE RESULT --------------------------------------------")
print("  France win     {:5.1f}%   @  {:5.2f}".format(r["pa"], r["oa"]))
print("  Draw           {:5.1f}%   @  {:5.2f}".format(r["pd"], r["ox"]))
print("  Morocco win    {:5.1f}%   @  {:5.2f}".format(r["pb"], r["ob"]))
print()
print("  -- ASIAN HANDICAP (90 minutes, from DC score matrix) -------------")
hcp_rows = []
for line in (1.0, 1.5, 2.0, 2.5):
    pw, pp, pl, fair_b, fair_a = handicap_underdog(r["matrix"], line)
    label = "+{:.1f}".format(line)
    push_note = "push {:4.1f}%".format(pp * 100) if pp > 0 else "no push  "
    print("  Morocco {}   win {:5.1f}%  {}  lose {:5.1f}%   fair @ {:5.2f}   (France {} @ {:.2f})".format(
        label, pw * 100, push_note, pl * 100, fair_b, "-{:.1f}".format(line), fair_a))
    hcp_rows.append((label, pw, pp, pl, fair_b, fair_a))
print()

# ── FIRST HALF ONLY ───────────────────────────────────────────────────────
lam_1h = r["lam"] * FIRST_HALF_GOAL_SHARE
mu_1h = r["mu"] * FIRST_HALF_GOAL_SHARE
mat_1h = build_matrix(lam_1h, mu_1h)

p1h_a = sum(p for (i, j), p in mat_1h.items() if i > j)
p1h_d = sum(p for (i, j), p in mat_1h.items() if i == j)
p1h_b = sum(p for (i, j), p in mat_1h.items() if i < j)
p1h_o05 = sum(p for (i, j), p in mat_1h.items() if i + j >= 1)
p1h_o15 = sum(p for (i, j), p in mat_1h.items() if i + j >= 2)
fo = lambda p: round(1 / p, 2) if p > 0.001 else 99.0

print("  -- FIRST HALF RESULT (goal share {:.0%}) ---------------------------".format(
    FIRST_HALF_GOAL_SHARE))
print("  France HT lead   {:5.1f}%   @  {:5.2f}".format(p1h_a * 100, fo(p1h_a)))
print("  Draw at HT       {:5.1f}%   @  {:5.2f}".format(p1h_d * 100, fo(p1h_d)))
print("  Morocco HT lead  {:5.1f}%   @  {:5.2f}".format(p1h_b * 100, fo(p1h_b)))
print()
print("  -- FIRST HALF ASIAN HANDICAP -------------------------------------")
hcp_1h_rows = []
for line in (0.5, 1.0, 1.5, 2.0):
    pw, pp, pl, fair_b, fair_a = handicap_underdog(mat_1h, line)
    label = "+{:.1f}".format(line)
    push_note = "push {:4.1f}%".format(pp * 100) if pp > 0 else "no push  "
    print("  Morocco {}   win {:5.1f}%  {}  lose {:5.1f}%   fair @ {:5.2f}   (France {} @ {:.2f})".format(
        label, pw * 100, push_note, pl * 100, fair_b, "-{:.1f}".format(line), fair_a))
    hcp_1h_rows.append((label, pw, pp, pl, fair_b, fair_a))
print()
print("  -- FIRST HALF TOTALS ---------------------------------------------")
print("  Over 0.5 (goal before HT)  {:5.1f}%   @  {:5.2f}".format(p1h_o05 * 100, fo(p1h_o05)))
print("  Under 0.5 (0-0 at HT)      {:5.1f}%   @  {:5.2f}".format((1 - p1h_o05) * 100, fo(1 - p1h_o05)))
print("  Over 1.5                   {:5.1f}%   @  {:5.2f}".format(p1h_o15 * 100, fo(p1h_o15)))
print("  Under 1.5                  {:5.1f}%   @  {:5.2f}".format((1 - p1h_o15) * 100, fo(1 - p1h_o15)))
print()
print("  -- OVER / UNDER 2.5 GOALS ----------------------------------------")
print("  Over 2.5       {:5.1f}%   @  {:5.2f}".format(r["po25"], r["oo25"]))
print("  Under 2.5      {:5.1f}%   @  {:5.2f}".format(100 - r["po25"], r["ou25"]))
print()
print("  -- ADVANCE TO SF (inc. ET + pens if 90min draw, pens split {:.1f}/{:.1f}) --".format(
    r["pen_a"], 100 - r["pen_a"]))
print("  France advance  {:5.1f}%   @  {:5.2f}".format(r["pw_a"], r["ow_a"]))
print("  Morocco advance {:5.1f}%   @  {:5.2f}".format(r["pw_b"], r["ow_b"]))
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
print("  NOTE: Tchouameni's absence is France's single biggest structural")
print("  NOTE: loss of the tournament — priced as +0.03 opponent-facing.")
print("  NOTE: Morocco held the Netherlands and shut out Canada; their floor")
print("  NOTE: is high even when outgunned (2022 SF: lost to France only 2-0).")
print("  NOTE: Re-run if Saibari/Riad passed fit (atk_b=0, def_b=0) or out.")
print()

# ── Markdown output for the record ────────────────────────────────────────
OUT.mkdir(exist_ok=True)
lines = [
    "# World Cup 2026 Quarterfinal — France vs Morocco",
    "",
    "Thu Jul 9, Boston Stadium (Gillette, Foxborough) — neutral venue, sea level.",
    "",
    "Model: Dixon-Coles Poisson from ELO, tactical multipliers, T5 absences, T7 knockout motivation.",
    "",
    "## ELO chain",
    "",
    f"- France: {round(fra_pre)} -> R32 {round(fra_r32)} (beat Sweden 3-0) -> R16 {FRA} (beat Paraguay 1-0)",
    f"- Morocco: {round(mar_pre)} -> R32 {round(mar_r32)} (1-1 Netherlands, won pens = ELO draw) -> R16 {MAR} (beat Canada 3-0)",
    "",
    "## Fair odds (90 minutes)",
    "",
    "| Market | France | Draw | Morocco |",
    "|---|---:|---:|---:|",
    f"| Probability | {r['pa']}% | {r['pd']}% | {r['pb']}% |",
    f"| Fair odds | {r['oa']} | {r['ox']} | {r['ob']} |",
    "",
    "## Asian handicap (90 minutes)",
    "",
    "| Line | Win | Push | Lose | Morocco fair | France fair |",
    "|---|---:|---:|---:|---:|---:|",
] + [
    f"| Morocco {label} | {pw*100:.1f}% | {pp*100:.1f}% | {pl*100:.1f}% | {fb:.2f} | {fa:.2f} |"
    for (label, pw, pp, pl, fb, fa) in hcp_rows
] + [
    "",
    "## First half only (goal share {:.0%})".format(FIRST_HALF_GOAL_SHARE),
    "",
    "| Market | France | Draw | Morocco |",
    "|---|---:|---:|---:|",
    f"| HT result | {p1h_a*100:.1f}% @ {fo(p1h_a)} | {p1h_d*100:.1f}% @ {fo(p1h_d)} | {p1h_b*100:.1f}% @ {fo(p1h_b)} |",
    "",
    "| 1H line | Win | Push | Lose | Morocco fair | France fair |",
    "|---|---:|---:|---:|---:|---:|",
] + [
    f"| Morocco {label} | {pw*100:.1f}% | {pp*100:.1f}% | {pl*100:.1f}% | {fb:.2f} | {fa:.2f} |"
    for (label, pw, pp, pl, fb, fa) in hcp_1h_rows
] + [
    "",
    f"- 1H Over 0.5: {p1h_o05*100:.1f}% @ {fo(p1h_o05)} | 0-0 at HT: {(1-p1h_o05)*100:.1f}% @ {fo(1-p1h_o05)}",
    f"- 1H Over 1.5: {p1h_o15*100:.1f}% @ {fo(p1h_o15)} | Under 1.5: {(1-p1h_o15)*100:.1f}% @ {fo(1-p1h_o15)}",
    "",
    "## Totals",
    "",
    f"- Over 2.5: {r['po25']}% @ {r['oo25']}",
    f"- Under 2.5: {100 - r['po25']:.1f}% @ {r['ou25']}",
    "",
    "## Advance to SF (inc. ET/pens)",
    "",
    f"- France: {r['pw_a']}% @ {r['ow_a']}",
    f"- Morocco: {r['pw_b']}% @ {r['ow_b']}",
    f"- Pens split if 90min draw: France {r['pen_a']}% / Morocco {100 - r['pen_a']:.1f}%",
    "",
    "## Most likely scorelines",
    "",
    ", ".join(f"{s[0]}-{s[1]} ({p*100:.1f}%)" for s, p in r["scorelines"]) + ".",
    "",
    "## T5 — Absences / data risk",
    "",
    "- France: Tchouameni OUT (first-choice DM anchor — the big one, +0.03 opponent-facing), "
    "Thuram OUT (rotation forward, -0.01 attack). Front four all fit.",
    "- Morocco: Saibari hamstring doubt (-0.02 attack), Riad CB fitness doubt (+0.02 defensive absence). "
    "Re-price at zero if both passed fit.",
    "",
    "## T7 — Motivation",
    "",
    "- Morocco +0.02: 2022 semifinal revenge narrative, second consecutive WC quarterfinal, "
    "Boston crowd will skew heavily Moroccan.",
    "- France +0.01: defending finalists' focus, nothing extra.",
    "",
    "## Assumptions / risk flags",
    "",
    "- ELO chain uses house K=40 convention; shootout counts 0.5, opponents at post-group baseline.",
    "- Boston Stadium is sea-level and neutral — no altitude or host adjustment.",
    "- Handicap probabilities come straight off the Dixon-Coles score matrix; whole lines quote "
    "fair odds excluding the push.",
    "- Market snapshot at pricing time (2026-07-08): France -180 / Draw +290 / Morocco +550 (90-min ML).",
]
out_path = OUT / "qf_france_morocco_pricing.md"
out_path.write_text("\n".join(lines), encoding="utf-8")
print("  Written: {}".format(out_path))
print()
