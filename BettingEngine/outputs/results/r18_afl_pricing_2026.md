# AFL R18 2026 — Pricing Analysis

**Generated:** 2026-07-09 (full re-price — supersedes the 2026-07-07 start-of-week run)
**Model version:** 1.0.0 (T1–T7 rules + ML shadow — **first round priced on the Jul 5 EMA/split-feature XGBoost retrain**)
**Byes:** None — all 18 teams playing.
**Market source:** ⚠️ **NONE — The Odds API key is still deactivated (401 Unauthorized, snapshots dead since Jul 3).** Fair prices are complete but there are no market lines to compare against, so no EV or bet sizing is possible until the key is fixed.

---

## What changed vs the Jul 7 run

1. **T2 style data is now a genuine R18 Footywire snapshot** — scraped today (site back up after its outage). The Jul 7 run silently used the last available snapshot, which was **R9 (May 12)**. This moved several handicaps (Magpies -14.3 → -20.3 the biggest).
2. **ML shadow was silently broken and is now fixed.** The Jul 8 pkl regeneration switched to the split-feature/EMA models (38-col regressors, 30-col H2H), but `prepare_afl_round.py` still built the old 29-feature row — model load failed and the shadow section was skipped. Fixed: split feature sets wired in, EMA form computed at deploy exactly per `game_log.py` (8-game window, 0.75 decay, opposition-adjusted), `mkt_home_prob_open` added with the training-time `elo_win_prob` fallback.
3. **Adelaide's "personal_tragedy major" T6 flag REMOVED.** The emotional scraper recycled April 2026 headlines about Jordan Dawson's brother. Dawson played R17 (27 disposals, 1 goal vs West Coast) and is available for R18 — no grief/rally adjustment applies. Crows line moved -30.6 → -26.9. Corrected prep file written to `emotional_r18_2026.json`.
4. **Brisbane T5 corrected from today's Lions injury report:** Jack Payne confirmed out for the season (carry forward); Darcy Gardiner (hamstring, 4–6 wks) added. McCluggage and Zorko RETURN vs Essendon — correctly absent from the outs list. Lions line -52.5 → -55.3.
5. **T7 weather re-pulled from Tomorrow.io today** for all games at kickoff hour.

---

## Tier Coverage Report (mandatory)

| Tier | Status | Detail |
|------|--------|--------|
| T1 — ELO baseline | ✅ REAL | Rebuilt features (Jul 9) on Jul 7 xlsx incl. all R17 results. Season calibration n=144: margin +4.8, total -3.5 |
| T2 — Style matchup | ✅ REAL (fresh) | Footywire season-to-date entering R18, scraped 2026-07-09, 18 teams. Hit ±4.0 cap on 6/9 games (known saturation issue) |
| T3 — Situational | ✅ REAL | Rest/travel/form from fixture + history. Zero on 4 games = genuine null, not fallback |
| T4 — Venue | ✅ REAL | Fortress fired: Giants +2.5, Lions +2.0 |
| T5 — Injuries | ✅ REAL (corrected) | Curated Jul 7 file + today's Payne/Gardiner corrections. Season-enders re-confirmed (Green, Rozee, Flanders, Darcy). Compound ⚡ on Saints/Power and Giants/Cats. Position/quality tags remain manual judgement calls — directionally right, not decimal-precise |
| T6 — Emotional | ✅ REAL (corrected) | 4 valid flags (rivalry: Coll/NM, Melb/Rich; must-win: BL minor, Freo normal). Bogus Dawson flag removed |
| T7 — Weather | ✅ REAL | Live Tomorrow.io, all venues. Strong wind (22–25 km/h) Marvel/MCG/Adelaide Oval Saturday → -6.0 totals docks; moderate wind Sunday venues |
| ML shadow | ✅ REAL (fixed) | New EMA/split-feature models (margin MAE 29.3, H2H 68.5% on 2025 holdout). Market-prob feature on ELO fallback — see risk flags |
| T9 — Matrix confluence | ✅ REAL | All 3 matrices, 9/9 games with 3+ way signals, JSON exported |

**Coverage: 9/9 tiers in scope genuinely populated — 100%, no defaults.** The one deliverable that could NOT be produced: **market comparison (EV, edges, bet selection)** — blocked by the dead Odds API key.

---

## Prices at a Glance (fair prices — no market lines available)

| Game | Date | Venue | Fair H2H | Fair Hcap | Fair Total |
|------|------|-------|----------|-----------|------------|
| **Fremantle** vs Sydney | Thu 9 Jul | Optus | 1.27 / 4.67 | Dockers -28.5 | 178.0 |
| **Collingwood** vs Nth Melb | Fri 10 Jul | Marvel | 1.40 / 3.49 | Magpies -20.3 | 163.5 |
| **St Kilda** vs Port Adelaide | Sat 11 Jul | Marvel | 1.74 / 2.35 | Saints -6.8 | 152.0 |
| GWS vs **Geelong** | Sat 11 Jul | ENGIE | 3.30 / 1.44 | Cats -18.6 | 194.0 |
| Carlton vs **Hawthorn** | Sat 11 Jul | MCG | 3.47 / 1.41 | Hawks -20.1 | 164.0 |
| **Adelaide** vs Gold Coast | Sat 11 Jul | Adelaide Oval | 1.30 / 4.39 | Crows -26.9 | 162.5 |
| **W. Bulldogs** vs West Coast | Sun 12 Jul | Marvel | 1.12 / 9.03 | Bulldogs -44.0 | 153.5 |
| **Melbourne** vs Richmond | Sun 12 Jul | MCG | 1.16 / 7.18 | Demons -39.0 | 154.0 |
| **Brisbane** vs Essendon | Sun 12 Jul | Gabba | 1.07 / 16.05 | Lions -55.3 | 164.0 |

