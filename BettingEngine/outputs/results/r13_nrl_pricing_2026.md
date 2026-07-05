# NRL R13 2026 — Pricing Analysis

**Generated:** 2026-05-27 (updated 2026-05-28 — T5 + T6 + T7/T8 weather fully loaded)
**Model version:** 1.0.0 (T1–T8)
**✅ FULL TIERS — T5 injuries (93 records), T6 refs (4/7 games), T7 emotional (1 flag), T8 weather (7/7 Tomorrow.io)**

---

## Prices at a Glance

| Game | Date | Venue | Model H2H | Model Hcap | Market Hcap | Model Total | Market Total |
|------|------|-------|-----------|------------|-------------|-------------|--------------|
| **Cronulla** vs Manly | Fri 29 May | Ocean Protect | 1.44 / 2.81 | Sharks -4.9 | Sharks -2.5 | 52.8 | 50.5 |
| **Newcastle** vs Parramatta | Sat 30 May | McDonald Jones | 1.11 / 6.57 | Knights -12.7 | Knights -14.5 | 58.8 | 53.5 |
| **Wests Tigers** vs Bulldogs | Sat 30 May | CommBank | 1.55 / 2.47 | Tigers -3.5 | Tigers -1.5 | 48.5 | 48.5 |
| Roosters vs **Melbourne** (neutral) | Sat 30 May | AAMI Park | 2.15 / 1.71 | Roosters -1.7 | Roosters -1.5 | 56.6 | 49.5 |
| **Brisbane** vs St George | Sun 31 May | Suncorp | 1.04 / 11.44 | Broncos -16.6 | Broncos -19.5 | 43.8 | 54.5 |
| **Canberra** vs North Queensland | Sun 31 May | GIO Stadium | 1.75 / 2.09 | Raiders -1.3 | Raiders -3.5 | 50.0 | 52.5 |
| **Penrith** vs New Zealand | Sun 31 May | CommBank | 1.11 / 6.57 | Panthers -12.7 | Panthers -7.5 | 44.1 | 48.5 |

**Bold = model's pick to win. Market prices from 2026-05-26 snapshot.**

---

## Tier Breakdown (Handicap — home perspective)

| Game | T1 | T2 | T3 | T4 | T5 | T6 | Final Mrg |
|------|----|----|----|----|----|----|-----------|
| Cronulla vs Manly | +0.7 | +0.0 | +2.0 | +1.5 | +0.8 | +0.0 | **+4.9** |
| Newcastle vs Parramatta | +8.0 | +4.0 | -0.9 | -1.5 | +3.0 | +0.0 | **+12.7** |
| Wests Tigers vs Bulldogs | +7.0 | -4.0 | +1.5 | -1.5 | +0.5 | +0.0 | **+3.5** |
| Melbourne vs Roosters | -2.3 | +0.0 | -0.7 | +1.5 | -0.5 | +0.0 | **-1.7** |
| Brisbane vs St George | +14.2 | +0.0 | +2.4 | +1.5 | -1.5 | +0.0 | **+16.6** |
| Canberra vs Cowboys | -2.1 | +0.0 | +3.0 | +1.5 | -1.0 | +0.0 | **+1.3** |
| Penrith vs Warriors | +6.0 | +0.0 | +3.0 | +1.5 | +2.2 | +0.0 | **+12.7** |

## Tier Breakdown (Totals)

| Game | T1 | T2 | T3 | T4 | T5 | T6 | T7emo | T8wx | Final |
|------|----|----|----|----|----|----|-------|------|-------|
| Cronulla vs Manly | 56.1 | +0.0 | -0.75 | -0.55 | -2.02 | +0.0 | +0.0 | +0.0 | **52.8** |
| Newcastle vs Parramatta | 63.0 | -1.5 | +0.0 | -2.0 | -0.75 | +0.0 | +0.0 | +0.0 | **58.8** |
| Wests Tigers vs Bulldogs | 50.6 | -0.75 | +0.0 | -2.0 | -1.35 | +2.0 | +0.0 | +0.0 | **48.5** |
| Melbourne vs Roosters | 56.3 | +0.0 | +0.0 | -1.0 | -1.2 | +2.0 | +0.5 | +0.0 | **56.6** |
| Brisbane vs St George | 45.5 | +0.0 | +0.0 | +2.0 | -1.8 | +0.0 | +0.0 | **-2.0** | **43.8** |
| Canberra vs Cowboys | 52.0 | +0.0 | -1.0 | +2.0 | -0.9 | -2.0 | +0.0 | +0.0 | **50.0** |
| Penrith vs Warriors | 47.5 | +0.0 | -1.0 | -2.0 | -0.38 | +0.0 | +0.0 | +0.0 | **44.1** |

