# Handover — OneDrive relocation and repo cleanup

Date: 2026-08-29
Machine: work ("Insight Survey" / ISLP06)
Scope: repo hygiene only. No pricing, ratings, or model work.

## What changed

### 1. BetMate moved out of OneDrive
- `F:\IS\OneDrive - insightsurvey.com.au\Documents\BetMate` → **`F:\dev\BetMate`**.
- Reason: OneDrive was locking `.git/objects` mid-write (`unable to write ... Permission denied`),
  the same failure that hit the SkyNet repo. "Pause syncing" was not enough — OneDrive
  (`OneDrive.exe` + `OneDrive.Sync.Service.exe`) had to be fully stopped for git to work.
- Post-move verification: `git fsck` clean, HEAD unchanged, both branches in sync,
  `git lfs fsck` OK, seed sha256 matches, `racing_engine.sqlite` `PRAGMA integrity_check` = ok.

### 2. Uncommitted work committed and pushed
- `b899593` — the full 28 Aug RacingEngine V2 build day (14 engine modules, 12 test
  suites, ~23 rating reports, 12 session docs) that had never been committed.
- `5ec2a32` — Codex exit-handover (Horse Ability v2.8 freeze notes, Group 1 Doncaster audit).
- `780fdfd` — this cleanup's hygiene commit (CLAUDE.md relocation note, `.gitignore` catch-alls).

### 3. Branch cleanup
- This machine had been working on `local-sandbox`, not `main` — a slow-motion version of
  the 2026-07-08 divergence. `local-sandbox` was exactly `main` + 11 commits (pure FF).
- Fast-forwarded `main` to `local-sandbox`, pushed, **deleted `local-sandbox`** (local + remote).
- This machine is back on the two-machine `main` protocol.
- `origin/racing-engine/step2-research` is fully absorbed (its commit `532629a` was
  cherry-picked as `cb6afe2`, identical files + seed blob). Safe to delete on GitHub —
  not yet done.

### 4. Standalone repos retired
- `Documents\BettingEngine\` (pre-monorepo checkout, own `.git` → `github.com/elliotbladen/BettingEngine`)
  had outstanding working-tree changes — committed + pushed as `786d483` so the repo is a
  complete snapshot, then the local folder was deleted. Its `WorldCupEngine/ml/epl/` is
  superseded by monorepo `ml/football/` (the Jul 9 league-parameterised refactor).
  **Archive that GitHub repo** (read-only) — not yet done.
- `Documents\RacingEngine\` — empty husk, deleted.

### 5. Data
- Backed up `RacingEngine/data/raw/` (43 MB, scraped Betfair/RNSW/racing.com sources) and
  the 682 MB `racing_engine_pre_2026-08-22_v2_ratings.sqlite` checkpoint to
  `F:\dev\_backup\BetMate-RacingEngine\` (checksums verified).
- Deleted the 603 MB uncompressed `data/seed/racing_seed.sql` build artifact (the tracked
  `.sql.gz` in LFS is canonical).
- `racing_engine.sqlite` (1.5 GB) is reproducible: `git lfs pull` → `restore_db.sh` →
  `python -m racing_engine.performance --as-of 2026-08-23`. Validated 28 Aug.
- Environments rebuilt fresh at the new path: `RacingEngine/.venv` (pypdf), `BettingEngine/.venv`
  (pandas/pytest/pydantic/...).

## Outstanding (user)

1. Restart OneDrive.
2. Archive `github.com/elliotbladen/BettingEngine` on GitHub.
3. `git push origin --delete racing-engine/step2-research` (or delete on GitHub).
4. Check for a standalone `RacingEngine` GitHub repo; archive if it exists.
5. Move `SkyNet Capital` out of OneDrive (`F:\dev\skynet-worldwide`) — blocked in-session.
6. MacBook: check its OneDrive copies for unpushed work, then fresh-clone into `~/dev/`,
   `git lfs pull`, `restore_db.sh`, rebuild venvs; delete the OneDrive copies.
7. Optional: make `scripts\git-sync-*.ps1` path-portable
   (`Set-Location (Split-Path $PSScriptRoot -Parent)`).
