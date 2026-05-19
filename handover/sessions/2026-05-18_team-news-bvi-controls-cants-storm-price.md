# Session 2026-05-18 — Team News, BVI/HA Controls, Canterbury vs Storm Price-Up

## What was done

### 1. Odds movement arrows
Confirmed arrows appear after the 2nd daily snapshot runs (need two snapshots to diff). Ran manual snapshot to seed the second one.

### 2. Team News system — built end to end
Created a real team news system for the BetMate odds page, covering fresh injuries and suspensions from the weekend's games only (not pre-existing absences).

**Files created:**
- `data/nrl/team-news/latest.json` — NRL R12 fresh news (3 teams: Rabbitohs, Wests Tigers, Manly)
- `data/afl/team-news/latest.json` — AFL R11 fresh news (3 teams: Richmond, West Coast, Gold Coast)
- `app/api/team-news/nrl/route.ts` — API route serving NRL team news
- `app/api/team-news/afl/route.ts` — API route serving AFL team news

**Middleware:** Added `/api/team-news` to PUBLIC_PATHS (was returning 401 without auth).

**NRL R12 news:**
- South Sydney Rabbitohs: Latrell Mitchell (back injury, out R12-13)
- Wests Tigers: Patrick Herbert (2-match ban, out R12-13)
- Manly Sea Eagles: Lehi Hopoate (1-match ban, out R12)

**AFL R11 news:**
- Richmond Tigers: Campbell Gray (hamstring, out R11); Nick Vlastuin (MRO reviewing, pending)
- West Coast Eagles: Harry Edwards (concussion 3rd in 3 games, TBC)
- Gold Coast Suns: Sam Clohesy (suspended, out R11)

**UI wired into DetailDrawer Team News tab:** OUT/SUSP pills per player, severity-coloured names, chip at bottom showing Alert/Monitor status.

### 3. BVI + H/A Value — moved from header into per-card controls
Removed global header toggles (BVI checkbox, H/A Value checkbox, Search button). Now each game card has independent toggle controls.

**Design:** Split-box controls top-right in each card, stacked below Ask Baz / Details buttons. Left half = checkbox toggle (BVI or H/A Value), right half = ℹ️ info button. Both halves share a single bordered container with a vertical divider.

**Per-card state:** `showBVI`, `showBVIInfo`, `showHaValue`, `showHaInfo` — independent per game.

**BVI display:** Still uses role-aware logic (fav uses fav_profit, dog uses und_profit). Suppresses both if both same tier. Per-card toggle gates display.

### 4. Canterbury Bulldogs (H) vs Melbourne Storm (A) — manual price-up

Full T1–T8 price-up using R11 data as of 2026-05-14.

**T1 result:** Storm -0.53 margin, Total 47.34
- Canterbury ELO: 1501.78, Storm ELO: 1536.13 (34.35 pt Storm ELO edge)
- Canterbury Pythagorean: 0.312 (very low attack, 17.4 pts for avg)
- Storm Pythagorean: 0.437 (slightly below average)
- Canterbury exceptional home defence: 20.5 pts against at home vs 26.4 season avg (+5.94 pt boost)
- Home HA computed: 3.58 pts (data_weight=0.643 — below min_games=14 threshold)
- ELO margin: +0.75 to home (HA overcomes Storm's ELO edge at 0.08 pts/pt)
- Blended margin (dynamic_elo_weight=0.335): -0.034 (virtual coin flip pre-lean)
- Class lean: -0.497 (Storm slightly better season quality) → adjusted -0.531

**T2:** Style stats NULL for both → 0.0 (in R11, Storm fired Family B -6.0 vs Parramatta — not replicable here)

**T3:** Storm travels ~701km Melbourne→CommBank; normal rest both → +0.77 to Canterbury

**T4/T5/T6/T7/T8:** All 0.0 (no fortress data, equal outs assumed, neutral ref, clear weather)

**Final pricing:**
- Canterbury **23.8** – Storm **23.6**
- Fair margin: Canterbury +0.24 (scratch)
- Fair odds: Canterbury $1.97 / Storm $2.03
- Book-adjusted (105%): Canterbury ~$1.88 / Storm ~$1.93
- Handicap: scratch (line at 0.5)
- Total: 47.3 → 47.5 line (lean under)

**Key insight:** Canterbury's home ground turns them from a ~9pt dog into a coin flip. That home defence stat (20.5 pts against, 5.9pt better than season average) is doing enormous work. Small sample (~4-5 home games) — watch if it holds.

**If T2 fires Family B for Storm (as in R11):** Storm would move to ~-6 favourites. The key unknown is whether Storm's Family B applies in a Canterbury matchup vs the Parramatta matchup where it fired.

---

## Automation notes

Weekly workflow for team news JSON files:
- NRL: after MRC announcements Monday (suspensions) + game injuries from weekend. Manual 2-min edit.
- AFL: after tribunal decisions Wednesday + game injuries from weekend.
- Future: `lib/scraper/nrl_team_news.py` could auto-generate injuries section from `latest-injuries.json`; suspensions still manual.

---

## Pending work carried forward

- BVI weekly Task Scheduler task: install Task Scheduler entry to run `afl_bvi.py` Monday 08:00
- AFL injury scraper: `afl_injuries.py` not yet built
- nrl_team_news.py automation script: auto-populate injuries from latest-injuries.json
- Odds movement alert threshold filter: only alert if change_pct >= 10%
- Style stats for Canterbury and Storm: if loaded, re-run T2 and it may change the Storm/Canterbury call significantly
