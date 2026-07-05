# 2026-05-30 - NRL Half-Time Pricing Edge

**Agent:** Codex
**Context:** Architecture concept for an NRL half-time/live pricing mechanism.

## Core Thesis

The half-time engine should not price the match from scratch and should not simply follow the scoreboard.

The edge is:

> What did the scoreboard make the market believe that the actual game did not support?

This is a scoreboard-versus-underlying-performance model. The pre-match model remains the anchor, but the half-time layer looks for market overreaction to the current score, current total, and simple public narratives.

## Primary Edge Types

### 1. Trailing But Winning T2

A team is down at half-time but winning the underlying game:

- run metres
- post-contact metres
- territory
- linebreaks
- field position
- completed sets
- possession quality

Market sees the team losing. The model sees variance, poor finishing, or short-term score distortion. This is the clean comeback or cover profile.

### 2. Leading But Losing T2

A team leads by roughly 6-10 but lost the underlying half:

- lost metres
- lost field position
- lost possession quality
- missed more tackles
- defended more repeat pressure

Points may have come from an intercept, kick error, sin-bin period, or one short-field try. Market may overprice the leader.

### 3. Fake Overs

Half-time total looks hot, but scoring quality was poor or unsustainable:

- tries from errors inside own 20
- intercept try
- unusually good goal kicking
- few linebreaks
- low run metres
- poor territory
- low repeat sets

Market lifts live total too much. Model looks under.

### 4. Hidden Overs

Half-time score is low, but the game is open:

- multiple linebreaks
- bombed tries
- held-up tries
- missed goal kicks
- high tackle breaks
- fast ruck
- repeat sets
- defensive fatigue building

Market sees low score. Model sees points left on the field.

### 5. Live Injury / Rotation Edge

Manual/watchlist edge where books may be slow on structural impact:

- hooker off
- halfback injured
- fullback limping
- middle rotation broken
- failed HIA
- edge defender replaced
- goal kicker off

### 6. Defensive Workload Edge

One team made 30-60 more tackles in the first half, defended repeat sets, had less possession, or has middle forwards on heavy minutes. Even if they lead, they may fade.

This belongs mostly to half-time T2/T3.

### 7. Ref Style Edge

Not referee bias. The live question is whether the referee profile changes game style:

- strict 10 metres
- fast ruck
- holding down punished
- high six-again count
- inside-10 penalties
- sin-bin risk

Some teams benefit from fast/clean games. Others benefit from a wrestle.

### 8. Weather Misread

Mostly a totals edge:

- wind behind one team first half
- rain intensifying
- surface getting worse
- humidity/fatigue

Market may extrapolate first-half scoring without adjusting second-half conditions.

### 9. Pre-Game Favourite Down Narrowly

Strong pre-game favourite down 1-6, T2 says they are equal or better, no major injury disadvantage, and market offers plus money.

Only clean if T2 confirms it. Do not bet only because the pre-game model liked them.

### 10. Weak Team Leading Early

Pre-game underdog leads, but needed perfect conversion, short fields, or opponent errors. Can create value on the stronger team if the live price overreacts.

### 11. Team-Specific T9 Patterns

T9 should be a filter, not a direct price adjustment. Look for repeated market mispricing by profile:

- good comeback teams
- bad front-running teams
- overs teams when trailing
- unders teams when leading
- teams that tire late
- teams that start slow but finish strong
- teams dependent on one player
- teams whose defence collapses after repeat sets

Rule:

- model edge + T9 confirms market has missed this profile before = stronger bet
- model edge + T9 says market usually prices this well = pass or reduce stake

Do not double-count T9 as both signal and price adjustment.

## Clean Edge Formula

For half-time, require at least two signals agreeing:

1. T2 says the scoreboard is wrong.
2. T3/T5/T6/T7 explains why it should correct or continue.
3. Market price gives enough gap.

Example long-side edge:

- team down 8
- +180 metres
- +2 linebreaks
- +8 completed sets
- opponent made 45 more tackles
- no injury disadvantage
- market gives +240 H2H

Example total edge:

