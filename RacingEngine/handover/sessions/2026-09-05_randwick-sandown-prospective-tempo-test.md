# Randwick and Sandown prospective tempo test

Date: 5 September 2026  
Timezone: Australia/Brisbane  
Status: live shadow collection running locally

## Purpose

Preserve a genuine pre-race Expected Tempo forecast for every race at Royal
Randwick and Sportsbet Sandown Hillside, then collect the official sectional
evidence as it becomes available. This is off-season evaluation data. It must
not alter horse ratings, prices, bets or staking during the meeting.

## Frozen pre-race capture

The first append-only snapshot was captured at `2026-09-05T01:42:39.108398Z`
(11:42:39 AEST), before Randwick Race 1 at 11:50 and Sandown Race 1 at 12:10.

| Meeting | Race 1 context | Even | Fast | Slow | Very fast/collapse | V0 call |
|---|---|---:|---:|---:|---:|---|
| Royal Randwick | 1400m, Good, 9 runners | 26.19% | 9.13% | 43.45% | 21.24% | Slow |
| Sandown Hillside | 1500m, Soft, 6 runners | 35.61% | 11.49% | 36.38% | 16.52% | Slow/even |

Official card inputs at capture time:

- Randwick: Good going bucket; rail +3m entire course; 10 races.
- Sandown Hillside: Soft going bucket; rail true; 10 races.
- Model bundle: `expected-tempo-cloud-bundle-v1`.
- Policy: `expected-tempo-shadow-policy-v1`.
- Horse-price integration: `false`.

The full V0 probability vector and phase scores for all 20 races are preserved
inside the first ledger record. Later records may update shadow middle/late
scores from prior completed races, but cannot replace the original forecast.

## Live collection

- Local monitor process started at approximately 11:43 AEST.
- Poll interval: 75 seconds.
- Maximum polls: 360, covering the meetings and post-race publication window.
- Venues: `randwick,sportsbet-sandown-hillside` only.
- Output is append-only JSONL plus a replaceable latest-state convenience file.
- Official NSW source: ATC Swiss Timing meeting PDF.
- Official Victorian source: Racing.com/Racing Victoria runner timing.
- A result is accepted only with at least three sectional runners and at least
  60% sectional coverage.
- Evidence from a different going bucket receives zero live weight.
- Only capped middle/late shadow scores update; early scores and probabilities
  remain at V0 under the current amber policy.

Files:

- `reports/expected_tempo/live/2026-09-05_randwick_sandown.jsonl`
- `reports/expected_tempo/live/2026-09-05_randwick_sandown_latest.json`
- `../logs/tempo_live/2026-09-05.out.log`
- `../logs/tempo_live/2026-09-05.err.log`

## Readiness fixes made during launch

- Added `tzdata==2026.2` to `cloud/requirements-tempo.txt` for Windows and
  reproducible cloud timezone support.
- Changed a pre-race ATC PDF HTTP 404 to mean `not published yet`, returning no
  observations instead of failing the Randwick meeting.
- Added dry-run race, observation and snapshot payloads so prospective evidence
  can be preserved and audited locally.
- Added `cloud/tempo_live_test.py`, a bounded local polling and append-only
  capture runner.

The two-meeting dry run completed successfully with 20 V0 snapshots and no
errors. Both Python files passed `py_compile`. The dedicated virtual environment
does not currently contain pytest, so the existing pytest suite was not rerun
during the time-critical pre-race launch.

## Off-season evaluation

After the meeting, join each frozen V0 forecast and each live version to the
official realised tempo label and phase scores. Report multiclass log loss,
Brier score, top-label accuracy, calibration by probability band, and changes
from V0 to V1...Vn separately for Randwick and Sandown. Keep this two-meeting
sample prospective and untouched; it is evidence, not a fitting set.

