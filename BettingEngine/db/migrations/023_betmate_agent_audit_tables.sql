-- migration 023: BetMate/Baz automation audit tables
-- Stores BetMate import and preflight results so automated pricing can fail
-- loudly and Baz can inspect pipeline state without reading logs.

CREATE TABLE IF NOT EXISTS betmate_import_runs (
    import_run_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    season             INTEGER NOT NULL,
    round_number       INTEGER NOT NULL,
    source_round_dir   TEXT,
    stage_dir          TEXT,
    imported_at        TEXT,
    status             TEXT NOT NULL DEFAULT 'unknown',
    injuries_count     INTEGER NOT NULL DEFAULT 0,
    referees_count     INTEGER NOT NULL DEFAULT 0,
    emotional_count    INTEGER NOT NULL DEFAULT 0,
    manifest_json      TEXT NOT NULL,
    created_at         TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now'))
);

CREATE INDEX IF NOT EXISTS idx_betmate_import_runs_round
    ON betmate_import_runs (season, round_number, imported_at);

CREATE TABLE IF NOT EXISTS betmate_preflight_checks (
    preflight_check_id INTEGER PRIMARY KEY AUTOINCREMENT,
    season             INTEGER NOT NULL,
    round_number       INTEGER NOT NULL,
    run_date           TEXT NOT NULL,
    checked_at         TEXT NOT NULL,
    ok                 INTEGER NOT NULL,
    errors_json        TEXT NOT NULL,
    warnings_json      TEXT NOT NULL,
    details_json       TEXT NOT NULL,
    created_at         TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now'))
);

CREATE INDEX IF NOT EXISTS idx_betmate_preflight_checks_round
    ON betmate_preflight_checks (season, round_number, checked_at);

