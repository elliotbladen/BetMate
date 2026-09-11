# EFL Championship GW7 pricing — and three model faults that made it a no-bet round

**Date:** 2026-09-10
**Scope:** Championship 2026/27 GW7 (11–13 Sep), 1X2 + O/U 2.5, normal and shadow.
**Outputs:** `BettingEngine/outputs/football/championship/2026-27/gw07/`
**Engine code changed:** none. Tests 255 pass / 3 pre-existing failures.

---

## What was asked

"Price up week 4 or 5 of the EFL, both 1X2 and O/U 2.5, normal mode and shadow mode."

## What the round actually was

GW4 (1–2 Sep) and GW5 (5–6 Sep) are both played and graded. So is GW6 (8–9 Sep) —
a midweek round of nine played fixtures plus three postponements (Bristol City v
Lincoln, Middlesbrough v Millwall → 15 Sep; Wolves v Portsmouth → 20 Oct). The next
unplayed round is **GW7**, which is what was priced. Six clubs arrive on five games.

ESPN event-ID blocks confirm the ordering (descending IDs as matchweek ascends):
293–304 = GW4, 281–292 = GW5, 269–280 = GW6, 257–268 = GW7.

---

## Data fix that had to happen first

**football-data.co.uk had not published the 8–9 Sep round.** Its live `E1.csv` stopped
at 60 matches. Pricing straight off it would have (a) dropped a full round from the
D-C fit and Elo, and (b) reported **7 days' rest for every club** when West Ham and
Wrexham were on a 3-day turnaround — so T3 fatigue would not have fired at all.

Fix: new reusable script `BettingEngine/scripts/ingest_espn_results_supplement.py`.
Pulls completed matches from ESPN for a date range, writes only the facts the engine
reads (goals, result, referee, shots, SOT, corners, fouls, cards), tags them
`SourceSupp=espn`, backs up the CSV first, and previews by default (`--apply` to write).
All nine referee names were checked against the historical football-data convention
before insertion (all nine matched, n=9–245 each). Fit went 6684 → 6693 matches,
zero duplicate (Date, Home, Away) keys.

`fetch_results.py --live-merge` de-dupes on (Date, HomeTeam, AwayTeam) keep="last",
so the official rows will replace the supplement automatically. **Re-run it once
football-data publishes 8–9 Sep** to recover the odds columns.

Also rebuilt: `player_match_stats_espn_2026.csv` (Championship 2026/27, 2759 rows,
all 69 matches). 28 cached feeds had been saved pre-kickoff with no rosters and were
re-fetched; 8 feeds for the 1 Sep round were missing entirely.

---

## Three model faults found

### 1. The O/U 2.5 isotonic calibrator has almost no resolution, and a hard ceiling

`fit_totals_calibrator` fitted on 2205 rows returns **six distinct values** over the
raw range 0.25–0.80 and is **censored at 0.6042** — raw 0.61 and raw 0.99 both map
to 0.6042. The widest plateau is raw 0.34–0.48 → 0.4495.

Across GW7's twelve fixtures the model emits **four** distinct P(Over) values;
**eight fixtures share 0.4495**. Model P(Over) is below market no-vig in **10/12**.

This is the calibrator honestly reporting that the raw D-C totals model does not
discriminate in this league — in the calibration set the actual over-rate is 0.4534
at raw 0.445, 0.4511 at raw 0.4685, 0.4451 at raw 0.5217 (flat, mildly inverted)
across the band holding 75% of games. The ceiling is set by 20 games with raw > 0.7
that went 50% over.

**Consequences:** O/U 2.5 selections cannot be ranked on this column; the model
structurally cannot price an Over (min fair Over 1.655), so its totals signal is
always Under. GW5's O/U picks were 10 Unders / 2 Overs, 5/12, −2.04% CLV.

**This is a different fault from the EPL totals bias.** Championship is goals-fed
(`xg_csv: null`) so the Understat scale-break does not apply — confirmed. EPL
over-predicts; Championship under-predicts and cannot resolve between games.
It needs its own fix.

