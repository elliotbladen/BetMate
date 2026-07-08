# Session Handover — 2026-06-18
## NRL R16 Pricing + ELO Audit + Model Accuracy

---

### What We Did

**1. Hawthorn ELO audit**
- Confirmed Hawthorn ELO = 1687 (4th in AFL), not over-estimated
- Three losses (bet-0022, bet-0030, bet-0069/70/71) caused by linear ELO→margin overcooking large ELO gaps
- Root cause: +301 ELO diff vs Melbourne → 79.6% win prob → model priced massive margin, actual was -39 loss
- Fix remains pending: sigmoid ELO scaling `(win_prob - 0.5) × SCALE` (end-of-season 2026 item)

**2. H2H model accuracy R8–now**
- NRL Rules H2H: 27/35 = **77.1%** (R9–R13, 5 rounds) — strong
- AFL Rules H2H: 13/25 = **52.0%** (R8, R11, R12 — R9/R10/R13 data missing) — below chance threshold
- AFL Market H2H: 64.0% — outperforms our model
- AFL R14 H2H: Rules 6/7 = 85.7%, ML 5/7 = 71.4% (good round)
- **Conclusion:** Don't bet AFL H2H until model > 65% over 50+ bets. Focus AFL on totals/handicaps where CLV edge exists.

**3. NRL R16 Pricing**

**Pre-pricing steps completed:**
- Scraped R16 fixture (7 games, 3 BYEs: Brisbane, Parramatta, South Sydney)
- Confirmed T10 Origin NOT firing (camp_end June 18, all games June 19+)
- Updated injury file: Crichton Bulldogs out→doubtful (named R16), added Dolphins Origin rests (Tabuai-Fidow, Cobbo, Flegler all key/out)
- Emotional scraper: 0 flags for R16 (ran fine)
- Referee scraper: no data yet (refs announced ~14:00 Wed)
- Added 2 missing venues to model.db: "Campbelltown Sports Stadium" (id=43), "One NZ Stadium" (id=44)

**Pipeline run:** `prepare_round.py --season 2026 --round 16` — all 7 games priced successfully

---

### R16 Prices (Rules Model)

| Game | Model Margin | Model Total | Key Signal |
|------|-------------|-------------|------------|
| Knights vs Dragons | Knights -13.8 | 52.4 | Neutral — on market |
| Tigers vs Dolphins | Dolphins -4.2 | 55.0 | WATCH: Tigers +4 if Dolphins confirm rests |
| Titans vs Panthers | Panthers -20.4 | 41.4 | WAIT: Cleary team list Thursday |
| Bulldogs vs Sea Eagles | Sea Eagles -7.4 | 38.9 | LEAN: Sea Eagles cover if market -7 to -8 |
| Warriors vs Cowboys | Warriors -12.0 | 46.2 | Neutral |
| Storm vs Raiders | Storm -7.5 | 45.5 | LEAN: Storm cover |
| Roosters vs Sharks | Roosters -2.4 | 52.2 | HIGH: Roosters H2H under 1.75 (Hynes elite out) |

**Top pick: Sydney Roosters H2H** — Nicho Hynes out (elite, Return R18), near-equal ELO, home ground, model -2.4. If market has Roosters -4 to -6, real value at H2H under 1.75.

---

### Key Manual Notes for Next Re-run (After Refs)

1. **Penrith Origin players** (Cleary elite, Yeo key, To'o rotation) NOT in injury file — confirm team list Thursday. If resting, add to injury file and re-run. Panthers price drops from -20.4 to ~-17 to -18 without Cleary.

2. **Tom Trbojevic** — kept as elite/doubtful in model (1.5 pts T5 penalty applied). He IS confirmed returning. If you want true price: remove him from injury file and re-run. True Sea Eagles margin would be ~-9 instead of -7.4.

3. **Josh Papalii** — listed as rotation in injury file but much more important than that. Model under-penalises Raiders if he misses. Storm margin could be -8 to -9 in reality.

4. **Dolphins resting** — only confirmed 3 key players (Cobbo, Tabuai-Fidow, Flegler). Did NOT add Plath/Finefeuiaki (rotation — uncertain). Check Dolphins official team list.

---

### Files Created/Modified

| File | Change |
|------|--------|
| `Apps/data/nrl/injuries/processed/latest-injuries.json` | Crichton out→doubtful; added Dolphins Origin rests |
| `Apps/data/nrl/fixture/processed/latest-fixture.json` | Updated to R16 (7 games) |
| `BettingEngine/data/model.db` | Added venues: Campbelltown Sports Stadium (43), One NZ Stadium (44) |
| `BettingEngine/results/r16_pricing_2026.csv` | R16 pricing output |

---

### To-Do Before Betting R16

- [ ] **14:00 today** — Run `scrapers/nrl_referees.py --round 16` then re-run `prepare_round.py --round 16 --skip-load` for T6
- [ ] **Thursday team lists** — Check Penrith (Cleary/Yeo/To'o), Dolphins (confirm rests), update injury file as needed
- [ ] **Re-run pricing** after any team list changes
- [ ] **ML shadow** — check if NRL ML shadow model output exists to cross-validate Roosters/Sharks pick

---

### ELO Standings Entering R16

| Rank | Team | ELO |
|------|------|-----|
| 1 | Penrith Panthers | 1589.0 |
| 2 | Brisbane Broncos | 1585.3 |
| 3 | Cronulla-Sutherland Sharks | 1548.7 |
| 4 | Canberra Raiders | 1531.5 |
| 5 | Sydney Roosters | 1530.9 |
| 6 | New Zealand Warriors | 1528.9 |
| 7 | Melbourne Storm | 1527.2 |
| 8 | Canterbury-Bankstown Bulldogs | 1512.8 |
| 9 | Manly-Warringah Sea Eagles | 1509.7 |
| 10 | Wests Tigers | 1496.2 |
| 11 | Dolphins | 1490.4 |
| 12 | South Sydney Rabbitohs | 1489.6 |
| 13 | North Queensland Cowboys | 1485.6 |
| 14 | Parramatta Eels | 1479.8 |
| 15 | Newcastle Knights | 1426.7 |
| 16 | Gold Coast Titans | 1390.5 |
| 17 | St. George Illawarra Dragons | 1377.2 |
