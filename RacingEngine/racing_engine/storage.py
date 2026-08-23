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
    distance_travelled_vs_winner_metres REAL,
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

-- Durable identity is separate from source spellings and name normalisation.
CREATE TABLE IF NOT EXISTS horses (
    horse_id TEXT PRIMARY KEY,
    canonical_name TEXT NOT NULL,
    identity_key TEXT NOT NULL UNIQUE,
    identity_status TEXT NOT NULL,
    detail_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Append-only, source-dated horse facts.  A source may report racing age
-- without exposing an exact foaling date; those are deliberately separate.
CREATE TABLE IF NOT EXISTS horse_profile_observations (
    profile_source TEXT NOT NULL,
    source_horse_id TEXT NOT NULL,
    horse_id TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    birth_date TEXT,
    observed_racing_age INTEGER,
    sex TEXT,
    country_code TEXT,
    source_url TEXT,
    confidence REAL NOT NULL,
    detail_json TEXT NOT NULL,
    imported_at TEXT NOT NULL,
    PRIMARY KEY (profile_source,source_horse_id,observed_at),
    FOREIGN KEY (horse_id) REFERENCES horses(horse_id)
);

-- Point-in-time derivation used by modelling.  Keeping the source observation
-- makes age/WFA calculations reproducible and prevents current-age leakage.
CREATE TABLE IF NOT EXISTS runner_derived_profiles (
    derivation_version TEXT NOT NULL,
    source TEXT NOT NULL,
    race_date TEXT NOT NULL,
    track_slug TEXT NOT NULL,
    race_number INTEGER NOT NULL,
    runner_number INTEGER NOT NULL,
    horse_id TEXT NOT NULL,
    birth_date TEXT,
    racing_age INTEGER,
    age_method TEXT,
    sex TEXT,
    country_code TEXT,
    profile_source TEXT,
    source_observed_at TEXT,
    detail_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (derivation_version,source,race_date,track_slug,race_number,runner_number),
    FOREIGN KEY (horse_id) REFERENCES horses(horse_id)
);

CREATE TABLE IF NOT EXISTS runner_horse_links (
    source TEXT NOT NULL,
    race_date TEXT NOT NULL,
    track_slug TEXT NOT NULL,
    race_number INTEGER NOT NULL,
    runner_number INTEGER NOT NULL,
    horse_id TEXT NOT NULL,
    source_horse_name TEXT NOT NULL,
    cleaned_horse_name TEXT NOT NULL,
    link_method TEXT NOT NULL,
    confidence REAL NOT NULL,
    review_status TEXT NOT NULL,
    detail_json TEXT NOT NULL,
    linked_at TEXT NOT NULL,
    PRIMARY KEY (source,race_date,track_slug,race_number,runner_number),
    FOREIGN KEY (horse_id) REFERENCES horses(horse_id)
);

CREATE TABLE IF NOT EXISTS horse_identity_reviews (
    review_key TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    source_horse_name TEXT NOT NULL,
    proposed_identity_key TEXT,
    reason TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    detail_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    resolved_at TEXT
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

-- Post-meeting estimate used to interpret completed historical runs. It is
-- never available to price another race on the same card.
CREATE TABLE IF NOT EXISTS daily_track_variants (
    variant_version TEXT NOT NULL,
    as_of_date TEXT NOT NULL,
    source TEXT NOT NULL,
    race_date TEXT NOT NULL,
    track_slug TEXT NOT NULL,
    raw_variant_lengths REAL,
    shrunk_variant_lengths REAL NOT NULL,
    races_used INTEGER NOT NULL,
    shrinkage_factor REAL NOT NULL,
    quality_status TEXT NOT NULL,
    detail_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (variant_version,as_of_date,source,race_date,track_slug)
);

-- Append-only market observations. Opening, decision-time and closing labels
-- are derived later; ingestion never overwrites an earlier observation.
CREATE TABLE IF NOT EXISTS market_snapshots (
    market_source TEXT NOT NULL,
    source TEXT NOT NULL,
    race_date TEXT NOT NULL,
    track_slug TEXT NOT NULL,
    race_number INTEGER NOT NULL,
    runner_number INTEGER NOT NULL,
    captured_at TEXT NOT NULL,
    price_type TEXT NOT NULL,
    decimal_odds REAL NOT NULL,
    available_volume REAL,
    source_event_id TEXT,
    detail_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (market_source,source,race_date,track_slug,race_number,runner_number,captured_at,price_type)
);

CREATE TABLE IF NOT EXISTS model_calibrations (
    calibration_version TEXT NOT NULL,
    source_model_version TEXT NOT NULL,
    protocol_hash TEXT NOT NULL,
    fit_period TEXT NOT NULL,
    method TEXT NOT NULL,
    parameter_json TEXT NOT NULL,
    sample_races INTEGER NOT NULL,
    status TEXT NOT NULL,
    detail_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (calibration_version,source_model_version,protocol_hash,fit_period)
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

-- Frozen, prediction-level evidence for reproducible model benchmarks.
CREATE TABLE IF NOT EXISTS benchmark_predictions (
    protocol_version TEXT NOT NULL,
    protocol_hash TEXT NOT NULL,
    model_version TEXT NOT NULL,
    period TEXT NOT NULL,
    source TEXT NOT NULL,
    race_date TEXT NOT NULL,
    track_slug TEXT NOT NULL,
    race_number INTEGER NOT NULL,
    runner_number INTEGER NOT NULL,
    runner_name TEXT NOT NULL,
    horse_key TEXT NOT NULL,
    raw_rating REAL NOT NULL,
    win_probability REAL NOT NULL,
    outcome REAL NOT NULL,
    history_depth INTEGER NOT NULL,
    unrated INTEGER NOT NULL,
    information_cutoff TEXT NOT NULL,
    detail_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (protocol_hash, model_version, source, race_date, track_slug, race_number, runner_number)
);

CREATE TABLE IF NOT EXISTS benchmark_reports (
    protocol_hash TEXT NOT NULL,
    model_version TEXT NOT NULL,
    report_name TEXT NOT NULL,
    database_cutoff TEXT NOT NULL,
    report_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (protocol_hash, model_version, report_name)
);

-- Versioned canonical sectional intervals derived without changing raw evidence.
CREATE TABLE IF NOT EXISTS canonical_sectionals (
    feature_version TEXT NOT NULL,
    source TEXT NOT NULL,
    race_date TEXT NOT NULL,
    track_slug TEXT NOT NULL,
    race_number INTEGER NOT NULL,
    runner_number INTEGER NOT NULL,
    final_200_seconds REAL,
    final_400_seconds REAL,
    final_600_seconds REAL,
    early_to_800_seconds REAL,
    eight_to_four_seconds REAL,
    position_800m INTEGER,
    position_600m INTEGER,
    position_400m INTEGER,
    position_200m INTEGER,
    quality_status TEXT NOT NULL,
    missing_reasons_json TEXT NOT NULL,
    derivation_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (feature_version,source,race_date,track_slug,race_number,runner_number)
);

-- Descriptive class-prior research; not consumed by the accepted model yet.
CREATE TABLE IF NOT EXISTS class_prior_research (
    research_version TEXT NOT NULL,
    as_of_date TEXT NOT NULL,
    level TEXT NOT NULL,
    group_key TEXT NOT NULL,
    parent_key TEXT,
    races INTEGER NOT NULL,
    runner_rating_coverage REAL NOT NULL,
    raw_mean_field_rating REAL,
    shrunk_field_rating REAL,
    shrinkage_weight REAL,
    prior_strength_races REAL,
    uncertainty REAL,
    detail_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (research_version,as_of_date,level,group_key)
);

-- Frozen prior-only runner states and field summaries at each historical race.
CREATE TABLE IF NOT EXISTS pre_race_runner_states (
    field_model_version TEXT NOT NULL,
    source TEXT NOT NULL,
    race_date TEXT NOT NULL,
    track_slug TEXT NOT NULL,
    race_number INTEGER NOT NULL,
    runner_number INTEGER NOT NULL,
    horse_id TEXT NOT NULL,
    horse_name TEXT NOT NULL,
    prior_rating REAL NOT NULL,
    prior_runs INTEGER NOT NULL,
    prior_uncertainty REAL NOT NULL,
    rated INTEGER NOT NULL,
    information_cutoff TEXT NOT NULL,
    detail_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (field_model_version,source,race_date,track_slug,race_number,runner_number)
);

CREATE TABLE IF NOT EXISTS pre_race_field_strengths (
    field_model_version TEXT NOT NULL,
    source TEXT NOT NULL,
    race_date TEXT NOT NULL,
    track_slug TEXT NOT NULL,
    race_number INTEGER NOT NULL,
    starters INTEGER NOT NULL,
    rated_runners INTEGER NOT NULL,
    rated_coverage REAL NOT NULL,
    field_median_rating REAL NOT NULL,
    rated_only_median_rating REAL,
    top_four_mean_rating REAL NOT NULL,
    top_rating REAL NOT NULL,
    depth_within_five INTEGER NOT NULL,
    field_uncertainty REAL NOT NULL,
    information_cutoff TEXT NOT NULL,
    detail_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (field_model_version,source,race_date,track_slug,race_number)
);

-- Pre-race Race Strength components. Completed-race evidence is separate below.
CREATE TABLE IF NOT EXISTS race_strength_ratings (
    race_strength_version TEXT NOT NULL,
    source TEXT NOT NULL,
    race_date TEXT NOT NULL,
    track_slug TEXT NOT NULL,
    race_number INTEGER NOT NULL,
    class_prior_level TEXT,
    class_prior_key TEXT,
    class_prior_official_scale REAL,
    class_global_official_scale REAL,
    class_only_rating REAL,
    class_reliability REAL NOT NULL,
    field_only_rating REAL NOT NULL,
    field_reliability REAL NOT NULL,
    combined_rating REAL NOT NULL,
    rated_coverage REAL NOT NULL,
    field_uncertainty REAL NOT NULL,
    information_cutoff TEXT NOT NULL,
    component_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (race_strength_version,source,race_date,track_slug,race_number)
);

CREATE TABLE IF NOT EXISTS post_race_strength_evidence (
    evidence_version TEXT NOT NULL,
    source TEXT NOT NULL,
    race_date TEXT NOT NULL,
    track_slug TEXT NOT NULL,
    race_number INTEGER NOT NULL,
    official_time_seconds REAL,
    winner_time_seconds REAL,
    finishers INTEGER NOT NULL,
    margin_observations INTEGER NOT NULL,
    runner_time_observations INTEGER NOT NULL,
    evidence_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (evidence_version,source,race_date,track_slug,race_number)
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

-- Official post-race steward material is immutable source evidence.  It is
-- deliberately separate from ratings: an incident is not automatically a
-- number of lengths, and must remain auditable after the parser evolves.
CREATE TABLE IF NOT EXISTS steward_reports (
    report_source TEXT NOT NULL,
    race_date TEXT NOT NULL,
    track_slug TEXT NOT NULL,
    race_number INTEGER NOT NULL,
    source_race_code TEXT,
    report_html TEXT NOT NULL,
    report_text TEXT NOT NULL,
    source_updated_at TEXT,
    source_url TEXT,
    parser_version TEXT NOT NULL,
    imported_at TEXT NOT NULL,
    PRIMARY KEY (report_source, race_date, track_slug, race_number)
);

-- One or more deterministic classifications can arise from an official
-- report paragraph.  ``suggested_trip_adjustment`` is a research proposal
-- only; it is not consumed by V1 performance ratings until walk-forward
-- validation proves that the category adds predictive value.
CREATE TABLE IF NOT EXISTS steward_events (
    report_source TEXT NOT NULL,
    race_date TEXT NOT NULL,
    track_slug TEXT NOT NULL,
    race_number INTEGER NOT NULL,
    event_key TEXT NOT NULL,
    horse_key TEXT NOT NULL,
    horse_name TEXT NOT NULL,
    category TEXT NOT NULL,
    severity TEXT NOT NULL,
    parser_confidence REAL NOT NULL,
    suggested_trip_adjustment REAL NOT NULL DEFAULT 0,
    fitness_status TEXT,
    requires_human_review INTEGER NOT NULL DEFAULT 0,
    evidence_text TEXT NOT NULL,
    parser_version TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (report_source, race_date, track_slug, race_number, event_key)
);

-- A meeting can legitimately have no published report in the public source.
-- Record that it was checked so retries do not hammer the source forever.
CREATE TABLE IF NOT EXISTS steward_report_ingestions (
    report_source TEXT NOT NULL,
    race_date TEXT NOT NULL,
    track_slug TEXT NOT NULL,
    status TEXT NOT NULL,
    detail TEXT,
    checked_at TEXT NOT NULL,
    PRIMARY KEY (report_source, race_date, track_slug)
);

CREATE INDEX IF NOT EXISTS idx_runner_results_history
  ON runner_results (race_date, runner_name, result_status);
CREATE INDEX IF NOT EXISTS idx_race_results_pars
  ON race_results (race_date, track_slug, state);
CREATE INDEX IF NOT EXISTS idx_steward_events_horse
  ON steward_events (horse_key, race_date);

-- Research-only reconstruction of the weight a runner actually carried and
-- the surrounding race conditions.  Missing source components stay NULL.
CREATE TABLE IF NOT EXISTS runner_weight_contexts (
    feature_version TEXT NOT NULL,
    source TEXT NOT NULL,
    race_date TEXT NOT NULL,
    track_slug TEXT NOT NULL,
    race_number INTEGER NOT NULL,
    runner_number INTEGER NOT NULL,
    horse_id TEXT,
    weight_condition TEXT NOT NULL,
    carried_weight_kg REAL,
    allocated_weight_kg REAL,
    apprentice_claim_kg REAL,
    overweight_kg REAL,
    penalty_kg REAL,
    official_wfa_kg REAL,
    carried_minus_wfa_kg REAL,
    carried_minus_field_median_kg REAL,
    official_rating REAL,
    race_benchmark INTEGER,
    weight_change_kg REAL,
    official_rating_change REAL,
    class_change REAL,
    distance_change_metres INTEGER,
    stronger_race INTEGER,
    evidence_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (feature_version,source,race_date,track_slug,race_number,runner_number)
);

-- A leakage-audited modelling row.  Historical outcome evidence is summarized
-- only from races strictly before target_race_date.
CREATE TABLE IF NOT EXISTS point_in_time_features (
    feature_version TEXT NOT NULL,
    source TEXT NOT NULL,
    target_race_date TEXT NOT NULL,
    track_slug TEXT NOT NULL,
    race_number INTEGER NOT NULL,
    runner_number INTEGER NOT NULL,
    horse_id TEXT,
    history_runs INTEGER NOT NULL,
    days_since_last_run INTEGER,
    campaign_run_number INTEGER,
    prior_weight_kg REAL,
    prior_weight_change_kg REAL,
    prior_official_rating REAL,
    prior_race_strength REAL,
    prior_daily_variant REAL,
    prior_going TEXT,
    prior_sectional_confidence REAL,
    prior_distance_travelled_vs_winner REAL,
    prior_steward_event_count INTEGER,
    current_distance_metres INTEGER,
    current_weight_condition TEXT,
    current_class_family TEXT,
    availability_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (feature_version,source,target_race_date,track_slug,race_number,runner_number)
);
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
        if "distance_travelled_vs_winner_metres" not in runner_columns:
            self.connection.execute("ALTER TABLE runner_results ADD COLUMN distance_travelled_vs_winner_metres REAL")
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def upsert_steward_report(self, *, report_source: str, race_date: str,
                              track_slug: str, race_number: int,
                              source_race_code: str | None, report_html: str,
                              report_text: str, source_updated_at: str | None,
                              source_url: str | None, parser_version: str,
                              events: list[dict[str, Any]]) -> None:
        """Store source report and deterministic event classifications together."""
        now = utc_now()
        self.connection.execute(
            """INSERT INTO steward_reports (report_source,race_date,track_slug,race_number,
               source_race_code,report_html,report_text,source_updated_at,source_url,parser_version,imported_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(report_source,race_date,track_slug,race_number) DO UPDATE SET
                 source_race_code=excluded.source_race_code, report_html=excluded.report_html,
                 report_text=excluded.report_text, source_updated_at=excluded.source_updated_at,
                 source_url=excluded.source_url, parser_version=excluded.parser_version,
                 imported_at=excluded.imported_at""",
            (report_source, race_date, track_slug, race_number, source_race_code,
             report_html, report_text, source_updated_at, source_url, parser_version, now),
        )
        self.connection.execute(
            """DELETE FROM steward_events WHERE report_source = ? AND race_date = ?
               AND track_slug = ? AND race_number = ?""",
            (report_source, race_date, track_slug, race_number),
        )
        for event in events:
            self.connection.execute(
                """INSERT INTO steward_events (report_source,race_date,track_slug,race_number,event_key,
                   horse_key,horse_name,category,severity,parser_confidence,suggested_trip_adjustment,
                   fitness_status,requires_human_review,evidence_text,parser_version,created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (report_source, race_date, track_slug, race_number, event["event_key"],
                 event["horse_key"], event["horse_name"], event["category"], event["severity"],
                 event["parser_confidence"], event["suggested_trip_adjustment"], event.get("fitness_status"),
                 int(event["requires_human_review"]), event["evidence_text"], parser_version, now),
            )
        self.connection.commit()

    def record_steward_report_check(self, *, report_source: str, race_date: str,
                                    track_slug: str, status: str, detail: str | None = None) -> None:
        self.connection.execute(
            """INSERT INTO steward_report_ingestions (report_source,race_date,track_slug,status,detail,checked_at)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(report_source,race_date,track_slug) DO UPDATE SET
                 status=excluded.status, detail=excluded.detail, checked_at=excluded.checked_at""",
            (report_source, race_date, track_slug, status, detail, utc_now()),
        )
        self.connection.commit()

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
                """INSERT INTO runner_results (source, race_date, track_slug, race_number, runner_number, runner_name, finish_position, beaten_lengths, finish_time_seconds, barrier, weight_carried_kg, jockey, trainer, official_handicap_rating, distance_travelled_vs_winner_metres, result_status, raw_json, imported_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(source, race_date, track_slug, race_number, runner_number) DO UPDATE SET
                     runner_name=excluded.runner_name, finish_position=excluded.finish_position,
                     beaten_lengths=excluded.beaten_lengths, finish_time_seconds=excluded.finish_time_seconds,
                     barrier=excluded.barrier, weight_carried_kg=excluded.weight_carried_kg, jockey=excluded.jockey,
                     trainer=excluded.trainer, official_handicap_rating=excluded.official_handicap_rating,
                     distance_travelled_vs_winner_metres=excluded.distance_travelled_vs_winner_metres,
                     result_status=excluded.result_status, raw_json=excluded.raw_json, imported_at=excluded.imported_at""",
                (source, race_date, track_slug, race_number, runner["runner_number"], runner["runner_name"], runner.get("finish_position"), runner.get("beaten_lengths"), runner.get("finish_time_seconds"), runner.get("barrier"), runner.get("weight_carried_kg"), runner.get("jockey"), runner.get("trainer"), runner.get("official_handicap_rating"), runner.get("distance_travelled_vs_winner_metres"), runner.get("result_status", "finished"), json.dumps(runner), now),
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

    def enrich_runner_trip_metrics(self, *, source: str, race_date: str, track_slug: str,
                                   race_number: int, runners: list[dict[str, Any]]) -> None:
        for runner in runners:
            if runner.get("distance_travelled_vs_winner_metres") is None:
                continue
            self.connection.execute(
                """UPDATE runner_results SET distance_travelled_vs_winner_metres = ?, imported_at = ?
                   WHERE source = ? AND race_date = ? AND track_slug = ? AND race_number = ? AND runner_number = ?""",
                (runner["distance_travelled_vs_winner_metres"], utc_now(), source, race_date,
                 track_slug, race_number, runner["runner_number"]),
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
