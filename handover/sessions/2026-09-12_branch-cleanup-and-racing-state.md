# Branch cleanup and racing handover — 12 September 2026

## Verified repository state

Fetched origin and checked all GitHub PR states. Main was `71a7f2472f68a3f73016d70018f8ac7445d48b5d`.
This is an inventory and documentation change, not approval to merge or deploy.

## Open work

| PR | Branch | State and next action |
|---|---|---|
| [14](https://github.com/elliotbladen/BetMate/pull/14) | `feat/fitness-trials-engine` | Steps 1–5 have code, documentation and synthetic tests. Review the foundation before continuing steps 6–10. |
| [13](https://github.com/elliotbladen/BetMate/pull/13) | `docs/2026-09-11-handover` | Previous session handover and CLAUDE.md update; preserve its operational findings pending review. |
| [2](https://github.com/elliotbladen/BetMate/pull/2) | `feat/analytics-backend-foundation` | Analytics endpoint, migration and validation tests; production migration is not applied according to the PR. Review against current Next.js 16 main. |

All three were reported mergeable by GitHub, but each had a failed Vercel status.
The failures were observed, not diagnosed. Mergeability does not establish readiness.
The owner was asked whether closing outstanding work means preparing it for merge
review or closing without merging. No unmerged PR was closed or merged during
this inventory. Specific merge approval remains required under root AGENTS.md.

## Cleanup performed

Deleted remote branches `chore/nextjs-16-upgrade`, `feat/tipping-reminders` and
`fix/tipping-saved-selection` after verifying all were ancestors of current main
and their PRs were merged. Deleted the first two corresponding local branches.

Retained `feat/market-engine-cloud`: fully merged, but the previous handover
records Railway using this branch. Verify the configured deployment source
before deleting it; changing production configuration requires owner approval.

The WFA-coverage and map PRs are merged and their remote branches were already
deleted. The rejected raw-time proposal, PR #5, is closed and its remote branch
was already deleted. Local references remain for the rejected proposal, the map
branch and the wind rollout. The map and wind worktree registrations are marked
prunable; no directories or unmerged local commits were removed. Wind has no
commits outside main; map retains a commit from its separately merged work.

The shared checkout contains unrelated generated logs/data and an untracked
collector script. These were left untouched. This handover uses an isolated
checkout based on current origin/main.

## Horse rating and pricing state

The accepted model remains `form-first-v2.0` under the stored promotion policy.
Newer speed/sectional blends and Dan-aligned WFA figures remain research/shadow.
The latest committed WFA rebuild reports 29,498 runs and approximately 98.7%
WFA coverage. Reconstructed profiles are retrospective; coverage is not proof
of point-in-time validity or promotion readiness.

Rating work still needs a clean chronological comparison against last-start
and official-mark baselines, using ordering, repeatability, margin calibration
and scale. Do not resurrect the rejected raw-time proposal as accepted work.
Older handovers contain conflicting production labels; the stored policy and
the explicit correction in CURRENT_RATINGS_STATE.md take precedence.

Tempo, context-conditioned shadow maps, blended course/barrier suitability and
track-specific connections foundations exist on main. They are not an integrated,
validated pricing model. The old price_card.py is a basic shadow converter and
does not combine the newer components into race-day fair prices.

PR #14 adds the missing fitness/trials foundation: event schema, source registry,
HTML ingestion/archive, identity linking and quality quarantine. Its remaining
planned stages are historical backfill, preparation state, meeting-type
conditioning, chronological model evaluation and operational integration.
The presence of these modules does not establish live source coverage or a
completed end-to-end ingestion pipeline. Its plan requires review at each step.

## Operational follow-up

PR #13 records unverified cloud execution and reminder-cron failures at the end
of September 11. Treat those as outstanding until checked against current
runtime evidence. Do not infer successful execution from a green build or an
Online service label. This session did not inspect or modify production.

## Validation and resume

Verified remote refs, PR states, merge ancestry, branch diffs and committed
racing reports. No engine tests were rerun during this documentation inventory.
Review this document's complete diff and run git diff --check before committing.
Resolve the owner's intended disposition of PRs #14, #13 and #2 before closing
or preparing releases. Preserve unfinished work and update this handover with
any subsequent decisions rather than calling it completed by assumption.