- half-time score 10-8
- live total 42.5
- tries came from short fields
- low linebreaks
- slow ruck
- rain worsening
- fair total 36.5

## Avoid

- betting only because the pre-game model liked a team
- betting only because a team is "due"
- betting only because odds are bigger now
- betting over just because the first half was high scoring
- betting comeback teams without T2 support
- double-counting T9

## Architecture Direction

Keep this separate from the pre-match engine, but reuse pre-match outputs.

Suggested module layout:

```text
pricing/
  halftime/
    engine.py              # orchestrates half-time pricing
    state.py               # HT input object/schema
    performance.py         # first-half T2 dominance/deserved margin
    totals.py              # fake overs / hidden overs logic
    fatigue.py             # defensive workload / rotation pressure
    injuries.py            # live injury/role-impact flags
    referee.py             # live ref style interpretation
    weather.py             # second-half weather adjustment
    team_patterns.py       # T9 filters, not direct price adjustments
    market.py              # compare fair price vs live market
    explain.py             # human-readable edge report
```

Pricing flow:

```text
pre-match expected margin/total
        +
half-time score state
        +
first-half T2 performance score
        +
second-half correction/fatigue/injury/ref/weather modifiers
        ↓
projected final margin
projected final total
        ↓
H2H odds / handicap line / total line
        ↓
market edge + confidence + bet/no-bet
```

## Key Internal Metrics

### Scoreboard Distortion

```text
scoreboard_margin - deserved_half_margin
```

Example:

```text
Team down 8, but deserved half margin says +4
= scoreboard distortion of 12 points
= comeback/cover candidate
```

### Total Distortion

```text
actual_half_total - deserved_half_total
```

Use this to separate fake overs from hidden overs.

## Implementation Order

1. Define the half-time input schema.
   - match id
   - teams
   - home/away half-time score
   - pre-match expected margin/total
   - first-half team stats
   - live odds/lines
   - injury/weather/ref notes

2. Build the T2 half-time performance score.
   - run metres
   - post-contact metres
   - territory
   - linebreaks
   - completed sets
   - field position
   - repeat sets
   - errors and short fields where available

3. Build edge classifiers.
   - `trailing_but_winning_t2`
   - `leading_but_losing_t2`
   - `fake_over`
   - `hidden_over`
   - `fatigue_fade`
   - `pregame_favourite_down`
   - `weak_team_leading`

4. Convert to fair price.
   - projected final margin
   - projected final total
   - H2H odds
   - handicap line
   - total line
   - reuse existing pricing math where possible

5. Add T9 as a filter.
   - strengthens/weakens confidence
   - does not directly move price unless later proven by backtest

6. Produce a report.
   - bet/no bet
   - fair price
   - market price
   - edge percentage
   - signal agreement
   - invalidation risks

## Market Capacity Notes

Australia:

- in-play sports betting is generally restricted to phone/on-course rather than normal online click-to-bet
- soft books may show bad numbers but are fragile for limits
- fresh recreational account on NRL/AFL main live markets may get hundreds to low thousands
- sharp/restricted accounts can become near unusable

UK:

- online in-play is more available than Australia
- UK soft books can have bad prices but still restrict winners
- NRL/AFL limits are usually modest compared with EPL

Asian/Pinnacle-style:

- best scale
- sharpest prices
- require larger edge threshold

Exchanges:

- liquidity-based
- transparent available money
- NRL/AFL half-time markets may be thin except major games

Practical ranking for repeatability:

1. Asian/Pinnacle-style books: best scale, hardest prices.
2. Exchanges: liquidity-dependent, transparent.
3. UK soft books: easier online access, but winner limits.
4. Australian soft books: softer prices, worse in-play access and fragile limits.

## Next Step

Start by creating the half-time schema and a small deterministic `performance.py` scorer. Do not train a black-box model first. The first version should be auditable and produce useful reports even before full historical backtesting.

## Architecture Decision - Automated Ingestion From Day One

The user wants automation from day one. Stakes/limits are expected to be low, so the priority is fast learning and dataset creation rather than avoiding every early false positive.

