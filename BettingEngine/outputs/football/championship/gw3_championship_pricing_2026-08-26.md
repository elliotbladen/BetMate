# EFL Championship GW3 Pricing — 2026-08-26

## Tier Coverage Audit

| Tier | Status | Notes |
|------|--------|-------|
| T1 Baseline (D-C + Elo) | REAL | 6,648 matches fitted, 2,205 calibration rows |
| T2 PPDA Pressing | REAL | Historical ppda_dated.csv — all 24 teams have data |
| T3 Form + Rest | REAL | Form from GW1/2 (2 games per team). All teams on short rest (3-4d) |
| T5 Injuries | MISSING | No injury data sourced — positions not specified |
| T6 Referees | MISSING | Referee appointments not sourced for GW3 |
| T7 Set-piece (corners) | REAL | Historical corner data for all established teams |
| T8 New-team prior | REAL | Fires for 6 teams: Wolves (+180), Burnley (+180), West Ham (+180), Bolton (-180), Cardiff (-180), Lincoln (-180) |
| T9 New manager | NOT CHECKED | Would need manual verification |

**Coverage: 5/9 tiers active (56%).** Below the 75% bar. Missing T5 injuries and T6 referees are the main gaps — both require manual input for Championship (no automated scraper). Price with caution.

## GW2 Results Review (model validation)

GW2 model picked the correct outright winner in **4/7 decided games** (57%). Market got **3/7** (43%).

Key result: **Model correctly backed West Brom over Burnley** (market had Burnley favourite). WBA won 3-1.

| Game | Result | Model Fav | Model | Mkt Fav | Mkt |
|------|--------|-----------|-------|---------|-----|
| Lincoln vs Portsmouth | 1-3 (A) | Lincoln | X | Lincoln | X |
| Birmingham vs Bristol City | 2-2 (D) | Birmingham | - | Birmingham | - |
| Millwall vs Norwich | 3-0 (H) | Millwall | OK | Millwall | OK |
| Wrexham vs Watford | 1-1 (D) | Wrexham | - | Wrexham | - |
| Preston vs Wolves | 1-3 (A) | Wolves | OK | Wolves | OK |
| Southampton vs Stoke | 3-1 (H) | Southampton | OK | Southampton | OK |
| QPR vs Bolton | 0-0 (D) | QPR | - | QPR | - |
| Blackburn vs Middlesbrough | 2-1 (H) | Middlesbrough | X | Middlesbrough | X |
| Swansea vs Sheffield United | 0-0 (D) | Swansea | - | Swansea | - |
| West Ham vs Charlton | 1-2 (A) | West Ham | X | West Ham | X |
| West Brom vs Burnley | 3-1 (H) | West Brom | OK | Burnley | X |

**Early-season pattern:** 5/12 games drew (42%). Relegated PL teams went 1W 2D 2L in GW2 — market is overvaluing them. West Ham lost at home to Charlton (again), Burnley lost 1-3 at WBA. Only Wolves won (3-1 at Preston).

---

## GW3 Prices — Friday 28 August

### Wrexham vs Birmingham (19:00 GMT)

| Market | Fair P | Fair Odds | Market | CLV |
|--------|--------|-----------|--------|-----|
| Home win | 0.526 | **1.90** | 2.39 | **+25.8% VALUE** |
| Draw | 0.261 | 3.84 | 3.27 | -14.8% |
| Away win | 0.214 | 4.68 | 2.85 | -39.1% |
| Over 2.5 | 0.476 | 2.10 | 1.97 | -6.2% |

**Context:** Wrexham strong D-C ratings (att 1.08, def 0.92, hfa 1.17). Form: Wrexham 2D (6pts from last 5), Birmingham 1W 2D (9pts). Both on 4d rest. T7 corners: Wrexham 5.7 won at home.

**Signal:** Model strongly backs Wrexham at home. Market has them as slight underdog (2.39) — that's a +25.8% edge. Birmingham's GW2 draw vs Bristol City and EFL Cup 1-6 to Brentford suggest they're still finding their feet. However, no T5/T6 data.

---

## GW3 Prices — Saturday 29 August

### Derby vs Swansea (12:30 GMT)

