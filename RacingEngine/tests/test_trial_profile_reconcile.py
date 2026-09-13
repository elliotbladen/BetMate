import hashlib
import json

import pytest

from racing_engine.trial_ingest import archive_payload
from racing_engine.trial_meeting import MeetingError, ingest_meeting
from racing_engine.trial_profile_reconcile import reconcile
from racing_engine.trial_profiles import SCHEMA, install_profile, profile_url
from test_trial_meeting import store, fixture as meeting_html, parse as meeting, URL, COLLECTED
from test_trial_profiles import fixture as profile_html, parse as profile


def setup_run(store,tmp_path):
    store.connection.executescript(SCHEMA)
    ingest_meeting(store,meeting(),raw_payload_hash='initial')
    # Use the real archive digest on the initial events, exactly as the importer does.
    # The payload hash itself is transport provenance, excluded from event semantics.
    pp=tmp_path/'profiles'; pp.mkdir()
    mp=tmp_path/'meetings'; mp.mkdir()
    raw=tmp_path/'raw'
    p=profile()
    a=archive_payload(raw,source_id='racing_nsw_profiles',source_url=profile_url('new'),payload=profile_html(),collected_at=p['observed_at'])
    install_profile(store,p,a['payload_hash'])
    (pp/'plan.json').write_text(json.dumps({'from_date':p['from_date'],'to_date':p['to_date'],'horses':[{'code':'new','names':['New Horse']}]}))
    (pp/(hashlib.sha256(b'new').hexdigest()+'.json')).write_text(json.dumps({'status':'verified','archive':a}))
    ma=archive_payload(raw,source_id='racing_nsw',source_url=URL,payload=meeting_html(),collected_at=COLLECTED)
    item={'date':'2026-09-08','track':'Rosehill Gardens','url':URL}
    (mp/'plan.json').write_text(json.dumps({'meetings':[item],'excluded_other_states':[]}))
    (mp/'meeting_000.json').write_text(json.dumps({**item,'archive':ma}))
    return dict(profile_directory=pp,meeting_directory=mp,archive_root=raw)


def test_reconcile_and_repeat_preserve_originals(store,tmp_path):
    args=setup_run(store,tmp_path)
    first=reconcile(store,run_directory=tmp_path/'first',**args)
    assert first['fitness_events']==3
    assert first['outstanding_identity_quarantine']==0
    assert first['new_resolutions']==1
    assert first['original_events_preserved']==2
    second=reconcile(store,run_directory=tmp_path/'second',**args)
    assert second['new_resolutions']==0
    assert second['original_events_preserved']==3
    assert second['fitness_quality_quarantine']==1


def test_corrupt_profile_archive_blocks_promotion(store,tmp_path):
    args=setup_run(store,tmp_path)
    path=tmp_path/'profiles'/(hashlib.sha256(b'new').hexdigest()+'.json')
    report=json.loads(path.read_text()); report['archive']['payload_hash']='wrong'; path.write_text(json.dumps(report))
    with pytest.raises(MeetingError,match='profile_archive_hash_mismatch'):
        reconcile(store,run_directory=tmp_path/'failed',**args)
    assert store.connection.execute('SELECT count(*) FROM fitness_events').fetchone()[0]==2


def test_failed_revalidation_of_installed_profile_blocks_replay(store,tmp_path):
    args=setup_run(store,tmp_path)
    path=tmp_path/'profiles'/(hashlib.sha256(b'new').hexdigest()+'.json')
    report=json.loads(path.read_text()); report['status']='failed'; path.write_text(json.dumps(report))
    with pytest.raises(MeetingError,match='installed_profile_failed_revalidation'):
        reconcile(store,run_directory=tmp_path/'failed',**args)
    assert store.connection.execute('SELECT count(*) FROM fitness_events').fetchone()[0]==2
