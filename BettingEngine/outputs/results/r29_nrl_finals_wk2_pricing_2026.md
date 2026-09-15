# NRL Finals Week 2 (R29) — pricing, 2026-09-15

**SF1 Sydney Roosters v Cronulla Sharks** — Allianz Stadium, Sat 19 Sep 7:50pm AEST
**SF2 New Zealand Warriors v Newcastle Knights** — **Eden Park, Auckland**, Sun 20 Sep
4:05pm AEST / 6:05pm NZST

Fixtures confirmed against the official nrl.com draw API and two media sources.

## Verdict — NO BET on either game this far out

Both games clear the EV gate on the frozen spec. Neither survives scrutiny. Reasons are
specific and are set out below, and **teams are not named until Tuesday**.

---

## Prices

| | model margin | model total | market line | market total | market H2H |
|---|---|---|---|---|---|
| SF1 | **Roosters -1.4** | 47.0 | Roosters **-6.5** @1.90 | 45.5 @1.90 | 1.44 / 2.82 |
| SF2 | **Warriors -9.3** | 51.5 | Warriors **-5.5** @1.90 | 44.5 @1.90 | 1.51 / 2.57 |

### Tier build-up

```
                          T1     T2     T3     T4     T5    T6    T7   margin  total
Roosters v Sharks       +2.4   +0.0   -1.0   +1.5   -1.5   +0.0  ...    +1.4    47.0
Warriors v Knights      +7.3   +0.0   +2.0   +0.0   +0.0   +0.0  ...    +9.3    51.5
```
Totals also carry T7 emotional +0.60 both games and **T8 weather -2.0 on SF2**.

**ELO entering the semis:** Dolphins 1595.1, Penrith 1588.7, **Warriors 1580.3**,
**Roosters 1547.3**, **Knights 1532.4**, **Sharks 1531.9**.

## Monte Carlo

200,000 sims. Dispersion is **measured, not assumed**: margin SD **18.88**, totals SD
**13.53**, taken from 2024-26 AusSportsBetting closing lines vs actual results (n=273 /
634) and cross-checked against the documented model RMSE of 18.39.

The blend run is 50/50 model/market and is the one that matters, because **this model's
2026 margin MAE is 14.49 against the market's 14.28** — the market is the better
estimator, so a large disagreement should be read as the model being wrong.

| | frozen | 50/50 blend |
|---|---|---|
| SF1 Sharks +6.5 | **+15.4%** | +5.6% |
| SF1 Sharks H2H @2.82 | +32.9% | +18.1% |
| SF1 Over 45.5 | +3.5% | -0.6% |
| SF2 Warriors -5.5 | **+10.3%** | +3.0% |
| SF2 Over 44.5 | **+32.7%** | +14.2% |

---

## Why each one is not a bet

### SF1 — the model is 5.1 points off the market toward a team whose injuries T5 is not pricing

The model has the Roosters at -1.4 where the market has -6.5, which makes Sharks +6.5
look like +15.4%. ELO agrees the teams are close (1547.3 v 1531.9, a 15-point gap).

⚠️ **But T5 fired ZERO for Cronulla, and Cronulla's injury list is not zero.** Carrying
into this week: Jesse Ramien (pectoral, season-ending), Michael Gabrael (suspended
through finals week 3), and unresolved questions over Braydon Trindall (dislocated
shoulder), Mawene Hiroti (ribs) and KL Iro. Those were excluded deliberately under the
"already in the ratings" rule — they have been absent for weeks, so feeding them to T5
would double-count. That rule is right on average. **It is exactly the wrong rule if the
market is pricing a fresh absence the model has not seen.**

**This is the same shape as the documented AFL PF1 fault** — a large model-vs-market gap
pointing at a team whose absences T5 cannot represent, which turned out to be a broken
input rather than an opportunity. The market taking the Roosters to -6.5 despite their
form (lost 50-20 to Souths in R27, lost to the Dolphins in R26, lost to the Tigers in
R25, lost QF1) is information, not an error.

⚠️ Also note **T4 gave the Roosters +1.5 and that is largely double-counted home
advantage** — 10 of their 12 Allianz games in the sample are home games, and T1 already
carries `home_advantage_points: 2.5` plus a team-specific term. Removing it would push
the model further toward the Sharks, so the T4 defect is not what is creating this
signal — but the signal still fails on T5.

