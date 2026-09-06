# AFL 2026 Semi Finals — Pricing Report

**Run date:** 2026-09-06
**Model:** Rules T1–T8 + ML (XGBoost) primary margin/H2H, rules primary totals.
Monte Carlo finals spec = 25% rules / 75% ML margin, bootstrapped 2025 residuals,
disagreement-widened.
**Round label:** 26 (wildcard = 25, priced earlier on the Mac).

---

## Finals Week 1 results brought in (ELO now current through 2026-09-05)

| Final | Result | ELO move |
|---|---|---|
| QF1 | **Hawthorn 72 def. Fremantle 40** (Optus) | Freo 1732 → **1681**, Hawthorn → 1705 |
| EF1 | **Geelong 107 def. Carlton 74** (MCG) | Geelong 1727 → **1748**, Carlton → 1610 |
| QF2 | **Sydney 141 def. Brisbane 88** (SCG) | Brisbane 1745 → **1706**, Sydney → 1743 |
| EF2 | **Adelaide 90 def. Western Bulldogs 68** (Adelaide Oval) | Adelaide 1638 → **1659**, Dogs → 1554 |

Results appended to `latest_with_finals_wk1.xlsx`, `features_afl.csv` rebuilt via
`game_log.py`. Post-week-1 ratings were applied as an explicit `FINALS_ELO_OVERRIDE`
because `get_current_elo()` otherwise lags one game (fine in the H&A season, not
across a finals week with three 30–53 pt upsets).

Hawthorn and Sydney won their QFs → straight to preliminary finals.
Fremantle and Brisbane lost their QFs → **host** the semis.

---

## Fixture

| Game | Home | Away | Venue | Date (local) |
|---|---|---|---|---|
| SF1 | Fremantle Dockers | Geelong Cats | Optus Stadium | Fri 11 Sep, 6:10pm AWST |
| SF2 | Brisbane Lions | Adelaide Crows | The Gabba | Sat 12 Sep, 7:35pm AEST |

---

## Model fair prices

### SF1 — Fremantle v Geelong (Optus)

| Metric | Rules | ML / Primary | Monte Carlo (finals spec) |
|---|---|---|---|
| Margin | Fremantle **−3.0** | Fremantle **−4.0** | Fremantle **−3.8** (mean) |
| H2H | Freo 53.3% / $1.88 | Freo **50.4% / $1.98** | Freo **52.8% / $1.89**, Geel 47.2% / $2.12 |
| Total | 183.7 | ML total **161** | 184 centre, ±wide (rules/ML gap 22 pts) |

- Raw ELO after the override: Geelong **1748** now rates **above** Fremantle **1681**;
  Optus home advantage (+46 ELO ≈ +4 pts) nearly cancels the gap. T1 margin only
  +2.1 Freo. Tiers: +3.0 Geelong travel to Perth, −2.0 style (Geelong edge),
  +1.0 injuries, −1.2 kicking, −4.5 weather (**totals only** — see caveat).
  Season calibration +4.0. → **pick'em, tiny Freo lean.**
- Rules and ML agree on direction and are within 1 pt. T9 form shadow leans
  Geelong (−2.2): Freo have been under their ELO expectation, Geelong over.

### SF2 — Brisbane v Adelaide (Gabba)

| Metric | Rules | ML / Primary | Monte Carlo (finals spec) |
|---|---|---|---|
| Margin | Brisbane **−15.8** | Brisbane **−25.8** | Brisbane **−23.3** (mean) |
| H2H | Bris 67.0% / $1.49 | Bris **65.1% / $1.54** | Bris **73.9% / $1.35**, Adel 26.1% / $3.83 |
| Total | 207.5 | ML total **153** | 207 centre, ±very wide (rules/ML gap 55 pts) |

