# AFL R21 2026 — Pricing Analysis

**Generated:** 2026-07-28
**Model version:** T1–T8 rules + ML shadow (Jul 5 EMA/split-feature XGBoost, unchanged this round)
**Games:** Thu 30 Jul – Sun 2 Aug 2026, 9 games, all 18 teams playing (no bye).
**Market source:** ⚠️ **NONE — Odds API still down.** Subscription lapsed since ~Jul 3; the user's own expected renewal was ~Jul 14, and it is still not back as of today (Jul 28) — 25 days and counting. Fair prices below are complete but there is no market line to compare against — no EV, no bet sizing, until the feed is restored.

---

## Tier Coverage Report (mandatory)

| Tier | Status | Detail |
|------|--------|--------|
| T1 — ELO baseline | ✅ REAL | Rebuilt today off the current historical xlsx |
| T2 — Style matchup | ✅ REAL | Footywire snapshot fresh this session |
| T3 — Situational | ✅ REAL | Rest/travel/form from fixture + history |
| T4 — Venue | ✅ REAL | Fortress/shared-venue adjustments applied across all 9 games |
| T5 — Injuries | ⚠️ **REAL BUT DEGRADED** | Fresh scrape (2026-07-28), but every player defaulted to **position=utility, quality=average** — not hand-curated this round due to time constraint (the injuries file's own metadata says so explicitly). See caveat below: this materially understates several teams' true injury damage. |
| T6 — Emotional | ✅ REAL (1 known gap) | Fresh AFL emotional scrape, 7 flags across 7 teams. 6 of 7 fired correctly; **Gold Coast's flag used flag_type `losing_streak`, which isn't in `AFL_T6_CONFIG`'s supported list — it silently produced zero impact.** Needs a code fix (map `losing_streak` to an existing type, e.g. `shame_blowout`-lite, or add native support). |
| T7 — Weather | ✅ REAL | Live Tomorrow.io, 9/9 venues. Moderate wind flagged at Adelaide Oval (Port Adelaide vs GWS) |
| T8 — Kicking accuracy | ✅ REAL | Season-to-date conversion vs league average, capped ±4pt |
| ML shadow | ✅ REAL | Same EMA/split-feature models, fresh features off today's ELO rebuild |
| T9 — Matrix confluence | ✅ REAL | All 3 matrices, 9/9 games with confluence signal, JSON generated |

**Coverage: 8/9 tiers genuinely populated at full quality, 1 (T5) real-but-degraded, 1 known sub-bug (T6/Gold Coast) — call it ~7.5/9 (83%).** The mandatory bar (75%) is cleared, but **T5 needs a hand-curation pass before this round should be bet on injury-driven signals** — see below.

---

## ⚠️ Priority data-quality flag: T5 injury quality regression

Every one of the ~80 confirmed-out players this round is tagged generic `utility/average`, so the injury impact table (which weights by position × quality) applies its smallest available weight everywhere. The result: several of the most injury-hit rosters in the competition are pricing with **near-zero T5 impact**, which is very likely wrong.

Concretely, comparing to last round's (R19) hand-curated tags for the same players:
- **Port Adelaide**: Zak Butters and Connor Rozee — both tagged **elite** in R19 — are out again this round (plus Sam Powell-Pepper, Ollie Lord, Josh Sinn, Ewan Mackinlay, 5 more). This round they price as generic average/utility. **Port Adelaide's T5 this round is 0.0/0.0** — essentially saying the injuries have zero effect, which contradicts last round's own -8.0pt finding for a similar (now worse) list.
- **GWS**: Tom Green, Joshua Kelly and Jesse Hogan — all tagged **elite** in R19 (Green and Kelly season-ending) — remain out, plus Toby Greene now added. Same generic-average treatment this round.
- **Richmond**: 11 players out including Noah Balta, Josh Gibcus, Jacob Hopper — a long list, all generic.

**Recommendation: do a manual position/quality pass on these three rosters at minimum (Port Adelaide, GWS, Richmond) before treating any T5-adjacent price as final** — the same way R19 was manually tagged. This round's numbers below are real and complete, just not fully trustworthy on T5 specifically.

---

## Prices at a Glance (fair prices — rules model, no market lines available)

| Game | Date | Venue | Fair H2H (Home/Away) | Fair Hcap | Fair Total | Model agreement |
|------|------|-------|----------------------|-----------|------------|------------------|
| **Collingwood** vs Geelong | Thu 30 Jul | MCG | 1.98 / 2.02 | Magpies +0.5 | 176.0 | ❌ **disagree** (rules: Pies, ML: Cats) |
| **Fremantle** vs W. Bulldogs | Fri 31 Jul | Optus Stadium | 1.18 / 6.64 | Dockers -37.2 | 174.8 | ✅ direction (both Dockers, size gap 37.2 vs 14.0) |
| St Kilda vs **Sydney** | Sat 1 Aug | Marvel | 2.90 / 1.53 | Swans -14.4 | 186.9 | ❌ **disagree** (rules: Swans, ML: Saints) |
| **Hawthorn** vs Nth Melbourne | Sat 1 Aug | UTAS Stadium | 1.13 / 8.49 | Hawks -42.7 | 161.6 | ✅ direction (both Hawks, size gap 42.7 vs 64.9) |
| Port Adelaide vs **GWS** | Sat 1 Aug | Adelaide Oval | 2.62 / 1.62 | Giants -10.8 | 151.6 | ✅ direction (both Giants, size gap 10.8 vs 4.2) |
| Carlton vs **Brisbane** | Sat 1 Aug | Marvel | 3.75 / 1.36 | Lions -22.4 | 189.5 | ✅ direction (both Lions, size gap 22.4 vs 21.5 — tight) |
| **Richmond** vs West Coast | Sun 2 Aug | MCG | 1.89 / 2.13 | Tigers +2.8 | 131.4 | ❌ **disagree** (rules: Tigers, ML: Eagles by 17.8) |
| Gold Coast vs **Melbourne** | Sun 2 Aug | Heritage Bank | 2.28 / 1.78 | Demons -5.5 | 165.6 | ✅ direction (both Demons, close: 5.5 vs 2.7) |
| Essendon vs **Adelaide** | Sun 2 Aug | Marvel | 9.04 / 1.12 | Crows -44.0 | 156.1 | ✅ direction (both Crows, size gap 44.0 vs 29.8) |

**Bold = model's pick to win (rules).**

---

## Tier Breakdown (Handicap, home perspective)

| Game | T1 | T2 | T3 | T4 | T5 | T6 | T8 | Final |
|------|----|----|----|----|----|----|----|-------|
| Collingwood vs Geelong | -0.4 | -3.9 | +1.61 | +2.5 | +0.0 | +1.5 | -0.86 | **+0.5** |
| Fremantle vs Bulldogs | +25.8 | +4.0 | +6.0 | +0.0 | +1.5 | +0.0 | -0.08 | **+37.2** |
| St Kilda vs Sydney | -10.7 | -4.0 | +0.69 | +0.0 | +1.5 | +0.0 | -1.9 | **-14.4** |
| Hawthorn vs Nth Melb | +38.1 | +4.0 | +0.5 | +1.0 | -0.5 | -1.0 | +0.6 | **+42.7** |
| Port Adelaide vs GWS | -3.6 | -4.0 | +0.44 | +1.5 | +0.0 | -2.25 | -2.88 | **-10.8** |
| Carlton vs Brisbane | -20.5 | -4.0 | +5.79 | +0.0 | -1.0 | +0.0 | -2.71 | **-22.4** |
| Richmond vs West Coast | +2.5 | -2.29 | +3.0 | +0.0 | -0.5 | -0.25 | +0.29 | **+2.8** |
| Gold Coast vs Melbourne | -2.6 | -4.0 | +0.0 | +0.0 | +1.5 | +0.0 | -0.42 | **-5.5** |
| Essendon vs Adelaide | -39.0 | -4.0 | +1.59 | +0.0 | -1.5 | +2.25 | -3.38 | **-44.0** |

T2 has hit its -4.0 cap on 6 of 9 games this round — same extreme-ELO-gap pattern flagged in prior rounds (Eagles/Lions, Cats/Saints style games last round).

---

## ML Shadow (EMA/split-feature models)

| Game | Rules Mrg | ML Mrg | MrgΔ | Rules Tot | ML Tot | Rules H% | ML H% |
|------|-----------|--------|------|-----------|--------|----------|-------|
| Collingwood vs Geelong | +0.5 | -4.5 | -5.0 | 176.0 | 172.8 | 50.5% | 50.5% |
| Fremantle vs Bulldogs | +37.2 | +14.0 | -23.2 | 174.8 | 149.6 | 84.9% | 61.2% |
| St Kilda vs Sydney | -14.4 | +11.7 | +26.1 | 186.9 | 175.8 | 34.5% | 54.8% |
| Hawthorn vs Nth Melb | +42.7 | +64.9 | +22.2 | 161.6 | 207.6 | 88.2% | 84.5% |
| Port Adelaide vs GWS | -10.8 | -4.2 | +6.6 | 151.6 | 157.2 | 38.2% | 54.9% |
| Carlton vs Brisbane | -22.4 | -21.5 | +0.9 | 189.5 | 173.2 | 26.7% | 54.6% |
| Richmond vs West Coast | +2.8 | -17.8 | -20.6 | 131.4 | 166.0 | 53.0% | 51.9% |
| Gold Coast vs Melbourne | -5.5 | -2.7 | +2.8 | 165.6 | 157.6 | 43.9% | 51.9% |
| Essendon vs Adelaide | -44.0 | -29.8 | +14.2 | 156.1 | 155.8 | 11.1% | 26.9% |

**Note the Richmond vs West Coast split:** rules and ML *margin* models disagree on the winner (+2.8 vs -17.8), but the ML *H2H classifier* — a separately-trained model, per the Jul 5 architecture — still gives Richmond 51.9%. The two ML models disagree with each other here, on top of disagreeing with rules on margin. Treat this as the least-resolved game of the round.

### Model-alignment check (standing betting rule)

**6 of 9 games have rules and ML agreeing on winner direction. 3 are off-limits for every market:**
- **Collingwood vs Geelong** — rules picks Magpies (barely, 50.5%), ML picks Cats (also barely). Coin-flip game with opposite picks either way. **No play.**
- **St Kilda vs Sydney** — rules has Swans clearly (65.5% away), ML has Saints (54.8% home). A real disagreement, not just size. **No play.**
- **Richmond vs West Coast** — rules has Tigers (barely), ML margin model has Eagles by 17.8. **No play.**

The other 6 agree on winner even where margin size diverges hard (Fremantle 37.2 vs 14.0, Essendon/Adelaide 44.0 vs 29.8) — treat those as "winner solid, number soft."

---

## T9 Matrix Confluence — Summary

| Game | Signal(s) | Direction | Ways | Agrees w/ rules+ML pick? |
|------|-----------|-----------|------|--------------------------|
| **Hawthorn vs Nth Melbourne** | H2H + Handicap | HAWTHORN | 11-way + 9-way | **Yes — strongest clean alignment of the round**, but several component edges show 100% splits (near-certainly tiny samples — T9 has no sample-size weighting yet, backlog item) |
| **Fremantle vs Bulldogs** | H2H + Totals + Handicap | FREMANTLE (overs) | 3+4+3-way | **Yes** — clean triple stack |
| Port Adelaide vs GWS | H2H + Handicap + Totals | **PORT ADELAIDE** (unders) | 3+4+3-way | **No — contradicts both models.** Every matrix category backs the home dog against a Giants pick from both rules and ML. Same shape as the R19 Power/Dockers conflict. Worth a second look, not a clean bet either way. |
| Carlton vs Brisbane | Handicap | BRISBANE covers | 3-way | **Yes** |
| Gold Coast vs Melbourne | Handicap | GOLD COAST covers | 3-way | Consistent with the tight model margins (both sides have Melbourne winning narrowly) |
| Essendon vs Adelaide | H2H + Totals + Handicap | Split: H2H backs Essendon (upset), Handicap backs Adelaide covering | 3+3+4-way | Internally split — reads as "fade the size" on the model's huge Adelaide margin, not a clean signal either way |
| Richmond vs West Coast | H2H (both directions) + Totals + Handicap | Split both ways | 4+6+3+4-way | Matrix itself is inconclusive here — consistent with this also being a rules/ML no-play game |
| St Kilda vs Sydney | Totals + Handicap | St Kilda covers (unders) | 4+3-way | Leans toward the ML pick (Saints), not the rules pick (Swans) — this is also a rules/ML disagree game, so still no play |
| Collingwood vs Geelong | Totals | OVERS | 5-way | No H2H/handicap read — totals-only signal on a coin-flip game |

---

## Top signals (rules + ML agree, matrix backs the winner, no market comparison possible)

1. **Hawthorn -42.7 (or wherever the line opens) vs North Melbourne** — 11-way H2H + 9-way handicap matrix, rules and ML both have Hawthorn winning big (ML even bigger, +64.9). Treat the *winner* as very solid; be cautious of the exact size given T2's -4.0 cap and the ELO-overcook pattern.
2. **Fremantle vs Western Bulldogs** — triple matrix stack (H2H, totals, handicap) all backing the Dockers, both models agree on winner despite a 23pt size gap.
3. **Brisbane -22.4 at Carlton** — clean handicap confluence, rules/ML agree almost exactly (22.4 vs 21.5, the tightest margin agreement of the round).

**Avoid entirely (standing model-alignment rule):** Collingwood/Geelong, St Kilda/Sydney, Richmond/West Coast.

**Flagged conflict — needs a second look before any market data returns:** Port Adelaide vs GWS. Every T9 category backs the home Power against a Giants pick from both rules and ML — the same pattern that flagged a real market inefficiency candidate last round (Power/Dockers, R19).

---

## Key Injury Notes (T5) — see quality caveat above, treat magnitudes as directionally soft this round

- **GWS**: Tom Green, Joshua Kelly, Jesse Hogan (all season-ending, all elite last round) plus Toby Greene newly out — arguably GWS's worst injury list of the season, priced at generic average/utility this round.
- **Port Adelaide**: Zak Butters, Connor Rozee (both elite last round) plus Ollie Lord, Sam Powell-Pepper, Josh Sinn, Ewan Mackinlay, Joe Richards, Mani Liddy, Esava Ratugolea, Kane Farrell — 10 players out, priced as if this were a minor list.
- **Richmond**: 11 players out (Noah Balta, Josh Gibcus, Jacob Hopper among them) against a West Coast side missing 10 of their own — a rough like-for-like wash on paper, but with the same generic-tagging caveat on both sides.
- **Essendon**: 7 out including Kyle Langford (suspension, returns this round anyway) and multiple season-enders (Archie May, Brayden Fiorini, Lewis Hayes, Nicholas Martin, Xavier Duursma) — against an Adelaide side that also lost Darcy Fogarty, Hugh Bond, Luke Pedlar, Rory Laird. Both playing shorthanded.

---

## Key Emotional Notes (T6)

- **Essendon**: shame_blowout (major) — off a 93-point loss last week, "must respond" narrative, home vs Adelaide. Fired correctly (+2.25 handicap).
- **GWS / West Coast / (Port Adelaide game & Richmond game respectively)**: both carry major shame_blowout flags off heavy losses last week — Port Adelaide vs GWS and Richmond vs West Coast are *both* games where the away team is nursing a blowout-loss narrative. Worth knowing both "must respond" games this round also happen to be model-disagreement or model-conflict games (Port/GWS is the T9 conflict above; Richmond/WCE is a rules/ML no-play).
- **Collingwood**: rivalry_derby (normal) vs Geelong — fired correctly (+1.5 handicap).
- **Richmond**: must_win (normal) vs West Coast — fired correctly, stacks with WCE's own shame_blowout flag in the same game.
- **North Melbourne**: must_win (minor) — fired correctly via Hawthorn's -1.0 handicap.
- **Gold Coast**: losing_streak flag present in the data but **not applied** — see T6 code gap above.

---

## Can't-price / open items

- **Market EV**: impossible until the Odds API renews. This has now run 25 days past the Jul 3 outage and 2 weeks past the user's own expected Jul 14 renewal — worth flagging directly, this may need checking on rather than assuming it'll resolve itself.
- **T5 hand-curation**: recommend a manual position/quality pass on Port Adelaide, GWS, and Richmond rosters before treating T5-adjacent prices (Port Adelaide vs GWS in particular, given it's also the round's T9 conflict game) as final.
- **T6 `losing_streak` flag_type**: not supported by `AFL_T6_CONFIG` — either map it to an existing type or add native support so Gold Coast's flag stops silently no-opping.
- **Port Adelaide vs GWS**: flagged above as a genuine matrix-vs-model conflict — no clean read either way without market data to arbitrate.
