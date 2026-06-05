# Session Handover — 2026-06-04
## NRL Model Predictions — Automation + R14 Live

---

### What Was Done

#### Model scores now live on the board (R14)
`data/nrl/predictions/latest.json` updated with R14 scores and pushed to Supabase `nrl_predictions`. The odds board will show model scores on every game card.

| Game | Model |
|------|-------|
| Manly vs Souths | Manly 27.4 – 24.1 Souths |
| Melbourne vs Newcastle | Storm 27.0 – 26.4 Knights |
| Canberra vs Roosters | Raiders 22.2 – 25.9 Roosters |
| Cowboys vs Dolphins | Cowboys 22.7 – 26.4 Dolphins |
| Brisbane vs Gold Coast | Broncos 20.0 – 19.7 Titans |
| Wests vs Panthers | Tigers 14.7 – 31.7 Panthers |
| Cronulla vs Dragons | Sharks 35.0 – 18.3 Dragons |
| Bulldogs vs Parramatta | Bulldogs 30.2 – 20.6 Eels |

---

#### New script: `scripts/push_nrl_predictions.py`
Reads the current round's pricing CSV, converts team names to Odds API format, writes JSON, pushes to Supabase.

**Round detection logic (robust):**
1. **Primary** — reads `data/nrl/fixture/processed/latest-fixture.json` → gets `round` + `season` → looks for `r{round}_pricing_{season}.csv` directly. Updates automatically every Tuesday when fixture scraper runs.
2. **Fallback** — if fixture missing or CSV not found, picks highest round number by filename (not mtime — prevents stale edits corrupting it).

**Team name mapping** (BettingEngine CSV → Odds API):
- `Manly-Warringah Sea Eagles` → `Manly Warringah Sea Eagles`
- `Cronulla-Sutherland Sharks` → `Cronulla Sutherland Sharks`
- `Canterbury-Bankstown Bulldogs` → `Canterbury Bulldogs`
- `St. George Illawarra Dragons` → `St George Illawarra Dragons`

**Supabase push** uses same pattern as other scrapers (`data` column, `updated_at`, list-wrapped payload, `resolution=merge-duplicates`).

#### New wrapper: `scripts/run_push_nrl_predictions.ps1`
Sets `BETMATE_ROOT` + `PYTHONUTF8`, runs the script via uv.

#### New Task Scheduler task: "BetMate NRL Predictions Push"
- **Schedule:** Every Thursday at 09:00
- **Next run:** 2026-06-11 09:00
- **Script:** `scripts/run_push_nrl_predictions.ps1`
- **Installer:** `scripts/install_nrl_predictions_task.ps1`
- **Log:** `data/logs/nrl_predictions_task.log`

The task fires after pricing is always complete (pipeline runs Tue, refs re-price Wed, predictions push Thu 9am before markets open).

---

### API Route
`app/api/nrl-predictions/route.ts` — tries Supabase first (`nrl_predictions` key), falls back to local file. No changes needed to the route.

---

### How to Run Manually
```powershell
cd C:\Users\ElliotBladen\Apps
$env:BETMATE_ROOT="C:\Users\ElliotBladen\Apps"; $env:PYTHONUTF8="1"
& C:\Users\ElliotBladen\.local\bin\uv.exe run --with requests python scripts\push_nrl_predictions.py
```

---

### To Reinstall Task (if it disappears)
```powershell
& C:\Users\ElliotBladen\Apps\scripts\install_nrl_predictions_task.ps1
```