BetMate should be the live cockpit and ingestion layer. Betting_model should remain the pricing brain.

```text
Live sources
  ↓
BetMate live collector
  ↓
normalised half-time snapshot
  ↓
Betting_model half-time pricing engine
  ↓
BetMate decision screen
  ↓
saved snapshot + model output + final result later
```

Important boundary:

- ingestion and display live in BetMate
- pricing/calibration/decision logic live in Betting_model
- bet placement remains manual by the user

V1 should automate:

1. fixture/match identification
2. live score polling
3. half-time detection
4. team match stats polling where available
5. live market odds/line capture where available
6. pre-match model baseline lookup
7. half-time snapshot save
8. pricing call to Betting_model
9. display of fair price, edge, and rationale
10. later final-score/result attachment for backtesting

Manual notes/overrides can still exist, but they are optional rather than required:

- injury
- rotation issue
- goal kicker off
- fake try
- bombed try
- ref style
- weather shift

V1 should not auto-place bets. The user will place bets manually.

Suggested automated snapshot payload:

```json
{
  "match_id": "NRL2026R12G4",
  "home_team": "Broncos",
  "away_team": "Storm",
  "period": "HT",
  "home_score": 8,
  "away_score": 14,
  "prematch_margin": 3.5,
  "prematch_total": 45.5,
  "live_home_odds": 2.45,
  "live_away_odds": 1.58,
  "live_home_line": 4.5,
  "live_total": 43.5,
  "home_stats": {
    "run_metres": 842,
    "post_contact_metres": 301,
    "line_breaks": 3,
    "territory": 57,
    "completion_rate": 82,
    "tackles_made": 142
  },
  "away_stats": {
    "run_metres": 690,
    "post_contact_metres": 240,
    "line_breaks": 1,
    "territory": 43,
    "completion_rate": 74,
    "tackles_made": 188
  }
}
```

Suggested pricing response:

```json
{
  "fair_home_odds": 2.05,
  "fair_away_odds": 1.95,
  "fair_home_line": 1.5,
  "fair_total": 39.5,
  "signals": [
    "trailing_but_winning_t2",
    "defensive_workload_edge"
  ],
  "recommendation": "home_h2h_or_home_line",
  "confidence": "medium"
}
```

Updated build order:

1. BetMate live NRL match poller.
2. Half-time snapshot schema.
3. Betting_model `pricing/halftime` engine.
4. BetMate half-time dashboard.
5. Snapshot/result storage for backtesting.
6. Automated signal review report.

## BetMate + Betting Engine Automation Architecture

Target split:

```text
BetMate = live data collection + dashboard
Betting Engine = pricing model + edge logic
User = manual bet placement
```

End-to-end flow:

```text
                    ┌────────────────────┐
                    │   Live NRL Match    │
                    └─────────┬──────────┘
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
          ▼                   ▼                   ▼
   Live score feed      Live team stats      Live odds / lines
   NRL / sports API     NRL match centre     Betfair / books /
                         or stats source     odds snapshot source
          │                   │                   │
          └──────────────┬────┴────┬──────────────┘
                         ▼         ▼
                  ┌────────────────────┐
                  │      BetMate        │
                  │ live collector      │
                  └─────────┬──────────┘
                            │
                            ▼
                  ┌────────────────────┐
                  │ Half-time snapshot │
                  │ score + stats +    │
                  │ market + baseline  │
                  └─────────┬──────────┘
                            │
                            ▼
                  ┌────────────────────┐
                  │  Betting Engine     │
                  │  HT pricing model   │
                  └─────────┬──────────┘
                            │
                            ▼
                  ┌────────────────────┐
                  │ BetMate dashboard   │
                  │ fair price / edge   │
                  │ signal explanation  │
                  └─────────┬──────────┘
                            │
                            ▼
                     User places bet manually
```

### Information Sources

BetMate should collect four groups of data.

#### 1. Pre-Match Baseline

Comes from Betting Engine before the game:

- pre-match expected margin
- pre-match expected total
- pre-match H2H probability
- pre-match handicap line
- team strength ratings
- injury/weather/ref assumptions

Possible local sources:

