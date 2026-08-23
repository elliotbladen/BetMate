# RacingEngine

Project status and the agreed build order are maintained in
[`docs/project_tracker.md`](docs/project_tracker.md). As audited on 20 August
2026, the data foundation and V0/V1 research baselines are built; class/Race
Strength, daily variant, weight/WFA, normalized pace/trip and production pricing
are not yet implemented.

The detailed, session-to-session rating plan is in
[`docs/ratings_build_plan.md`](docs/ratings_build_plan.md).

Approved internal **BetMate research project** for horse-racing data and
pricing. It is not a customer product, betting service or public data feed.

The first slice ingests Saturday metropolitan thoroughbred racecards from
FormFav into a raw archive and local SQLite database. It does **not** publish
FormFav data to the BetMate website.

## First import

Create the local key file from `BettingEngine/` first:

```bash
python3 scripts/set_formfav_key.py
```

Then import a card:

```bash
cd /Users/elliotbladen/BetMate/RacingEngine
python3 -m racing_engine.import_saturday --date 2026-08-15 --state NSW
python3 -m racing_engine.import_saturday --date 2026-08-15 --state VIC
```

The importer stores raw provider responses under `data/raw/formfav/` and a
canonical local database at `data/racing_engine.sqlite`.

Current scope: NSW/Victoria metropolitan Saturday thoroughbreds only. Racing
NSW and Racing Victoria have each provided approval for this non-commercial
research use; preserve source attribution and do not publish or redistribute
their raw data without a separate written commercial arrangement.

## Results and sectionals: canonical imports

`templates/results.csv` and `templates/sectionals.csv` are the canonical
interchange formats for authorised/manual data. They preserve the source
identifier and source URL on every imported record.

```bash
python3 -m racing_engine.results_import \
  --results templates/results.csv \
  --sectionals templates/sectionals.csv \
  --source authorised-manual-import
```

The season starts on 2026-08-01. Record all NSW/VIC Saturday results from that
date onward, including beaten lengths and official time. Sectionals are stored
per runner/marker when an authorised source supplies them.

Market odds and model fair prices remain separate layers. A price must be
labelled provisional until historical results have been imported and the model
has passed calibration testing.

## Racing NSW authorised results and sectionals

With Racing NSW approval, import the approved NSW meetings. The importer uses
the official sectional-PDF archive as its primary historical source, parses
official race/runner times plus reported sectional and in-run-position fields,
and retains the unmodified PDF locally:

```bash
python3 -m racing_engine.rnsw --date 2026-08-01
python3 -m racing_engine.rnsw --date 2026-08-08
```

The legacy RNSW CSV endpoint is used only as a current-meeting fallback. It is
not reliably retained for older meetings. Some official PDF archive dates are
unavailable; those gaps may be filled with the public Racing.com result record
under the separate source `racing-com-nsw-results-fallback`. Those rows contain
results only — never invented sectionals — so every rating input remains
auditable by source.

Create the isolated environment used for authorised sectional-PDF parsing with
`python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`.

## Racing Victoria authorised results and sectionals

With Racing Victoria's explicit non-commercial research approval, the importer
scrapes the same public Racing.com form-service payload used by its Victorian
form page, archives the unmodified JSON locally, and ingests verified result
and runner-split fields:

```bash
python3 -m racing_engine.racing_com --date 2026-08-01  # Flemington
python3 -m racing_engine.racing_com --date 2026-08-08  # Caulfield Heath
```

The importer currently supports the configured Saturday metro meetings only.
It records result position, margin, official race time, runner finish time,
800m/400m/finish split durations and the supplied 800m/400m positions.
`109` is Racing.com's non-runner code and is stored as scratched, never as a
finishing position. Raw JSON is retained under `data/raw/racing_com/` and must
remain local to the research project.

Inspect a historical Victorian backfill before downloading it:

```bash
python3 -m racing_engine.racing_com \
  --from-date 2025-08-16 --to-date 2026-08-15 --dry-run
```

