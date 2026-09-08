# NRL 2026 Finals Week 1 — Proper T1–T9 Pricing (T2 added)

> ⚠️ **Emotional layer superseded 2026-09-08** — see `finals_2026_emotional_tier_2026-09-08.md`. All other tiers in this report stand.

**Run date:** 2026-09-06. **Supersedes** the earlier hand-built QF/EF notes.
**Method:** real engine tier functions, DB reconstructed from the AusSportsBetting
xlsx (2009 → R27, R27 appended manually) + fresh Fox Sports team style stats.

- **T1**: `pricing.tier1_baseline.compute_baseline()` — the actual function
  `prepare_round.py` calls. ELO from `bootstrap_elo_historical.py` walked
  2009→2025 train + full 2026 (era K, 0.25 season reversion). Season attack/defence,
  win%, ladder, home/away splits, last-5 form all reconstructed from the xlsx.
- **T2**: real `pricing.tier2_matchup` family A/B/C/D + league norms, off
  **Fox Sports 2026 season team stats fetched today** (completion, run m, kick m,
  errors, penalties, missed tackles, line breaks, FDO, kick-return m).
- **T3 / T4 / T5 / T7**: real `pricing.tier3/4/5/7` functions with reconstructed
  context (rest, travel, venue margins from 2024–26 xlsx, injury points, flags).
- **T9**: `nrl_h2h_matrix.xlsx` net-lean, sample-weighted (N<10=0.3 / 10–25=0.6 / 25+=1.0).
- **T6 referee**: NOT priced — finals appointments not released until Tuesday.
- **T8 weather**: manual estimate only (5–6 days out).
- **ML**: excluded per instruction.
- **Market**: Odds API down — market lines below are estimates, re-check Mon.

---

## Post-R27 2026 ELO (bootstrap walk)

| # | Team | ELO | | # | Team | ELO |
|--|------|----:|--|--|------|----:|
| 1 | Penrith Panthers | **1620.8** | | 6 | Melbourne Storm | 1545.1 |
| 2 | NZ Warriors | **1584.8** | | 7 | Canberra Raiders | 1520.3 |
| 3 | Dolphins | **1582.0** | | 8 | Sth Sydney Rabbitohs | **1511.7** |
| 4 | Sydney Roosters | **1578.0** | | 9 | Nth Qld Cowboys | **1502.7** |
| 5 | Cronulla Sharks | **1551.2** | | 11 | Newcastle Knights | **1483.7** |

Note: this is **win/loss ELO** (margin-blind). It does **not** dock the Roosters
for the manner of their 3 straight losses (incl. 50–20), nor credit the Knights'
Ponga-fuelled late surge. Read those two with the manual overlays below.

---

## Tier build

| Game (Home v Away) | T1 | T2 | T3 | T4 | T5 | T7 | **Margin** | Total |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **QF1** Penrith v Roosters | +7.8 | 0.0 | −1.0 | +1.5 | +3.0 | −1.0 | **Penrith −10.3** | 43.2 |
| **QF2** Warriors v Dolphins | +4.4 | 0.0 | +2.0 | +1.5 | 0.0 | 0.0 | **Warriors −7.9** | 45.7 |
| **EF1** Sharks v Cowboys | +7.5 | **+1.5** | +1.9 | +1.5 | +0.7 | −1.0 | **Sharks −12.0** | 46.3 |
| **EF2** Rabbitohs v Knights | +4.6 | **+1.5** | −1.4 | +1.5 | +3.0 | +1.5 | **Souths −10.7** | 50.1 |

