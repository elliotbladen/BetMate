"""Append evidence-backed identity, result, clock and participant-name resolutions."""
from __future__ import annotations
import argparse
from collections import defaultdict, Counter
from datetime import datetime
import json
from difflib import SequenceMatcher
from pathlib import Path
from .fitness_identity import link_rows
from .horse_identity import clean_name, identity_key
from .storage import RacingStore, utc_now
from .trial_calendar_expansion import digest,save,track_key
from .trial_meeting import validate_review_target

SCHEMA='''CREATE TABLE IF NOT EXISTS trial_data_resolutions (
 resolution_id TEXT PRIMARY KEY, observation_id TEXT NOT NULL REFERENCES trial_calendar_observations(observation_id),
 horse_id TEXT REFERENCES horses(horse_id), resolution_status TEXT NOT NULL,
 resolved_at TEXT NOT NULL, effective_at TEXT NOT NULL, detail_json TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS trial_data_resolutions_observation ON trial_data_resolutions(observation_id);
CREATE TRIGGER IF NOT EXISTS trial_data_resolutions_no_update BEFORE UPDATE ON trial_data_resolutions
 BEGIN SELECT RAISE(ABORT,'trial evidence is append-only'); END;
CREATE TRIGGER IF NOT EXISTS trial_data_resolutions_no_delete BEFORE DELETE ON trial_data_resolutions
 BEGIN SELECT RAISE(ABORT,'trial evidence is append-only'); END;
CREATE VIEW IF NOT EXISTS trial_current_resolutions AS
 SELECT * FROM (SELECT r.*,row_number() OVER (PARTITION BY observation_id ORDER BY resolved_at DESC,resolution_id DESC) AS revision_rank FROM trial_data_resolutions r) WHERE revision_rank=1;
DROP VIEW IF EXISTS trial_normalized_observations;
CREATE VIEW trial_normalized_observations AS
 SELECT o.observation_id,o.source_entry_id,o.source_horse_id,CASE WHEN r.resolution_id IS NOT NULL THEN r.horse_id ELSE o.horse_id END AS horse_id,
 o.horse_name,o.event_type,o.event_date,o.state,o.track,
 COALESCE(json_extract(r.detail_json,'$.official.heat_number'),o.heat_number) AS heat_number,
 CASE WHEN json_type(r.detail_json,'$.official')='object' THEN json_extract(r.detail_json,'$.official.finish_position') ELSE o.finish_position END AS finish_position,
 COALESCE(json_extract(r.detail_json,'$.official.field_size'),o.field_size) AS field_size,
 COALESCE(json_extract(r.detail_json,'$.official.distance_metres'),o.distance_metres) AS distance_metres,
 CASE WHEN json_type(r.detail_json,'$.official')='object' THEN json_extract(r.detail_json,'$.official.heat_time_seconds') ELSE json_extract(o.detail_json,'$.detail.heat_time_seconds') END AS heat_time_seconds,
 COALESCE(json_extract(r.detail_json,'$.official.jockey_name'),json_extract(o.detail_json,'$.jockey_name')) AS jockey_name,
 COALESCE(json_extract(r.detail_json,'$.official.trainer_name'),json_extract(o.detail_json,'$.trainer_name')) AS trainer_name,
 COALESCE(r.resolution_status,o.review_status) AS review_status,
 json_extract(r.detail_json,'$.identity_status') AS identity_status,
 json_extract(r.detail_json,'$.clock_status') AS clock_status,
 COALESCE(r.effective_at,o.observed_at) AS effective_at,o.source_url AS original_source_url,
 json_extract(r.detail_json,'$.official.source_url') AS official_source_url,
 r.detail_json AS resolution_detail_json
 FROM trial_calendar_observations o LEFT JOIN trial_current_resolutions r USING(observation_id);

'''

def name_key(name):return identity_key(clean_name('racing_com',name)[0])

def official_rows(c):
    rows=[]
    if c.execute("SELECT 1 FROM sqlite_master WHERE name='trial_official_observations'").fetchone():
        for r in c.execute('SELECT detail_json,payload_hash FROM trial_official_observations'):
            d=json.loads(r['detail_json'])
            # Older Racing NSW adapter rows stored participant names as strings;
            # preserve those immutable records while normalising them for review.
            for role in ('jockey','trainer'):
                if isinstance(d.get(role), str): d[role]={'name': d[role] or None, 'source_id': None}
            d.update(payload_hash=r['payload_hash'],jockey_name=(d.get('jockey') or {}).get('name'),trainer_name=(d.get('trainer') or {}).get('name'));rows.append(d)
    queries=["SELECT raw_json,payload_hash FROM fitness_events WHERE source='racing_nsw'",
      "SELECT raw_json,payload_hash FROM fitness_quality_quarantine WHERE source='racing_nsw'",
      "SELECT raw_json,NULL AS payload_hash FROM fitness_identity_quarantine WHERE source='racing_nsw'"]
    for query in queries:
        for r in c.execute(query):
            d=json.loads(r['raw_json']);detail=d.get('detail',{})
            d.update(state='NSW',heat_time_seconds=detail.get('heat_time_seconds'),payload_hash=d.get('raw_payload_hash') or detail.get('raw_payload_hash') or r['payload_hash'],
              observed_at=d.get('collected_at'),track=d.get('track_slug'))
            rows.append(d)
    return rows

