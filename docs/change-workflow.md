# Five-step workflow

The owner requires this workflow for every change. `AGENTS.md` is the repository
instruction and `.github/pull_request_template.md` is the review checklist.

1. Start a dedicated branch from current main. Isolate unrelated workspace work.
2. Review the complete diff and explain the change to the owner.
3. Run relevant tests and check the real behaviour locally.
4. Push the branch and open a PR for owner/teammate review.
5. Wait for explicit approval of that PR, then merge and deploy. Verify the live
   result after deployment.

Opening a PR or creating a preview is not permission to merge or deploy to
production. Previous release approvals do not carry forward. Never push directly
to main. Record test limitations and planned data/configuration changes in the
PR before asking for approval. These files guide contributors and agents; they
are not a substitute for GitHub branch protection or a human review.

## Tipping regression checks

The saved-selection fix can be reviewed without signing into a real account or
changing production tips. Browser tests intercept every tipping API request and
use a synthetic Supabase session on a fake project hostname.

Use an isolated checkout with dependencies installed. For this local test server,
put these **dummy** values in its ignored `.env.local` (do not overwrite a working
environment file or commit it):

```dotenv
NEXT_PUBLIC_SUPABASE_URL=https://tipping-test.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=local-browser-test-key
```

Start `npm run dev -- --port 3101` in one terminal. In another:

```sh
npm run test:tipping
npm run test:tipping:ui
npx tsc --noEmit
```

Playwright requires its Chromium browser to be installed. `TIPPING_TEST_URL` can
select a different localhost port. Tests refuse non-local hosts and must never
be pointed at a live deployment. The URL hostname must match the configured
synthetic cookie domain; use `localhost` by default.

Covered behaviour:

- Late initial-round tips cannot replace the active round's saved highlights.
- Ten saved choices remain 10/10 when a choice is changed, saved and reloaded.
- Delayed fixture responses cannot replace cards after switching rounds.
- Foreign, obsolete and duplicate tip rows cannot inflate the count.
- A refresh started before an edit/save cannot overwrite the newer choice.
- Unsubmitted choices survive the five-minute refresh interval.
- Failed loads offer a retry; failed writes do not display a success message.

## Tipping change review — 10 September 2026

Reproduced before the fix using synthetic data: resolve GW3 fixtures and tips,
then release a delayed GW1 tip response. The page showed **10/10 with zero
highlighted teams**. Selecting Draw changed it to **11/10**.

The fix loads fixtures and tips as one round/account-scoped result, aborts old
requests, validates tip IDs against the round, and derives progress from the
visible fixtures. It also preserves drafts during refresh and checks the API's
per-tip save outcomes. No fixture IDs are migrated and no production data repair
is required for this reproduced issue. A read-only production diagnostic found
valid stored IDs for the checked GW3/GW4 records; private selections were not
exported or copied into tests.

Validation before review: TypeScript passed; 9 existing tipping unit tests and
5 browser regression scenarios passed. Production merge/deployment remains gated
on the owner's approval of the PR.
