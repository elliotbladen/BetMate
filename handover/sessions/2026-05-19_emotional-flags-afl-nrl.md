# Session 2026-05-19 — Emotional Flags: NRL fix + AFL build + automation

## What was done

### NRL Emotional Scraper — path fix + reschedule
- `scripts/run_nrl_emotional.ps1` had stale path: `Apps\BetMate\.env.local` → fixed to `Apps\.env.local`
- Task "BetMate NRL Emotional Flags" rescheduled from Tuesday 11:00 → Tuesday 14:00 (`schtasks /Change /TN ... /ST 14:00`)
- Ran for R12 — 5 games loaded (bye round), 0 flags returned by Claude. Correct — no notable motivational angles.

### AFL Emotional Scraper — built from scratch
- New file: `lib/scraper/afl_emotional.py`
- Architecture mirrors `nrl_emotional.py` with AFL-specific changes:
  - Fixture read from `BettingEngine/outputs/afl_round_prep/rNN_YYYY/fixture_rNN_YYYY.csv` (no AFL fixture JSON exists)
  - `--round 0` auto-detects latest round from that directory
  - No DB-based shame_blowout (no AFL results in BettingEngine DB)
  - AFL rivalry list: 15 pairs including WA Derby, Showdown, Freeway Derby, Sydney Derby, Queensland Derby
  - Injuries from `data/afl/injuries/processed/latest-injuries.json` (flat list)
  - Team news from `data/afl/team-news/latest.json` (nested by team)
  - Output: `data/afl/emotional/raw/`, `data/afl/emotional/processed/`, `data/afl/emotional/logs/`
- Claude model: `claude-opus-4-7`, conservative system prompt (0-2 flags expected per round)

### Wrapper + Task Scheduler
- New wrapper: `scripts/run_afl_emotional.ps1` — loads `.env.local`, sets PYTHONUTF8, runs with `--round 0`
- New task: "BetMate AFL Emotional Flags" — Tuesday 14:30, verified next run 26/05/2026
- Test-fired via `schtasks /Run` — clean execution, log confirmed at `data/afl/emotional/logs/task.log`

### R11 AFL test run
- Ran for R11 — 9 games loaded, 0 rivalry derbies in fixture, Claude returned 0 flags. Correct.

## Current task state
- NRL emotional: fixed, rescheduled, tested ✅
- AFL emotional: built, automated, tested ✅

### Bets Logged + CLV Reports (R11 NRL + R10 AFL)
- 12 bets logged to `BettingEngine/data/bets/actual_bets_2026.csv` (ids 2026-0016 to 2026-0027)
- Screenshots saved to `data/bets/screenshots/` (3 files)
- `lib/researchData.ts` updated: 11 new LEGACY_BETS (ids 341–351), cumPL now 27.35
- 5 NRL R11 MODEL_BETS added (ids 27–31), MODEL runningTotal now 2.07
- Fixed encoding bug in `BettingEngine/scripts/nrl_weekly_clv_report.py`: `utf-8-sig` → `latin-1` (pricing CSV has em-dash in cp1252)
- **NRL R11 CLV reports run successfully:**
  - `outputs/nrl_weekly_review/reports/r11_nrl_clv_report_2026.csv` — 48 rows, model 12W/12L, market 6W/13L
  - `outputs/nrl_weekly_review/reports/r11_nrl_ml_comparison_2026.csv` — ML **16W/8L** vs normal 12W/12L vs market 6W/13L
  - ML shadow is outperforming on totals: consistently picks under, rules engine consistently picks over
- AFL R10 CLV: **not available** — no AFL predictions stored for R10 (AFL pricing only ran for R11 this session)

**Session P&L (11 bets excl. horse racing):**
NRL R11 Magic Round: 4W/1L (+$130.35 profit)
AFL R10: 4W/3L (+$159.75 profit on winners, -$150 losses) = net +$9.75 across AFL
Combined session: 8W/3L

### CLV TXT Generator — built + run
- New script: `BettingEngine/scripts/generate_clv_txt.py`
  - Usage: `python generate_clv_txt.py --sport NRL --season 2026 --round 11`
  - Reads from: `outputs/{sport}_weekly_review/reports/r{rnd}_{sport}_clv_report_{season}.csv`
  - Outputs to: `results/clv_{sport}_r{rnd}_{season}.txt`
  - Mirrors the hand-crafted R8 format (H2H CLV, Handicap, Totals, Summary)
