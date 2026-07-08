# AFL R17 2026 — Pricing Analysis

**Generated:** 2026-07-02 (full tiered re-price — fresh injuries, fresh emotional scrape, ELO rebuilt on latest historical xlsx)
**Model version:** 1.0.0 (T1–T7 rules + ML shadow, XGBoost trained 2009–2023)
**Byes:** None — all 18 teams playing.
**Market source:** Odds snapshot 2026-07-02 12:00 (10 bookmakers, median line used)

---

## What changed in this re-price

- **Footywire injury scrape failed (503 Service Unavailable)** — used the existing curated injury file (last successfully scraped 2026-06-30) as the base.
- **Cross-checked against a fresh AFL emotional-flags scrape (Claude + Google News, run today)** and found **Jordan Dawson (Adelaide's captain, elite midfielder) missing from the injury list** — he is out of the West Coast clash following the death of his brother. Added to T5 manually. This materially moved the Eagles vs Crows price (T5 handicap shifted from +6.0 to -2.0 for the home team; final model margin moved from Crows -39.5 to Crows -36.5).
- **AFL ELO rebuilt** from `latest.xlsx` (Jun 30 download, 3488 games, 990 in the 2022+ deploy window) before pricing.
- **T7 weather pulled fresh from Tomorrow.io** for all 6 distinct venues in use this round.
- **T9 matrix confluence run** across H2H, handicap and totals matrices for all 9 games.

---

## Prices at a Glance

| Game | Date | Venue | Model H2H | Model Hcap | Market Hcap | Model Total | Market Total |
|------|------|-------|-----------|------------|-------------|-------------|--------------|
| **Geelong** vs Brisbane | Thu 2 Jul | GMHBA | 1.26 / 4.90 | Cats -29.8 | Cats -14.5 | 197.2 | 171.0 |
| **Sydney** vs W. Bulldogs | Fri 3 Jul | SCG | 1.25 / 5.02 | Swans -30.4 | Swans -16.5 | 177.2 | 184.5 |
| West Coast vs **Adelaide** | Fri 3 Jul | Optus | 6.45 / 1.18 | Crows -36.5 | Crows -32.5 | 151.8 | 171.0 |
| Gold Coast vs **Collingwood** | Sat 4 Jul | People First | 1.72 / 2.39 | Suns -7.4 | Suns -8.5 | 168.4 | 173.5 |
| GWS vs **Fremantle** | Sat 4 Jul | ENGIE | 3.36 / 1.42 | Dockers -19.2 | Dockers -20.5 | 192.5 | 177.0 |
| **Hawthorn** vs Melbourne | Sat 4 Jul | MCG | 1.26 / 4.92 | Hawks -29.9 | Hawks -14.5 | 172.3 | 168.0 |
| Richmond vs **Carlton** | Sat 4 Jul | MCG | 3.90 / 1.34 | Blues -23.6 | Blues -35.5 | 151.7 | 168.5 |
| Essendon vs **St Kilda** | Sun 5 Jul | Marvel | 3.47 / 1.41 | Saints -20.1 | Saints -29.5 | 150.2 | 177.5 |
| **Port Adelaide** vs Nth Melb | Sun 5 Jul | Adelaide Oval | 1.97 / 2.04 | Power -0.8 | Power -17.0 | 149.7 | 172.0 |

**Bold = model's pick to win.**

---

## Tier Breakdown (Handicap — home perspective)

| Game | ELO gap | T1 | T2 | T3 | T4 | T5 | T6 | T7wx | Final |
|------|---------|----|----|----|----|----|----|------|-------|
| Cats vs Lions | +77 | +16.4 | +4.0 | +4.9 | +3.0 | +3.5 | -2.0 | -6.0 | **+29.8** |
| Swans vs Bulldogs | +152 | +23.2 | +4.0 | +1.7 | +3.0 | -1.5 | +0.0 | -6.0 | **+30.4** |
| Eagles vs Crows | -436 | -29.8 | -4.0 | +6.0 | -3.0 | -2.0 | -3.8 | +0.0 | **-36.5** |
| Suns vs Magpies | -39 | +5.9 | +4.0 | +0.0 | -4.0 | -0.5 | +2.0 | +0.0 | **+7.4** |
| Giants vs Dockers | -273 | -15.1 | -1.1 | +2.5 | +2.5 | -8.0 | +0.0 | +0.0 | **-19.2** |
| Hawks vs Demons | +178 | +22.7 | +3.1 | -1.5 | +0.0 | +5.5 | +0.0 | +0.0 | **+29.9** |
| Tigers vs Blues | -286 | -19.1 | -4.0 | +1.0 | +0.0 | -1.5 | +0.0 | +0.0 | **-23.6** |
| Bombers vs Saints | -273 | -18.0 | -4.0 | -1.5 | +0.0 | +3.4 | +0.0 | +0.0 | **-20.1** |
| Power vs Kangaroos | -14 | +8.2 | -4.0 | +1.1 | +1.5 | -4.5 | -1.5 | +0.0 | **+0.8** |

*T2 hit its ±4.0 cap on 5 of 9 games this round — the model's style-matchup layer cannot express separation beyond that regardless of how lopsided the underlying stats are.*

---

## ML Shadow Divergences

| Game | Rules Mrg | ML Mrg | Gap | Rules Tot | ML Tot | Flag |
|------|-----------|--------|-----|-----------|--------|------|
| Cats vs Lions | +29.8 | +15.2 | -14.6 | 197.2 | 140.0 | margin+H2H+total |
| Swans vs Bulldogs | +30.4 | +16.4 | -14.0 | 177.2 | 152.0 | margin+H2H+total |
| Eagles vs Crows | -36.5 | -18.2 | +18.3 | 151.8 | 165.0 | margin+H2H+total |
| Suns vs Magpies | +7.4 | +10.0 | +2.6 | 168.4 | 158.5 | H2H+total |
| Giants vs Dockers | -19.2 | -19.8 | -0.6 | 192.5 | 162.2 | total only |
| Hawks vs Demons | +29.9 | +23.3 | -6.6 | 172.3 | 178.3 | margin |
| Tigers vs Blues | -23.6 | -24.3 | -0.7 | 151.7 | 169.4 | total only |
| Bombers vs Saints | -20.1 | -20.5 | -0.4 | 150.2 | 161.5 | H2H+total |
| Power vs Kangaroos | +0.8 | -9.4 | -10.2 | 149.7 | 153.8 | margin+H2H |

**Every game except Power vs North Melbourne has rules and ML pointing the same direction.** Power vs Kangaroos is the one true model disagreement this round — rules calls it a coin flip, ML calls Kangaroos, and per the standing betting rule that means the game is off-limits for a handicap or H2H bet regardless of what the market or matrix says.

---

## T9 Matrix Confluence

| Game | Signal | Direction | Ways |
|------|--------|-----------|------|
| Cats vs Lions | Handicap | HOME COVERS (Cats) | 4-way |
| Swans vs Bulldogs | Handicap | HOME COVERS (Swans) | 3-way |
| **Eagles vs Crows** | **H2H** | **BACK AWAY (Crows)** | **6-way, incl. 100% "vs Adelaide"** |
| **Eagles vs Crows** | **Handicap** | **AWAY COVERS (Crows)** | **5-way** |
| Eagles vs Crows | Totals | OVERS | 3-way (weak, <10% edges) |
| Eagles vs Crows | Handicap | HOME COVERS (Eagles) | 3-way (conflicts with the 5-way above — home-side splits are thin) |
| Hawks vs Demons | Handicap | HOME COVERS (Hawks) | 5-way |
| Hawks vs Demons | Totals | UNDERS | 3-way |
| Giants vs Dockers | Handicap | AWAY COVERS (Dockers) | 3-way |
| Tigers vs Blues | Totals | UNDERS | 3-way (weak, <6% edges) |
| Bombers vs Saints | Handicap | HOME COVERS (Bombers) | 3-way |
| **Power vs Kangaroos** | **H2H** | **BACK HOME (Power)** | **8-way, incl. 100% "vs Port Adelaide" and 100% "Adelaide Oval"** |
| Power vs Kangaroos | Handicap | HOME COVERS (Power) | 3-way |

Eagles vs Crows and Power vs Kangaroos both threw the biggest confluence stacks of the round. They point opposite ways on the model-alignment test: Eagles/Crows has rules+ML agreeing (both favour Crows) so the matrix reinforces a real signal; Power/Kangaroos has rules+ML disagreeing, so the matrix signal here is decision-support only — it does not override the model conflict.

---

## Injury Notes (T5)

**Adelaide Crows** — Luke Pedlar (average utility) already out; **Jordan Dawson (elite midfielder, captain) added today** — out for the West Coast game following a family bereavement, confirmed via the emotional-flags news scan and not yet reflected in Footywire's list. This alone moved the Eagles/Crows T5 handicap from +6.0 (Eagles) to -2.0 (Crows), a ~3pt swing in Crows' favour on top of what was already a heavy ELO mismatch.

**Greater Western Sydney Giants** — heaviest injury list of the round. Three elite absentees: Tom Green (midfielder, season-ending — re-confirmed this week per the CRITICAL DATA ENTRY RULE, since season-enders don't carry forward automatically), Jesse Hogan (key forward), Joshua Kelly (midfielder), plus 8 more rotation-tier outs. T5 -8.0 hcap, the largest injury adjustment of the round (⚡ compound penalty, 2+ key players out).

**Essendon Bombers** — 10 players out but only depth-tier (2 good, 8 average) — no elite absentees. T5 actually favours Essendon (+3.4) net of St Kilda's own list.

**St Kilda Saints** — four elite outs: Sam Flanders (midfielder, season), Max King (key forward), Jack Sinclair (key defender), Tom De Koning (ruck, bruised lung). Despite this, market still has Saints -29.5 — their depth is evidently still rated well above Essendon's.

**Hawthorn vs Melbourne** — Melbourne's list is worse (9 outs incl. Jack Viney elite mid, 3 more good-tier) vs Hawthorn's 5 (2 good-tier). T5 +5.5 to Hawthorn is the single biggest T5 in the round after Giants/Dockers.

**Port Adelaide** — Connor Rozee (elite midfielder, season-ending, hamstring) still out — correctly carried forward.

Full team-by-team T5 outs are in the pricing run output; nothing else stood out as materially mispriced against what the emotional scan and current fixture cross-check surfaced.

---

## Emotional Notes (T6)

Fresh scrape run today (Claude + Google News), 4 flags validated for R17:

- **Adelaide Crows — personal_tragedy (major):** Jordan Dawson's bereavement. Team expected to rally around their captain. +2.5 hcap bump applied for Adelaide (shows as part of the -3.8 T6 in the Eagles/Crows row, home-perspective negative = Crows favoured).
- **North Melbourne Kangaroos — farewell (normal):** a retiring player being honoured ahead of the Port Adelaide game. Small bump to Kangaroos, shows as -1.5 T6 in the Power/Kangaroos row.
- **Gold Coast Suns — must_win (normal):** finals-defining framing vs Collingwood, despite Suns being hit by the Rioli/Gulbin injuries and Clohesy suspension. +2.0 T6 to Suns.
- **Brisbane Lions — must_win (normal):** Grand Final rematch vs Geelong billed as high-stakes; Lions coming off a 52-pt win but banged up. -2.0 T6 in the Cats/Lions row (home-perspective negative = Lions boosted).

---

## Weather (T7)

| Venue | Temp | Wind | Precip | Condition | Games affected |
|-------|------|------|--------|-----------|-----------------|
| GMHBA Stadium | 11.4°C | 27.0 km/h | 0.0mm | **strong_wind** | Cats vs Lions (-6.0 total) |
| SCG | 17.3°C | 25.2 km/h | 0.0mm | **strong_wind** | Swans vs Bulldogs (-6.0 total) |
| Optus Stadium | 16.5°C | 12.2 km/h | 0.0mm | clear | Eagles vs Crows (no adj) |
| MCG | 10.9°C | 12.6 km/h | 0.0mm | clear | Hawks vs Demons, Tigers vs Blues (no adj) |
| ENGIE Stadium | 16.2°C | 1.4 km/h | 0.0mm | clear | Giants vs Dockers (no adj) |
| People First Stadium | 19.0°C | 12.2 km/h | 0.0mm | clear | Suns vs Magpies (no adj) |
| Marvel Stadium | 12.4°C | 13.3 km/h | 0.0mm | clear | Bombers vs Saints (no adj, roof) |
| Adelaide Oval | 13.2°C | 8.6 km/h | 0.0mm | clear | Power vs Kangaroos (no adj) |

Only the two Thursday/Friday openers (GMHBA, SCG) get a real wind adjustment this round — both -6.0 on totals.

---

## Game-by-Game Read

### Geelong vs Brisbane — Thu, GMHBA
Rules: Cats -29.8 | ML: Cats -15.2 | Market: Cats -14.5

ML sits almost exactly on the market line while rules runs nearly double. This is the recurring extreme-ELO overcook pattern (T1 alone was only +16.4 off a modest +77 ELO gap, but T2/T3/T4/T5 all stacked in Geelong's favour and T2 hit its +4.0 cap). Matrix gives a 4-way HOME COVERS lean, but with ML barely clearing the number there's minimal real edge.

- **Handicap: thin lean Cats -14.5.** ML clears the market number by only 0.7pt — not enough to call it a strong signal on its own, but every model, the matrix, and the market direction all agree Geelong wins comfortably.
- **Totals: SKIP.** Rules 197.2 vs ML 140.0 vs market 171.0 — a 57pt rules/ML spread. No usable signal.

---

### Sydney vs Western Bulldogs — Fri, SCG
Rules: Swans -30.4 | ML: Swans -16.4 | Market: Swans -16.5

ML lands within 0.1pt of the market line. Market is efficiently priced here; rules is the outlier (again, ELO gap of only +152 turning into a 30pt line via tier stacking). No edge.

- **Handicap: SKIP.** Market already matches the more reliable ML read almost exactly.
- **Totals: SKIP.** Rules 177.2 vs ML 152.0 vs market 184.5 — 33pt rules/ML spread.

---

### West Coast vs Adelaide — Fri, Optus Stadium
Rules: Crows -36.5 | ML: Crows -18.2 | Market: Crows -32.5

The round's headline game. West Coast are last in the AFL (ELO 1217) and Adelaide sit mid-table (1654), a 436-point gap — the largest of the round. Both models agree Adelaide win comfortably even after losing their captain today (Dawson). The matrix throws the biggest confluence stack of the round on this exact matchup: **6-way H2H (100% historical "vs Adelaide" split)** and **5-way handicap**, both backing Crows.

Model H2H (Crows 1.18) matches the market (Crows 1.18) almost exactly — this market is efficiently priced on the head-to-head, so there's no H2H value play here despite the matrix strength; it's confirmation, not an overlay.

On the handicap, rules (-36.5) sits above the market number (-32.5) while ML (-18.2) sits well below it — a genuine 18pt rules/ML gap, the second-largest of the round. Direction is aligned (both favour Crows), which is what the betting rule requires, but the size of the disagreement means conviction on the exact number should stay moderate.

- **Handicap: Adelaide -32.5 — moderate signal.** Rules exceeds the market line, matrix gives the strongest confluence of the round in the same direction, and the personal-tragedy rally flag (T6) is already baked in. ML's much smaller number is the caution here — treat as moderate, not high, confidence.
- **Totals: SKIP.** Rules 151.8 is well under both ML (165.0) and market (171.0) — likely the compounding effect of West Coast's 8 outs plus Adelaide's 2, worth a flag for review but not actionable today.

---

### Gold Coast vs Collingwood — Sat, People First Stadium
Rules: Suns -7.4 | ML: Suns -10.0 | Market: Suns -8.5

Tightly calibrated — rules, ML and market all sit within 2.6pts of each other. Efficient market, no handicap edge.

- **Handicap: SKIP.** Fairly priced.
- **Totals: lean UNDER 173.5, low-medium.** Rules 168.4 and ML 158.5 both sit under the market line — aligned direction, 5–15pt gap. Suns' must_win emotional bump (T6 +2.0) is on margin not total, so doesn't offset this.

---

### GWS vs Fremantle — Sat, ENGIE Stadium
Rules: Dockers -19.2 | ML: Dockers -19.8 | Market: Dockers -20.5

Best-calibrated game of the round — rules and ML agree to within 0.6pt of each other and both sit within 1.3pts of market. GWS's brutal injury list (Green, Hogan, Kelly all elite outs, T5 -8.0 — the round's biggest) is already fully priced by both models and the market agrees. Matrix gives a 3-way AWAY COVERS lean, consistent but the number is already fair.

- **Handicap: SKIP — efficiently priced.** No edge either side.
- **Totals: SKIP.** Rules 192.5 vs ML 162.2 — 30pt spread, no clean read.

---

### Hawthorn vs Melbourne — Sat, MCG
Rules: Hawks -29.9 | ML: Hawks -23.3 | Market: Hawks -14.5

Both models clear the market number comfortably (by 8.8pts even using the conservative ML figure) — the best "genuine value" case of the round outside of Eagles/Crows. Melbourne's list (9 outs incl. Jack Viney) is worse than Hawthorn's, and the model has already loaded that in (+5.5 T5 to Hawthorn). Matrix backs it too: 5-way HOME COVERS.

- **Handicap: Hawthorn -14.5 — moderate-high confidence.** Rules, ML and matrix all agree, and even the conservative ML number clears the market line by a real margin.
- **Totals: mild OVER lean, low confidence.** Rules 172.3 and ML 178.3 both sit above the market's 168.0, but the gap is modest and matrix actually points UNDER (3-way) — conflicting signals, treat as informational only.

---

### Richmond vs Carlton — Sat, MCG
Rules: Blues -23.6 | ML: Blues -24.3 | Market: Blues -35.5

Rules and ML agree tightly with each other (0.7pt apart) but both sit ~11–12pts short of the market. Richmond are bottom of the ladder (ELO 1172, the lowest in the competition) and this is exactly the profile where the documented ELO→margin calibration gap shows up worst (see backlog: linear conversion under-separates at extreme ELO gaps; T2 is also capped at ±4.0 and hit that cap here, meaning the model literally cannot express more separation via style stats even though the underlying numbers would support it).

- **Handicap: NO SIGNAL — calibration caution, not a bet.** This isn't "value on Richmond," it's the model hitting a known structural limit at extreme ELO gaps. Treat the -35.5 market line as more likely correct than the model here.
- **Totals: SKIP.** Rules 151.7 vs ML 169.4 — 18pt spread.

---

### Essendon vs St Kilda — Sun, Marvel Stadium
Rules: Saints -20.1 | ML: Saints -20.5 | Market: Saints -29.5

Same pattern as Richmond/Carlton — rules and ML agree closely (0.4pt) but both sit ~9pts short of market. Essendon's 10 outs are all depth-tier (no elite), while St Kilda's 4 elite outs are already priced in and the model still doesn't get near the market's number. Same calibration caution applies.

- **Handicap: NO SIGNAL — same calibration caution as Richmond/Carlton.**
- **Totals: SKIP.** Rules 150.2 vs ML 161.5 — 11pt spread, and Essendon's roster of depth-only outs makes this genuinely hard to project.

---

### Port Adelaide vs North Melbourne — Sun, Adelaide Oval
Rules: Power +0.8 | ML: Kangaroos -9.4 | Market: Power -17.0

**The only game this round where rules and ML disagree on winner.** Rules calls it a pick'em; ML actively favours the Kangaroos; the market has Port as big home favourites. The matrix throws an 8-way H2H confluence (including two 100% historical splits — "vs Port Adelaide" and "Adelaide Oval") backing Power, which on its own would look like the strongest signal of the round.

Per the standing betting rule, model disagreement on direction is a hard stop regardless of what the matrix says — the matrix numbers here are historical situational splits, not a substitute for the pricing models agreeing. **Do not bet either side of this game.**

- **Handicap / H2H: AVOID.** Rules vs ML disagree on the winner outright.
- **Totals: SKIP.** Rules 149.7 vs ML 153.8 vs market 172.0 — both models well under market, but with the win-direction disagreement, no confidence in the underlying scoring model for this game either.

---

## Signal Summary

| Game | Signal | Side | Market Price | Confidence |
|------|--------|------|---------------|------------|
| **Eagles vs Crows** | Handicap | **Adelaide -32.5** | ~1.90 | Moderate — 6-way H2H + 5-way handicap matrix, rules exceeds market, but 18pt rules/ML gap caps conviction |
| **Hawks vs Demons** | Handicap | **Hawthorn -14.5** | ~1.90 | Moderate-high — rules AND ML both clear market by 9pt+, matrix backs it 5-way |
| Gold Coast vs Collingwood | Totals | **UNDER 173.5** | ~2.00 | Low-medium — rules and ML both below market |
| Cats vs Lions | Handicap | Geelong -14.5 | ~1.90 | Low — ML barely clears market, matrix says yes, don't lean hard |

**No bet:** Swans/Bulldogs, Giants/Dockers (efficiently priced), Richmond/Carlton, Essendon/St Kilda (model calibration caution at extreme ELO gaps — market more likely correct), **Power/Kangaroos (rules vs ML disagree on winner — hard avoid despite the round's biggest matrix confluence)**.

---

## Key Caveats

**Footywire injuries down (503) at scrape time.** Base injury data is from the 2026-06-30 curated file, cross-checked (and one gap fixed — Jordan Dawson) against a fresh emotional-flags news scan today. Re-scrape before kickoff if Footywire comes back up, particularly for Friday/weekend games where late outs could still emerge.

**Extreme-ELO-gap underestimation confirmed again this round** (Richmond/Carlton, Essendon/St Kilda) — both cases rules and ML agree closely with each other but sit 9–12pts short of market. This matches the documented backlog item: linear `POINTS_PER_ELO` conversion and the T2 ±4.0 cap can't express enough separation for genuinely one-sided matchups. Sigmoid ELO→margin scaling (`(win_prob − 0.5) × ~90-100`) remains the flagged fix, not yet built.

**Totals model is noisy this round** — 6 of 9 games have rules vs ML total gaps of 17pts or more. Not using totals as a primary signal except where both rules and ML independently sit on the same side of market (Suns/Magpies UNDER was the only clean case).

**T2 cap hit on 5/9 games** (±4.0) — Cats/Lions, Swans/Bulldogs, Eagles/Crows, Suns/Magpies, Tigers/Blues. Worth reviewing whether the cap is too tight for genuinely extreme style mismatches, separate from the ELO-scaling fix.

---

## Previous Round Reference
- R16 (Jun 26–29): no md filed this cycle — see `results/r16_afl_2026.csv` for raw prices.
- Recurring theme across R14–R17: rules model runs hot on moderate ELO gaps (overcooks favourites like Cats/Lions, Swans/Bulldogs, Hawks/Demons) but runs cold on the most extreme gaps (undercooks Richmond/Carlton, Essendon/St Kilda-type blowouts). ML shadow is the more reliable cross-check in both directions until the sigmoid rescale ships.
