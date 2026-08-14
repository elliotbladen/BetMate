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
Market odds and model fair prices are deliberately separate future layers.
