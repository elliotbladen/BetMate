# Session Handover — 2026-06-04
## AFL Model Predictions — Automation + R13 Live

---

### What Was Done

#### AFL model scores now live on the board (R13)
`data/afl/predictions/latest.json` written and pushed to Supabase `afl_predictions`.
AFL tab on odds board now shows model scores on every game card (same as NRL).

| Game | Home Score | Away Score |
|------|-----------|-----------|
| Adelaide Crows vs Geelong Cats | 91.3 | 97.9 |
| Hawthorn Hawks vs Western Bulldogs | 104.4 | 65.7 |
| Gold Coast Suns vs Brisbane Lions | 92.2 | 84.2 |
| North Melbourne vs Fremantle | 79.1 | 106.0 |
| West Coast Eagles vs Port Adelaide | 60.5 | 86.0 |
| Essendon Bombers vs Carlton Blues | 69.3 | 91.2 |
| Sydney Swans vs St Kilda Saints | 124.5 | 70.1 |
| Collingwood Magpies vs Melbourne | 101.6 | 80.2 |

Scores derived from rules model: `home = (rules_total + rules_margin) / 2`

---

### New Files

| File | Purpose |
|------|---------|
| `scripts/push_afl_predictions.py` | Reads latest `r{N}_afl_2026.csv`, derives scores, writes JSON + Supabase |
| `scripts/run_push_afl_predictions.ps1` | PowerShell wrapper (sets env vars, runs via uv) |
| `scripts/install_nrl_predictions_task.ps1` | Task Scheduler installer for NRL (reference) |
| `app/api/afl-predictions/route.ts` | API route — Supabase first, local file fallback |
| `data/afl/predictions/latest.json` | AFL predictions JSON (auto-updated Thursday) |

### Modified Files

| File | Change |
|------|--------|
| `app/odds/page.tsx` | Added `aflPredictions` state + `/api/afl-predictions` fetch + passed to OddsBoard |

---

### Round Detection Logic (AFL)
No fixture JSON exists for AFL (unlike NRL). Instead:
- Finds all `r{N}_afl_{season}.csv` files in `BettingEngine/results/`
- Picks highest N by regex on filename — robust, not mtime-based

---

### Task Scheduler
- **Task:** "BetMate AFL Predictions Push"
- **Schedule:** Every Thursday at 09:00 (same time as NRL)
- **Next run:** 2026-06-11 09:00
- **Reinstall:** `scripts/install_nrl_predictions_task.ps1` (NRL) — create AFL equivalent if needed

---

### How to Run Manually
```powershell
cd C:\Users\ElliotBladen\Apps
$env:BETMATE_ROOT="C:\Users\ElliotBladen\Apps"; $env:PYTHONUTF8="1"
& C:\Users\ElliotBladen\.local\bin\uv.exe run --with requests python scripts\push_afl_predictions.py
```