**Bold = model's pick to win.**

---

## Tier Breakdown (Handicap — home perspective)

| Game | ELO gap | T1 | T2 | T3 | T4 | T5 | T6 | T7wx | Final |
|------|---------|----|----|----|----|----|----|------|-------|
| Dockers vs Swans | +111 | +19.0 | -4.0 | +5.0 | +0.0 | +6.5 | +2.0 | +0.0 | **+28.5** |
| Magpies vs Kangaroos | +162 | +20.8 | +2.0 | +0.0 | +0.0 | -4.0 | +1.5 | +0.0 | **+20.3** |
| Saints vs Power | +9 | +7.0 | +3.5 | +0.1 | +0.0 | -3.8 | +0.0 | -6.0 | **+6.8** |
| Giants vs Cats | -222 | -11.0 | -2.0 | +0.0 | +2.5 | -8.0 | +0.0 | +0.0 | **-18.6** |
| Blues vs Hawks | -225 | -14.1 | -4.0 | +0.0 | +0.0 | -2.0 | +0.0 | -6.6 | **-20.1** |
| Crows vs Suns | +108 | +18.7 | +4.0 | +2.7 | +0.0 | +1.5 | +0.0 | -6.0 | **+26.9** |
| Bulldogs vs Eagles | +370 | +39.5 | +4.0 | +3.0 | +0.0 | -2.5 | +0.0 | -2.8 | **+44.0** |
| Demons vs Tigers | +326 | +35.5 | +4.0 | +0.0 | +0.0 | -2.0 | +1.5 | -3.1 | **+39.0** |
| Lions vs Bombers | +517 | +50.0 | +4.0 | +1.8 | +2.0 | -3.5 | +1.0 | -2.8 | **+55.3** |

Injury highlight: Sydney brings 7 outs across the country on the back of Fremantle's home 5-day-vs-travel edge — T5 +6.5 is the biggest single injury swing of the round.

---

## ML Shadow (new EMA/split-feature models — first live round)

| Game | Rules Mrg | ML Mrg | Gap | Rules Tot | ML Tot | Rules H% | ML H% | Flag |
|------|-----------|--------|-----|-----------|--------|----------|-------|------|
| Dockers vs Swans | +28.5 | +7.1 | -21.4 | 177.9 | 150.7 | 78.6% | 55.8% | margin+H2H+total |
| Magpies vs Kangaroos | +20.3 | +30.3 | +10.0 | 163.5 | 170.6 | 71.4% | 73.3% | margin |
| Saints vs Power | +6.8 | +6.1 | -0.7 | 152.0 | 146.0 | 57.5% | 53.8% | — |
| Giants vs Cats | -18.6 | -6.3 | +12.3 | 194.0 | 165.8 | 30.3% | 54.6% | margin+H2H+total |
| Blues vs Hawks | -20.1 | -32.5 | -12.4 | 163.8 | 175.7 | 28.8% | 51.9% | margin+H2H+total |
| Crows vs Suns | +26.9 | +27.3 | +0.4 | 162.7 | 173.3 | 77.2% | 79.2% | total |
| Bulldogs vs Eagles | +44.0 | +43.1 | -0.9 | 153.6 | 171.3 | 88.9% | 85.4% | total |
| Demons vs Tigers | +39.0 | +59.1 | +20.1 | 154.1 | 195.7 | 86.1% | 98.8% | margin+H2H+total |
| Lions vs Bombers | +55.3 | +82.4 | +27.1 | 163.8 | 195.9 | 93.8% | 97.7% | margin+total |

### Model-alignment check (standing betting rule)

- **Handicap direction (winner pick): rules and ML agree on all 9 games.** Note this REVERSES the Jul 7 finding — the old models had Sydney beating Fremantle; the new EMA models have Fremantle +7.1. The game is no longer a hard model-disagreement avoid, but a 21-point margin gap on a 5.5-goal favourite is still a low-confidence line.
- **H2H disagreements — 2 games OFF-LIMITS for H2H:**
  - **GWS vs Geelong** — rules 30.3% home vs ML 54.6% home (ML internally split: margin says Cats, H2H leans Giants).
  - **Carlton vs Hawthorn** — rules 28.8% home vs ML 51.9% home (same internal split).
  - Caveat: the H2H classifier's `mkt_home_prob_open` feature ran on its ELO fallback (no live odds), which drags probabilities toward 50%. Re-check both once the odds feed is restored before treating them as final vetoes.