- Betting_model pricing output
- `results/nrl/*.csv`
- pricing runs table if/when wired

This is the half-time anchor. The live model should know what the pre-game model believed before kickoff.

#### 2. Live Score / Clock

Needed for automatic half-time detection:

- home score
- away score
- match status
- clock
- period
- half-time flag

Possible sources:

- NRL.com match centre / draw API
- sports data API
- score scraper
- manual fallback in BetMate

BetMate should poll this every 15-30 seconds during live games.

#### 3. Live Team Stats

This is the main edge source:

- run metres
- post-contact metres
- territory
- possession
- completion rate
- completed sets
- total sets
- linebreaks
- tackle breaks
- missed tackles
- tackles made
- tackles in opposition 20
- errors
- penalties
- six-agains / set restarts
- sin bins
- kick metres
- forced dropouts

Possible sources:

- NRL.com match centre stats
- NRL live stats endpoint if available
- Fox/Kayo-style match centre if scrapeable
- paid sports data feed later

This feeds the half-time T2 performance model.

#### 4. Live Market Prices

Needed to decide whether there is a bet:

- live H2H odds
- live handicap line
- live handicap price
- live total line
- live over price
- live under price
- exchange available liquidity where available

Possible sources:

- Betfair Exchange
- bookmaker odds API if available
- BetMate odds snapshot system
- manual fallback entry

For V1, one reliable market source is enough.

### System Responsibilities

BetMate responsibilities:

- poll live score
- poll live stats
- poll live odds
- detect half-time
- build normalised half-time snapshot
- call Betting Engine
- display output
- save every snapshot
- save every model recommendation
- attach final score later

Betting Engine responsibilities:

- load pre-match baseline
- calculate scoreboard distortion
- calculate T2 deserved half margin
- classify fake over / hidden over
- classify comeback / fade spots
- apply fatigue, injury, ref, weather adjustments
- convert to fair odds and fair lines
- return recommendation and explanation

### Example Half-Time Snapshot

```json
{
  "match_id": "NRL2026R12G4",
  "home_team": "Broncos",
  "away_team": "Storm",
  "period": "HT",
  "home_score": 8,
  "away_score": 14,
  "prematch_margin": 3.5,
  "prematch_total": 45.5,
  "live_home_odds": 2.45,
  "live_away_odds": 1.58,
  "live_home_line": 4.5,
  "live_total": 43.5,
  "home_stats": {
    "run_metres": 842,
    "post_contact_metres": 301,
    "territory": 57,
    "completion_rate": 82,
    "line_breaks": 3,
    "tackles_made": 142,
    "missed_tackles": 12,
    "errors": 4
  },
  "away_stats": {
    "run_metres": 690,
    "post_contact_metres": 240,
    "territory": 43,
    "completion_rate": 74,
    "line_breaks": 1,
    "tackles_made": 188,
    "missed_tackles": 21,
    "errors": 5
  }
}
```

### Example Betting Engine Response

```json
{
  "fair_home_odds": 2.05,
  "fair_away_odds": 1.95,
  "fair_home_line": 1.5,
  "fair_total": 39.5,
  "signals": [
    "trailing_but_winning_t2",
    "defensive_workload_edge"
  ],
  "recommendation": "home_h2h_or_home_line",
  "confidence": "medium",
  "explanation": "Home trails by 6 but is winning metres, territory and linebreaks. Away has made 46 more tackles. Market appears scoreboard-led."
}
```

### Automation Loop

1. BetMate sees scheduled NRL game is live.
2. BetMate starts polling score, stats and odds.
3. BetMate detects half-time.
4. BetMate freezes a half-time snapshot.
5. BetMate sends snapshot to Betting Engine.
6. Betting Engine prices H2H, line and total.
7. BetMate displays fair price, market price, edge, signal bucket, and bet/no-bet.
8. User manually places the bet if they agree.
9. BetMate saves the decision.
10. After full-time, BetMate attaches result for review/backtest.

### V1 Build Priority

1. Live score + half-time detection.
2. Live team stats.
3. Live odds.
4. Betting Engine half-time model.
5. BetMate dashboard.
6. Result tracking and review.

