"""Cache public horse identity evidence for preparation records; no rating calculations."""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import sqlite3
from collections import defaultdict, Counter
from datetime import date, datetime
from pathlib import Path
from .racing_com import graphql_request
from .storage import RacingStore, utc_now
from .trial_source_requests import SourceGate, SourceAccessStopped, bounded_map
from .trial_ingest import archive_payload
from .trial_meeting import MeetingError, validate_review_target
from .trial_calendar_expansion import save
from .horse_identity import clean_name, identity_key, durable_id
from .fitness_identity import _candidates, _provider_ids

# Subset of the public horse page request. Owners, silks and commercial statistics omitted.
QUERY='''query getHorseProfile($horseId: ID!) {
 getHorseProfile(id: $horseId) {
  id name sex country foalDate damHorseName sireHorseName lastUpdated
  horseDam { id name country } horseSire { id name country }
  trainer { id fullName name }
 }
}'''
SCHEMA='''CREATE TABLE IF NOT EXISTS trial_provider_profiles (
 source_horse_id TEXT PRIMARY KEY, horse_id TEXT NOT NULL REFERENCES horses(horse_id),
 canonical_name TEXT NOT NULL, birth_date TEXT NOT NULL, payload_hash TEXT NOT NULL,
 source_url TEXT NOT NULL, observed_at TEXT NOT NULL, profile_json TEXT NOT NULL);
CREATE TRIGGER IF NOT EXISTS trial_provider_profiles_no_update BEFORE UPDATE ON trial_provider_profiles
 BEGIN SELECT RAISE(ABORT,'trial evidence is append-only'); END;
CREATE TRIGGER IF NOT EXISTS trial_provider_profiles_no_delete BEFORE DELETE ON trial_provider_profiles
 BEGIN SELECT RAISE(ABORT,'trial evidence is append-only'); END;
'''

def name_key(value):return identity_key(clean_name('racing_com',value)[0])

def parse_profile(payload, code, anchors, observed_at):
    if not anchors:raise MeetingError('profile_requires_trial_anchors')
    p=payload.get('data',{}).get('getHorseProfile')
    if payload.get('errors') or not isinstance(p,dict) or str(p.get('id'))!=code:
        raise MeetingError('profile_identity_mismatch')
    name=p.get('name')
    if not isinstance(name,str) or len(name_key(name))<3:raise MeetingError('profile_missing_name')
    try:born=date.fromisoformat(p['foalDate'][:10]);observed=datetime.fromisoformat(observed_at)
    except (TypeError,KeyError,ValueError):raise MeetingError('profile_missing_birth_date')
    if observed.tzinfo is None or not 0<(observed.date()-born).days<40*366:
        raise MeetingError('profile_invalid_birth_date')
    for anchor in anchors:
        if born.isoformat()>=anchor['event_date']:raise MeetingError('profile_born_after_event')
        # A breeding placeholder in the historical entry can differ from the current
        # registered name, but the nested horse identity must corroborate the profile.
        if name_key(anchor.get('provider_name') or anchor['horse_name'])!=name_key(name):
            raise MeetingError('profile_name_disagreement')
    return {k:p.get(k) for k in ('id','name','sex','country','foalDate','damHorseName','sireHorseName','horseDam','horseSire','trainer','lastUpdated')}

