# RacingEngine

Internal-only horse-racing data and pricing engine for BetMate.

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

Current scope: NSW/Victoria metropolitan Saturday thoroughbreds only.

## Results and sectionals: canonical imports

`templates/results.csv` and `templates/sectionals.csv` are the only accepted
interchange formats for authoritative/manual data. They preserve the source
identifier and source URL on every imported record, so no unlicensed scraper
is needed or implied.

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

## Racing NSW authorised results

With Racing NSW approval, import the approved Season 1 NSW meetings and archive
their official result CSV plus sectional PDF:

```bash
python3 -m racing_engine.rnsw --date 2026-08-01
python3 -m racing_engine.rnsw --date 2026-08-08
```

The CSV importer loads official times, finishing position and beaten lengths.
The source sectional PDF is archived intact; marker-level PDF parsing remains a
separate verification step so no sectional value is inferred or guessed.

Create the isolated environment used for authorised sectional-PDF parsing with
`python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`.

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
