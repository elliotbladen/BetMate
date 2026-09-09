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


---

## RESOLVED, same day — root cause found and fixed

The wrong meetings were not an archive quirk. An older importer cached the ATC
report as `sectionals.pdf` from a URL with **no year in it**, so 2024-04-13
Randwick fetched *"13 April 2019 - Royal Randwick"*. 108 dates carried that file.
`download_atc_sectional_pdf` already builds a year-qualified URL
(`/{year}/{DDMM}{RAND|RHIL}.pdf`) and caches under `atc-sectionals.pdf`, so the
code was correct — the stale data had simply never been re-imported.

`scripts/reimport_nsw_clocks.py` deletes the legacy rows for a date and
re-imports it. **111/111 meetings, no failures.**

| | before | after |
|---|---:|---:|
| NSW clock coverage (source) | 23.3% | **96.0%** |
| NSW in the clean layer | — | **94.6%** |
| state gap vs VIC | 42.8pp | **5.1pp** |
| wrong-meeting races | 437 | **0** |
| clocks needing donation | 926 | **0** |
| coverage gate | FAIL | **PASS** |

Clocks are now native on the result row, so the donation path is no longer used
at all. Pride Of Jenni's 2024 Queen Elizabeth is back at 2000m and returns to 2nd
all-time (124.5).

**Remaining 76 races, documented not hidden:**
- **19 unrecoverable.** Four Feb–Mar 2025 meetings time a 1500m race only from
  the 1400m marker; there is no "Official" line and the largest clock in the
  document is the 1400m cumulative. Estimating the opening section would be
  inventing data.
- **57 with no clock at source** — genuine ATC 404s (2025-08-09 and 2024-06-22
  Randwick both return HTTP 404) plus partial-meeting parse gaps. A second pass
  re-imported 19 meetings and recovered none.

**96.0% is the ceiling with the current parser; ~98.7% is the theoretical
maximum.** Passing that needs parser work on the partial-meeting layout, not more
importing.

### Bug found in the seed tooling while closing out

`racing_seed_status.py` reported LOCAL IS BEHIND after the cleanup, because it
treated a smaller row count as staleness — but the purge legitimately removed 978
wrong-meeting rows while the local data was a week newer. Recency now decides;
row count only breaks a tie when both sides hold the same latest race date.
Left unfixed, it would have told the next session to restore over its own fix.

---

## racing.racingnsw.com.au investigated as a gap-filler — it cannot help

Checked at the user's request whether Racing NSW's own site could supply the 76
races the ATC feed cannot.

**Two endpoints exist and both work — but only for recent meetings.**

| Endpoint | Carries a race clock? | Retention |
|---|---|---|
| `/FreeFields/CSV.aspx?Key=…&stage=Results` | **No** — 33 columns, none is a race time. `seconds(row[16])` in `rnsw.py` refers to an older CSV layout that no longer exists. | recent only |
| `/FreeFields/Results.aspx?Key=…` | **Yes** — 20 clocks per meeting | **~3 months** |

Retention boundary probed directly (`Results.aspx`, Royal Randwick):

| date | page | clocks |
|---|---:|---:|
| 2026-09-05 | 239 KB | 20 |
| 2026-08-22 | 244 KB | 20 |
| 2026-06-20 | 277 KB | 20 |
| 2026-03-14 | 32 KB | **0** |
| 2025-11-29 | 32 KB | **0** |
| 2024-06-22 | 32 KB | **0** |

A 32 KB response is the "not found" page. Anything older than roughly three
months is simply not served.

**Every one of our 76 missing races is older than the retention window** — the
newest is 2026-03-28. Query confirming it returns nothing:

```sql
SELECT race_date, track_slug, COUNT(*) FROM race_results
WHERE source='racing-com-nsw-authorised-v2' AND official_time_seconds IS NULL
  AND race_date >= '2026-06-01' GROUP BY 1,2;   -- empty
```

So Racing NSW cannot close the gap. **96.0% stands as the ceiling** from
available sources.

**Worth wiring up anyway, for the future:** `Results.aspx` is a live second
source for the current window. Fetching it weekly alongside the ATC PDF would
mean a meeting whose PDF 404s or parses short is caught while it is still
retained, instead of becoming a permanent hole three months later. That is how
the 76 became permanent — nothing was watching at the time.