def install_profile(store,p,archive):
    c=store.connection;code=str(p['id']);born=p['foalDate'][:10]
    old=c.execute('SELECT * FROM trial_provider_profiles WHERE source_horse_id=?',(code,)).fetchone()
    if old:
        if old['birth_date']!=born or name_key(old['canonical_name'])!=name_key(p['name']):raise MeetingError('existing_profile_conflict')
        return {'horse_id':old['horse_id'],'created':0,'inserted':0}
    names=_candidates(store);providers=_provider_ids(store)
    ids=providers.get(('racing_com',code),set());matches=names.get(name_key(p['name']),set())
    if len(ids)>1 or len(matches)>1 or (ids and matches and ids!=matches):raise MeetingError('ambiguous_registry_identity')
    hid=next(iter(ids or matches),None);created=int(hid is None)
    if hid:
        if any(provider=='racing_com' and existing_code!=code and hid in values for (provider,existing_code),values in providers.items()):raise MeetingError('multiple_provider_ids_for_horse')
        known=[r[0] for r in c.execute('SELECT birth_date FROM trial_provider_profiles WHERE horse_id=?',(hid,))]
        if c.execute("SELECT 1 FROM sqlite_master WHERE name='trial_profile_evidence'").fetchone():
            known += [r[0] for r in c.execute('SELECT birth_date FROM trial_profile_evidence WHERE horse_id=?',(hid,))]
        if any(v!=born for v in known):raise MeetingError('registry_birth_date_conflict')
        # Two distinct provider IDs require explicit equivalence evidence, not a name match.
        if c.execute('SELECT 1 FROM trial_provider_profiles WHERE horse_id=? AND source_horse_id<>?',(hid,code)).fetchone():raise MeetingError('multiple_provider_ids_for_horse')
    now=utc_now()
    with c:
        if not hid:
            key='racing_com:'+code;hid=durable_id(key)
            c.execute('INSERT INTO horses (horse_id,canonical_name,identity_key,identity_status,detail_json,created_at,updated_at) VALUES (?,?,?,?,?,?,?)',
              (hid,clean_name('racing_com',p['name'])[0],key,'reviewed',json.dumps({'identity_basis':'public_profile_id_name_birth_date'}),now,now))
        c.execute('INSERT INTO trial_provider_profiles VALUES (?,?,?,?,?,?,?,?)',(code,hid,p['name'],born,archive['payload_hash'],archive['source_url'],archive['collected_at'],json.dumps(p,sort_keys=True)))
    return {'horse_id':hid,'created':created,'inserted':1}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('database','registry-database','archive','run-directory'):parser.add_argument('--'+key,type=Path,required=True)
    parser.add_argument('--download-only',action='store_true')
    parser.add_argument('--cached-only',action='store_true')
    a=parser.parse_args();validate_review_target(a.database,a.registry_database);a.run_directory.mkdir(parents=True,exist_ok=True)
    c=sqlite3.connect('file:'+str(a.database.resolve())+'?mode=ro',uri=True);c.row_factory=sqlite3.Row
    anchors=defaultdict(list)
    for r in c.execute('SELECT source_horse_id,horse_name,event_date,detail_json FROM trial_calendar_observations WHERE source_horse_id IS NOT NULL'):
        d=json.loads(r['detail_json']);anchors[r['source_horse_id']].append({'horse_name':r['horse_name'],'provider_name':d['detail'].get('provider_horse_name'),'event_date':r['event_date']})
    c.close()
    plan_path=a.run_directory/'plan.json'
    if plan_path.exists():
        plan=json.loads(plan_path.read_text())
        if any(code not in anchors for code in plan['codes']):raise MeetingError('profile_plan_anchor_missing')
        anchors={code:anchors[code] for code in plan['codes']}
    else:
        plan={'horses':len(anchors),'source':'trial_calendar_observations','codes':sorted(anchors)};save(plan_path,plan)
    scope_expected=len(anchors)
    if a.cached_only:
        anchors={code:values for code,values in anchors.items() if (a.run_directory/('horse_'+code+'.json')).exists() and json.loads((a.run_directory/('horse_'+code+'.json')).read_text()).get('archive')}
    gate=SourceGate(a.run_directory/'access_block.json')
    def collect(code):
        path=a.run_directory/('horse_'+code+'.json');r={'code':code,'status':'failed'}
        try:
            prior=json.loads(path.read_text()) if path.exists() else {}
            archive=prior.get('archive')
            if archive:
                raw=Path(archive['payload_path']).read_bytes()
                if hashlib.sha256(raw).hexdigest()!=archive['payload_hash']:raise MeetingError('profile_archive_hash_mismatch')
                payload=json.loads(raw)
            else:
                payload=gate.call(graphql_request,QUERY,{'horseId':code})
                url='https://www.racing.com/horses/'+re.sub('[^a-z0-9]+','-',anchors[code][0]['horse_name'].lower()).strip('-')+'-'+code
                archive=archive_payload(a.archive,source_id='racing_com_horse_profiles',source_url=url,payload=json.dumps(payload,sort_keys=True).encode(),collected_at=utc_now())
            r['archive']=archive;p=parse_profile(payload,code,anchors[code],archive['collected_at']);r.update(status='verified',profile=p)
        except SourceAccessStopped:raise
        except Exception as exc:r['error']=str(exc) if isinstance(exc,MeetingError) else type(exc).__name__
        save(path,r);return r
    reports=[];store=None
    if not a.download_only:store=RacingStore(a.database);store.connection.executescript(SCHEMA)
    for n,r in enumerate(bounded_map(collect,sorted(anchors)),1):
        if store and r['status']=='verified':
            try:r.update(install_profile(store,r['profile'],r['archive']),status='installed')
            except MeetingError as exc:r.update(status='held',error=str(exc))
            save(a.run_directory/('horse_'+r['code']+'.json'),r)
        reports.append(r)
        if n%100==0:print(json.dumps({'processed':n,'of':len(anchors),'statuses':dict(Counter(x['status'] for x in reports))}),flush=True)
    if store:store.close()
    summary={'expected':scope_expected,'processed':len(reports),'statuses':dict(Counter(x['status'] for x in reports)),'errors':dict(Counter(x.get('error') for x in reports if x.get('error'))),'created':sum(x.get('created',0) for x in reports)}
    save(a.run_directory/'summary.json',summary);print(json.dumps(summary),flush=True)

if __name__=='__main__':main()
