"""
FIFA World Cup 2026 — FINAL: Spain vs Argentina
Sunday July 19, MetLife Stadium (East Rutherford, NJ) — neutral venue, sea level.

⚠️ CORRECTED 2026-07-16: the semifinal/QF scripts in this engine chained ELO from
`data/elo_ratings.py`, a hand-maintained dict whose header claims a "late-2025
eloratings.net" baseline but was never actually verified against the real site
(the planned Kaggle Elo import was never completed — see repo history). That file
had Argentina ~94 points above Spain pre-tournament, which produced an "Argentina
favoured" price for the semifinal and an early draft of this Final. Fact-checked
against two independent real sources on 2026-07-16 and it does not hold up:
  - eloratings.net direct (mid-tournament, Jul 7 2026): Spain 2177 (#1), Argentina
    2151 (#2) — Spain AHEAD, not behind.
  - blog.recommend.games, citing eloratings.net Jun 10 2026 (day before kickoff):
    Spain 35.3% tournament win probability vs Argentina 23.0% — Spain the clear
    pre-tournament Elo favourite.
  - eloratings.net direct (current, post-SF, Jul 16 2026): **Spain 2232, Argentina
    2177** — used directly below instead of the internal engine's chained numbers.

This version uses the real, current, post-semifinal eloratings.net figures for
both finalists rather than re-deriving them from the flawed internal baseline.
Everything else (Dixon-Coles pricing engine, T2 tactical, T5 absences, T7
motivation, T9 pressure tier) is unchanged from the rest of this engine.

T1 ELO (real, eloratings.net) | T2 Tactical | T5 Absences | T7 Motivation | T9 pressure (Final tier)

Usage:
    cd C:\\Users\\ElliotBladen\\Apps\\BettingEngine
    python WorldCupEngine/scripts/price_final_spain_argentina.py
"""
import sys
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "outputs"
sys.path.insert(0, str(DATA))

from knockout_context import PRESSURE_EDGE_BY_ROUND

K = 40  # house convention — kept for reference; not used to derive ESP/ARG below

# ── Real Elo ratings (eloratings.net, current as of 2026-07-16, post-semifinal) ──
# Source: eloratings.net direct query, 2026-07-16. Spain #1, Argentina #2 overall.
ESP = 2232
ARG = 2177

print()
print("  ELO source: eloratings.net DIRECT (real, current, post-semifinal) — 2026-07-16")
print("    Spain      {} (world #1)".format(ESP))
print("    Argentina  {} (world #2)".format(ARG))
print("    Gap: Spain +{} — REVERSES the earlier chained-ELO draft, which had".format(ESP - ARG))
print("    Argentina ahead by ~66 using the internal engine's unverified baseline file.")

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
               mot_a=0.0, mot_b=0.0, round_idx=4):
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

    # Final pressure edge from knockout_context.py — ELO-weighted ET/pens split
    pressure = PRESSURE_EDGE_BY_ROUND.get(round_idx, 0.0)  # round idx 4 = Final
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


# ── T5 absences (confirmed via web search 2026-07-16) ────────────────────
# Spain: no fresh injury news for the final. Pre-tournament doubts (Yamal
#   hamstring, Merino stress fracture, Nico Williams hamstring) all resolved
#   or squad-managed weeks ago. Spain have conceded once in the entire
#   tournament and are unbeaten in 37 straight — essentially full strength.
# Argentina: Cristian "Cuti" Romero has carried a partial MCL tear since a
#   group-stage knock (R2 vs Austria), came off at halftime of extra time
#   vs Switzerland (QF) exhausted, but played through the England SF with
#   no reported withdrawal — treated as a managed knock, not a confirmed
#   out. Lisandro Martinez is the ready deputy if Romero doesn't start.
#   Messi has no fitness concerns and played every minute of the QF.
r = price_game(
    "Spain", ESP,
    "Argentina", ARG,
    atk_a=0.00, def_a=0.00,      # Spain: essentially full strength
    atk_b=0.00, def_b=0.02,      # Argentina: Romero managed knock (small opponent-facing defensive risk)
    mot_a=0.01,                  # Spain: first World Cup final since 2010, 37-game unbeaten run
    mot_b=0.02,                  # Argentina: defending champions, Messi's likely last WC, back-to-back final
    round_idx=4,                 # Final pressure tier
)

