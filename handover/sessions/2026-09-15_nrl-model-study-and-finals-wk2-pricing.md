# 2026-09-15 — Betting study, betmate.au fixes, and NRL finals week 2 (UNFINISHED)

Long session. Three finished pieces of work, then **NRL finals week 2 pricing which is
part-built and is where the next session should start.** Read section 5 first.

---

## 1. Championship new-team reset — CLOSED, merged to main

Covered by its own diary `2026-09-15_championship-new-team-reset-closed.md`. Summary:
the third candidate (`elo_seeded_level_neutral`) FAILED its pre-registered rule at
O/U +0.0063 against a +0.002 tolerance — the pre-registration had named +0.007 in
advance as still a fail. `new_team_reset` stays `league_average` for totals.

**Owner then signed off `elo_seeded` for 1X2 only**, shipped as a per-market split
(`new_team_reset_1x2: elo_seeded`). Merged as `b3b56fa`.

⚠️ **Championship O/U 2.5 is closed — owner confirmed it will not be bet.** Pooled, the
totals model scores 0.69263 against 0.69107 for a constant base-rate guess: it loses to
a sticky note.

---

## 2. betmate.au — four fixes, all live and verified on the served page

| commit | what |
|---|---|
| `73aea0b` | **screenshot bets were logged at FULL stake, should be HALF.** 11 rows. $25 = 0.5u (unit is $50), set by the "0.5u flat" NRL rows above them. Football running total 2.90 -> 1.37, NRL 2.76 -> 2.46 |
| `9bd231c` | stripped `(stake $25; return $65.75)` from market labels; dollars moved to comments |
| `d489238` | removed the CLV column from the Sports Betting tab (every row was an em dash) |
| `41b4a6c` | removed the **Predicted** column from all three model tabs; **filled CLV on 15 rows** from the AusSportsBetting download |
| `3d12d8a` | added an **Avg CLV (pts)** card beside the beat-CLV count |

**CLV sign convention, derived from existing rows and verified on seven knowns before
writing** (documented at the head of `lib/researchData.ts`): positive always means we got
the better number. Line and Under = `taken − close`; Over = `close − taken`.

⚠️ **17 rows stay blank and are structurally unmeasurable** — live/in-play, multis, a
margin bucket, a 2nd-half total, and all 8 football rows (UCL file is a 2003-2024
benchmark with no closing fields; nothing prices Championship cards; football-data E0
stops 31 Aug so 13-14 Sep is unpublished).

⚠️ **STILL OPEN — a suspected sign error I did NOT change:** `Bulldogs +31.5 PYL` stores
`clv: -8.0` but the close was +23.5, which by the repo's own convention is **+8.0**.
Owner asked only for blanks to be filled, so it was left. Flip it if confirmed.

---

## 3. The betting study — was the owner lucky, unlucky, or neither?

**Answer: neither, and if anything slightly LUCKY.** 183 priceable bets, 132.11u staked.

```
ACTUAL        -1.11u   ROI -0.84%
EXPECTED      -6.94u   ROI -5.25%   (de-vigged closing prices)
vig baseline  -5.56u   ROI -4.21%   (betting blindly into the close)
LUCK          +5.83u      +4.41%    95% CI [-10.2%, +19.2%]
```

Per sport: **NRL** actual +3.40% / expected -3.00% / price edge vs close **+0.89%**.
**AFL** actual -5.03% / expected -7.48% / price edge **-2.98%, CI [-11.3%, -3.9%] EXCLUDES
ZERO — a real negative edge.**

**H2H is the worst market on EXPECTATION in both codes** (-6.11% NRL, -9.03% AFL),
independently confirming the standing "shrink or stop the h2h book" finding.

⚠️ **The page's "Beat CLV" is a COUNT** (71% NRL, 61% AFL) and hid that AFL's average CLV
is NEGATIVE — winners +3.97 pts, losers -7.17 pts. That is why the Avg CLV card was added.

**Timing:** NRL takes the open (42% AT the open, only 32% better) and the market drifts
+0.47 pts toward it -> beats the close by **+0.91 pts, CI [+0.42, +1.42], SIGNIFICANT.**
AFL is level with the close (-0.08, CI [-1.83, +1.54]).
⚠️ I initially claimed the AFL drift ran against the owner and that betting later would
help — **that was overstated, the CI spans zero. Corrected in-session. Do not act on it.**

Lines do NOT round-trip: only 8% of AFL games close near their opening number, and on
line/total bets the PRICE is pinned at ~1.90 (mean open 1.901, close 1.901) — the LINE
moves, not the odds.

---

## 4. The NRL model study — the important one

**Every NRL model handicap pick, flat $1, 117 games:**

