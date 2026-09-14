# 2026-09-15 — Championship new-team reset: three candidates, three failures, closed

Branch `fix/championship-ratings-and-feed-audit`, merged to main. Covers the unfinished
14 Sep evening session (which left no diary) and today's completion of it.

## What was asked

Finish two things left hanging: the goals/results download, and the level-neutral
backtest — the owner wanting to know whether O/U 2.5 had become usable.

**Answer: no. Championship O/U 2.5 is not to be bet. Owner accepted and confirmed.**

## The download

`fetch_results.py --league championship --live-merge` ran clean, but football-data.co.uk
**still has not published the 11-13 Sep round**. Verified by fetching the raw E1 file
directly: 69 rows, ending 09/09/2026. Not a fetcher fault.

What it did achieve: the 9 ESPN-supplemented GW6 rows were replaced by official ones
(`SourceSupp=espn` 9 -> 0), and all 69 current-season rows now carry `HxG`/`AxG`.

GW7 came from `ingest_espn_results_supplement.py` instead — all 12 fixtures, with refs
and cards. 6,693 -> 6,705 rows. `--live-merge` de-dupes keep="last" so official rows will
replace these automatically when they appear.

⚠️ Note for whoever re-runs it: the raw CSV now sits behind a **302 from the www vhost**;
`curl` needs `-L` (the fetcher already tries both hosts and handles it).

## GW7 graded — 1W-6L, -5.20u, ROI -69.3%

`gw07/4_review_bets.csv`. West Ham 6-0 Wrexham took down the 1X2, the draw AND the Under
off one scoreline; Middlesbrough 4-3 Norwich buried a third Under.

⚠️ **Read this correctly.** These were not games the engine declined to price — they are
the EV screen's own qualifiers at +16.4% to +69.6%. Left to the >=10% EV entry rule the
engine backs all seven and loses 5.20u. What said "no bet" was the review layer, for
documented reasons (calibrator plateau, promoted-club rating lag). **The model was wrong
on all seven and the write-up caught it.** The one winner came off the flat 0.4495
plateau, so on merit it is 0/7. Season: **1W-14L**.

CLV is NaN throughout — 2026/27 has no Pinnacle closing totals odds yet.

## The level-neutral test — FAIL

Run against the rule locked in `LEVEL_NEUTRAL_PREREGISTRATION.md` before the variant was
written. 2,436 fixtures, 10 seasons, walk-forward, spine only, 2025/26 sealed.

| | 1X2 | seasons | O/U | seasons |
|---|---|---|---|---|
| baseline `league_average` | 1.0554 | — | 0.6908 | — |
| `shrunk_current_season` | 1.0501 (-0.0053) | 7/10 | 0.7082 (+0.0174) | 0/10 |
| `elo_seeded` | 1.0366 (-0.0188) | 10/10 | 0.7050 (+0.0142) | 2/10 |
| `elo_seeded_level_neutral` | 1.0372 (-0.0182) | 10/10 | 0.6970 (+0.0063) | 4/10 |
| market (de-vigged close) | 1.0172 | — | — | — |

O/U needed to be within +0.002. It landed at **+0.0063** — and the pre-registration had
named **+0.007 in advance as still a fail**. Fail, not a near miss.

**The mechanism worked; the prediction did not.** The scalar removed **83%** of the level
shift (mean expected total +0.1191 -> +0.0205) and the 1X2 gain survived at -0.0182. But
O/U recovered only **56%** of its damage. Removing 83% of the cause removed 56% of the
effect, so **"defence divides" is incomplete** — part of the harm is the spread itself,
not the level. Per the pre-registration this is logged as a finding about the diagnosis.
**No fifth variant was built.**

## The finding that actually settles O/U 2.5

Baseline O/U surprise **0.6908**; a constant guess at the base rate scores **0.6916**.

Checked against the full league rather than the promoted-club subset, using the earlier
probe's four test seasons (n=2,153):

```
production D-C totals    0.69263
constant base-rate guess 0.69107   <- model WORSE by 0.00155
closing line             0.68121   <- model worse by 0.01142
```

