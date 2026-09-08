# UCL researched repricing — 2026-09-08

User explicitly requested internet research for current injuries and domestic
form/rest, followed by prices incorporating that information.

## Outcome

Nine provisional 90-minute 1X2 prices produced for European September 8–9 /
Sydney September 9–10. Three remain blocked for missing comparable opponent
strength: AEK–LASK, Lille–Betis, Stuttgart–Viking. Current form and injury context
was researched for all 24 teams, including these blocked matches.

Outputs: `outputs/football/ucl/2026-09-08_researched/run1/report.md`,
`prices.csv`, `prices.json`. No production promotion, bet signals or placements.
Totals remain withheld because the separate live O/U model does not consume
these tiers; raw score-matrix totals were not substituted for that model.

## Research and provenance

- Downloaded 2026/27 domestic results for England, Spain, Italy, Germany, France,
  Portugal, Belgium, Netherlands, Greece and Turkey from Football-Data. Austrian
  and Norwegian archives use AUT/NOR feeds. The www hostname returned 503;
  the non-www hostname worked after network escalation.
- Read current UEFA team news for all fixtures and archived the page.
- Supplemented Slovan from its official dated fixture/results page, including
  the August 30 loss to Michalovce and September 5 loss at DAC.
- Updated Viking's September 4 draw and LASK's September 5 cup match for rest.
- Dimarco changed from UEFA doubtful to out after the September 7 travel report.
- Real Madrid club training and press conference supersede parts of the UEFA
  list: Mendy remains out; Endrick/Thiago are treated as uncertain/limited rather
  than definite absences. Endrick's limited minutes are documented, not assumed
  to be a full match. Tchouameni remains a scenario uncertainty.
- Archived sources, hashes and detailed inputs in `raw/` and `context.json`.
  `build_context.py` reproduces the research input from those archives and the
  explicitly documented manual source supplements.

## Calculation repairs and boundaries

1. Explicitly harmonized 28 historical club-ID aliases in this research dataset.
2. Added optional optimizer settings/diagnostics to shared DC fit. Legacy default
   optimizer settings remain unchanged. UCL research allows 500,000 evaluations
   and 2,000 iterations; the corrected run converged in 680 iterations / 224,575
   evaluations.
3. Found an actual normalization defect: dividing attack and defence by separate
   geometric means changes the expected-goals ratio unless the base rates are
   compensated. Added opt-in `preserve_fitted_rates=True`; compensation in this
   run was 0.5670072861. Legacy production callers keep their existing version.
   The old uncorrected converged fit produced inflated rates and even a negative
   score cell for PSG–Slovan, which the research runner rejected.
4. Added explicit `context` support to the UCL adapter. Live context replaces
   stale historical UCL-only form/rest; it is never added a second time.
5. New `ml/football/ucl_researched_pricing.py` validates provenance/cutoffs,
   rejects missing teams and nonconverged fits, checks the canonical training
   hash and the full probability distribution, and writes a new output directory.

Research scenario uses existing capped broad-position injury weights. It does
not activate the trained player shadow. Expected minutes/replacement quality
are not learned; long-term absences can overlap historical strength. Confirmed
outs enter the central price; four home/away doubtful-out combinations provide
availability sensitivity. No probability is assigned to the doubtful scenarios.

Form uses current-season domestic league results only. Where fewer than five
matches exist, unplayed slots contribute a neutral 1.5-point prior, explicitly
labelled as a shrinkage assumption rather than invented results. Rest uses
calendar-date differences from the latest verified competitive club match.

Referee names are sourced, but referee scoring rates, PPDA, calibrated weather,
travel/rotation and confluence are not populated. No current bookmaker quote was
captured and no EV calculated. These remain provisional researched prices, not
complete validated all-tier production outputs.

## Reproduction and verification

Fit script: `outputs/football/ucl/2026-09-08_researched/fit_researched.py --output NEW_FILE`.
Frozen ratings: `ratings_corrected.json` in the same directory. `ratings_probe.json`
is the earlier uncorrected normalization probe and must not be used for pricing.

Pricing:

```bash
.venv/bin/python -m ml.football.ucl_researched_pricing \
  --context outputs/football/ucl/2026-09-08_researched/context.json \
  --aliases outputs/football/ucl/2026-09-08_researched/aliases.json \
  --ratings outputs/football/ucl/2026-09-08_researched/ratings_corrected.json \
  --output outputs/football/ucl/2026-09-08_researched/NEW_RUN
```

Fifteen targeted unittest tests passed: new researched-pricing tests and existing
UCL tier/context/market tests. They cover normalization invariance, live context
replacement, injury direction, doubt handling, future inputs, team identity,
and failed-fit rejection. Verified all nine prices and four scenarios per match
have valid probabilities. Scoped whitespace check passed. Pytest is not installed;
used the repository's unittest style without installing a dependency.
