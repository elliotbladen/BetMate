# Session Diary — 2026-05-28 — T7 Weather Wired to Tomorrow.io + Full-Tier Pricing

## What was done

### 1. Wired T7 weather to Tomorrow.io for both NRL and AFL

**NRL — `BettingEngine/scripts/fetch_weather.py`** (completed in previous session):
- Replaced Open-Meteo + MetService with Tomorrow.io
- `_fetch_tomorrow_io(lat, lng, kickoff_datetime)` — same endpoint as BetMate weather API
- windSpeed m/s → km/h conversion (×3.6)
- Reads `TOMORROW_API_KEY` from `C:\Users\ElliotBladen\Apps\.env.local`

**AFL — `BettingEngine/scripts/prepare_afl_round.py`** (done this session):
- Added `import urllib.request`
- Added `AFL_VENUE_COORDS` dict (15 venues from lib/aflVenues.ts)
- Added `_load_tomorrow_api_key_afl()` + `_fetch_afl_weather_tomorrow()` functions
- Modified T7 section: manual WEATHER dict entry takes precedence (explicit `{}` = Marvel roof closed); otherwise auto-fetches from Tomorrow.io on each pricing run
- Log line per game: `[T7] MCG: T=13.4°C W=18.0km/h P=0.0mm [tomorrow_io]`

**Fixed `prepare_round.py` import error:**
- `step6a_fetch_weather` was importing `AUCKLAND_VENUE_IDS` from `fetch_weather.py` — removed when MetService was deleted. Removed from import.

### 2. Ran NRL R13 weather fetch + full pricing

```powershell
& ".\.venv\Scripts\python.exe" scripts\fetch_weather.py --season 2026 --round 13
```
7/7 weather rows fetched. Key: Suncorp Stadium moderate_wind (20.2 km/h) → -2.0 on Broncos/Dragons total.

Full pricing via `run_nrl_pricing.ps1`:
- T5: 93 injury records loaded
- T6: 4/7 refs loaded (Gough flow+2, Atkins flow+2, Klein whistle-2, Sutton neutral)
- T8 weather: all 7 games from Tomorrow.io DB

CSV export failed with PermissionError (file locked — open in Excel). Fix: close Excel, run:
```powershell
$env:BETMATE_ROOT = "C:\Users\ElliotBladen\Apps"; $env:PYTHONUTF8 = "1"
& ".\.venv\Scripts\python.exe" scripts\export_round_csv.py --season 2026 --round 13
```

### 3. Ran AFL R12 full pricing

```powershell
$env:BETMATE_ROOT = "C:\Users\ElliotBladen\Apps"; $env:PYTHONUTF8 = "1"
& ".\.venv\Scripts\python.exe" scripts\prepare_afl_round.py --season 2026 --round 12
```
T7 weather auto-fetched for all 7 games. Only Optus Stadium fired: moderate_wind (25.6 km/h) → -2.8 on Eagles/Bombers total.

Key change from T6 emotional (Essendon new_coach_bounce): Eagles/Bombers hcap flipped from Eagles +2.0 → Bombers -0.5.

---

## NRL R13 Final Prices

| Game | Model Hcap | Market Hcap | Model Total | Market Total |
|------|-----------|-------------|-------------|--------------|
| **Cronulla** vs Manly | Sharks -4.9 | Sharks -2.5 | 52.8 | 50.5 |
| **Newcastle** vs Parramatta | Knights -12.7 | Knights -14.5 | 58.8 | 53.5 |
| **Wests Tigers** vs Bulldogs | Tigers -3.5 | Tigers -1.5 | 48.5 | 48.5 |
| Roosters vs **Melbourne** | Roosters -1.7 | Roosters -1.5 | 56.6 | 49.5 |
| **Brisbane** vs St George | Broncos -16.6 | Broncos -19.5 | **43.8** | 54.5 |
| **Canberra** vs Cowboys | Raiders -1.3 | Raiders -3.5 | 50.0 | 52.5 |
| **Penrith** vs Warriors | Panthers -12.7 | Panthers -7.5 | **44.1** | 48.5 |

