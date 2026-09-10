# EFL Championship 2026/27 — GW7 model card (11–13 Sep)

**Built:** 2026-09-10 · **Engine:** production Championship engine (`league=championship`)
**Driver:** `scripts/price_efl_week7_normal_shadow_2026.py`
**Markets priced:** 1X2 and Over/Under 2.5, **normal** (production) and **shadow** (comparison only)
**Machine-readable:** `1_model.json` · working: `_supporting/normal_full_working.txt`

---

## Which round this is

GW4 (1–2 Sep) and GW5 (5–6 Sep) are both played and graded. So is **GW6 (8–9 Sep)**,
a midweek round of which nine fixtures were played and three postponed
(Bristol City v Lincoln and Middlesbrough v Millwall to 15 Sep, Wolves v Portsmouth
to 20 Oct). This is therefore **GW7**, and six clubs arrive on five games rather
than six.

### Data fix applied before pricing

football-data.co.uk had **not published the 8–9 Sep round** at build time — its live
`E1.csv` stops at 60 matches (5–6 Sep). Pricing on that file would have:

* dropped a full round from the Dixon-Coles fit and the Elo, and
* reported **7 days' rest for every club**, when West Ham and Wrexham are on a
  3-day turnaround and eight other clubs on 3–4 days.

The nine completed matches were supplemented from ESPN (scores, referees, shots,
shots on target, corners, fouls, cards; no odds) via a new reusable script,
`scripts/ingest_espn_results_supplement.py`. Rows are tagged `SourceSupp=espn`,
the CSV was backed up first, and `fetch_results.py --live-merge` de-duplicates on
(Date, HomeTeam, AwayTeam) keeping the source row — so the official football-data
rows will replace these automatically once published. All nine referee names were
verified against the historical football-data naming convention before insertion.
Fit size went 6684 → 6693 matches.

---

## Prices

λ–μ are the post-tier expected goals. "N" = normal, "S" = shadow. Fair odds, no vig.

| Match | KO | N λ–μ | N 1X2 fair | N O2.5 | S 1X2 fair | S O2.5 | Shadow XI dates |
|---|---|---|---|---|---|---|---|
| West Ham v Wrexham | 09-11 | 1.32–1.18 | 2.50 / 3.43 / 3.24 | 2.22 | 2.73 / 3.32 / 3.01 | 2.38 | 08 Sep / 08 Sep |
| Bolton v Cardiff | 09-12 | 1.35–1.13 | 2.41 / 3.43 / 3.40 | 2.22 | 2.15 / 3.49 / 4.03 | 2.26 | 08 Sep / 08 Sep |
| Derby v Birmingham | 09-12 | 1.19–0.86 | 2.40 / 3.21 / 3.68 | 2.48 | 2.44 / 2.99 / 3.92 | 3.02 | 09 Sep / 09 Sep |
| West Brom v QPR | 09-12 | 1.54–0.89 | 2.02 / 3.56 / 4.46 | 2.22 | 2.27 / 3.43 / 3.72 | 2.25 | 09 Sep / 09 Sep |
| Blackburn v Millwall | 09-12 | 1.14–1.00 | 2.93 / 3.33 / 2.80 | 2.22 | 2.69 / 3.23 / 3.14 | 2.39 | 08 Sep / 05 Sep |
| Charlton v Portsmouth | 09-12 | 1.10–1.10 | 2.70 / 3.25 / 3.11 | 2.22 | 2.88 / 3.08 / 3.04 | 2.52 | 09 Sep / 05 Sep |
| Middlesbrough v Norwich | 09-12 | 1.63–1.20 | 2.16 / 3.70 / 3.76 | 2.10 | 2.14 / 3.73 / 3.77 | 2.07 | 05 Sep / 09 Sep |
| Preston v Lincoln | 09-12 | 1.28–1.17 | 2.63 / 3.43 / 3.05 | 2.22 | 2.48 / 3.34 / 3.36 | 2.41 | 08 Sep / 05 Sep |
| Southampton v Bristol City | 09-12 | 2.17–1.15 | 1.76 / 4.31 / 5.01 | 1.68 | 1.75 / 4.17 / 5.29 | 1.84 | 08 Sep / 05 Sep |
| Swansea v Burnley | 09-12 | 1.46–1.08 | 2.31 / 3.52 / 3.54 | 2.22 | 2.46 / 3.38 / 3.36 | 2.42 | 08 Sep / 08 Sep |
| Watford v Stoke | 09-12 | 1.45–0.88 | 2.10 / 3.45 / 4.26 | 2.22 | 2.10 / 3.26 / 4.59 | 2.59 | 08 Sep / 08 Sep |
| Sheffield United v Wolves | 09-13 | 1.70–1.05 | 2.05 / 3.70 / 4.12 | 2.10 | 2.06 / 3.53 / 4.34 | 2.40 | 08 Sep / 06 Sep |

## Model vs market

Market = Odds API snapshot 2026-09-10 13:29 UTC, ~28 non-exchange books per fixture
(exchanges excluded — their prices are gross of commission). "no-vig" normalises 1/odds.

