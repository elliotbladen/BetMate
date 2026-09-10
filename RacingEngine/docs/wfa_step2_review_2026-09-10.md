# Step 2: WFA profile and component review

The owner rejected the step-1 race-strength figures for Lindermann and Ceolwulf.
PR #5 is closed and unmerged. This branch starts from main and does not contain
or consume that candidate. This review investigates WFA data and weight
components without changing horse ratings.

## What was wrong

The corrected Sydney result source has no links to the old derived-profile
table. That explains much of the reported 39% WFA coverage: age and sex actually
exist inside the archived Racing.com runner records.

Those embedded profiles have **current age at fetch time**, not historical
race-day age. For example, Lindermann's 2023 records contain age seven after
being fetched in 2026. The existing ingestion code uses the race date as the
age observation date and labels every source Victorian. The review bypasses
that path; it does not rebuild or overwrite those legacy observations.

## Implemented review path

`wfa_profile_review` matches the clean race and runner to the exact raw source
record, checks its embedded provider ID and cleaned horse name, and reconstructs
racing age across Australian August season boundaries. It uses the import
timestamp in Australia/Sydney as a fetch-date proxy. Unknown or timezone-less
timestamps are not replaced with race dates.

Same-ID observations can supply missing profile facts; conflicting inferred
age seasons, names or male/female groups are rejected. Current gelding status
is not projected backwards: only the male/female group needed for the base
reference is used. Existing linked birth dates provide a separate check;
a disagreement blocks the reconstructed reference.

The output includes base WFA weight, carried weight, their difference and
standalone component scenarios at 0.5, 0.65 and 0.9 points/kg. These coefficients
are **unfitted, uncapped sensitivity examples**, not selected rating settings.
No component is added to an existing figure, which could double-count its
existing weight adjustment. There is no new race-strength calculation.

Every row is labelled retrospective and `pit_eligible=false`, including missing
rows. The observation date is not proof of historical availability. The CLI
opens the source read-only and requires a new output file, preserving previous
reviews. Separate race and observation cutoffs are mandatory.

## Official table correction

AR168 gives the five-plus reference as **59kg for over 1600m through 2400m**.
The code incorrectly used 59.5kg in both distance bands. It now uses 59kg;
the over-2400m band remains 59.5kg. Female references in the affected bands
therefore become 57kg after the existing allowance.

Verified against page 87 of the [official June 2026 rules](https://www.racingaustralia.horse/uploadimg/Australian_rules_of_Racing/Australian_Rules_of_Racing_01_June_2026.pdf)
and page 83 of the [June 2023 rules](https://www.racingaustralia.horse/uploadimg/Australian_rules_of_Racing/Australian_Rules_of_Racing_01_Jun_2023.pdf).
The correction is labelled `ar168-170-2026-06-01-transcription-v2`; tests cover
all months, both affected band boundaries, mature males/females and the
unchanged 2401m boundary. This shared helper correction would affect future
rebuilds after approval; it has not been applied to a production database.

## Local results

Exclusive race cutoff: 2026-09-06. Observation cutoff: through 2026-09-10.
The denominator is identical for both coverage columns: finished clean-layer
runs, not an external meeting calendar or a different model's run population.

| State | Finished runs | Old linked base references | Reconstructed base references |
|---|---:|---:|---:|
| NSW | 15,275 | 0 | 15,038 |
| VIC | 14,266 | 11,522 | 14,006 |
| Total | 29,541 | 11,522 (39.0%) | 29,044 (98.3%) |

Birth-date comparisons: 11,546 rows checked, with one disagreement (Lake Forest,
8 November 2025). That row stays unresolved. This cross-check is available only
for linked Victorian rows; it is not independent confirmation of every Sydney
profile. Across the finished population, 28,209 reconstructed race-day ages
differ from the embedded current ages.

The 497 missing references are explicit:

- 360 two-year-old runs outside populated schedule cells;
- 113 missing age or sex;
- 23 identities not verified;
- one birth-date age disagreement.

Northern-hemisphere AR170 eligibility has **not** been established from these
profiles. Horse country or sire-country labels alone do not prove eligibility.
The 98.3% figure is base-reference coverage, not complete AR170-adjusted WFA
coverage, and not point-in-time coverage.

## What the components do

September 5, 2026 examples:

| Horse | Reconstructed age | Carried kg | Base WFA kg | Difference kg | Component at 0.65 points/kg |
|---|---:|---:|---:|---:|---:|
| Lindermann | 7 | 59 | 59 | 0 | 0 |
| Ceolwulf | 6 | 59 | 59 | 0 | 0 |
| Tempted | 4 | 58 | 56.5 | +1.5 | +0.975 |

**WFA alone cannot repair the rejected low race levels for Lindermann and
Ceolwulf:** both carried their base reference weight on that day. Tempted's
component spans +0.75 to +1.35 across the three illustrative coefficients.

The age correction matters much more in young-horse history. Tempted's
1 February 2025 run reconstructs to age two, not the fetched age four. The
base reference is 44kg versus 54.5kg carried: an uncapped +6.825-point component
at 0.65. That is not automatically a next-start uplift. The existing young-horse
promotion policy and its achieved-merit/current-ability distinction still apply.

## Verification and reproduction

**26 tests passed:** ten new profile-review tests, six WFA schedule tests,
three horse-profile tests, two Breednet tests, two Dan-calibration tests and
three achieved-young-WFA tests. The profile-review fixture is synthetic.

Checks cover identity mismatch, unsupported sources, fetch-date age projection,
August/timezone boundaries, missing timestamps and sex, conflicting profiles,
birth-date disagreements, unavailable schedule cells, component-only output,
read-only source bytes, separate cutoffs and refusal to overwrite output.
No UI changes were made.

From `RacingEngine/`:

```sh
python3 -m unittest discover -s tests -p 'test_wfa*.py'
python3 -m racing_engine.wfa_profile_review \
  --database /path/to/source.sqlite \
  --output /path/to/new-review.sqlite \
  --as-of 2026-09-06 \
  --observed-through 2026-09-10
```

The committed JSON report contains the input digest, coverage, exceptions and
example components. No ratings were rebuilt; no wind adjustment was added;
no model was promoted. Review the data correction and reference method before
choosing any rating conversion coefficient or integrating this with a model.
