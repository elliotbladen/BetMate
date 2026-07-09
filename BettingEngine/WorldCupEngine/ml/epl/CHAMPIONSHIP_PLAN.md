# Championship Engine — Proposed Architecture & Build Plan
**Drafted:** 2026-07-09 | **Status: AWAITING USER OK — no code written**
Companion research: `LEAGUE_EXPANSION_RESEARCH.md` | Parent engine: `ARCHITECTURE.md` (EPL)

---

## Step 0 — League-parameterised refactor (do this FIRST)

Before any Championship code, extract the EPL engine's shared core so we get one engine
with N league configs, not three diverging copies:

```
ml/football/                        ← shared core (moved out of ml/epl/)
├── models/
│   ├── dixon_coles.py              (gains a goals-vs-xG input switch)
│   ├── elo.py                      (gains promotion/relegation seeding hooks)
│   ├── calibration.py              (unchanged — calibrators are per-league instances)
│   └── tiers.py                    (tier stack; availability driven by league config)
├── price_match.py                  (reads --league)
├── backtest/walk_forward.py        (reads --league)
├── leagues/
│   ├── epl.yaml                    ← current EPL constants, verbatim
│   └── championship.yaml           ← everything below
└── data/{epl|championship}/...
```

A league config declares: data source + league code, goals-fed vs xG-fed, base scoring
constants, HFA, decay half-life, calibrator path, and which tiers are active.
EPL backtest must reproduce **RPS 0.1335 exactly** after the refactor before we touch
Championship — that's the regression gate.

---

## The Championship model (championship.yaml + new components)

### Core
| Component | EPL | Championship | Why |
|---|---|---|---|
| D-C input | xG (Understat) | **Goals** (no Understat coverage) | Classic D-C; 46 games/season partly offsets goals noise |
| Blend | D-C 70 / Elo 30 | Same starting point — re-tune in backtest | |
| Data | football-data E0 | **football-data E1**, 2014/15→2025/26 (~6,600 matches — bigger than EPL's 4,180) | Same fetcher, league-code change |
| Base goals | ~2.8 | **refit ≈2.4–2.5** | League scores less |
| Draw handling | D-C tau | **Re-fit and validate against ~33% draw rate** | Draw-heaviest big league in Europe |
| HFA | per-team, EPL-fit | **per-team, E1-fit (expect higher)** | Home wins near 50% in 24/25 |
| Decay half-life | 693d | **Longer (goals noisier) — grid-search in backtest** | |
| Calibration | isotonic O2.5 | **Own isotonic instance** (O2.5 base rate sub-50% — EPL calibrator would poison it) | |

### Tier stack
| Tier | Status | Detail |
|---|---|---|
| T2 pressing | **REPLACED** | No PPDA. V1: shots-based suppression proxy (shots for/against vs league avg from E1). Kept at LOW weight, and only ships if the backtest ablation shows it helps — otherwise dropped, honestly. |
| T3 form + rest | KEPT, hotter | Fires constantly (46 rounds + midweeks). Validate the ×0.94 fatigue multiplier doesn't overcook Christmas congestion. |
| T5 injuries | KEPT | Manual position flags (`--injuries-home "ST,CM"`), same weights initially — Championship squads are thinner, so if anything the weights are conservative. |
| T6 referee | KEPT | E1 has referee names. Refit goals/game deviations on E1. |
| T7 set-piece | KEPT | E1 has corners. Refit league averages; Championship is MORE set-piece dependent than EPL, expect a bigger coefficient. |
| **T8 season-reset prior** | **NEW — the centrepiece** | Every August, 6 new teams have no in-league history. Seed strength from **ClubElo** (free API, covers English tiers 1–5) + a **parachute flag**: relegated Y1/Y2/Y3 get a graded attack/defence prior boost (research: parachute clubs 3× promotion rate, £90m vs £27m revenue); promoted-from-L1 get a discount prior. Prior weight decays linearly to zero by ~matchweek 15 as real E1 data takes over. |
| **T9 manager change** | **NEW** | Manual flag (same pattern as NRL emotional flags): new-manager bounce, capped small (+0.05–0.10 xG equivalent), because sackings are constant in this league. |

### Markets & betting posture
Same menu as EPL — **AH primary, O/U 2.5 second, 1X2 last** — with two Championship
notes: (1) higher bookmaker margins mean EV thresholds must clear more vig; (2) the
hypothesised exploitable window is **August–October** (market also flying blind on the
6 new teams — our T8 prior is the bet). Playoffs (May, two-legged semis + Wembley
final) are out of scope for v1; the WorldCupEngine knockout machinery covers them later.

---

## Testing — yes, EPL regime + two Championship-specific additions

**1. Walk-forward backtest, identical to EPL:** train 2014/15→, test three full held-out
seasons (**2022/23, 2023/24, 2024/25** — with 2025/26 available as a fourth). Same
metrics: RPS / Brier / LogLoss / accuracy.
**Benchmark honesty:** do NOT expect EPL's 0.1335. The Championship is inherently
noisier. The pass bar is *relative*: our RPS must beat (a) the academic ~0.1925-class
benchmark and (b) sit within ~2% of the **market's own RPS** computed from de-vigged
E1 closing odds — that's the real opponent.

**2. CLV backtest (better than what EPL had):** football-data E1 carries Pinnacle
opening AND closing odds from 2019/20 → we can compute genuine CLV per simulated bet
across 5+ seasons before risking a cent. Pass bar: positive CLV on the AH/totals
signal segments.

**3. August-window test (Championship-specific):** score the model's accuracy and CLV
separately for matchweeks 1–15 vs 16–46, with and without the T8 prior. This directly
tests the "edge lives in early season" hypothesis and proves T8 earns its place.

**4. Ablations:** each tier on/off (especially the T2 shots proxy) — a tier that
doesn't move RPS or CLV gets cut, not kept.

**5. Live paper phase:** GW1–GW10 paper-tracked CLV only (same house rule as
NRL/AFL/EPL). No real stakes until the paper CLV is positive.

---

## Build sequence & effort

| Phase | What | Est. |
|---|---|---|
| 1 | League-parameterised refactor + EPL regression gate (RPS must reproduce 0.1335) | 1 session |
| 2 | E1 fetcher + goals-fed D-C + refit constants (base, HFA, decay, tau) | 1 session |
| 3 | Tiers: T6/T7 refit, T2 shots proxy, T3 congestion check | 1 session |
| 4 | T8 season-reset prior (ClubElo API + parachute flags) + T9 manager flag | 1–2 sessions |
| 5 | Full backtest suite (walk-forward + CLV + August-window + ablations) | 1 session |
| 6 | Paper-trade from Championship GW1 (~Aug 8 — season starts a week before EPL) | ongoing |

Total: ~5–6 sessions to backtested and paper-ready, comfortably before the season.

**Open questions for the user:**
1. OK to do the refactor (Step 0) first? It touches the EPL engine's file layout (not its numbers).
2. T8 parachute prior sizes will be fit from data, but the ClubElo dependency is new — happy to add one external API (free, no key)?
3. Do we want 2025/26 as a fourth test season, or hold it out entirely as final validation after the model is frozen?
