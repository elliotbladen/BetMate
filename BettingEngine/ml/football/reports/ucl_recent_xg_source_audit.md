# Recent UCL xG source audit

SofaScore's public event endpoints provide match shotmaps with per-shot xG for both required seasons. The first pull returned 441 completed events: 215 in 2024/25 and 226 in 2025/26, including qualifying and knockout events. Every row has an event ID, teams, score, kickoff field and non-null home/away xG; duplicate event IDs are zero.

This is enough to build a recent-season xG candidate, but it is not yet production-ready. The next validation must map events one-to-one to our 378 competition matches, confirm that kickoff timestamps and club identities agree, and record retrieval timestamps/checksums. The public endpoint is an undocumented source, so it remains a labelled provider feed rather than an assumed official UEFA archive.

Source coverage was verified from SofaScore's UCL season endpoint, which lists season IDs 61644 (2024/25) and 76953 (2025/26). Shotmaps were downloaded from the corresponding event endpoints.

The conservative identity/date join now maps 342 of 378 canonical modern-era matches (90.5%): 156/189 in 2024/25 and 186/189 in 2025/26. Six candidates remain ambiguous and 36 are unmapped; these are quarantined. This is a strong candidate feed, but it is not yet safe to replace the goals fallback for every match.

Investigation found the principal 2024/25 gap is upstream date quality: the Openfootball repair archive collapses multiple league-phase matchdays onto placeholder dates. Those rows cannot be date-joined safely even when the club pair is known. They must be repaired from a dated fixture source or matched by a separately audited matchday/leg key.
