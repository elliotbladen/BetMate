# Result — Elo-seeded new-team ratings: FAIL (but it found the real problem)

Run 2026-09-14 against the rule locked in `ELO_SEEDED_PREREGISTRATION.md` (commit
`32936eb`, 07:44:32Z, before the variant was run). Rule unchanged afterwards.

**Verdict: FAIL.** `new_team_reset` stays `league_average`. Both candidate modes remain
implemented and tested behind the config key; neither is the default.

## The numbers

2,436 fixtures, 10 seasons, walk-forward, spine only. Surprise score, lower is better.
Baseline is `league_average`.

| | 1X2 | seasons better | O/U | seasons better |
|---|---|---|---|---|
| baseline | 1.0554 | — | 0.6908 | — |
| shrunk_current_season | 1.0501 (−0.0053) | 7/10 | 0.7082 (+0.0174) | 0/10 |
| **elo_seeded** | **1.0366 (−0.0188)** | **10/10** | 0.7050 (+0.0142) | 2/10 |
| market (de-vigged close) | 1.0172 | — | — | — |

Against the locked rule: O/U not worse **FAIL** (+0.0142 vs a +0.002 tolerance); 1X2 not
worse PASS; at least one better PASS; no market worse in 8+ seasons **FAIL** (O/U worse
in 8). Two of four fail.

## The 1X2 result is the best thing measured so far

−0.0188, **better in all ten seasons**. Drop 2015/16 — where Elo has only one prior
season to work from and is an obvious outlier — and it is −0.0191 in **nine of nine**.
That is not noise, and it is three and a half times the gain the shrunk mode managed.

The trade is the same shape as before and is coherent: home **0.8364 → 0.8078** and away
**1.1840 → 1.1259** both improve while draws **1.2823 → 1.3231** worsen. Spreading
ratings apart makes a draw less likely, so a draw becomes more surprising.

## The root cause, and it is structural

Both candidates fail on totals, and both push expected goals the **same way**:

| | shift in expected total | fixtures pushed up |
|---|---|---|
| shrunk_current_season | +0.098 | 51% |
| elo_seeded | +0.119 | 72% |

This is not a coincidence and not a property of either method. **It falls out of the
model's algebra.** Expected goals is `lam = base × att_home / def_away` — defence
**divides**. So spreading defence ratings away from 1.0 raises average expected goals
*even when the spread is perfectly symmetric*: halving one club's defence adds a full
goal's worth of scoring, while doubling another's only takes half of one away. The
gains and losses do not cancel.

`league_average` sets every new club to att = def = 1.0, which is the only value that
introduces no level shift at all. **Any** method that gives new clubs real, differing
ratings will raise the totals — and the more spread it adds, the further it pushes. Which
is exactly what the table shows: elo_seeded adds more spread than shrunk, and moves the
level more (+0.119 vs +0.098).

So the two failures are one failure. We have been treating "give new clubs better
ratings" and "keep the goal level right" as though they were independent, and in this
parameterisation they are not.

## What follows

The 1X2 side is solved — Elo seeding wins in ten seasons out of ten. What remains is
purely the level shift, and it now has a named cause rather than a shrug.

The next candidate should keep the Elo ordering exactly as it is and neutralise the level:
after seeding, apply a single scalar correction to the new clubs' defence values so the
mean expected total across their fixtures matches the `league_average` baseline. That
preserves every bit of the 1X2 gain and removes the one thing breaking totals.

It needs its own pre-registration and its own run. It has NOT been tested, and the
failure above stands until it is.
