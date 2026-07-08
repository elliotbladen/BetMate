# Session Diary — 2026-06-25: NRL R17 Full Pricing + WC R32 Monte Carlo

## What happened this session

### World Cup 2026 — R32 Bracket Monte Carlo
- User shared bracket image `a.png` showing actual R32 matchups after group stage
- Filled `WorldCupEngine/data/bracket.py` with all 32 actual teams in correct slot positions
- Applied R3 ELO updates to `WorldCupEngine/data/elo_ratings.py` based on bracket-implied results:
  - Scotland beat Brazil (+31/-31)
  - Sweden beat Japan (+19/-19)
  - Iran beat Egypt est. (+20/-20, both qualified from Group G)
- Ran 100,000-sim Monte Carlo — results:
  - Argentina 38.8% SF / 25.5% Final / 16.6% WIN
  - Spain 33.7% SF / 18.6% Final / 10.1% WIN
  - France 26.2% SF / 17.3% Final / 10.0% WIN (hardest section)
  - England 21.7% / 12.0% / 6.9%
  - Brazil 20.4% / 10.5% / 5.5% (knocked down by Scotland loss)
  - USA 19.5% / 8.6% / 3.7%
- Note: Colombia vs DR Congo (Group K R2, Jun 24 UTC) ELO was estimated — confirm actual result

### NRL R17 Full Pricing (T1–T10)
**Context:** Thursday pricing run. Refs not yet scraped. Had to find refs manually.

**Step 1 — Emotional scraper run:**
```
uv run --with requests --with beautifulsoup4 --with anthropic python scrapers/nrl_emotional.py --round 17
```
Flags returned:
- Brisbane Broncos: rivalry_derby (vs Roosters)
- Parramatta Eels: milestone (Mitchell Moses)

**Step 2 — Referee search:**
NRL.com match-centre scraper returned empty (no refs posted yet). Used WebSearch:
- ESPN article had full R17 ref table
- Confirmed by rugbyleaguezone.com
All 8 assignments confirmed:
- Parramatta/Souths: Gerard Sutton
- Gold Coast/Bulldogs: Todd Smith
- Brisbane/Roosters: Grant Atkins
- Dolphins/Warriors: Adam Gee
- Cowboys/Panthers: Wyatt Raymond
- Manly/Storm: Ashley Klein
- Raiders/Dragons: Ziggy Przeklasa-Adamski
- Knights/Tigers: Peter Gough

**Step 3 — Manual ref load:**
Created `BettingEngine/scripts/_load_r17_refs.py` — keyword-matches R17 games in DB, finds referee_id, upserts to `weekly_ref_assignments`. All 8/8 loaded with scoring_delta and home_bias_adj confirmed.

**Step 4 — Full pricing run:**
```
cd C:\Users\ElliotBladen\Apps\BettingEngine
$env:BETMATE_ROOT = "C:\Users\ElliotBladen\Apps"; $env:PYTHONUTF8 = "1"
& ".\scripts\run_nrl_pricing.ps1"
```
Note: Step 5 in output shows "0/6 refs loaded" from stale CSV but T6 Referee check confirms all 8 refs applied correctly from `weekly_ref_assignments` DB table. Prices are correct.

**Step 5 — T9 Matrix confluence:**
```
.\.venv\Scripts\python.exe scripts\matrix_confluence.py --season 2026 --round 17 --min-edges 1 --min-edge-pct 0
```

## Final R17 Prices

| Game | Model Margin | Totals | Referee |
|------|-------------|--------|---------|
| Parramatta vs Souths | Souths −10.3 | 53.7 | Gerard Sutton (whistle, -3.1 Eels hcap, -1.1 tot) |
| Gold Coast vs Bulldogs | Bulldogs −4.5 | 35.7 | Todd Smith (neutral) |
| Brisbane vs Roosters | Roosters −3.1 | 45.9 | Grant Atkins (neutral) |
| Dolphins vs Warriors | Dolphins +6.5 | 49.4 | Adam Gee (neutral) |
| Cowboys vs Panthers | Panthers −21.3 | 51.9 | Wyatt Raymond (flow, +3.1 tot) |
| Manly vs Storm | Manly +13.1 | 45.9 | Ashley Klein (whistle, +3.2 Manly hcap, -1.2 tot) |
| Raiders vs Dragons | Raiders +15.7 | 46.5 | Ziggy Przeklasa-Adamski (neutral) |
| Knights vs Tigers | Knights +7.5 | 60.3 | Peter Gough (flow, +1.0 tot) |

## Key Bet Signals

**Tier A (model + matrix aligned):**
1. Manly H2H / cover (-13.1) — T1+T2+T3+T4+T6 all Manly, Ashley Klein +3.2, 11-way matrix HOME COVERS + 7-way H2H
2. Newcastle H2H / cover (-7.5) — Tigers missing 7 players, 14-way handicap matrix, 10-way H2H, total 60.3 if market ~54
3. Bulldogs H2H / cover (-4.5) — 9-way H2H + 9-way handicap both Canterbury, model -4.5

**Tier B (strong model, partial matrix):**
4. Roosters H2H — 10-way H2H BACK ROOSTERS, Broncos missing Reynolds (elite) + 7 rotation
5. Cowboys/Panthers OVER 51.9 — if market ≤50, Wyatt Raymond 3.1pt gap

**Notable for research:**
- Raiders vs Dragons: H2H strongly Raiders but handicap matrix 10-way Dragons cover (small spread vs big model gap)

## Pending
- G3 Origin squad (Jul 8, camp Jul 3) needs populating in `data/nrl/origin/2026.json` before R18
- WC: confirm Colombia vs DR Congo actual result (estimated Colombia win in ELO)
- Run CLV scripts after R17 closes (Sunday)

## Files written
- `BettingEngine/results/r17_pricing_2026.csv` ✅
- `BettingEngine/outputs/nrl_t9_confluence_latest.json` ✅
- `BettingEngine/scripts/_load_r17_refs.py` ✅ (manual ref loader for R17)
- `WorldCupEngine/data/bracket.py` ✅ (full R32 teams)
- `WorldCupEngine/data/elo_ratings.py` ✅ (R3 ELO updates)