| Market | Fair P | Fair Odds | Market | CLV |
|--------|--------|-----------|--------|-----|
| Home win | 0.382 | 2.62 | 2.23 | -14.9% |
| Draw | 0.303 | 3.30 | 3.22 | -2.4% aligned |
| Away win | 0.315 | 3.17 | 3.13 | -1.3% aligned |

**Context:** Model sees this as dead even — Swansea slightly ahead despite being away. Derby poor form (4pts, 1L 1D inc 2-2 home draw vs Cardiff). Swansea excellent form (11pts from last 5). Both low-press teams (PPDA 14+). T3 form adjustment: Derby -0.056, Swansea +0.056.

**Signal:** No clear edge. Draw and away aligned with market.

### Middlesbrough vs West Brom (12:30 GMT)

| Market | Fair P | Fair Odds | Market | CLV |
|--------|--------|-----------|--------|-----|
| Home win | 0.457 | **2.19** | 1.70 | -22.4% |
| Draw | 0.296 | 3.38 | 3.75 | **+10.9% VALUE** |
| Away win | 0.248 | 4.04 | 4.62 | **+14.4% VALUE** |

**Context:** Both on 10pts from last 5 (excellent). WBA on 3d rest (fatigue penalty applied). Boro have monster corner stats (10.1 won at home → T7 boost +0.067 xG). Market has Boro heavily short (1.70), model says 2.19. WBA beat Burnley 3-1 last week showing they can travel.

**Signal:** Market overpricing Boro. Draw and WBA offer value if market odds are accurate. But WBA fatigue (Saturday → Saturday with likely midweek cup game) is real.

### Wolves vs Stoke (12:30 GMT)

| Market | Fair P | Fair Odds | Market | CLV |
|--------|--------|-----------|--------|-----|
| Home win | 0.510 | **1.96** | 1.48 | -24.5% |
| Draw | 0.278 | 3.60 | 4.45 | **+23.6% VALUE** |
| Away win | 0.212 | 4.71 | 6.13 | **+30.1% VALUE** |

**Context:** Wolves D-C ratings are reset (new to Championship). T8 prior gives +180 Elo boost (+0.036 xG). Won 3-1 at Preston GW2, drew 2-2 with Blackburn GW1. Stoke 0pts from 2 (lost both). Market backs Wolves very heavily at 1.48.

**CAUTION:** Model's D-C reset likely UNDERVALUES Wolves at this stage. The +180 T8 prior is modest given their PL squad. Market is probably closer to truth here. The model will converge as more results come in. **Do not bet against Wolves based purely on model price.**

### Blackburn vs QPR (15:00 GMT)

| Market | Fair P | Fair Odds | Market | CLV |
|--------|--------|-----------|--------|-----|
| Home win | 0.442 | 2.26 | 2.25 | -0.4% aligned |
| Draw | 0.297 | 3.37 | 3.30 | -2.1% aligned |
| Away win | 0.261 | 3.84 | 3.10 | -19.3% |

**Context:** Model and market very aligned on Blackburn home. Blackburn in good form (8pts, beat Boro 2-1 at home GW2). QPR mixed (beat Pompey 3-1 GW1, drew 0-0 vs Bolton GW2).

**Signal:** No value. Model and market agree.

### Bolton vs Lincoln (15:00 GMT)

| Market | Fair P | Fair Odds | Market | CLV |
|--------|--------|-----------|--------|-----|
| Home win | 0.446 | **2.24** | 2.43 | **+8.5% VALUE** |
| Draw | 0.292 | 3.42 | 3.25 | -5.0% |
| Away win | 0.262 | 3.82 | 2.80 | -26.7% |

**Context:** Both promoted from League One, both D-C ratings reset. T8 prior -180 Elo for both. Bolton won GW1 (2-1 vs Preston), Lincoln 0pts from 2 (lost both). Market has Lincoln surprisingly short (2.80 away) — model disagrees.

**Signal:** Mild value on Bolton home. Lincoln have lost every game and look out of their depth. Market may be overreacting to Lincoln's "brand" rather than results.

### Bristol City vs Portsmouth (15:00 GMT)

| Market | Fair P | Fair Odds | Market | CLV |
|--------|--------|-----------|--------|-----|
| Home win | 0.444 | 2.25 | 2.12 | -5.8% |
| Draw | 0.282 | 3.55 | 3.35 | -5.6% |
| Away win | 0.274 | 3.65 | 3.32 | -9.0% |

