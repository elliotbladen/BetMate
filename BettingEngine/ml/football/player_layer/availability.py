"""Auditable player availability store for EPL and Championship.

The database is intentionally a local SQLite file: it is easy to inspect, easy
to back up, and prevents an external feed from silently rewriting history.  Every
availability assertion and line-up record is timestamped and source-attributed.
Snapshots only expose information known at their declared cutoff.
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path


class AvailabilityStatus(StrEnum):
    AVAILABLE = "available"
    DOUBTFUL = "doubtful"
    INJURED = "injured"
    SUSPENDED = "suspended"
    REST_RISK = "rest_risk"
    INTERNATIONAL_DUTY = "international_duty"
    OUT = "out"


class SnapshotStage(StrEnum):
    EARLY = "early"
    FINAL = "final"


_VALID_POSITIONS = {"GK", "CB", "FB", "WB", "DM", "CM", "AM", "W", "ST"}
_VALID_SOURCES = {"official_club", "official_league", "manager_press_conference", "reputable_report", "manual"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _parse_iso(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include a timezone, e.g. 2026-08-13T10:00:00+10:00")
    return parsed.astimezone(timezone.utc)


def _normalise_position(position: str) -> str:
    result = position.upper().strip()
    if result not in _VALID_POSITIONS:
        raise ValueError(f"unsupported position '{position}'; use one of {sorted(_VALID_POSITIONS)}")
    return result


@dataclass(frozen=True)
class SnapshotPlayer:
    player_id: int
    player_name: str
    team: str
    position: str
    availability: str
    start_probability: float
    expected_minutes: float
    evidence_recorded_at: str
    source_type: str
    source_url: str | None


class AvailabilityStore:
    """Read/write store for one competition's player availability data."""

    def __init__(self, path: Path, league: str):
        if league not in {"epl", "championship"}:
            raise ValueError("player layer currently supports only 'epl' and 'championship'")
        self.path = Path(path)
        self.league = league

    @classmethod
    def for_league(cls, league: str, data_root: Path | None = None) -> "AvailabilityStore":
        root = data_root or Path(__file__).resolve().parents[1] / "data"
        return cls(root / league / "player_layer" / "availability.sqlite", league)

    def _connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def initialise(self) -> None:
        with closing(self._connect()) as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS players (
                    id INTEGER PRIMARY KEY,
                    league TEXT NOT NULL,
                    team TEXT NOT NULL,
                    player_name TEXT NOT NULL,
                    position TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1,
                    UNIQUE(league, team, player_name)
                );
                CREATE TABLE IF NOT EXISTS availability_updates (
                    id INTEGER PRIMARY KEY,
                    player_id INTEGER NOT NULL REFERENCES players(id),
                    status TEXT NOT NULL,
                    start_probability REAL NOT NULL CHECK(start_probability >= 0 AND start_probability <= 1),
                    expected_minutes REAL NOT NULL CHECK(expected_minutes >= 0 AND expected_minutes <= 120),
                    source_type TEXT NOT NULL,
                    source_url TEXT,
                    note TEXT NOT NULL DEFAULT '',
                    event_time TEXT NOT NULL,
                    recorded_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_availability_cutoff
                    ON availability_updates(player_id, recorded_at, event_time);
                CREATE TABLE IF NOT EXISTS match_snapshots (
                    id INTEGER PRIMARY KEY,
                    league TEXT NOT NULL,
                    home_team TEXT NOT NULL,
                    away_team TEXT NOT NULL,
                    kickoff_at TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    cutoff_at TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(league, home_team, away_team, kickoff_at, stage, cutoff_at)
                );
                CREATE TABLE IF NOT EXISTS snapshot_players (
                    snapshot_id INTEGER NOT NULL REFERENCES match_snapshots(id),
                    player_id INTEGER NOT NULL REFERENCES players(id),
                    side TEXT NOT NULL CHECK(side IN ('home', 'away')),
                    confirmed_starter INTEGER NOT NULL DEFAULT 0,
                    confirmed_bench INTEGER NOT NULL DEFAULT 0,
                    start_probability REAL NOT NULL CHECK(start_probability >= 0 AND start_probability <= 1),
                    expected_minutes REAL NOT NULL CHECK(expected_minutes >= 0 AND expected_minutes <= 120),
                    source_update_id INTEGER REFERENCES availability_updates(id),
                    PRIMARY KEY(snapshot_id, player_id)
                );
                CREATE TABLE IF NOT EXISTS observed_appearances (
                    id INTEGER PRIMARY KEY,
                    league TEXT NOT NULL,
                    home_team TEXT NOT NULL,
                    away_team TEXT NOT NULL,
                    kickoff_at TEXT NOT NULL,
                    player_id INTEGER NOT NULL REFERENCES players(id),
                    started INTEGER NOT NULL CHECK(started IN (0, 1)),
                    minutes_played REAL NOT NULL CHECK(minutes_played >= 0 AND minutes_played <= 120),
                    position_played TEXT,
                    recorded_at TEXT NOT NULL,
                    UNIQUE(league, home_team, away_team, kickoff_at, player_id)
                );
                """
            )
            conn.commit()

    def add_player(self, team: str, player_name: str, position: str) -> int:
        self.initialise()
        with closing(self._connect()) as conn:
            conn.execute(
                "INSERT INTO players (league, team, player_name, position) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(league, team, player_name) DO UPDATE SET position=excluded.position, active=1",
                (self.league, team.strip(), player_name.strip(), _normalise_position(position)),
            )
            row = conn.execute(
                "SELECT id FROM players WHERE league=? AND team=? AND player_name=?",
                (self.league, team.strip(), player_name.strip()),
            ).fetchone()
            conn.commit()
            return int(row["id"])

    def record_update(
        self, *, team: str, player_name: str, position: str, status: str,
        start_probability: float, expected_minutes: float, source_type: str,
        source_url: str | None = None, note: str = "", event_time: str | None = None,
        recorded_at: str | None = None,
    ) -> int:
        """Record what was known, when it was known. Never update past records."""
        status = AvailabilityStatus(status).value
        if source_type not in _VALID_SOURCES:
            raise ValueError(f"source_type must be one of {sorted(_VALID_SOURCES)}")
        if not 0 <= start_probability <= 1 or not 0 <= expected_minutes <= 120:
            raise ValueError("start_probability must be 0–1 and expected_minutes 0–120")
        event_time = event_time or _utc_now()
        recorded_at = recorded_at or _utc_now()
        _parse_iso(event_time)
        _parse_iso(recorded_at)
        player_id = self.add_player(team, player_name, position)
        with closing(self._connect()) as conn:
            cur = conn.execute(
                """INSERT INTO availability_updates
                   (player_id,status,start_probability,expected_minutes,source_type,source_url,note,event_time,recorded_at)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (player_id, status, start_probability, expected_minutes, source_type,
                 source_url, note.strip(), event_time, recorded_at),
            )
            conn.commit()
            return int(cur.lastrowid)

    def create_snapshot(
        self, *, home_team: str, away_team: str, kickoff_at: str, stage: str,
        cutoff_at: str, confirmed_home: list[str] | None = None,
        confirmed_away: list[str] | None = None,
    ) -> int:
        """Freeze information available by cutoff; final snapshots may mark named starters."""
        stage = SnapshotStage(stage).value
        kickoff = _parse_iso(kickoff_at)
        cutoff = _parse_iso(cutoff_at)
        if cutoff > kickoff:
            raise ValueError("snapshot cutoff cannot be after kickoff")
        if stage == SnapshotStage.EARLY and (confirmed_home or confirmed_away):
            raise ValueError("early snapshots cannot contain confirmed team-sheet data")
        self.initialise()
        with closing(self._connect()) as conn:
            cur = conn.execute(
                """INSERT INTO match_snapshots (league,home_team,away_team,kickoff_at,stage,cutoff_at,created_at)
                   VALUES (?,?,?,?,?,?,?)""",
                (self.league, home_team, away_team, kickoff_at, stage, cutoff_at, _utc_now()),
            )
            snapshot_id = int(cur.lastrowid)
            for side, team, confirmed in (("home", home_team, set(confirmed_home or [])), ("away", away_team, set(confirmed_away or []))):
                rows = conn.execute(
                    """SELECT p.id, p.player_name, u.id AS update_id, u.start_probability, u.expected_minutes
                       FROM players p
                       LEFT JOIN availability_updates u ON u.id = (
                         SELECT u2.id FROM availability_updates u2
                         WHERE u2.player_id=p.id AND u2.recorded_at<=? AND u2.event_time<=?
                         ORDER BY u2.event_time DESC, u2.recorded_at DESC LIMIT 1)
                       WHERE p.league=? AND p.team=? AND p.active=1""",
                    (cutoff.isoformat(), cutoff.isoformat(), self.league, team),
                ).fetchall()
                for row in rows:
                    is_starter = row["player_name"] in confirmed
                    # A named starter is certainty, but minutes remain conservative at 78.
                    probability = 1.0 if is_starter else float(row["start_probability"] or 0.0)
                    minutes = 78.0 if is_starter else float(row["expected_minutes"] or 0.0)
                    conn.execute(
                        """INSERT INTO snapshot_players
                           (snapshot_id,player_id,side,confirmed_starter,confirmed_bench,start_probability,expected_minutes,source_update_id)
                           VALUES (?,?,?,?,?,?,?,?)""",
                        (snapshot_id, row["id"], side, int(is_starter), 0, probability, minutes, row["update_id"]),
                    )
            conn.commit()
            return snapshot_id

    def snapshot_players(self, snapshot_id: int) -> list[SnapshotPlayer]:
        with closing(self._connect()) as conn:
            rows = conn.execute(
                """SELECT p.id player_id,p.player_name,p.team,p.position,u.status,u.source_type,u.source_url,
                          u.recorded_at,sp.start_probability,sp.expected_minutes
                   FROM snapshot_players sp JOIN players p ON p.id=sp.player_id
                   LEFT JOIN availability_updates u ON u.id=sp.source_update_id
                   WHERE sp.snapshot_id=? ORDER BY p.team,p.position,p.player_name""",
                (snapshot_id,),
            ).fetchall()
        return [SnapshotPlayer(
            player_id=int(r["player_id"]), player_name=r["player_name"], team=r["team"],
            position=r["position"], availability=r["status"] or "unknown",
            start_probability=float(r["start_probability"]), expected_minutes=float(r["expected_minutes"]),
            evidence_recorded_at=r["recorded_at"] or "", source_type=r["source_type"] or "",
            source_url=r["source_url"],
        ) for r in rows]

    def record_appearance(
        self, *, home_team: str, away_team: str, kickoff_at: str, team: str,
        player_name: str, position: str, started: bool, minutes_played: float,
        position_played: str | None = None,
    ) -> None:
        """Store the observed line-up/minutes after a match for shadow evaluation."""
        _parse_iso(kickoff_at)
        if team not in {home_team, away_team}:
            raise ValueError("appearance team must be either the home or away team")
        if not 0 <= minutes_played <= 120:
            raise ValueError("minutes_played must be 0–120")
        player_id = self.add_player(team, player_name, position)
        played_position = _normalise_position(position_played) if position_played else None
        self.initialise()
        with closing(self._connect()) as conn:
            conn.execute(
                """INSERT INTO observed_appearances
                   (league,home_team,away_team,kickoff_at,player_id,started,minutes_played,position_played,recorded_at)
                   VALUES (?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(league,home_team,away_team,kickoff_at,player_id) DO UPDATE SET
                     started=excluded.started, minutes_played=excluded.minutes_played,
                     position_played=excluded.position_played, recorded_at=excluded.recorded_at""",
                (self.league, home_team, away_team, kickoff_at, player_id, int(started),
                 minutes_played, played_position, _utc_now()),
            )
            conn.commit()
