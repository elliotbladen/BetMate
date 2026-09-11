# Branch cleanup and racing handover — 12 September 2026

## Final owner decision and closeout

The owner explicitly instructed: merge/close the other PRs and **leave PR #14
open because the fitness/trials engine still needs work**. This supersedes the
initial inventory and pending clarification recorded below.

- PR #2 merged as `170c6684524b12cc621b5ec8c362e57425db2113`.
- PR #13 squash-merged as `0495bf23f2dc83e8804098ab41be51bf1d70791a`.
- This final handover is delivered in approved PR #15.
- PR #14 remains OPEN at `f51b0774e4753956623f72c06d8ac8959d5d7aea`.
- The remote analytics and September 11 handover branches were deleted after
  their merges. The earlier Next.js/reminder/tipping-fix cleanup also stands.
- Obsolete local map and wind branches were removed. Map's remaining commit
  was patch-equivalent to main and both changed files matched main exactly;
  wind had no unique commits. Only stale registrations for missing worktree
  directories were pruned; no worktree directory was deleted.
- The rejected raw-time local branch was removed after preserving its tip in
  local tag `archive/rejected-raw-time-2026-09-12` (PR #5 remains closed).
- Keep `feat/market-engine-cloud` until Railway runtime/source is verified.
  The later September 11 note says its source was moved to main, but explicitly
  retains the branch until collection is proven. No runtime check was made here.
- The shared checkout remains on its existing local branch with unrelated
  cloud edits, logs, data and scripts untouched. Local review checkouts may
  remain; a local reference does not mean a PR is still open.

### Validation and small repairs

Analytics initially passed its three tests but failed the Next.js build because
`route.ts` exported `validAnalyticsEvent`, which is not an allowed route export.
Moved the unchanged validator into `lib/analyticsEvent.ts`; the three tests and
Next.js 16 production webpack build then passed. Webpack was used because the
isolated checkout reused the existing node_modules via a symlink. The original
Vercel failures were not independently diagnosed. Production analytics storage,
its migration and deployment success were not verified or changed in this
closeout; merging source does not establish operational readiness.

Two fitness tests referenced deleted development-session temporary paths.
Changed only their imports and registry paths to use the committed repository.
All 14 focused fitness and horse-identity tests pass. This repair was pushed to
PR #14, which remains open; it does not mean the engine is complete.

Final documentation removes participant-specific records and private tips from
PR #13's final content. Documentation diffs were reviewed and whitespace checked.
No UI changes are part of these PRs and no visual checks were performed here.

### Trial-data question — verified limits

No racing database or trial archive was deleted or overwritten during this
cleanup. A read-only check of the local 18,624,581,632-byte racing database found
no tables with fitness/trial names. No trial collection archive was found in the
checked RacingEngine paths, and the original `/private/tmp/fitness_step*` folders
were absent before cleanup of any worktree registration. This does not prove
that data was never collected elsewhere or on another machine.

The trial schema, collector, source registry, identity and quality code are
preserved in PR #14 and the isolated fitness checkout. The committed plan lists
historical backfill as step 6, still outstanding. Locate and reconcile any
previous collection before re-collecting or claiming that trial data was lost.

### Resume horse-engine work

Continue PR #14; review the integration between extraction, identity, quality
checks and canonical event insertion before historical backfill. Measure actual
source coverage, then build preparation state, meeting-type conditioning,
chronological model evaluation and operational integration. Ratings and pricing
remain separate: accepted ratings are still form-first-v2.0, newer blends are
shadow/research, and no integrated validated race-day pricing engine is claimed.

## Initial inventory (historical; superseded by the closeout above)

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
