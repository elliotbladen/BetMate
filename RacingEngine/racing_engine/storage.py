"""Canonical local SQLite storage for raw FormFav Saturday-card imports."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS ingestion_runs (
    id INTEGER PRIMARY KEY,
    source TEXT NOT NULL,
    race_date TEXT NOT NULL,
    state TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    status TEXT NOT NULL,
    detail TEXT
);

CREATE TABLE IF NOT EXISTS meetings (
    source TEXT NOT NULL,
    race_date TEXT NOT NULL,
    state TEXT NOT NULL,
    track_slug TEXT NOT NULL,
    track_name TEXT NOT NULL,
    raw_json TEXT NOT NULL,
    imported_at TEXT NOT NULL,
    PRIMARY KEY (source, race_date, track_slug)
);

CREATE TABLE IF NOT EXISTS races (
    source TEXT NOT NULL,
    race_date TEXT NOT NULL,
    track_slug TEXT NOT NULL,
    race_number INTEGER NOT NULL,
    race_name TEXT,
    start_time TEXT,
    distance TEXT,
    condition TEXT,
    weather TEXT,
    race_class TEXT,
    prize_money TEXT,
    number_of_runners INTEGER,
    raw_json TEXT NOT NULL,
    imported_at TEXT NOT NULL,
    PRIMARY KEY (source, race_date, track_slug, race_number),
    FOREIGN KEY (source, race_date, track_slug)
      REFERENCES meetings(source, race_date, track_slug) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS runners (
    source TEXT NOT NULL,
    race_date TEXT NOT NULL,
    track_slug TEXT NOT NULL,
    race_number INTEGER NOT NULL,
    runner_number INTEGER NOT NULL,
    runner_name TEXT NOT NULL,
    jockey TEXT,
    trainer TEXT,
    barrier INTEGER,
    weight REAL,
    form TEXT,
    scratched INTEGER NOT NULL DEFAULT 0,
    raw_json TEXT NOT NULL,
    imported_at TEXT NOT NULL,
    PRIMARY KEY (source, race_date, track_slug, race_number, runner_number),
    FOREIGN KEY (source, race_date, track_slug, race_number)
      REFERENCES races(source, race_date, track_slug, race_number) ON DELETE CASCADE
);

-- Official results are kept separate from the declared card. A card changes
-- through scratchings; a result is an immutable record of what was run.
CREATE TABLE IF NOT EXISTS race_results (
    source TEXT NOT NULL,
    race_date TEXT NOT NULL,
    track_slug TEXT NOT NULL,
    race_number INTEGER NOT NULL,
    state TEXT NOT NULL,
    distance_metres INTEGER,
    race_class TEXT,
    race_class_code TEXT,
    scheduled_start_at TEXT,
    official_time_seconds REAL,
    track_condition TEXT,
    rail_position TEXT,
    source_url TEXT,
    raw_json TEXT NOT NULL,
    imported_at TEXT NOT NULL,
    PRIMARY KEY (source, race_date, track_slug, race_number)
);

CREATE TABLE IF NOT EXISTS runner_results (
    source TEXT NOT NULL,
    race_date TEXT NOT NULL,
    track_slug TEXT NOT NULL,
    race_number INTEGER NOT NULL,
    runner_number INTEGER NOT NULL,
    runner_name TEXT NOT NULL,
    finish_position INTEGER,
    beaten_lengths REAL,
    finish_time_seconds REAL,
    barrier INTEGER,
    weight_carried_kg REAL,
    jockey TEXT,
    trainer TEXT,
    official_handicap_rating REAL,
    result_status TEXT NOT NULL DEFAULT 'finished',
    raw_json TEXT NOT NULL,
    imported_at TEXT NOT NULL,
    PRIMARY KEY (source, race_date, track_slug, race_number, runner_number),
    FOREIGN KEY (source, race_date, track_slug, race_number)
      REFERENCES race_results(source, race_date, track_slug, race_number) ON DELETE CASCADE
);

-- One row per runner per observed marker. `section_seconds` is the time from
-- the preceding marker; marker_metres is distance remaining to the finish.
CREATE TABLE IF NOT EXISTS runner_sectionals (
    source TEXT NOT NULL,
    race_date TEXT NOT NULL,
    track_slug TEXT NOT NULL,
    race_number INTEGER NOT NULL,
    runner_number INTEGER NOT NULL,
    marker_metres INTEGER NOT NULL,
    section_seconds REAL,
    position_at_marker INTEGER,
    distance_travelled_metres REAL,
    speed_kmh REAL,
    source_url TEXT,
    raw_json TEXT NOT NULL,
    imported_at TEXT NOT NULL,
    PRIMARY KEY (source, race_date, track_slug, race_number, runner_number, marker_metres)
);

CREATE TABLE IF NOT EXISTS rating_snapshots (
    model_version TEXT NOT NULL,
    as_of_date TEXT NOT NULL,
    horse_key TEXT NOT NULL,
    horse_name TEXT NOT NULL,
    rating REAL NOT NULL,
    races_rated INTEGER NOT NULL,
    reliability REAL NOT NULL,
    detail_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (model_version, as_of_date, horse_key)
);

CREATE TABLE IF NOT EXISTS fair_prices (
    model_version TEXT NOT NULL,
    race_date TEXT NOT NULL,
    track_slug TEXT NOT NULL,
    race_number INTEGER NOT NULL,
    runner_number INTEGER NOT NULL,
    horse_name TEXT NOT NULL,
    win_probability REAL NOT NULL,
    fair_odds REAL NOT NULL,
    confidence REAL NOT NULL,
    detail_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (model_version, race_date, track_slug, race_number, runner_number)
);

-- A horse name is not a durable universal identifier.  Preserve every source
-- spelling and permit a reviewed alias before using it in modelling.
CREATE TABLE IF NOT EXISTS horse_aliases (
    source TEXT NOT NULL,
    source_horse_name TEXT NOT NULL,
    horse_key TEXT NOT NULL,
    canonical_name TEXT NOT NULL,
    review_status TEXT NOT NULL DEFAULT 'automatic',
    detail_json TEXT NOT NULL DEFAULT '{}',
    updated_at TEXT NOT NULL,
    PRIMARY KEY (source, source_horse_name)
);

CREATE TABLE IF NOT EXISTS track_pars (
    model_version TEXT NOT NULL,
    as_of_date TEXT NOT NULL,
    track_slug TEXT NOT NULL,
    distance_metres INTEGER NOT NULL,
    going_bucket TEXT NOT NULL,
    sample_size INTEGER NOT NULL,
    par_time_seconds REAL NOT NULL,
    method TEXT NOT NULL,
    detail_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (model_version, as_of_date, track_slug, distance_metres, going_bucket)
);

-- One auditable performance assessment for every finished runner.  This is
-- intentionally separate from the current horse state: a horse can improve
-- or regress while its prior run ratings remain immutable evidence.
CREATE TABLE IF NOT EXISTS run_performances (
    model_version TEXT NOT NULL,
    as_of_date TEXT NOT NULL,
    source TEXT NOT NULL,
    race_date TEXT NOT NULL,
    track_slug TEXT NOT NULL,
    race_number INTEGER NOT NULL,
    runner_number INTEGER NOT NULL,
    horse_key TEXT NOT NULL,
    horse_name TEXT NOT NULL,
    performance_rating REAL NOT NULL,
    time_component REAL,
    margin_component REAL,
    sectional_component REAL,
    pace_component REAL,
    confidence REAL NOT NULL,
    detail_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (model_version, as_of_date, source, race_date, track_slug, race_number, runner_number)
);

CREATE TABLE IF NOT EXISTS horse_rating_states (
    model_version TEXT NOT NULL,
    as_of_date TEXT NOT NULL,
    horse_key TEXT NOT NULL,
    horse_name TEXT NOT NULL,
    overall_rating REAL NOT NULL,
    peak_rating REAL,
    consistency REAL,
    rated_runs INTEGER NOT NULL,
    uncertainty REAL NOT NULL,
    detail_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (model_version, as_of_date, horse_key)
);

CREATE TABLE IF NOT EXISTS evaluation_runs (
    model_version TEXT NOT NULL,
    as_of_date TEXT NOT NULL,
    evaluation_name TEXT NOT NULL,
    races_scored INTEGER NOT NULL,
    runners_scored INTEGER NOT NULL,
    mean_brier REAL,
    mean_log_loss REAL,
    detail_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (model_version, as_of_date, evaluation_name)
);

-- Parsed, categorical race conditions.  Keep this separate from a numerical
-- class rating: the latter must be estimated and validated, not hard-coded.
CREATE TABLE IF NOT EXISTS race_classifications (
    source TEXT NOT NULL,
    race_date TEXT NOT NULL,
    track_slug TEXT NOT NULL,
    race_number INTEGER NOT NULL,
    race_type TEXT,
    class_family TEXT NOT NULL,
    group_grade INTEGER,
    benchmark INTEGER,
    class_number INTEGER,
    age_condition TEXT,
    sex_condition TEXT,
    raw_class_text TEXT NOT NULL,
    parser_version TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (source, race_date, track_slug, race_number)
);

CREATE TABLE IF NOT EXISTS race_weather (
    source TEXT NOT NULL,
    race_date TEXT NOT NULL,
    track_slug TEXT NOT NULL,
    race_number INTEGER NOT NULL,
    weather_source TEXT NOT NULL,
    station_id TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    temperature_c REAL,
    humidity_pct REAL,
    precipitation_mm REAL,
    wind_direction_deg REAL,
    wind_speed_kmh REAL,
    pressure_hpa REAL,
    quality_json TEXT NOT NULL,
    raw_json TEXT NOT NULL,
    imported_at TEXT NOT NULL,
    PRIMARY KEY (source, race_date, track_slug, race_number, weather_source)
);

CREATE INDEX IF NOT EXISTS idx_runner_results_history
  ON runner_results (race_date, runner_name, result_status);
CREATE INDEX IF NOT EXISTS idx_race_results_pars
  ON race_results (race_date, track_slug, state);
"""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class RacingStore:
    def __init__(self, database_path: Path) -> None:
        database_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(database_path)
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript(SCHEMA)
        self._migrate_schema()

    def _migrate_schema(self) -> None:
        """Add V2 columns for databases created before the historical layer."""
        columns = {row[1] for row in self.connection.execute("PRAGMA table_info(race_results)")}
        for name, definition in (("distance_metres", "INTEGER"), ("race_class", "TEXT"), ("race_class_code", "TEXT"), ("scheduled_start_at", "TEXT")):
            if name not in columns:
                self.connection.execute(f"ALTER TABLE race_results ADD COLUMN {name} {definition}")
        runner_columns = {row[1] for row in self.connection.execute("PRAGMA table_info(runner_results)")}
        for name, definition in (("barrier", "INTEGER"), ("weight_carried_kg", "REAL"), ("jockey", "TEXT"),
                                 ("trainer", "TEXT"), ("official_handicap_rating", "REAL")):
            if name not in runner_columns:
                self.connection.execute(f"ALTER TABLE runner_results ADD COLUMN {name} {definition}")
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def start_run(self, race_date: str, state: str) -> int:
        cursor = self.connection.execute(
            "INSERT INTO ingestion_runs (source, race_date, state, started_at, status) VALUES (?, ?, ?, ?, ?)",
            ("formfav", race_date, state, utc_now(), "running"),
        )
        self.connection.commit()
        return int(cursor.lastrowid)

    def finish_run(self, run_id: int, status: str, detail: str) -> None:
        self.connection.execute(
            "UPDATE ingestion_runs SET completed_at = ?, status = ?, detail = ? WHERE id = ?",
            (utc_now(), status, detail, run_id),
        )
        self.connection.commit()

    def upsert_card(self, race_date: str, state: str, meeting: dict[str, Any], cards: list[dict[str, Any]]) -> int:
        now = utc_now()
        track_slug = str(meeting["slug"])
        self.connection.execute(
            """INSERT INTO meetings (source, race_date, state, track_slug, track_name, raw_json, imported_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(source, race_date, track_slug) DO UPDATE SET
                 state=excluded.state, track_name=excluded.track_name, raw_json=excluded.raw_json, imported_at=excluded.imported_at""",
            ("formfav", race_date, state, track_slug, meeting["track"], json.dumps(meeting), now),
        )
        runner_count = 0
        for card in cards:
            race_number = int(card["raceNumber"])
            self.connection.execute(
                """INSERT INTO races (source, race_date, track_slug, race_number, race_name, start_time, distance, condition, weather, race_class, prize_money, number_of_runners, raw_json, imported_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(source, race_date, track_slug, race_number) DO UPDATE SET
                     race_name=excluded.race_name, start_time=excluded.start_time, distance=excluded.distance, condition=excluded.condition, weather=excluded.weather, race_class=excluded.race_class, prize_money=excluded.prize_money, number_of_runners=excluded.number_of_runners, raw_json=excluded.raw_json, imported_at=excluded.imported_at""",
                ("formfav", race_date, track_slug, race_number, card.get("raceName"), card.get("startTime"), card.get("distance"), card.get("condition"), card.get("weather"), card.get("raceClass"), str(card.get("prizeMoney", "")), card.get("numberOfRunners"), json.dumps(card), now),
            )
            self.connection.execute(
                "DELETE FROM runners WHERE source = ? AND race_date = ? AND track_slug = ? AND race_number = ?",
                ("formfav", race_date, track_slug, race_number),
            )
            for runner in card.get("runners", []):
                runner_number = runner.get("number")
                if runner_number is None:
                    continue
                self.connection.execute(
                    """INSERT INTO runners (source, race_date, track_slug, race_number, runner_number, runner_name, jockey, trainer, barrier, weight, form, scratched, raw_json, imported_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    ("formfav", race_date, track_slug, race_number, int(runner_number), runner.get("name", "Unknown"), runner.get("jockey"), runner.get("trainer"), runner.get("barrier"), runner.get("weight"), runner.get("form") or runner.get("last10Starts"), int(bool(runner.get("scratched") or runner.get("isScratched"))), json.dumps(runner), now),
                )
                runner_count += 1
        self.connection.commit()
        return runner_count

    def upsert_result(
        self,
        *,
        source: str,
        race_date: str,
        state: str,
        track_slug: str,
        race_number: int,
        distance_metres: int | None = None,
        race_class: str | None = None,
        race_class_code: str | None = None,
        scheduled_start_at: str | None = None,
        official_time_seconds: float | None,
        track_condition: str | None,
        rail_position: str | None,
        source_url: str | None,
        raw_race: dict[str, Any],
        runners: list[dict[str, Any]],
    ) -> None:
        """Upsert one official result and its runner outcomes.

        Inputs are already normalised by the importer. Keeping raw payloads on
        every row makes a later source correction auditable.
        """
        now = utc_now()
        self.connection.execute(
            """INSERT INTO race_results (source, race_date, track_slug, race_number, state, distance_metres, race_class, race_class_code, scheduled_start_at, official_time_seconds, track_condition, rail_position, source_url, raw_json, imported_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(source, race_date, track_slug, race_number) DO UPDATE SET
                 state=excluded.state, distance_metres=excluded.distance_metres, race_class=excluded.race_class, race_class_code=excluded.race_class_code, scheduled_start_at=excluded.scheduled_start_at, official_time_seconds=excluded.official_time_seconds,
                 track_condition=excluded.track_condition, rail_position=excluded.rail_position,
                 source_url=excluded.source_url, raw_json=excluded.raw_json, imported_at=excluded.imported_at""",
            (source, race_date, track_slug, race_number, state, distance_metres, race_class, race_class_code, scheduled_start_at, official_time_seconds, track_condition, rail_position, source_url, json.dumps(raw_race), now),
        )
        for runner in runners:
            self.connection.execute(
                """INSERT INTO runner_results (source, race_date, track_slug, race_number, runner_number, runner_name, finish_position, beaten_lengths, finish_time_seconds, barrier, weight_carried_kg, jockey, trainer, official_handicap_rating, result_status, raw_json, imported_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(source, race_date, track_slug, race_number, runner_number) DO UPDATE SET
                     runner_name=excluded.runner_name, finish_position=excluded.finish_position,
                     beaten_lengths=excluded.beaten_lengths, finish_time_seconds=excluded.finish_time_seconds,
                     barrier=excluded.barrier, weight_carried_kg=excluded.weight_carried_kg, jockey=excluded.jockey,
                     trainer=excluded.trainer, official_handicap_rating=excluded.official_handicap_rating,
                     result_status=excluded.result_status, raw_json=excluded.raw_json, imported_at=excluded.imported_at""",
                (source, race_date, track_slug, race_number, runner["runner_number"], runner["runner_name"], runner.get("finish_position"), runner.get("beaten_lengths"), runner.get("finish_time_seconds"), runner.get("barrier"), runner.get("weight_carried_kg"), runner.get("jockey"), runner.get("trainer"), runner.get("official_handicap_rating"), runner.get("result_status", "finished"), json.dumps(runner), now),
            )
        self.connection.commit()

    def enrich_result_metadata(self, *, source: str, race_date: str, track_slug: str,
                               race_number: int, race_class: str | None,
                               race_class_code: str | None, scheduled_start_at: str | None,
                               runners: list[dict[str, Any]]) -> None:
        """Attach card metadata without replacing the authoritative result raw data."""
        self.connection.execute(
            """UPDATE race_results SET race_class = COALESCE(?, race_class),
                   race_class_code = COALESCE(?, race_class_code), scheduled_start_at = COALESCE(?, scheduled_start_at), imported_at = ?
               WHERE source = ? AND race_date = ? AND track_slug = ? AND race_number = ?""",
            (race_class, race_class_code, scheduled_start_at, utc_now(), source, race_date, track_slug, race_number),
        )
        for runner in runners:
            self.connection.execute(
                """UPDATE runner_results SET barrier = COALESCE(?, barrier),
                       weight_carried_kg = COALESCE(?, weight_carried_kg), jockey = COALESCE(?, jockey),
                       trainer = COALESCE(?, trainer), official_handicap_rating = COALESCE(?, official_handicap_rating),
                       imported_at = ?
                   WHERE source = ? AND race_date = ? AND track_slug = ? AND race_number = ? AND runner_number = ?""",
                (runner.get("barrier"), runner.get("weight_carried_kg"), runner.get("jockey"), runner.get("trainer"),
                 runner.get("official_handicap_rating"), utc_now(), source, race_date, track_slug,
                 race_number, runner["runner_number"]),
            )
        self.connection.commit()

    def upsert_race_classification(self, row: dict[str, Any]) -> None:
        self.connection.execute(
            """INSERT INTO race_classifications (source, race_date, track_slug, race_number, race_type,
                   class_family, group_grade, benchmark, class_number, age_condition, sex_condition,
                   raw_class_text, parser_version, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(source, race_date, track_slug, race_number) DO UPDATE SET
                 race_type=excluded.race_type, class_family=excluded.class_family, group_grade=excluded.group_grade,
                 benchmark=excluded.benchmark, class_number=excluded.class_number,
                 age_condition=excluded.age_condition, sex_condition=excluded.sex_condition,
                 raw_class_text=excluded.raw_class_text, parser_version=excluded.parser_version,
                 created_at=excluded.created_at""",
            (row["source"], row["race_date"], row["track_slug"], row["race_number"], row.get("race_type"),
             row["class_family"], row.get("group_grade"), row.get("benchmark"), row.get("class_number"),
             row.get("age_condition"), row.get("sex_condition"), row["raw_class_text"],
             row["parser_version"], utc_now()),
        )
        self.connection.commit()

    def upsert_race_weather(self, row: dict[str, Any]) -> None:
        now = utc_now()
        self.connection.execute(
            """INSERT INTO race_weather (source,race_date,track_slug,race_number,weather_source,station_id,observed_at,
                   temperature_c,humidity_pct,precipitation_mm,wind_direction_deg,wind_speed_kmh,pressure_hpa,
                   quality_json,raw_json,imported_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(source,race_date,track_slug,race_number,weather_source) DO UPDATE SET
                 station_id=excluded.station_id,observed_at=excluded.observed_at,temperature_c=excluded.temperature_c,
                 humidity_pct=excluded.humidity_pct,precipitation_mm=excluded.precipitation_mm,
                 wind_direction_deg=excluded.wind_direction_deg,wind_speed_kmh=excluded.wind_speed_kmh,
                 pressure_hpa=excluded.pressure_hpa,quality_json=excluded.quality_json,raw_json=excluded.raw_json,
                 imported_at=excluded.imported_at""",
            (row["source"],row["race_date"],row["track_slug"],row["race_number"],row["weather_source"],
             row["station_id"],row["observed_at"],row.get("temperature_c"),row.get("humidity_pct"),
             row.get("precipitation_mm"),row.get("wind_direction_deg"),row.get("wind_speed_kmh"),row.get("pressure_hpa"),
             json.dumps(row["quality"],sort_keys=True),json.dumps(row["raw"],sort_keys=True),now),
        )
        self.connection.commit()

    def upsert_sectionals(self, rows: list[dict[str, Any]]) -> None:
        now = utc_now()
        for row in rows:
            self.connection.execute(
                """INSERT INTO runner_sectionals (source, race_date, track_slug, race_number, runner_number, marker_metres, section_seconds, position_at_marker, distance_travelled_metres, speed_kmh, source_url, raw_json, imported_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(source, race_date, track_slug, race_number, runner_number, marker_metres) DO UPDATE SET
                     section_seconds=excluded.section_seconds, position_at_marker=excluded.position_at_marker,
                     distance_travelled_metres=excluded.distance_travelled_metres, speed_kmh=excluded.speed_kmh,
                     source_url=excluded.source_url, raw_json=excluded.raw_json, imported_at=excluded.imported_at""",
                (row["source"], row["race_date"], row["track_slug"], row["race_number"], row["runner_number"], row["marker_metres"], row.get("section_seconds"), row.get("position_at_marker"), row.get("distance_travelled_metres"), row.get("speed_kmh"), row.get("source_url"), json.dumps(row), now),
            )
        self.connection.commit()
