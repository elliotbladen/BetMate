# 2026-09-10 (PM/2) — Championship O/U 2.5: the last two questions, answered

**Branch:** `research/efl-totals-vault-test`
**Outcome: both null. The Championship totals question is closed, not parked.**

## What this session was

The previous session ended by spending the sealed 2025/26 vault on a market-anchored
rule that failed on ROI (−5.79%) and closing that line of work. Two things were left
explicitly undone in `TOTALS_SIGNAL_PROBE.md`:

1. its own closing caveat — *"a tree ensemble might extract interaction effects …
   worth one attempt before closing the question for good"*
2. the "routes back in" list — real xG, confirmed lineups, weather

Both are now settled, and neither reopens the market-anchored line (the vault was not
touched; `load()` drops 2025/26 before anything else runs).

## 1. Trees find nothing — `ml/football/backtest/efl_totals_tree_probe.py`

The design point that makes this a fair test: the de-vigged close enters as an XGBoost
**`base_margin`**, so the trees can only learn residual structure. A tree handed the
market as an ordinary feature has to rediscover it and would look bad for reasons that
have nothing to do with the hypothesis. Rounds come from early stopping on the last
*training* season; one conservative hyper-parameter set, no grid; two pre-specified
feature sets (7 symmetric aggregates, and all 21 raw per-team stats — symmetric sums
being exactly what would destroy an interaction).

```
market-only          0.68194   <- baseline
market+treeA (agg)   0.68167   +0.00027   1/4 seasons   CI [-0.0027, +0.0033]
market+treeB (raw)   0.68119   +0.00075   2/4 seasons   CI [-0.0011, +0.0026]
trees only, no mkt   0.69214   -0.01020   (worse)
closing line         0.68121   <- treeB lands on it to 5 decimal places
```

The best tree configuration reproduces the closing line to within 0.00002. That is what
"a tidier copy of the market" looks like measured. Early stopping picked 4–37 rounds in
three of four seasons — given the market, the trees declined to move.

**Self-tests** (`--selftest`), because a null is what a broken harness produces:
0 boosting rounds reproduce the market to 5.7e-08 (proving the base margin is wired up —
otherwise every gain above is measured off the wrong base), and a planted realised total
collapses log-loss to 0.0189.

## 2. Confirmed lineups are already priced — `efl_totals_lineup_probe.py`

ESPN confirmed XIs for 2023/24 + 2024/25 (851 matches joined; the vault's 525 starter
matches deliberately not loaded). Features = what tonight's XI actually did in that
team's prior 10 matches: per-90 shots/SOT/goals summed over the eleven, plus
minutes-share continuity.

Two things reframe this test and both cut against it: the XI is known ~1h pre-kickoff,
so the honest benchmark is the **close**, not the open this account bets into; and with
the vault spent there is no sealed season left, so the primary test is a **powered
correlation over all 851 matches** rather than an under-powered one-season walk-forward.

| feature | r vs over25 | r vs **market residual** | p |
|---|---:|---:|---:|
| xi_shots90_sum | +0.056 | **+0.0004** | .992 |
| xi_sot90_sum | +0.062 | +0.021 | .550 |
| xi_minshare_sum | +0.024 | +0.036 | .294 |

n=851 detects |r| ≥ 0.096 at 80% power. The XI carries the same weak information about
scoring as the features already tested — and none of it against the market residual.
Walk-forward confirms: market-only .68717 → market+XI .69465, worse.

Join integrity checked: all 24 team names map cleanly in both directions, the 958→851
loss is the per-team 5-match burn-in, and planting the realised total against the
residual returns r=+0.79.

## 3. The xG route is blocked for far longer than the parked plan assumed

The parked decision said "re-run with real xG in ~a month". Verified directly against
football-data headers: **HxG/AxG exist in 2026/27 only** — absent in E0 and E1 for
2022/23 through 2025/26. Local coverage is Championship 60/69, EPL 30/30, zero before.
At 552 matches a season, a usable Championship sample arrives around **May 2027**.

Alternatives were checked rather than assumed:

* **Understat is more dead than recorded.** League pages return 200 with the right title
  but no embedded data payload at all — 18KB, adsense blob only, no `datesData` — and
  that is true for *historical* seasons too. This also kills it as the fix for the EPL
  scale break, which the 2026-09-10 AM session had listed as the top football priority.
* **FBref/StatsBomb** returns 403 to a plain client. Plausible, unverified, and a
  source-evaluation job rather than a probe re-run.

## Where the question stands

Three independent classes of input have now been tested and all three are already in the
price: the raw stats linearly, the same stats with interactions, and confirmed lineups.
Only weather is untested, and it needs a historical backfill that does not exist.

**Do not price Championship O/U 2.5 as a bettable market, and do not spend more time
modelling it.** The one piece of work that would change anything is acquiring real xG
from a source that is not football-data — and that is worth doing on its own merits,
because it also unblocks the EPL totals scale break, which is a live model fault rather
than a speculative edge.

## Files

| Path | What |
|---|---|
| `ml/football/backtest/efl_totals_tree_probe.py` | tree probe + `--selftest` |
| `ml/football/backtest/efl_totals_lineup_probe.py` | lineup probe |
| `outputs/football/championship/_research/TOTALS_SIGNAL_PROBE.md` | Addendum 2 — full results |
| `outputs/football/championship/_research/totals_tree_probe.csv` | per-season tree results |
| `outputs/football/championship/_research/totals_lineup_probe.csv` | 851 joined matches + features |

No engine code modified; no production model, calibrator or pricing output touched.
