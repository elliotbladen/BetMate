# 2026 Finals — Emotional tier added (NRL T7 / AFL T6)

**Run date:** 2026-09-08
**Supersedes the emotional layer only** in `nrl_finals_week1_pricing_2026.md` and
`afl_semifinals_pricing_2026.md` (both 2026-09-06). Every other tier in those
reports stands unchanged.

**Method:** production tier functions, no hand calculation —
`pricing.tier7_emotional.compute_emotional_adjustments` with the canonical
`config/tiers.yaml :: tier7_emotional`, and `pricing.afl_tier6_emotional.compute_t6`
with `AFL_T6_CONFIG`. Driver: `scripts/price_finals_emotional_2026.py`.

Fair H2H is Φ(margin / 12.0), the same margin_std the 6 Sep NRL report used —
it reproduces that report's QF prices exactly ($1.24/$5.12, $1.34/$3.92).

---

## Why this run exists

- **AFL T6 was never priced.** The 6 Sep report records it as
  `❌ no scraper for finals — left neutral`.
- **NRL T7 was priced but contained two invalid flags** (below). Correcting them
  moves two of the four games.

---

## Tier output

### NRL Finals Week 1 — T7

| Game | Match | T7 hcp | T7 totals |
|---|---|---:|---:|
| QF1 | Penrith v Roosters | −1.00 | +0.50 |
| QF2 | Warriors v Dolphins | 0.00 | 0.00 |
| EF1 | Sharks v Cowboys | 0.00 | +0.60 |
| EF2 | Rabbitohs v Knights | 0.00 | +0.60 |

Positive handicap = home emotional edge.

### AFL Semi Finals — T6

| Game | Match | T6 hcp | T6 totals |
|---|---|---:|---:|
| SF1 | Fremantle v Geelong | 0.00 | +1.00 |
| SF2 | Brisbane v Adelaide | 0.00 | +1.00 |

---

## Flags fired

| Game | Team | Flag | Strength | Evidence |
|---|---|---|---|---|
| QF1 | Sydney Roosters | shame_blowout | normal | Lost 20–50 to Souths in R27 = **exactly 30 pts**, meets the 30+ NRL threshold |
| EF1 | Cronulla Sharks | must_win | normal | Sudden-death elimination final |
| EF1 | North QLD Cowboys | must_win | normal | Sudden-death elimination final |
| EF2 | South Sydney Rabbitohs | must_win | normal | Sudden-death elimination final |
| EF2 | Newcastle Knights | must_win | normal | Sudden-death elimination final |
| SF1 | Fremantle Dockers | must_win | normal | Sudden-death semi final |
| SF1 | Geelong Cats | must_win | normal | Sudden-death semi final |
| SF2 | Brisbane Lions | must_win | normal | Sudden-death semi final |
| SF2 | Adelaide Crows | must_win | normal | Sudden-death semi final |

`must_win` is applied **only to sudden-death games**. The two NRL qualifying
finals carry a double chance, so the desperation premium does not apply there.
Because both sides of a sudden-death game receive it, the margin effect nets to
zero by construction and only the total moves — which is the intended behaviour.

**Judgment call flagged:** the config wording for `must_win` is
"finals-*positioning* desperation game", i.e. late-season games to *reach* the
finals. Extending it to elimination finals themselves is a reading, not a
documented rule. It is symmetric and small (totals only), but it should be
ratified or removed rather than left implicit.

## Considered and rejected

| Game | Team | Flag | Why not |
|---|---|---|---|
| NRL EF1 | North QLD Cowboys | shame_blowout | Lost by **20** to Canberra in R27. NRL threshold is **30+**. **Was applied on 6 Sep — invalid.** |
| NRL EF2 | South Sydney | star_return (Latrell Mitchell) | Latrell **returned in R27** and scored in the 50–20 win. This is not his return game. **Was applied on 6 Sep — stale by one round.** |
| NRL EF2 | South Sydney | personal_tragedy (Jai Arrow) | Genuine adversity — forced retirement on a serious health diagnosis — but his 100th/final game was R27, so the peak event has passed. Config rates this flag's evidence quality as "None". Left neutral. |
| NRL QF2 | Dolphins | star_return (Cobbo, Nikorima) | Both were **rested** in R27, not returning from a long absence. Fails the flag definition. |
| AFL SF1 | Fremantle | shame_blowout | Lost QF by **32**. AFL threshold is **60+** (10 goals). |
| AFL SF2 | Brisbane | shame_blowout | Lost QF by **53** — under the 60+ threshold despite the poor-performance narrative. |
| AFL SF1 | Fremantle | star_return (Sean Darcy) | Recalled for the semi, but absent from the current injury list and no verifiable 6+ week absence. Selection recall, not a star return. |

