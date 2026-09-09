# Matchday 1 — the six remaining fixtures

Sydney Friday 11 September 2026 (European Thursday 10 September). These are the six
league-phase fixtures left after the twelve already covered in
[`../researched_prices.csv`](../researched_prices.csv) and
[`../player_shadow_final/`](../player_shadow_final/).

- [Price board — 1X2 and O/U 2.5, normal and shadow](report.md)
- [Board CSV](prices.csv)
- Full audits, tier reasons, scenarios and hashes:
  [normal](../../2026-09-10_remaining/normal/prices.json) ·
  [shadow](../../2026-09-10_remaining/shadow/prices.json)
- Inputs, raw sources and the scripts that built them:
  [`../../2026-09-10_remaining/`](../../2026-09-10_remaining/)

## What was priced

| | Normal | Shadow |
|---|---:|---:|
| Priced | 3 of 6 | 1 of 6 |

Priced in normal mode: PSV–Shakhtar, Bayern–Bodø/Glimt, Slavia–Lens. Only
Bayern–Bodø/Glimt also has a player-shadow price.

Fenerbahçe, Como and Sabah have no Champions League archive history at all, so
Fenerbahçe–Roma, Como–Leipzig and Manchester United–Sabah are blocked on T1 in the
same way AEK–LASK, Lille–Betis and Stuttgart–Viking were on 9 September. A handful of
recent domestic results does not establish comparable cross-league strength and a
league-average fallback is not permitted.

The shadow needs eleven identified players a side with prior roster history. Shakhtar's
ESPN history stops in January 2025 and Slavia's in January 2026, because neither the
Ukrainian nor the Czech league is covered by any player feed available here — three
Shakhtar and five Slavia projected starters have no prior record at all, and two more
Shakhtar names could not be resolved against the current squad. Those are genuine data
blocks, not model failures.

## Read the three prices with their coverage warnings

Presence in the archive is not the same as coverage. Lens have six archive matches, the
most recent from September 2023; Slavia have fourteen and Bodø/Glimt twelve; Shakhtar's
most recent is 596 days old. The engine still returns a confident-looking single number
for each — Lens are given an expected 0.50 goals away at Slavia, Bayern an expected 4.07
at home — and those numbers rest on very little. The report prints the warning next to
each price; treat Slavia–Lens in particular as a diagnostic rather than a price.

## Totals

O/U 2.5 comes from the same score matrix as the 1X2 price, not from the separate
market-anchored challenger, which needs a live two-sided market that is not available.
The raw matrix probability is measurably 4.58 percentage points too high on Over across
378 held-out matches (Brier 0.24398, mean Over 70.45% against an actual 65.87%). The
archived isotonic calibration lowers Brier to 0.22964 but compresses everything toward
the middle: it prices these three very different fixtures at 1.61, 1.81 and 1.83 on
Over. Both tracks are published so the gap is visible. Neither is a betting price.

## Other limits

- The strength fit runs to 30 May 2026 and does not include Wednesday's twelve matchday-1
  results. No team playing tomorrow played in them.
- UEFA's possible line-ups and absence lists were last modified on 7 September and are
  three days old; uefa.com was unreachable for a fresher pull (HTTP/2 INTERNAL_ERROR and
  timeouts), so no matchday team news is included.
- No matchday-1 referee appointments were published in any source consulted, so T6 is
  unpopulated. T4 is neutral at matchday 1 and T5 does not apply in the league phase.
- Absences are priced from ESPN squad position groups mapped to the generic role in each
  group. A full-back absent from a "D" group is therefore priced with centre-back weights;
  the `form_rest_only` and `baseline` prices in the JSON show how far T2 moved each price.
- No market quotes, no EV, no confluence, no stakes, no bets.

## Reproduce

```bash
R=outputs/football/ucl/2026-27/md01/_supporting/2026-09-10_remaining
S=outputs/football/ucl/2026-27/md01/_supporting/2026-09-08_researched
.venv/bin/python $R/build_context.py
.venv/bin/python -m ml.football.ucl_price_league_phase \
  --context $R/context.json --aliases $S/aliases.json \
  --ratings $S/ratings_corrected.json --output NEW_DIR
.venv/bin/python $R/build_snapshot.py --context $R/context.json \
  --news $R/raw/uefa_team_news.html --history $R/player_history/audited_history.csv \
  --overrides $R/player_name_overrides.json --output $R/projected_snapshot.json
.venv/bin/python scripts/price_ucl_week1_player_shadow.py --output NEW_DIR \
  --snapshot $R/projected_snapshot.json --baseline $R/normal/prices.json \
  --history $R/player_history/audited_history.csv
.venv/bin/python $R/build_board.py --normal $R/normal/prices.json \
  --shadow $R/shadow/prices.json --output NEW_DIR
```

## Sources

- [ESPN matchday-1 scoreboard](https://site.api.espn.com/apis/site/v2/sports/soccer/uefa.champions/scoreboard?dates=20260909-20260913) — fixtures and kick-off times
- [UEFA matchday-1 possible line-ups and team news](https://www.uefa.com/uefachampionsleague/news/02a9-2188cf675017-df8325ec95c3-1000--champions-league-predicted-line-ups-matchday-1-team-news-/) — archived 7 September copy
- [football-data.co.uk](https://www.football-data.co.uk/downloadm.php) — English, Italian, German, French, Dutch, Turkish and Norwegian league results
- [2026–27 Czech First League](https://en.wikipedia.org/wiki/2026%E2%80%9327_Czech_First_League) and [2026–27 Ukrainian Premier League](https://en.wikipedia.org/wiki/2026%E2%80%9327_Ukrainian_Premier_League) — reconciled against those articles' own league tables before use
- [TheSportsDB](https://www.thesportsdb.com/) — individual match dates for those two leagues
- ESPN squad rosters and match summaries — player identities, position groups and rolling history

## A note on the history file

`../../2026-09-10_remaining/player_history/audited_history.csv` is not committed: it is
regenerated by `ml.football.ucl_player_features.load_history` from the ESPN response
cache and is byte-identical (SHA-256 `ecb0137b…`) to the frozen copy under
`../../2026-09-10_remaining/shadow/inputs/`, which is committed so the shadow run's
recorded input hashes can still be checked.
