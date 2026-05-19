# BetMate + BettingEngine — Full Architecture Map
**Generated:** 2026-05-15

---

## Overview

Two tightly coupled projects:
- **BetMate** — Next.js frontend. Data scraping, live odds UI, Baz chat interface.
- **BettingEngine** — Python pricing engine. 7-tier model, SQLite DB, signal generation.

BetMate feeds BettingEngine. BettingEngine feeds Baz.

---

## BetMate — Directory Structure

```
Apps/
├── app/
│   ├── api/
│   │   ├── afl-bvi/            Serves latest-bvi.json to AFL odds page
│   │   ├── chat/               Baz chat — calls Anthropic API + local BettingEngine context
│   │   ├── ev-signals/         EV signal generation endpoint
│   │   ├── odds/
│   │   │   ├── nrl/            NRL odds from The Odds API (server-side cache)
│   │   │   ├── afl/            AFL odds from The Odds API
│   │   │   └── opening/        Opening price tracking
│   │   └── weather/            Tomorrow.io proxy (1hr server cache) + ping logger
│   ├── odds/                   Main odds board (NRL + AFL tabs, 10 bookmakers)
│   ├── research/               Baz Results page — bet history, CLV, ROI
│   └── tools/                  Tools suite
│
├── components/
│   ├── layout/Header.tsx       Navigation
│   ├── odds/GameCard.tsx       Game card — prices, weather, movement chips, tooltip
│   ├── odds/OddsBoardCard.tsx  Weather + EV wrapper
│   ├── chat/ChatPanel.tsx      Baz chat UI (localStorage history)
│   └── home/LiveOddsPreview.tsx  Landing page odds preview
│
├── lib/
│   ├── scraper/                Python scrapers (run via uv, Task Scheduler)
│   │   ├── odds_snapshot.py    The Odds API → data/odds_snapshots/ (09:00 + 18:00)
│   │   ├── odds_movement_tracker.py  Diffs last 2 snapshots → data/odds_movements/
│   │   ├── nrl_injuries.py     NRL.com casualty ward → data/nrl/injuries/
│   │   ├── nrl_fixture.py      NRL fixture → data/nrl/fixture/
│   │   ├── nrl_style_stats.py  Team styles → data/nrl/style-stats/
│   │   ├── nrl_emotional.py    Team sentiment → data/nrl/emotional/
│   │   ├── nrl_referees.py     Referee assignments → data/nrl/referees/
│   │   ├── nrl_historical_results.py  aussportsbetting.com xlsx → data/nrl/historical/
│   │   └── afl_bvi.py          aussportstipping.com BVI → data/afl/bvi/
│   │
│   ├── teams.ts                NRL + AFL team metadata (must match Odds API names exactly)
│   ├── venues.ts               NRL venue → lat/lng (for weather)
│   ├── aflVenues.ts            AFL venue → lat/lng
│   ├── oddsApi.ts              The Odds API wrapper + BOOKMAKER_META (10 books + Betfair adj)
│   ├── researchData.ts         LEGACY_BETS + MODEL_BETS for research page
│   └── matrixEV.ts             EV matrix calculations
│
├── scripts/
│   ├── install_odds_snapshot_task.ps1   Task Scheduler: 09:00 + 12:00 + 18:00, retry x2
│   ├── run_odds_snapshot_cycle.ps1      Wrapper: snapshot → movement tracker → toast on fail
│   ├── install_nrl_referees_task.ps1    Task: Tue 14:00 + 17:00
│   ├── install_nrl_emotional_task.ps1   Task: Tue 11:00
│   ├── market_hammered_drift.py         H2H/handicap drift ≥15% analysis (3 seasons)
│   ├── shortened_team_roi.py            ROI of backing shortened side by team
│   └── market_wrong_underdogs.py        Underdog calibration by team
│
├── data/
│   ├── odds_snapshots/YYYY/YYYY-MM-DD.csv    Daily odds (all books, all markets)
│   ├── odds_movements/YYYY/YYYY-MM-DD.csv    Intraday price changes
│   ├── nrl/
│   │   ├── fixture/processed/latest-fixture.json
│   │   ├── injuries/processed/latest-injuries.json  ← BettingEngine reads this
│   │   ├── style-stats/processed/latest-style-stats.csv  ← BettingEngine reads this
│   │   ├── emotional/processed/latest-emotional.json  ← BettingEngine reads this
│   │   ├── referees/processed/latest-referees.csv  ← BettingEngine reads this
│   │   └── historical/latest.xlsx  ← BettingEngine ELO rebuild
│   ├── afl/bvi/processed/latest-bvi.json
│   └── weather/YYYY/YYYY-MM-DD.csv
│
└── .env.local
    ODDS_API_KEY
    NEXT_PUBLIC_SUPABASE_URL / NEXT_PUBLIC_SUPABASE_ANON_KEY
    TOMORROW_API_KEY
    BAZ_LOCAL_API=http://localhost:8765    ← BettingEngine local context server
```

