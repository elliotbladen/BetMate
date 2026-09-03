# V2.10 young-horse/WFA shadow findings — 1 September 2026

## Decision

**Keep as a research shadow. Do not replace `form-first-v2.0`.**

The candidate fixes the identified achieved-run scale compression and rerates
Guest House at **104.30**, supported by both contextual time and sectionals. Its
historical validation also confirms that achieved performance and forecast
ability must remain separate products.

## Guest House

- Accepted achieved run: 98.4626
- V2.10 race strength: 100.7609
- Observed 1.25-length margin component: +3.5417
- Contextual time signal: +0.9583 MAD, confidence 0.895
- Sectional achievement signal: +1.7835, confidence 0.95
- Evidence-retained margin fraction: 100%
- V2.10 achieved run: **104.3026**

The individual dated age/sex profile is missing for this NSW row, so no
individual WFA calculation was invented. The race description unambiguously
identifies a three-year-old-only event. Set-weight allowances are treated as
neutral rather than added as merit.

## Scale compression

For Listed and Group winners, mean rating minus the generic class standard:

| Cohort | Accepted | V2.10 |
|---|---:|---:|
| 2YO only | -20.28 | -5.37 |
| 3YO only | -21.28 | -8.42 |
| Open age | -3.45 | -2.36 |

V2.10 materially reduces young-race compression without materially moving
open-age Group/Listed winners. It does not force every age-restricted race to
the generic class standard; opposition reliability still controls the blend.

## Point-in-time validation

Shrinkage was selected only on races before 1 January 2025 and evaluated on
2025 onward. The target was the horse's next accepted performance rating.

| Cohort | Sample | Base MAE | Full achieved-run MAE | Pre-2025-selected carry | Shrunk MAE |
|---|---:|---:|---:|---:|---:|
| 2YO Group/Listed | 67 | 11.71 | 19.43 | 0% | 11.71 |
| 3YO Group/Listed | 108 | 8.36 | 10.16 | **15%** | **7.68** |
| Open Group/Listed | 237 | 6.39 | 6.75 | 40% | 6.41 |

The raw achieved-run figure is not a next-start forecast. For three-year-old
Group/Listed winners, retaining only 15% of the uplift improved test MAE by
0.68 points. Applying that illustrative state update to Guest House would move
the next-start state from 98.46 to approximately **99.34**, while preserving
104.30 as the completed-run achievement. A richer latent-ability model should
also incorporate earlier runs, official 102, development and uncertainty, so
99.34 is a diagnostic rather than a final forecast.

The two-year-old result selects zero carry and warns that the current class
prior remains too coarse for juvenile races. Open-age results do not justify a
broad replacement either.

## Implementation

- Added `racing_engine/achieved_run_young_wfa.py`.
- Added unit tests for cohort parsing, young-field reliability caps and
  evidence-dependent margin credit.
- Rebuilt contextual time evidence through Rosehill 29 August.
- Rebuilt hierarchical 200m energy/sectional evidence.
- Wrote 29,355 V2.10 shadow performances across 2,732 races.
- Preserved all accepted ratings unchanged.

## Next gate

Run V2.10 prospectively and build the separate latent-ability state using the
pre-2025-selected 3YO update as a baseline. Promotion still requires race-rank
calibration, NSW/Victoria and sex splits, complete age-profile coverage, and an
untouched prospective cohort. Existing time and sectional components have not
passed their standalone broad promotion gates, so they currently control
margin confidence rather than directly adding rating points.
