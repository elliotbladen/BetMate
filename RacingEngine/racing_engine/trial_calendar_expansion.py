"""Date-complete discovery of trial and jumpout meetings for the review database."""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path
from threading import Lock
from urllib.parse import urlparse

from .fitness_identity import link_rows
from .horse_identity import identity_key
from .racing_com import DATE_QUERY, QUERY, graphql_request, centiseconds, distance_metres, lengths
from .storage import RacingStore, utc_now
from .trial_ingest import archive_payload
from .trial_meeting import MeetingError, validate_review_target

VERSION = 'racing-com-preparation-calendar-v1'
SCHEMA = '''
CREATE TABLE IF NOT EXISTS trial_calendar_observations (
 observation_id TEXT PRIMARY KEY, source_entry_id TEXT NOT NULL, source_horse_id TEXT,
 horse_id TEXT REFERENCES horses(horse_id), horse_name TEXT NOT NULL, event_type TEXT NOT NULL,
 event_date TEXT NOT NULL, state TEXT NOT NULL, track TEXT NOT NULL, heat_number INTEGER NOT NULL,
 finish_position INTEGER, field_size INTEGER, listed_runners INTEGER NOT NULL,
 distance_metres INTEGER, source_url TEXT NOT NULL, observed_at TEXT NOT NULL,
 payload_hash TEXT NOT NULL, review_status TEXT NOT NULL, detail_json TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS trial_calendar_observations_horse_date ON trial_calendar_observations(horse_id,event_date);
CREATE TRIGGER IF NOT EXISTS trial_calendar_observations_no_update BEFORE UPDATE ON trial_calendar_observations
 BEGIN SELECT RAISE(ABORT,'trial evidence is append-only'); END;
CREATE TRIGGER IF NOT EXISTS trial_calendar_observations_no_delete BEFORE DELETE ON trial_calendar_observations
 BEGIN SELECT RAISE(ABORT,'trial evidence is append-only'); END;
'''


def save(path, value):
    tmp=path.with_suffix('.tmp'); tmp.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n'); tmp.replace(path)


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()


def validate_calendar(payload, day, states):
    if payload.get('errors') or not isinstance(payload.get('data',{}).get('GetMeetingByDate'),list):
        raise MeetingError('invalid_daily_calendar')
    included=[]; excluded=[]
    for item in payload['data']['GetMeetingByDate']:
        if item.get('date') != day:
            raise MeetingError('calendar_returned_wrong_date')
        if not item.get('isTrial') and not item.get('isJumpOut'):
            continue
        if not item.get('id') or not item.get('venue') or item.get('isTrial') == item.get('isJumpOut'):
            raise MeetingError('invalid_preparation_meeting_identity')
        url=urlparse(item.get('meetUrl') or '')
        if url.scheme!='https' or url.netloc!='www.racing.com' or not url.path.startswith('/form/'+day+'/'):
            raise MeetingError('invalid_meeting_source_url')
        (included if item.get('state') in states else excluded).append(item)
    return included,excluded


