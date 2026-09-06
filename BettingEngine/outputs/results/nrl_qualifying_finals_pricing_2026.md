# NRL 2026 Qualifying Finals — Pricing Report

**Run date:** 2026-09-06 (Round 27 finishing today — fixture derived, not yet NRL-confirmed)
**Method:** Manual tier build. **The NRL engine could not be run on this machine**
(no NRL tables in `model.db`, ELO ~2 rounds stale, NRL ML features frozen at
2026-04-12, Odds API down). This is a hand price-up, weaker than the AFL semis one.

---

## Fixture (derived — ~95% certain)

Top 4 locked: **Warriors, Panthers, Dolphins, Roosters.** Panthers need only a
2+ pt win over Wests Tigers today to take the minor premiership off the Warriors
(who scraped Manly 31–30). Assuming that:

| Game | Home (seed) | Away (seed) | Venue | Likely slot |
|------|------------|------------|-------|-------------|
| **QF1** | Penrith Panthers (1st) | Sydney Roosters (4th) | CommBank Stadium, Penrith | Fri/Sat 11–12 Sep |
| **QF2** | NZ Warriors (2nd) | Dolphins (3rd) | Go Media Stadium, Auckland | Sat/Sun 12–13 Sep |

*If Penrith lose or win by 1: swap to Warriors v Roosters (Auckland) + Penrith v Dolphins (Penrith).*

---

## Rating base

From `results/r27_pricing_2026.csv` (pre 27–30 Aug round), hand-adjusted for the
two rounds since:

| Team | CSV ELO | Since | Working ELO |
|------|--------:|------|------------:|
| Penrith | 1564.9 | won R26 & R27 as expected | **~1567** |
| Roosters | 1578.2 | **thrashed by Dolphins (R26) then Souths 50–20 (R27)** | **~1555** ↓ |
| Warriors | 1574.4 | big win R26, scratchy 31–30 v Manly R27 | **~1573** |
| Dolphins | 1568.9 | beat Roosters, Parra 34–16, GC — in form | **~1573** ↑ |

NRL `points_per_elo_point = 0.08`, league home advantage ≈ 3.5 pts.

---

## QF1 — Penrith Panthers v Sydney Roosters (Penrith)

| Tier | Hcp (Penrith +) | Note |
|------|---:|------|
| T1 baseline | **+9 to +10** | ELO +1 + HFA 3.5 + form gap (Penrith strong / Roosters in freefall) |
| T3 situational | +1 to +2 | Roosters short trip; carrying two hidings into a final |
| T4 venue | +3.5 | Penrith Stadium fortress (dynasty ~85%+ there; CSV home-ground avg +15) |
| T5 injuries | **+4 to +5** | **Roosters: Sam Walker (HB) OUT — syndesmosis; Radley doubtful; Tedesco just back.** Penrith: Cogger 3-wk ban (Cole in) ≈ −1 |
| T6 referee | n/a | finals refs announced Tue — **not priced** |
| T7 emotional | −0.5 | Roosters off a 50–20 humiliation — small; finals usually a pride response |
| T8 weather | pending | Penrith mid-Sept night — check game day |
| **Model margin** | **Penrith ≈ −18 to −20** | |
| Model total | **~34–38** | Roosters attack gutted + Penrith grind + fortress |

**Estimated market:** Penrith −13.5/−15.5, H2H Penrith ~$1.22 / Roosters ~$4.75, total ~39–41.

**Read:** the model is **more bullish on Penrith than the market**, and for once
the home-favourite lean is backed by *hard recent evidence* — the Roosters lost
their halfback and got smashed by 30 last week. **Lean: Penrith on the handicap
if it opens ≤ −14.5.** H2H no value at ~$1.22. **Under** the total if it's ≥ 39.

---

## QF2 — NZ Warriors v Dolphins (Go Media Stadium, Auckland)

| Tier | Hcp (Warriors +) | Note |
|------|---:|------|
| T1 baseline | +1 to +2 | ELO level; HFA 3.5 offset by Dolphins' better recent form |
| T3 situational | **+2.5 to +3.5** | Dolphins trans-Tasman travel (~2,150 km + time zone) — real NRL penalty |
| T4 venue | +3.5 | Go Media a genuine Warriors fortress; home NRL final atmosphere |
| T5 injuries | +0.5 | nothing major either side; Warriors got bodies back for the run home |
| T6 referee | n/a | not priced |
| T7 emotional | **−1.5** | Warriors' finals-choke history + home pressure vs Dolphins' first real finals tilt (house money, no scar tissue) |
| T8 weather | pending | Auckland mid-Sept often wet/windy — would compress the total, mild help to the Dolphins' structure |
| **Model margin** | **Warriors ≈ −6 to −8** | |
| Model total | **~40–44** | |

**Estimated market:** Warriors −4.5/−6.5, H2H Warriors ~$1.60 / Dolphins ~$2.35, total ~41–44.

**Read:** model and market roughly agree. The model's home lean is bigger, but
the documented NRL bias (**rules model overrates home teams +9–11% vs market**)
says shave it — and after shaving, model ≈ market. The market rates the **Dolphins
above the Warriors for the title** ($7.50 v $11) despite the ladder, they're in
form, and they carry no finals baggage. So the marginal philosophical lean is
**Dolphins +the points / Dolphins H2H at $2.30+** — but it is **not a bet**.
Warriors-in-an-Auckland-final is a legitimately hard assignment for a visitor.

---

## Value verdict

| Selection | Confidence | Why / why not |
|---|---|---|
| **Penrith −handicap (≤ −14.5)** | Modest lean | Model −18/−20 vs market ~−14; Roosters genuinely broken (Walker out, 2 hidings, travel). Short-market/finals-compression risk. Wait for the real line. |
| **QF1 Under (≥ 39)** | Modest lean | Roosters attack gutted, Penrith fortress grind. |
| Penrith H2H | No | ~$1.22, no edge |
| QF2 Dolphins +pts / H2H | Watch only | Market efficient; NRL home-overcook bias + Dolphins form/freedom, but not enough to bet |
| QF2 Warriors anything | No | Model's edge is the untrustworthy home lean |

**Nothing is a confirmed bet.** Odds API is down so every market number above is
an estimate — re-check against real opening lines (Sun night / Mon). The one to
watch is **Penrith's handicap**.

---

## Tier coverage — BELOW THE 75% BAR

| Tier | Status |
|------|--------|
| T1 baseline | ⚠️ ELO ~2 rounds stale, hand-adjusted for form; no engine |
| T3 situational | ✅ rest/travel from fixture |
| T4 venue | ✅ both home fortresses applied |
| T5 injuries | ✅ from web team news (Walker, Radley, Cogger) |
| T6 referee | ❌ finals appointments not out until Tuesday |
| T7 emotional | ✅ manual (Roosters blowout, Warriors finals history) |
| T8 weather | ❌ 5–6 days out, not forecastable — check game day |
| ML shadow | ❌ NRL features frozen at 2026-04-12 on this machine |
| T10 Origin | n/a (September) |
| Market / EV | ❌ Odds API down — all market numbers are estimates |

**5 of 9 in-scope layers genuinely populated.** Treat this as a directional
first look, not a price you bet off. The AFL semis price-up is on much firmer
ground than this one.
