import copy
import pytest
from racing_engine.trial_profile_catalog import SCHEMA,parse_profile,install_profile
from racing_engine.fitness_identity import link_rows
from racing_engine.trial_meeting import MeetingError
from test_trial_meeting import store
NOW='2026-09-14T00:00:00+00:00'
PROFILE={'id':'p100','name':'New Horse','foalDate':'2021-09-01T00:00:00Z','sex':'Gelding'}
ANCHORS=[{'horse_name':'Sire/Dam/2021','provider_name':'New Horse','event_date':'2026-08-01'}]
ARCHIVE={'payload_hash':'synthetic','source_url':'https://www.racing.com/horses/new-horse-p100','collected_at':NOW}

def test_profile_requires_id_name_birth_evidence():
    assert parse_profile({'data':{'getHorseProfile':PROFILE}},'p100',ANCHORS,NOW)['name']=='New Horse'
    for change in [{'id':'different'},{'name':'Other Horse'},{'foalDate':'2026-09-01'}]:
        with pytest.raises(MeetingError):parse_profile({'data':{'getHorseProfile':{**PROFILE,**change}}},'p100',ANCHORS,NOW)

def test_profile_install_is_idempotent_and_links_provider_with_late_evidence(store):
    store.connection.executescript(SCHEMA)
    first=install_profile(store,PROFILE,ARCHIVE)
    assert first['created']==1 and install_profile(store,PROFILE,ARCHIVE)['inserted']==0
    row={'source':'racing_com','source_horse_id':'p100','horse_name':'Sire/Dam/2021','effective_at':'2026-09-13T00:00:00+00:00'}
    linked=link_rows(store,[row])['linked_rows'][0]
    assert linked['horse_id']==first['horse_id'] and linked['effective_at']==NOW
    with pytest.raises(MeetingError):install_profile(store,{**PROFILE,'id':'p101'},ARCHIVE)
    with pytest.raises(MeetingError):install_profile(store,{**PROFILE,'foalDate':'2020-09-01'},ARCHIVE)