def primary_match(row,candidates):
    """Agreeing official sources can corroborate; conflicting sources remain held."""
    local=[x for x in candidates if x['heat_number']==row['heat_number']]
    chosen=local or candidates
    if not local and row.get('finish_position') is not None:
        matching=[x for x in chosen if x.get('finish_position')==row['finish_position']]
        if matching:chosen=matching
    if not chosen:return None,'no_official_result_match'
    fields=('heat_number','distance_metres','finish_position','field_size','heat_time_seconds','result_status')
    cores={tuple(x.get(k) for k in fields) for x in chosen}
    if len(cores)>1:return None,'conflicting_or_ambiguous_official_results'
    best=sorted(chosen,key=lambda x:(x.get('source')=='racing_australia',x.get('observed_at') or ''),reverse=True)[0]
    if best['result_status'] in {'scr','scratched','dns'}:status='confirmed_nonstarter'
    elif best['result_status']!='finished':status='confirmed_source_nonfinish_status'
    elif best['heat_number']!=row['heat_number']:status='corrected_source_heat_assignment'
    elif any(row.get(k)!=best.get(k) for k in ('distance_metres','finish_position')):status='corrected_source_result'
    else:status='verified_against_official_result'
    return best,status

def reconcile(store):
    c=store.connection;c.executescript(SCHEMA);index=defaultdict(list)
    registry=defaultdict(list)
    for h in c.execute('SELECT horse_id,canonical_name FROM horses'):
        key=name_key(h['canonical_name']); registry[(key[:1],len(key)//3)].append((h['horse_id'],key))
    for row in official_rows(c):index[(row['event_date'],row['state'],track_key(row['track']),name_key(row['horse_name']))].append(row)
    observations=[dict(r) for r in c.execute('SELECT * FROM trial_calendar_observations')]
    rows=[]
    for r in observations:
        row=json.loads(r['detail_json']);row.pop('horse_id',None);row['_observation_id']=r['observation_id'];rows.append(row)
    linked=link_rows(store,rows);byid={r['_observation_id']:r for r in linked['linked_rows']+linked['quarantined_rows']}
    profiles={r['source_horse_id']:r['canonical_name'] for r in c.execute('SELECT source_horse_id,canonical_name FROM trial_provider_profiles')} if c.execute("SELECT 1 FROM sqlite_master WHERE name='trial_provider_profiles'").fetchone() else {}
    counts=Counter();inserted=0;now=utc_now()
    with c:
        for original in observations:
            row=byid[original['observation_id']];names={name_key(row['horse_name']),name_key(profiles.get(row.get('source_horse_id'),row['horse_name']))}
            candidates=[x for name in names for x in index.get((row['event_date'],row['state'],track_key(row['track']),name),[]) if row['event_type']=='official_trial']
            best,status=primary_match(row,candidates);hid=row.get('horse_id')
            # Composite fingerprint fallback: same date/venue/heat/result and
            # a unique near-name match can safely resolve legacy spelling drift.
            if not hid and best and best.get('horse_name'):
                target=name_key(best['horse_name']); pool=[]
                for bucket in range(max(0,len(target)//3-1),len(target)//3+2): pool.extend(registry.get((target[:1],bucket),[]))
                scores=sorted(((SequenceMatcher(None,target,k).ratio(),horse_id) for horse_id,k in pool),reverse=True)
                if scores and scores[0][0]>=0.95 and (len(scores)==1 or scores[0][0]-scores[1][0]>=0.02):
                    hid=scores[0][1]; row['identity_method']='composite_fingerprint'; row['identity_confidence']=scores[0][0]
            detail={'identity_status':'linked' if hid else 'unmatched','identity_method':row.get('identity_method'),'original_review_status':original['review_status']}
            if best:
                keys=('source','source_url','payload_hash','observed_at','horse_name','heat_number','distance_metres','finish_position','field_size','beaten_margin','result_status','jockey_name','trainer_name','heat_time_seconds','timing_method','surface','going','jockey','trainer')
                detail['official']={k:best.get(k) for k in keys};detail['clock_scope']='heat_winner'
                detail['clock_status']='verified_official_clock' if best.get('heat_time_seconds') else 'not_reported_by_official_source'
                detail['names_status']='official_event_participants'
            else:
                detail['clock_status']='not_independently_verified';detail['names_status']='source_spelling_preserved'
                if status=='no_official_result_match' and row['detail'].get('source_position_code')==109:
                    status='confirmed_nonstarter';detail['status_evidence']='Racing.com browser audit 2026-09-14: result code 109 displayed SCR'
            detail['result_status']=status
            effective=max([row['effective_at']]+([best['observed_at']] if best and best.get('observed_at') else []),key=datetime.fromisoformat)
            resolution_id=digest([original['observation_id'],hid,status,detail,effective])
            inserted+=c.execute('INSERT OR IGNORE INTO trial_data_resolutions VALUES (?,?,?,?,?,?,?)',(resolution_id,original['observation_id'],hid,status,now,effective,json.dumps(detail,sort_keys=True))).rowcount
            counts[status]+=1
            if not hid:counts['unmatched_identity']+=1
            if best and best.get('heat_time_seconds'):counts['official_clock_verified']+=1
    return {'observations':len(observations),'inserted_resolutions':inserted,'counts':dict(counts),'integrity_check':c.execute('PRAGMA integrity_check').fetchone()[0],'foreign_key_violations':len(c.execute('PRAGMA foreign_key_check').fetchall())}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('database','registry-database','report'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();validate_review_target(a.database,a.registry_database);store=RacingStore(a.database)
    try:result=reconcile(store);save(a.report,result);print(json.dumps(result),flush=True)
    finally:store.close()

if __name__=='__main__':main()
