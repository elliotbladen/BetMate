# Result — Elo-seeded, level-neutral: FAIL

Run 2026-09-15 against the rule locked in `LEVEL_NEUTRAL_PREREGISTRATION.md` (commit
`4b8bd07`, written before the variant was run). Rule unchanged afterwards.

**Verdict: FAIL.** `new_team_reset` stays `league_average`. All three candidate modes
remain implemented and tested behind the config key; none is the default.

## The numbers

2,436 fixtures, 10 seasons, walk-forward, spine only, 2025/26 sealed. Surprise score,
lower is better. Baseline is `league_average`.

| | 1X2 | seasons better | O/U | seasons better |
|---|---|---|---|---|
| baseline | 1.0554 | — | 0.6908 | — |
| shrunk_current_season | 1.0501 (−0.0053) | 7/10 | 0.7082 (+0.0174) | 0/10 |
| elo_seeded | 1.0366 (−0.0188) | 10/10 | 0.7050 (+0.0142) | 2/10 |
| **elo_seeded_level_neutral** | **1.0372 (−0.0182)** | **10/10** | 0.6970 (+0.0063) | 4/10 |
| market (de-vigged close) | 1.0172 | — | — | — |

Against the locked rule: O/U not worse **FAIL** (+0.0063 vs a +0.002 tolerance); 1X2 not
worse PASS; at least one better PASS; no market worse in 8+ seasons PASS (O/U worse in 6).
One of four fails, and the pre-registration stated in advance that partial credit is not
a pass — naming **+0.007 instead of +0.014 as still a fail**. It landed on +0.0063.

## The correction worked mechanically and did not buy what was predicted

The scalar did what it was designed to do. Mean expected total:

| | mean lam+mu | shift vs baseline | fixtures pushed up |
|---|---|---|---|
| league_average | 2.6124 | — | — |
| shrunk_current_season | 2.7100 | +0.0976 | 51% |
| elo_seeded | 2.7315 | +0.1191 | 72% |
| level_neutral | 2.6329 | **+0.0205** | 39% |

**83% of the level shift was removed.** The 1X2 gain survived almost intact (−0.0188 →
−0.0182, still 10/10 seasons) — so the Elo ordering and the goal level really are
separable, which was the substantive claim.

But O/U only recovered **56%** of its damage (+0.0142 → +0.0063). Removing 83% of the
cause removed 56% of the effect. **The "defence divides" diagnosis is therefore
incomplete**: a material part of the O/U degradation is not the level shift at all, it is
the spread itself — giving new clubs dispersed ratings makes the totals distribution
worse even after the mean is put back.

Per the pre-registration this is recorded as a finding about the diagnosis and **not** as
a cue to build a fifth variant.

## The context that matters more than any of the above

Baseline O/U surprise is **0.6908**. A constant guess of the base rate — the same
probability on every fixture, no model at all — scores **0.6916**.

**The Championship totals model is worth 0.0008 over knowing nothing.** Every number in
the O/U column of this study is noise around a model that carries essentially no
fixture-specific information, which is consistent with the isotonic calibrator having six
distinct outputs and a hard ceiling, and with `project_championship_ou25_no_edge`.

No new-team reset mode can fix that: this study only touches the 246 fixtures a season
that involve a promoted club, about 10% of the fixture list. Making O/U 2.5 respectable
is a different job — it needs the calibrator rebuilt on an input that actually separates
fixtures, and the only untested input class left is real xG, which football-data does not
carry for the Championship before 2026/27.