- **NRL R11 CLV TXT produced:** `results/clv_nrl_r11_2026.txt`
  - H2H CLV @ open: **+16.5%** (elite benchmark +3%) — 6/8 picks won (75%)
  - Handicap: 4/8 (50%)
  - **Totals: 1/8 (12%)** — model consistently pricing totals too HIGH vs market (Eels 62.1 vs 52.5, Roosters 60.4 vs 54.5) — totals model needs review
  - Key value wins: Warriors +42% CLV @ open (won 42-12), Sharks +17% (won 38-16), Dolphins +15% @ open
  - Tiger miss: CLV +79% (market had them at 3.40, model 1.90) — lost 18-46 to Eagles; market was right

### Rolling CLV — Extended to R9
- Generated `data/import/r9_results_2026.csv` from DB (round 8 games — `r9_pricing_2026.csv` was mislabeled pre-offset-fix, contains April 23-26 games = DB round 8)
- Ran `nrl_weekly_clv_report.py --round 9` → `outputs/nrl_weekly_review/reports/r9_nrl_clv_report_2026.csv`
- Ran `nrl_weekly_ml_clv_report.py --round 9` → `outputs/nrl_weekly_review/reports/r9_nrl_ml_comparison_2026.csv`
- Rolling summary now covers R9, R10, R11:
  - H2H (rules engine): **17-7 (71%)** across 3 rounds, avg beat-close +2.4%
  - Handicap: 11-13 (46%) — flat
  - Totals: 6-10 (42%) — systematic problem, model prices totals 5-10pts too high

### AFL CLV
- **AFL R10 (user's bets):** No model prices exist for R10 (pipeline skipped R10 entirely — R9→R11). Market CLV only (beat-the-close from xlsx):
  | Bet | CLV vs Close | Result |
  |-----|-------------|--------|
  | Under 181.5 Swans/Collingwood | -7.0% (market going OVER, contrarian win) | WIN |
  | Collingwood +35.5 | +0.5% | WIN |
  | Gold Coast -26.5 | 0.0% | LOSS (won by 25, needed 26.5) |
  | Carlton H2H @ 2.56 | +8.9% (best beat) | WIN |
  | Hawthorn -18.5 | -2.1% | LOSS (Melbourne won by 39) |
  | Adelaide -18.5 | +2.7% | WIN (won by 68) |
  - Average CLV: +0.5% (flat). 4W/2L.
- **AFL R9 model CLV** (last priced round): ran `afl_weekly_ml_clv_report.py --round 9`
  - H2H: **9W/0L (100%)**, avg CLV +1.2% — extraordinary round, every pick won
  - Handicap: 6W/3L (67%)
  - Totals: 5W/4L (56%) — same over-pricing issue as NRL

### Tuesday 2026-05-19 Pipeline — All Automation Ran Clean
- NRL Results Fetch (Mon 09:00): R11 loaded to DB ✅
- NRL + AFL Historical Downloads: new xlsx files saved ✅
- NRL Injuries (11:05): 109 records R12 ✅
- AFL Injuries (16:00): 167 records R11 ✅
- NRL + AFL Style Stats: updated ✅
- NRL Round Prep R12 ✅ (referees 404 — expected, not announced yet)
- AFL Round Prep R11 ✅
- NRL Emotional R12: 0 flags ✅
- AFL Emotional R11: 0 flags ✅
- Odds Snapshot: running ✅

### SaaS Architecture Discussion
Product vision confirmed: BetMate as SaaS community, Baz as lead AI agent across sports + planned crypto AI agent.

**Decided architecture:**
- Vercel (Next.js frontend, always on)
- Supabase (all data — replaces local file reads)
- Cloudflare Tunnel (exposes Baz, IP stays private)
- VPS when traffic justifies
- MCP layer makes Baz domain-agnostic for sports + crypto

**Pre-launch blocker:** API routes currently read local files (`data/` directory). These must move to Supabase before Vercel deployment works. This is the main pre-launch session needed.

## Pending
- **NRL R12 reprice:** run `scripts/run_nrl_pricing.ps1` after refs announced Wednesday 14:00
- BVI weekly task: install Task Scheduler entry for `afl_bvi.py` Monday 08:00
- AFL R10 data gap: never priced — no retroactive fix needed, just ensure pipeline runs every round
- AFL totals model review: systematically over-pricing totals (both AFL and NRL)
- Pre-launch SaaS: migrate local data files to Supabase
- MCP server build (medium-term — after AFL automation stable)
