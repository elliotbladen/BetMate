# Handover — 2026-05-27 — Emotional scrapers fixed (AFL + NRL)

## What happened

### AFL emotional scraper (`scrapers/afl_emotional.py`)
Fixed 3 root causes that were preventing R12 flags from firing:

1. **`ANTHROPIC_API_KEY` not loading** — added `_load_env()` at module level, reads from `.env.local`
2. **No news feed** — added `fetch_afl_news()` using Google News RSS (3 queries, up to 30 headlines)
3. **Fixture timing** — task was running at 14:30, before round prep at 16:20. Rescheduled to 16:45.
4. **Bye-team validation** — added `playing_teams` set built from fixture; `validate_flag()` now rejects flags for teams not playing (e.g. Adelaide Crows on bye)

Fired manually for R12. Result: 1 flag — `Essendon Bombers | new_coach | normal`
This is correct: Mark Harvey appointed after Brad Scott's sacking.

### NRL emotional scraper (`scrapers/nrl_emotional.py`)
Applied identical fixes:

1. **`_load_env()`** — added at module level (after ROOT/BASE_DIR definitions)
2. **`fetch_nrl_news()`** — Google News RSS, NRL-specific queries
3. **`build_claude_prompt()`** — now accepts `news_headlines` param, included in prompt
4. **`validate_flag()`** — now accepts `playing_teams: set[str] | None`, rejects bye-team flags
5. **`run()`** — builds `playing_teams` from fixture games; fetches news before Claude call
6. **Task rescheduled** — "BetMate NRL Emotional Flags" moved from 14:00 → 16:45 Tuesday

Fired manually for R13. Result: 1 flag — `Melbourne Storm | rivalry_derby | normal` (Storm vs Roosters)
Claude returned [] for additional flags — correct given no major storylines in R13 news feed.

## Pipeline order (Tuesday) — now correct
```
10:00  NRL Injuries
10:30  NRL Team News
11:30  AFL Injuries
16:00  NRL Historical Results (+ AFL download)
16:15  NRL Style Stats / AFL Style Stats
16:20  NRL Round Prep / AFL Round Prep  ← fixture CSVs written here
16:40  BettingEngine NRL Pricing
16:45  NRL Emotional Flags  ← AFTER round prep ✅
16:45  AFL Emotional Flags  ← AFTER round prep ✅
```

## Output files
- `data/nrl/emotional/processed/latest-emotional.json` — now exists, R13, 1 flag
- `data/nrl/emotional/processed/2026/round-13.json` — validated flags
- `data/nrl/emotional/raw/2026/round-13.json` — raw API + prompt
- `data/afl/emotional/processed/latest-emotional.json` — R12, 1 flag (Essendon new_coach)

## Pending
- **Reprice AFL R12** with Essendon new_coach flag loaded into T7. Current pricing in `BettingEngine/results/r12_afl_2026.csv` was run before this flag existed.
- AFL fixture CSV for R13 will need to be written manually next week (same as R12 — `prepare_afl_round.py` reads but doesn't write the fixture CSV)
- Fixture CSV path: `BettingEngine/outputs/afl_round_prep/r{NN}_{YYYY}/fixture_r{NN}_{YYYY}.csv`
