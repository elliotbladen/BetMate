# Session Handover — 2026-06-05
## AFL History Tab — Live

### What Was Done

Wired AFL match history into the BetMate history/form tab. Mirrors the existing NRL implementation.

---

### Data Flow

```
BettingEngine/outputs/afl_weekly_review/historical/latest.xlsx
  → scripts/push_afl_history.py  (normalise names + push)
    → Supabase betmate_data_store key: afl_match_history
      → app/api/form/route.ts?sport=AFL
        → HistoryTab in odds page
```

---

### Files Changed

| File | Change |
|------|--------|
| `app/api/form/route.ts` | Removed AFL "coming soon" early return. Added `historyKey` dynamic var — `afl_match_history` for AFL, `nrl_match_history` for NRL. |
| `scripts/push_afl_history.py` | NEW — reads xlsx (2022+), normalises all 18 AFL team names, pushes 961 matches to Supabase. |

---

### Critical: Team Name Normalisation

The AFL historical xlsx uses **short names** ("Hawthorn", "West Coast", "GWS Giants"). The Odds API uses **full mascot names** ("Hawthorn Hawks", "West Coast Eagles", "Greater Western Sydney Giants"). The form route's nickname matching uses the LAST WORD of the full name — so "Hawthorn" would never match "hawks".

The push script normalises via `AFL_TEAM_MAP` dict before pushing. All 18 teams verified. If this mapping ever breaks (e.g. new team name from Odds API), form tab silently returns empty — check this dict first.

---

### Data in Supabase

- **Key:** `afl_match_history`
- **Records:** 961 games (2022–2026-05-31)
- **Newest:** 2026-05-31 West Coast Eagles vs Essendon Bombers
- **Oldest:** 2022-03-16 Melbourne Demons vs Western Bulldogs

---

### Automation — INSTALLED ✅

**Task:** "BetMate AFL History Push"
**Schedule:** Every Tuesday at 12:00
**Next run:** 2026-06-09 12:00
**Wrapper:** `scripts/run_push_afl_history.ps1`
**Log:** `data/logs/afl_history_push.log`

Runs 30 minutes after "BettingEngine AusSportsBetting AFL Download" (11:30 Tuesday).
That download writes to `BettingEngine/outputs/afl_weekly_review/historical/latest.xlsx`
which is exactly what `push_afl_history.py` reads.

**Tuesday pipeline order (relevant tasks):**
```
11:30  BettingEngine AusSportsBetting AFL Download  ← downloads xlsx
12:00  BetMate AFL History Push                     ← pushes to Supabase
```

**Manual run:**
```powershell
cd C:\Users\ElliotBladen\Apps
& C:\Users\ElliotBladen\.local\bin\uv.exe run --with requests --with openpyxl python scripts\push_afl_history.py
```
