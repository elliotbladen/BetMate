# NRL Round 20 2026 — Full Tiered Pricing (Jul 16–19)
**Priced:** 2026-07-16
**Model:** rules engine T1–T8 + T10, matrices T9. CSV: `results/r20_pricing_2026.csv`

---

## ⚠️ WHAT THE MODEL COULD NOT PRICE THIS ROUND — READ FIRST

| # | Item | Why | Impact |
|---|------|-----|--------|
| 1 | **Market EV / bet selection** | **Odds API still down — no snapshot since Jul 3.** The `@105` prices below are the model's own juiced prices, not market. | Cannot compute EV, cannot line-shop, cannot log CLV entry prices. Compare to market before staking anything once the API is confirmed back. |
| 2 | **T6 Referees — 0/8** | Not yet announced by NRL.com for any game (checked twice today, standard for a Wed/Thu appointment cycle). | Every T6 column in the CSV is a neutral 0.0 default. **Re-run `run_nrl_pricing.ps1` Wed/Thu once refs drop** — worth a full reprice, not a patch, since T6 can move totals 2-3pts on whistle-heavy/flow-heavy refs. |
| 3 | **NRL ML shadow** | `ml/predict.py` still not implemented — NRL has no ML model (AFL-only capability). | Model-alignment rule can't be checked. Treat every signal below as single-model; size down accordingly. |
| 4 | **T2 style-stats import miss (recurring)** | Importer skips "St George Illawarra Dragons" (name-alias mismatch) — same bug flagged last round. R19 it didn't matter (Dragons were on bye); **this round Dragons actually play** (vs Warriors), so their T2 style row is stale/using a fallback rather than a fresh Jul 14 update. | Fix the alias in the style-stats importer before R21. Small risk on the Warriors/Dragons T2 handicap figure (+6.0 to Warriors) — treat as directionally right, not precisely calibrated. |
| 5 | **Final team lists** | Injury data is fresh (scraped this morning) but doubtfuls (Papali'i, Reynolds, Ezra Mam, Piakura, Kikau, Tuala, several more) firm up 24h out. | Re-check Wed/Thu team lists, especially Panthers/Broncos and Bulldogs/Tigers where multiple doubtfuls sit on both sides. |
| 6 | **Origin backup fatigue window** | G3 was Jul 8; T10 correctly shows no active camp this round (camp window has closed) — this is expected, not a gap, R20 is far enough past Origin that the tier legitimately returns 0. | None — flagging only so it isn't mistaken for a missed tier like R19 was. |

Everything else priced with real, current data (see tier coverage at the bottom).

---

## Prices (home perspective; H@105/A@105 = model price incl. 5% margin — NOT market)

| Game | Model margin | Score | Total | H fair | A fair | H@105 | A@105 |
|------|-------------|-------|-------|--------|--------|-------|-------|
| **Panthers vs Broncos** (Thu, CommBank) | Panthers by 23.7 | 32.2–8.5 | 40.7 | 1.03 | 41.4 | 0.98 | 39.5 |
| **Sharks vs Knights** (Fri, Ocean Protect) | Sharks by 11.9 | 31.4–19.5 | 50.9 | 1.19 | 6.22 | 1.13 | 5.93 |
| **Roosters vs Storm** (Fri, Allianz) | Roosters by 9.1 | 27.8–18.7 | 46.5 | 1.29 | 4.46 | 1.23 | 4.25 |
| **Raiders vs Rabbitohs** (Sat, GIO) | Raiders by 4.5 | 27.2–22.7 | 49.9 | 1.55 | 2.83 | 1.47 | 2.69 |
| **Warriors vs Dragons** (Sat, Go Media) | Warriors by 26.1 | 33.2–7.1 | 40.3 | 1.02 | 67.5 | 0.97 | 64.3 |
| **Bulldogs vs Tigers** (Sat, Accor) | Bulldogs by 10.2 | 25.3–15.1 | 40.4 | 1.25 | 5.06 | 1.19 | 4.82 |
| **Titans vs Sea Eagles** (Sun, Cbus Super) | Manly by 9.4 | 13.1–22.5 | 35.6 | 4.61 | 1.28 | 4.39 | 1.22 |
| **Dolphins vs Cowboys** (Sun, Suncorp) | Dolphins by 7.0 | 30.3–23.3 | 53.6 | 1.39 | 3.57 | 1.32 | 3.40 |

---

## Game Notes — tiers + T9 matrix confluence

### Panthers vs Broncos — no matrix confluence, model number is extreme
- Build-up: T1 +14.1 (huge ELO gap, H:29.9 A:15.9), T2 +6.0 style family [A,D], T5 +1.2 (Broncos worse hit — Reynolds elite doubtful) → **Panthers -23.7**
- T9: no 3-way confluence either side — matrices are silent here, which is itself worth noting given how large the model number is
- ⚠️ A 23.7pt handicap is the biggest number of the round. No T6 to sanity-check it against a whistle-heavy/flow-heavy ref yet. Treat as a strong ELO-driven read, not a validated price, until refs land.

### Sharks vs Knights — matrices strongly agree with the model
- Model Sharks -11.9 (T1 +8.3, T5 +2.0 — Knights down 6 including Marzhew/Hopwood/Saifiti)
- T9: **7-way handicap SHARKS COVER** + **5-way H2H BACK HOME** — the strongest stack of the round, same direction as the model on both markets
- Totals: 3-way UNDERS lean vs model's 50.9 total — mild conflict worth a look if a total market opens near 51-52

### Roosters vs Storm — biggest injury story of the round, no clean signal
- Both captains/spine out: **Tedesco (elite) out for Roosters, Munster (elite) + Kamikamica + Hughes out for Storm** — Storm's absence list is longer (6 outs, incl. two elite-tier) than Roosters' (5 outs, 1 elite)
- Model still has Roosters -9.1 despite the head-to-head injury comparison favouring Roosters relatively, not absolutely
- No T9 confluence fired either side — matrices flat here. Genuinely thin signal for a game with this much team-news volatility; re-price if either spine player is a late inclusion

### Raiders vs Rabbitohs — matrices agree, model is the most conservative number
- Model Raiders +4.5 only, despite T5 showing **Latrell Mitchell (elite) out** for Souths plus five more rotation/doubtful Rabbitohs
- T9: **3-way H2H BACK HOME** (100% this exact fixture direction, 88% reverse) — matrices back the same side as the model but more strongly than the model's modest 4.5pt line suggests
- Worth a look if the market prices Raiders shorter than ~-4.5

### Warriors vs Dragons — biggest number after Panthers/Broncos, but this one has matrix support
- Model Warriors -26.1 (T1 +18.7 is doing almost all of it — Dragons have been the league's weakest team this season)
- T9: **4-way handicap AWAY COVERS** (i.e. matrices lean Dragons +26.1, not Warriors) **against** the model direction, plus a 3-way H2H lean to Dragons too — this is a real model-vs-matrix conflict, and per house rules a number this size with matrices pointing the other way is a no-play zone on the handicap
- Totals: 4-way UNDERS confluence agrees with the model's low 40.3 total
- ⚠️ Remember the T2 import bug above — Dragons' style row may be stale, which could be inflating this gap artificially. Recheck once the importer is fixed.

### Bulldogs vs Tigers — matrices strongly favour the home side
- Model Bulldogs -10.2 (T2 +4.0 style edge, T5 +1.5 — Tigers down 6 including Koroisau elite)
- T9: **6-way H2H BACK HOME** + **3-way handicap HOME COVERS** — matrices agree directionally and add extra conviction (Tigers 0% historical away wins at Accor in this sample)

### Titans vs Sea Eagles — matrices split on H2H, agree on handicap
- Model Manly -9.4. T9 handicap **4-way HOME COVERS** (i.e. Eagles, who are the model's road favourite here — "home" in the matrix output refers to Titans hosting, matrix backing the visiting Eagles to cover) agrees with the model direction
- H2H matrices actually split both ways (4-way BACK AWAY vs 4-way BACK HOME) depending on which angle set you weight — genuinely mixed, handicap is the cleaner read this game
- Moderate wind at Cbus Super (22.7km/h) — no totals adjustment applied by T8, worth a manual sanity check if a wind-affected total opens materially under 35.6

### Dolphins vs Cowboys — thin signal, model and matrices roughly line up
- Model Dolphins -7.0. T9: 3-way handicap HOME COVERS agrees; H2H matrix lean is toward Cowboys (BACK AWAY) — mixed picture, no strong single read here

---

## Tier Coverage Report — 8/9 tiers real (89%)

| Tier | Status | Source / reason |
|------|--------|-----------------|
| T1 ELO | ✅ REAL | Rebuilt today — R19 results loaded first (Warriors, Sharks, Raiders, Roosters, Rabbitohs, Cowboys, Storm all updated), ELO current through R19 |
| T2 Style | ✅ REAL (1 known gap) | Style stats scraped Jul 14, 16/17 teams updated. **"St George Illawarra Dragons" alias miss recurs — see warning #4** |
| T3 Schedule/rest | ✅ REAL | From fixture, rest days computed directly |
| T4 Venue | ✅ REAL | DB venue table |
| T5 Injuries | ✅ REAL | Zero Tackle scrape this morning — 91 records across 17 teams |
| T6 Referee | ❌ NOT AVAILABLE | 0/8 — NRL.com hasn't published R20 appointments yet. Neutral default across the board. **Reprice when refs land (Wed/Thu).** |
| T7 Emotional | ✅ REAL | Scraper ran fresh — 1 flag (Roosters vs Storm recognised rivalry, normal tier). No blowout/coach-change/milestone triggers found this week |
| T8 Weather | ✅ REAL | Tomorrow.io fetched today, 8/8 games — mostly clear, one moderate-wind game (Titans/Eagles) |
| T9 Matrices | ✅ REAL | Regenerated post-R19 results, confluence JSON written, pushed to Supabase — 6/8 games showed 3+ way confluence |
| T10 Origin | ✅ REAL + dormant (expected) | No active camp window this round — genuinely nothing to price, not a gap |
| ML shadow | ❌ N/A | NRL ML not implemented |
| Market/EV | ❌ BLOCKED | Odds API still down since Jul 3 — no snapshot to compare against |

**8 of 9 applicable tiers populated with real, fresh data (89%) — clears the 75% mandatory bar.** The one gap (T6 referees) is a genuine "not yet announced" situation, not a scraper failure, and should resolve with a reprice later this week.
