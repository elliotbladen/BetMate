# NRL Round 19 2026 — Full Tiered Pricing (Jul 10–12)
**Priced:** 2026-07-09 (re-run of the Jul 7 auto-pricing with refs, fresh emotional scrape, T9 confluence)
**Model:** rules engine T1–T8 + T10, matrices T9. CSV: `results/r19_pricing_2026.csv`

---

## ⚠️ WHAT THE MODEL COULD NOT PRICE THIS ROUND — READ FIRST

| # | Item | Why | Impact |
|---|------|-----|--------|
| 1 | **Market EV / bet selection** | **Odds API down (401s) since Jul 3 — user-confirmed Jul 9 it's down for now, not locally fixable. No snapshots, no market lines.** The `@105` prices below are the MODEL's own juiced prices, not market. | Cannot compute EV, cannot line-shop, cannot log CLV entry prices. **When the API is back: run a snapshot cycle, then compare these prices to market before staking anything.** |
| 2 | **NRL ML shadow** | `ml/predict.py` is still a Phase-3 stub (`NotImplementedError`) — NRL has no ML model, unlike AFL. | The model-alignment rule (rules + ML must agree) **cannot be verified**. Per house rules, treat every signal below as single-model. Size down. |
| 3 | **Origin G3 backup fatigue** | T10 models *camp absence* only. G3 was played **Wed Jul 8** — R19 starts 2 days later. No tier prices the backup. | **Roosters 6 G3 players** (Tedesco, S. Walker elite) into a Sat -14.1 line; **Dolphins 5** (Sat); Storm 3 (Munster+Grant, Sun); Sharks/Raiders/Cowboys 3 each. Model is likely **over** on heavy-Origin favourites. |
| 4 | **Tyson Brough T6** | No historical bucket for this ref (first-year sample) | Storm/Titans T6 = 0.0 — neutral by ignorance, not by evidence |
| 5 | **Final team lists** | Injury data is Jul 7 casualty ward; team lists firm 24h pre-game | **Jarome Luai (elite, doubtful)** is ±~3pts on Tigers/Warriors. Re-check Friday teams. |
| 6 | Emotional flags (T7) | Scraper ran twice, returned 0 — but a **manual web double-check found one it missed**: the Jai Arrow MND tribute game (his 14-headline window is too narrow). No other candidates: no R18 blowouts (max margin 22), no coach changes this week. | **Jai Arrow flag applied manually** (personal_tragedy, major) → Souths -3.3 became **-5.5**. Scraper's news window needs widening before R20. |

Everything else priced with real, current data (see tier coverage at the bottom).

---

## Prices (home perspective; H@105/A@105 = model price incl. 5% margin — NOT market)

| Game | Model margin | Score | Total | H fair | A fair | H@105 | A@105 |
|------|-------------|-------|-------|--------|--------|-------|-------|
| **Tigers vs Warriors** (Fri 8pm, Campbelltown) | Warriors by 12.4 | 19.4–31.8 | 51.2 | 6.64 | 1.18 | 6.32 | 1.12 |
| **Dolphins vs Sharks** (Sat 3pm, Kayo) | Dolphins by 0.3 | 25.6–25.3 | 50.9 | 1.96 | 2.04 | 1.87 | 1.94 |
| **Bulldogs vs Raiders** (Sat 5:30pm, Accor) | Raiders by 0.2 | 18.1–18.3 | **36.4** | 2.03 | 1.97 | 1.93 | 1.88 |
| **Roosters vs Eels** (Sat 7:35pm, Allianz) | Roosters by 14.1 | 32.2–18.1 | 50.3 | 1.14 | 8.33 | 1.08 | 7.94 |
| **Rabbitohs vs Knights** (Sun 2pm, Accor) | Souths by 5.5 | 28.1–22.6 | 50.7 | 1.48 | 3.09 | 1.41 | 2.95 |
| **Sea Eagles vs Cowboys** (Sun 4:05pm, 4 Pines) | Manly by 9.2 | 27.1–17.9 | 45.0 | 1.29 | 4.51 | 1.22 | 4.30 |
| **Storm vs Titans** (Sun 6:15pm, AAMI) | Storm by 14.2 | 28.3–14.1 | 42.4 | 1.13 | 8.45 | 1.08 | 8.05 |

---

## Game Notes — tiers + T9 matrix confluence

### Tigers vs Warriors — model and matrices ALIGNED on Warriors
- Build-up: T1 -8.5, T2 -2.0, T5 -3.0 (Tigers 7.0 injury pts: Luai *doubtful*, Herbert/Pearce-Paul/Hunt out), T6 +0.6 → **Warriors -12.4**
- T9: **7-way H2H BACK WARRIORS** (Tigers 100% losing streak in this fixture, 71.6% Fri-night fade, after-loss, July) + **5-way handicap WARRIORS COVER** — the strongest matrix stack of the round, same direction as the model
- Ref Raymond flow_heavy: totals +3.1 → 51.2
- ⚠️ If Luai plays, Tigers improve ~3; the 12.4 assumes his likely absence

### Dolphins vs Sharks — genuine coin flip, matrices SPLIT
- Model dead even (+0.3). T9 handicap 5-way DOLPHINS COVER (50% at Kayo) but H2H 3-way BACK SHARKS — split signal, no clean edge

