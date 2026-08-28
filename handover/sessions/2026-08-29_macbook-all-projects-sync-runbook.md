# MacBook sync runbook — all projects (2026-08-29)

Written on the Windows work machine after moving every repo out of OneDrive and
creating the SkyNet Capital GitHub remote. Follow this on the MacBook to pull the
latest from GitHub, fold in anything that only exists on the Mac, and push back so
both machines match.

Do the projects **in this order**. SkyNet is safe to do first (no divergence
possible). BetMate needs care — read its whole section before touching the Mac's
copy.

---

## 0. Golden rules

1. **Never keep a working copy inside iCloud Drive, OneDrive, or Dropbox.** File
   sync races with `.git/`, `bin/`, `obj/`, `node_modules/`, `.venv/` and corrupts
   state. Git is the only sync path between machines. Put everything under
   `~/dev/`.
2. **Never `git pull` / `git reset --hard` / `git checkout --` over uncommitted or
   unpushed work.** Check first (commands below). If both machines committed since
   the last sync, reconcile deliberately — keep the newer of each file — don't let
   git auto-merge or force.
3. **Commit and push before you walk away from a machine.** A machine left with
   uncommitted work is how the 2026-07-08 BetMate divergence happened.

### The "is there anything on the Mac I'd lose?" check

Run this in each existing Mac repo copy **before** pulling or deleting it:

```bash
cd <mac-copy-path>
git status                          # uncommitted changes?
git stash list                      # stashed work?
git log --branches --not --remotes --oneline    # commits never pushed anywhere?
git branch -vv                      # local branches, and which are [gone] upstream
```

- `git status` clean + last three commands empty  → nothing to save, safe to delete.
- Anything shows up  → deal with it per the project section below.

---

## 1. SkyNet Capital  (easy — one linear history, nothing to merge)

Remote: `https://github.com/elliotbladen/SkyNet-Capital` (private). It has **one
branch, `main`**, and the Windows machine pushed all of it. There is no sandbox
branch and nothing to reconcile.

### If the Mac has NO copy yet

```bash
mkdir -p ~/dev && cd ~/dev
git clone https://github.com/elliotbladen/SkyNet-Capital.git skynet-worldwide
cd skynet-worldwide
git config core.hooksPath .githooks          # blocks accidental direct pushes to main
dotnet build Skynet.slnx && dotnet test Skynet.slnx
```

Expect: 62 tests pass, 0 warnings. Green build + tests on macOS closes the Week 1
"architecture compiles on Windows and Mac" gate — tick it in
`docs/WEEK1_STATUS.md`.

### If the Mac has an OLD copy (e.g. under `~/Library/.../OneDrive/` or iCloud)

```bash
cd <old-skynet-copy>
git status
git log --branches --not --remotes --oneline
```

- **Clean + no unpushed commits** → just delete the old folder and fresh-clone as
  above.
- **Has unpushed commits** → they predate the GitHub remote, so rebase them on:
  ```bash
  git remote set-url origin https://github.com/elliotbladen/SkyNet-Capital.git
  git fetch origin
  git rebase origin/main          # resolve any conflicts, keep the newer content
  dotnet build Skynet.slnx && dotnet test Skynet.slnx
  git push origin main            # or push a branch + open a PR
  ```
  Then move the folder to `~/dev/skynet-worldwide` (or delete and re-clone) and
  run `git config core.hooksPath .githooks`.

### Push back

Nothing to push unless you rebased old Mac commits above. When you do:
`git push origin main` (the `.githooks/pre-push` hook will stop a *direct* push to
`main` — use a branch + PR, or `git push --no-verify` for a one-off).

### After

Delete every SkyNet copy that is not `~/dev/skynet-worldwide`. Confirm:
`git -C ~/dev/skynet-worldwide status` → clean, up to date with `origin/main`.

---

## 2. BetMate  (careful — two-machine repo, may have diverged)

Remote: `https://github.com/elliotbladen/BetMate.git`. Uses **Git LFS** and a large
local SQLite DB that does **not** travel by git.

Per `CLAUDE.md`, the second machine has historically been a Windows box at
`C:\Users\ElliotBladen\Apps`. **If your MacBook is now that second machine, or a
third one, treat its copy as potentially holding work nobody has pushed** and run
the full check below. Known possibly-unpushed item: the diary
`handover/sessions/2026-07-05_afl-ema-form-split-models.md` was flagged as existing
only on the other machine.

### Step A — prerequisites on the Mac

```bash
brew install git-lfs && git lfs install
brew install node
curl -LsSf https://astral.sh/uv/install.sh | sh      # uv, for the Python engines
```

### Step B — inspect the Mac's existing copy (do NOT pull yet)

```bash
cd <mac-betmate-copy>
git fetch origin
git status
git stash list
git log --branches --not --remotes --oneline        # unpushed commits
git rev-list --count origin/main..HEAD               # ahead of remote
git rev-list --count HEAD..origin/main               # behind remote
```

Interpret:

| ahead | behind | meaning | action |
|------:|-------:|---------|--------|
| 0 | 0 | in sync | nothing to do, go to Step D |
| 0 | >0 | Mac is just behind | `git pull --ff-only origin main` |
| >0 | 0 | Mac has commits to push | commit any WIP, then `git push origin main` |
| >0 | >0 | **diverged** — both machines committed | Step C |

