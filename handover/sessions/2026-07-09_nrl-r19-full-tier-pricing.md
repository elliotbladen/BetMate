# 2026-07-09 — NRL R19 full-tier pricing (100% coverage + can't-price report)

User asked: "price up NRL, full tier 100%, make sure the model tells me if it can't
price anything up." Full writeup: `BettingEngine/outputs/results/r19_nrl_pricing_2026.md`
(leads with the can't-price table, per the request). CSV: `results/r19_pricing_2026.csv`.

## What the Jul 7 auto-run was missing (why the re-run)
- **Refs: all NaN** — appointments weren't on NRL.com Tuesday (or Wednesday, or Thursday —
  the scraper legitimately found 0/7 on three attempts; NRL.com match centre never
  published them). Hand-sourced all 7 from ESPN's round preview, corroborated
  Sutton/Gee on a second source, wrote `latest-referees.csv` + round-19 archive copy.
  Sutton whistle_heavy is worth -3.1 hcap / -1.1 totals on Bulldogs/Raiders.
- **Emotional flags looked stale (Jun 25 file)** — investigated: the scraper is NOT
  broken. It ran Tue and again today, found 0 validated flags for R19, and by design
  doesn't overwrite the old file when empty. prepare_round's round-guard correctly
  rejected the R17 file either way.
- **BUT the scraper's zero was wrong** — user asked for a web double-check on T7, and
  it found the **Jai Arrow MND tribute game**: the R19 Souths v Knights Sunday game IS
  the NRL-wide "World's Biggest Birthday Party" / Stand With Jai fundraiser at Accor
  (Arrow's 31st birthday, world-record attempt, Wiggles halftime). The scraper's
  14-headline Google News window missed it. Applied manually as personal_tragedy/major
  (+2.25 Souths) and re-priced: **Souths -3.3 → -5.5** (fair 1.48/3.09, 28.1–22.6).
  Verified no other missed flags: R18 max margin 22 (no shame_blowout), no coach
  changes this week, no milestones found. **Fix before R20: widen the emotional
  scraper's news window / add club-site + NRL.com news sources.**
- T9 confluence JSON was from the old run — regenerated after re-pricing.

## Pipeline result (all steps clean)
67 injury records (12 "errors" = bye-team players, correct), 7/7 refs, 7/7 weather
(all clear, 0 adj), T10 dormant (G3 camp ended Jul 9, R19 starts Jul 10), matrices
regenerated + pushed to Supabase with confluence.

## Headline model numbers
Warriors -12.4 @ Tigers (aligned with the round's strongest matrix stack: 7-way H2H
+ 5-way hcap) | Roosters -14.1 v Eels (matrices agree BUT 6 Roosters backed up from
Wed's Origin G3 — unmodeled fatigue, flagged as optimistic end) | Storm -14.2 v
Titans | Manly -9.2 v Cowboys (aligned) | Bulldogs/Raiders total 36.4 (Sutton
whistle_heavy + venue) | Dolphins/Sharks coin flip | **Rabbitohs/Knights: model
(Souths -3.3) vs matrices (Knights both markets) CONFLICT → no-play by house rules.**

## Explicitly unpriceable this round (the user's "tell me" list)
1. **Market EV** — Odds API down since Jul 3 (user-confirmed not locally fixable).
   The @105 prices are model prices, not market. No EV/CLV possible until it's back.
2. **NRL ML shadow** — `ml/predict.py` is still `NotImplementedError` (Phase 3 never
   built; AFL has ML, NRL doesn't). Model-alignment rule unverifiable → single-model
   signals only, size down.
3. **Origin G3 backup fatigue** — T10 covers camp absence only; G3 was Wed, round
   starts Fri. Roosters (6 players) and Dolphins (5) most exposed.
4. **Tyson Brough** — no historical ref bucket → neutral by default, not by data.
5. **Final team lists** — injuries are Jul 7 casualty ward; Luai (elite) doubtful is
   ±3 on Tigers/Warriors. Re-check Friday.

## Incidental finds (not fixed, note for later)
- Style-stats importer: `"St George Illawarra Dragons"` (no period) unknown-team skip —
  Dragons on bye so zero impact this round; add the alias before R20.
- `run_nrl_pricing.ps1` assumes CWD=BettingEngine (`config/settings.yaml` relative
  path) — fine under Task Scheduler, trips up manual runs from Apps root.
- prepare_round.py emits datetime.utcnow() deprecation warnings (Python 3.14) — cosmetic.

## Same-day parallel session
AFL R18 was re-priced in a parallel session (see its diary + CLAUDE.md) — that session
found and fixed the broken AFL ML shadow and confirmed the Odds API outage.