| Match | Best 1X2 | Market no-vig H/D/A | Model H/D/A | Best O/U | Mkt no-vig O | Model O | Δ(O) |
|---|---|---|---|---|---|---|---|
| West Ham v Wrexham | 1.62/4.33/5.50 | .592/.226/.182 | .400/.292/.308 | 1.65/2.25 | .581 | .449 | −.132 |
| Bolton v Cardiff | 2.50/3.80/2.70 | .383/.260/.357 | .415/.291/.294 | 1.64/2.30 | .577 | .449 | −.128 |
| Derby v Birmingham | 3.30/3.50/2.20 | .291/.279/.430 | .417/.311/.272 | 2.00/1.83 | .473 | .403 | −.071 |
| West Brom v QPR | 2.05/3.80/3.60 | .460/.261/.278 | .495/.281/.224 | 1.79/2.12 | .536 | .449 | −.087 |
| Blackburn v Millwall | 2.95/3.50/2.40 | .328/.277/.395 | .342/.301/.358 | 1.93/1.93 | .496 | .449 | −.046 |
| Charlton v Portsmouth | 2.75/3.30/2.80 | .351/.296/.353 | .370/.308/.322 | 2.20/1.67 | .429 | .449 | +.020 |
| Middlesbrough v Norwich | 1.91/4.00/3.90 | .497/.246/.257 | .464/.270/.266 | 1.62/2.35 | .586 | .476 | −.110 |
| Preston v Lincoln | 2.30/3.60/3.15 | .418/.268/.313 | .381/.291/.328 | 1.83/1.95 | .518 | .449 | −.069 |
| Southampton v Bristol City | 1.71/4.20/4.75 | .558/.235/.207 | .569/.232/.200 | 1.60/2.30 | .587 | .595 | +.008 |
| Swansea v Burnley | 2.20/3.60/3.30 | .441/.268/.291 | .433/.284/.283 | 1.83/1.96 | .520 | .449 | −.070 |
| Watford v Stoke | 2.45/3.50/3.00 | .395/.280/.325 | .475/.290/.235 | 1.94/1.88 | .488 | .449 | −.039 |
| Sheffield United v Wolves | 3.10/3.60/2.35 | .320/.269/.411 | .487/.270/.243 | 1.75/2.05 | .542 | .476 | −.066 |

---

## Tier status

| Tier | Status | Note |
|---|---|---|
| T1 D-C + Elo | live | goals-fed, 6693 matches, decay 0.001 |
| T2 PPDA | **stale** | `ppda_dated.csv` has only matchweek-1 2026/27 rows (16–17 Aug) and `get_ppda` has no recency guard. Effect this round is small (≈ −0.02 xG/team) but it is a 4-week-old input. |
| T3 form / rest | live | now correct — the 8–9 Sep supplement makes West Ham and Wrexham register 3-day rest (×0.94 each) |
| T5 injuries | live, tightly filtered | see below |
| T6 referee | **not injected** | the EFL had not published GW7 appointments (ESPN `gameInfo.officials` null on all 12) |
| T7 set-piece | live | corners from actual 2026/27 matches |
| T8 new-team prior | live, weak | static preseason Elo priors (no ClubElo file); weight 1 − n/15 ≈ 0.53–0.60 → ±0.03 xG |
| T9 new manager | off | no qualifying appointments |

### T5 — how the absence list was built (and why it is short)

The published Championship injury lists carry ~110 names. Cross-checking every name
against the 2026/27 per-player match feeds shows **62 of them have made zero
appearances this season**. Their absence is already fully embedded in the results
the D-C fit and the Elo are built on, so feeding them to T5 **double-counts**.

T5 was therefore restricted to players who (a) appear on a published unavailability
list, (b) featured in one of their club's last two completed matches, and (c) start
at least 60% of the time. That leaves **10 players across 6 clubs**:

| Club | Out | Pos | λ/μ effect |
|---|---|---|---|
| West Ham | Valentín Castellanos | ST | λ 1.45 → 1.32 |
| Bolton | Lewis Brunt | RB | λ 1.37 → 1.35, μ 1.10 → 1.13 |
| West Brom | Brayann Pereira (red card, 9 Sep) | RB | λ 1.57 → 1.54, μ 0.86 → 0.89 |
| Millwall | de Norre, Coburn, Metcalfe (red card), Sykes | CM/ST/CM/RB | μ 1.17 → 1.00 (**attack disruption hits the 0.15 cap**) |
| Burnley | Hannibal Mejbri | CM | μ 1.11 → 1.08 |
| Stoke | Gallagher, Lawal | AM/CB | μ 0.95 → 0.88 |

Both suspensions were derived independently from red cards in the match data and
then confirmed against a published list. The excluded names are recorded in
`scripts/_efl_gw7_doubts_2026.json`. The full T5-off price set is kept at
`_supporting/model_t5_off.json` so every EV can be read with and without T5.

