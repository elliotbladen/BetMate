# Pre-registration — does the new-team reset fix actually help?

**Written 2026-09-14, BEFORE any historical result was computed.** Committed ahead
of the harness deliberately: the point is that the yardstick cannot be chosen after
the numbers are seen. Nothing below may be changed once the run has happened. If the
answer is "no", that is the answer.

## The question

`_reset_new_team_dc_ratings` clears stale D-C parameters for clubs newly promoted or
relegated into the Championship. The old behaviour (`league_average`) sets their
attack/defence to exactly 1.0, which also throws away their current-season results.
The new behaviour (`shrunk_current_season`) refits on the current season alone and
shrinks toward average by n/(n+6).

Does the new behaviour predict better?

## Why not test it on 2026/27

Because it cannot be answered there. `dc_fit` needs 50 matches before it will fit, so
the new mode is inactive until 5 Sep 2026. That leaves **9 affected games this season**
(≈14 once GW7 lands) — far too few to separate a real gain from noise. GW7 is also the
round that prompted the change, so it is the worst possible place to judge it.

## Population

- Seasons scored: **2015/16 – 2024/25** (10 seasons). 2014/15 is burn-in for the fit.
- **2025/26 is the sealed vault and is excluded**, per the standing rule.
- Games scored: every fixture in which **at least one club is new to the division**
  that season (not present in the previous season's fixtures) — the only fixtures the
  reset can change. Expected ≈ 43% of each season.
- Walk-forward throughout: ratings are fitted only on matches played strictly before
  kickoff. No fixture contributes to its own prediction.

## What is being compared

The **spine only** — Dixon-Coles blended with Elo, exactly as `price_match` blends
them — with no tier adjustments.

This is deliberate, and it is a limitation worth stating: T5 needs injury lists and T6
needs referee profiles that do not exist for past seasons, so a full-tier historical
run is not possible. The reset changes D-C attack/defence, and the tiers are additive
nudges applied afterwards, so the spine is where the effect lives. A full-tier check on
GW7 is a separate sanity pass, not the verdict.

## The metric

**Surprise score:** for each game, how unlikely the model thought the result that
actually occurred. Lower is better. (Log loss, averaged per game.)

Scored separately on:
1. **1X2** — home / draw / away
2. **Over-under 2.5 goals**

**Both must improve.** If one improves and the other worsens, that is a mixed result
and the change is reworked, not kept.

## The decision rule — fixed now

The new mode is kept only if, on the fixtures defined above:

1. It improves the mean surprise score on **1X2**, AND
2. It improves the mean surprise score on **over-under 2.5**, AND
3. Each of those improvements holds in **at least 7 of the 10 seasons individually**.

Condition 3 is the one that matters. A pooled average can be carried by a single
season; a real effect shows up again and again. Anything short of all three is a fail.

## Scorer validation — run first, on known answers

The scoring code is tested against inputs whose answers are known before it is trusted
with the comparison:

- A model that calls every outcome equally likely **must score worse** than the real
  model.
- The bookmaker's **closing price**, de-vigged, **must score better** than the real model.
- A model given the actual result as a certainty must score near-perfect.

If the scorer cannot separate those, the scorer is broken and no result it produces
counts. Three of the ten entries in `handover/DATA_INTEGRITY_LESSONS.md` are cases where
the checking tool was the thing that was wrong.

## Reported but explicitly NOT part of the verdict

- Performance against opening and closing prices (EV, CLV, hit rate).

Whether the model beats the market is a different question from whether it predicts
better, and merging them is how a flattering number gets chosen. These are reported for
information only and cannot rescue a fail on the rule above.

## Not being tested here

The `min_matches` floor stays at its current value of 50 for this test. Relaxing it is a
separate change and gets its own run — changing two things at once and measuring the
pair leaves you unable to say which one worked.