```
at the OPEN    71-46 (60.7%)   staked $117   profit +$17.75   ROI +15.17%   CI [-1.4%, +32.4%]
at the CLOSE   71-46 (60.7%)   staked $117   profit +$18.35   ROI +15.68%
totals         57-60 (48.7%)                                  ROI  -0.14%   <- no edge
```

Against the owner's actual NRL betting: **+3.09% realised on a -3.00% expectation.**

**Checked for the obvious ways this could be fake, and it is not:** model margin MAE
**14.49** / RMSE 18.45 against the documented rules MAE of 14.29, so it is genuinely
pre-game; favourites covered only **47.9%**, so it is not a favourite artefact; every
winning price was between 1.80 and 2.00, and stripping the five best still leaves +11.56%;
settlement was hand-verified on five games.

**The leak is WHAT is bet, not WHICH games.** Games actually bet 58.9% / +11.88%; games
skipped 62.3% / +18.20%. Even on the games actually bet, the plain handicap at the
standard line returned **+11.88%** versus the -3.00% expectation of what was actually bet
(h2h, multis, live, PYL, totals).

⚠️ **Two things stop this being proven.** Against break-even it is only z=1.75 (p~0.08).
And it is front-loaded: **May-Jul n=75 -> +3.80%; Aug-Sep n=42 -> +35.48%.**

⚠️ **NO FILTER IS SUPPORTED.** Tested: bet-everything +15.17%, EV>=10% +12.05%, EV>=20%
+17.06%, EV<10% +18.57%. All CIs overlap; there is no monotonic direction. **Do not adopt
a threshold — any cutoff is fitted to 117 games.**
⚠️ I earlier said "the biggest disagreements are the worst bets" — that was measured
against the CLOSE, which is not knowable at bet time. **Measured against the OPEN it
reverses** (gap>10 pts: +1.92% vs close, +42.08% vs open, n~12 either way). No reliable
finding in that tail; I corrected this in-session.

**Phase split** (owner's early/mid/late intuition, using the documented Origin rule with
G1 May 27 / G2 Jun 17 / G3 Jul 8): early(9) +7.22%, **ORIGIN(51) +7.75%**, late(49)
+15.92%, finals(8) +66.88%. Origin era returns roughly half the rest, but the difference
CI is [-21.2%, +47.4%] — not established.
⚠️ **The mechanism is the opposite of "Origin is harder":** model MAE is at its *lowest*
during Origin (13.41 vs market 13.60 — model better), and *worse than the market* late
(15.27 vs 14.91) and in finals (14.21 vs 11.88). **ROI is highest exactly where the model
is measurably worse than the market** — which is an argument that the late-season surge is
variance, not skill.

Working files: `/private/tmp/.../scratchpad/study/` (nrl_joined.csv, classified.json,
bets.json). Not committed — regenerate if needed.

---

## 5. ⚠️ NRL FINALS WEEK 2 PRICING — START HERE

**Fixtures (confirmed from the official nrl.com draw API AND two media sources):**

| | match | when | venue |
|---|---|---|---|
| SF1 | **Sydney Roosters v Cronulla Sharks** | Sat 19 Sep, 7:50pm AEST | Allianz Stadium |
| SF2 | **New Zealand Warriors v Newcastle Knights** | Sun 20 Sep, 4:05pm AEST / 6:05pm NZST | **Eden Park, Auckland** |

⚠️ **Eden Park is NOT the Warriors' home ground.** First NRL final ever played there,
~48,500 expected (a NZ rugby league record). Their venue history is all Go Media/Mt Smart.
Knights' first visit. This is a genuine T4 problem, not a normal home game.

### What was FIXED this session (all written to data/model.db)

The DB was ~5 rounds stale. Now current through finals week 1:
- **R25 results loaded** via `scripts/fetch_nrl_results.py --round 25` (the standing
  blocker in CLAUDE.md — now cleared).
- **R26, R27, R28 matches + results inserted**, and **R29 fixtures loaded**, by
  `scratchpad/backfill_nrl.py` off the nrl.com draw API. **Every scoreline was
  cross-checked against `data/nrl/historical/latest.xlsx` and agreed on both sources.**
- **Eden Park added to `venues` (venue_id 47)** with lat/lng -36.8748/174.7445.
- **ELO now rebuilds cleanly**, applying all 28 games 2026-08-19 -> 2026-09-13.

**ELO entering the semis:** Dolphins 1595.1 | Penrith 1588.7 | **Warriors 1580.3** |
**Roosters 1547.3** | **Knights 1532.4** | **Sharks 1531.9** | Souths 1523.1 | Cowboys
1500.2 | Raiders 1492.1 | Storm 1492.0 | Bulldogs 1482.9 | Manly 1479.3 | Eels 1459.6 |
Broncos 1442.1 | Tigers 1427.8 | Titans 1414.5 | Dragons 1410.8

