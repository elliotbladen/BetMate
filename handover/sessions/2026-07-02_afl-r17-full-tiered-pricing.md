# 2026-07-02 — AFL R17 Full Tiered Pricing

## What happened

User asked for a full, properly done tiered AFL round price — "get all the injuries, get all the emotional tiers etc." Round 17 (9 games, Thu 2 Jul – Sun 5 Jul, no byes) was already priced from Jun 30 but stale by 2 days going into game day, so did a full re-price rather than trust the existing file.

## Steps taken

1. Tried to re-scrape Footywire injuries fresh (`scrapers/afl_injuries.py --round 17`) — got 503 Service Unavailable on all 3 retry attempts. Site is down, not our bug. Fell back to the 2026-06-30 curated `injuries_r17_2026.json`.
2. Ran the AFL emotional-flags scraper fresh (`scrapers/afl_emotional.py --round 17`) — needed `--with anthropic` since the base `uv run` didn't have it installed. Got 4 new flags, including a major one: **Jordan Dawson (Adelaide's captain, elite midfielder) is out following his brother's death.**
3. Cross-checked that against the injury file — **Dawson was missing entirely.** Added him manually to `BettingEngine/outputs/afl_round_prep/r17_2026/injuries_r17_2026.json` (Adelaide Crows, midfielder, elite). This is exactly the kind of gap that matters — Footywire wouldn't have this listed as a medical injury, it's a personal-reasons absence, and the emotional scraper's news search caught it but nothing wired it into T5 automatically.
4. Rebuilt AFL ELO from the latest historical xlsx (`ml/afl/game_log.py`) before pricing — 990 games in the deploy window, 135 in the 2026 season through R17.
5. Ran `scripts/prepare_afl_round.py --round 17` for the full T1–T7 rules stack + ML shadow. Exported via `scripts/_export_afl_prices.py`.
6. Ran `scripts/afl_matrix_confluence.py --round 17` for T9 signals across H2H/handicap/totals matrices.
7. Pulled today's odds snapshot (`data/odds_snapshots/2026/2026-07-02.csv`) and computed median market lines per bookmaker for every game, to compare fair prices against the market properly rather than eyeballing.
8. Wrote the full analysis to `BettingEngine/outputs/results/r17_afl_pricing_2026.md` — tier breakdown, ML divergence table, T9 matrix, injury/emotional/weather notes, per-game reads, and a signal summary that strictly applies the standing "rules and ML must agree on direction" betting rule.
9. Pushed fresh predictions to the site (`scripts/push_afl_predictions.py`) — confirmed live on Vercel via the endpoint health-check.

## What the pricing found

- **Adelaide's price moved materially** once Dawson was added — Eagles/Crows T5 handicap went from +6.0 (favouring Eagles) to -2.0 (favouring Crows), on top of an already-massive ELO gap (Eagles are last in the league, -436 ELO gap to Adelaide). This game also threw the round's strongest T9 matrix signal (6-way H2H, 5-way handicap, both backing Crows) and rules+ML agree on direction — best signal of the round alongside Hawthorn -14.5.
- **Only one game had rules and ML actually disagree on the winner: Port Adelaide vs North Melbourne.** Rules calls it a coin flip, ML favours the Kangaroos, but the market has Power as big favourites and the matrix throws an 8-way H2H confluence (two 100% historical splits) backing Power. This is a clean test case for the betting rule — the matrix looks compelling but the model disagreement overrides it. Flagged as a hard avoid.
- **Confirmed (again) the known extreme-ELO-gap undercook** on Richmond/Carlton and Essendon/St Kilda — rules and ML agree closely with each other but both sit 9-12pts short of the market line. This isn't "value," it's the documented `POINTS_PER_ELO` linear-conversion limitation plus the T2 ±4.0 cap being hit. Treated as calibration caution, not a betting signal, and called that out explicitly in the writeup so it doesn't get mistaken for an edge.
- Moderate-conviction games this round were thinner than usual — only Eagles/Crows and Hawks/Demons cleared the bar. Several games that looked interesting on rules alone (Cats/Lions, Swans/Bulldogs) turned out to be efficiently priced once ML was checked — ML sat almost exactly on the market line in both cases.

## Gotchas hit

- `scrapers/afl_injuries.py` needs `beautifulsoup4` — the plain `uv run --with requests` invocation from CLAUDE.md's example is missing it; the round-prep orchestrator script has the right deps.
- `scrapers/afl_emotional.py` needs `anthropic` as an explicit `--with` dependency — not in any of the documented one-liners.
- The `data/pricing/afl/` structure (`convert_pricing_files.py`) hasn't had an AFL round added since R11 — it's not part of the active workflow anymore. Didn't try to force this round into it; the active pattern is `results/r{round}_afl_2026.csv` + `outputs/results/r{round}_afl_pricing_2026.md`, which is what CLAUDE.md's "Round Pricing — Current Files" table actually references.
- Footywire injury site returning 503 is worth watching — if it's still down next Tuesday's automated injury scrape task will also fail silently (returns 0 records, doesn't error the task). Nothing broken on our end but flag it if it recurs.

## Next steps

- Re-run the injury scraper before kickoff if Footywire comes back up — particularly for the Saturday/Sunday games where late outs could still land.
- No bets placed this session — this was pricing only, as requested.
