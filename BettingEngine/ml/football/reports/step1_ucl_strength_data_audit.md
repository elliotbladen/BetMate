# UCL Step 1 — data and strength audit

The repaired Openfootball archive is the validated fixture foundation: 1,997 matches, 136 clubs and 15 seasons (2011/12–2025/26). All required match identifiers, scores and UTC dates are present, with zero invalid rows. Market odds were not used.

The archive is now content-addressed with SHA-256 `d58573395a1460e8ee95e9fa85ad9c6c0c8fd65ca232d3a606e07b20b7a8a99c`; duplicate match IDs and missing team IDs are both zero. This makes source drift and accidental fixture replacement detectable.

The audit also found the important remaining dependency: a dated UEFA coefficient file and domestic-strength snapshots are not yet present in the repository. The model therefore must not pretend that the UEFA prior is active. ClubElo and the existing Dixon-Coles/form/rest stack can operate, but Step 1 is only fully complete after the coefficient and domestic-strength imports are sourced and timestamped.

The machine-readable result is `step1_ucl_strength_data_audit.json`. The next action is to populate the coefficient and domestic-strength contracts, validate club-name coverage against the canonical registry, and then activate the cross-league shrinkage prior.
