# ⚠ RNSW importer fetches the WRONG MEETING for 43% of dates

Date: 9 September 2026 · **This supersedes the distance-donation claims made
earlier the same day.**

## What was found

Chasing why Pride Of Jenni's 2024 Queen Elizabeth was recorded at 3200m led to a
much larger problem. Comparing runner identity between the two NSW sources for
every race they share:

| | races |
|---|---:|
| runner sets MATCH (≥80% overlap) | 557 |
| partial (20–80%) | 12 |
| **MISMATCH (≤20%) — wrong meeting** | **437** |

`rnsw-authorised` rows for 2024-04-13 Randwick contain **WINX, HARTNELL and
HAPPY CLAPPER**. That is the **2018** Queen Elizabeth, not the 2024 card. The
same shape appears on 2023-09-02 Randwick R5, where RNSW has Redzel/Spieth/Nieta
and racing-com has an entirely different field.

The RNSW importer is resolving some dates to an archived PDF from another year.

## What this invalidates

Two claims made earlier today were wrong, and both are now corrected in code:

1. **"racing-com has wrong distances on 362 NSW races."** It does not. All 362
   "distance disagreements" were RNSW rows describing a *different meeting*. With
   identity verification on, `distances_corrected_from_rnsw` is **0**.
2. **"926 NSW clocks recovered."** Only **487** are real. The other 439 were
   clocks from other meetings, which is worse than no clock — it silently
   attaches another race's facts to this one.

The Redzel example used to justify the distance fix was itself a wrong-meeting
row. The evidence looked strong (RNSW distance consistent with RNSW clock in
362/362 cases) precisely because both fields came from the same wrong race.

## The fix

`v2_ratings.py` now verifies runner identity before any donation:
`DONOR_IDENTITY_OVERLAP = 0.80` of the smaller runner set must match. Donation is
skipped otherwise, and the rebuild reports
`donor_races_identity_verified` / `donor_races_rejected_wrong_meeting`.

## Where coverage actually stands

| | NSW | VIC |
|---|---:|---:|
| clock coverage | **57.0%** | 99.8% |
| gap | **42.8pp** (tolerance 15pp) | |

`check_state_clock_coverage.py` **FAILS** — correctly. The earlier 87.9% PASS was
built on wrong-meeting data.

`form-first-v2.0` on verified data: concordance 0.5526, repeatability 0.646,
0.164 points per length, scale 49.0–103.1. Essentially unchanged, which is
expected — v2 uses no clock and the identity fix removed bad *race* facts, not
runner facts.

## Next

1. **Fix the RNSW date→PDF resolution.** Until then the archive cannot be trusted
   for any date whose runner set does not match. That is the real blocker on NSW
   clock coverage, not missing meetings.
2. The 34-meeting backfill run earlier is fine — those imports used
   `import_structured_result` (racing-com) for results, and identity verification
   now protects anything downstream.
3. Re-run coverage after the parser fix; only then consider a cross-state
   leaderboard.

**Lesson worth keeping:** two fields agreeing with each other is not evidence
they are correct. The distance and clock agreed 362/362 because they came from
the same wrong race. Identity — *who actually ran* — was the only check that
could catch it.
