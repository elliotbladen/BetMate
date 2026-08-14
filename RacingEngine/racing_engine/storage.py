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
"""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class RacingStore:
    def __init__(self, database_path: Path) -> None:
        database_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(database_path)
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript(SCHEMA)

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
