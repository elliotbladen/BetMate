# Matchday 1 — the six remaining fixtures

Sydney Friday 11 September 2026 (European Thursday 10 September). These are the six
league-phase fixtures left after the twelve already covered in
[`../researched_prices.csv`](../researched_prices.csv) and
[`../player_shadow_final/`](../player_shadow_final/).

Everything for this slate lives in this folder — the board, the frozen predictions, the
inputs, the scripts and both runs.

| File | What it is |
|---|---|
| [`report.md`](report.md) | The price board: 1X2 and O/U 2.5, normal and shadow |
| [`prices.csv`](prices.csv) | Same board as data, with expected goals and coverage warnings |
| [`predictions.csv`](predictions.csv) | Frozen predictions with empty result columns, ready to settle |
| [`run/normal/prices.json`](run/normal/prices.json) | Full normal-mode audit: tiers, scenarios, hashes |
| [`run/shadow/prices.json`](run/shadow/prices.json) | Full shadow audit: per-player features, blockers, hashes |
| [`run/raw/`](run/raw/) | Every source response as retrieved |
| [`run/`](run/) | The four builders and the settlement script |

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

## Settling this next week

`predictions.csv` holds twelve rows — six fixtures × two modes — with the probabilities
frozen at the 10 September cutoff, the ESPN event id for each fixture, and empty
`home_goals` / `away_goals` / `settled_at_utc` columns. Blocked fixtures are kept as
rows with empty probabilities so next week's coverage is visible rather than implied.

Once the matches are played:

```bash
cd BettingEngine
D=outputs/football/ucl/2026-27/md01/_supporting/week_1_champions_league_prices/md1_remaining_normal_and_shadow
.venv/bin/python $D/run/settle.py --predictions $D/predictions.csv --output $D/settled
```

It pulls each final score from the same ESPN endpoint the fixtures came from, fills the
result columns, and scores 1X2 (RPS, Brier, log loss, hit rate) and O/U 2.5 (Brier, log
loss, hit rate, mean probability against actual rate) for each mode. Fixtures that are
not finished are left unsettled rather than scored on a partial scoreline.

Read the output with the sample size in front of you. Normal mode has three fixtures and
shadow has one, so the per-mode table is not a like-for-like comparison; `settle.py` also
reports a common-fixtures-only block, which for this slate means the single
Bayern–Bodø/Glimt match. One matchday cannot separate these two modes, and the O/U 2.5
calibration gap below is a season-scale finding, not something three matches will settle.

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
Over. Both tracks are published so the gap is visible, and `settle.py` scores both.
Neither is a betting price.

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
cd BettingEngine
D=outputs/football/ucl/2026-27/md01/_supporting/week_1_champions_league_prices/md1_remaining_normal_and_shadow
S=outputs/football/ucl/2026-27/md01/_supporting/2026-09-08_researched
.venv/bin/python $D/run/build_context.py
.venv/bin/python -m ml.football.ucl_price_league_phase \
  --context $D/run/context.json --aliases $S/aliases.json \
  --ratings $S/ratings_corrected.json --output NEW_DIR
.venv/bin/python $D/run/build_snapshot.py --context $D/run/context.json \
  --news $D/run/raw/uefa_team_news.html --history $D/run/player_history/audited_history.csv \
  --overrides $D/run/player_name_overrides.json --output $D/run/projected_snapshot.json
.venv/bin/python scripts/price_ucl_week1_player_shadow.py --output NEW_DIR \
  --snapshot $D/run/projected_snapshot.json --baseline $D/run/normal/prices.json \
  --history $D/run/player_history/audited_history.csv
.venv/bin/python $D/run/build_board.py --normal $D/run/normal/prices.json \
  --shadow $D/run/shadow/prices.json --output NEW_DIR
.venv/bin/python $D/run/build_predictions.py --normal $D/run/normal/prices.json \
  --shadow $D/run/shadow/prices.json --raw $D/run/raw --output NEW_DIR/predictions.csv
```

## A note on the history file

`run/player_history/audited_history.csv` is not committed: it is regenerated by
`ml.football.ucl_player_features.load_history` from the ESPN response cache and is
byte-identical (SHA-256 `ecb0137b…`) to the frozen copy under `run/shadow/inputs/`,
which is committed so the shadow run's recorded input hashes can still be checked.

## Sources

- [ESPN matchday-1 scoreboard](https://site.api.espn.com/apis/site/v2/sports/soccer/uefa.champions/scoreboard?dates=20260909-20260913) — fixtures and kick-off times
- [UEFA matchday-1 possible line-ups and team news](https://www.uefa.com/uefachampionsleague/news/02a9-2188cf675017-df8325ec95c3-1000--champions-league-predicted-line-ups-matchday-1-team-news-/) — archived 7 September copy
- [football-data.co.uk](https://www.football-data.co.uk/downloadm.php) — English, Italian, German, French, Dutch, Turkish and Norwegian league results
- [2026–27 Czech First League](https://en.wikipedia.org/wiki/2026%E2%80%9327_Czech_First_League) and [2026–27 Ukrainian Premier League](https://en.wikipedia.org/wiki/2026%E2%80%9327_Ukrainian_Premier_League) — reconciled against those articles' own league tables before use
- [TheSportsDB](https://www.thesportsdb.com/) — individual match dates for those two leagues
- ESPN squad rosters and match summaries — player identities, position groups and rolling history
