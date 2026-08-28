# BetMate — repo audit & cleanup runbook

**Date:** 2026-08-28
**Machine audited:** Windows (F:). MacBook not inspected.
**BetMate state at audit:** branch `local-sandbox`, HEAD `907f790`.

---

## Verdict

No emergency, but do this soon.

- BetMate's Git history is **intact and current** with `origin` (local `main` == `origin/main`).
- Real exposure #1: every working copy lives under
  `F:\IS\OneDrive - insightsurvey.com.au\Documents\` — the exact setup that produced
  `unable to write .git/objects: Permission denied` on SkyNet this morning.
- Real exposure #2: ~3.0 GB of racing data exists **only** on this disk + OneDrive,
  with no real backup.

Fix = one-time relocation out of OneDrive on both machines + a proper data copy +
retiring the duplicate `BettingEngine` checkout. ~1 hour of careful work per machine.

---

## Findings (worst first)

### RISK — Every repo lives inside OneDrive
`BetMate`, `BettingEngine`, `RacingEngine`, `SkyNet Capital` all sit under
`…\OneDrive - insightsurvey.com.au\Documents\`. OneDrive continuously syncs `.git/`
internals, `.venv/`, `__pycache__/`. When it locks an object mid-write, Git fails:

```
error: unable to write file .git/objects/58/2bf4…: Permission denied
```

This machine also has **two** OneDrive roots (`OneDrive` and `OneDrive - INSIGHTSURVEY`
under the user folder, plus `insightsurvey.com.au` on F:) — easy to half-sync a project
to the wrong account.

### RISK — ~3.0 GB of racing data has no backup
In `BetMate/RacingEngine/data/`, only `seed/racing_seed.sql.gz` is tracked (Git LFS).
Local-only:

| path | size | note |
|---|---|---|
| `racing_engine.sqlite` | 1.5 GB | live working DB |
| `backups/` | 685 MB | rolling DB backups |
| `seed/` | 650 MB | seed + the tracked `.sql.gz` |
| `raw/` | 44 MB | scraped source files |

A 1.5 GB SQLite file live-synced by OneDrive can tear. `build_seed.py` / `restore_db.py`
already exist for cross-machine transfer — use that, don't sync the raw file.

### FIX — Duplicate, divergent `BettingEngine`
- `BetMate/BettingEngine/` — **active**, monorepo, work through Aug 2026, no own `.git`.
- `Documents/BettingEngine/BettingEngine/` — **stale**, own `.git` →
  `github.com/elliotbladen/BettingEngine`, last real commit ~Jun 2026 ("EPL engine v2").

BetMate's `.gitignore` literally says *"BettingEngine is tracked in this monorepo again."*
Files that differ and need a look before retiring the standalone:
`ml/afl/train.py`, `pricing/afl_tier4_venue.py`, `pricing/afl_tier7_weather.py`,
`pricing/tier6_referee.py`, `config/tiers.yaml`, `config/sports/nrl.yaml`, `db/queries.py`.

### FIX — Empty standalone `RacingEngine/` folder
RacingEngine now lives in BetMate (`BetMate/RacingEngine/`, branch
`racing-engine/step2-research`). `Documents/RacingEngine/` is 0 files — delete it.

### WATCH — Virtualenvs & caches syncing to OneDrive
`BetMate/RacingEngine/.venv`, `Documents/BettingEngine/BettingEngine/.venv` (~14 MB,
thousands of files each), plus `__pycache__/` everywhere. Regenerable. Moving repos out
of OneDrive + recreating venvs fixes it.

### WATCH — `local-sandbox` branch has drifted
Checked-out branch. 8 commits ahead of `origin/main` (all on `origin/local-sandbox`),
plus 1 local commit (`907f790`), 2 modified tracked files, ~40 untracked files
(RacingEngine V2 rating scripts + report JSON, ~1 MB). Decide: PR into `main`, rename to
a real feature branch, or land + delete.

### OK — Core Git integrity is fine
`git count-objects`: one 20 MB pack, zero garbage. LFS working (1 file). `.git` is 120 MB
only because `.git/lfs` holds 98 MB of cache — not bloat. No stashes, no detached HEAD,
no corruption.

---

## Runbook

Do phases in order. Run A–D on Windows first (it has the live data), then E for the Mac.

### A. Make everything safe first
- [ ] Commit/stash the dirty tree on `local-sandbox`, then `git push origin local-sandbox`.
- [ ] Copy `BetMate/RacingEngine/data/` to a backup **outside** OneDrive (external drive).
- [ ] Run `build_seed.py`, then `restore_db.py` into a throwaway path and diff row counts —
      prove the DB is recreatable from seed.
- [ ] Note: fresh clones need `git lfs install` then `git lfs pull`.

### B. Get BetMate out of OneDrive (Windows) — target `F:\dev\`
- [ ] Confirm `git status` clean/pushed, `git fsck` quiet.
- [ ] Move `Documents\BetMate` → `F:\dev\BetMate` (move, not copy).
- [ ] Reopen from new path; `git status`, `git lfs pull`, `git log --oneline -3`.
- [ ] Recreate `RacingEngine\data\` in place from backup or seed (it's Git-ignored).
- [ ] Rebuild venvs: `python -m venv .venv` + `pip install -r requirements.txt` in
      RacingEngine and BettingEngine.
- [ ] Smoke-test: one RacingEngine rating build + one BettingEngine pricing script.
- [ ] Same move for `SkyNet Capital` → `F:\dev\skynet-worldwide` (see its `docs/REPO_SETUP.md`).

### C. Retire the duplicates
- [ ] Diff standalone `BettingEngine` vs `BetMate/BettingEngine`; salvage newer logic.
- [ ] Commit anything salvaged into the monorepo.
- [ ] Delete `Documents\BettingEngine\`; **archive** (don't delete) the GitHub repo.
- [ ] Delete empty `Documents\RacingEngine\`; archive its GitHub repo if one exists.

### D. Hygiene
- [ ] Tighten BetMate `.gitignore`: `**/.venv/`, `RacingEngine/data/` (only root `/data/`
      is ignored today), `**/*.sqlite`, `**/backups/`.
- [ ] Resolve `local-sandbox` (PR / rename / land+delete).
- [ ] Keep all dev work in `F:\dev\`, outside OneDrive entirely.
- [ ] Add a "where things live" note to BetMate `CLAUDE.md`.

### E. Bring the MacBook into line (after Windows is clean + pushed)
- [ ] Check every old OneDrive copy on the Mac for unpushed commits / stashes.
- [ ] Fresh clone into `~/dev/`; `git lfs install && git lfs pull`.
- [ ] Recreate venvs; restore RacingEngine DB from seed.
- [ ] Smoke-test the same two scripts.
- [ ] Delete the old OneDrive copies.
- [ ] From now on: `git pull` when you start, `git commit && git push` before you leave.
      Never OneDrive.