### R13 Signals (finalised)
1. **Cronulla -2.5 — HIGH** (7-way matrix + model -4.9 vs -2.5)
2. **Panthers/Warriors UNDER 48.5 — HIGH** (8-way matrix + model 44.1)
3. **Broncos/Dragons UNDER 54.5 — HIGH** (model 43.8 with T8 wind, 10.7pt gap)
4. **Parramatta +14.5 — MEDIUM-HIGH** (model Knights 12.7 vs market 14.5 — gap narrowed after T5)
5. **Panthers -7.5 — MEDIUM** (model 12.7 vs market 7.5)

Missing refs: Cronulla/Manly (Todd Smith scraper mismatch), Newcastle/Parra (not assigned), Broncos/Dragons (Wyatt Raymond mismatch). Ref scraper match lookup needs name normalisation fix.

---

## AFL R12 Final Prices (full tiers)

| Game | Model Hcap | Market Hcap | Model Total | Market Total |
|------|-----------|-------------|-------------|--------------|
| St Kilda vs **Hawthorn** | Hawks -30.4 | Hawks -12.5 | 177.0 | 182.5 |
| Carlton vs **Geelong** | Cats -44.1 | Cats -23.5 | 187.0 | 179.5 |
| **Sydney** vs Richmond | Swans -95.6 | Swans -61.5 | 195.5 | 178.5 |
| **Brisbane** vs Fremantle | Lions -13.2 | Lions -6.5 | 185.0 | 182.5 |
| **Bulldogs** vs Collingwood | Bulldogs -2.0 | Bulldogs -7.5 | 160.5 | 180.5 |
| **Melbourne** vs GWS | Demons -15.2 | Demons -5.5 | 191.0 | 176.5 |
| West Coast vs **Essendon** | Bombers -0.5 | Bombers -10.5 | **149.0** | 165.5 |

### R12 AFL Signals (finalised)
1. **Collingwood +7.5 — HIGH** (Bulldogs ruck crisis, coin flip)
2. **Bulldogs/Magpies UNDER 180.5 — HIGH** (model 160.3)
3. **Eagles +10.5 — HIGH** (rules 0.5, ML 7.6, both well inside market)
4. **Eagles/Bombers UNDER 165.5 — MEDIUM** (upgraded: rules 149.0, ML 158.5 both below market — T5+T7 aligned)
5. **Carlton +23.5 — MEDIUM** (ML divergence: rules -44.1 vs ML -2.3)
6. **Geelong/Carlton OVER 179.5 — MEDIUM** (8-way Geelong matrix confluence)
7. **Hawks -12.5 — MEDIUM**

---

## Files Changed

| File | Change |
|------|--------|
| `BettingEngine/scripts/fetch_weather.py` | Tomorrow.io replaces Open-Meteo (prev session) |
| `BettingEngine/scripts/prepare_afl_round.py` | AFL_VENUE_COORDS + _fetch_afl_weather_tomorrow() + T7 auto-fetch |
| `BettingEngine/scripts/prepare_round.py` | Removed AUCKLAND_VENUE_IDS from import (no longer exists) |
| `BettingEngine/outputs/results/r13_nrl_pricing_2026.md` | Full-tier update with T5+T6+T7/T8 |
| `BettingEngine/outputs/results/r12_afl_pricing_2026.md` | T6 Essendon flag + T7 Optus weather + Eagles/Bombers flip |
| `Apps/CLAUDE.md` | Current state updated |

---

## Task Scheduler Fix Needed (carry-forward from prev session)

NRL ref scraper: 2 matches return "ERROR (match not found)":
- Cronulla/Manly: scraper sends "Cronulla Sutherland Sharks vs Manly Warringah Sea Eagles" but DB has "Cronulla-Sutherland Sharks" (with hyphens)
- Broncos/Dragons: scraper sends "Brisbane Broncos vs St George Illawarra Dragons" but DB has "St. George Illawarra Dragons"

Team name normalisation fix needed in the referee loader step in `prepare_round.py`. Not urgent — missing refs are safe for bet decisions (buffer exists in all relevant markets).

---

## Pending

- Close Excel and re-run `export_round_csv.py --season 2026 --round 13` (CSV locked)
- Marvel Stadium roof status for R12 games (3 games at Marvel). If roof confirmed closed on game day, add `{}` entries to WEATHER dict in `prepare_afl_round.py`.
- Sean Darcy (Fremantle) — confirm doubtful status before Brisbane/Fremantle bet
- AFL T6 umpires: no data source yet
