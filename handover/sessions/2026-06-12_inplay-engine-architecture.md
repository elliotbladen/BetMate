# Session Diary — 2026-06-12: InPlayEngine Architecture + Betfair Setup

## What Was Done

### 1. Closing Price Fills (ids 19–26) — carried from previous session
All MODEL_BETS entries in `lib/researchData.ts` now have `closingPrice` filled.
Id 26 ("St George vs Penrith") used the May 17 game's closing price of 9.50 (CLV = -80%).

### 2. NRL Origin Comeback Analysis — carried from previous session
`scripts/origin_comeback_analysis.py` — scrapes NRL match centre for HT+FT scores across Origin window (Jun–Jul) 2023–2026.
Key finding: Away team down 9–10 at HT = 0/6 wins. Home team down 1–4 = 52% comeback.

### 3. InPlayEngine Architecture — this session

#### What was built
Full multi-sport in-play pricing framework:

**Directory: `InPlayEngine/`** (alongside BettingEngine)
```
InPlayEngine/
├── pyproject.toml
├── inplay_engine/              ← Python package
│   ├── core/
│   │   ├── exchange.py         Betfair CSV loader (sport-agnostic)
│   │   └── halftime.py         HT price extraction at kickoff+offset
│   ├── sports/
│   │   ├── nrl/
│   │   │   ├── config.py       NRL: halftime=2400s, betfair URLs, scoring
│   │   │   └── features.py     Feature engineering for HT pricing model
│   │   ├── afl/
│   │   │   └── config.py       AFL: halftime=3900s (wider window)
│   │   └── _template/
│   │       └── config.py       Copy this when adding EPL/NBA/etc
│   └── data/
│       ├── downloaders/
│       │   └── betfair.py      Download Betfair CSVs by sport + year
│       └── processors/
│           └── extract_halftime.py  Raw CSV → halftime_prices_{year}.csv
├── models/                     Model artifacts (gitignored)
├── outputs/                    Analysis outputs (gitignored)
└── scripts/
    ├── download_betfair_nrl.py   Entry: download NRL 2022–2026
    └── build_halftime_dataset.py Entry: extract + feature-engineer
```

**Directory: `data/inplay/`** (under existing data/)
```
data/inplay/
├── nrl/
│   ├── betfair/raw/2022..2026/ ← Betfair CSVs land here
│   ├── halftime/extracted/     ← halftime_prices_{year}.csv
│   ├── halftime/processed/     ← halftime_dataset.csv (model-ready)
│   └── live_snapshots/         ← future: real-time 45min captures
├── afl/ (same structure)
└── _schema/
    ├── betfair_match_odds.md   Column reference for raw CSVs
    └── halftime_prices.md      Column reference for processed output
```

#### Design decisions
- **src-layout:** `InPlayEngine/inplay_engine/` is the importable package, `InPlayEngine/` is the project directory. Scripts use `sys.path.insert(0, REPO_ROOT / "InPlayEngine")` then `from inplay_engine.x import ...`
- **Sport-agnostic core:** `exchange.py` and `halftime.py` have zero sport-specific logic — timing passed in from SportConfig
- **Sport configs are frozen dataclasses:** all constants in one place per sport, easy to add a new sport in < 10 min
- **`_template/`:** copy when adding EPL, NBA, NFL, T20 cricket etc.

#### Betfair data source confirmed
URL: `https://betfair-datascientists.github.io/assets/NRL_{YEAR}_Match_Odds.csv`
Years available: 2021–2026. We download 2022+ only (skip COVID-disrupted 2021).
CSV columns: market_id, inplay, selection, last_price_traded, publish_time, ex_best_back_1..3, ex_best_lay_1..3

## Next Steps

1. **Download the data:** Run `uv run --with requests python InPlayEngine/scripts/download_betfair_nrl.py`
   - Will pull ~5 CSVs into `data/inplay/nrl/betfair/raw/`
2. **Extract halftime prices:** Run `uv run python InPlayEngine/scripts/build_halftime_dataset.py --sport nrl`
   - Produces `data/inplay/nrl/halftime/processed/halftime_dataset.csv`
3. **Join with HT scores from origin_comeback_analysis** — merge on kickoff date + teams to get: HT score diff + HT exchange price → did the trailing team win?
4. **Build halftime pricing model** — logistic regression or XGBoost on (score_diff, ht_price_impl_prob, home/away) → P(win)
5. **Wire live snapshot** — add 45-min-post-kickoff capture to OddsBoardCard for upcoming games

## Important Notes
- `last_price_traded` can be NaN if no exchange trades in that interval → fall back to `ex_best_back_1`
- AFL halftime window is wider (8 min) due to variable time-on across quarters
- `data/inplay/` is gitignored (covered by existing `data/` rule)
- `InPlayEngine/models/` and `InPlayEngine/outputs/` explicitly gitignored
