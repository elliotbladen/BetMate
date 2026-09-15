from racing_engine.trial_data_reconcile import primary_match

def official(**kw):
    return dict(heat_number=4,distance_metres=800,finish_position=1,field_size=7,heat_time_seconds=48.98,result_status='finished',source='racing_australia',**kw)

def test_wrong_heat_is_resolved_only_by_unambiguous_official_event():
    row={'heat_number':6,'distance_metres':800,'finish_position':1}
    best,status=primary_match(row,[official()])
    assert status=='corrected_source_heat_assignment' and best['heat_number']==4
    other=official();other['heat_number']=7
    assert primary_match(row,[official(),other])==(None,'conflicting_or_ambiguous_official_results')

def test_conflicting_clocks_are_held_and_scratch_is_not_a_finish():
    row={'heat_number':4,'distance_metres':800,'finish_position':1}
    changed=official();changed['heat_time_seconds']=49.1
    assert primary_match(row,[official(),changed])[0] is None
    scratch=official();scratch.update(result_status='scr',finish_position=None)
    assert primary_match(row,[scratch])[1]=='confirmed_nonstarter'

from test_trial_meeting import store
from test_trial_calendar_expansion import payload,ITEM,NOW
from racing_engine.trial_calendar_expansion import SCHEMA,parse_meeting,install_meeting
from racing_engine.trial_data_reconcile import reconcile

def test_resolution_replay_preserves_original_evidence(store):
    store.connection.executescript(SCHEMA)
    install_meeting(store,parse_meeting(payload(),ITEM,NOW),'synthetic')
    before=[tuple(r) for r in store.connection.execute('SELECT * FROM trial_calendar_observations')]
    assert reconcile(store)['inserted_resolutions']==2
    assert reconcile(store)['inserted_resolutions']==0
    assert before==[tuple(r) for r in store.connection.execute('SELECT * FROM trial_calendar_observations')]
    row=store.connection.execute('SELECT * FROM trial_normalized_observations LIMIT 1').fetchone()
    assert row['clock_status']=='not_independently_verified' and row['identity_status']=='linked'

def test_cross_heat_scratch_does_not_hide_uniquely_corroborated_finish():
    row={'heat_number':14,'finish_position':4,'distance_metres':815}
    result=official();result.update(heat_number=13,finish_position=4,distance_metres=815)
    scratch=official();scratch.update(result_status='scr',finish_position=None)
    best,status=primary_match(row,[scratch,result])
    assert status=='corrected_source_heat_assignment' and best['heat_number']==13

def test_new_identity_conflict_does_not_retain_previous_accepted_link(store):
    from racing_engine.trial_profile_catalog import SCHEMA as PROFILE_SCHEMA
    store.connection.executescript(SCHEMA+PROFILE_SCHEMA)
    install_meeting(store,parse_meeting(payload(),ITEM,NOW),'synthetic')
    store.connection.execute('INSERT INTO trial_provider_profiles VALUES (?,?,?,?,?,?,?,?)',('p1','h2','Second Horse','2021-01-01','synthetic','https://example.test/profile',NOW,'{}'))
    store.connection.commit();reconcile(store)
    row=store.connection.execute("SELECT horse_id,identity_status FROM trial_normalized_observations WHERE source_entry_id='e1'").fetchone()
    assert row['horse_id'] is None and row['identity_status']=='unmatched'
    assert store.connection.execute("SELECT horse_id FROM trial_calendar_observations WHERE source_entry_id='e1'").fetchone()[0]=='h1'