Also handle uncommitted changes first: if `git status` is dirty, decide
per-file whether it's newer than what's on `main`; commit the keepers with a clear
message, discard the rest deliberately.

### Step C — reconcile a divergence (only if ahead >0 AND behind >0)

Do **not** `git pull` (it would auto-merge) and do **not** `git rebase` blind.

```bash
git log --oneline --graph --left-right origin/main...HEAD    # see both sides
git diff origin/main...HEAD --stat                            # files each side touched
```

For every file touched on both sides, open both versions and keep the newer /
correct content. Then:

```bash
git merge origin/main            # resolve conflicts by hand, favouring newer work
# OR, if the Mac's commits should sit on top cleanly:
git rebase origin/main
```

Untracked model artefacts (`ml/afl/results/models/*.pkl`) do **not** travel by git
— after merging any ML *code* changes, retrain locally (see `CLAUDE.md` → the
AFL ML retrain command).

If unsure, stop and open a Claude session on the Mac: *"BetMate sync-start says the
machines have diverged, reconcile it"* — the repo's `CLAUDE.md` documents the
2026-07-08 incident and the expected procedure.

### Step D — restore the RacingEngine database (not synced by git)

```bash
cd <betmate>/RacingEngine
git lfs pull
./restore_db.sh
# rebuild the two V1 tables excluded from the seed:
uv run python -m racing_engine.performance --as-of 2026-08-23
sqlite3 racing_engine.sqlite "PRAGMA integrity_check;"   # expect: ok
```

### Step E — rebuild environments and verify

```bash
cd <betmate>
cp .env.local.example .env.local        # fill in ODDS_API_KEY + Supabase keys
npm install

cd RacingEngine   && uv venv && uv pip install -r requirements.txt && uv run pytest -q ; cd ..
cd BettingEngine  && uv venv && uv pip install -r requirements.txt && uv run pytest -q ; cd ..
```

Expected (per the 2026-08-29 Windows run): RacingEngine ~141 pass / 1 skip,
BettingEngine ~95 pass.

### Step F — final position and push

```bash
cd <betmate>
git status                              # clean
git log --branches --not --remotes      # empty
git push origin main                    # if you have local commits
```

Move/rename the folder to `~/dev/BetMate` if it isn't already there. Delete any
BetMate copy under iCloud/OneDrive once this one is clean and green.

### Step G — scheduled tasks

The Windows `scripts/*.ps1` Task Scheduler jobs are Windows-only and hardcode
`C:\Users\ElliotBladen\Apps`. They do not apply on the Mac — ignore them there
unless you deliberately want the Mac running the pipeline.

---

## 3. Retired standalone repos

### BettingEngine (standalone, pre-monorepo)

- Its code now lives inside the BetMate monorepo (`BettingEngine/`). The standalone
  repo `https://github.com/elliotbladen/BettingEngine` was fully pushed
  (`786d483`) and the Windows copy deleted.
- On the Mac: run the "anything I'd lose?" check on any standalone
  `~/.../BettingEngine` folder that has its **own** `.git` pointing at
  `github.com/elliotbladen/BettingEngine` (not the monorepo). If it has unpushed
  work, push it to that repo; then delete the folder.
- Then **archive `github.com/elliotbladen/BettingEngine`** on GitHub (Settings →
  Archive this repository) so it's read-only.

### RacingEngine (standalone)

- On the Windows machine this was an empty husk and was deleted. Its real code is
  `BetMate/RacingEngine/`.
- On the Mac: if a standalone `RacingEngine` folder exists, run the check; push
  anything unpushed to its remote (if it has one), then delete.
- Check whether a standalone `RacingEngine` repo exists on GitHub — if so, archive
  it too.

### BetMate remote branch cleanup (do once, from any machine)

```bash
git push origin --delete racing-engine/step2-research
```

Its one commit (`532629a`) was already cherry-picked into `main` as `cb6afe2` —
identical files — so the branch is safe to delete.

---

## 4. Done-when checklist

- [ ] `~/dev/skynet-worldwide` — builds + tests green on macOS; `git status` clean;
      up to date with `origin/main`; `core.hooksPath` set to `.githooks`
- [ ] `~/dev/BetMate` — merged/rebased cleanly; LFS pulled; DB integrity `ok`;
      venvs rebuilt; tests green; `git status` clean; nothing unpushed
- [ ] No repo copy left under iCloud Drive / OneDrive / Dropbox
- [ ] `git config --global pull.ff only` set on the Mac
- [ ] BettingEngine (and any standalone RacingEngine) GitHub repos archived
- [ ] `racing-engine/step2-research` remote branch deleted
- [ ] `docs/WEEK1_STATUS.md` — macOS build line ticked, committed, pushed

## 5. Machine-identity note to resolve

`BetMate/CLAUDE.md` still describes the second machine as Windows at
`C:\Users\ElliotBladen\Apps`. If the MacBook has replaced that machine, update the
"TWO-MACHINE RULE" and "Where the repo lives" sections of `CLAUDE.md` with the Mac
path (`~/dev/BetMate`) and note that the `.ps1` sync scripts need bash equivalents
(or just run the git steps by hand). Same for SkyNet's `docs/WORKFLOW.md` if the
Windows↔Mac assumption there changes.
