# Handover — Step 1 going/rail/time family

Implemented `race-time-context-v2.1-shadow` in
`racing_engine/race_time_evidence.py`. It has strictly prior going-aware pars,
bounded rail evidence, leave-one-out meeting variants and provenance-preserving
Racing NSW clock observations subordinate to Racing.com identities.

The model built 1,266 historical figures from 2,264 available clocks. Training
on 2,603 pre-2025 next-start pairs selected coefficient zero, so it is not
promoted. Natural Fling's correctly adjusted clock is −0.70 fast MAD (0.315 sec
slow after the unusually fast meeting variant), not positive evidence.

Also audited the apparent 56 kg versus 49.5 kg WFA difference. Almost the whole
field carried the same 56 kg prescribed SWP base. Do not add that absolute
difference as personal merit; it would double-count race conditions.

Step 1 is not complete. Next: opposition strength and point-in-time collateral
reliability. Steward/trip remains shadow-only under the existing failed gates.
See `reports/v2_ratings/race_time_context_v2_1_findings.md` and JSON companion.