---

## Task Scheduler — Tuesday Pipeline

| Time  | Task | Script | Output |
|-------|------|--------|--------|
| 09:00 | Odds Snapshot | `run_odds_snapshot_cycle.ps1` | `data/odds_snapshots/` |
| 10:00 | NRL Injuries | `nrl_injuries.py` | `data/nrl/injuries/` |
| 11:00 | NRL Emotional | `nrl_emotional.py` | `data/nrl/emotional/` |
| 12:00 | Odds Snapshot | `run_odds_snapshot_cycle.ps1` | `data/odds_snapshots/` |
| 14:00 | NRL Referees | `nrl_referees.py` | `data/nrl/referees/` |
| 17:00 | NRL Historical | `nrl_historical_results.py` | `data/nrl/historical/` |
| 17:00 | NRL Referees | `nrl_referees.py` | `data/nrl/referees/` |
| 18:00 | NRL Style Stats | `nrl_style_stats.py` | `data/nrl/style-stats/` |
| 18:00 | Odds Snapshot | `run_odds_snapshot_cycle.ps1` | `data/odds_snapshots/` |
| 18:05 | NRL Round Prep | `nrl_round_prep.py` | fixture + injuries + referees |
| 19:03 | **BettingEngine Pricing** | `prepare_round.py` | `results/rN_pricing_YYYY.csv` |

---

## BettingEngine — Directory Structure

```
BettingEngine/
├── scripts/
│   ├── prepare_round.py         MAIN PIPELINE — orchestrates all tiers, outputs signals
│   ├── fetch_nrl_results.py     Monday 09:00 — scrapes NRL API scores → DB
│   ├── betmate_import_round.py  Ingests BetMate files into DB with validation
│   ├── nrl_weekly_clv_report.py  Post-round CLV (profit, ROI, Sharpe)
│   ├── nrl_h2h_matrix.py        H2H EV matrix → outputs/nrl_h2h_matrix.xlsx
│   ├── nrl_handicap_matrix.py   Handicap EV matrix
│   ├── afl_weekly_ml_clv_report.py  AFL CLV report
│   └── baz_server.py            ← LOCAL CONTEXT API (see Baz Agent section)
│
├── pricing/
│   ├── engine.py                Orchestrator — calls T1→T8 in sequence
│   ├── tier1_baseline.py        ELO + team strength + form + home advantage
│   ├── tier2_matchup.py         Style interactions + coach H2H
│   ├── tier3_situational.py     Bye, turnaround, bounce-back
│   ├── tier4_venue.py           Fortress venues + travel fatigue
│   ├── tier5_injury.py          Key outs + spine disruption + replacement quality
│   ├── tier6_referee.py         Penalty buckets + set restarts + scoring environment
│   ├── tier7_emotional.py       Team confidence + news sentiment
│   ├── tier8_weather.py         Temperature + wind + precipitation
│   └── afl_tier*.py             AFL variants of each tier
│
├── config/
│   ├── settings.yaml            Active sport, DB path, logging
│   ├── pricing.yaml             EV threshold (20%), Kelly fraction (1/4), stake caps
│   ├── kelly.yaml               Staking rules
│   ├── tiers.yaml               Per-tier weights + toggles (granular)
│   ├── bookmakers.yaml          Bookmaker codes + priority ranks
│   └── baz_agent.yaml           Baz agent config (tools, context depth, sport scope)
│
├── data/
│   ├── model.db                 CANONICAL DATABASE (SQLite)
│   ├── bets/actual_bets_2026.csv  Manual bet log
│   └── import/betmate/rN_YYYY/  BetMate import snapshots per round
│
├── db/
│   ├── schema.sql               Full schema (20+ tables)
│   ├── migrations/001-023_*.sql  Version-controlled DDL
│   └── connection.py            SQLite connection + init
│
└── outputs/
    ├── results/rN_pricing_YYYY.csv   Model prices + EV% + Kelly per match
    ├── nrl_h2h_matrix.xlsx
    ├── nrl_handicap_matrix.xlsx
    ├── afl_h2h_matrix.xlsx
    └── baz/latest_learning_review.json
```