### SF2 — the handicap is marginal and the totals edge is one the model does not have

Warriors -5.5 at +10.3% frozen collapses to **+3.0% blended**, under any sensible gate.

**Over 44.5 at +32.7% is the loudest number on the page and must be ignored.** This
season's study measured **the NRL model's totals at -0.14% ROI across 117 games** — no
edge at all, at either the open or the close. The handicap is where this model's edge
lives (60.7%, +15.17%); the totals are noise, and a 7-point totals disagreement is a
reason for suspicion, not a bet.

⚠️ **Weather supports the same conclusion.** Eden Park at kickoff: 12.4C, 0.0mm,
**wind 26.0 km/h with gusts to 72.4 km/h**. The engine classified `moderate_wind` and
applied -2.0 to the total, but **the classifier uses sustained wind only and does not
see the gusts**, so the true suppression is probably larger than -2.0 and the model's
51.5 is too high.

⚠️ **Eden Park is not the Warriors' home ground.** First NRL final ever played there,
~48,500 expected (a NZ rugby league record), Knights' first visit. T4 correctly returns
0 because no history exists — but **T1's home-advantage term is still being applied as
though this were Mt Smart**, which likely overstates the Warriors.

---

## Tier coverage — 6 of 9 real

| tier | state |
|---|---|
| T1 ELO | ✅ rebuilt over all 28 games to 2026-09-13 |
| T2 style | ⚠️ data present (as_of 2026-09-08) but fired +0.0 on both — unverified whether that is a genuine no-fire. **Snapshot holds 16 teams, not 17.** |
| T3 situational | ✅ fires (+2.0 SF2 — Knights travelling to Auckland) |
| T4 venue | ✅ seeded this session — but see the double-count note above. Eden Park correctly 0. |
| T5 injury | ⚠️ **PROVISIONAL** — only Egan Butcher (Roosters, concussion, failed HIA in QF1). Teams named Tuesday. |
| T6 referee | ❌ not announced (Tue/Wed) |
| T7 emotional | ✅ reasoned — `must_win` both sides in both games (symmetric, nets to zero on handicap, +0.6 total). **Rejected with reasons:** Roosters `shame_blowout` (already spent in QF1), `star_return` for Crichton/Walker/Trindall (all unconfirmed — "I don't know about Gussy"), `rivalry_derby` (neither is a derby), milestones/farewells (none found; Tupou's 300th was earlier in 2026). |
| T8 weather | ✅ **real forecast, first time this season** |
| T10 Origin | ✅ correctly dormant |

⚠️ **T7 has no flag type for the Eden Park story** — a historic first final and a record
crowd have no representation in the schema. Same gap as the AFL siege-mentality finding.

## Engine faults found and fixed this session

1. **DB was ~5 rounds stale.** R25 results missing, R26/R27/R28 absent entirely. All
   backfilled from the nrl.com API and cross-checked against AusSportsBetting — every
   scoreline agreed on both sources.
2. ⚠️ **T8 weather has been dead all season.** Every row in `weather_conditions` was
   `mock_clear` 20C/5km/h, because **46 of 47 venues had NULL lat/lng**. Fixed by running
   `load_geo_data.py` (25 venues + **team_home_bases 17/17**, which also repairs T3).
3. ⚠️ **T4 venue has been a silent no-op all season.** `seed_venue_stats.py` reads
   seasons **2023 + 2025**; `model.db` holds **only 2026**, so it wrote zero rows every
   time and reported success. Now defaults to 2026 with a `--seasons` flag.
4. **Eden Park was not in `venues`** — added (id 47).
5. Display bug: the "T7 Weather check" block prints the **emotional** delta under a
   Weather heading.

## Still open

- Teams Tuesday -> re-run T5. Refs Tue/Wed -> T6.
- **R24 has 8 duplicate fixtures (match_id 197-204)**, no results, no dependents.
  Deletion was denied as irreversible; harmless to ELO but R24 reads as 16 games.
- `data/nrl/origin/2026.json` absent on this machine (T10 skipped — correct for finals).
- No ML shadow run for these games.
