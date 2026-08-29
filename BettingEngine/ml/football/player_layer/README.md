# Football player availability and line-up layer

This is shared by EPL and Championship. It supports the player-layer shadow
model without altering the live base model.

## Non-negotiable timing rule

Every update has both `event_time` (when the information became true/public) and
`recorded_at` (when we captured it), plus a source and URL. An **early** snapshot
may only use updates at or before its cutoff. A **final** snapshot is created
separately after official team sheets. Never edit a historical update: add the
new evidence as a new row.

## Weekly routine

1. Initialise once per league.
2. Add/update only meaningful absences, doubts, returns, rotation risks and likely
   starters. Use `official_club` or `official_league` wherever possible.
3. Freeze an early snapshot at the chosen early-price time.
4. Freeze a final snapshot after official XI confirmation.
5. Retain both snapshots for the later player-layer walk-forward test.

## Commands

```bash
python -m ml.football.player_layer.player_tracker init --league epl
python -m ml.football.player_layer.player_tracker init --league championship

# First-time squad load; use the supplied CSV shape as the template.
python -m ml.football.player_layer.player_tracker import-roster --league epl \
  --csv ml/football/player_layer/templates/roster.csv

python -m ml.football.player_layer.player_tracker update --league epl \
  --team Arsenal --player "Bukayo Saka" --position W --status doubtful \
  --start-probability 0.55 --expected-minutes 50 \
  --source-type official_club --source-url "https://www.arsenal.com/" \
  --note "Manager says late fitness test"

python -m ml.football.player_layer.player_tracker snapshot --league epl \
  --home Arsenal --away Chelsea --kickoff-at 2026-08-22T19:00:00+01:00 \
  --cutoff-at 2026-08-21T17:00:00+01:00 --stage early

python -m ml.football.player_layer.player_tracker snapshot --league epl \
  --home Arsenal --away Chelsea --kickoff-at 2026-08-22T19:00:00+01:00 \
  --cutoff-at 2026-08-22T18:05:00+01:00 --stage final \
  --confirmed-home "Bukayo Saka,Martin Odegaard" \
  --confirmed-away "Cole Palmer,Moises Caicedo"

# After the match, record observed starts/minutes to score the two shadow inputs.
python -m ml.football.player_layer.player_tracker record-appearance --league epl \
  --home Arsenal --away Chelsea --kickoff-at 2026-08-22T19:00:00+01:00 \
  --team Arsenal --player "Bukayo Saka" --position W --started --minutes-played 84
```

`start_probability` and `expected_minutes` are intentionally separate. A player
can have a 100% chance of starting but only 65 expected minutes after returning
from injury. Initial confidence bands are a manual operational judgment; the
future PyTorch layer learns player impact, not whether an unsupported rumour is
true.

## What this deliberately does not do yet

- scrape websites automatically;
- claim an injury rumour is true;
- alter the established D-C/Elo price;
- train on final XI information while evaluating early prices.

We first collect clean, timestamped records. Then the same snapshots become the
training and walk-forward data for the player correction model.

See `PLAYER_LAYER_BUILD_SPEC.md` for the frozen two-model comparison and the
PyTorch architecture that will be trained once the historical data are ready.