The non-dry command ingests precisely that discovered list. Start in small,
reviewable batches; do not run a large backfill until the returned meetings
have been checked. NSW backfill remains a separate authorised schedule because
its official report URL requires the correct venue/code for each meeting.

`racing_engine.rnsw` discovers Randwick/Rosehill Saturday meetings and tries
both Rosehill archive identifiers (`ROSE` and legacy `RHIL`). It fails loudly
for an unavailable report rather than creating an empty meeting.

## Historical rating spine (internal only)

`racing_engine.performance` is the new V1 research pipeline. It persists:

- source-specific horse aliases (so name matching can be reviewed);
- track/distance/going time pars, calculated only from races before an
  explicit cutoff date;
- one auditable performance rating for each finished runner;
- a recency-weighted, uncertainty-aware current horse state.

Run it only after a verified result backfill:

```bash
python3 -m racing_engine.performance --as-of 2026-08-15
```

The current formula is deliberately modest: time versus a median
track/distance/going par, beaten lengths only where individual finish time is
unavailable, and a tightly capped last-400 relative split signal. Weight,
class, rail, distance-travelled and pace/trip adjustments are recorded as
pending rather than guessed. The default requires five historical races for a
par; use a smaller number only for pipeline testing, never for a price.

Evaluate it chronologically before trusting any number:

```bash
python3 -m racing_engine.evaluation --end-date 2026-08-15
```

For every race date, this rebuilds pars and horse states from strictly earlier
races, then records Brier score and log loss. It is a research diagnostic, not
a claim of profitability or a publishable fair-price model.

## Historic card and class enrichment

After result ingestion, enrich historical runner metadata from the public form
record without replacing the authoritative result/sectional raw source:

```bash
python3 -m racing_engine.enrich_history --state ALL
python3 -m racing_engine.classify_history --state ALL
```

This records barrier, carried weight, jockey, trainer, official handicap rating
and a categorical Group/Listed/BM/Class taxonomy. It deliberately does not
assign an arbitrary numerical value to a class; race-strength and class effects
must be estimated through no-look-ahead validation.

Historic race timestamps and nearest configured hourly weather-station records
are populated separately:

```bash
python3 -m racing_engine.weather_history
```

Each weather variable retains its source-quality tag. Use only observed
station values for a production feature; model-filled or missing precipitation
must remain low-confidence evidence rather than being presented as fact.

For cached NSW official reports, extract the explicit DT-W (distance travelled
versus winner) value when the report text supplies it:

```bash
python3 -m racing_engine.trip_history
```

Missing DT-W remains null. It must not be inferred from barrier or finishing
position alone.

## Official steward reports: evidence layer

The authorised public form record exposes the official steward report per race.
Import it separately from results and rebuild classifications whenever parser
rules change:

```bash
python3 -m racing_engine.steward_reports --state ALL
```

The importer archives the report text and source timestamp, then identifies a
small transparent set of events: slow starts, interference, held-up runs,
wide/no-cover passages, over-racing, gait issues and material veterinary
findings. The initial adjustment scale is conservative: minor wording is 0,
moderate trip evidence is at most +0.75 rating points, severe corroborated
interference is at most +1.50, and a single run can never exceed +2.0. Wide
passages receive no automatic lift until they can be checked against DT-W and
sectionals. Veterinary findings create a fitness/review flag, never a
forgiveness lift.

Those numbers are stored as *provisional research evidence only*. They do not
enter `performance-par-v1.0` until a chronological validation study shows an
improvement. Any severe incident or material veterinary outcome is queued for
human review.

## V0 shadow ratings and prices

After importing results, the first transparent rating pass is available:

```bash
python3 -m racing_engine.price_card --date 2026-08-15 --state NSW \
  --output data/outputs/nsw_2026-08-15_base_lengths_v0_1.json
```

`base-lengths-v0.1` uses prior official results and beaten lengths only. It
shrinks lightly raced horses to neutral, normalises a fair win book across the
field, and writes every rating/price snapshot to SQLite. It deliberately does
not claim to apply class, weight, barrier, track-par or sectional adjustments
until those data layers are present and validated.
