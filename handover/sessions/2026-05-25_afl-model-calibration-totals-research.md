# Session Diary — 2026-05-25 — AFL Model Calibration + Totals Research

## What we did

### 1. Manual pricing — NRL R13 Cronulla vs Manly

Priced Cronulla vs Manly (assumed home at Sharks Stadium) across known tiers.

Key numbers (T1–T4 only, T5/T6/T7/T8 unknown):
- **T1:** −0.57 pts (Manly by 0.57 — coin flip). ELO says Cronulla by ~5 (ELO 1547 vs Manly ~1529 post-R12 update). Pythagorean ratings say Manly clearly better class (PA avg 19.8 vs Cronulla 26.0). Blend comes out near-even.
- **T2:** 0 — styles too similar, no family fires.
- **T3:** +1.5 to +2.0 for Cronulla (BYE vs Manly ~6-7 day rest). Matrix: bye_vs_normal = +1.5, bye_vs_short = +2.0.
- **T4:** +1.5 for Cronulla (Sharks Stadium fortress, avg margin +9.0 over 11 games, hits cap). −0.5 totals.
- **Known tiers total:** Cronulla −2.65, fair H2H ~1.70/2.42, total ~50.6 (model runs high, true fair ~42-45).

Key swing: **Trbojevic** (was out R12). If back = flip to Manly territory. If still out = Cronulla pushes to −6+.

Manly ELO update: 1519.09 → ~1529.35 (K=32, won 12-10 vs Gold Coast ELO 1389, expected=0.679).
Cronulla ELO: 1547.96 unchanged (bye).

### 2. AFL model accuracy diagnosis

Ran through R8–R9 model accuracy data. Found two clear culprits:

**Handicap (home bias):**
| Round | Rules vs market | Rules vs actual |
|---|---|---|
| R8 | +6.2 pts | +20.1 pts |
| R9 | +14.9 pts | +8.4 pts |

Model consistently giving home teams 6–15 more pts than market, and home teams underperforming model by 8–20 pts vs actual.

**Totals (systematic underestimation):**
| Round | Rules vs market | Rules vs actual |
|---|---|---|
| R8 | −13.3 pts | −20.4 pts |
| R9 | −7.8 pts | +4.0 pts |

West Coast vs Richmond (R8): rules total 136.9, market 185.5, actual 187. A 50 pt miss.

Root cause analysis:
- Home advantage: `home_advantage_points: 8.5` + `team_ha_max_delta: 3.0` = up to 11.5 pts HA at T1, then T4 adds up to 3 more. AFL home advantage in the market is 5-8 pts, not 14+.
- Totals: the additive averaging formula `((home_PF + home_PA) + (away_PF + away_PA)) / 2` double-counts defensive suppression. Two weak teams produce artificially low totals. The formula has no floor.

### 3. Config changes made

**`BettingEngine/config/sports/afl.yaml`:**
- `home_advantage_points: 8.5 → 0.0` (zeroed for recalibration)
- `team_ha_max_delta: 3.0 → 0.0` (prevents fortress effects adding HA back via side door)
- Rationale: T3 travel (scale 1.8, cap 5.0) now carries the real interstate penalty. T4 venue is inert anyway (no AFL venue profiles in DB — all 26 entries in venue_profiles are NRL grounds). The real AFL home edge IS largely the travel penalty for interstate teams.

### 4. T4 venue audit

Checked DB: `venue_profiles` table has 26 entries — all NRL venues. AFL venues (MCG, Adelaide Oval, Optus, GMHBA, Gabba etc.) exist in the `venues` table (IDs 1–16) but have **zero entries** in `venue_profiles`. `team_venue_stats` has 200 rows — all NRL. T4 is completely inert for AFL (falls through to zero for every AFL game). Do NOT disable T4 — when AFL venue profiles are eventually populated, the tier works automatically.

---

## Deep research — AFL totals methodology

Commissioned deep research across: Squiggle, Matter of Stats (MoSHBODS), Betfair Data Scientists, AFL Lab, The Arc, aussportstipping, academic papers (Manderson et al., Bradley-Terry). Full findings below.

### Root cause of the formula flaw

The additive model `((PF_h + PA_h) + (PF_a + PA_a)) / 2` fails because:
1. It uses raw averages, not opponent-adjusted ratings. West Coast's 65 pts/game was scored against good defences — their true attack is higher.
2. When two weak-offence/weak-defence teams play, the formula artificially collapses totals below league average. Real AFL: even bad teams participate in 170+ pt scoring environments.
3. Game-state distortion: garbage time in blowouts inflates PA for the winner and PF for the loser. Season averages include this noise.