---

## 7-Tier Pricing Model

```
BetMate Input Data
    │
    ├── Injuries (T5)  — data/nrl/injuries/processed/latest-injuries.json
    ├── Style Stats (T2) — data/nrl/style-stats/processed/latest-style-stats.csv
    ├── Emotional (T7) — data/nrl/emotional/processed/latest-emotional.json
    ├── Referees (T6)  — data/nrl/referees/processed/latest-referees.csv
    └── Historical (T1) — data/nrl/historical/latest.xlsx
                │
                ▼
    prepare_round.py
        T1: Baseline — ELO × form × home advantage → expected points
        T2: Matchup  — style interaction adjustment
        T3: Situational — bye/turnaround modifier
        T4: Venue    — fortress/travel adjustment
        T5: Injury   — key out penalty per importance tier
        T6: Referee  — penalty bucket scoring environment shift
        T7: Emotional — confidence/sentiment modifier (bounded)
        T8: Weather  — wind/rain/temperature adjustment
                │
                ▼
    Expected Points (Home + Away)
        → Margin = Home − Away
        → Totals = Home + Away
        → H2H probability → model odds
                │
                ▼
    Compare to market (The Odds API)
    EV = (model_prob × market_odds) − 1
                │
                ▼
    Signal if EV ≥ 20% + no hard veto
    → results/rN_pricing_YYYY.csv
    → Human reviews → places bet manually
    → Logs to data/bets/actual_bets_2026.csv
                │
                ▼
    After round: CLV report
    CLV = actual_close_odds − signal_odds
```

---

## Data Hand-off: BetMate → BettingEngine

| Data | BetMate writes | BettingEngine reads | Tier |
|------|---------------|--------------------|----|
| Fixture | `data/nrl/fixture/processed/latest-fixture.json` | `prepare_round.py → betmate_latest_fixture()` | All |
| Injuries | `data/nrl/injuries/processed/latest-injuries.json` | T5 | T5 |
| Style Stats | `data/nrl/style-stats/processed/latest-style-stats.csv` | T2 | T2 |
| Emotional | `data/nrl/emotional/processed/latest-emotional.json` | T7 | T7 |
| Referees | `data/nrl/referees/processed/latest-referees.csv` | T6 | T6 |
| Historical xlsx | `data/nrl/historical/latest.xlsx` | ELO rebuild | T1 |

---

## External Dependencies

| Service | Key | Used by |
|---------|-----|---------|
| The Odds API | `ODDS_API_KEY` | `odds_snapshot.py` + Next.js API routes |
| Tomorrow.io | `TOMORROW_API_KEY` | `app/api/weather/route.ts` |
| Supabase | `NEXT_PUBLIC_SUPABASE_*` | Auth (login/sessions) |
| Anthropic API | `ANTHROPIC_API_KEY` | `app/api/chat/route.ts` (Baz chat) |

---

## Baz Agent Architecture

See: `handover/baz_agent_architecture.md`
