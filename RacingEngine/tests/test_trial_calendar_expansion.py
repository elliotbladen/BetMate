import copy
import pytest
from racing_engine.trial_calendar_expansion import SCHEMA,parse_meeting,install_meeting,validate_calendar
from racing_engine.trial_meeting import MeetingError
from test_trial_meeting import store

ITEM={'id':'m1','venue':'Synthetic Park','date':'2026-08-11','state':'VIC','isTrial':False,'isJumpOut':True,'meetUrl':'https://www.racing.com/form/2026-08-11/synthetic-park-jumpout'}
NOW='2026-09-13T04:00:00+00:00'

def payload():
    return {'data':{'getNoCacheRacesForMeet':[{'id':'r1','raceNumber':1,'distance':'1000m','meet':{k:ITEM[k] for k in ('id','venue','date','state')},'trackCondition':'Soft','formRaceEntries':[
    {'id':'e1','horseName':'Known Horse','horse':{'id':'p1','fullName':'Known Horse'},'position':1,'winningTime':'6325'},
    {'id':'e2','horseName':'Second Horse','horse':{'id':'p2','fullName':'Second Horse'},'position':2,'winningTime':'6325'}]}]}}

def test_jumpout_time_and_all_runners():
    rows=parse_meeting(payload(),ITEM,NOW)
    assert len(rows)==2 and rows[0]['event_type']=='jumpout'
    assert rows[0]['official_time_seconds']==63.25
    assert rows[1]['official_time_seconds'] is None
    assert rows[1]['field_size']==2


def test_unknown_status_not_position_or_starter_count():
    p=payload();p['data']['getNoCacheRacesForMeet'][0]['formRaceEntries'][1]['position']=104
    rows=parse_meeting(p,ITEM,NOW)
    assert rows[1]['finish_position'] is None
    assert all(r['field_size'] is None for r in rows)
    assert rows[1]['detail']['source_position_code']==104


def test_wrong_meeting_and_duplicate_runner_rejected():
    p=payload();p['data']['getNoCacheRacesForMeet'][0]['meet']['date']='2025-08-11'
    with pytest.raises(MeetingError):parse_meeting(p,ITEM,NOW)
    p=payload();p['data']['getNoCacheRacesForMeet'][0]['formRaceEntries'][1]['id']='e1'
    with pytest.raises(MeetingError):parse_meeting(p,ITEM,NOW)


def test_daily_calendar_checks_date_and_preserves_duplicate_venue_ids():
    a=copy.deepcopy(ITEM);a['id']='other'
    data={'data':{'GetMeetingByDate':[ITEM,a]}}
    assert len(validate_calendar(data,'2026-08-11',['VIC'])[0])==2
    with pytest.raises(MeetingError):validate_calendar(data,'2026-08-12',['VIC'])


def test_replay_and_conflicting_results_are_preserved(store):
    store.connection.executescript(SCHEMA)
    rows=parse_meeting(payload(),ITEM,NOW)
    first=install_meeting(store,rows,'original')
    assert first['accepted_inserted']==2
    assert install_meeting(store,rows,'original')['accepted_inserted']==0
    p=payload();p['data']['getNoCacheRacesForMeet'][0]['formRaceEntries'][0]['position']=2
    result=install_meeting(store,parse_meeting(p,ITEM,NOW),'changed')
    assert result['held']==1 and result['accepted_inserted']==0
    assert store.connection.execute('SELECT count(*) FROM fitness_events').fetchone()[0]==2


def test_empty_placeholder_heats_and_ambiguous_numbering(store):
    p=payload(); races=p['data']['getNoCacheRacesForMeet']
    empty=copy.deepcopy(races[0]);empty['formRaceEntries']=[];races.append(empty)
    assert len(parse_meeting(p,ITEM,NOW))==2
    other=copy.deepcopy(races[0]);other['id']='other'
    for e in other['formRaceEntries']:e['id']+='other'
    races.append(other)
    rows=parse_meeting(p,ITEM,NOW)
    assert len(rows)==4 and all(r['detail']['ambiguous_heat_number'] for r in rows)
    store.connection.executescript(SCHEMA)
    assert install_meeting(store,rows,'source')['accepted_inserted']==0

def test_discovery_reuses_verified_archive_with_new_state_filter(tmp_path,monkeypatch):
    import hashlib,json,sys
    import racing_engine.trial_calendar_expansion as module
    old=tmp_path/'old';old.mkdir();new=tmp_path/'new'
    raw=json.dumps({'data':{'GetMeetingByDate':[ITEM]}}).encode();archive=tmp_path/'calendar.json';archive.write_bytes(raw)
    cached={'date':ITEM['date'],'status':'verified','meetings':[],'excluded':[ITEM],
      'archive':{'payload_path':str(archive),'payload_hash':hashlib.sha256(raw).hexdigest()}}
    (old/('calendar_'+ITEM['date']+'.json')).write_text(json.dumps(cached))
    args=['collect','--database',str(tmp_path/'review.sqlite'),'--registry-database',str(tmp_path/'registry.sqlite'),
      '--archive',str(tmp_path/'raw'),'--run-directory',str(new),'--from-date',ITEM['date'],'--to-date',ITEM['date'],
      '--states','VIC','--reuse-run',str(old),'--discovery-only']
    monkeypatch.setattr(sys,'argv',args)
    def network_forbidden(*args,**kwargs):raise AssertionError('cached discovery must not request the source')
    monkeypatch.setattr(module,'graphql_request',network_forbidden)
    module.main();plan=json.loads((new/'plan.json').read_text())
    assert plan['days_verified']==1 and plan['meetings']==[ITEM]
    assert not (tmp_path/'review.sqlite').exists()