print()
print("=" * 72)
print("  FIFA WORLD CUP 2026 — FINAL")
print("  Spain vs Argentina — Sun Jul 19, MetLife Stadium, East Rutherford NJ (neutral)")
print("  T1 ELO + T2 Tactical + T5 Absences + T7 Motivation + pressure/pens (Final tier)")
print("=" * 72)
print()
print("  Spain ELO: {}  |  Argentina ELO: {}  |  Diff: {:+d}".format(ESP, ARG, r["diff"]))
print("  xGoals:    Spain {:.3f}  —  Argentina {:.3f}  (xG total: {})".format(r["lam"], r["mu"], r["xg"]))
print()
print("  -- 90-MINUTE RESULT --------------------------------------------")
print("  Spain win       {:5.1f}%   @  {:5.2f}".format(r["pa"], r["oa"]))
print("  Draw            {:5.1f}%   @  {:5.2f}".format(r["pd"], r["ox"]))
print("  Argentina win   {:5.1f}%   @  {:5.2f}".format(r["pb"], r["ob"]))
print()
print("  -- OVER / UNDER 2.5 GOALS ----------------------------------------")
print("  Over 2.5        {:5.1f}%   @  {:5.2f}".format(r["po25"], r["oo25"]))
print("  Under 2.5       {:5.1f}%   @  {:5.2f}".format(100 - r["po25"], r["ou25"]))
print()
print("  -- LIFT THE TROPHY (inc. ET + pens if 90min draw, pens split {:.1f}/{:.1f}) --".format(
    r["pen_a"], 100 - r["pen_a"]))
print("  Spain champions      {:5.1f}%   @  {:5.2f}".format(r["pw_a"], r["ow_a"]))
print("  Argentina champions  {:5.1f}%   @  {:5.2f}".format(r["pw_b"], r["ow_b"]))
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
print("  MARKET CHECK (web-sourced 2026-07-16, opening lines):")
print("  Bookmaker 90-min: Spain ~5/4 (2.25) | Argentina ~5/2 (3.50)")
print("  Bookmaker to lift trophy: Spain -156 (~1.64) / ~58% | Argentina +136 (~2.36) / ~43%")
print("  Model here vs market: NOW AGREES with the market on the favourite (Spain), after")
print("  correcting the ELO input. Spain 90-min win prob {:.1f}% vs market-implied ~44.4%".format(r["pa"]))
print("  (1/2.25) — same side, model slightly less bullish on Spain than the market. Champions")
print("  number: Spain {:.1f}% here vs market's ~58%; Argentina {:.1f}% here vs market's ~43%".format(r["pw_a"], r["pw_b"]))
print("  — closely aligned once the real eloratings.net figures replace the flawed internal")
print("  baseline. Still no CLV/closing-line validation history on this engine, but the direction")
print("  and rough size of this price now make sense against independent data.")
print()

