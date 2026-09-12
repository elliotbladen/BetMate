import json

import pytest

from racing_engine.trial_batch import collect_batch, discover_meetings
from racing_engine.trial_meeting import MeetingError, validate_review_target
from test_trial_meeting import fixture, URL, store


def test_calendar_deduplicates_and_records_out_of_scope_states():
    html = '''<a href="/FreeFields/Results.aspx?Key=2026Sep08,NSW,Rosehill Gardens,Trial">Results</a>
    <a href="/FreeFields/Results.aspx?Key=2026Sep08,NSW,Rosehill Gardens,Trial">Available</a>
    <a href="/FreeFields/Results.aspx?Key=2026Sep04,ACT,Canberra,Trial">ACT</a>
    <a href="/FreeFields/Results.aspx?Key=2026Sep08,NSW,Rosehill Gardens">Race</a>
    <a href="https://example.test/FreeFields/Results.aspx?Key=2026Sep08,NSW,Rosehill Gardens,Trial">Other host</a>'''
    plan = discover_meetings(html.encode())
    assert len(plan['meetings']) == 1
    assert plan['meetings'][0]['url'] == URL
    assert len(plan['excluded_other_states']) == 1
    assert plan['excluded_other_states'][0]['state'] == 'ACT'


def test_empty_calendar_fails_explicitly():
    with pytest.raises(MeetingError, match='no_nsw_trial'):
        discover_meetings(b'<html>No results</html>')


def test_batch_accounts_for_failures_and_replays_without_duplicate_events(store, tmp_path):
    good = {'date': '2026-09-08', 'state': 'NSW', 'track': 'Rosehill Gardens', 'url': URL}
    bad = {**good, 'date': '2026-09-09', 'url': URL.replace('Sep08', 'Sep09')}
    plan = {'meetings': [good, bad], 'excluded_other_states': []}
    first_dir = tmp_path / 'first'; first_dir.mkdir()
    summary = collect_batch(store, plan, archive_root=tmp_path / 'raw', run_directory=first_dir,
        fetcher=lambda _: fixture(), delay=0)
    assert summary['expected_meetings'] == 2
    assert summary['reconciled_meetings'] == 1
    assert len(summary['failed_meetings']) == 1
    assert summary['status'] == 'completed_with_gaps'
    assert summary['inserted'] == 2
    second_dir = tmp_path / 'second'; second_dir.mkdir()
    def forbidden_fetch(_):
        raise AssertionError('Replay must not download')
    replay = collect_batch(store, plan, archive_root=tmp_path / 'raw', run_directory=second_dir,
        fetcher=forbidden_fetch, delay=0, replay_directory=first_dir)
    assert replay['inserted'] == 0 and replay['unchanged'] == 2
    # A modified cache is rejected rather than trusted.
    report = json.loads((first_dir / 'meeting_000.json').read_text())
    from pathlib import Path
    Path(report['archive']['payload_path']).write_bytes(b'corrupted')
    third_dir = tmp_path / 'third'; third_dir.mkdir()
    damaged = collect_batch(store, plan, archive_root=tmp_path / 'raw', run_directory=third_dir,
        fetcher=forbidden_fetch, delay=0, replay_directory=first_dir)
    assert damaged['failed_meetings'][0]['error'] == 'archive_hash_mismatch'


def test_registry_database_cannot_be_used_as_output(tmp_path):
    path = tmp_path / 'existing.sqlite'
    path.touch()
    with pytest.raises(MeetingError, match='separate review'):
        validate_review_target(path, path)
    hardlink = tmp_path / 'hardlink.sqlite'
    hardlink.hardlink_to(path)
    with pytest.raises(MeetingError, match='separate review'):
        validate_review_target(hardlink, path)