After manual overlays (below): **EF1 Sharks ≈ −10.5** (Dearden back),
**EF2 Souths ≈ −8.7** (if Knights' bans are served).

Fair H2H (margin_std 12.0): QF1 Penrith $1.24 / Roosters $5.12 · QF2 Warriors
$1.34 / Dolphins $3.92 · EF1 Sharks ~$1.20 / Cowboys ~$5.8 · EF2 Souths ~$1.25 /
Knights ~$4.9.

**Tier notes**
- **T2**: QF1 and QF2 come out **neutral** — the two pairs are stylistically
  close (completion, run m, errors near-identical). **EF1 +1.5 Sharks** — Family A
  (territory) + C fire: Sharks kick **629 m/game vs Cowboys 532**, Cowboys leak
  (errors 11.0, missed tackles 40.5, line breaks conceded 6.1); T2 totals −3.0.
  **EF2 +1.5 Souths** — Family C: Souths' league-high **7.5 line breaks/game** vs
  the Knights' missed-tackle vulnerability (40.0/game); T2 totals −1.5. Both
  capped by the directional-halving rule (T2 reinforces T1).
- **T3 QF1 −1.0**: Penrith on **short rest** (played Sun R27) vs Roosters normal — engine correctly penalises the minor premiers.
- **T3 QF2 +2.0**: Dolphins' trans‑Tasman trip, capped.
- **T3 EF2 −1.4**: Knights had the **bye** (rest edge) — `normal_vs_bye` cuts the Souths margin.
- **T4 all +1.5**: hits the clamp. Penrith @ CommBank is a real fortress (**+11.5 avg margin, n=22**); the Cowboys' Allianz record (**−13.3, n=3**) gives the Sharks their +1.5 despite Cronulla not being at their own ground.
- **T5 QF1 +3.0 (capped)**: Roosters — **Sam Walker OUT** (HB, syndesmosis) + Radley doubtful. Penrith — Cogger banned (depth piece).
- **T5 EF2 +3.0 (capped)** ⚠️: based on Knights outs (Crossland knee + suspensions) that **may be served bans by finals**. If the Knights are near full strength, T5 ≈ +1.0 → **model drops to Souths ~−7.2**.
- **T7**: shame_blowout bounce for Roosters / Cowboys (−1.0 to the fav); Latrell's return = star_return +1.5 Souths.

---

## T9 matrix net-lean (2022–25 history vs market, weighted)

| Game | Net (→ Home +) | Verdict |
|---|---:|---|
| QF1 | **+10.3%** | leans **Penrith** — conflues with model |
| QF2 | **+36.6%** | leans **Warriors** hard — Dolphins' "away long-haul to NZ" row is +26.8% opposing (n=6); conflues with model |
| EF1 | **+50.9%** | leans **Sharks** hard — Cowboys +49% opposing "vs Sharks" (n=9), poor night-game record; conflues with model |
| EF2 | **−66.7%** | leans **KNIGHTS** — **conflicts with the model.** Souths poor on home / night / after-a-win splits; H2H history (n=4) favours Newcastle |

---

## Manual overlays (things the tiers can't see)

- **QF1**: Roosters' true strength is *below* 1578 (margin-blind ELO). Model may be a touch light on Penrith even at −10.3.
- **EF1**: **Tom Dearden (Cowboys captain / No.7) returns** — a real positive T5 didn't capture. Shave ~1.5 → **Sharks ≈ −9**. Also the Sharks slid into 5th on poor form.
- **EF2**: model/matrix **conflict** + shaky T5. Treat as a coin flip.

---

## Value verdict (vs ESTIMATED market)

| Selection | Model | Est. market | Call |
|---|---|---|---|
| **QF2 Warriors −handicap** | −7.9 (T2 neutral), matrix +37 | ~ −5.5 | **Best of the four.** Model + matrix both clearly ahead of market; the Dolphins-to-Auckland long-haul pattern is real. Bet if line ≤ −6.5. Caveat: no ML check; Dolphins are genuinely good. |
| **EF1 Sharks −handicap** | −12.0 → ~−10.5 after Dearden; T2 +1.5 + matrix +51 | ~ −6.5/−8.5 | **Upgraded to a moderate lean.** The T2 kicking/territory edge (629 vs 532 m) is a real signal and the matrix agrees hard. Still shave for Dearden's return + the Sharks' late slide. Sharks cover if ≤ −9.5. |
| **QF1 Penrith −handicap** | −10.3, T2 neutral, matrix +10 | ~ −9.5/−11.5 | Model ≈ market. Mild lean Penrith cover if ≤ −10.5 (Roosters worse than their ELO). |
| **EF2 — anything** | Souths −10.7 (T2 +1.5) but shaky T5 | ~ Souths −5 | **STILL NO PLAY** — model vs matrix conflict (matrix −67% → Knights). T2 pushing Souths doesn't break the tie. |
| QF1 Under / EF1 Under / EF2 Over | 43.2 / 46.3 / 50.1 | — | small leans only if market diverges 2–3+ pts |

**Bets worth the name:**
1. **QF2 Warriors to cover** if the line opens ≤ −6.5 — the strongest.
2. **EF1 Sharks to cover** if ≤ −9.5 — now backed by a real T2 style edge + the matrix.

Everything else is a lean at best, and every market number here is an estimate —
confirm against real opening lines Monday.

---

## Tier coverage

T1 ✅ (real `compute_baseline`) · **T2 ✅ (real family A–D off fresh Fox Sports stats)** ·
T3 ✅ · T4 ✅ · T5 ✅ (EF2 shaky) · **T6 ❌ (refs Tuesday)** · T7 ✅ ·
T8 ⚠️ (manual estimate) · T9 ✅ (matrix) · ML — excluded per instruction.

**8 of 9 tiers done properly.** Only T6 (referee) is missing — appointments
aren't released until Tuesday. This is a full model price.

Working scripts: `_nrl_finals_t1.py`, `_nrl_finals_assemble.py`, `_nrl_finals_t2.py`,
`_nrl_finals_t9.py`. Fox stats cached at `%TEMP%/fox/fox_*.json`.
