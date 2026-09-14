# Result — new-team reset fix: REWORK

Run 2026-09-14 against the rule fixed in `RESET_FIX_PREREGISTRATION.md` (committed
`6761e90`, before the harness existed). The rule was not changed after seeing this.

**Verdict: FAIL. The change is not shipped.** `new_team_reset` is back to
`league_average` in `championship.yaml`. The shrunk mode stays in the code, tested and
available behind the config key, as a candidate for rework — not as the default.

## The numbers

2,436 fixtures, 10 seasons (2015/16–2024/25), walk-forward, spine only, 2025/26 sealed.
Surprise score — lower is better.

| | old | new | |
|---|---|---|---|
| 1X2 pooled | 1.0554 | **1.0501** | better |
| O/U pooled | 0.6908 | **0.7082** | worse |
| seasons won, 1X2 | | 7 / 10 | scrapes the threshold |
| seasons won, O/U | | **0 / 10** | unanimous |

Market reference (de-vigged closing, Pinnacle where available): **1.0172** on 1X2 —
better than either model variant, as it should be. That is the third scorer validation
from the pre-registration, and it passed.

Decision rule: 1X2 pooled PASS, O/U pooled FAIL, ≥7 of 10 on both FAIL. Two of three
fail. Rework.

## What actually happened — and the lesson in it

The change did exactly what it was designed to do. It nearly doubled the spread of the
model's total-goals expectation (sd **0.304 → 0.568**). Compression was the disease this
was meant to treat, and it treated it.

**The totals still got worse, in all ten seasons.** Splitting the breakdown by outcome
shows why:

| | surprise when it went OVER | when it went UNDER |
|---|---|---|
| old | 0.7284 | 0.6571 |
| new | 0.7076 | 0.7087 |

The old model leans UNDER — it is good at unders and poor at overs. The new mode
genuinely fixed that lean (overs improved 0.7284 → 0.7076) and then overshot, wrecking
the unders (0.6571 → 0.7087). Unders are 53% of these fixtures, so the damage outweighs
the gain.

**The lesson: more spread is not automatically better.** The extra movement has to track
reality. Here the current-season fit moved the totals estimate around more than the
underlying truth supported — it added variance without adding accuracy. Any future
attempt at the compression problem has to be judged on accuracy, not on whether the
output stops looking flat. Looking less flat was never the goal; it was a symptom we
were using as a proxy, and this run shows the proxy can move on its own.

On 1X2 the effect is coherent: home **0.8364 → 0.8224** and away **1.1840 → 1.1466**
both improve, while draws **1.2823 → 1.3268** get worse. Pushing ratings apart makes
draws less likely, so a draw becomes more of a surprise. That is a real trade, not noise,
and it is why the 1X2 gain is thin.

## For the rework

Not attempted here, and each needs its own pre-registered run:

- Shrink harder. `n/(n+6)` gives a club 50% weight at six games, which this suggests is
  too much. A heavier prior would move less — but tuning that constant on this same data
  is the trap the pre-registration exists to stop, so it needs fresh terms.
- Split the path: current-season ratings into 1X2, league average into totals. Motivated
  by the result rather than by theory, so treat it as a hypothesis needing its own test.
- Set the new clubs' starting point from Elo rather than a D-C refit — Elo is a single
  number per club and cannot push attack and defence in contradictory directions.
- Or leave the reset alone entirely. The 1X2 gain here is 0.5%, at exactly the minimum
  passing season count. Even the version that "won" won barely.

The `min_matches` floor was deliberately left at 50 for this run and remains untested.
