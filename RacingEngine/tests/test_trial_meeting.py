"""Synthetic source fixtures test the full trial pipeline without private data."""
import copy
import json
import sqlite3
from pathlib import Path

import pytest

from racing_engine.storage import RacingStore
from racing_engine.trial_meeting import MeetingError, ingest_meeting, parse_meeting

URL = 'https://mdata.racingnsw.com.au/FreeFields/Results.aspx?Key=2026Sep08,NSW,Rosehill%20Gardens,Trial'
COLLECTED = '2026-09-12T03:00:00+00:00'


def runner(number, name, finish, code, *, scratched=False, margin='', barrier='0'):
    cells = [finish, str(number), f'<a href="../Horse.aspx?horsecode={code}">{name}</a>',
             'Synthetic Trainer', 'Synthetic Rider', margin, barrier]
    return '<tr class="' + ('Scratched' if scratched else 'EvenRow') + '">' + ''.join('<td>' + v + '</td>' for v in cells) + '</tr>'


def fixture():
    header = '''<header class='race-venue'><h2><span notranslate>Rosehill Gardens: Test Club</span>
    <span class='race-venue-date'>Tuesday 08, September 2026</span></h2></header>
    <div>Total Number of starters for this meeting (including emergencies) 3</div>
    <b>Results Last Published:</b> Tue 08-Sep-26 11:00AM AEST<br>
    <a href="#Race1">1</a><a href="#Race2">2</a>'''
    def heat(n, rows):
        return f'''<div notranslate class="race-title"><a>Race {n} - 9:00AM OPEN TRIAL (1000 METRES)</a></div>
        <div class="race-info"><b>Track Type:</b> Turf <b>Track Condition:</b> Good 4
        <b>Time:</b> 1:00.00 <b>Last 600m:</b> 0:35.00 <b>Timing Method:</b> Electronic</div>
        <table class="race-strip-fields"><thead><tr>''' + ''.join('<th>' + c + '</th>' for c in
        ['Finish', 'No.', 'Horse', 'Trainer', 'Jockey', 'Marg(L)', 'Bar']) + '</tr></thead><tbody>' + rows + '</tbody></table>'
    return (header + heat(1, runner(1, 'Known Horse', '1', 'known') + runner(2, 'New Horse', '2', 'new', margin='1.25') +
                         runner(3, 'Scratched Horse', '', 'scratched', scratched=True)) +
            heat(2, runner(1, 'Second Horse', '1', 'second'))).encode()


def parse(payload=None, **overrides):
    opts = dict(expected_date='2026-09-08', expected_track='Rosehill Gardens', collected_at=COLLECTED)
    opts.update(overrides)
    return parse_meeting(payload or fixture(), URL, **opts)


@pytest.fixture
def store(tmp_path):
    store = RacingStore(tmp_path / 'trials.sqlite')
    for hid, name, key in [('h1', 'Known Horse', 'knownhorse'), ('h2', 'Second Horse', 'secondhorse')]:
        store.connection.execute('INSERT INTO horses VALUES (?,?,?,?,?,?,?)',
            (hid, name, key, 'reviewed', '{}', COLLECTED, COLLECTED))
    store.connection.commit()
    yield store
    store.close()


def test_source_counts_scratches_and_time_semantics():
    meeting = parse()
    assert meeting['advertised_starters'] == 3
    assert len(meeting['rows']) == 4
    assert [h['starters'] for h in meeting['heats']] == [2, 1]
    assert meeting['rows'][0]['barrier'] is None
    assert meeting['rows'][0]['official_time_seconds'] == 60
    assert meeting['rows'][1]['official_time_seconds'] is None
    assert meeting['rows'][1]['detail']['heat_time_seconds'] == 60
    assert meeting['rows'][1]['effective_at'] == COLLECTED
    assert meeting['rows'][2]['result_status'] == 'scr'


@pytest.mark.parametrize('old,new', [
    ('Tuesday 08, September 2026', 'Tuesday 08, September 2025'),
    ('Rosehill Gardens: Test Club', 'Wrong Track: Test Club'),
    ('<b>Timing Method:</b> Electronic', '<b>Timing Method:</b> Electronic INTERIM RESULTS'),
    ('including emergencies) 3', 'including emergencies) 4'),
    ('<a href="#Race2">2</a>', ''),
    ('<th>Marg(L)</th>', '<th>Changed column</th>'),
    ('<td>1.25</td>', '<td>unknown margin</td>'),
])
def test_identity_and_completeness_fail_closed(old, new):
    with pytest.raises((MeetingError, ValueError)):
        parse(fixture().replace(old.encode(), new.encode()))


def test_truncated_rows_cannot_disappear():
    with pytest.raises(MeetingError, match='width'):
        parse(fixture().replace(b'<td>1.25</td><td>0</td>', b'<td>1.25</td>'))


