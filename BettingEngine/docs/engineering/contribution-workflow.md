# BetMate contribution workflow

This is the human-facing version of the mandatory engineering rules in
`CLAUDE.md`.

## A normal change

1. Start from an up-to-date `main` branch.
2. Create a focused branch named for the change.
3. Write the acceptance criteria.
4. Implement the smallest complete change.
5. Add meaningful tests.
6. Run checks locally and record the commands and results.
7. Commit with a conventional message.
8. Open a GitHub pull request.
9. Review the diff, tests, risks and screenshots or reports.
10. Merge only after CI passes and review is complete.
11. Verify staging, then deploy production when appropriate.
12. Write a handover note before ending the session.

## Change-specific evidence

### Frontend

Include type checks, lint, build output, relevant browser tests and screenshots.

### Backend and API

Include request validation tests, contract tests, error behaviour, migration
notes and compatibility information.

### Data ingestion

Include source URLs, licence notes, timestamps, schema checks, row counts,
identity checks and raw-input hashes.

### Model research

Include the hypothesis, cutoff, training/test split, baseline, walk-forward
metrics, calibration, leakage controls, negative controls, artefact hashes and
promotion decision.

## When the user reviews

The user should review visible product behaviour, material model decisions,
privacy-impacting changes and production deployment decisions. The reviewer
should be able to reproduce the result from the PR without relying on chat
history.

## What is never acceptable

- Directly editing `main` for ordinary work
- Mixing unrelated changes in one commit
- Merging with failing tests
- Overwriting frozen outputs without a new run ID
- Treating shadow output as official pricing
- Guessing missing data without labelling the assumption
- Deploying without a staging check
