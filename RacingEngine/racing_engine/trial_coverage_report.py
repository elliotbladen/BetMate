"""Audit saved calendar/result checkpoints without making network requests."""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
from .trial_calendar_expansion import save,digest
from .trial_meeting import MeetingError,validate_review_target
from .storage import utc_now

SCHEMA='''CREATE TABLE IF NOT EXISTS trial_meeting_resolutions (
 resolution_id TEXT PRIMARY KEY, source_meeting_id TEXT NOT NULL, resolution_status TEXT NOT NULL,
 canonical_source_meeting_id TEXT, observed_at TEXT NOT NULL, detail_json TEXT NOT NULL);
CREATE TRIGGER IF NOT EXISTS trial_meeting_resolutions_no_update BEFORE UPDATE ON trial_meeting_resolutions
 BEGIN SELECT RAISE(ABORT,'trial evidence is append-only'); END;
CREATE TRIGGER IF NOT EXISTS trial_meeting_resolutions_no_delete BEFORE DELETE ON trial_meeting_resolutions
 BEGIN SELECT RAISE(ABORT,'trial evidence is append-only'); END;
'''

def verified_payload(report):
    archive=report['archive'];raw=Path(archive['payload_path']).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=archive['payload_hash']:raise MeetingError('coverage_archive_hash_mismatch')
    return json.loads(raw)['data']['getNoCacheRacesForMeet']

def duplicate_target(report,reports):
    item=report['meeting'];same=[r for r in reports if r['meeting']['id']!=item['id'] and r.get('status')=='imported' and
      all(r['meeting'][k]==item[k] for k in ['date','state','venue','meetUrl','isTrial','isJumpOut'])]
    if len(same)!=1:return None
    empty=verified_payload(report);populated=verified_payload(same[0])
    if any(r['formRaceEntries'] for r in empty):raise MeetingError('empty_listing_contains_results')
    if not populated or not any(r['formRaceEntries'] for r in populated):return None
    if not {r['raceNumber'] for r in empty}<={r['raceNumber'] for r in populated}:return None
    return same[0]

def build(database,plan_path,runs):
    plan=json.loads(plan_path.read_text());reports={};access_blocks=[]
    for root in runs:
        if (root/'access_block.json').exists():access_blocks.append(json.loads((root/'access_block.json').read_text()))
        for path in root.glob('meeting_*.json'):
            r=json.loads(path.read_text());mid=r['meeting']['id']
            if r.get('archive') and (mid not in reports or reports[mid].get('status')=='failed'):reports[mid]=r
    c=sqlite3.connect(database);c.executescript(SCHEMA);empty=[]
    with c:
        for mid,r in reports.items():
            if r.get('status')!='no_results_published':continue
            target=duplicate_target(r,list(reports.values()))
            entry={'meeting':r['meeting'],'status':'duplicate_empty_source_listing' if target else 'unresolved_empty_source_meeting',
              'canonical_source_meeting_id':target['meeting']['id'] if target else None,
              'source_payload_hash':r['archive']['payload_hash'],'canonical_payload_hash':target['archive']['payload_hash'] if target else None}
            key=digest(entry);c.execute('INSERT OR IGNORE INTO trial_meeting_resolutions VALUES (?,?,?,?,?,?)',(key,mid,entry['status'],entry['canonical_source_meeting_id'],utc_now(),json.dumps(entry,sort_keys=True)));empty.append(entry)
    states={}
    for state in plan['settings']['states']:
        ids={m['id'] for m in plan['meetings'] if m['state']==state}
        states[state]={'calendar_meetings':len(ids),'cached_populated_meetings':sum(mid in reports and reports[mid].get('status')=='imported' for mid in ids),
          'coverage_status':'incomplete' if ids else 'no_calendar_entries; geographic coverage not independently established'}
    table_counts={table:c.execute('SELECT count(*) FROM '+table).fetchone()[0] for table in ['horses','fitness_events','trial_calendar_observations','trial_official_observations','trial_provider_profiles']}
    status_counts=dict(c.execute('SELECT resolution_status,count(*) FROM trial_current_resolutions GROUP BY resolution_status').fetchall())
    result={'status':'not_ready_for_signoff','window':{'from':plan['settings']['from_date'],'to':plan['settings']['to_date']},'calendar_days_expected':plan['days_expected'],'calendar_days_verified':plan['days_verified'],
      'calendar_meetings':len(plan['meetings']),'cached_meetings':len(reports),'states':states,'empty_meeting_resolutions':empty,'table_counts':table_counts,'observation_resolution_statuses':status_counts,
      'unmatched_observations':c.execute('SELECT count(*) FROM trial_current_resolutions WHERE horse_id IS NULL').fetchone()[0],
      'verified_clock_observations':c.execute("SELECT count(*) FROM trial_current_resolutions WHERE json_extract(detail_json,'$.clock_status')='verified_official_clock'").fetchone()[0],
      'official_participant_name_observations':c.execute("SELECT count(*) FROM trial_current_resolutions WHERE json_extract(detail_json,'$.names_status')='official_event_participants'").fetchone()[0],
      'identity_links_resolved':c.execute('SELECT count(*) FROM trial_current_resolutions r JOIN trial_calendar_observations o USING(observation_id) WHERE o.horse_id IS NULL AND r.horse_id IS NOT NULL').fetchone()[0],
      'recorded_access_blocks':access_blocks,
      'blockers':['National result/profile backfill incomplete','NT coverage has no Racing.com calendar entries and requires a primary-source archive','Remaining empty/ambiguous meetings and unverified clocks require further source evidence'],
      'integrity_check':c.execute('PRAGMA integrity_check').fetchone()[0],'foreign_key_violations':len(c.execute('PRAGMA foreign_key_check').fetchall())}
    c.close();return result

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ['database','registry-database','plan','report']:p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--run',type=Path,action='append',required=True);a=p.parse_args();validate_review_target(a.database,a.registry_database)
    result=build(a.database,a.plan,a.run);save(a.report,result);print(json.dumps({k:v for k,v in result.items() if k not in ['states','empty_meeting_resolutions']}),flush=True)

if __name__=='__main__':main()