def parse_meeting(payload, item, observed_at):
    if datetime.fromisoformat(observed_at).tzinfo is None or observed_at[:10]<item['date']:
        raise MeetingError('invalid_evidence_timestamp')
    if payload.get('errors'):
        raise MeetingError('meeting_source_errors')
    races=payload.get('data',{}).get('getNoCacheRacesForMeet')
    if not isinstance(races,list):
        raise MeetingError('invalid_meeting_response')
    if not races:
        return []
    rows=[]; seen_heats=set(); seen_entries=set()
    populated_counts=Counter(r.get('raceNumber') for r in races if r.get('formRaceEntries'))
    for race in races:
        meet=race.get('meet') or {}
        if any(str(meet.get(k))!=str(item[k]) for k in ('id','date','state','venue')):
            raise MeetingError('meeting_identity_mismatch')
        heat=race.get('raceNumber'); entries=race.get('formRaceEntries')
        if not isinstance(heat,int) or heat<1 or not isinstance(entries,list):
            raise MeetingError('missing_or_duplicate_heat')
        seen_heats.add(heat)
        if not entries:
            continue
        distance=distance_metres(race.get('distance'))
        if distance is None or not 100<=distance<=4000:
            raise MeetingError('invalid_preparation_distance')
        # Provider status codes (e.g. 104/109) are NOT finishing positions.
        all_placed=all(type(e.get('position')) is int and 1<=e['position']<=len(entries) for e in entries)
        field_size=len(entries) if all_placed else None
        clocks={centiseconds(e.get('winningTime')) for e in entries if e.get('winningTime')}
        clock=next(iter(clocks)) if len(clocks)==1 else None
        for entry in entries:
            eid=str(entry.get('id') or ''); horse=entry.get('horse') or {}; code=str(horse.get('id') or '')
            name=entry.get('horseName'); pos=entry.get('position')
            if not eid or eid in seen_entries or not name:
                raise MeetingError('missing_or_duplicate_runner')
            seen_entries.add(eid)
            finish=pos if type(pos) is int and 1<=pos<=len(entries) else None
            rows.append({'source':'racing_com','provider':'racing_com','source_horse_id':code or None,
                'source_entry_id':eid,'source_event_id':str(race['id']),'horse_name':name,
                'event_type':'jumpout' if item['isJumpOut'] else 'official_trial','event_date':item['date'],
                'effective_at':observed_at,'collected_at':observed_at,'state':item['state'],'track':item['venue'],
                'track_slug':re.sub(r'[^a-z0-9]+','-',item['venue'].lower()).strip('-'),
                'heat_number':heat,'finish_position':finish,'field_size':field_size,'listed_runners':len(entries),
                'distance_metres':distance,'source_url':item['meetUrl']+'/race/'+str(heat),
                'beaten_margin':lengths(entry.get('margin')),'jockey_name':entry.get('jockeyName'),
                'trainer_name':entry.get('trainerName'),'going':race.get('trackCondition'),
                'official_time_seconds':clock if finish==1 else None,'parser_version':VERSION,
                'detail':{'source_position_code':pos,'heat_time_seconds':clock,'time_scope':'heat_winner',
                    'clock_conflict':len(clocks)>1,'ambiguous_heat_number':populated_counts[heat]>1,'provider_horse_name':horse.get('fullName'),
                    'field_size_basis':'all_listed_runners_have_valid_positions' if all_placed else 'unknown_status_codes_present',
                    'condition_text':race.get('condition'),'retrospective_collection':True}})
    return rows


def track_key(value):
    key=identity_key(value)
    return {'royalrandwick':'randwick','rosehillgardens':'rosehill','southsidepakenham':'pakenham',
        'southsidepakenhamsynthetic':'pakenhamsynthetic'}.get(key,key)