---

## T9 Matrix Confluence — Summary

| Game | Best signal | Direction | Ways | Agrees w/ rules+ML pick? |
|------|------------|-----------|------|--------------------------|
| **Collingwood vs Nth Melb** | H2H | BACK HOME (Magpies) | 8-way, incl. four 100% splits | **Yes — strongest clean alignment of the round** |
| Fremantle vs Sydney | Handicap | AWAY COVERS (Sydney) | 6-way, incl. 100% "Swans at Optus" | No — and ML's +7.1 sits far closer to the matrix than rules' +28.5. Caution on the Dockers line |
| Adelaide vs Gold Coast | Handicap | HOME COVERS (Crows) | 6-way | **Yes — best clean handicap alignment** (rules +26.9, ML +27.3 near-identical) |
| Melbourne vs Richmond | H2H | BACK HOME (Demons) | 6-way, incl. 100% "Tigers vs Melbourne" | **Yes** |
| W. Bulldogs vs West Coast | H2H | BACK HOME (Bulldogs) | 5-way | **Yes** (huge favourite — limited value) |
| Carlton vs Hawthorn | Handicap | AWAY COVERS (Hawks) | 4-way | Yes on handicap — but H2H is model-disagreement, avoid H2H |
| Brisbane vs Essendon | Handicap | AWAY COVERS (Bombers) | 4-way | Fade-the-line signal vs a 55.3 model margin; ML (+82!) says the opposite. EMA features are punishing Essendon's freefall hard |
| St Kilda vs Port Adelaide | H2H | BACK AWAY (Port) | 3-way | No — matrix leans Power, rules+ML lean Saints. Caution, not veto |
| GWS vs Geelong | H2H | BACK HOME (Giants) | 3-way, incl. noisy 123.5% row | Matrix + ML H2H both lean Giants vs rules' Cats — genuinely murky, avoid |

---

## Top signals (rules + ML agree, matrix backs it)

1. **Adelaide -26.9 vs Gold Coast** — 6-way handicap matrix, rules/ML within 0.4 pts of each other. Cleanest signal of the round. (Note: this number no longer includes any Dawson emotional boost — it's pure football.)
2. **Collingwood vs North Melbourne (Magpies H2H / -20.3)** — 8-way H2H matrix incl. four 100% historical splits, rules+ML agree, ML even more bullish (+30.3).
3. **Melbourne -39.0 vs Richmond** — 6-way matrix incl. 100% Tigers-vs-Melb split, rules+ML agree (ML +59 — extreme, treat the ML size as EMA-driven Richmond-freefall signal, not a literal margin).
4. **Hawthorn -20.1 at Carlton (handicap only)** — 4-way matrix, margins aligned (-20.1/-32.5). H2H is off-limits per the alignment rule.

**Avoid:** GWS vs Geelong (H2H model disagreement + matrix backs Giants against rules), Carlton vs Hawthorn H2H (model disagreement).
**Caution:** Fremantle -28.5 (matrix 6-way against incl. a 100% split, ML 21 pts lower), St Kilda vs Port (matrix leans against, both lists gutted), Brisbane -55.3 (extreme-ELO-gap overcook risk + 4-way matrix fade).

---

## Key Injury Notes (T5)

- **GWS again carries the competition's heaviest list**: Tom Green (season, re-confirmed), Jesse Hogan, Joshua Kelly — three elite absentees, compound penalty applied.
- **St Kilda has four elite outs** (Flanders, King, Sinclair, De Koning) vs Port missing Rozee (season) + six others. Both sides hurting — whole game low-confidence.
- **Carlton missing captain Jacob Weitering** (elite key defender) vs Hawthorn.
- **Collingwood missing captain Darcy Moore** (elite key defender) vs North Melbourne.
- **Brisbane: Payne (season — confirmed this week), Gardiner (new, hamstring), McCarthy, Allen out — but McCluggage and Zorko RETURN** vs Essendon.
- **Western Bulldogs missing Sam Darcy** (elite key forward, season) — West Coast's 8 outs are all sub-elite.
- **Melbourne missing Jack Viney** (elite midfielder) vs Richmond.

---

## Assumptions / Data Risk Flags

- **No market lines anywhere in this analysis** — Odds API key deactivated. EV, edges, CLV baselines and bet selection are all blocked until it's replaced. This also means `mkt_home_prob_open` (a model feature) ran on its ELO fallback — ML H2H probabilities are softer than they'd be with a live market anchor.
- **T5 position/quality tags are manual judgement calls**, not scraped. Directionally right, not decimal-precise.
- **Sydney's "Max King" entry** is distinct from St Kilda's Max King — unverified, held at average tier.
- **Extreme-ELO-gap games** (Lions -55.3, Bulldogs -44.0, Demons -39.0) carry the documented linear-ELO overcook risk (sigmoid rescale still backlogged). Unusually, the new ML is even MORE bullish than rules on Lions/Demons — the EMA form features are hammering Essendon and Richmond's current freefalls.
- **Saturday wind docks (-6.0 totals at three venues)** assume the 22–25 km/h forecast holds — re-check T7 game morning.
