# 2026-08-14 — BetMate Racing: Pro Workbench + Race Digital Twin

## Product decision

If BetMate enters racing, do **not** build a tips page or a Punting Form clone.
Build a serious-punter workbench that supplies a transparent base model, then
lets users construct, test and audit their own view of each race.

The distinction matters:

- Recreational users can consume simple value cards and plain-English Baz
  explanations.
- Serious/pro users need a research and decision environment: their own prices,
  editable assumptions, a book builder, filters, historical tests and a full
  post-race learning loop.

Target pro subscription concept: roughly $100/month once the tool is genuinely
useful. It cannot be justified as merely a feed of selections.

## Data strategy and constraints

Punting Form is not an appropriate scraping dependency. Its terms prohibit
automated access without permission and its proprietary sectionals/benchmarks
are a data moat. Do not build a scraper that risks the account or cannot be
used commercially.

Punting Form publishes that it captures runner-level raw sectionals, wides,
early pace and track pars, then makes proprietary comparable benchmarks. Their
team includes offshore data experts. We cannot assume we can match this
nationwide quickly or redistribute any licensed raw data.

Start with authorised/official data and derived BetMate outputs:

- NSW Punter's Intelligence: runner tracking, sectionals, distance travelled,
  speed and position. Confirm an authorised bulk/export route before automating.
- Racing Queensland: publicly published meeting sectional CSV ZIPs. Confirm
  usage rights before production ingestion.
- Betfair: current market, liquidity, BSP and historical market data for
  calibration/CLV.

Build a performance-rating model, not a "sectional model". Sectionals are an
input that upgrades/downgrades a past-run rating when available. The rating
must still work in races/states without high-quality tracking.

## Core product: Race Digital Twin

Do not ship a single deterministic speed map where runners are manually dragged
into four buckets. That is current-generation form-guide software.

The next-generation concept is a probabilistic race-shape simulator:

```text
runner history + barrier + likely jockey tactics
+ pace/energy profile + track geometry + rail + going
+ scratches + market moves + weather
→ many plausible simulated race shapes
→ position/ground-loss/energy distributions by runner
→ scenario-specific and blended fair odds
```

It should show several coherent worlds, each with a probability (for example:
soft uncontested lead, contested early speed, wide runner crosses, chaotic first
400m), rather than pretending the system knows one exact map.

For each runner show:

- probability of leading, settling each position band, racing wide and being
  held up;
- expected pace, energy cost and ground loss;
- chance its preferred race shape occurs;
- fair price in each major scenario and blended fair price;
- price sensitivity: which user assumption actually creates the edge.

The pro user states a thesis rather than simply dragging a runner:

> "This jockey will take a sit from barrier 13."  
> "Horse 4 is materially faster early than its last two restrained runs show."  
> "Three-wide is less costly today given rail/track conditions."

The simulation reruns and reports what this thesis changes in probability and
fair odds. Users can save named books/scenarios (default, heavy track, late
market, carnival) and compare their book with BetMate and the market.

## Pro workbench requirements

1. **Transparent base book** — BetMate fair odds, performance ratings,
   confidence/data-quality grade, model reasons and market price/liquidity,
   all timestamped.
2. **Personal book builder** — the user enters their own horse, pace, bias,
   barrier, fitness and sectional adjustments; the whole field re-normalises to
   100% and reprices immediately.
3. **Scenario canvas** — distributions and top race-shape scenarios, not one
   static map.
4. **Counterfactual lab** — test pace, tactics, scratches, track bias and rail
   assumptions. Preserve the exact assumptions behind every saved book.
5. **Research/angle builder** — point-in-time filters and backtests with sample
   size, ROI, BSP/closing comparison, drawdown and calibration. Never permit
   future data leakage.
6. **Baz Pro** — an evidence-bound research assistant that queries current race
   data and the user's saved books/notes. It can suggest and run experiments but
   must show the sample and never fabricate a rating or backtest.
7. **Post-race truth audit** — compare predicted scenario and user assumptions
   to actual position/pace/outcome. Track BetMate price, user price, market
   close, BSP, CLV and outcome over time.

## Build order

### V1 — prove the base

- NSW/QLD-focused performance rating model.
- BetMate base book versus Betfair, with permanent historical snapshots.
- Data-quality exclusion rules; no forcing a rating from dubious data.
- Shadow price for a full season; assess calibration, log loss and closing-line
  performance before recommendations affect users.

### V2 — serious-user interaction

- Personal adjustments, saved books and a basic probabilistic pace model.
- Scenario comparison and post-race audit.
- Start with a limited set of variables that can be validated.

### V3 — Race Digital Twin

- Track-specific energy and ground-loss model.
- Monte Carlo scenario simulator.
- Track/rail/weather updates and simulation rerun on scratches.

### V4 — AI and rich tracking

- AI research copilot over structured, timestamped data.
- Video/GPS-assisted tactic and trip detection only when licensed data and
  sufficient labelled history exist.

## Commercial positioning

The value proposition for pros is:

> "BetMate gives you a transparent base model, lets you build your own book on
> top of it, and helps you test whether your race-reading insight is genuinely
> worth money."

Do not promise a black-box edge or sell unsubstantiated tips. The product is
decision support, research tooling, reproducibility and learning.

## References researched in this session

- Punting Form — sectionals: https://docs.puntingform.com.au/docs/sectional-data
- Punting Form — Modeller: https://puntingform.com.au/products/modeller
- Punting Form — worksheets: https://docs.puntingform.com.au/docs/worksheets-1
- Punting Form — speed maps: https://docs.puntingform.com.au/docs/speed-map
- Punting Form — company/data operation: https://puntingform.com.au/about-us
- Dan O'Sullivan, ratings introduction: https://www.betfair.com.au/hub/education/racing-strategy/introduction-to-horse-ratings/
- Racing NSW Punter's Intelligence: https://www.racingnsw.com.au/punters-intelligence/
- Racing Queensland sectionals: https://www.racingqueensland.com.au/industry/thoroughbred/thoroughbred-sectionals
- HKJC speed-map limitations: https://www.hkjc.com/english/formguide/formstudy_help.asp
- Generative multi-competitor race/counterfactual research: https://arxiv.org/abs/2310.01748
