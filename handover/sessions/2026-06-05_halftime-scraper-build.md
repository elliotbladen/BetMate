# Session Diary — 2026-06-05 — NRL Half-Time Scraper

## What was done

Built the automated NRL half-time scraper. Investigated stat sources thoroughly before building.

### Data source investigation

- **Sofascore**: Free but no official API. Unofficial API documented for football/soccer only. Rugby league specific stats (inside-20 possessions, set restarts, errors) NOT confirmed available. Dropped.
- **Flashscore**: Similar — basic scores only, not granular enough.
- **Stats Perform**: Official NRL data provider. Complete data but paid/licensed.
- **NRL.com match centre**: Has ALL stats we need (inside-20, errors, set restarts, run metres, completion rate, set restarts). Free with NRL account. Requires Playwright to render (React app).

**Decision: NRL.com + Playwright.** User created NRL account. Credentials in `.env.local`.

### NRL draw API findings (confirmed live)

```json
{
  "matchState": "FullTime",   // "HalfTime" during half time
  "matchCentreUrl": "/draw/nrl-premiership/2026/round-14/sea-eagles-v-rabbitohs/",
  "clock": { "gameTime": "80:00" },  // "40:00" at half time
  "homeTeam": { "nickName": "Sea Eagles", "score": 28 },
  "awayTeam": { "nickName": "Rabbitohs", "score": 14 }
}
```

Half-time detection: `matchState == "HalfTime"` OR `gameTime ≈ "40:00"` + live state.

### Files built

**`scrapers/nrl_halftime_scraper.py`** (NEW — replaces deleted `nrl_halftime_stats.py`)
- Polls NRL draw API → detects half-time games via `matchState`
- Playwright (headless Chrome) logs into NRL.com using `.env.local` credentials
- Saves browser session to `data/nrl/halfTime/.nrl_session.json` after first login (reused on subsequent runs — no re-login each time)
- Navigates to match centre → clicks Stats tab → extracts stats table
- 4-strategy extraction: class pattern → table rows → definition lists → full text parse
- Maps NRL.com stat labels → HalfTimeStats fields via `STAT_MAP` (20+ label variants)
- Saves: `data/nrl/halfTime/R{nn}/YYYY-MM-DD_{home}_vs_{away}_stats.json`
- Auto-triggers `halfTime_price_nrl.py` after each game scraped
- `--debug` flag saves screenshots + page text for field name investigation

**Deleted**: `scrapers/nrl_halftime_stats.py` (manual entry, superseded)

### Credentials stored

```
# .env.local
NRL_EMAIL=elliotbladen@gmail.com
NRL_PASSWORD=Parklife0912
```

**NOTE:** User should change NRL password at a convenient time — was shared in chat session.

---

## First run instructions

```powershell
# Install playwright browsers (one-time)
& C:\Users\ElliotBladen\.local\bin\uv.exe run playwright install chromium

# Run during a live game at half time
$env:BETMATE_ROOT = "C:\Users\ElliotBladen\Apps"
& C:\Users\ElliotBladen\.local\bin\uv.exe run python scrapers\nrl_halftime_scraper.py --round 14

# First time debugging (saves screenshots to data/nrl/halfTime/)
& C:\Users\ElliotBladen\.local\bin\uv.exe run python scrapers\nrl_halftime_scraper.py --round 14 --debug

# Force run (ignores half-time check — for testing outside game)
& C:\Users\ElliotBladen\.local\bin\uv.exe run python scrapers\nrl_halftime_scraper.py --round 14 --force --debug

# Clear saved session and re-login
& C:\Users\ElliotBladen\.local\bin\uv.exe run python scrapers\nrl_halftime_scraper.py --round 14 --clear-session
```

---

## What needs live testing

1. **NRL.com stat tab selector** — need to confirm which Playwright selector hits the Stats tab. Run `--debug` during a live game to see screenshots.
2. **Stat label names** — the `STAT_MAP` covers 20+ variants but exact NRL.com labels need confirming. The scraper logs `Discovered stat labels: [...]` — check this output on first run.
3. **Inside-20 field name** — this is the key ETxP stat. Might be "Tackles Inside 20", "Inside 20m", "20m Tackles" etc.
4. **Session persistence** — session file at `.nrl_session.json` should survive multiple runs. If login fails, run with `--clear-session`.

---

## Pending

- Matrix (`halfTime_matrix_nrl.py`) — build later per user decision
- AFL version — build next week
- Calibration log filling — happens post-game, once first predictions are logged
- Phase 2 (BetMate integration) — after model is proven