Missing data should not kill the system. If live stats fail, BetMate should still show score/odds. If odds fail, it should still store half-time stats. If a source breaks, the snapshot should record which fields were missing.

## Half-Time-Only Data Architecture

This is the cleaned-up working architecture. It excludes pre-game collection because the pre-game model and data flow already exist.

```text
BetMate = live data collection + half-time dashboard
Betting Engine = half-time pricing logic
User = manual bet placement
```

```text
Free live sources
    ↓
BetMate collectors
    ↓
normalised half-time snapshot
    ↓
Betting Engine half-time model
    ↓
BetMate edge dashboard
    ↓
User places bet manually
```

### 1. Live Score / Half-Time Detection

Primary source: NRL.com Match Centre.

Use for:

- home score
- away score
- match clock
- match status
- half-time trigger
- final result later

Backup sources:

- ABC NRL Score Centre: `https://www.abc.net.au/news/sport/score-centre/nrl`
- ESPN NRL Scoreboard: `https://www.espn.com/nrl/scoreboard`
- Flashscore NRL: `https://www.flashscore.com/rugby-league/australia/nrl/`

Flow:

```text
BetMate polls live score every 15-30 seconds
    ↓
detects status == half-time
    ↓
freezes score snapshot
```

### 2. Live Team Stats

Primary source: NRL.com Match Centre / official stats payload.

Use for the core T2 half-time edge:

- run metres
- post-contact metres
- territory
- possession
- completed sets
- total sets
- completion rate
- linebreaks
- tackle breaks
- missed tackles
- tackles made
- tackles inside opposition 20
- errors
- penalties
- set restarts / six-agains
- sin bins
- forced dropouts
- kick metres

Backup/technical reference:

- STATS Rugby League web-service structure, if accessible

Flow:

```text
BetMate polls match stats during first half
    ↓
at half-time, freezes home/away stats
    ↓
passes stats to Betting Engine
```

This is the most important data source. If live stats cannot be obtained reliably, the model loses most of its edge.

### 3. Event Flow / Score Quality

Primary source: NRL.com Match Centre commentary/event feed, if available.

Use for:

- tries from errors
- tries from penalties
- short-field tries
- intercept tries
- sin-bin period scoring
- held-up tries
- bombed tries
- field position before scoring
- scoring timing

Potential fields:

- scoring event
- game time
- team
- player
- score method
- home score
- away score
- commentary text
- previous possession/error/penalty event

Flow:

```text
BetMate collects first-half event flow
    ↓
classifies score quality
    ↓
flags fake over / hidden over / short-field scoring
```

This should be optional in V1. Team stats are more reliable; event-flow classification is a bonus.

### 4. Live Market Prices

Source: BetMate odds feed.

Use for:

- live H2H odds
- live handicap line
- handicap price
- live total line
- over price
- under price
- bookmaker/source
- timestamp

Free/public options:

- The Odds API free tier
- AusOdds public odds comparison
- Betfair Exchange API if available
- existing BetMate odds snapshot system

Flow:

```text
BetMate polls live odds
    ↓
at half-time, freezes best available market
    ↓
compares Betting Engine fair price to market
```

The Betting Engine can price the game without odds, but it cannot recommend a bet without market prices.

### 5. Weather

Primary source: Open-Meteo.

Use for:

- rain
- wind speed
- wind gusts
- temperature
- humidity
- weather change between first and second half
- worsening rain / wind
- heat or humidity fatigue

Backup:

- Bureau of Meteorology observations

Flow:

```text
venue coordinates
    ↓
Open-Meteo hourly forecast/current conditions
    ↓
BetMate stores half-time and second-half weather view
    ↓
Betting Engine flags weather total edge
```

### 6. Live Injury / Rotation Signals

No perfect free structured source.

Possible sources:

- NRL.com match commentary
- NRL.com interchange/event flow
- live player minutes if exposed
- visible HIA/interchange events
- manual BetMate note if watching

Use for:

- hooker off
- halfback/fullback injury
- failed HIA
- goal kicker off
- middle rotation broken
- edge defender replaced
- heavy minutes for middle forwards

Flow:

```text
event/interchange feed
    ↓
detect unusual injury/interchange pattern
    ↓
optional manual confirmation
    ↓
Betting Engine applies structural flag
```

This should be treated as a confidence modifier unless the signal is clear.

### 7. Final Result For Review

Sources:

- NRL.com Match Centre
- ABC / ESPN fallback
- AusSportsBetting later for official historical reconciliation

Use for:

- final score
- whether bet won/lost
- whether model signal worked
- backtesting
- calibration

Flow:

```text
after full-time
    ↓
BetMate attaches final score to half-time snapshot
    ↓
stores result for review
```

### V1 Source Priority

```text
1. NRL.com Match Centre
   score, status, live stats, event flow, final result

2. BetMate odds feed
   live H2H, line, total

3. Open-Meteo
   weather and second-half weather shift

4. ABC / ESPN / Flashscore
   score/status fallback

5. NRL commentary/interchange feed
   injury and rotation signals

6. AusSportsBetting
   later reconciliation and historical review
```

### Collector Layout In BetMate

```text
BetMate
  collectors/
    nrl_live_score_collector
    nrl_live_stats_collector
    nrl_event_flow_collector
    odds_collector
    weather_collector
    injury_rotation_collector
    result_collector

  normalisers/
    nrl_match_normaliser
    odds_normaliser
    weather_normaliser

  storage/
    halftime_snapshots
    halftime_model_outputs
    halftime_results

  dashboard/
    live_halftime_screen
```

### Half-Time Snapshot

```json
{
  "match_id": "NRL2026R12G4",
  "snapshot_time": "2026-06-01T10:05:00Z",
  "period": "HT",
  "home_team": "Broncos",
  "away_team": "Storm",
  "home_score": 8,
  "away_score": 14,
  "live_market": {
    "home_odds": 2.45,
    "away_odds": 1.58,
    "home_line": 4.5,
    "home_line_price": 1.91,
    "away_line_price": 1.91,
    "total_line": 43.5,
    "over_price": 1.90,
    "under_price": 1.90,
    "source": "betmate_odds"
  },
  "home_stats": {
    "run_metres": 842,
    "post_contact_metres": 301,
    "territory": 57,
    "possession": 55,
    "complete_sets": 18,
    "total_sets": 22,
    "line_breaks": 3,
    "tackle_breaks": 19,
    "tackles_made": 142,
    "missed_tackles": 12,
    "errors": 4,
    "penalties_conceded": 3,
    "set_restarts_conceded": 1,
    "sin_bins": 0
  },
  "away_stats": {
    "run_metres": 690,
    "post_contact_metres": 240,
    "territory": 43,
    "possession": 45,
    "complete_sets": 15,
    "total_sets": 21,
    "line_breaks": 1,
    "tackle_breaks": 10,
    "tackles_made": 188,
    "missed_tackles": 21,
    "errors": 5,
    "penalties_conceded": 5,
    "set_restarts_conceded": 2,
    "sin_bins": 0
  },
  "weather": {
    "rain_mm": 0.8,
    "wind_kmh": 26,
    "wind_gust_kmh": 39,
    "humidity": 78,
    "second_half_worsening": true
  },
  "event_flags": {
    "home_short_field_tries": 0,
    "away_short_field_tries": 1,
    "intercept_try": true,
    "sin_bin_scoring_period": false,
    "bombed_tries": 1,
    "held_up_tries": 1
  },
  "injury_rotation_flags": {
    "home_key_spine_issue": false,
    "away_key_spine_issue": false,
    "home_rotation_stress": false,
    "away_rotation_stress": true,
    "goal_kicker_issue": false
  }
}
```

### Betting Engine Response

```json
{
  "fair_home_odds": 2.05,
  "fair_away_odds": 1.95,
  "fair_home_line": 1.5,
  "fair_total": 39.5,
  "signals": [
    "trailing_but_winning_t2",
    "defensive_workload_edge"
  ],
  "recommendation": "home_h2h_or_home_line",
  "confidence": "medium",
  "explanation": "Home trails by 6 but is winning metres, territory and linebreaks. Away has made 46 more tackles. Market appears scoreboard-led."
}
```

