# 2026-07-10 — Season Phase Tagging (evidence base for 2027 phase-weighted pricing)

## Context
User decided to split next NRL season into 4 phases (early / Origin / late / finals) and
weight-adjust the model per phase. Agreed approach before any weights are fitted:

1. **Event-anchor the phases, don't use fixed round numbers.** Origin dates drift year to
   year and the effect bleeds past the window — R19 2026 was the proof (G3 played Wed Jul 8,
   backup fatigue landed Jul 10–12, outside the naive R12–18 "Origin block").
2. **One mechanism per phase, not per-tier weight sets.** 4 phases × 10 tiers on ~200
   games/season = curve-fitting. Early = uncertainty (already handled by pfpa shrink; stake
   down rather than reprice). Origin = T10 absence + 0.34× backup fatigue. Late = ladder
   context (resting/tanking — NO current tier sees this; it's the one genuinely new build).
   Finals = hard-coded priors only (9 games/yr, never fittable).
3. **Measure before fitting.** Tag 2026 rounds with phase now, review per-phase model
   bias/CLV at end of season, fit only to measured bias on pooled multi-season data with
   walk-forward validation.

This session built step 3's instrumentation.

## What was built
- **`scripts/season_phases.py`** (new):
  - `origin_windows(season)` — [camp_start, game_date + 7d] per Origin game from
    `{BETMATE_ROOT}/data/nrl/origin/{season}.json`. The +7d is the backup-fatigue round.
  - `nrl_phase(...)` — early (before first camp) / origin (inside the Origin era, with
    `origin_window` bool = round actually overlaps a camp/backup window vs merely
    Origin-era) / late (after last window) / finals (round > 27).
  - `afl_phase(...)` — DESCRIPTIVE only (early ≤8 / mid ≤16 / late ≤23 / finals ≥24);
    AFL has no event anchor, don't fit weights to these without a mechanism.
  - `phase_for_round(sport, season, round)` — the API the reporting scripts call.
    NRL round dates come from `model.db` matches table.
  - CLI: `python scripts/season_phases.py --season 2026` prints the verification table.
- **`scripts/update_clv_running.py`** — now emits `phase` + `origin_window` columns in
  `NRL_CLV_running_2026.csv` / `AFL_CLV_running_2026.csv`.
- **`scripts/generate_model_accuracy.py`** — same columns in `MODEL_ACCURACY_RUNNING_2026.csv`.
- Both scripts fully regenerate their outputs, so the 2026 backfill happened by re-running
  them. All three CSVs verified tagged.

## 2026 NRL phase map (verified against reality)
R0–R11 early | R12 origin(G1 camp) | R13 origin(G1 backup) | R14 origin(clean) |
R15 origin(G2 camp) | R16 origin(G2 backup) | R17 origin(clean) | R18 origin(G3 camp) |
R19 origin(G3 backup)

## First read (SMALL SAMPLE — no conclusions, sample-size discipline applies)
NRL CLV: early phase +9.0% avg (23 bets, R8–11) vs origin phase +2.6% (32 bets, R12–15).
If that gap survives the rest of the season it's the first evidence the phase split has
teeth. AFL: early +2.3% (8 bets) / mid +1.4% (35 bets) — nothing yet.

## Also this session (earlier)
- R19 totals question resolved: refs are **T6** (already priced 7/7 into R19 totals);
  T10 = Origin. Post-Origin fatigue overlay computed but NOT applied — user confirmed
  R19 prices stand as-is. Fatigue would have moved 3 totals down ~0.2–0.6pt only
  (the 2.5pt threshold soaks most of the 0.34×-scaled points).
- Recommendation recorded for 2027 pre-season: rebuild T5 into a player-value
  availability tier (rates the named 17/22 vs full-strength baseline; absorbs T10,
  season-enders, returns-from-injury, doubtfuls, backup fatigue as states of one
  variable). Runner-up: sigmoid ELO→margin (already backlogged).

## FOLLOW-UP FINDING (same session) — the "Origin CLV collapse" is mostly an artifact
User set a target: get Origin-phase CLV back to 5-10%. Dug into it with
`scripts/clv_phase_report.py` (new, permanent — actual bets only, excludes the R8/R9
model-CLV supplement rows that inflated the running file's early number):

- **Actual bets:** early +3.76% (7 bets) vs origin +2.58% (32 bets) — much closer than
  the running file's +9.0%/+2.6% suggested.
- **Origin camp/backup window weeks were the BEST CLV of the season: +5.09% (13 bets,
  10/13 positive).** Clean Origin-era weeks: +2.62% (7 bets). The Origin edge already
  exists when betting into true camp/backup rounds — already at the bottom of the
  user's 5-10% target band.
- **The damage is one round: R13 (12 bets, ~-0.2% avg, G1 backup week).** Two candidate
  causes, both actionable: (1) backup fatigue was NOT modeled then (0.34× rule wasn't
  calibrated until Jul 7) — market moved toward fatigue-adjusted prices after we bet;
  (2) suspected early bet timing (the R13 post-mortem note said "betting too early
  before sharp money"). Can't test (2): **all 12 R13 bets are missing placed_date in
  the ledger** (bet_ids 2026-0046..0059, listed by the script). USER ACTION: fill
  placed_date/placed_time for those rows if recoverable from bookmaker history.
- All other Origin-phase bets with known timing were placed post-team-list; zero
  pre-teamlist Origin bets recorded, so timing discipline is already de facto policy.

**Path to 5-10% during Origin (2027):** (1) T10 post-Origin fatigue mode (0.34×) built
in so backup rounds are priced BEFORE betting — R13 was the cost of not having it;
(2) hard rule: no Origin-week bets before Tuesday team lists; (3) keep measuring with
clv_phase_report.py as rounds are filed.

## Next steps
- End of 2026 season: per-phase bias/CLV review off the tagged files → decide which
  phase mechanisms earn a weight in 2027.
- When building the 2027 phase logic: extend `tier10_origin.py` with the post-Origin
  fatigue mode (0.34×) so the R19 case prices automatically — already in backlog.
- Ladder-context (late-season resting/tanking) adjustment is the one new build the
  phase plan actually requires. Needs ladder position + games-remaining context per round.
- `generate_model_accuracy.py` SOURCES list still only covers NRL R9–11 / AFL R8–9 —
  add newer ml_comparison files as closing lines get filed (existing known workflow).
