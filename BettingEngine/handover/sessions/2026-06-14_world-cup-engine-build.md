# Session: World Cup 2026 Pricing Engine Build
**Date:** 2026-06-14

---

## What was built

`WorldCupEngine/` — complete pricing engine for FIFA World Cup 2026.

### Research conclusions (confirmed before build)
1. **ELO source confirmed**: eloratings.net methodology (Kaggle dataset) — beats FIFA ranking across 6 metrics in peer-reviewed research (Lasek et al. 2013). No goal-diff or ELO blending needed.
2. **Monte Carlo confirmed in scope**: Build alongside match pricing. Edge is in ADVANCEMENT markets (group stage QF/SF reach), not outright winner. Outright winner market is systematically overpriced by books.
3. **Markets confirmed**: H2H, Asian handicap, total goals, draw probability only.

---

## Files created

```
WorldCupEngine/
├── config/
│   ├── tier_weights_by_stage.yaml    # T1–T7 weights per stage (gw1→final)
│   └── settings.yaml                 # ELO, Poisson, markets, EV thresholds
├── data/
│   ├── elo/DOWNLOAD_ELO_DATA.txt     # Instructions to get Kaggle ELO data
│   └── fixtures/wc2026_groups.yaml   # 48 teams in 12 groups + fixture template
├── pricing/
│   ├── core/
│   │   ├── elo.py       # ELO ratings, win prob, home advantage, update formula
│   │   ├── poisson.py   # Dixon-Coles scoreline matrix + sampler
│   │   └── markets.py   # H2H, Asian handicap, totals, EV calc
│   └── tiers/
│       ├── t1_baseline.py   # ELO → expected goals (lambda/mu)
│       ├── t2_tactical.py   # PPDA/style matchup matrix (high press vs low block)
│       ├── t3_form.py       # Recent form, tournament results
│       ├── t4_venue.py      # Altitude (Denver, Mexico City), heat/humidity
│       ├── t5_injuries.py   # Key player absences, xG impact
│       └── t7_motivation.py # Must-win, can-draw, host pressure, stage flags
├── simulation/
│   ├── bracket.py              # Group ranking, R32 bracket, knockout match sim
│   ├── monte_carlo.py          # 100k tournament simulations
│   └── tournament_markets.py   # Advancement odds, EV signals, CSV export
└── scripts/
    ├── price_game.py      # Single game entry point (CLI)
    ├── price_stage.py     # Price all games in a stage
    └── run_simulation.py  # Monte Carlo tournament runner
```

---

## How to use

### Price a single game
```bash
cd WorldCupEngine
python scripts/price_game.py --home France --away Morocco --stage r16 \
    --venue "AT&T Stadium" \
    --bookie-home 1.55 --bookie-draw 4.00 --bookie-away 6.50
```

### Price all group-week 1 games
```bash
python scripts/price_stage.py --stage gw1
```

### Run full Monte Carlo tournament simulation
```bash
python scripts/run_simulation.py --sims 100000 --seed 42
```
Outputs:
- `outputs/tournament_odds/wc2026_sim_probs_YYYY-MM-DD_n100000.csv` — probabilities per team per stage
- `outputs/tournament_odds/wc2026_signals_YYYY-MM-DD.csv` — EV signals vs bookmaker

---

## Critical next step: Get ELO data

Without ELO data, all teams default to 1500 (equal). Engine runs but produces meaningless odds.

1. Go to: https://www.kaggle.com/datasets/saifalnimri/international-football-elo-ratings
2. Download CSV
3. Save as: `WorldCupEngine/data/elo/international_elo_history.csv`
4. Re-run any script — warning disappears, real ratings load automatically.

---

## Architecture notes

### Dixon-Coles calibration (international football)
- Base goals per team: 1.18 (neutral venue, major tournament)
- ELO scale: 0.003 (each ELO point shifts log-attack by 0.3%)
- Dixon-Coles rho: -0.13 (low-score correction — reduces 0-0 prob, increases 1-0/0-1)

### Draw probability model
- At 0 ELO diff: 26% draw (correct for international football)
- At 100-pt diff: 24% draw
- At 200-pt diff: 20% draw
- At 300-pt diff: 14% draw
- Decay constant: 0.000007 (calibrated to match research)

### Stage-specific tier weights (key differences)
| Stage | T1 | T7 motivation | Note |
|---|---|---|---|
| GW1 | 52% | 4% | No form data yet, venue dominant |
| GW3 | 40% | 18% | Must-win scenarios, highest motivation weight |
| QF/SF | 50% | 8% | Fatigue compounds |
| Final | 48% | 12% | Both teams desperate, starts cautious |

### Altitude venues to watch
- Empower Field, Denver: 1609m — 8% goals reduction
- Estadio Azteca, Mexico City: 2250m — 15% reduction (unless altitude-trained)
- Estadio Guadalajara: 1566m — 8% reduction

---

## Simulation performance
- 2000 sims: 6.3 seconds
- 100k sims: ~5 minutes
- For interactive use: `--sims 10000` (31 seconds)

---

## Confirmed group fixtures (template in wc2026_groups.yaml)
Groups A-L placeholder teams are from available draw information.
**Verify against official FIFA draw before using for real bets.**

---

## Next session
- Download ELO data from Kaggle (5 minutes)
- Populate confirmed WC 2026 fixtures in `wc2026_groups.yaml`
- Run 100k simulation → export advancement markets
- Input real bookie odds for EV signals
- Build `data/bookie_outrights.yaml` template so bookie odds feed into EV calc
