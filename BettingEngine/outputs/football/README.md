# Football records — folder and file convention

One folder per competition, per season, per round. **Four artefacts per round.**
Nothing else goes in a round folder except `_supporting/`.

```
outputs/football/
├── COVERAGE.md                  auto-generated gap report — read this first
├── README.md                    this file
├── _reference/                  season-long, not weekly (confluence matrices etc.)
├── epl/2026-27/
│   ├── gw01/ … gw38/
│   │   ├── 1_model.{json,csv,md}        full-round 1X2 + O/U 2.5 prices   PRE-round
│   │   ├── 2_bets.{csv,md}              +EV vs market + matrix confluence PRE-round
│   │   ├── 2_bets_matrix.{json,md}      matrix working (optional)
│   │   ├── 3_review_model.{csv,md}      model vs market, CLV + ROI        POST-round
│   │   ├── 4_review_bets.{csv,md}       bets, CLV + ROI                   POST-round
│   │   └── _supporting/                 injury audits, raw working, superseded drafts
│   └── _season/                         ledgers and season rollups
├── championship/2026-27/gwNN/…          same shape
└── ucl/2026-27/mdNN/…                   same shape, `md` (matchday) instead of `gw`
```

## The four artefacts

| # | File | When | What |
|---|---|---|---|
| 1 | `1_model` | before the round | Model prices for **every match**: 1X2 and O/U 2.5 |
| 2 | `2_bets` | before the round | Selections clearing the EV rule, with matrix confluence and stake |
| 3 | `3_review_model` | after the round | Model vs market over the full round — CLV and ROI |
| 4 | `4_review_bets` | after the round | The bets — CLV and ROI |

## Rules

1. **Zero-padded round numbers** (`gw03`, not `gw3`) so folders sort correctly.
2. **The number prefix is the contract.** `football_records_coverage.py` matches on
   the `1_model` / `2_bets` / `3_review_model` / `4_review_bets` prefixes. Any
   suffix is fine (`3_review_model_ou25.csv`), the prefix is not optional.
3. **A round with no qualifying bets is not a gap** — write `2_bets_none.md` saying
   why. That satisfies slot 2. Silence does not.
4. **Never delete a superseded draft.** Move it to `_supporting/` (see
   `championship/2026-27/gw05/_supporting/bets_pre_injury.*`).
5. **Round numbers come from the results feed, not from memory.** The coverage
   script derives them by chunking played matches into full rounds, so a round
   appears the moment football-data publishes it.

## Weekly workflow

```bash
# before the round        -> 1_model, 2_bets
# after the round         -> 3_review_model, 4_review_bets
python3 scripts/model_vs_market_football_round.py     # slot 3
python3 scripts/score_football_saved_bets.py          # slot 4
python3 scripts/football_records_coverage.py          # verify, exits 1 on any gap
```

`football_records_coverage.py` exits non-zero when anything is missing, so it can
gate a weekly task rather than relying on someone noticing.

## Known gaps in 2026/27 (as at 2026-09-08)

Carried over from before this convention existed. Recorded rather than hidden:

- **EPL GW01–02, EFL GW01–03** predate the four-artefact rule; several slots were
  never produced.
- **EFL GW04** (1–2 Sep midweek) has **nothing** — the round was played but never
  priced, bet or reviewed.
- **EFL GW05** has no `1_model`: `scripts/price_efl_week4_2026.py` prints prices to
  stdout instead of writing a file. **Fix that script before GW06** or this gap
  repeats every week.
- **UCL** has no results feed wired, so no round calendar can be derived. MD1 work
  sits in `ucl/2026-27/md01/_supporting/`; the 2026-09-08 pricing attempt failed its
  model fit, so no `1_model` or `2_bets` exists.