def test_pipeline_saves_all_observations_and_is_idempotent(store):
    meeting = parse()
    first = ingest_meeting(store, meeting, raw_payload_hash='source-hash')
    assert (first['inserted'], first['identity_quarantined'], first['quality_quarantined']) == (2, 1, 1)
    assert first['parsed_rows'] == sum(first[k] for k in ('inserted','unchanged','identity_quarantined','quality_quarantined'))
    events = [tuple(row) for row in store.connection.execute('SELECT * FROM fitness_events ORDER BY event_id')]
    later = parse(collected_at='2026-09-13T03:00:00+00:00')
    rerun = ingest_meeting(store, later, raw_payload_hash='new-transport-hash')
    assert rerun['inserted'] == 0 and rerun['unchanged'] == 2
    assert events == [tuple(row) for row in store.connection.execute('SELECT * FROM fitness_events ORDER BY event_id')]
    for table, count in [('fitness_events', 2), ('fitness_identity_quarantine', 1), ('fitness_quality_quarantine', 1)]:
        assert store.connection.execute('SELECT count(*) FROM ' + table).fetchone()[0] == count
    assert store.connection.execute('PRAGMA foreign_key_check').fetchall() == []


def test_changed_result_is_quarantined_without_overwriting(store):
    meeting = parse()
    ingest_meeting(store, meeting, raw_payload_hash='source-hash')
    changed = copy.deepcopy(meeting)
    changed['rows'][0]['official_time_seconds'] = 59.5
    result = ingest_meeting(store, changed, raw_payload_hash='revision-hash')
    assert result['unchanged'] == 1 and result['quality_quarantined'] == 2
    assert store.connection.execute("SELECT official_time_seconds FROM fitness_events WHERE horse_id='h1'").fetchone()[0] == 60


def test_database_failure_rolls_back_events_and_quarantine(store):
    store.connection.execute("""CREATE TRIGGER fail_second BEFORE INSERT ON fitness_events
        WHEN NEW.horse_id='h2' BEGIN SELECT RAISE(ABORT,'synthetic write failure'); END""")
    with pytest.raises(sqlite3.IntegrityError):
        ingest_meeting(store, parse(), raw_payload_hash='source-hash')
    for table in ['fitness_events', 'fitness_identity_quarantine', 'fitness_quality_quarantine']:
        assert store.connection.execute('SELECT count(*) FROM ' + table).fetchone()[0] == 0


def test_provider_crosswalk_collision_and_name_disagreement_are_quarantined(store):
    from racing_engine.fitness_identity import link_rows
    meta = json.dumps({'racing_nsw': {'source_horse_id': 'duplicate'}})
    store.connection.execute('UPDATE horses SET detail_json=?', (meta,))
    result = link_rows(store, [{'source': 'racing_nsw', 'source_horse_id': 'duplicate', 'horse_name': 'Known Horse'}])
    assert result['quarantined_rows'][0]['quarantine_reason'] == 'duplicate_provider_identity'
    store.connection.execute("UPDATE horses SET detail_json='{}' WHERE horse_id='h2'")
    result = link_rows(store, [{'source': 'racing_nsw', 'source_horse_id': 'duplicate', 'horse_name': 'Second Horse'}])
    assert result['quarantined_rows'][0]['quarantine_reason'] == 'provider_name_disagreement'


def test_dangling_alias_is_not_a_durable_horse_match(store):
    from racing_engine.fitness_identity import link_rows
    store.connection.execute('INSERT INTO horse_aliases VALUES (?,?,?,?,?,?,?)',
        ('racing_nsw', 'Ghost Horse', 'missing-id', 'Ghost Horse', 'automatic', '{}', COLLECTED))
    result = link_rows(store, [{'source': 'racing_nsw', 'horse_name': 'Ghost Horse'}])
    assert result['quarantined_rows'][0]['quarantine_reason'] == 'no_registry_match'


def test_runner_link_cannot_reference_another_meeting():
    payload = fixture().replace(b'horsecode=known', b'horsecode=known&amp;Key=2025Sep08,NSW,Rosehill%20Gardens,Trial')
    with pytest.raises(MeetingError, match='runner_link_meeting_mismatch'):
        parse(payload)


def test_duplicate_horse_cannot_fill_two_result_rows():
    with pytest.raises(MeetingError, match='duplicate_source_horse'):
        parse(fixture().replace(b'horsecode=new', b'horsecode=known'))


def test_emergency_runner_number_preserves_source_label():
    payload = fixture().replace(b'<td>2</td><td>2</td>', b'<td>2</td><td>12e</td>')
    meeting = parse(payload)
    row = meeting['rows'][1]
    assert row['runner_number'] == 12
    assert row['detail']['source_runner_label'] == '12e'
    assert row['detail']['emergency'] is True


def test_lp_is_preserved_for_review_without_a_completed_event(store):
    payload = fixture().replace(b'<td>2</td><td>2</td>', b'<td>LP</td><td>2</td>')
    result = ingest_meeting(store, parse(payload), raw_payload_hash='lp-hash')
    assert result['advertised_starters'] == 3  # matches the source denominator
    assert result['inserted'] == 2
    assert result['identity_quarantined'] == 0
    assert result['quality_quarantined'] == 2  # one scratch, one unresolved LP


def test_abandoned_meeting_is_accounted_for_without_inventing_events(store):
    header = fixture().split(b'</header>')[0] + b'</header>'
    meeting = parse(header + b"<div class='Scratched'>Meeting Abandoned.</div>")
    result = ingest_meeting(store, meeting, raw_payload_hash='abandoned-hash')
    assert result['meeting_status'] == 'abandoned'
    assert result['parsed_rows'] == 0 and result['inserted'] == 0
    with pytest.raises(MeetingError, match='abandoned_meeting_has_result_rows'):
        parse(fixture() + b'<div>Meeting Abandoned.</div>')
