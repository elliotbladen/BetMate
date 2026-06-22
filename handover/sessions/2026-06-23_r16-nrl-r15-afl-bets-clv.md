# Session: R16 NRL + R15 AFL Bets Logged + CLV
**Date:** 2026-06-23

---

## What Was Done

### 1. Historical Data Refresh (completed early session)
- Downloaded latest AusSportsBetting xlsx for NRL and AFL via Playwright scrapers
- NRL: `data/nrl/historical/latest.xlsx` — 3,541 rows, now includes R16 (Jun 19-21)
- AFL: `BettingEngine/outputs/afl_weekly_review/historical/latest.xlsx` — 3,481 rows, now includes R15 (Jun 18-21)
- Pushed both to Supabase: 546 NRL matches (2024+), 983 AFL matches (2022+)
- History tab on bet-mate-ten.vercel.app now reflects R16/R15 results

### 2. Bet Logging (screenshots A.png–E.png)

16 bets logged as 2026-0092 through 2026-0107:

**AFL R15 (7 bets, 6 wins, 1 loss, P&L +$90.04):**
| ID | Game | Bet | Odds | Stake | Result |
|----|------|-----|------|-------|--------|
| 0092 | Richmond v NM | NM -17.5 | 1.89 | $25 | WIN +$22.25 |
| 0093 | GCS v Hawthorn | Under 180.5 | 1.90 | $50 | LOSS -$50 |
| 0094 | Richmond v NM | Under 176.5 | 1.91 | $50 | WIN +$45.50 |
| 0095 | GCS v Hawthorn | Hawthorn H2H | 1.77 | $25 | WIN +$19.25 |
| 0099 | Collingwood v Port | Collingwood -13.5 | 1.90 | $25 | WIN +$22.50 |
| 0100 | Adelaide v Melbourne | Adelaide -4.5 PYL | 1.82 | $22 | WIN +$18.04 |
| 0101 | Fremantle v Geelong | Geelong +33.5 PYL | 1.50 | $25 | WIN +$12.50 |

**NRL R16 (5 bets, 2 wins, 3 losses, P&L -$54.25):**
| ID | Game | Bet | Odds | Stake | Result |
|----|------|-----|------|-------|--------|
| 0096 | Bulldogs v Sea Eagles | Under 48.5 | 1.83 | $50 | WIN +$41.50 |
| 0097 | Storm v Raiders | Raiders +8.5 | 1.90 | $50 | LOSS -$50 |
| 0098 | Roosters v Sharks | Sharks H2H | 2.53 | $50 | LOSS -$50 |
| 0105 | Tigers v Dolphins | Tigers H2H (LIVE) | 1.83 | $22 | LOSS -$22 |
| 0106 | Storm v Raiders | Under 67.5 (LIVE) | 2.05 | $25 | WIN +$26.25 |

**Soccer / World Cup (4 bets, 1 win, 3 losses, P&L -$19.79 — CLV exempt):**
| ID | Game | Bet | Odds | Stake | Result |
|----|------|-----|------|-------|--------|
| 0102 | USA v Australia | Draw | 4.10 | $19 | LOSS |
| 0103 | Mexico v South Korea | Draw | 3.30 | $18.50 | LOSS |
| 0104 | Belgium v Iran | Iran & Draw | 2.85 | $20 | WIN +$37 |
| 0107 | Tunisia v Japan | Under 2.5 | 1.77 | $19.29 | LOSS |

### 3. CLV Calculation

Used Jun 19 12:00 snapshot as proxy closing line (no Jun 20-21 snapshots exist — weekend task did not run).

**CLV filed for 8 pre-game standard bets (0092-0099):**
| Bet | CLV | Note |
|-----|-----|------|
| NM -17.5 | -0.53% | Line moved 4pts against (close -21.5) |
| Under 180.5 GCS/Haw | 0.00% | Line 2pts better (close 178.5) |
| Under 176.5 Ric/NM | +0.53% | Line 2pts better (close 174.5) |
| Hawthorn H2H | +4.12% | Got 1.77 vs close 1.70 |
| Under 48.5 Bulldogs/SEA | -2.66% | Got 1.83 vs close 1.88 |
| Raiders +8.5 | +0.53% | Got 1.90 vs close 1.89 |
| Sharks H2H | +2.02% | Got 2.53 vs close 2.48 |
| Collingwood -13.5 | 0.00% | Line 2pts against (close -11.5) |

**Average (8 bets): +0.50%**

**Excluded from CLV:**
- 0100, 0101: Pick Your Line bets — market line too different (Adelaide market -19.5, user took -4.5; Geelong market +20.5, user took +33.5)
- 0105: Tigers H2H — market had Tigers @ 2.88 pre-game, user bet @ 1.83 → clearly a live bet
- 0106: Under 67.5 Storm/Raiders — market standard line was 50.5 Under @ 1.87; 67.5 @ 2.05 only makes sense in-play

### 4. Running CLV Updated

| Sport | Round | Bets | Week CLV | Running CLV | Week P&L | Running P&L |
|-------|-------|------|----------|-------------|----------|-------------|
| AFL | R15 | 5 | +0.82% | +0.77% | +$90.04 | +$85.21 |
| NRL | R16 | 3 | -0.04% | +4.99% | -$54.25 | +$115.50 |

### 5. Model Notes (R15/R16 Performance)

**AFL R15 — excellent week:**
- Model signals mostly correct. 6/7 bets won.
- Hawthorn H2H was solid: market 1.70 → got 1.77. Model had Hawthorn fairly priced at 1.69.
- NM total under: model had 152.6/146.6, market 176.5 — excellent value.
- PYL bets (Adelaide -4.5, Geelong +33.5) were "safety" bets at low odds — both landed easily.

**NRL R16 — tough week, live bets skew picture:**
- Storm/Raiders: model had Storm -1.9 (Raiders +8.5 should cover) but Storm won by 22. T10 Origin over-penalisation confirmed — Storm missing Munster/Grant but still dominated.
- Roosters/Sharks: model had 50/50 (0.3 Roosters), user took Sharks @ 2.53. Roosters won by 19. Same T10 issue.
- Sharks CLV was +2.02% (good price) but wrong result.
- Live bets: Tigers @ 1.83 (market 2.88 pre-game) and Under 67.5 Storm @ 2.05 (market 50.5 standard line) — mixed results.

---

## Pending

- NRL R17 prep: Origin G3 Jul 8, camp Jul 3 — T10 squads need populating
- AFL R16 pricing: next Tuesday
- AFL rules model sigmoid ELO scaling: next AFL session
- T10 calibration review: Storm/Roosters showed Origin penalty too heavy for depth teams
- www.betmate.au DNS fix pending
- Supabase UNIQUE constraint on betmate_data_store.key still pending
- Update `actual_bets_clv_2026.csv` (per-bet CLV) from master ledger data
