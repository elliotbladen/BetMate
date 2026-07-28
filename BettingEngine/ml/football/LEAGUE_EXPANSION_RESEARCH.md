# League Expansion Research — Championship + Champions League
**Researched:** 2026-07-09 (web) | **Status:** pre-build research, no code yet
**Context:** EPL engine is production-ready (see ARCHITECTURE.md). User wants Championship
and UCL engines next and is right that both need skewing — they break different core
assumptions of the EPL build.

---

## TL;DR — what breaks where

| EPL engine assumption | Championship | Champions League |
|---|---|---|
| Understat xG feeds Dixon-Coles | ❌ **No Understat coverage** — goals-fed D-C or FBref | ❌ No Understat; FBref has it but Cloudflare-blocked |
| Understat PPDA feeds T2 pressing | ❌ Unavailable — replace with shots-based proxy | ❌ Unavailable — use domestic PPDA as carry-in |
| One closed league, 20 stable teams | ⚠️ 24 teams, 6+ churn per season, parachute distortion | ❌ 36 teams from ~15 leagues, cross-league strength problem |
| 38 games/season per team to learn from | ✅ Better — 46 games | ❌ **Only 8 league-phase games** — cannot fit in-competition |
| ~2.8 goals/game, Over 2.5 ~55% | ❌ Lower scoring, **Over 2.5 sub-50%**, draws ~1 in 3 | ⚠️ League phase scores freely; **knockouts run below 2.8** |
| Single-league home advantage | ⚠️ Stronger (home wins near 50% in 24/25) | ⚠️ Varies wildly (travel, altitude, atmosphere); neutral final |
| No knockout logic needed | ⚠️ Playoffs only (4 teams, May) | ❌ Two-legged KOs, no away-goals rule (since 2021), ET+pens |

---

# 1. EFL Championship

