# NFL Step 8C — QB profile and reviewed-starter workflow

## Outcome

A pregame QB profile library and reviewed-starter workflow are operational.
Historical play-by-play through 2025 produced 446 regressed QB profiles; 104
players appeared in 2025. Profiles contain prior dropbacks, EPA, success, sack,
turnover and scramble posteriors using the frozen 150-dropback prior.

The Week 1 review sheet has one row per game. It requires a named starter and
backup for both teams, a starter probability, review cutoff, published source
timestamp, source name and optional notes. IDs are resolved against the profile
library before they can enter the live tier template.

## Safety behavior

- Historical results generate player profiles but do not choose 2026 starters.
- Source publication must be no later than the review cutoff.
- The review cutoff must be before kickoff.
- Unknown player IDs, duplicate games and probabilities outside zero to one are
  rejected.
- A blank review returns `review_unresolved`, archives nothing and applies no
  adjustment.
- The generated profile library is descriptive shadow data; no automatic bet or
  T1 price change is authorised.

## Artefacts

- `ml/nfl/step8_qb_profiles.py`
- `data/nfl/live_tiers/qb_profiles_through_2025.csv`
- `data/nfl/live_tiers/2026_week01_qb_review.csv`
- `tests/test_nfl_step8_qb_profiles.py`

The focused NFL suite passes 30 tests. The remaining operational input is a
timestamped, reviewed Week 1 starter/backup list. Starter probabilities should
be explicit judgment backed by official depth charts and injury/practice news,
not inferred from the eventual player who starts.