### 2. New-team D-C reset distorts totals (not 1X2)

`_reset_new_team_dc_ratings` forces the six clubs new to the division to
att = def = hfa = 1.00, discarding their 5–6 games. Five of twelve GW7 fixtures
are affected. Re-priced with a current-season D-C refit shrunk n/(n+6)
(`_supporting/reset_sensitivity.json`):

| Fixture | Prod total | Alt total | Δ | ΔP(home) |
|---|---:|---:|---:|---:|
| West Ham v Wrexham | 2.50 | 2.62 | +0.12 | +0.005 |
| Bolton v Cardiff | 2.48 | 2.78 | +0.30 | +0.003 |
| Preston v Lincoln | 2.45 | 1.86 | −0.59 | −0.036 |
| Swansea v Burnley | 2.54 | 2.97 | +0.43 | +0.035 |
| Sheffield United v Wolves | 2.75 | 3.47 | +0.72 | −0.007 |

**The 1X2 effect is small** — when both clubs are misstated in the same direction the
errors cancel in the H/D/A split. That corrects my initial expectation, and it differs
from the EPL GW4 finding where the reset drove 1X2 EV directly. **The totals effect is
large and mostly one-way** (4 of 5 move up, to +0.72 goals), because the reset flattens
exactly the clubs with extreme scoring profiles: Wolves top scorers (13 GF), Burnley
worst defence (13 GA), Bolton and Cardiff next worst.

T8 does not rescue it: no ClubElo file exists, so it falls back to static preseason
`new_team_elo_priors` worth ±0.03 xG at this decay weight — and it gives Burnley
**+180** (relegated PL), i.e. it makes the bottom club stronger.

### 3. Ratings lag the table badly

Rank correlation between raw D-C net strength (att × def, pre-reset) and 2026/27 PPG
is **0.334** (0.384 excluding reset clubs). At `decay_rate: 0.001` (half-life ≈ 693
days) six games barely move a rating. Burnley are bottom with the worst defence and
are the **highest-rated club in the raw fit**; Derby are 21st and rated 10th;
Birmingham 11th and rated 23rd. This is the direct source of the round's biggest
model-vs-market gaps: West Ham (.400 vs .592), Sheffield United (.487 vs .320),
Derby (.417 vs .291) — 13–19pp against a 28-book consensus.

---

## T5: 62 of ~110 listed absentees were already in the ratings

Published Championship injury lists carry ~110 names. Cross-checked every one against
the 2026/27 per-player feeds: **62 have made zero appearances this season**. Their
absence is already embedded in the results the D-C fit and Elo are built on, so
feeding them to T5 double-counts. That is very likely what sank GW5 — its absence list
was largely these same season-long absentees, T5 pushed opponents up, and all five
selections lost.

T5 was restricted to players who (a) are on a published unavailability list, (b)
featured in one of their club's last two completed matches, and (c) start ≥60% of the
time. Result: **10 players, 6 clubs**. Both suspensions (Pereira/West Brom,
Metcalfe/Millwall) were derived independently from red cards in the match data and
then confirmed against a published list. Millwall's four absences hit the 0.15
attack-disruption cap.

Every EV is reported with and without T5 (`_supporting/model_t5_off.json`).

---

## Result: no bets

Ten selections cleared 10% EV at best price. All rejected:

* **4 Unders** (Bolton/Cardiff +26.6%, West Ham/Wrexham +23.9%, Middlesbrough/Norwich
  +23.2%, West Brom/QPR +16.7%) — all from two plateau values; the ordering is purely
  the market's. Two are also on reset fixtures biased toward Under.
* **Wrexham +69.6%, draw +26.3%** — West Ham's rating is a forced constant.
* **Sheffield United +51.0%** — Wolves reset; the matrix's +7 is seven overlapping
  Sheffield-United base-rate cells ("All games +8.7pp", "Home games +9.8pp"), one fact
  counted seven times.
* **Derby +37.6%** — rating lag; matrix opposes at −2 (short rest ≤3d −11.7pp n=41).
* **Watford +16.4%** — collapses to +8.6% with T5 off; the whole edge is Stoke's
  two absences.
