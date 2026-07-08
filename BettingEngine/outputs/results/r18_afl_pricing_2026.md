# AFL R18 2026 — Pricing Analysis

**Generated:** 2026-07-07 (start-of-week price-up)
**Model version:** 1.0.0 (T1–T7 rules + ML shadow, XGBoost trained 2009–2023)
**Byes:** None — all 18 teams playing.
**ELO base:** rebuilt from AusSportsBetting workbook downloaded 2026-07-07 (includes R17 results, 144 deploy games)

---

## Tier Coverage (mandatory per CLAUDE.md — 2026-07-07 rule)

| Tier | Status | Detail |
|------|--------|--------|
| T1 — ELO baseline | ✅ Populated | All 9 games, real ELO diffs from freshly rebuilt ratings |
| T2 — Style matchup | ✅ Populated | All 9 games; hit the ±4.0 cap on 5/9 (Magpies/Kangaroos, Blues/Hawks, Crows/Suns, Bulldogs/Eagles, Demons/Tigers, Lions/Bombers — 6/9 actually) |
| T3 — Situational (rest/travel/form) | ✅ Populated | Ran for all 9; genuinely zero for 4 games (no rest/travel/form differential to flag) — not a fallback, a real null result |
| T4 — Venue | ✅ Populated | All 9 games; fortress bonus fired for Giants (+2.5) and Lions (+2.0) |
| T5 — Injuries | ✅ Populated (fixed mid-session) | **Initially fired as zero for all 9 games** — the round's injury data lives in a manually-curated `injuries_r18_2026.json` that didn't exist yet; the freshly-scraped 145-record BetMate file isn't read directly by the pricing engine. Built that file from the fresh scrape (83 confirmed outs), manually tagging position/quality since the scraper doesn't supply either. Re-ran — now active on all 9 games, compound penalty (⚡) on 2. |
| T6 — Emotional | ✅ Populated | Fresh scrape run today — 5 flags (2 rivalry_derby, 1 personal_tragedy [Jordan Dawson, carried forward], 1 shame_blowout [Essendon], 1 losing_streak [Fremantle]). Non-zero on 4/9 games — the other 5 legitimately have no emotional storyline this week. |
| T7 — Weather | ✅ Populated | Live Tomorrow.io pull for all 9 venues. Wind adjustment fired on 5/9 (Saints/Power, Blues/Hawks, Crows/Suns, Bulldogs/Eagles, Demons/Tigers) |
| T9 — Matrix confluence | ✅ Populated | Ran across all 9 games — every game produced 3+ way confluence on at least one market |
| ML shadow | ✅ Populated | XGBoost ran independently for all 9 games |

**8/8 tiers populated with real data = 100% coverage** (well above the 75% bar). The one thing genuinely worth flagging: T5's position/quality tags are my own football-knowledge judgement calls, not scraped — the source data only gives player name + status + injury description, no position or importance tier. Treat T5 as directionally right, not to-the-decimal precise.

---

## Prices at a Glance

| Game | Date | Venue | Model H2H | Model Hcap | Model Total |
|------|------|-------|-----------|------------|--------------|
| Fremantle vs **Sydney** | Thu 9 Jul | Optus | 1.29 / 4.43 | Dockers -27.1 | 178.5 |
| Collingwood vs North Melb | Fri 10 Jul | Marvel | 1.53 / 2.89 | Magpies -14.3 | 161.5 |
| St Kilda vs Port Adelaide | Sat 11 Jul | Marvel | 1.78 / 2.28 | Saints -5.6 | 151.5 |
| GWS vs **Geelong** | Sat 11 Jul | ENGIE | 3.43 / 1.41 | Cats -19.8 | 193.5 |
| Carlton vs **Hawthorn** | Sat 11 Jul | MCG | 3.47 / 1.41 | Hawks -20.1 | 164.0 |
| Adelaide vs Gold Coast | Sat 11 Jul | Adelaide Oval | 1.25 / 5.06 | Crows -30.6 | 162.5 |
| W. Bulldogs vs West Coast | Sun 12 Jul | Marvel | 1.12 / 9.03 | Bulldogs -44.0 | 153.5 |
| Melbourne vs Richmond | Sun 12 Jul | MCG | 1.16 / 7.18 | Demons -39.0 | 154.0 |
| Brisbane vs Essendon | Sun 12 Jul | The Gabba | 1.08 / 13.85 | Lions -52.5 | 166.0 |

**Bold = model's pick to win where it differs from ML** (Dockers vs Swans is the one true model disagreement — see below).

---

## Model Alignment Check (rules vs ML direction)

**Only one disagreement this round: Fremantle vs Sydney.** Rules has the Dockers as big home favourites (+27.1); ML actually favours Sydney (-1.3, i.e. away). Per the standing betting rule, this is a hard avoid on H2H/handicap regardless of what the matrix says — and the matrix (below) throws its strongest signal of the round on this exact game, backing Sydney. Worth watching but not betting.

Every other game has rules and ML pointing the same direction (margin size varies, sometimes a lot — see Dockers/Swans-style total gaps below — but the winner pick agrees in all 8 remaining games).

---

## T9 Matrix Confluence — Summary