- ELO: Brisbane **1706** vs Adelaide **1659** (+47) + Gabba fortress (+2.0) +
  Adelaide interstate travel. T1 +12.4 Brisbane. Tiers: +4.2 (Adelaide travel +
  Brisbane bounce-back off the 53-pt loss), +2.0 fortress, +1.5 injuries
  (Peatling out), −4.5 weather (totals only). → **Brisbane −15 to −18 on rules.**
- **ML is 10 pts more bullish (−25.8) → divergence flag.** ML reads Brisbane's
  H&A form/opp-adjusted margin as elite and Adelaide's underlying as softer than
  their ladder spot. Both models still agree Brisbane wins and covers a mid-teens
  line, so direction is aligned — but the 10-pt gap = elevated uncertainty, treat
  the rules number (−15.8) as the floor and true fair as roughly −18 to −20.

---

## Value check ⚠️ AGAINST ESTIMATED MARKET ONLY

**The Odds API is down and no live semi-final market has been published yet**
(fixture only confirmed today; books firm up Sun night / Mon). The lines below are
my estimates, not captured prices. EVs are indicative only — re-run against real
opening odds before betting.

| Selection | Est. market | Model prob | Est. EV | Read |
|---|---|---|---|---|
| Geelong H2H | $2.20 | 47.2% | **+3.8%** | below 10% gate; "model undercooks the market favourite" pattern — CLAUDE notes this went 4–8 ATS historically. Not a bet. |
| Geelong +7.5 | $1.90 | 54.2% cover | **+3.0%** | small line lean if the real line is Freo −7.5 or longer. Marginal. |
| Fremantle H2H / −7.5 | $1.70 / $1.90 | 52.8% / 45.8% | −10% / −13% | avoid |
| Brisbane H2H | $1.50 | 73.9% (MC) / 65% (rules-ML) | **+11%** (MC) / ~0% (conservative) | edge exists ONLY if the market is this soft; I'd expect books to open Brisbane ≈ $1.38–1.45 which erases it |
| Brisbane −14.5 | $1.90 | 58.1% cover | **+10%** | same caveat — depends entirely on line being ≤ −14.5. At −18/−20 there is no edge |
| Adelaide +14.5 / H2H | $1.90 / $2.60 | 41.9% / 26.1% | −20% / −32% | avoid |
| Overs (both) | — | model 74% / 80% | huge on paper | **NO BET.** rules/ML totals disagree by 22 and 55 pts; ML says 153–161, finals footy trends low; 2026 AFL totals −3.82u. Model's worst-documented market. |

---

## Verdict

**No disciplined value bet stands up right now.**

- **SF1 Fremantle v Geelong** is a genuine model-vs-market disagreement — the model
  has it a coin flip (post-QF, Geelong now the higher-rated side) while the market
  will likely install Fremantle a clear favourite on minor-premiership + Optus
  fortress. But this is exactly the "rules+ML agree, both under the market
  favourite" shape the project has already tested and found **unprofitable (4–8
  ATS)**. If the real line opens Fremantle −8.5 or longer, Geelong + the points is
  a small (~+3%) lean, nothing more.

