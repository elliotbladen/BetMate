# NRL 2026 Elimination Finals — Pricing Report

**Run date:** 2026-09-06 — companion to `nrl_qualifying_finals_pricing_2026.md`.
**Same limitations:** NRL engine can't run here (no NRL tables in `model.db`,
ELO ~2 rounds stale, ML features frozen 2026-04-12, Odds API down). Manual tier
build. Weaker than the AFL semis price-up.

---

## Fixture (final 8 now locked)

| Game | Home (seed) | Away (seed) | Venue | Slot |
|------|------------|------------|-------|------|
| **EF1** | Cronulla Sharks (5th) | North Queensland Cowboys (8th) | Allianz Stadium, Sydney (relocated home final) | Sat evening |
| **EF2** | South Sydney Rabbitohs (6th) | Newcastle Knights (7th) | Sydney (Allianz / Accor) | Fri evening — opens the finals |

R27 that shaped this: **Rabbitohs 50–20 over an under-strength Roosters** (Souths
to 6th, home final); **Cowboys lost 50–30 to Canberra** (held 8th, Raiders 9th);
**Knights had the bye** (Ponga fit and firing after his mid-season Lisfranc);
Sharks locked 5th off a poor late-season slide.

---

## Rating base (hand-adjusted from `results/r27_pricing_2026.csv`)

| Team | CSV ELO | Since | Working ELO |
|------|--------:|------|------------:|
| Cronulla Sharks | 1546.2 | **late-season slide** (ESPN "big slides") | **~1542** ↓ |
| Nth Qld Cowboys | 1513.0 | lost R27 50–30, conceded 50 | **~1507** ↓ |
| Sth Sydney Rabbitohs | 1514.5 | **surged**, 50–20 v weak Roosters (regress it) | **~1528** ↑ |
| Newcastle Knights | 1530.8 | bye R27; Ponga back in top gear | **~1526** |

`points_per_elo_point = 0.08`, league HFA ≈ 3.5 (reduced at a relocated venue).

---

## EF1 — Cronulla Sharks v North Queensland Cowboys (Allianz)

| Tier | Hcp (Sharks +) | Note |
|------|---:|------|
| T1 baseline | **+6** | ELO +2.8 + reduced HFA ~+2 (Allianz isn't PointsBet Stadium) + slight form |
| T3 situational | **+3** | **Cowboys travel Townsville→Sydney (~1,700 km)**; Cowboys off conceding 50 |
| T4 venue | +0.5 to +1 | relocated home final — not a Sharks fortress |
| T5 injuries | 0 (TBD) | Sharks carried injuries through their slide; Cowboys manage Taumalolo — check team lists Tue |
| T6 referee | n/a | not announced |
| T7 emotional | −0.5 (Cowboys) | Cowboys off a 50-point shame blowout |
| T8 weather | pending | Sydney mid-Sept — check game day |
| **Model margin** | **Sharks ≈ −10 to −12** | |
| Model total | **~44–47** | Cowboys leaky, both can score |

**Estimated market:** Sharks −6.5/−8.5, H2H Sharks ~$1.42 / Cowboys ~$2.90.

**Read:** model ahead of market on the Sharks, but that's largely the **home
overcook** plus the Cowboys' travel. Cowboys keep genuine x-factor (Dearden,
Drinkwater, Holmes) and finals are volatile. Shave the model → **roughly fair,
slight Sharks handicap lean; Cowboys +8.5 has merit if the line inflates.**

---

## EF2 — South Sydney Rabbitohs v Newcastle Knights (Sydney)

| Tier | Hcp (Souths +) | Note |
|------|---:|------|
| T1 baseline | **+4 to +5** | ELO level + HFA 3.5; Souths' form spike regressed (50–20 was vs a checked-out Roosters) |
| T3 situational | +1 to +2 | Knights short trip; **Knights bye = rested but rusty**, Souths match-fit + momentum |
| T4 venue | +2 to +3 | Souths home final, big crowd |
| T5 injuries | 0 to +1 (TBD) | **Latrell Mitchell durability = swing factor** (assume plays); **Bradman Best (Knights, hamstring) — confirm**; Ponga IN and firing |
| T6 referee | n/a | not announced |
| T7 emotional | +1 | Souths momentum + Bennett finals nous; Jai Arrow 100-game emotion carried over |
| T8 weather | pending | — |
| **Model margin** | **Souths ≈ −9 to −12** | |
| Model total | **~45–48** | both attacking, Souths humming |

**Estimated market:** Souths −3.5/−6.5 (maybe as short as −4.5), H2H Souths ~$1.50 / Knights ~$2.55.

**Read:** **this is the shakiest of the four finals.** The model has Souths well
clear; the market won't. The 50–20 was one game against an under-strength
opponent, **Ponga is a genuine finals difference-maker**, and the model's home
lean here is exactly the documented **NRL +9–11% home overcook**. Treat as close
to a coin flip. If Souths get bet up to −6.5+, **Knights + the points is the
value side.**

---

## Value verdict

| Selection | Confidence | Why / why not |
|---|---|---|
| EF1 Sharks −handicap (small line) | Mild lean | Cowboys travel + conceded 50 last week is real; but shave for home overcook |
| EF1 Cowboys +8.5 | Watch | if the line inflates past the model-shaved fair (~−8) |
| EF2 — either side | **No** | coin flip; model's Souths edge is the untrustworthy home lean + a one-game form spike vs Ponga's finals class |
| EF2 Knights +pts | Watch only | value side if Souths get over-bet to −6.5+ |
| Totals (both) | Mild over lean | EF1 ~45 / EF2 ~46 — bet only if markets open ≥ 2–3 pts under that |

**No confident bets.** Every market figure is an estimate (Odds API down) —
re-check real opening lines Sun night / Mon. Both EFs are genuine 50/50-ish
finals where the rules model's home lean should not be trusted at face value.

---

## Tier coverage — BELOW 75%

T1 (stale ELO + form) ⚠️ · T3 ✅ · T4 ✅ · T5 partial ⚠️ · T7 ✅ ·
**T6 refs ❌ (Tue)** · **T8 weather ❌ (too far out)** · **ML shadow ❌ (features frozen April)** ·
**Market/EV ❌ (Odds API down — estimates only)**.
5 of 9 in-scope layers genuinely populated. Directional first look, not a
betting price.