| Game | Best signal | Direction | Ways | Agrees w/ rules+ML pick? |
|------|------------|-----------|------|--------------------------|
| **Fremantle vs Sydney** | Handicap | AWAY COVERS (Sydney) | 6-way, incl. 100% "Swans at Optus Stadium" | No — this is the model-disagreement game, avoid regardless |
| Collingwood vs North Melb | H2H | BACK HOME (Magpies) | 8-way, incl. four 100% splits | **Yes** — strongest clean alignment of the round |
| St Kilda vs Port Adelaide | H2H | BACK AWAY (Port) | 3-way | No — matrix leans Power, rules+ML lean Saints. Caution, not a veto. |
| GWS vs Geelong | H2H | BACK HOME (Giants) | 3-way | No — matrix leans Giants, rules+ML lean Cats. Caution. |
| Carlton vs Hawthorn | Handicap | AWAY COVERS (Hawks) | 4-way | **Yes** |
| Adelaide vs Gold Coast | Handicap | HOME COVERS (Crows) | 6-way | **Yes** — best clean handicap alignment of the round |
| W. Bulldogs vs West Coast | H2H | BACK HOME (Bulldogs) | 5-way | **Yes** (though already a huge favourite — limited value) |
| Melbourne vs Richmond | H2H | BACK HOME (Demons) | 6-way, incl. 100% "Tigers vs Melbourne" | **Yes** |
| Brisbane vs Essendon | Handicap | AWAY COVERS (Essendon) | 4-way | Not a veto (Lions are a 52.5pt favourite — "away covers" is compatible with a comfortable Lions win, just not by *that* much) |

---

## Top Signals (rules+ML agree, matrix backs it)

1. **Adelaide -30.6 vs Gold Coast** — 6-way handicap matrix, rules+ML agree, T6 carries the Jordan Dawson rally-effect. Best clean signal of the round.
2. **Collingwood (Magpies) H2H/handicap -14.3 vs North Melbourne** — 8-way matrix incl. four 100% historical splits, rules+ML agree.
3. **Melbourne (Demons) -39.0 vs Richmond** — 6-way matrix incl. a 100% "Tigers vs Melbourne" split, rules+ML agree, but note Richmond's Josh Gibcus (key defender) and Jacob Hopper (midfielder) outs are already priced into T5.
4. **Hawthorn (Hawks) -20.1 vs Carlton** — 4-way matrix confluence, rules+ML agree, T5 has Carlton missing captain Jacob Weitering (elite key defender).

**Avoid:** Fremantle vs Sydney (rules/ML disagree on winner outright — the matrix's strongest signal of the round points the other way from rules, which is exactly the scenario the betting rule exists for).

**Caution, not a veto:** St Kilda/Port Adelaide and GWS/Geelong both have the matrix leaning against the rules+ML pick. Both games also carry heavy T5 injury loads on both sides (Saints missing four elite players — Flanders, King, Sinclair, De Koning; Power missing Rozee; Giants missing Green, Hogan, Kelly — three elite absentees, the heaviest list in the competition again), so treat these as lower-confidence even before the matrix disagreement.

---

## Key Injury Notes (T5)

- **GWS again carries the competition's heaviest list**: Tom Green (season-ending, re-confirmed per the standing data-entry rule), Jesse Hogan, Joshua Kelly — three elite absentees, compound penalty applied.
- **St Kilda has four elite outs** (Flanders, King, Sinclair, De Koning) against Port Adelaide, who are missing their own elite midfielder (Connor Rozee, season-ending, carried forward). Both sides are hurting — treat the whole game with caution.
- **Carlton missing captain Jacob Weitering** (elite key defender) vs Hawthorn.
- **Collingwood missing captain Darcy Moore** (elite key defender) vs North Melbourne.
- **Western Bulldogs missing Sam Darcy** (elite key forward, season-ending) vs West Coast — West Coast also has 8 outs but none elite-tier, consistent with their rebuilding-list injury profile.
- **Melbourne missing Jack Viney** (elite midfielder) vs Richmond.

---

## Weather (T7)

Wind was the only material weather factor this round — strong wind at Marvel Stadium (Sat) affecting St Kilda/Port Adelaide, strong wind at MCG affecting Carlton/Hawthorn, strong wind at Adelaide Oval affecting Adelaide/Gold Coast, and moderate wind at Marvel (Sun) and MCG (Sun) affecting Bulldogs/Eagles and Demons/Tigers respectively. All other venues clear/calm.

---

## Assumptions / Data Risk Flags

- **T5 position/quality tags are manually assigned**, not scraped — the raw injury feed only has player + status + injury description. Treat T5 magnitudes as directionally right, not precise to the decimal.
- **Sydney Swans injury list has a "Max King" entry** distinct from St Kilda's Max King — not independently verified as two different players; treated cautiously (average-tier, not elite) since I can't confirm which real player this refers to.
- **Fixture built from a live web search + direct fetch** (footywire.com), not the usual Odds API-fed pipeline — the Odds API key is still deactivated (see earlier this week). Worth double-checking against the odds board once bookmaker lines are up, to confirm no fixture discrepancies (postponements, venue changes).