*T6 refs: Wests/Bulldogs = Peter Gough (flow_heavy +2.0), Storm/Roosters = Grant Atkins (flow_heavy +2.0), Raiders/Cowboys = Ashley Klein (whistle_heavy -2.0), Panthers/Warriors = Gerard Sutton (neutral). Cronulla/Manly, Newcastle/Parra, Broncos/Dragons still missing.*
*T8wx: Suncorp moderate_wind (20.2 km/h) → -2.0 on Brisbane/St George total. All other games clear.*

---

## Game Notes

### Cronulla vs Manly — Fri, Ocean Protect Stadium
Model: Sharks -4.2 | Market: Sharks -2.5

Near-equal by ELO (+0.7 baseline). Sharks get the nod from rest (14 days vs Manly's 6-day turnaround = +2.03 T3) and home venue (+1.5 T4). No style edge.

**MATRIX ANALYSIS (run 2026-05-27 via `_cronulla_manly_matrix.py`): 7-way confluence — all backing Cronulla.**

Manly has 7 applicable 20%+ matrix edges for this specific game, ALL pointing to opposing Manly:

| Condition | Manly actual | Manly implied | Edge | n |
|-----------|-------------|--------------|------|---|
| As away team | 32.0% | 48.2% | 34% OPPOSING | 50 |
| Night games (≥18:00) | 38.9% | 50.7% | 23% OPPOSING | 54 |
| Thu/Fri games | 31.6% | 51.4% | 39% OPPOSING | 38 |
| After a win | 44.4% | 57.2% | 22% OPPOSING | 45 |
| Short rest (≤6 days) | 29.4% | 53.2% | 45% OPPOSING | 34 |
| vs Cronulla (H2H) | 14.3% | 39.4% | 64% OPPOSING | 7 |
| May games | 31.2% | 49.4% | 37% OPPOSING | 16 |

The H2H data is striking: Cronulla wins 85.7% of these matchups vs 65.6% implied (Manly only 14.3% vs 39.4% implied). Manly on short rest away on a Thursday/Friday night is historically terrible at covering market expectations. All 7 conditions compound in the same direction.

Market at Sharks -2.5 is 1.7pts below the model's -4.2. With 7-way matrix confluence on top, this game has the clearest directional signal of the round.

- **Handicap: Cronulla -2.5 — UPGRADED TO HIGH SIGNAL.** Model +matrix both point Cronulla. Wait for injury/ref confirmation but matrix confluence overrides the preliminary "marginal" rating.
- **H2H: Cronulla — value.** If market H2H is near 1.50-1.55 vs model 1.57, check EV. Confluence supports backing Cronulla outright.
- **Totals: UNDER 50.5 — lean.** Model 54.8 vs market 50.5. NRL totals model runs 5-10pts high, so fair line ~48-50. Market at 50.5 is at the upper edge of fair. Slight lean under.

---

### Newcastle vs Parramatta — Sat, McDonald Jones Stadium
Model: Knights -9.65 | Market: Knights -14.5

Newcastle fire T2 family [C] (+4.0 hcap) which gives them a style edge over Parramatta. But the market has priced them as -14.5 — **4.85pts more aggressive than the model**. Both teams had long rest (Knights 13d, Eels 14d) — T3 net near zero.

**Market is significantly overpricing Newcastle.** The model's -9.65 vs market -14.5 gap is one of the cleaner signals of the round, even without injury data loaded. Parramatta at home ground disadvantage still, but the line has moved too far.

- **Handicap: Parramatta +14.5 — value.** Model says Knights by 9.65. Market at 14.5 gives 4.85pts of free handicap for Eels. Even if T5 loads a couple of Newcastle injuries (improving their case), the gap would need to be enormous to justify -14.5. **Best handicap bet of the round pre-injury update.**
- **Totals: Skip.** Model 59.5 vs market 53.5. NRL bias means model is running high. Market probably fair.

---

### Wests Tigers vs Bulldogs — Sat, CommBank Stadium
Model: Tigers -3.0 | Market: Tigers -1.5

T2 fires style family [D] — Bulldogs style interaction hits them -4.0 hcap. Tigers get extra rest (+1.52 T3, 14d). Bulldogs slight away disadvantage (-1.5 T4 at CommBank).

Model has Tigers by 3, market by 1.5. Minor edge to Tigers but close.

- **Handicap: Skip.** 1.5pt gap between model and market. Wait for injury/ref data.
- **Totals: Skip.** Model 47.8 vs market 48.5. Nearly identical.

---

### Melbourne Storm vs Sydney Roosters — Sat, AAMI Park
Model: Roosters -1.48 | Market: Roosters -1.5

Near-perfect match. Roosters ELO edge (-2.3), Storm get AAMI home boost (+1.5), Roosters had extra rest (14 days, bye R12) but travelled 712km (net -0.72 T3). Model and market are essentially identical at -1.5. Storm had 8 days rest, lost R12 to Bulldogs 20-30.

**MATRIX ANALYSIS (run 2026-05-27 via `_storm_roosters_matrix.py`): No triple confluence — signals split evenly. Coin-flip confirmed.**

Storm applicable edges (2, conflicting):
- vs Roosters H2H: **25% BACKING Storm** (n=10) — Storm wins 80.0% vs 63.8% implied. Strong historical dominance.
- May games: **21% OPPOSING Storm** (n=16) — Storm only 56.2% in May vs 71.4% implied. Unusual May slump.

Roosters applicable edges (2, conflicting):
- Full moon (±1 day): **24% BACKING Roosters** (n=13) — 98.1% illumination, full moon May 31. Roosters perform 69.2% vs 55.9% implied near full moons.
- vs Melbourne H2H: **51% OPPOSING Roosters** (n=10) — Roosters win only 20.0% vs Storm vs 41.1% implied.

The H2H signal is dominant on both sides (Storm 25% BACKING, Roosters 51% OPPOSING = same direction). But May games (-21% for Storm) and full moon (+24% for Roosters) push back. Net result: 2 aligned signals each way — no trigger.

The model and market are correct to call this a coin flip at -1.5. Neither team has enough matrix conviction to override the pricing.

- **Handicap: Skip.** Model = market = -1.5. No matrix edge either way.
- **Totals: Lean UNDER 49.5.** Model 55.3 vs market 49.5. NRL totals model runs 5-10pts high, so fair line ~49-51. Market at 49.5 is within range but slight lean under — if right price.

---

### Brisbane vs St George Illawarra — Sun, Suncorp Stadium
Model: Broncos -18.1 | Market: Broncos -19.5

Market (19.5) is actually 1.4pts more aggressive than the model (18.1). Brisbane are massive ELO favourites (+14.2 baseline), extra rest, at Suncorp. Dragons are travelling 800km. No injury data loaded — if Dragons have outs, market may be right to go wider.

Skip handicap — model and market within 1.5pts after injuries load, this likely converges.

- **Totals: UNDER 54.5 — value.** Model has this at 47.6 vs market 54.5 = **6.9pt gap**. With NRL totals bias (model runs 5-10pts high), fair line is approximately 47-52. Market at 54.5 is inflated. Brisbane-Dragons games often grind low — this looks like a strong under.

---

### Canberra Raiders vs North Queensland Cowboys — Sun, GIO Stadium
Model: Raiders -2.34 | Market: Raiders -3.5

Cowboys have the ELO edge (-2.1 at baseline) but Raiders neutralize it with extra rest (+2.97 T3, 10 days) and home fortress (+1.5 T4). Model ends up Raiders by 2.34 — market at -3.5 is 1.16pts more bullish on Raiders.

This is very close. The Cowboys travel 1792km which is a real factor (already loaded at T3 +1.0 for Raiders).

- **Handicap: Cowboys +3.5 — marginal.** Model sees Raiders by 2.34 so Cowboys cover the 3.5 line. But it's thin — T5 and T6 will determine if this is worth taking.
- **Totals: Skip.** Model 53.0 vs market 52.5. Essentially the same.

---

### Penrith Panthers vs New Zealand Warriors — Sun, CommBank Stadium
Model: Panthers -10.47 | Market: Panthers -7.5

Model is 2.97pts more bullish on Penrith than the market. Panthers get extra rest (14 days, bye R12), Warriors travel 2182km from NZ (-1.0 T3 for totals), and Penrith's CommBank game counts as a home game (+1.5 T4 applied). No style edge fires.

H2H gap is notable — market at 1.67/2.98 gives Warriors much better than model's 1.18/4.99 implies. Market is less convinced on Panthers' dominance than the model.

- **Handicap: Panthers -7.5 — value.** Model says -10.47, market -7.5. 2.97pt gap. Even if injuries slightly dent Penrith (Luai, To'o?), Panthers at -7.5 looks good value.

**TOTALS MATRIX (run 2026-05-27 via `_panthers_warriors_totals_matrix.py`): 8-way UNDER confluence for Panthers, 4-way for Warriors. UPGRADED TO HIGH.**

Panthers (HOME) — 8 UNDER / 1 OVER applicable:

| Condition | Edge | Direction | n | Avg vs line |
|-----------|------|-----------|---|-------------|
| vs Warriors (H2H) | **46%** | UNDER | 7 | avg 41 vs 45 (**-4**) |
| At CommBank Stadium | 26% | UNDER | 18 | avg 43 vs 45 (-2) |
| Day games (<18:00) | 26% | UNDER | 41 | avg 43 vs 44 (-1) |
| Sunday games | 23% | UNDER | 27 | avg 42 vs 45 (-4) |
| May games | 22% | UNDER | 17 | avg 38 vs 43 (-5) |
| Long rest (>=10d) | 20% | UNDER | 19 | avg 38 vs 42 (-5) |
| Home games | 16% | UNDER | 61 | avg 40 vs 43 (-3) |
| Regular season | 13% | UNDER | 107 | avg 42 vs 43 (-2) |
| Full moon (±1d) | 20% | **OVER** | 11 | avg 46 vs 43 (+3) |

Warriors (AWAY) — 4 UNDER / 1 OVER applicable:

| Condition | Edge | Direction | n | Avg vs line |
|-----------|------|-----------|---|-------------|
| May games | **34%** | UNDER | 17 | avg 41 vs 44 (-3) |
| vs Panthers (H2H) | 46% | UNDER | 7 | avg 41 vs 45 (-4) |
| Day games (<18:00) | 13% | UNDER | 57 | avg 44 vs 46 (-1) |
| Regular season | 10% | UNDER | 106 | avg 45 vs 45 (-1) |
| Long rest (>=10d) | 16% | **OVER** | 18 | avg 45 vs 45 (+0) |

The H2H pattern is the standout signal: Panthers vs Warriors games average **41 actual vs 45 market line** (-4 pts below line, going UNDER 71.4% of the time, n=7). Both teams flag the same H2H from their respective perspectives.

Both teams agree on UNDER for: H2H, day games, May games, regular season — 4 shared UNDER conditions with zero shared OVER conditions. The full moon (Panthers 20% OVER) and Warriors long rest (16% OVER, avg diff = 0) are the only counterweights — both thin.

Market 48.5. Model 44.5. NRL totals bias correction: fair line ~44-46. H2H average actual: 41.

- **Totals: UNDER 48.5 — UPGRADED TO HIGH.** 8-way matrix confluence for Panthers, 4-way for Warriors, identical H2H (-4 avg vs line). Model, matrix, and H2H history all point UNDER.

---

## Signal Summary

**All tiers loaded. Cronulla/Manly and Newcastle/Parra refs still missing — those games not fully finalised.**

| Game | Signal | Side | Market Price | Confidence | Notes |
|------|--------|------|-------------|------------|-------|
| **Cronulla vs Manly** | Handicap | **Cronulla -2.5** | ~1.90 | **High** | **7-way matrix confluence** — Manly terrible Fri night away on short rest. Model -4.9 vs market -2.5. T5 adds +0.8 Sharks. |
| Newcastle vs Parramatta | Handicap | **Parramatta +14.5** | ~1.91 | High | Model Knights by 12.7 vs market 14.5 — 1.8pt gap (narrowed from 4.85 pre-T5). T5 adds +3.0 Newcastle (Parra injuries significant). Still value at +14.5. |
| **Panthers vs Warriors** | Totals | **UNDER 48.5** | ~1.98 | **High** | **8-way matrix confluence** — H2H avg 41 vs line 45 (-4), model 44.1. Gerard Sutton neutral ref. |
| Broncos vs Dragons | Totals | **UNDER 54.5** | ~1.90 | **High** | Model 43.8 (T8 weather: -2.0 moderate wind at Suncorp). 10.7pt gap. NRL bias correction still puts fair ~43-48. Massive UNDER. |
| Panthers vs Warriors | Handicap | **Panthers -7.5** | ~2.00 | Medium | Model 12.7 vs market 7.5 — 5.2pt gap (stronger post-T5). Gerard Sutton neutral. |
| Raiders vs Cowboys | Handicap | **Cowboys +3.5** | ~1.95 | Low-Med | Model Raiders by 1.3 — marginal. Ashley Klein whistle-heavy hurts Raiders' total, not hcap. |
| Melbourne vs Roosters | Totals | **UNDER 49.5** | ~1.90 | Low | Model 56.6 (Grant Atkins flow_heavy +2.0 inflates this). Rivalry flag adds +0.5. NRL bias puts fair line ~50-53. Pass. |

---

## Referee Impact

4 of 7 refs loaded (scraped 2026-05-28):
| Game | Referee | Bucket | Totals Impact |
|------|---------|--------|---------------|
| Wests Tigers vs Bulldogs | Peter Gough | flow_heavy | +2.0 |
| Melbourne vs Roosters | Grant Atkins | flow_heavy | +2.0 |
| Canberra vs Cowboys | Ashley Klein | whistle_heavy | -2.0 |
| Panthers vs Warriors | Gerard Sutton | neutral | 0.0 |
| Cronulla vs Manly | — | — | 0.0 |
| Newcastle vs Parramatta | — | — | 0.0 |
| Brisbane vs St George | — | — | 0.0 |

**Missing refs:** Todd Smith (Cronulla/Manly), Wyatt Raymond (Broncos/Dragons), Newcastle/Parra unassigned. Re-run pricing if these are high-confidence bet games once refs load.

---

## Injury Notes

T5 loaded 2026-05-28 (93 records, scraped from NRL.com casualty ward). Key impacts:
- **Cronulla:** home +0.8 pts hcap (minor Manly outs vs clean Sharks)
- **Newcastle:** home +3.0 pts hcap — significant Parramatta injury load. **Narrows the Parra +14.5 gap but doesn't eliminate it** (model still 12.7 vs market 14.5 = 1.8pt gap).
- **Penrith:** home +2.25 pts hcap — Warriors carrying more outs (Roger Tuivasa-Sheck, Morgan Gannon, Charnze Nicoll-Klokstad all out). **Strengthens Panthers -7.5 signal.**
- **Brisbane:** away -1.5 pts hcap (some Broncos outs). Narrows margin slightly.

---

## Key Caveats

**NRL totals bias:** Model runs 5-10pts high on NRL totals. Discount all totals by ~7pts when evaluating. This strengthens all UNDER calls.

**Parramatta +14.5:** Model 12.7 post-T5 vs market 14.5 = 1.8pt gap. Still in the direction of value, but less convincing than the pre-T5 4.85pt gap. T2 style family [C] is firing hard for Newcastle (+4.0) — if this is noise, gap narrows further. Treat as Medium-High, not automatic.

**Brisbane/Dragons UNDER 54.5 is the strongest totals signal this round.** Model 43.8 (T8 wind -2.0 applied) — that's a 10.7pt gap vs market. Even with 7pt NRL bias, fair line is ~43-50, market at 54.5 is way out.

**Refs still missing for 3 games:** Cronulla/Manly result not materially affected (Sharks -4.9 is a comfortable cushion over -2.5 regardless). Newcastle/Parra T6 unlikely to flip the signal at any ref. Brisbane/Dragons — ref bucket could shift total by ±2pts but market at 54.5 has 10.7pt buffer so immaterial.
