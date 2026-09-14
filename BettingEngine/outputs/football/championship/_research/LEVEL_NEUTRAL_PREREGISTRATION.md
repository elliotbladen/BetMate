# Pre-registration — Elo-seeded, level-neutral (candidate 3)

**Written 2026-09-14, BEFORE the variant was run.** Rule not to be edited afterwards.

## The candidate

`mode="elo_seeded_level_neutral"`. Identical to `elo_seeded` — which improved 1X2 by
−0.0188 in **10 of 10 seasons** — with one addition: every new club's defence is scaled
by a single scalar `c`, chosen so the mean expected total across all new-club-versus-
established-club pairings equals what the flat `league_average` baseline produces.

`c` is computed per matchday in closed form from the league's actual ratings. Ratios
between the new clubs are untouched, so the 1X2 ordering that produced the 10/10 result
is preserved exactly; only the goal level moves.

## Why this and not something else

Both previous candidates failed on totals, both in the same direction (+0.098 and +0.119
goals). That is the model's algebra, not the method: `lam = base x att / def_away` means
defence divides, so spreading defence away from 1.0 raises average goals even when the
spread is symmetric. `att = def = 1.0` is the unique level-neutral pair, which is exactly
what the flat baseline sets.

This candidate keeps the part that demonstrably works (Elo ordering) and removes the
one mechanism breaking totals. It is a correction to a known mathematical artefact, not
a search for a setting that scores well.

Recorded because it is the kind of thing that gets quietly forgotten: my first
derivation assumed a notional average opponent and produced `c = 0.996`, a no-op. It was
wrong — the shift comes from the real spread of opposition. The version being tested
averages over the league's actual established ratings.

## The rule — fixed now, unchanged from candidate 2

Baseline `league_average`: pooled 1X2 **1.0554**, pooled O/U **0.6908**. Lower is better.
"Not worse" means within **+0.002**.

Keep it only if ALL of:

1. **O/U not worse**: `d_ou <= +0.002`
2. **1X2 not worse**: `d_1x2 <= +0.002`
3. **At least one genuinely better**: `d_1x2 <= -0.002` OR `d_ou <= -0.002`
4. **No lopsided degradation**: neither market worse in 8 or more of the 10 seasons

## Stated in advance, so it cannot be claimed afterwards

The expected outcome is 1X2 ≈ −0.019 (inherited from `elo_seeded`) and O/U ≈ 0.000
(the level shift removed). **If O/U does not come back to roughly baseline, the
"defence divides" explanation is wrong or incomplete**, and that is a finding about the
diagnosis, not a reason to try another correction. Say so rather than reaching for a
fourth variant.

Partial credit is not a pass. O/U landing at +0.007 instead of +0.014 is still a fail.

## Unchanged

Walk-forward, spine only, no tiers, 2,436 fixtures, 10 seasons, 2025/26 sealed. Market
reference de-vigged closing, Pinnacle first. Scorer re-validated on known answers at the
start of every run. `min_matches` stays 50 and remains untested.