# ── Markdown output for the record ────────────────────────────────────────
OUT.mkdir(exist_ok=True)
lines = [
    "# World Cup 2026 FINAL — Spain vs Argentina",
    "",
    "Sun Jul 19, MetLife Stadium, East Rutherford NJ — neutral venue, sea level.",
    "",
    "Model: Dixon-Coles Poisson from ELO, tactical multipliers, T5 absences, T7 knockout motivation.",
    "",
    "## ELO source — CORRECTED 2026-07-16",
    "",
    "Earlier WC scripts in this engine (including the first draft of this Final and the "
    "England/Argentina semifinal) chained ELO from `data/elo_ratings.py`, a hand-maintained file "
    "that was never actually verified against real eloratings.net data — it had Argentina ~94 "
    "points above Spain pre-tournament. Fact-checked against two independent sources and it does "
    "not hold up: eloratings.net direct (Jul 7, mid-tournament) had **Spain 2177 (#1) ahead of "
    "Argentina 2151 (#2)**; blog.recommend.games, citing eloratings.net from Jun 10 (day before "
    "kickoff), had **Spain a 35.3% tournament win probability vs Argentina's 23.0%** — Spain the "
    "clear pre-tournament favourite by real Elo, not Argentina.",
    "",
    f"- Spain: **{ESP}** (world #1, eloratings.net direct, current as of 2026-07-16, post-semifinal)",
    f"- Argentina: **{ARG}** (world #2, eloratings.net direct, current as of 2026-07-16, post-semifinal)",
    f"- Gap: Spain +{ESP - ARG} — reverses the earlier chained-ELO draft, which had Argentina ahead "
    "by ~66 using the internal engine's unverified baseline.",
    "",
    "## Fair odds (90 minutes)",
    "",
    "| Market | Spain | Draw | Argentina |",
    "|---|---:|---:|---:|",
    f"| Probability | {r['pa']}% | {r['pd']}% | {r['pb']}% |",
    f"| Fair odds | {r['oa']} | {r['ox']} | {r['ob']} |",
    "",
    "## Totals",
    "",
    f"- Over 2.5: {r['po25']}% @ {r['oo25']}",
    f"- Under 2.5: {100 - r['po25']:.1f}% @ {r['ou25']}",
    "",
    "## Lift the trophy (inc. ET/pens)",
    "",
    f"- Spain: {r['pw_a']}% @ {r['ow_a']}",
    f"- Argentina: {r['pw_b']}% @ {r['ow_b']}",
    f"- Pens split if 90min draw: Spain {r['pen_a']}% / Argentina {100 - r['pen_a']:.1f}%",
    "",
    "## Most likely scorelines",
    "",
    ", ".join(f"{s[0]}-{s[1]} ({p*100:.1f}%)" for s, p in r["scorelines"]) + ".",
    "",
    "## T5 — Absences / data risk",
    "",
    "- Spain: no fresh injury news for the final. Pre-tournament doubts (Yamal hamstring, Merino stress "
    "fracture, Nico Williams hamstring) all resolved or squad-managed weeks ago. Spain have conceded once "
    "in the entire tournament and are unbeaten in 37 straight games — essentially full strength. No adjustment.",
    "- Argentina: Cristian \"Cuti\" Romero has carried a partial MCL tear since a group-stage knock (R2 vs "
    "Austria), came off at halftime of extra time vs Switzerland (QF) exhausted, but played through the "
    "England semifinal with no reported withdrawal — treated as a managed knock, not a confirmed absence. "
    "Small opponent-facing defensive adjustment applied (def_b +0.02). Lisandro Martinez is the ready deputy "
    "if Romero doesn't start. Messi has no fitness concerns and played every minute of the quarterfinal.",
    "",
    "## T7 — Motivation",
    "",
    "- Spain +0.01: first World Cup final since 2010, riding a 37-game unbeaten run — historic weight, "
    "standard knockout-focus treatment per house convention.",
    "- Argentina +0.02: defending champions going for back-to-back titles, Messi's likely last World Cup — "
    "judgment value, kept modest per house convention on motivation edges.",
    "",
    "## Market check (web-sourced 2026-07-16, opening lines)",
    "",
    "- Bookmaker 90-min: Spain ~5/4 (2.25 decimal) / Argentina ~5/2 (3.50 decimal).",
    "- Bookmaker to lift the trophy: Spain -156 (~1.64 decimal, ~58% implied) / Argentina +136 "
    "(~2.36 decimal, ~43% implied) — Kalshi has it at a similar 58/43 split.",
    "- **This model now agrees with the market on the favourite (Spain), after correcting the ELO input.** "
    f"90-min: Spain {r['pa']}% vs market-implied ~44.4% (1/2.25) — same side, model a touch less bullish "
    f"on Spain. Champions market: Spain {r['pw_a']}% here vs the market's ~58%; Argentina {r['pw_b']}% here "
    "vs the market's ~43% — closely aligned once the real eloratings.net figures (Spain 2232, Argentina "
    "2177, current as of 2026-07-16) replaced the flawed internal `elo_ratings.py` baseline that had "
    "Argentina ~66 points ahead post-knockout. That earlier number drove both the first draft of this Final "
    "and the England/Argentina semifinal pricing — this correction should be read back onto that SF writeup too.",
    "- Squawka's own prediction (Spain 2-1 Argentina) now points the same direction as this model's "
    "favoured side, for what that's worth as one more data point.",
    "",
    "## Assumptions / risk flags",
    "",
    "- **ELO input corrected 2026-07-16** — see the ELO source section above. The rest of the engine "
    "(Dixon-Coles pricing, T2 tactical multipliers, T5/T7 adjustments, pressure tier) is unchanged and uses "
    "the same house K=40 convention as every prior WC script for context, but Spain/Argentina's actual "
    "ratings are now sourced directly from eloratings.net rather than derived from it.",
    "- Final pressure tier (0.010) applied per `knockout_context.py`'s `PRESSURE_EDGE_BY_ROUND` — the "
    "largest pressure/composure edge of the tournament, reflecting maximum stakes.",
    "- MetLife Stadium (East Rutherford, NJ) is sea-level and neutral for both sides — no altitude or "
    "host-nation adjustment. Crowd will likely skew heavily Argentine (as it did in the semifinal) but the "
    "model does not price crowd for non-host nations, per house convention.",
    "- This WC engine is a light ELO/Dixon-Coles model with no CLV or closing-line validation history. The "
    "ELO-source bug found and fixed here (internal baseline file never verified against the real site it "
    "claimed to be based on) likely also affected every earlier WC price in this tournament that used "
    "`elo_ratings.py` — worth a full audit before trusting any of the QF/SF writeups' exact numbers, even "
    "though the QF picks themselves (Norway/England, Argentina/Switzerland) happened to land on the right side.",
    "- Re-run this script if either camp names a confirmed team news update before kickoff (3:00pm ET Jul 19).",
]
out_path = OUT / "final_spain_argentina_pricing.md"
out_path.write_text("\n".join(lines), encoding="utf-8")
print("  Written: {}".format(out_path))
print()
