# Session: Round Renumbering + Week 10 Pricing
**Date:** 2026-05-05
**Goal:** Fix DB round numbering to match NRL official rounds, then price Week 10 (May 7-11).

---

## Problems Found

### 1. DB had pre-season games inflating round numbers by +1
- Feb 28 games (Canterbury vs St George, Newcastle vs NQ Cowboys) were stored as round 1
- This pushed every subsequent NRL round up by 1 vs the NRL official numbering
- DB R10 = NRL R9, DB R11 = NRL R10, etc.

### 2. DB was missing NRL Round 10 entirely
- The DB had DB R10 (May 1-3, NRL R9) and DB R11 (May 15-17 Magic Round, NRL R11)
- NRL Round 10 (May 7-11) was never scraped or loaded
- The BetMate fixture scraper had jumped from round 9 to round 11

### 3. Round renumbering cascade bug
- First migration attempt used sequential UPDATEs top-down which cascaded all rounds into R1
- Fixed by reassigning from match dates using date range UPDATE queries

---

## Migration Applied

**matches table (NRL 2026):**
- R1 (Feb 28 pre-season) → R0
- R2-R10 (Mar 5 – May 3) → R1-R9 (shifted down by 1, done by date ranges)
- R11 (Magic Round, May 15-17) → stays R11

**tier2_performance, weekly_ref_assignments, ml_shadow_predictions:**
- round 10 → round 9 (all season=2026)

**fetch_nrl_results.py:**
- `NRL_API_ROUND_OFFSET` changed from -1 to 0 (DB now aligns with NRL API)

**venues table:**
- 'QCB Stadium' renamed to 'Queensland Country Bank Stadium' (Townsville)

---

## Week 10 Priced (May 7-11)

Games inserted as DB round 10, priced with ELO through R9 actuals.
No injuries (T5=0) or referees (T6=0) — both announced Tue/Wed.

| Game | Venue | Fair Margin | H2H Home |
|---|---|---|---|
| Dolphins vs Canterbury | Suncorp | -7.2 | 1.38 |
| Sydney Roosters vs Gold Coast | Polytec | -9.4 | 1.28 |
| NQ Cowboys vs Parramatta | QCBS | -12.4 | 1.18 |
| St George vs Newcastle | WIN | +0.3 (pick) | 2.04 |
| South Sydney vs Cronulla | Accor | -3.5 | 1.63 |
| Manly vs Brisbane | 4 Pines | -3.5 | 1.63 |
| Melbourne Storm vs Wests Tigers | AAMI | -7.4 | 1.37 |
| Canberra vs Penrith | GIO | +7.1 (Penrith fav) | 3.61 |

**Output CSV:** `results/r10_nrl_week10_pricing_2026.csv`

---

## Current DB Round State (NRL 2026)

| DB Round | Dates | Status |
|---|---|---|
| 0 | Feb 28 | Pre-season, results in |
| 1-9 | Mar 5 – May 3 | All results loaded |
| 10 | May 7-11 | **Priced, pending injuries/refs** |
| 11 | May 15-17 Magic Round | Priced (needs reprice after R10 actuals) |

---

## Pending

- **Tue/Wed:** Add injuries + referee draw for R10, re-run prepare_round.py --round 10
- **Next Monday 9AM:** fetch_nrl_results.py will auto-run and pick up R10 actuals (offset now 0)
- **Magic Round (R11):** re-price after R10 results load (ELO will update)
- **fetch_nrl_results.py offset:** changed to 0 — verify it works for R10 next Monday
