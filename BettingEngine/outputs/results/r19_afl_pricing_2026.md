# AFL R19 2026 — Pricing Analysis

**Generated:** 2026-07-16 (re-priced same day to add the new T8 kicking-accuracy tier)
**Model version:** T1–T8 rules + ML shadow (Jul 5 EMA/split-feature XGBoost, models trained through Jul 8, unchanged this round)
**Byes:** None — all 18 teams playing.
**Market source:** ⚠️ **NONE — Odds API still down, latest snapshot is 2026-07-03 (13 days old), 0/9 games matched.** Fair prices are complete but there is no market line to compare against — no EV, no bet sizing, until the feed is restored.

This round required building the R19 round-prep files from scratch (fixture, injuries, emotional flags) — none existed yet. Fixture confirmed via web search against the official AFL Round 19 schedule (Thu Jul 16 – Sun Jul 19). Injuries scraped fresh from Zero Tackle-equivalent AFL source (139 raw records) and manually tagged for position/quality — the scraper does not supply either field, same limitation as every prior round.

**New this run — T8 kicking accuracy tier.** Built and wired in today (`pricing/afl_tier8_kicking.py`): a capped ±4pt adjustment based on each team's season-to-date goal-kicking conversion rate vs the 2026 league average (52.2%), sourced from goals/behinds in the same historical xlsx the ELO rebuild uses. This is the lightweight stop-gap version of the "set-shot conversion tracker" backlog item — it nudges the current round's price, it does **not** change how ELO itself is built from history. The deeper fix (feed `scoring_shots × 3.70` into the ELO update itself) is banked for the 2026 off-season per the earlier discussion — this tier doesn't replace that plan. All numbers below are the T8-adjusted re-price; the original T1–T7-only prices from earlier today are superseded.

---

## Tier Coverage Report (mandatory)