### Bulldogs vs Raiders — the UNDER stands out
- Model total **36.4** vs T1 base 40.3: T4 venue -2.0, T5 -0.8, **T6 Sutton whistle_heavy -1.1**; both teams even (0.2)
- T9: 3-way H2H + 3-way handicap both RAIDERS (long-rest edge 56.4%/37.6%) — mild away lean vs model's even line
- Turpin (key) out for Bulldogs already in T5

### Roosters vs Eels — model's biggest number, biggest caveat
- **Roosters -14.1**, T1 +9.6 doing the work, T3 +2.0, T4 +1.5
- T9 agrees: **6-way handicap ROOSTERS COVER** (Eels 50% July fade, 50% Allianz fade) + 4-way H2H
- ⚠️ **But: 6 Roosters backed up from Wednesday's Origin G3** — unmodeled fatigue on a two-touchdown favourite 3 days later. This is exactly the spot where the model over-rates. Treat -14.1 as the optimistic end.

### Rabbitohs vs Knights — model vs matrices CONFLICT (now wider)
- Model Souths by 5.5 *with* Latrell Mitchell (elite) + Cody Walker already priced OUT (6.2 injury pts)
- **T7 Jai Arrow flag (+2.25, applied manually after web verification):** the R19 Sunday game IS the "World's Biggest Birthday Party" — NRL-wide Stand With Jai MND fundraiser at Souths' home ground, Arrow's 31st birthday, world-record crowd event. Textbook team-rallying-around-adversity spot. Caveat: emotional occasion games can also cut the other way (distraction) — the +2.25 is the house-calibrated value, not a certainty
- T9 points the other way: 3-way H2H BACK KNIGHTS (56.2%/56.0% fixture history) + 3-way handicap KNIGHTS COVER
- Single-model conflict with no ML tiebreaker available → **still a no-play zone by house rules**, now with an even wider model-vs-matrix gap

### Sea Eagles vs Cowboys — aligned on Manly
- Model Manly -9.2 (T2 +4.0 style edge). T9: 3-way H2H + 3-way handicap both MANLY. Cowboys' Dearden doubtful. Cowboys on 15d rest is the counter-angle (long-rest teams have matrix support elsewhere this round)

### Storm vs Titans — H2H aligned, handicap matrices disagree
- Model Storm -14.2; T9 H2H 5-way BACK STORM (Titans away/night/July fades) **but** handicap 3-way TITANS COVER (60% fixture cover both directions)
- Munster + Grant backed up from G3 (Sun = 4 days rest, milder than Roosters' 3)
- Brough ref = unpriced (neutral default)

---

## Tier Coverage Report — 100% accounted for

| Tier | Status | Source / reason |
|------|--------|-----------------|
| T1 ELO | ✅ REAL | Rebuilt today, results through R18 (cutoff Jul 5) |
| T2 Style | ✅ REAL | Style stats scraped Jul 7, 16 teams updated ("St George Illawarra Dragons" name-miss in importer — Dragons on BYE, zero impact this round; fix the alias before R20) |
| T3 Schedule/rest | ✅ REAL | From fixture (rest days verified in T9 context) |
| T4 Venue | ✅ REAL | DB venue table |
| T5 Injuries | ✅ REAL | NRL.com casualty ward Jul 7 — 67 records loaded; 12 "errors" were bye-team players (Broncos/Panthers/Dragons), correct behaviour. **Re-check final teams Friday (Luai)** |
| T6 Referee | ✅ REAL | **NRL.com hadn't published R19 appointments (scraper: 0 found Wed+Thu).** Sourced from web (ESPN full list, Sutton+Gee corroborated on second source), hand-loaded 7/7. Brough = no bucket (unpriceable → neutral) |
| T7 Emotional | ✅ REAL (1 flag, manual) | Scraper returned 0 twice; web double-check found the **Jai Arrow MND tribute game** (Souths v Knights IS the fundraiser centrepiece). Applied as personal_tragedy/major (+2.25 Souths). Verified: no R18 blowouts (max 22), no coach changes, no other milestones found. **Fix before R20: widen the scraper's news window** |
| T8 Weather | ✅ REAL | Tomorrow.io fetched today, 7/7 games, all **clear** → 0 adjustments |
| T9 Matrices | ✅ REAL | Regenerated post-R18, confluence JSON written (`outputs/nrl_t9_confluence_latest.json`), pushed to Supabase |
| T10 Origin | ✅ REAL + dormant | G3 squads fully populated; camp ended Jul 9, R19 starts Jul 10 → no camp absences. **Backup fatigue not modeled — see warning #3** |
| ML shadow | ❌ N/A | NRL ML not implemented (`ml/predict.py` stub) |
| Market/EV | ❌ BLOCKED | Odds API key dead since Jul 3 — restore key, then compare these prices to market before betting |

**Referee sources:** [ESPN R19 preview](https://www.espn.com.au/nrl/story/_/id/49282302/nrl-round-19-teams-line-ups-tips-odds-everything-need-know-weekend) (all 7), corroborated for Sutton/Gee via secondary search results.