- **SF2 Brisbane v Adelaide**: the model likes Brisbane to win and cover a mid-teens
  line at the Gabba. The paper EV clears 10%, but only against my soft market
  estimate and with a 10-pt rules/ML split. I expect the real market to price
  Brisbane close to the model (≈ −18, $1.40), leaving no edge. Also un-modelled:
  Brisbane looked disengaged in a 53-pt QF loss ("may have taken the Swans
  lightly" — Fagan); the ML can't see selection/psychology.

- **Totals**: ignore the model entirely this week.

**Action:** wait for real opening lines (Sunday night / Monday). The one number
worth watching is **Brisbane's handicap** — if it opens at −14.5 or shorter, the
rules+ML both back Brisbane to cover and it becomes a live play. Everything else
is a pass.

---

## T9 H2H matrix — Fremantle v Geelong (net lean)

Context applied: Fre home / after a loss / **normal rest ~8d**; Geelong away
interstate-long-haul / after a win / normal rest ~7d; Friday night; September;
finals; Optus Stadium. (The `afl_matrix_confluence.py` auto-run mis-read rest as
20 days off the stale Aug-26 xlsx and pulled the wrong "Long Rest ≥10d" row — the
figures below use the correct normal-rest row.)

| Context row | Fre edge% | Geel edge% | net (→Fre +) | N |
|---|---:|---:|---:|---|
| Generic home / away | −8.8 | +7.2 | −1.6 | 48/47 |
| Night game (≥18:00) | −16.0 | −2.5 | −18.5 | 24/48 |
| Thursday / Friday | −36.2 | +2.4 | −33.8 | 13/25 |
| Normal rest 7–9d | +6.2 | +7.5 | **+13.7** | 55/50 |
| After a loss / win | +4.3 | −2.2 | +2.1 | 39/66 |
| September = Finals* | −38.7 | −22.0 | −60.7 | 3/8 |
| H2H vs this opponent | +70.0 | +41.7 | **+111.7** | 5/5 |
| Venue: Optus Stadium | −7.6 | −5.0 | −12.6 | 51/4 |
| Geelong interstate / long-haul | . | −13.9 / +12.0 | −1.9 | 20/5 |

\* September and Finals are the same games — counted once below.

| Net measure (Sep=Finals de-duped) | Value | Lean |
|---|---:|---|
| Raw sum of edge % | **≈ −60** | Geelong |
| Raw sum of difference (pp) | **≈ −13** | Geelong |
| Sample-weighted edge % (N<10=0.3 / 10–25=0.6 / 25+=1.0) | **≈ −16** | Geelong |
| `afl_matrix_confluence.py` flag (20% / 3+) | **4-way BACK AWAY** | Geelong |

**Yes — there is a net edge well beyond ±5, and it points to Geelong.** Every
reasonable weighting lands between −12 and −35 toward the Cats. It is driven by
Fremantle's poor record *vs the market* in exactly this slot — Thu/Fri games
(38.5% actual win vs 60.3% market-implied, 2022–25), night games (54% vs 64%),
and September/finals (33% on 3 games). The only rows pulling toward Fremantle are
the 5-game head-to-head history (Fre 3–2, 60% vs 35% implied) and normal rest.

**This agrees with the model** (Monte Carlo had it 47.2% Geelong, i.e. a live
dog) and with the T9 confluence flag. So the matrix strengthens the "Geelong with
the points / Geelong H2H if the market over-favours Freo" lean — but note it is
still shadow-only, several rows are N=3–5, and the finals rows describe a
2022–25 Fremantle, not necessarily this year's minor premiers.

---

## Tier coverage

| Tier | Status |
|---|---|
| T1 ELO/baseline | ✅ current through FW1 (manual post-week-1 override applied) |
| T2 style | ⚠️ R23 snapshot, 3 rounds stale (Footywire not re-scraped) |
| T3 situational | ✅ travel + bounce-back fired |
| T4 venue | ✅ Gabba fortress applied |
| T5 injuries | ✅ light week — Peatling (Adel) out; Stanley (Geel) backup ruck; Freo net-neutral (Cox out ↔ Amiss/Chapman/Switkowski/Reid back) |
| T6 emotional | ❌ no scraper for finals — left neutral |
| T7 weather | ⚠️ live Tomorrow.io: Optus 0.3mm / Gabba 0.1mm (both effectively dry) yet model applied its −4.5 "light rain" totals tier — **over-twitchy at trace precip, treat totals as un-penalised** |
| T8 kicking | ✅ conversion rates applied (small) |
| ML shadow | ✅ available after installing `xgboost` into the venv |
| Market/EV | ❌ Odds API down — EVs above are vs estimates only |

7 of 9 layers genuinely populated. The two gaps (live market, T6) plus stale T2
and twitchy T7 are why this is a "quick look", not a bettable price.
