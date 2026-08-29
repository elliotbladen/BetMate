from pathlib import Path

import pytest

from ml.football.player_layer.availability import AvailabilityStore


def test_early_snapshot_uses_only_information_known_at_cutoff(tmp_path: Path):
    store = AvailabilityStore(tmp_path / "availability.sqlite", "epl")
    store.record_update(
        team="Arsenal", player_name="Example Player", position="ST", status="doubtful",
        start_probability=0.45, expected_minutes=42, source_type="official_club",
        event_time="2026-08-20T10:00:00+00:00", recorded_at="2026-08-20T10:05:00+00:00",
    )
    store.record_update(
        team="Arsenal", player_name="Example Player", position="ST", status="available",
        start_probability=0.95, expected_minutes=80, source_type="official_club",
        event_time="2026-08-22T10:00:00+00:00", recorded_at="2026-08-22T10:05:00+00:00",
    )
    snapshot_id = store.create_snapshot(
        home_team="Arsenal", away_team="Chelsea", kickoff_at="2026-08-22T15:00:00+00:00",
        stage="early", cutoff_at="2026-08-21T12:00:00+00:00",
    )
    players = store.snapshot_players(snapshot_id)
    assert len(players) == 1
    assert players[0].availability == "doubtful"
    assert players[0].start_probability == 0.45


def test_early_snapshot_rejects_confirmed_team_sheet(tmp_path: Path):
    store = AvailabilityStore(tmp_path / "availability.sqlite", "championship")
    with pytest.raises(ValueError, match="early snapshots"):
        store.create_snapshot(
            home_team="Leeds", away_team="Coventry", kickoff_at="2026-08-22T15:00:00+00:00",
            stage="early", cutoff_at="2026-08-21T12:00:00+00:00", confirmed_home=["Player"],
        )


def test_observed_appearance_can_be_corrected_without_duplicating_row(tmp_path: Path):
    store = AvailabilityStore(tmp_path / "availability.sqlite", "epl")
    details = dict(home_team="Arsenal", away_team="Chelsea", kickoff_at="2026-08-22T15:00:00+00:00",
                   team="Arsenal", player_name="Example Player", position="ST")
    store.record_appearance(**details, started=True, minutes_played=80)
    store.record_appearance(**details, started=True, minutes_played=82)
    with store._connect() as conn:
        rows = conn.execute("SELECT minutes_played FROM observed_appearances").fetchall()
    assert len(rows) == 1
    assert rows[0]["minutes_played"] == 82
