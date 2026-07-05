# Session: Fix NRL Injury Scraper + R10 Repricing with T5
**Date:** 2026-05-05
**Goal:** Fix broken injury scraper (Fox Sports URL returning motorsport page), re-price R10 with live injury data.

---

## Problem Found

`BetMate/lib/scraper/nrl_injuries.py` targeted `https://www.foxsports.com.au/nrl/injury-list`.
Fox Sports changed their site — the URL now redirects to a motorsport page. Scraper returned 0 records.

---

## Fix Applied

**New source:** NRL.com casualty ward article (server-rendered HTML, no JS required):
```
https://www.nrl.com/news/{season}/01/01/nrl-casualty-ward-how-your-club-is-shaping-heading-into-{season}/
```

URL is computed from season year — automatically correct for 2027, 2028, etc.

**HTML structure (actual, not guessed):**
```html
<h3><a id="Broncos"></a>Brisbane Broncos</h3>
<ul>
  <li>Adam Reynolds (head knock, TBC)</li>
  <li>Preston Riki (suspended, Round 10)</li>
</ul>
```

**Parser changes:**
- Old format expected: `Player: Injury | Return` (Fox Sports table rows)
- New format: `Player (injury description, Round N or TBC)` (NRL.com casualty ward li items)
- TEAM_MAP: added `"cronulla sharks"` and `"st george illawarra dragons"` (no period) to match NRL.com h3 heading text

**Status logic:**
- `TBC` or `Indefinite` → `"out"`
- `Round N` where N < current round → skip (already returned)
- `Round N` where N == current round → `"doubtful"`
- `Round N` where N > current round → `"out"`

---

## R10 Injury Data — SCRAPED

103 records across all 17 teams, 82 out / 21 doubtful.

Key elite/key players out for R10:
| Player | Team | Status | Injury |
|--------|------|--------|--------|
| Adam Reynolds | Brisbane Broncos | out | Head knock |
| Ben Hunt | Brisbane Broncos | out | Knee (Round 12-14) |
| Tom Trbojevic | Manly-Warringah Sea Eagles | out | Hamstring (Round 13-15) |
| Jake Turpin | Canterbury-Bankstown Bulldogs | out | Biceps |

---

## R10 Repriced with T5 (Injuries)

Re-ran `prepare_round.py --round 10 --season 2026`. 94 of 103 injury records loaded (9 Warriors skipped — Warriors on bye R10, no match).

| Game | T5 adj | Final margin | H2H home | Notes |
|------|--------|-------------|----------|-------|
| Dolphins vs Canterbury | +3.0 | +10.2 | 1.25 | Bulldogs depleted |
| Sydney Roosters vs Gold Coast | -2.0 | +7.5 | 1.36 | Roosters outs |
| NQ Cowboys vs Parramatta | +2.5 | +14.9 | 1.12 | Eels depleted |
| St George vs Newcastle | -3.0 | -3.3 | 2.55 | Dragons 10 players out |
| South Sydney vs Cronulla | -1.8 | +1.7 | 1.79 | Souths outs |
| Manly vs Brisbane | +3.0 | +6.6 | 1.42 | Reynolds + Hunt both out |
| Melbourne vs Wests Tigers | +0.2 | +7.7 | 1.35 | Near neutral |
| Canberra vs Penrith | -2.8 | -9.9 | 4.89 | Canberra outs |

T6 (referees) still zero — draw announced Wednesday.

---

## Monday Pipeline (final)

| Time | Task |
|------|------|
| 09:00 | fetch_nrl_results.py — scrapes last round results |
| 10:00 | nrl_injuries.py — scrapes NRL.com casualty ward |
| 17:00 | nrl_historical_results.py — downloads aussportsbetting xlsx |
| 18:00 | style stats scraper |
| 19:03 | prepare_round.py — prices upcoming round with T1-T7 |

---

## Still Pending

- **Wednesday:** Run `nrl_referees.py --round 10` after draw announced, re-run `prepare_round.py --round 10`
- **Magic Round (R11):** Re-price after R10 actuals load next Monday
- **Queensland Country Bank Stadium lat/lng:** Weather step skips Townsville — needs coordinates in venues table
- **AFL injury scraper:** No equivalent yet; AFL priced manually
- **BetMate UI polish:** User flagged but no specific request this session