* **Bolton/Cardiff draw +10.7%** — both clubs reset.

Season context: Championship model selections are **0W–8L, −100% ROI** (paper, not
staked) with **+6.67% CLV** — good prices, wrong sides, which is the signature of a
mis-specified probability. GW5 1X2 RPS 0.2286 vs closing market 0.1915.

---

## Follow-ups

1. **Fix new-team handling** — fit clubs new to the division on current-season data,
   or populate a live ClubElo feed so T8 has a real prior. Unlocks 5/12 fixtures.
2. **Rebuild the Championship totals model** — or suspend the O/U 2.5 market for this
   league until it has measured edge. The E1 file now carries `HxG`/`AxG` non-null for
   all 60 published 2026/27 matches, which would feed this *and* the EPL xG work
   already flagged as the top football priority.
3. **Shorten decay or add a current-season blend** — 0.33 rank correlation with the
   live table is too low to bet 13-point disagreements against 28 books.
4. **Before GW8:** re-run `fetch_results.py --live-merge` for the official 8–9 Sep
   rows; inject T6 referees once the EFL publishes them; refresh `ppda_dated.csv`
   (still only matchweek-1 2026/27 rows, and `get_ppda` has no recency guard).

## Files

New scripts: `ingest_espn_results_supplement.py`, `price_efl_week7_normal_shadow_2026.py`,
`efl_gw7_candidate_confluence.py`, `_efl_gw7_ev_screen.py`, `_efl_gw7_reset_sensitivity.py`,
plus `_efl_gw7_{market,absences,doubts}_2026.json`.
Outputs: `gw07/{1_model.md,1_model.json,2_bets.md,2_bets.csv,2_bets_matrix.md,2_bets_matrix.json}`
and `gw07/_supporting/{ev_screen.csv,model_t5_off.json,reset_sensitivity.json,normal_full_working.txt}`.


---

## Addendum — GW7 slate saved for grading (same session)

User asked to save the round's selections to judge next week. Saved the **seven
≥20% EV selections** to `gw07/2_bets.csv` in the gameweek schema, marked
`status = tracked_selection_not_staked` (the engine recommendation stays NO BET).
Stakes follow the frozen matrix rule: 7.5u total, with Sheffield United at 1.5u on
net +7. The previous `2_bets.csv` (candidate rejection screen) moved to
`_supporting/candidate_screen.csv`.

**Matrix coverage extended.** The frozen rule scores 1X2 team sides only, so two
scans were added: `_supporting/matrix_full_scan.csv` (all 24 team-sides, not just
EV qualifiers) and `_supporting/matrix_ou_scan.json` (`scripts/_efl_gw7_ou_confluence.py`,
applying the same category slices and ±7.5pp cell test to `stats_goals`). Of the
seven saved selections only **Sheffield United (+7)** has matrix support; the three
Unders score +0, +0 and −1, and the draw is unscoreable.

**Grader bug found and fixed.** `score_football_saved_bets.py` could not grade a
**Draw** or an **Under** — draws were scored as losses against the AWAY odds column,
and unders were graded *backwards* against the OVER odds column. Four of the seven
saved selections would have been mis-graded next week. Patched, and the historical
2026-09-08 output re-runs byte-identical (12 bets, 3W-9L, −7.23u, +8.57% CLV).

New reusable entry point `scripts/grade_gameweek_saved_bets.py` grades any gameweek
`2_bets.csv` for result, P&L and CLV, handles all three 1X2 sides and both O/U sides,
and reports fixtures with no result row rather than silently skipping them. Validated
by re-grading GW5: reproduces its published figures exactly (0W-5L, −5.50u, −100% ROI,
+12.61% CLV, beat close 3/5).

**Next week:** run `fetch_results.py --league championship --live-merge` (which also
replaces the ESPN 8-9 Sep supplement with official rows), then
`grade_gameweek_saved_bets.py --bets .../gw07/2_bets.csv --league championship`.
