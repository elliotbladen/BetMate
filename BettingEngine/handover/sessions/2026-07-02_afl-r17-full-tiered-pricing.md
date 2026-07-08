# 2026-07-02 — AFL R17 Full Tiered Pricing

## Task
User wanted AFL R17 priced up properly end-to-end — all injuries, all emotional flags, full tier stack, not just a quick reprice.

## Pipeline run (in order)
1. `ml/afl/game_log.py --xlsx outputs/afl_weekly_review/historical/latest.xlsx` — ELO rebuild first, always before pricing.
2. `scrapers/afl_injuries.py --round 17` (main repo) — **failed, Footywire 503 on all 3 attempts.** Not our bug, site is down. Used existing 2026-06-30 curated file.
3. `scrapers/afl_emotional.py --round 17` (main repo) — needed `--with anthropic` on the uv invocation, not documented anywhere. Worked once added. Surfaced 4 flags, most importantly Jordan Dawson's bereavement absence for Adelaide.
4. Manually added Dawson to `outputs/afl_round_prep/r17_2026/injuries_r17_2026.json` (T5) since he wasn't in the injury file — his absence is a personal-reasons out, not something Footywire tracks, so cross-checking the emotional scrape against T5 caught a real gap in the injury data that a routine scrape re-run wouldn't have fixed on its own.
5. `scripts/prepare_afl_round.py --season 2026 --round 17` — full T1-T7 rules + ML shadow.
6. `scripts/_export_afl_prices.py --season 2026 --round 17` — DB → CSV export.
7. `scripts/afl_matrix_confluence.py --season 2026 --round 17` — T9 signals.
8. Pulled `data/odds_snapshots/2026/2026-07-02.csv` (main repo) and computed median market lines per game across ~10-12 bookmakers for a proper model-vs-market comparison rather than eyeballing single-book prices.
9. Wrote full analysis to `outputs/results/r17_afl_pricing_2026.md`.
10. Pushed fresh predictions to the site via `scripts/push_afl_predictions.py` (main repo) — verified live via the endpoint health-check baked into that script.

## Findings worth remembering

**The betting rule (rules+ML must agree on direction) did real work this round.** Power vs Kangaroos had the single strongest T9 matrix signal of the round (8-way H2H, two 100% historical splits) but rules and ML flatly disagree on who wins. Flagged as a hard avoid in the writeup. This is exactly the scenario the rule was built for — a compelling matrix stack that would look like the best bet of the round if you only looked at T9, but the two independent pricing models can't agree on winner.

**Extreme-ELO-gap undercook confirmed again** — Richmond/Carlton (ELO gap -286) and Essendon/St Kilda (ELO gap -273) both had rules and ML agreeing closely with each other (within 1pt) but sitting 9-12pts short of the market line. T2 hit its ±4.0 style-matchup cap on 5 of 9 games this round, which is a second, separate constraint from the ELO-scaling issue — worth reviewing independently. Neither issue is new (both are in the backlog) but this round is a clean, current data point for whoever picks up the sigmoid rescale work.

**Jordan Dawson gap is the interesting process finding.** Footywire tracks medical injuries; it will never catch a bereavement absence. The emotional-flags scraper (which pulls Google News + Claude synthesis) is actually the better source for these edge cases, but nothing currently cross-checks emotional flags against the injury list automatically to catch "this player is out but not listed in T5." Worth considering whether the emotional scraper should flag "player unavailable" cases back into the injury pipeline automatically rather than relying on someone reading both outputs side by side.

## Nothing broken, no destructive actions
No DB schema changes, no deletions. `outputs/afl_round_prep/r17_2026/injuries_r17_2026.json` was edited in place (one player added) — this file isn't tracked by any automated overwrite script for R17 specifically (R12-R16 don't even have this file, it's manually curated per round), so the edit is safe and will persist until someone re-curates the round from scratch.

## Next steps
- Re-run `scrapers/afl_injuries.py --round 17` if Footywire comes back before kickoff (first game is tonight, 2026-07-02).
- `data/pricing/afl/` (the `convert_pricing_files.py` structure) hasn't had a round added since R11 — flagged in the main-repo diary too. Not touched this session; it's evidently not part of the live workflow anymore, but worth a decision on whether to retire it or catch it up.