### Automation Loop

1. BetMate sees an NRL game is live.
2. BetMate polls score, stats, event flow, odds, and weather.
3. BetMate detects half-time.
4. BetMate freezes one official half-time snapshot.
5. Snapshot is sent to Betting Engine.
6. Betting Engine prices H2H, line and total.
7. BetMate displays fair price, market price, edge and signal bucket.
8. User manually places the bet if they agree.
9. BetMate saves the model output and user decision.
10. After full-time, BetMate attaches result for review.

### Key Build Risk

The main risk is not odds, weather, score, or final result. BetMate can get those.

The real risk is whether live NRL team stats are consistently accessible for free at half-time. That is the first thing to test during a live game.

## Event Flow Source Research

Question investigated: does NRL.com have the event-flow / score-quality information needed for the half-time model?

Status:

```text
Structured NRL Match Centre play-by-play:
YES after/full-time.
LIKELY live via site/app payload, but not confirmed from static public HTML.

NRL.com live blog:
YES live, confirmed, and it contains the score-quality detail needed.

Backup:
Use NRL live blog + Match Centre + ABC/Flashscore score + Fox Match Centre.
```

### Confirmed Post-Game Structured Event Flow

Completed NRL/club Match Centre pages expose structured Play by Play data.

Example source:

- `https://www.rabbitohs.com.au/game/index?gameId=20251110530`

Observed fields/events:

- game time
- event type
- player
- team
- score on scoring events
- errors
- penalties
- set restarts
- linebreaks
- tries
- conversions
- interchanges
- video referee / no-try events
- sin-bin return events where applicable

Observed event labels include:

- `Error`
- `Penalty - Offside inside 10m`
- `Set Restart`
- `Linebreak`
- `Try`
- `Conversion-Made`
- `Interchange`
- `Video Referee - On Field Try - Video Referee No Try`

Conclusion:

Post-game structured event flow is definitely available and can be used for review, reconciliation, and calibration.

### Live Match Centre Status

A live/current Match Centre page was checked:

- `https://www.nrl.com/draw/nrl-premiership/2026/round-13/storm-v-roosters/`

The page had the Play by Play heading, but the static HTML did not expose live play-by-play events at that moment. This does not prove the live events are unavailable; they may be loaded client-side or through an underlying payload.

Conclusion:

```text
Live structured Match Centre event flow remains unconfirmed.
```

### Confirmed Free Live Backup - NRL.com Live Blog

NRL.com live blog was confirmed to contain live score-quality information.

Example source:

- `https://www.nrl.com/news/2026/05/30/knights-eels-launch-huge-saturday-triple/`

Observed live-blog details useful for the model:

- half-time stats, including completion rates
- held-up / bombed chances
- penalties and captain's challenges
- line busts leading to tries
- errors causing turnovers
- HIA exits and returns
- messy/fake try descriptions
- disallowed tries
- intercepts

Conclusion:

The NRL.com live blog is a valid free live backup for score-quality classification.

### Operational Decision

Build event-flow ingestion as a fallback stack:

```text
1. Try NRL Match Centre structured event payload.
   If live play-by-play is exposed, use it.

2. If not available, scrape NRL.com live blog.
   Use NLP/keyword extraction for score-quality flags:
   - intercept
   - error
   - charge-down
   - held up
   - no try
   - HIA
   - sin bin
   - short side / short field where described

3. If live blog missing, use team stats only.
   Still price T2 scoreboard distortion, but reduce confidence on fake/hidden score-quality flags.

4. Post-game, reconcile from NRL/club Match Centre Play by Play.
   Use this for audit and model learning.
```

### V1 Implication

Do not treat event flow as impossible or optional-only. Build a two-level system:

```text
structured event flow if available
otherwise live blog text extraction
otherwise stats-only fallback
```

The source risk is manageable because free live score-quality context exists through NRL.com live blogs, even if live structured Match Centre payloads need further testing.
