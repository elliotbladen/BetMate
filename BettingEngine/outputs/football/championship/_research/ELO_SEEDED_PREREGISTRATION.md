# Pre-registration — Elo-seeded new-team ratings (candidate 2)

**Written 2026-09-14, BEFORE the variant was run.** Same discipline as
`RESET_FIX_PREREGISTRATION.md`. The rule below is not to be edited after the numbers
land.

## What changed in the objective, and why that is legitimate

The first test required **both** markets to improve. The owner has since stated the
actual requirement: the spine carries no edge on its own — the **tier stack supplies the
edge** — so the spine only has to avoid being *worse*, and an improvement on 1X2 is a
bonus rather than the point.

That is a change of objective by the person who owns it, not a re-scoring of the failed
run. It is written down here, before this candidate is run, precisely so it cannot be
mistaken for moving the goalposts afterwards. The previous result stands as a fail on
the terms it was set.

It does not rescue `shrunk_current_season`. That mode was worse on O/U in **10 seasons
out of 10** and raised expected totals by +0.098 goals in 9 of 10. Unanimous is not
"basically even".

## The candidate

`mode="elo_seeded"`. A club new to the division takes its attack and defence from its
**Elo**, not from a current-season Dixon-Coles refit.

The reasoning is structural rather than empirical. Elo is a single number per club: it
can express "stronger" but has no vocabulary for "higher scoring". It therefore cannot
push attack and defence in contradictory directions, and cannot move the league goal
level the way an independent two-parameter refit did. The mapping from Elo to
attack/defence is calibrated by regressing log attack and log defence on Elo across the
**established** clubs in the same fit, then applying those slopes to the new clubs.
Nothing is tuned on the new clubs themselves.

## The rule — fixed now

Baseline is `league_average`: pooled 1X2 **1.0554**, pooled O/U **0.6908**.
Surprise score, lower is better. "Not worse" is defined as within **+0.002**.

Keep `elo_seeded` only if ALL of:

1. **O/U not worse**: `d_ou <= +0.002`
2. **1X2 not worse**: `d_1x2 <= +0.002`
3. **At least one genuinely better**: `d_1x2 <= -0.002` OR `d_ou <= -0.002`
4. **No lopsided degradation**: neither market is worse in 8 or more of the 10 seasons

Condition 4 is the guard that caught the last candidate. A change can look flat pooled
while losing almost every season, and that is a real defect hiding inside an average.

## Choose vs confirm

Results are reported split as well as pooled:

- **2015/16–2020/21** (6 seasons)
- **2021/22–2024/25** (4 seasons)

There is only one candidate here, so there is no selection to protect against — the
split is reported so a result driven by one era is visible rather than buried. A verdict
that holds in one half and reverses in the other is not a pass regardless of the pooled
number. 2025/26 stays sealed.

## Unchanged

Walk-forward, spine only, no tiers, 2,436 fixtures where at least one club is new to the
division. Market reference is de-vigged closing odds — Pinnacle first, average as
fallback, because the average columns are empty before 2019/20. Scorer is re-validated
on known answers at the start of every run.

`min_matches` stays at 50 and remains untested.