**Context:** Model and market broadly aligned — Bristol City slight home favourites. Pompey won 3-1 at Lincoln GW2 but lost 1-3 to QPR GW1. Bristol City lost 0-2 to Millwall GW1, drew 2-2 at Birmingham GW2.

**Signal:** No clear edge. Market slightly shorter than model across the board.

### Sheffield United vs Cardiff (15:00 GMT)

| Market | Fair P | Fair Odds | Market | CLV |
|--------|--------|-----------|--------|-----|
| Home win | 0.513 | **1.95** | 2.48 | **+27.2% VALUE** |
| Draw | 0.269 | 3.72 | 3.45 | -7.3% |
| Away win | 0.218 | 4.59 | 2.62 | -42.9% |

**Context:** Sheff Utd have the best defensive D-C rating in the division (1.20). Cardiff D-C reset (newly promoted). Model strongly backs home win.

**MARKET ODDS WARNING:** The scraped market odds may have home/away swapped. Cardiff at 2.62 away seems far too short against Sheffield United at home. If the real market has Sheff Utd at ~1.80-2.00 then model and market are aligned. Disregard CLV figures for this game until verified.

### Preston vs Charlton (15:00 GMT)

| Market | Fair P | Fair Odds | Market | CLV |
|--------|--------|-----------|--------|-----|
| Home win | 0.393 | **2.54** | 3.30 | **+29.9% VALUE** |
| Draw | 0.307 | 3.26 | 3.25 | -0.3% aligned |
| Away win | 0.301 | 3.33 | 2.18 | -34.5% |

**Context:** Charlton in stunning form — won GW1 at home, beat West Ham 2-1 AWAY in GW2. Market has them as strong away favourites (2.18). Model sees it as much closer (home 39% vs away 30%).

**Signal:** Model says Preston home is huge value at 3.30 if Charlton really are priced at 2.18 away. But Charlton's recent form is real — they look transformed. This is a genuine model-vs-market conflict. T7 set-piece shows Preston win 6.1 corners/game at home vs Charlton conceding 9.2 away — that's a big dead-ball advantage.

### Norwich vs Burnley (15:00 GMT)

| Market | Fair P | Fair Odds | Market | CLV |
|--------|--------|-----------|--------|-----|
| Home win | 0.428 | **2.34** | 2.45 | **+4.7% VALUE** |
| Draw | 0.267 | 3.75 | 2.90 | -22.7% |
| Away win | 0.305 | 3.28 | 3.60 | **+9.8% VALUE** |

**Context:** Norwich high press (PPDA 9.1). Burnley D-C reset, T8 +180 prior. Burnley on 3d rest (fatigue penalty 0.94x). Lost 1-3 at WBA GW2. Norwich poor early form (4pts) but strong D-C ratings (att 1.18).

**Signal:** Mild home value. Market's draw price (2.90) looks short relative to model (3.75). Market may be pricing this as more of a coin flip.

### Southampton vs Millwall (15:00 GMT)

| Market | Fair P | Fair Odds | Market | CLV |
|--------|--------|-----------|--------|-----|
| Home win | 0.452 | **2.21** | 1.55 | -29.9% |
| Draw | 0.276 | 3.63 | 4.00 | **+10.2% VALUE** |
| Away win | 0.272 | 3.68 | 5.50 | **+49.5% VALUE** |

**Context:** **BIGGEST MODEL-VS-MARKET GAP OF THE ROUND.** Market has Southampton at 1.55 (implied 64.5%), model at 2.21 (45.2%). Millwall are the best-performing team in the division — 13pts from last 5 (form leader), beat Norwich 3-0 away GW2, beat Bristol City 2-0 away GW1. Their defensive D-C rating (1.21) is second only to Sheff Utd's 1.20. Southampton beat Stoke 3-1 GW2 but their attack rating (1.56) is boosted by last season's form.

**Signal:** Model strongly disagrees with market. If these market odds are accurate, Draw and Millwall away are massive value. Millwall's away form (2W in 2, 5 goals scored, 0 conceded) is exceptional. However, Southampton's overall squad quality is higher — the model's D-C data leans heavily on last season where Millwall were a midtable defensive side. **This one depends on whether you trust early-season momentum (Millwall) or squad depth (Southampton).**