| Tier | Status | Detail |
|------|--------|--------|
| T1 — ELO baseline | ✅ REAL | Rebuilt today on the historical xlsx (dated Jul 14, includes all R18 results through Jul 12). Season calibration n=153: margin +5.1, total -3.5 |
| T2 — Style matchup | ✅ REAL | Footywire snapshot already fresh for R19 (dated Jul 14) — no re-scrape needed |
| T3 — Situational | ✅ REAL | Rest/travel/form/occasion from fixture + history |
| T4 — Venue | ✅ REAL | Fortress fired: Cats +3.0, Swans +3.0, Power +1.5, Magpies +2.5, Eagles -3.0, Suns -4.0 |
| T5 — Injuries | ✅ REAL (manually tagged) | 139 fresh records scraped this morning, position/quality assigned by football knowledge (scraper limitation, unchanged from every prior round). Compound ⚡ penalties on Cats/Saints, Power/Dockers, and Bombers/Giants (2+ key absences each side) |
| T6 — Emotional | ✅ REAL (1 manual addition) | 2 deterministic rivalry flags (Collingwood/Carlton, Richmond/Hawthorn) + Essendon shame_blowout (major) added manually after the scraper's Claude layer returned truncated/invalid JSON **twice in a row** — see risk flags below, this needs a fix |
| T7 — Weather | ✅ REAL | Live Tomorrow.io, all 9 venues, re-fetched on this re-price. Moderate wind at Optus (Eagles/Lions) and People First (Suns/Bulldogs), -2.8 totals each — People First dropped from "strong" to "moderate" between the two fetches (20.2km/h vs 21.2km/h, live forecast drift, not a bug) |
| T8 — Kicking accuracy | ✅ REAL (new this session) | Season-to-date conversion vs 2026 league avg (52.2%), all 18 teams have enough shots for a signal. Capped ±4pt. Biggest movers: Power/Dockers (-2.81 hcp, Port's 47.1% conversion compounds their injury crisis), Eagles/Lions (-3.34), Bombers/Giants (-2.18) |
| ML shadow | ✅ REAL | Same Jul 8 EMA/split-feature models, fresh features computed off today's ELO rebuild. ML margin/total now also carry T8 (same as T2/T5/T6/T7 pattern); ML H2H probability is raw XGBoost, unaffected by any tier |
| T9 — Matrix confluence | ✅ REAL | All 3 matrices, 8/9 games with 3+ way signals, JSON exported and pushed to Supabase |

**Coverage: 10/10 tiers in scope genuinely populated — 100%, no silent defaults.** The one thing that could not be produced: **market comparison** — Odds API has been down since Jul 3, so there's nothing to check these fair prices against.

---

## Prices at a Glance (fair prices — no market lines available)

| Game | Date | Venue | Fair H2H | Fair Hcap | Fair Total |
|------|------|-------|----------|-----------|------------|
| **Geelong Cats** vs St Kilda | Thu 16 Jul | GMHBA | 1.21 / 5.87 | Cats -34.3 | 178.1 |
| **Sydney Swans** vs Adelaide | Fri 17 Jul | SCG | 1.30 / 4.36 | Swans -26.7 | 191.7 |
| Port Adelaide vs **Fremantle** | Sat 18 Jul | Adelaide Oval | 4.67 / 1.27 | Dockers -28.5 | 161.8 |
| Nth Melbourne vs **Melbourne** | Sat 18 Jul | Marvel | 2.47 / 1.68 | Demons -8.7 | 164.7 |
| **Collingwood** vs Carlton | Sat 18 Jul | MCG | 1.40 / 3.49 | Magpies -20.3 | 163.4 |
| West Coast vs **Brisbane** | Sat 18 Jul | Optus | 9.43 / 1.12 | Lions -44.9 | 163.0 |
| Richmond vs **Hawthorn** | Sun 19 Jul | MCG | 6.74 / 1.17 | Hawks -37.6 | 154.6 |
| **Gold Coast** vs W. Bulldogs | Sun 19 Jul | People First | 1.80 / 2.25 | Suns -5.0 | 152.2 |
| Essendon vs **GWS Giants** | Sun 19 Jul | Marvel | 3.66 / 1.38 | Giants -21.7 | 154.6 |

**Bold = model's pick to win.**

---

## Tier Breakdown (Handicap — home perspective)

| Game | ELO gap | T1 | T2 | T3 | T4 | T5 | T6 | T7wx | T8 | Final |
|------|---------|----|----|----|----|----|----|------|----|-------|
| Cats vs Saints | +235 | +30.4 | +4.0 | +0.1 | +3.0 | -4.0 | +0.0 | +0.0 | +0.7 | **+34.3** |
| Swans vs Crows | +75 | +16.0 | +4.0 | +5.4 | +3.0 | -1.5 | +0.0 | +0.0 | -0.2 | **+26.7** |
| Power vs Dockers | -304 | -18.2 | -4.0 | +3.0 | +1.5 | -8.0 | +0.0 | +0.0 | -2.8 | **-28.5** |
| Kangaroos vs Demons | -178 | -9.6 | -4.0 | +2.5 | +0.0 | +4.0 | +0.0 | +0.0 | -1.6 | **-8.7** |
| Magpies vs Blues | +97 | +15.2 | +2.5 | -1.5 | +2.5 | -1.5 | +1.5 | +0.0 | +1.6 | **+20.3** |
| Eagles vs Lions | -520 | -37.6 | -4.0 | +6.0 | -3.0 | -3.0 | +0.0 | -2.8 | -3.3 | **-44.9** |
| Tigers vs Hawks | -477 | -36.5 | -4.0 | +2.0 | +0.0 | +1.0 | +1.5 | +0.0 | -1.6 | **-37.6** |
| Suns vs Bulldogs | -78 | +2.2 | +2.8 | +1.5 | -4.0 | +2.0 | +0.0 | -2.8 | +0.5 | **+5.0** |
| Bombers vs Giants | -388 | -28.5 | -4.0 | +2.7 | +0.0 | +8.0 | +2.2 | +0.0 | -2.2 | **-21.7** |

Injury highlight (unchanged): **Port Adelaide's midfield is gone** — Butters (elite), Rozee (elite, season), Horne-Francis (elite, suspended) all out simultaneously against Fremantle. T5 -8.0 is the single biggest injury swing of the round — and now T8 compounds it: Port's own conversion rate (47.1%, well below the 52.2% league average) adds another -2.8 on top, taking the Dockers line from -25.7 to -28.5. Two independent tiers pointing the same way on the same team is worth noting.

---

## ML Shadow (EMA/split-feature models; margin/total now also carry T8, same pattern as T2/T5/T6/T7)

| Game | Rules Mrg | ML Mrg | MrgΔ | Rules Tot | ML Tot | TotΔ | Rules H% | ML H% | Flag |
|------|-----------|--------|------|-----------|--------|------|----------|-------|------|
| Cats vs Saints | +34.3 | +21.4 | -12.9 | 178.1 | 168.1 | -10.0 | 83.0% | 63.7% | margin+H2H+total |
| Swans vs Crows | +26.7 | +9.6 | -17.1 | 191.7 | 157.5 | -34.2 | 77.1% | 56.7% | margin+H2H+total |
| Power vs Dockers | -28.5 | -35.2 | -6.7 | 161.8 | 155.3 | -6.5 | 21.4% | 36.2% | margin+H2H |
| Kangaroos vs Demons | -8.7 | +0.5 | +9.2 | 164.7 | 167.4 | +2.7 | 40.4% | 65.3% | margin+H2H |
| Magpies vs Blues | +20.3 | +16.3 | -4.0 | 163.4 | 177.1 | +13.7 | 71.3% | 58.6% | H2H+total |
| Eagles vs Lions | -44.9 | -36.3 | +8.6 | 163.0 | 172.3 | +9.3 | 10.6% | 35.4% | margin+H2H+total |
| Tigers vs Hawks | -37.6 | -46.7 | -9.1 | 154.6 | 170.9 | +16.3 | 14.8% | 10.6% | margin+total |
| Suns vs Bulldogs | +5.0 | -13.2 | -18.2 | 152.2 | 147.2 | -5.0 | 55.6% | 43.6% | margin+H2H |
| Bombers vs Giants | -21.7 | -18.1 | +3.6 | 154.6 | 147.2 | -7.4 | 27.3% | 17.6% | H2H |

**ML H2H% is unaffected by T8** — it's the raw XGBoost probability, no tier ever touches it. Only Rules H% shifted (via final_margin), and only by the same small amount T8 contributed to each game's margin.

### Model-alignment check (standing betting rule)

**7 of 9 games have rules and ML agreeing on the winner — unchanged by adding T8. 2 games are still off-limits for every market:**

- **North Melbourne vs Melbourne** — rules has **Demons** favoured (40.4% home = Kangaroos underdog), ML has **Kangaroos** favoured (65.3% home). A genuine winner disagreement, not just a size gap. **No play on H2H, handicap, or totals.**
- **Gold Coast vs Western Bulldogs** — rules has **Suns** favoured (55.6%), ML has **Bulldogs** favoured (43.6% home). Same situation. **No play.** This is also the one game with zero T9 matrix signal (see below) — the least-supported price of the round from every angle.

Every other game agrees on winner direction even where the *size* of the margin diverges hard (Cats/Saints and Swans/Crows both show 15-20pt gaps between rules and ML despite agreeing Geelong/Sydney win — treat those margins as directionally solid but not decimal-precise).

---

## T9 Matrix Confluence — Summary

| Game | Best signal | Direction | Ways | Agrees w/ rules+ML pick? |
|------|------------|-----------|------|--------------------------|
| **West Coast vs Brisbane** | H2H | BACK AWAY (Lions) | 8-way, incl. a 100% split | **Yes — strongest clean alignment of the round** |
| Richmond vs Hawthorn | Handicap | AWAY COVERS (Hawks) | 6-way | **Yes** |
| North Melbourne vs Melbourne | H2H | BACK AWAY (Demons) | 6-way | Rules agrees (Demons), ML doesn't — this is the model-disagreement game, matrix breaks the tie toward rules but house rule still says no play |
| Sydney vs Adelaide | Handicap | HOME COVERS (Swans) | 5-way | **Yes** |
| West Coast vs Brisbane | Handicap | HOME COVERS (Lions, i.e. covers *against* the huge line — a fade-the-size signal) | 5-way | Partial — agrees on winner, disagrees on the 44.9pt size |
| Geelong vs St Kilda | Handicap | AWAY COVERS (Saints) | 3-way | Fade-the-size signal vs a 34.3pt model margin — both rules and ML have Cats winning big, matrix says not *that* big |
| Collingwood vs Carlton | Totals | UNDERS | 4-way | N/A (totals-only signal, no handicap/H2H read) |
| Essendon vs GWS | Handicap | AWAY COVERS (Giants) | 3-way | Fade-the-size signal vs a 21.7pt model margin |
| Port Adelaide vs Fremantle | Handicap | HOME COVERS (Power) | 4-way | Disagrees with both rules (-28.5) and ML (-35.2) — matrix likes the home dog here despite the historic midfield injury list AND the new T8 kicking penalty. Worth a second look given how extreme Port's outs list is |
| **Gold Coast vs Western Bulldogs** | — | — | — | **No confluence found at all** — the only game in the round with zero matrix signal, on top of being a model-disagreement game |

---

## Top signals (rules + ML agree, matrix backs the winner)

1. **Brisbane -44.9 (or better) at West Coast** — 8-way H2H matrix including a 100% historical split, rules and ML both have Lions winning comfortably (though matrix also suggests fading the exact size of the line).
2. **Hawthorn -37.6 at Richmond** — 6-way handicap matrix, rules/ML agree on Hawks (margins -37.6/-46.7, ML even more bullish).
3. **Sydney -26.7 vs Adelaide** — 5-way handicap matrix backs the Swans, rules/ML agree on winner (margins diverge a lot in size, 26.7 vs 9.6 — treat as "Swans win," not "Swans by 27").

**Avoid entirely:** North Melbourne vs Melbourne, Gold Coast vs Western Bulldogs — both are rules/ML winner disagreements per the standing betting rule. The Suns/Bulldogs game additionally has no matrix support of any kind.

**Caution (winner agreed, size in question):** Geelong (-34.3, matrix fades the size), Brisbane (-44.9, matrix fades the size), Essendon/GWS (-21.7, matrix fades the size). Three of the round's biggest model margins all draw a matrix pushback on magnitude — worth treating the *winner* as the signal and the *number* as soft. **Port Adelaide -28.5 is now the round's biggest single-session mover** — T5 injuries and T8 kicking accuracy both independently push the same direction on the same team, worth flagging as the tier stack "piling on" rather than one big signal.

---

## Key Injury Notes (T5)

- **Port Adelaide's entire first-choice midfield engine room is out simultaneously**: Zak Butters (elite), Connor Rozee (elite, season), Jason Horne-Francis (elite, suspended this round only). Add Jack Lukosius (key forward) and a doubtful Mitch Georgiades (concussion protocol) and Port is missing most of its attacking spine against Fremantle.
- **GWS carries three elite absences**: Tom Green (season), Joshua Kelly (season), Jesse Hogan, plus a doubtful Lachie Whitfield (concussion protocol) — against an Essendon side that has now lost 12 straight, this is a genuine "who wants it less" spot.
- **Both captains/star key defenders out for the Collingwood-Carlton blockbuster**: Darcy Moore (Collingwood, season) and Jacob Weitering (Carlton, 4-5 weeks) — a like-for-like structural wash that the model already reflects via T5 on both sides.
- **Geelong's ruck is in crisis**: Toby Conway (out) and Rhys Stanley (doubtful) — first and second choice ruck both compromised, on top of Jeremy Cameron (elite key forward) out for the St Kilda opener.
- **Western Bulldogs missing three elite-tier names**: Sam Darcy (season), Bailey Dale, and a doubtful Tim English (best ruck in the competition) — against a Gold Coast side missing far less. This is part of why ML disagrees with rules on this game; worth investigating once market data returns.
- **Jack Viney (elite midfielder) out for Melbourne** against North Melbourne — the other half of that game's model disagreement.

---

## Assumptions / Data Risk Flags

- **No market lines anywhere in this analysis** — Odds API has been down since Jul 3 (13 days). EV, edges, and bet selection are all blocked until it's restored. `mkt_home_prob_open` ran on its ELO fallback for all 9 games — the pipeline's own pre-flight health check flagged this explicitly.
- **Emotional scraper (T6) bug**: the Claude/Anthropic layer of `afl_emotional.py` returned truncated, invalid JSON on **two consecutive runs**, both times cutting off mid-string on the same Essendon blowout flag. The deterministic layer (rivalry detection) worked fine; only the LLM-generated flags failed. Applied the Essendon flag manually after web-verifying the underlying fact (lost 8.11/59 to Brisbane's 22.17/149 at the Gabba, Jul 12 — 12th straight loss). **This needs a real fix, not another manual workaround** — worth checking if the scraper's max_tokens setting is too low for a round with this many newsworthy teams.
- **T5 position/quality tags are manual judgement calls**, not scraped — same limitation flagged every round. Directionally right, not decimal-precise.
- **Sydney's "Max King" entry** — a second, separate "Max King" appears in Sydney's injury list this round alongside St Kilda's well-known Max King. Consistent with the same flag raised in the R18 writeup: held as a distinct, low-confidence, average-tier entry rather than assumed to be a duplicate, per that established precedent.
- **Extreme-ELO-gap games** (Eagles/Lions -44.9, Cats/Saints +34.3, Tigers/Hawks -37.6) carry the documented linear-ELO overcook risk — the sigmoid rescale fix (full xScore ELO rebuild) is still banked for the 2026 off-season, see memory note `project_afl_xscore_elo_endofseason`. T8 is a lightweight, capped, current-season-only patch — it nudges these prices slightly but does not fix the underlying ELO issue. T9 matrix confluence independently agrees on all three winners but pushes back on the exact size in two of the three (Geelong, Brisbane), which is a useful cross-check in the absence of market data.
- **T8 kicking accuracy tier — new today.** Capped ±4pt (handicap and totals separately), needs 30+ season shots per team to fire (all 18 teams qualify this week). Full spec and rationale in `pricing/afl_tier8_kicking.py`. This is deliberately the lightweight version — see the off-season xScore ELO plan for the deeper fix.
- **Strong wind at People First Stadium (21.2km/h)** drives the round's single biggest totals dock (-6.0, Suns/Bulldogs) — re-check forecast Sunday morning before treating 147.5 as final.
- **Round-prep files (fixture/injuries/emotional) built from scratch this round** — no automated scraper writes `outputs/afl_round_prep/r{N}_2026/` the way the NRL equivalent does. Fixture was web-verified against the official AFL schedule rather than pulled from an API. Worth building a proper AFL fixture scraper if this becomes a weekly manual bottleneck.
