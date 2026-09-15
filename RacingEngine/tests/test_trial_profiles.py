import copy
import pytest
from racing_engine.trial_profiles import SCHEMA, install_profile, parse_profile, profile_url
from racing_engine.trial_meeting import MeetingError
from test_trial_meeting import store


def fixture(name='New Horse'):
    return f'''<table class="horse-search-details"><tr><td>{name} 4yo Bay Gelding D.O.B: 01-Oct-2022 by Test Sire from Test Dam View Pedigree Report</td></tr></table>
    <table class="horse-search-details"><tr><td>OWNER MUST NOT BE STORED</td></tr></table>
    <table class="horse-last-start"><tr><td class="Pos">T 2nd of 2</td><td><a href="Meeting.aspx?meetcode=synthetic#Race1">TEST 08Sep26</a> 900m OPEN-BT</td></tr>
    <tr><td class="Pos">1st of 8</td><td>Race result</td></tr></table>'''.encode()


def parse(payload=None, **kwargs):
    args = dict(code='new',expected_names=['New Horse'],source_url=profile_url('new'),observed_at='2026-09-13T04:00:00+00:00',from_date='2023-09-13',to_date='2026-09-12')
    args.update(kwargs)
    return parse_profile(payload or fixture(),**args)


def test_profile_identity_and_trial_only():
    p=parse()
    assert p['birth_date']=='2022-10-01'
    assert len(p['history'])==1
    assert p['history'][0]['finish_position']==2
    assert 'OWNER' not in str(p)
    assert parse(from_date='2026-09-09')['history']==[]


@pytest.mark.parametrize('kwargs', [dict(expected_names=['Other Horse']),dict(code='wrong'),dict(observed_at='2026-09-13'),dict(to_date='2027-01-01')])
def test_reject_wrong_identity_and_time(kwargs):
    with pytest.raises(MeetingError): parse(**kwargs)


def test_bad_history_fails_closed():
    with pytest.raises(MeetingError): parse(fixture().replace(b'#Race1', b'#Unknown'))
    with pytest.raises(MeetingError): parse(fixture().replace(b'2nd of 2', b'9th of 2'))


def test_install_and_replay_preserve_original(store):
    store.connection.executescript(SCHEMA)
    p=parse()
    result=install_profile(store,p,'hash')
    assert result['new_horse'] and result['history_inserted']==1
    replay=install_profile(store,p,'hash')
    assert not replay['new_horse'] and replay['history_inserted']==0
    assert store.connection.execute('SELECT count(*) FROM trial_profile_evidence').fetchone()[0]==1
    conflict=copy.deepcopy(p); conflict['birth_date']='2021-10-01'
    with pytest.raises(MeetingError): install_profile(store,conflict,'changed')
    assert store.connection.execute('SELECT birth_date FROM trial_profile_evidence').fetchone()[0]=='2022-10-01'


def test_resolve_only_after_event_installed_with_current_availability(store):
    from racing_engine.trial_profiles import record_resolutions
    from racing_engine.trial_meeting import ingest_meeting
    from test_trial_meeting import parse as parse_meeting
    store.connection.executescript(SCHEMA)
    meeting=parse_meeting()
    assert ingest_meeting(store,meeting,raw_payload_hash='meeting')['identity_quarantined']==1
    p=parse()
    install_profile(store,p,'profile')
    assert record_resolutions(store)==0
    result=ingest_meeting(store,meeting,raw_payload_hash='meeting')
    assert result['inserted']==1 and result['unchanged']==2
    assert record_resolutions(store)==1
    assert record_resolutions(store)==0
    assert store.connection.execute('SELECT count(*) FROM fitness_identity_quarantine').fetchone()[0]==1
    event=store.connection.execute('SELECT effective_at FROM fitness_events WHERE horse_id=(SELECT horse_id FROM trial_profile_evidence)').fetchone()
    assert event[0]==p['observed_at']


def test_different_provider_cannot_claim_existing_verified_horse(store):
    store.connection.executescript(SCHEMA)
    p=parse(); install_profile(store,p,'profile')
    other=copy.deepcopy(p); other['source_horse_id']='different'
    with pytest.raises(MeetingError,match='conflicting_registry_profile'):
        install_profile(store,other,'other')


def test_profile_cannot_resolve_a_different_meeting_result(store):
    from racing_engine.trial_meeting import ingest_meeting
    from test_trial_meeting import parse as parse_meeting
    store.connection.executescript(SCHEMA)
    ingest_meeting(store,parse_meeting(),raw_payload_hash='meeting')
    p=parse(); p['history'][0]['finish_position']=1
    with pytest.raises(MeetingError,match='profile_history_meeting_disagreement'):
        install_profile(store,p,'profile')
    assert store.connection.execute('SELECT count(*) FROM trial_profile_evidence').fetchone()[0]==0


def test_evidence_tables_are_append_only(store):
    import sqlite3
    store.connection.executescript(SCHEMA)
    install_profile(store,parse(),'profile')
    with pytest.raises(sqlite3.IntegrityError,match='append-only'):
        store.connection.execute('DELETE FROM trial_history_observations')


@pytest.mark.parametrize('label,status',[('Failed to Finish','dnf'),('Lost Rider','lr')])
def test_written_non_finish_labels(label,status):
    p=parse(fixture().replace(b'2nd',label.encode()))
    assert p['history'][0]['finish_position'] is None
    assert p['history'][0]['result_status']==status