def install_meeting(store,rows,payload_hash):
    identity=link_rows(store,rows)
    counts={'observations_inserted':0,'accepted_inserted':0,'existing_events':0,'held':0}
    with store.connection:
        for row in identity['linked_rows']+identity['quarantined_rows']:
            hid=row.get('horse_id'); status='verified_result'; prior=None
            if not hid:status='unmatched_registry_identity'
            elif not row.get('source_horse_id'):status='missing_provider_identity'
            elif row['finish_position'] is None:status='unresolved_source_result_code'
            elif row['detail']['clock_conflict']:status='conflicting_heat_clocks'
            elif row['detail']['ambiguous_heat_number']:status='ambiguous_source_heat_number'
            if hid:
                candidates=store.connection.execute('SELECT * FROM fitness_events WHERE horse_id=? AND event_date=? AND heat_number=? AND event_type=?',
                    (hid,row['event_date'],row['heat_number'],row['event_type'])).fetchall()
                candidates=[p for p in candidates if track_key(p['track_slug'])==track_key(row['track_slug'])]
                if len(candidates)>1:status='ambiguous_existing_event'
                elif candidates:
                    prior=candidates[0]
                    if (prior['finish_position'],prior['distance_metres']) != (row['finish_position'],row['distance_metres']):status='conflicting_existing_result'
                    elif status=='verified_result':status='corroborates_existing_event'
            stable={k:v for k,v in row.items() if k not in ('effective_at','collected_at')}
            observation_id=digest([row['source_entry_id'],payload_hash])
            values=(observation_id,row['source_entry_id'],row['source_horse_id'],hid,row['horse_name'],row['event_type'],row['event_date'],row['state'],row['track'],row['heat_number'],row['finish_position'],row['field_size'],row['listed_runners'],row['distance_metres'],row['source_url'],row['collected_at'],payload_hash,status,json.dumps(row,sort_keys=True))
            counts['observations_inserted']+=store.connection.execute('INSERT OR IGNORE INTO trial_calendar_observations VALUES ('+','.join('?' for _ in values)+')',values).rowcount
            if status=='verified_result':
                event={k:row.get(k) for k in ('horse_id','event_type','event_date','effective_at','source','source_event_id','track_slug','distance_metres','going','heat_number','field_size','finish_position','beaten_margin','official_time_seconds','jockey_name','trainer_name','source_url','collected_at','parser_version')}
                event.update(event_id='trial_'+digest(['racing_com',row['source_event_id'],hid]),payload_hash=digest(stable),
                    raw_json=json.dumps(row,sort_keys=True),detail_json=json.dumps({**row['detail'],'raw_payload_hash':payload_hash},sort_keys=True),created_at=utc_now())
                counts['accepted_inserted']+=store.connection.execute('INSERT OR IGNORE INTO fitness_events ('+','.join(event)+') VALUES ('+','.join('?' for _ in event)+')',tuple(event.values())).rowcount
            elif status=='corroborates_existing_event':counts['existing_events']+=1
            else:counts['held']+=1
    return counts


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('database','registry-database','archive','run-directory'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--from-date',required=True);p.add_argument('--to-date',required=True)
    p.add_argument('--states',default='NSW,VIC,ACT')
    a=p.parse_args();validate_review_target(a.database,a.registry_database)
    start=date.fromisoformat(a.from_date);end=date.fromisoformat(a.to_date)
    if end<start or end>=date.today():raise MeetingError('window_must_contain_completed_days')
    root=a.run_directory;root.mkdir(parents=True,exist_ok=True);states=a.states.split(',')
    settings={'from_date':a.from_date,'to_date':a.to_date,'states':states,'database':str(a.database.resolve())}
    if (root/'settings.json').exists():
        if json.loads((root/'settings.json').read_text())!=settings:raise MeetingError('resume_settings_mismatch')
    else:save(root/'settings.json',settings)
    throttle=Lock()
    def request(query,variables):
        with throttle:time.sleep(.25)
        return graphql_request(query,variables)
    def collect_day(day):
        path=root/('calendar_'+day+'.json')
        if path.exists():
            previous=json.loads(path.read_text())
            if previous.get('status')=='verified':
                raw=Path(previous['archive']['payload_path']).read_bytes()
                if hashlib.sha256(raw).hexdigest()!=previous['archive']['payload_hash']:raise MeetingError('calendar_archive_hash_mismatch')
                included,excluded=validate_calendar(json.loads(raw),day,states)
                if included!=previous['meetings'] or excluded!=previous['excluded']:raise MeetingError('calendar_checkpoint_mismatch')
                return previous
        report={'date':day,'status':'failed'}
        try:
            result=request(DATE_QUERY,{'date':day})
            archive=archive_payload(a.archive,source_id='racing_com_trial_calendar',source_url='https://www.racing.com/form/'+day,payload=json.dumps(result,sort_keys=True).encode(),collected_at=utc_now())
            included,excluded=validate_calendar(result,day,states)
            report.update(status='verified',meetings=included,excluded=excluded,archive=archive)
        except Exception as exc:report['error']=str(exc) if isinstance(exc,MeetingError) else type(exc).__name__
        save(path,report);return report
    days=[(start+timedelta(days=n)).isoformat() for n in range((end-start).days+1)]
    with ThreadPoolExecutor(max_workers=4) as pool:calendars=list(pool.map(collect_day,days))
    meetings={}
    for day in calendars:
        for item in day.get('meetings',[]):
            if item['id'] in meetings and meetings[item['id']]!=item:raise MeetingError('conflicting_calendar_meeting')
            meetings[item['id']]=item
    plan={'settings':settings,'days_expected':len(days),'days_verified':sum(d['status']=='verified' for d in calendars),
        'failed_dates':[d['date'] for d in calendars if d['status']!='verified'],'meetings':list(meetings.values())}
    save(root/'plan.json',plan);print(json.dumps({k:v for k,v in plan.items() if k!='meetings'}),flush=True)
    store=RacingStore(a.database);store.connection.executescript(SCHEMA)
    def collect(item):
        path=root/('meeting_'+item['id']+'.json')
        report=json.loads(path.read_text()) if path.exists() else {'meeting':item,'status':'pending'}
        rows=None
        try:
            if report.get('archive'):
                archive=report['archive'];payload=Path(archive['payload_path']).read_bytes()
                if hashlib.sha256(payload).hexdigest()!=archive['payload_hash']:raise MeetingError('archive_hash_mismatch')
                result=json.loads(payload)
            else:
                result=request(QUERY,{'meetCode':item['id']})
                archive=archive_payload(a.archive,source_id='racing_com_trial_meetings',source_url=item['meetUrl'],payload=json.dumps(result,sort_keys=True).encode(),collected_at=utc_now())
                report['archive']=archive
            rows=parse_meeting(result,item,archive['collected_at'])
        except Exception as exc:report.update(status='failed',error=str(exc) if isinstance(exc,MeetingError) else type(exc).__name__)
        return path,report,rows
    reports=[]
    with ThreadPoolExecutor(max_workers=4) as pool:
        for n,(path,report,rows) in enumerate(pool.map(collect,plan['meetings']),1):
            if rows is not None:
                report.update(install_meeting(store,rows,report['archive']['payload_hash']))
                report.update(status='imported' if rows else 'no_results_published',source_rows=len(rows))
                report.pop('error',None)
            save(path,report);reports.append(report)
            if n%20==0 or n==len(plan['meetings']):print(json.dumps({'meetings_processed':n,'of':len(plan['meetings']),'source_rows':sum(r.get('source_rows',0) for r in reports)}),flush=True)
    summary={k:v for k,v in plan.items() if k!='meetings'}
    summary.update(meetings_expected=len(meetings),meetings_imported=sum(r['status']=='imported' for r in reports),
        unavailable_meetings=[r['meeting'] for r in reports if r['status']=='no_results_published'],
        failed_meetings=[{'meeting':r['meeting'],'error':r.get('error')} for r in reports if r['status']=='failed'])
    for key in ('source_rows','observations_inserted','accepted_inserted','existing_events','held'):summary[key]=sum(r.get(key,0) for r in reports)
    summary['integrity_check']=store.connection.execute('PRAGMA integrity_check').fetchone()[0]
    summary['foreign_key_violations']=len(store.connection.execute('PRAGMA foreign_key_check').fetchall())
    summary['status']='completed_with_source_gaps' if summary['unavailable_meetings'] or summary['failed_meetings'] or summary['failed_dates'] else 'downloaded'
    save(root/'summary.json',summary);store.close();print(json.dumps(summary,sort_keys=True),flush=True)
    if summary['failed_dates'] or summary['failed_meetings']:raise SystemExit(2)

if __name__=='__main__':main()