### The fix — multiplicative model (used by every serious AFL model)

```python
LEAGUE_AVG = 88  # pts per team per game, current era (~176 combined)

home_attack  = home_PF_avg / LEAGUE_AVG
away_attack  = away_PF_avg / LEAGUE_AVG
home_defence = home_PA_avg / LEAGUE_AVG   # >1.0 = leaky
away_defence = away_PA_avg / LEAGUE_AVG

expected_home = LEAGUE_AVG * home_attack / away_defence
expected_away = LEAGUE_AVG * away_attack / home_defence
total         = expected_home + expected_away
```

This is the **Squiggle OFFDEF** formula (`85 × ATK / DEF`). When West Coast (attack 0.74) meets another weak defence (ratio 1.31), result is pulled toward league average, not below it. The formula is self-correcting.

### Five levers — priority order

**1. Multiplicative formula** (highest priority, fixes structural flaw, no new data needed)

**2. Opponent-adjusted ratings** (iterative ELO-style update, like Squiggle OFFDEF)
Each week: update attack rating based on how much team over/underscored vs what opponent's defence should have allowed. Closes the remaining gap to market after the formula fix.

**3. Shrinkage toward league average**
```python
shrink = n_games / (n_games + 12)   # K≈12 for AFL
adjusted = shrink * raw_rating + (1 - shrink) * 1.0
```
Prevents small samples or schedule-distorted early ratings from breaking totals.

**4. Hard venue lookup table** (key outliers)
| Venue | Adjustment |
|---|---|
| Marvel Stadium (Docklands) | +10 pts — enclosed roof, no weather downside |
| UTAS Stadium Launceston | −10 pts — coldest venue on calendar |
| UTAS Stadium Hobart | −10 pts |
| Norwood Oval (Adelaide) | −6 pts — small, congested |
| MCG | +2 pts |
| All others | 0 until data accumulated |

Marvel is the single biggest venue outlier — fully enclosed, eliminates the entire wet-weather tail. Manually seed these two rows in `venue_profiles` immediately.

**5. Weather calibration** (already in T8, numbers confirmed correct)
- Light rain (5–10mm): −7 pts
- Heavy rain (>10mm): −13 pts
- Wind >30 km/h: additional −4 pts

### Structural AFL scoring floor

Sub-130 combined totals are vanishingly rare in the modern era (~1-2 per season). The practical floor is ~130–140 pts even in wet/wind conditions. Any model output below ~145 for a non-extreme-weather game is underestimating.

### Why professional bookmakers are better at this

They use:
- Opponent-adjusted attack/defence ratings (not raw PF/PA)
- Late team news (injured key forwards worth 5–8 pts each)
- Venue-specific scoring adjustments (Marvel/Hobart are the big ones)
- Closing line as the benchmark (closing prices are more efficient than opening)
- Dynamic line movement tracking (sharp money on AFL totals = syndicate models)

### Resources identified for calibration data

- **aussportstipping.com/sports/afl/** — per-venue scoring averages, O/U records. Seed venue_profiles from here.
- **matterofstats.com** — MoSHBODS ratings and quantile regression methodology. Best public AFL analytics.
- **squiggle.com.au** — live OFFDEF ratings, can calibrate against.
- **aussportsbetting.com/data/historical-afl-results-and-odds-data/** — historical AFL O/U odds from 2013+. Use closing prices for backtesting.
- **afltables.com** — complete historical game scores from 1897.
- **betfair-datascientists.github.io/modelling/AFLmodellingPython/** — open-source AFL model in Python.
- **arxiv 2405.12588** — Bradley-Terry models for AFL (2024).
- **Manderson et al. (2018)** — Dynamic Bayesian / Skellam distribution model. Academic gold standard.

---

## Pending work from this session

- [ ] Implement multiplicative totals formula in AFL T1 code path (no NRL impact)
- [ ] Manually seed Marvel Stadium and Hobart/Launceston into `venue_profiles` using aussportstipping data
- [ ] Build iterative opponent-adjusted attack/defence ratings (longer project)
- [ ] Re-run R8–R9 accuracy tests after formula change to measure improvement
- [ ] Recalibrate home_advantage_points for AFL from data (currently 0.0 — needs evidence-based value, probably 4.0–6.0 once totals are fixed and more rounds accumulate)
- [ ] R13 Cronulla vs Manly: confirm venue, plug in refs Wednesday, T5 Thursday when teams drop

---

## NRL state — unchanged

NRL model untouched. R13 Cronulla vs Manly pricing complete for known tiers.
CLV for R12 still pending (opening/closing lines not yet filed).