## The league's character (research findings)
- **Draw-heavy, low-scoring:** draws land in almost 1 of 3 games; most matches finish 0–2
  goals; modal correct scores 1-1 / 1-0 / 0-0; Over 2.5 strike drops below 50%
  ([bettingexpert](https://www.bettingexpert.com/football/england/championship)). The D-C
  tau/draw correction and a league-specific totals calibration carry MORE weight here, not less.
- **Home advantage is stronger** — home teams won at nearly a 50% clip in 2024/25.
  Re-fit per-team HFA on E1 data; do not import EPL HFA constants.
- **Parachute payments are a structural distortion, not noise:** 40.5% of relegated clubs
  (2009/10–2022/23) bounce straight back; parachute clubs became **3× more likely to be
  promoted** than non-parachute clubs; average parachute-club revenue **£90m vs £27m**
  ([theesk analysis](https://theesk.org/2025/08/12/the-analysis-series-yo-yos-and-parachutes-premier-league-relegation-subsequent-performance-and-financial-impact-2010-2024/),
  [Wikipedia](https://en.wikipedia.org/wiki/Premier_League_parachute_and_solidarity_payments)).
  2024/25 sent all three promoted clubs straight back down for the second consecutive
  season — the EPL/Championship gap is widening, which makes the relegated-club prior
  even stronger.
- **Squad churn + managerial churn:** 6 new teams every season (3 down with parachutes,
  3 up from League One), heavy summer turnover, and sackings far more frequent than the
  EPL → a new-manager bounce flag earns its keep here.
- **46 games + midweek rounds:** fixture congestion is chronic — the T3 rest/fatigue
  multiplier fires far more often than in the EPL (where it's rare outside cup weeks).

## Data sources — the deciding constraint
- **football-data.co.uk E1** = same pipeline as the EPL engine: results, odds, shots,
  corners, cards, **referee** all present ([notes.txt](https://www.football-data.co.uk/notes.txt)).
  `fetch_results.py` needs ~a one-line league-code change. T6 referee and T7 set-piece
  survive as-is (recalibrated on E1 data).
- **xG: Understat does NOT cover the Championship** (EPL/La Liga/Bundesliga/Serie A/
  Ligue 1/RFPL only — [understat.com](https://understat.com/)). Options:
  1. **Goals-fed Dixon-Coles (recommended v1)** — classic D-C was designed for goals;
     46 games/season partially compensates for goals being noisier than xG. Lengthen the
     time-decay half-life to offset.
  2. FBref has Championship xG ([fbref.com](https://fbref.com/en/comps/10/Championship-Stats))
     but sits behind Cloudflare — scraping is fragile/expensive. Revisit if v1 underperforms.
- **PPDA (T2 pressing): unavailable.** Replace with a **shots-based tempo/suppression
  proxy** from E1 shots data (shots for/against vs league average), or drop T2 in v1 and
  measure the RPS cost.

## Skew list — Championship engine v1
1. Re-fit everything on E1 (2014/15→): base goals ≈2.4–2.5 (own constant), per-team HFA
   (higher), league-specific isotonic calibration for totals (**do not reuse EPL
   calibrator — its Over 2.5 base rate is a different distribution**).
2. Goals-fed D-C, longer decay half-life; draw modelling (tau) validated against the
   ~33% draw rate.
3. **New tier — season-reset prior (the Championship-specific edge):** at season start,
   seed the 6 new teams from **ClubElo** (free API, covers English tiers 1–5:
   [clubelo.com](http://clubelo.com/), `api.clubelo.com/YYYY-MM-DD`) + a **parachute
   flag** (year-1/2/3 payment status) as a strength prior. This is where the market may
   be beatable — August–October, before in-season data accumulates.
4. New-manager bounce flag (reuse T7-emotional pattern from NRL: flag + capped boost).
5. T3 fatigue: same multiplier, much higher firing rate — verify it doesn't overcook
   during Christmas congestion.
6. Betting note: softer market but higher margins than EPL — EV thresholds must clear
   the bigger vig; expect the edge in totals/AH, not 1X2.

**Effort estimate:** the smallest lift of the two. Same data pipeline, same model file,
league-parameterised. The real work is item 3 (promotion/relegation priors) and
re-backtesting (E1 walk-forward — target: beat the EPL engine's headline RPS is NOT
expected; Championship is inherently noisier. Set the benchmark from literature ~0.20+ RPS.)

---

# 2. UEFA Champions League

## Format reality (post-2024 Swiss model)
36 teams, single league table, **8 games each vs 8 different opponents (4H/4A) drawn by
seeding pots**. Top 8 → R16 directly; 9th–24th → two-legged playoff; 25th–36th out of
Europe entirely ([CBS explainer](https://www.cbssports.com/soccer/news/new-champions-league-format-explained-how-does-swiss-system-work-number-of-teams-league-phase/),
[football365](https://www.football365.com/news/how-does-the-new-champions-league-swiss-model-format-for-24-25-work)).
Knockouts: two legs, **away-goals rule abolished (2021)**, ET + pens. Final at neutral venue.

## What the research says matters
- **The core problem is cross-league strength.** A D-C fit needs a closed league; UCL
  teams share almost no common opponents domestically. Solution: **ClubElo as the T1
  backbone** — free API, daily ratings, all UEFA clubs on one scale, built exactly for
  cross-country comparison. Domestic xG form (we already have Understat for all big-5
  leagues) layers on top as the form/tier signal.
- **8 league-phase games = never fit in-competition.** The engine must price UCL games
  almost entirely from *imported* domestic state (ratings, form, PPDA, injuries) —
  the EPL engine inverted: cross-league Elo primary, D-C xG secondary.
- **Knockouts score below the ~2.8–3.0 average** — cautious first legs, low blocks away,
  and the away-goals abolition made first legs more balanced but not more open
  ([Breaking The Lines tactical betting guide](https://breakingthelines.com/opinion/champions-league-knockout-stage-the-tactical-betting-guide/),
  [ResearchGate KO goals data](https://www.researchgate.net/figure/Average-number-of-goals-per-match-in-the-knockout-phase-of-the-Champions-League_fig5_353281156)).
  → stage-dependent totals damper (league phase ≈ neutral, KO first leg strongest damper).
- **Rotation/fatigue is bidirectional:** KO rounds coincide with domestic run-ins;
  league-phase matchdays sit midweek between league games. Needs a congestion input
  fed from the domestic fixture list.
- **Motivation around the format's thresholds:** the Swiss table creates live incentives
  at top-8 (skip playoff) and top-24 (survival) — final matchdays need a
  motivation/scenario flag (the WorldCupEngine T7-motivation pattern maps directly).

## Skew list — UCL engine v1
1. **T1 = ClubElo cross-league rating** (blend weight flipped vs EPL: Elo-primary).
   D-C attack/defence shapes from domestic Understat xG, scaled by a league-strength
   coefficient (derivable from ClubElo league averages).
2. European HFA fit separately (bigger spread than domestic; neutral-venue final).
3. Stage-dependent totals adjustment: league phase / KO leg 1 / KO leg 2 / final.
4. **Reuse the WorldCupEngine knockout machinery** — two-leg tie aggregation, ET/pens
   advance probabilities, motivation and pressure tiers already exist from the WC build
   (`price_qf_*.py` pattern, `knockout_context.py`). This is the big head start.
5. Rotation flag: derived from domestic congestion + squad depth proxy.
6. Data: no Understat UCL and FBref is Cloudflare-blocked → **don't fight it**: price
   from domestic state + ClubElo, use UCL results only to update Elo (ClubElo does this
   for us). Odds for CLV: manual entry (OddsPortal), same house rule as AFL/NRL.

**Effort estimate:** medium — bigger conceptual change (cross-league layer) but heavy
reuse (WC knockout code + existing Understat/EPL fetchers for domestic form). Sample-size
honesty: ~125 UCL games/season merged across stages — expect 2+ seasons before any
edge claim is credible. Treat year 1 as paper-tracked CLV only.

---

# Build order recommendation
1. **Championship first** (August, aligns with EPL GW1 refresh — same pipeline, one new
   league config; the season-reset prior is the only genuinely new component).
2. **UCL league phase second** (starts ~mid-September — needs the ClubElo layer built).
3. UCL knockout module in December–January (reusing WC engine), before the February playoff round.

# Shared engineering implication
The EPL engine should be refactored **league-parameterised** before Championship work
starts: `league config = {data source, base xG/goals, HFA, decay, calibrator, tier
availability}`. One engine, N league configs — otherwise we fork three copies of
`price_match.py` and repeat the BetMate/BettingEngine divergence story inside the repo.