---

## Updated model prices

### NRL Finals Week 1

| Game | Match | Margin (old → new) | Total (old → new) |
|---|---|---|---|
| QF1 | Penrith v Roosters | Penrith −10.3 → **−10.3** | 43.2 → **43.2** |
| QF2 | Warriors v Dolphins | Warriors −7.9 → **−7.9** | 45.7 → **45.7** |
| EF1 | Sharks v Cowboys | Sharks −12.0 → **−13.0** | 46.3 → **46.4** |
| EF2 | Rabbitohs v Knights | Souths −10.7 → **−9.2** | 50.1 → **50.2** |

Fair H2H at the new margins:

| Game | Fair line | Home | Away | Home win % |
|---|---|---:|---:|---:|
| QF1 | Panthers −10.3 | $1.24 | $5.12 | 80.5% |
| QF2 | Warriors −7.9 | $1.34 | $3.92 | 74.5% |
| EF1 | Sharks −13.0 | $1.16 | $7.18 | 86.1% |
| EF1 | *after manual overlay* −11.5 | $1.20 | $5.92 | 83.1% |
| EF2 | Rabbitohs −9.2 | $1.28 | $4.51 | 77.8% |
| EF2 | *after manual overlay* −7.2 | $1.38 | $3.65 | 72.6% |

Manual overlays are the 6 Sep report's own (EF1 Dearden back −1.5; EF2 Knights
bans possibly served −2.0), carried onto the corrected base.

### AFL Semi Finals

| Game | Match | Rules margin | ML margin | MC margin | Rules total (old → new) | MC total |
|---|---|---:|---:|---:|---|---:|
| SF1 | Fremantle v Geelong | Fre −3.0 | Fre −4.0 | Fre −3.8 | 183.7 → **184.7** | **185** |
| SF2 | Brisbane v Adelaide | Bris −15.8 | Bris −25.8 | Bris −23.3 | 207.5 → **208.5** | **208** |

AFL margins are unchanged — T6 is 0.00 on the handicap in both games because
`must_win` is symmetric. Only the totals move, +1.0 each.

---

## TOTALS SUMMARY

| Game | Match | Model total |
|---|---|---:|
| NRL QF1 | Penrith v Roosters | **43.2** |
| NRL QF2 | Warriors v Dolphins | **45.7** |
| NRL EF1 | Sharks v Cowboys | **46.4** |
| NRL EF2 | Rabbitohs v Knights | **50.2** |
| AFL SF1 | Fremantle v Geelong | **184.7** rules / 161 ML / 185 MC |
| AFL SF2 | Brisbane v Adelaide | **208.5** rules / 153 ML / 208 MC |

⚠️ **AFL totals carry two live warnings from the 6 Sep run and should not be bet.**
The rules and ML totals disagree by 23.7 pts (SF1) and 55.5 pts (SF2), and the
weather tier applied a −4.5 "light rain" totals penalty on trace precipitation
(0.3 mm / 0.1 mm — effectively dry). AFL totals are also the model's worst
documented market at −15.4% ROI across 39 bets this season.

NRL totals are on a sounder footing but there is no market to price against.

---

## Tier coverage after this run

| Sport | Before | After |
|---|---|---|
| NRL | T7 ✅ but 2 of 3 flags invalid | T7 ✅ **corrected** |
| AFL | T6 ❌ neutral | T6 ✅ **priced** |

Unchanged gaps: NRL T6 referees (finals appointments Tuesday), NRL T8 weather
(manual estimate), AFL T2 style (3 rounds stale), AFL T7 weather (over-twitchy
at trace precip), and **market/EV for both — the Odds API is deactivated**
(`DEACTIVATED_KEY` confirmed 2026-09-08).