---

## Three model faults that bear on this round

### 1. The O/U 2.5 calibrator has almost no resolution — and a hard ceiling

`fit_totals_calibrator` fits isotonic regression on 2205 backtest rows. Over the
raw range 0.25–0.80 it returns **six distinct values**, and it is **censored at
0.6042** — raw 0.61 and raw 0.99 both map to 0.6042. The widest plateau spans raw
0.34–0.48 and maps everything to 0.4495.

Across the twelve GW7 fixtures the model produces **four distinct P(Over) values**:
0.4025, 0.4495 (×8), 0.4756 (×2), 0.5950. Eight fixtures share one number.

This is the calibrator faithfully reporting that the raw D-C totals model has no
measured discrimination in this league: in the calibration set the actual over-rate
is 0.4534 at raw 0.445, 0.4511 at raw 0.4685 and 0.4451 at raw 0.5217 — flat, and
mildly *inverted*, across the band where 75% of games land. The 0.6042 ceiling is
set by just 20 games with raw > 0.7 that went 50% over.

**Consequence: O/U 2.5 selections cannot be ranked on this column, and the model
structurally cannot price an Over** (minimum fair Over odds 1.655). Model P(Over)
sits below the market's no-vig number in **10 of 12** fixtures, so every O/U signal
this round is an Under. That is a mechanical property of the calibrator, not a read
on the fixtures.

Note this is a *different* fault from the EPL totals bias in CLAUDE.md. Championship
is goals-fed (`xg_csv: null`), so the Understat scale-break does not apply here —
confirmed. The EPL model over-predicts totals; the Championship model under-predicts
them and cannot resolve between games.

### 2. New-team D-C reset distorts totals, not 1X2

`_reset_new_team_dc_ratings` forces the six clubs new to the division
(Burnley, West Ham, Wolves down; Bolton, Cardiff, Lincoln up) to att = def = hfa = 1.00,
discarding their 5–6 games this season. Five of the twelve GW7 fixtures contain such a club.

Re-pricing those five with a current-season D-C refit (shrunk n/(n+6)) —
`_supporting/reset_sensitivity.json`:

| Fixture | Prod total | Current-season total | Δ | Prod P(O) | Alt P(O) | ΔP(home) |
|---|---:|---:|---:|---:|---:|---:|
| West Ham v Wrexham | 2.50 | 2.62 | +0.12 | .449 | .476 | +0.005 |
| Bolton v Cardiff | 2.48 | 2.78 | +0.30 | .449 | .476 | +0.003 |
| Preston v Lincoln | 2.45 | 1.86 | −0.59 | .449 | .355 | −0.036 |
| Swansea v Burnley | 2.54 | 2.97 | +0.43 | .449 | .559 | +0.035 |
| Sheffield United v Wolves | 2.75 | 3.47 | +0.72 | .476 | .604 | −0.007 |

The 1X2 effect is small (max ±0.036) because when both clubs are misstated in the
same direction the errors largely cancel in the H/D/A split. **The totals effect is
large and mostly one-way**: four of five move up, by as much as 0.72 goals. The
reset is flattening exactly the clubs whose scoring profiles are extreme — Wolves are
the league's top scorers (13 GF), Burnley have the worst defence (13 GA), Bolton and
Cardiff the next two worst. Every Under signal on a reset fixture is therefore biased
in the direction the model is already biased.

### 3. Slow decay leaves ratings well behind the current table

Rank correlation between the raw D-C net strength (att × def, pre-reset) and
2026/27 points per game is **0.334** across all 24 clubs, **0.384** excluding the
six reset clubs. With `decay_rate: 0.001` (half-life ≈ 693 days) six games barely
move a rating. Concretely: Burnley are bottom of the table with the league's worst
defence and are the **highest-rated club in the raw fit** (that is what the reset
exists to paper over); Derby are 21st on 4 points and rated 10th; Birmingham are
11th and rated 23rd.

That is the direct source of this round's largest model-vs-market disagreements —
West Ham (model .400 home vs market .592), Sheffield United (.487 vs .320), Derby
(.417 vs .291). These are 13–19 percentage-point disagreements with a 28-book
consensus in a liquid market.

---

## Limitations

* GW6 results supplemented from ESPN, not football-data (see above). No odds columns
  on those nine rows — they feed the fit and the rest/form tiers, not the CLV backtest.
* T6 referee un-injected; on the Championship ref coefficient this is worth roughly
  ±0.05 on raw P(Over) at the extremes.
* T2 PPDA is a matchweek-1 seed.
* Shadow is comparison-only: it projects each club's most recent *completed* starting
  XI (GW6 where played, GW5 otherwise) and applies a ±0.12-goal capped ridge delta.
  It is not a lineup forecast; official GW7 XIs are not available.
* The shadow model was trained on 2023/24 with a 2024/25 holdout and improves goal
  MAE by 0.016 — a real but very small effect. Treat divergence as a flag, not a price.
* The 2025/26 season remains the sealed vault and was not used anywhere.