Beats the constant in 3 of 4 seasons, but 2021/22 (.7090 vs .6909) wipes that out.
**Pooled, the Championship totals model loses to a constant.** Two independent
measurements agree. It is seven times further from the close than from the constant.

Tiers and matrix do not rescue it: the goals matrix was tested and is noise (1,309 cells,
69 hits at p<0.05 vs ~65 by chance = **1.05x**, zero survive BH at q=0.10), matrix
confluence double-counts (GW7's Sheffield United "+7" was one fact counted seven times),
and the live record is GW5 5/12 at -2.04% CLV plus GW7's 1-3.

## SIGNED OFF AND SHIPPED — the per-market split is now production

Owner signed off `elo_seeded` for Championship **1X2** on 2026-09-15 and asked for it in
production. Implemented as a **per-market split**, not a wholesale flip.

**Why a split and not `new_team_reset: elo_seeded`.** That key sets the D-C ratings
feeding BOTH markets, so flipping it would have taken 1X2 to 1.0366 (good) and dragged
O/U to 0.7050 (worse in 8/10 seasons). Totals are not bet, so that was survivable — but
it was avoidable.

**The mechanism.** `new_team_reset` now governs totals + Asian handicap;
`new_team_reset_1x2` governs 1X2 and **defaults to `new_team_reset`**, so every other
league — EPL included, checked — behaves exactly as before and the unsplit code path is
the one that has always run.

```yaml
new_team_reset:     league_average   # totals + AH
new_team_reset_1x2: elo_seeded       # 1X2 only
```

**The composition was verified, not assumed.** `scripts/verify_new_team_reset_split.py`
prices real fixtures three ways and asserts the split's 1X2 equals a whole-model
`elo_seeded` run and its totals equal a whole-model `league_average` run, to 1e-9:

```
West Ham v Wrexham   p_home  avg 0.4188  elo 0.4766  split 0.4766   1X2 == elo_seeded
                     p_over  avg 0.4495  elo 0.4756  split 0.4495   totals == league_average
```

The arms genuinely differ, so this is not a vacuous pass. **That is what lets the measured
backtest numbers be claimed for this configuration without re-running the 10-season
walk-forward:** 1X2 **1.0366, better in 10 of 10 seasons**; O/U **0.6908, unchanged**.

The script exits non-zero on mismatch, so it gates future changes to `price_match`.

⚠️ **Sober caveat, unchanged by the sign-off: even at 1.0366 this is well short of the
market's 1.0172. It is a better MODEL, not an edge. Do not bet Championship 1X2 off it.**
The yaml comment says so at the config line.

pytest **250 passed / 3 failed** (the pre-existing pyarrow failures).

## State

- `new_team_reset` stays **`league_average`**. All three modes remain implemented behind
  the config key; the yaml now carries all three failures with their numbers and the
  shared cause, so none can be switched on without meeting the evidence.
- pytest **247 passed / 3 failed** — the documented pre-existing pyarrow failures.
- Timestamped matches backups now gitignored.

## Next

1. **Do not price or bet Championship O/U 2.5.** Third independent line of evidence.
2. Pre-register and run the per-market split for `elo_seeded`.
3. **Cards is where the measured football edge is** (referee cards persist r=+0.42
   p=0.0001; goals r=+0.08, CI straddles zero) and the EPL prices it at Pinnacle, so real
   EV/CLV is obtainable instead of a break-even proxy.
4. ⚠️ **Two real staked cards bets are settleable and were deliberately left alone** —
   Preston v Lincoln O3.5 and Charlton v Portsmouth U3.5 now have HY/AY from the GW7
   supplement. Settling writes to the money ledger; owner's call.
5. ClubElo feed (`ml/football/data/championship/clubelo/`) still does not exist, so T8
   falls back to the hardcoded `new_team_elo_priors` guess. `check_football_feeds.py`
   reports it.
6. football-data still owes 11-13 Sep — re-run `--live-merge` to swap the ESPN rows out.