### Baseline prices (T1 + T3 ONLY — every other tier is currently ZERO)

```
Roosters v Sharks     T1 +2.4  T3 -1.0  -> margin +1.4  hcap -1.4  H2H 54.6%  total 45.8
Warriors v Knights    T1 +7.3           -> margin +7.3  hcap -7.3  H2H 72.9%  total 53.9
```

**DO NOT BET OFF THESE.** They are a baseline, not a price.

### ⚠️ What is still missing — the actual work

1. **T5 injuries — NOTHING LOADED.** Research started, not finished. What was found:
   - **Roosters:** Egan Butcher OUT (concussion, failed HIA). Angus Crichton (foot) a
     possible return but Robinson said "I don't know about Gussy". Sam Walker (ankle) not
     ruled out — "never say never", was seen running. Salesi Foketi back from flu.
   - **Sharks:** Nicho Hynes and Blayke Brailey both named after being rested. Braydon
     Trindall (dislocated shoulder) possible return. Mawene Hiroti and KL Iro injured.
   - **Warriors / Knights: NOT RESEARCHED YET.**
   - ⚠️ Teams are named **Tuesday** for finals — re-check before pricing.
   - Load via `scripts/load_injury_round.py` or the `injury_reports` table.
2. **T6 referees — not announced** (Tue/Wed). Re-check.
3. **T7 emotional — NOT DONE.** Owner explicitly asked for it. Angles worth testing:
   Eden Park record crowd / historic first final; Knights' first trip there; Roosters lost
   50-20 to Souths in R27 then beat nobody in QF1 (check `shame_blowout` threshold is 30+,
   they lost by 30 exactly in R27 — the R28 file already fired that once); must_win both
   games (single elimination).
4. **T8 weather — MOCKED, NOT REAL.** `TOMORROW_API_KEY` is missing from `.env.local`, so
   both games defaulted to `mock_clear` 20°C/5km/h. **Allianz has no lat/lng in the DB at
   all** ("SKIP — no lat/lng"). Eden Park now has coords. Get real forecasts manually for
   Sat night Sydney and Sun afternoon Auckland.
5. **T4 venue — DEAD.** `team_venue_stats` is EMPTY and `scripts/seed_venue_stats.py`
   reads seasons **2023 + 2025**, but the DB holds **only 2026** (218 matches), so it
   writes 0 rows. Either point the seeder at 2026, or seed from
   `data/nrl/historical/latest.xlsx` (3,629 rows, 2024-2026, has a Venue column).
   **Eden Park correctly gets 0 either way — no history exists.**
6. **T2 style** — data IS present (`team_style_stats` as_of 2026-09-08, 16 teams) but fired
   +0.0 on both games. Confirm that is a genuine no-fire and not a lookup failure.
   ⚠️ 16 teams, not 17 — one club is missing from the snapshot.
7. **Monte Carlo — NOT RUN.** AFL has `scripts/monte_carlo_afl_finals.py`; check whether an
   NRL equivalent exists or whether that one can be parameterised.

### ⚠️ Known DB defect left in place

**R24 has 8 duplicate fixtures (match_id 197-204)** — exact copies of 173-180 with no
results and no dependent rows. **I tried to delete them and the action was denied
(irreversible local destruction).** They are harmless to ELO (the rebuild joins `results`,
so resultless rows are invisible) and to R29 pricing, but R24 will read as 16 games in any
count. Delete when convenient:
`delete from matches where match_id between 197 and 204;`

### Commands to resume

```bash
cd /Users/elliotbladen/BetMate/BettingEngine
BETMATE_ROOT=/Users/elliotbladen/BetMate PYTHONUTF8=1 \
  .venv/bin/python scripts/prepare_round.py --season 2026 --round 29 --dry-run
# drop --dry-run to write; then scripts/export_round_csv.py
```
DB backup from before this session's writes:
`scratchpad/model.db.backup-20260915T125547` (scratchpad is session-scoped — copy it
somewhere durable if it still matters).

---

## Next session, in order

1. Finish T5 research (Warriors + Knights, and confirm Roosters/Sharks after Tuesday teams).
2. T7 emotional — the owner asked for it specifically.
3. Real weather for both venues; add Allianz lat/lng to `venues`.
4. Fix the T4 seeder (season list) and reseed.
5. Re-run `prepare_round.py --round 29`, then Monte Carlo.
6. Only then produce a price and a bet recommendation.
