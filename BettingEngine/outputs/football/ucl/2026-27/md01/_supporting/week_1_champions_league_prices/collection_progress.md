# Week 1 Champions League — player collection started

Built scripts/collect_ucl_player_history.py and ran it against free ESPN feeds. It reuses the existing EPL/EFL parse_match function unchanged. Raw downloads have source URLs, retrieval timestamps and SHA-256 hashes; repeat runs use the cache.

| Dataset | Matches | Player records |
|---|---:|---:|
| domestic_eng1_2026_pre_md1 | 11 | 440 |
| espn_2024_25 | 189 | 8223 |
| espn_2025_26 | 189 | 8245 |

Total: 16,908 player-match records. All 389 collected matches contain 11 starters per side; no failed match downloads or duplicate competition/match/player keys. This checks the retrieved data, not independent full-competition coverage.

## Week 1 team coverage

| Team | Collected matches | Recent domestic history collected |
|---|---:|---|
| AEK Athens | 0 | No |
| LASK | 0 | No |
| Club Brugge | 22 | No |
| Aston Villa | 15 | Yes |
| Borussia Dortmund | 24 | No |
| Villarreal | 8 | No |
| Porto | 0 | No |
| Manchester City | 23 | Yes |
| Lille | 10 | No |
| Real Betis | 0 | No |
| Real Madrid | 28 | No |
| Inter | 25 | No |
| Barcelona | 26 | No |
| Feyenoord | 12 | No |
| Stuttgart | 8 | No |
| Viking | 0 | No |
| Liverpool | 25 | Yes |
| Atlético de Madrid | 26 | No |
| Paris Saint-Germain | 34 | No |
| Slovan Bratislava | 8 | No |
| Sporting CP | 22 | No |
| Galatasaray | 12 | No |
| Napoli | 8 | No |
| Arsenal | 32 | Yes |

68 previously researched availability records are staged in data/ucl/player_layer/availability_staging.json. Player IDs, publication timestamps and expected-minute shares remain null pending validation. These are not loaded into the ready-status event file.

## Remaining before a shadow price-up

1. Collect domestic history for the other clubs and extend recent histories far enough for eight prior appearances. AEK, LASK, Porto, Real Betis and Viking have no team history in this initial collection. Historical player-ID matches after transfers also need a coverage audit.
2. Validate minutes, especially extra time, red cards and the inherited 65/25-minute substitution fallbacks. Missing stats are flagged because the inherited parser otherwise defaults them to zero.
3. Resolve availability identities/publication times and freeze projected/final lineups separately. Do not use eventual historical lineups as early-snapshot evidence.
4. Join UCL baseline predictions, build prior-match rolling features, run chronological residual evaluation and implement UCL inference. No model training, shadow prices or tier promotion occurred in this collection step.
5. Fill separate tier gaps: missing opponent strengths, non-English domestic form/rest coverage, pressing, referee/weather coefficients, market comparison and confluence. Player data alone does not activate them.

## Repeat collection

```bash
.venv/bin/python scripts/collect_ucl_player_history.py --from-date 2024-09-01 --to-date 2025-05-31 --output data/ucl/player_layer/espn_2024_25
.venv/bin/python scripts/collect_ucl_player_history.py --from-date 2025-09-01 --to-date 2026-05-31 --output data/ucl/player_layer/espn_2025_26
.venv/bin/python scripts/collect_ucl_player_history.py --league eng.1 --from-date 2026-08-01 --to-date 2026-09-07 --output data/ucl/player_layer/domestic_eng1_2026_pre_md1 --team-ids 359 382 364 362
```

Validation: two targeted unittest checks pass (leap-month bounds and absent-vs-zero statistics). All three datasets reproduced from cache.
