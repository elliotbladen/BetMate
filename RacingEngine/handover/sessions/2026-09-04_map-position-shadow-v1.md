# Map Position Indicator shadow V1 handover

Implemented on 4 September 2026:

- Architecture: `docs/map_position_indicator_architecture.md`
- Audited early-time recovery in `racing_engine/sectional_features.py`
- Expanded map-relevant steward classifications in `racing_engine/stewards.py`
- Historical profiles, isolated storage, probabilistic field prediction,
  deterministic 10,000-run constrained simulation and evaluation in
  `racing_engine/map_position.py`
- Partial course registry in `config/map_course_configurations_v1.json`
- Supabase append-only prediction migration in
  `../supabase/migrations/20260904_map_position_shadow.sql`
- Tests in `tests/test_map_position.py` and `tests/test_sectional_features.py`
- Scorecard: `reports/map_position/map_position_v1_scorecard.md`

Database materialized 43,721 historical rows and 37,713 observed labels. The
first chronological model failed the population baseline and is therefore
correctly blocked from pricing.

Still required before V2 evaluation:

1. Backfill the official Racing NSW post-race reports and pre-race Raceday
   Rundown/tactics documents. The generic deterministic event parser now knows
   map-relevant categories, but the dedicated NSW archive acquisition run is
   not yet implemented/executed.
2. Populate verified first-turn distances for each track/distance start. The
   registry deliberately leaves unverified distances null.
3. Add distance/track/going, trainer and jockey partial pooling to the model.
4. Wire the Supabase migration/output call into the existing Railway tempo
   worker and deploy only after local dry-run approval.
5. Collect and score 500 genuinely live runner predictions.

Production remains `form-first-v2.0`; horse ability V2.10 and Map Position V1
both remain independent shadow products.
