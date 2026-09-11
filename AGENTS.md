# Required change workflow

These rules apply to every change in this repository, including fixes,
configuration, data changes and deployments. They record the owner's explicit
agreement of 10 September 2026 and take precedence over a faster release path.

1. **Separate branch.** Start from current production/main on a dedicated branch.
   Use an isolated checkout when the shared workspace contains unrelated work.
   Do not commit or overwrite another task's changes.
2. **Review the diff.** Inspect the complete diff and explain the problem,
   proposed behaviour and material risks in plain language. Give the owner a
   concrete diff to review; never ask them to approve an unspecified change.
3. **Verify.** Run checks appropriate to the change, reproduce bug reports when
   possible, and check the actual UI for visual or interaction changes. Report
   what passed, what failed and what could not be verified.
4. **Pull request.** Push the dedicated branch and open a pull request into main.
   Include the cause, fix, validation evidence and any outstanding limitations.
   Stop at a reviewable PR while awaiting the owner's review.
5. **Approval, then release.** Merge and deploy only after the owner explicitly
   approves that specific change/PR. Prior approvals or earlier requests to
   deploy other changes do not authorise the next release. Never push directly
   to main or change production configuration/data before this approval.

Creating a branch, editing files, running local tests and opening the PR are
already authorised by a request to fix or implement something. Do not repeatedly
ask permission for those steps. Sandbox permissions are separate from release
approval. A preview deployment is for review, not permission to promote it.

Never include secrets, authentication tokens, private tips or unrelated user
records in commits, PR descriptions, logs or test fixtures. Reproduce data issues
with anonymised/synthetic fixtures. Production diagnostics should be read-only;
prepare any necessary repair as a reviewable, scoped operation for step 5.

<!-- BEGIN:nextjs-agent-rules -->

# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->