### West Ham vs Watford (15:00 GMT)

| Market | Fair P | Fair Odds | Market | CLV |
|--------|--------|-----------|--------|-----|
| Home win | 0.439 | **2.28** | 1.84 | -19.3% |
| Draw | 0.291 | 3.44 | 3.60 | **+4.7% VALUE** |
| Away win | 0.270 | 3.70 | 4.20 | **+13.5% VALUE** |

**Context:** West Ham D-C reset. T8 +180 prior. But their RESULTS don't match their reputation — 1pt from 2, lost at home to Charlton 1-2 GW2. Market still prices them as strong favourites (1.84). Model much more cautious (2.28). Watford have 4pts from 2 (1W 1D).

**Signal:** Market is pricing West Ham on their PL squad, model on their actual Championship results. West Ham's poor start (0W 1D 1L) plus conceding at home to Charlton suggests they haven't adjusted yet. Value on Draw/Watford if market really has West Ham this short.

---

## Summary Table

| Game | Model H/D/A | Market H/D/A | Value Signal |
|------|-------------|--------------|--------------|
| Wrexham vs Birmingham | 1.90/3.84/4.68 | 2.39/3.27/2.85 | **HOME +25.8%** |
| Derby vs Swansea | 2.62/3.30/3.17 | 2.23/3.22/3.13 | Aligned |
| Boro vs West Brom | 2.19/3.38/4.04 | 1.70/3.75/4.62 | Draw/Away value |
| Wolves vs Stoke | 1.96/3.60/4.71 | 1.48/4.45/6.13 | **CAUTION** — model undervalues Wolves (D-C reset) |
| Blackburn vs QPR | 2.26/3.37/3.84 | 2.25/3.30/3.10 | Aligned |
| Bolton vs Lincoln | 2.24/3.42/3.82 | 2.43/3.25/2.80 | Home +8.5% |
| Bristol City vs Portsmouth | 2.25/3.55/3.65 | 2.12/3.35/3.32 | Aligned |
| Sheff Utd vs Cardiff | 1.95/3.72/4.59 | 2.48/3.45/2.62 | **Market odds suspect** |
| Preston vs Charlton | 2.54/3.26/3.33 | 3.30/3.25/2.18 | **HOME +29.9%** (vs form) |
| Norwich vs Burnley | 2.34/3.75/3.28 | 2.45/2.90/3.60 | Mild home value |
| Southampton vs Millwall | 2.21/3.63/3.68 | 1.55/4.00/5.50 | **AWAY +49.5%** (biggest gap) |
| West Ham vs Watford | 2.28/3.44/3.70 | 1.84/3.60/4.20 | Draw/Away value |

## Key Themes

1. **Relegated PL teams still overpriced by market.** West Ham (1.84 mkt vs 2.28 model), Wolves (1.48 vs 1.96), Burnley reflected in Norwich game. GW2 showed 1W 2D 2L for these sides. Model's D-C reset is too aggressive the other way — truth is in between.

2. **Millwall are the story of the round.** 2W from 2 away, 5-0 goal record, best form in division. Market ignoring this at 5.50 vs Southampton. Model's +49.5% CLV on the away win is the biggest signal but carries high uncertainty.

3. **Charlton's form is real.** Beat West Ham away. Market prices them as away favourites at Preston. Model disagrees but acknowledges the form gap.

4. **Draw-heavy early season.** 5/12 draws in GW2 (42%). Market draw prices may be systematically too long in these early games as teams are still finding their feet.

## Missing Data / Caveats

- **Odds API deactivated** — market odds scraped from web search results. Confidence varies by game. Sheffield United vs Cardiff odds particularly suspect.
- **No T5 injury data** — no automated Championship injury scraper exists. Manual check recommended before any bets.
- **No T6 referee data** — referee appointments not sourced. Historical ref profiles exist in `data/championship/refs/`.
- **D-C reset for 6 new teams** — Wolves/West Ham/Burnley (relegated PL) and Bolton/Cardiff/Lincoln (promoted L1) all have generic 1.00/1.00/1.00 D-C ratings. Model will converge by GW6-8 as results accumulate. Until then, market is probably more accurate for these teams.
- **Over 2.5 goals** — isotonic calibrator has 2,205 rows but Championship goals-fed mode (no xG) means the calibration may be slightly looser than EPL.
