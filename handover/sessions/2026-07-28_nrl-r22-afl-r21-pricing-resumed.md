# 2026-07-28 — NRL R22 + AFL R21 pricing, resumed after crash

## Context
The previous session crashed partway through this session's round pricing. No diary
had been written for it, so this session started by reconstructing what had already
happened from file timestamps and content rather than asking the user to re-explain —
per the CLAUDE.md instruction to read Current State, not ask "what were you working on."

## What had already been done (recovered from timestamps, ~08:14–08:45 today)
- NRL: backfilled a skipped Round 21 (fixture + results were never loaded into the DB —
  discovered mid-session) purely to keep ELO current. Not a priced round.
- NRL R22 fully priced and written up (`results/r22_pricing_2026.csv`,
  `outputs/results/r22_nrl_pricing_2026.md`) — this part was already complete when the
  crash happened.
- AFL R21 round-prep built fresh (fixture, injuries scrape, emotional scrape), pricing
  CSV generated (T1–T8 + ML shadow), T9 matrix confluence run. The crash happened before
  the AFL R21 writeup was produced — that was the missing piece.

## What this session did
1. Reconstructed the timeline via file mtimes and git status (no assumptions —
   cross-checked which files were touched today vs which were older).
2. Verified AFL T6 (emotional) values in the CSV against `data/afl/emotional/processed/
   latest-emotional.json` — confirmed a fresh scrape had run (7 flags, 7 teams) and traced
   `prepare_afl_round.py`'s loader path (`ROOT.parent/data/afl/emotional/...`, i.e. repo
   root not BettingEngine root — easy to get wrong).
3. Found a real data-quality regression: this round's AFL injuries file admits in its own
   metadata it wasn't hand-curated — every player defaults to position=utility,
   quality=average. Cross-checked against the R19 writeup's hand-tagged list and confirmed
   Port Adelaide (Butters, Rozee) and GWS (Green, Kelly, Hogan) — all elite/season-ending
   last round — are now pricing as if their injuries barely matter (T5 = 0.0 for Port
   Adelaide this round vs -8.0 in R19 for a similar list).
4. Found a second gap: the emotional scraper introduced a `losing_streak` flag_type for
   Gold Coast that isn't in `AFL_T6_CONFIG`'s supported list (milestone/new_coach/
   star_return/shame_blowout/farewell/personal_tragedy/rivalry_derby/must_win/club_drama)
   — it silently produced zero adjustment. Not fixed this session, flagged for next AFL
   touch.
5. Read `scripts/matrix_confluence.py`'s `normalise_direction()` to correctly interpret
   the T9 JSON bucket keys (`h2h_HOME_WIN` etc. are already the normalised ground truth —
   don't try to re-derive direction from individual row labels, that's a trap that led to
   a wrong first read of the Hawthorn/Nth Melbourne and Port Adelaide/GWS games).
6. Wrote `outputs/results/r21_afl_pricing_2026.md` in the same house format as prior AFL
   writeups (R19 was the template) — tier coverage table, prices at a glance, tier
   breakdown, ML shadow + model-alignment check, T9 confluence summary, injury/emotional
   notes, can't-price section.
7. Updated both `CLAUDE.md` Current State sections (root + BettingEngine) and this diary.

## Key findings worth carrying forward
- **AFL R21 model-alignment no-plays (3 of 9):** Collingwood/Geelong, St Kilda/Sydney,
  Richmond/West Coast — rules and ML margin models pick different winners.
- **Port Adelaide vs GWS flagged as a T9-vs-both-models conflict** — every matrix category
  (H2H, handicap, totals) backs Port Adelaide at home; both rules and ML have GWS winning.
  Same shape as the R19 Power/Dockers conflict. No clean read without market data.
- **AFL T5 needs a manual re-tag** on Port Adelaide, GWS, and ideally Richmond before any
  T5-driven price from this round is trusted for betting.
- **Odds API is still down** — 25 days past the Jul 3 outage, 2 weeks past the user's own
  ~Jul 14 expected renewal. Worth the user actively checking rather than assuming it'll
  sort itself out.

## Not done / left for next session
- T6 `losing_streak` flag_type fix in `pricing/afl_tier6_emotional.py` / `AFL_T6_CONFIG`.
- Manual T5 re-tag pass for Port Adelaide / GWS / Richmond.
- NRL T6 (referees) re-price once NRL posts R22 appointments Wednesday.
- Neither round's pricing was pushed to Supabase/betmate.au this session — site is still
  intentionally paused per the Odds API note above; do not push predictions until the
  user confirms renewal.
