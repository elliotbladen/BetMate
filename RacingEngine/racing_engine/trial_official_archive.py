"""Reconciled national Racing Australia trial result evidence, isolated from ratings."""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import sqlite3
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode, urlparse, parse_qs
from .horse_identity import identity_key
from .trial_meeting import MeetingError, _Table, _text, _class_block, _one, _label, _seconds, validate_review_target
from .trial_ingest import fetch, archive_payload
from .trial_calendar_expansion import save, digest, track_key
from .storage import utc_now

SCHEMA='''CREATE TABLE IF NOT EXISTS trial_official_observations (
 observation_id TEXT PRIMARY KEY, source_entry_id TEXT NOT NULL, source_horse_id TEXT NOT NULL,
 event_date TEXT NOT NULL, state TEXT NOT NULL, track TEXT NOT NULL, heat_number INTEGER NOT NULL,
 horse_name TEXT NOT NULL, payload_hash TEXT NOT NULL, observed_at TEXT NOT NULL,
 source_url TEXT NOT NULL, detail_json TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS trial_official_observations_meeting ON trial_official_observations(event_date,state,track,heat_number);
CREATE TRIGGER IF NOT EXISTS trial_official_observations_no_update BEFORE UPDATE ON trial_official_observations
 BEGIN SELECT RAISE(ABORT,'trial evidence is append-only'); END;
CREATE TRIGGER IF NOT EXISTS trial_official_observations_no_delete BEFORE DELETE ON trial_official_observations
 BEGIN SELECT RAISE(ABORT,'trial evidence is append-only'); END;
'''

def source_url(item):
    if not item['isTrial'] or item['isJumpOut']:raise MeetingError('not_an_official_trial')
    key=','.join([datetime.fromisoformat(item['date']).strftime('%Y%b%d'),item['state'],item['venue'],'Trial'])
    return 'https://www.racingaustralia.horse/FreeFields/Results.aspx?'+urlencode({'Key':key})

def clock(value):
    result=_seconds(value)
    return result if result and result>0 else None

def parse(payload,item,url,observed_at):
    if url!=source_url(item):raise MeetingError('official_url_identity_mismatch')
    now=datetime.fromisoformat(observed_at)
    if now.tzinfo is None or observed_at[:10]<item['date']:raise MeetingError('invalid_evidence_timestamp')
    html=payload.decode('utf-8-sig')
    if re.search(r'<title>\s*(?:Are you human\?|Access Denied|Just a moment)',html,re.I):raise MeetingError('source_access_challenge')
    venue=_one(r"<div class=['\"]race-venue['\"]>(.*?)</h2>",html,'venue')
    stamp=_text(_one(_class_block('span','race-venue-date'),venue,'meeting_date'))
    if datetime.strptime(stamp,'%A, %d %B %Y').date().isoformat()!=item['date']:raise MeetingError('official_date_mismatch')
    heading=_text(re.split(r'<span\b',venue)[0]).split(':')[0]
    if track_key(heading)!=track_key(item['venue']):raise MeetingError('official_venue_mismatch')
    headings=list(re.finditer(_class_block('table','race-title'),html,re.I|re.S))
    if re.search(r'\bMeeting Abandoned\.',_text(venue)) or (not headings and re.search(r'\bMeeting Abandoned\.',_text(html))):
        return {'status':'abandoned','rows':[],'heats':[],'advertised_starters':0}
    total=int(_one(r'Total Number of starters for this meeting \(including emergencies\)\s*(\d+)',html,'starter_total'))
    published=_one(r'Results Last Published:</b>\s*([^<]+)',html,'publication').strip()
    index=[int(x) for x in re.findall(r'href=[\'"]#Race(\d+)[\'"]',html)]
    if not headings or len(index)!=len(headings) or len(set(index))!=len(index):raise MeetingError('official_heat_index_mismatch')
    rows=[];heats=[]
    for i,h in enumerate(headings):
        title=_text(_one(r'<th\b[^>]*>(.*?)</th>',h[1],'heat_title'))
        match=re.match(r'Race (\d+)\s*-\s*(\d+:\d+[AP]M)\s+(.+?)\s+\((\d+) METRES\)',title)
        if not match:raise MeetingError('not_a_trial_heat')
        heat=int(match[1]);distance=int(match[4])
        if heat!=index[i] or not 100<=distance<=4000:raise MeetingError('official_heat_identity_mismatch')
        info=_one(r'<td\b[^>]*>(.*?)</td>',h[1],'heat_info')
        if re.search(r'INTERIM|ABANDONED|CANCELLED',_text(info),re.I):raise MeetingError('official_heat_not_final')
        winner_clock=clock(_label(info,'Time'));last600=clock(_label(info,'Last 600m'))
        if last600 and winner_clock and distance>=600 and last600>winner_clock:raise MeetingError('official_sectional_exceeds_heat_clock')
        chunk=html[h.end():headings[i+1].start() if i+1<len(headings) else len(html)]
        table=_Table();table.feed(_one(_class_block('table','race-strip-fields'),chunk,'result_table'))
        if len(table.rows)<2:raise MeetingError('official_empty_heat')
        headers=[x['text'].lower() for x in table.rows[0]]
        required=['finish','no.','horse','trainer','jockey','margin','bar.']
        if any(headers.count(x)!=1 for x in required):raise MeetingError('official_columns_changed')
        ix={x:headers.index(x) for x in required};heatrows=[];seen=set()
        for cells,classes in zip(table.rows[1:],table.row_classes[1:]):
            if len(cells)!=len(headers):raise MeetingError('official_row_width_mismatch')
            values={x:cells[j]['text'] for x,j in ix.items()}
            links=cells[ix['horse']]['links']
            source_keys=[parse_qs(urlparse(link).query).get('Key') for link in links]
            if not source_keys or any(key!=parse_qs(urlparse(url).query).get('Key') for key in source_keys):raise MeetingError('official_runner_meeting_key_mismatch')
            codes={v for link in links for v in parse_qs(urlparse(link).query).get('horsecode',[])}
            if len(codes)!=1 or not values['horse']:raise MeetingError('official_missing_horse_identity')
            code=next(iter(codes));number=re.fullmatch(r'(\d+)(?:e)?',values['no.'],re.I)
            if not number or code in seen:raise MeetingError('official_duplicate_or_missing_runner')
            seen.add(code);pos=values['finish'].upper()
            if 'scratched' in classes:
                if pos.isdigit():raise MeetingError('official_scratched_has_position')
                pos='SCR'
            finish=int(pos) if pos.isdigit() else None
            if finish is None and pos not in {'SCR','SCRATCHED','DNS','DNF','FF','LR','UR','DQ','DSQ','LP'}:raise MeetingError('official_unknown_result_status:'+pos)
            margin=values['margin'].rstrip('L').strip()
            if margin and not re.fullmatch(r'\d+(?:\.\d+)?',margin):raise MeetingError('official_invalid_margin')
            people={}
            for role,key in [('jockey','jockeycode'),('trainer','trainercode')]:
                ids={v for link in cells[ix[role]]['links'] for v in parse_qs(urlparse(link).query).get(key,[])}
                if len(ids)>1:raise MeetingError('ambiguous_person_identity')
                people[role]={'name':values[role] or None,'source_id':next(iter(ids),None)}
            heatrows.append({'source':'racing_australia','source_horse_id':code,'source_entry_id':digest([item['date'],item['state'],item['venue'],heat,code]),
              'horse_name':values['horse'],'event_date':item['date'],'state':item['state'],'track':item['venue'],'heat_number':heat,
              'distance_metres':distance,'finish_position':finish,'result_status':'finished' if finish else pos.lower(),
              'beaten_margin':float(margin) if margin else (0.0 if finish==1 else None),
              'jockey':people['jockey'],'trainer':people['trainer'],'heat_time_seconds':winner_clock,'heat_last_600m_seconds':last600,
              'timing_method':_label(info,'Timing Method'),'surface':_label(info,'Track Type'),'going':_label(info,'Track Condition'),
              'source_url':url,'observed_at':observed_at,'source_published_text':published,'time_scope':'heat_winner',
              'official_time_seconds':winner_clock if finish==1 else None})
        starters=sum(r['result_status'] not in {'scr','scratched','dns'} for r in heatrows)
        finishes=[r['finish_position'] for r in heatrows if r['finish_position'] is not None]
        if not finishes or min(finishes)!=1 or max(finishes)>starters:raise MeetingError('official_invalid_positions')
        for r in heatrows:r['field_size']=starters
        heats.append({'heat_number':heat,'starters':starters,'listed':len(heatrows)});rows.extend(heatrows)
    if sum(h['starters'] for h in heats)!=total:raise MeetingError('official_starter_count_mismatch')
    return {'status':'verified','rows':rows,'heats':heats,'advertised_starters':total}

def install(c,rows,archive):
    inserted=0
    with c:
        for r in rows:
            values=[digest([r['source_entry_id'],archive['payload_hash']]),r['source_entry_id'],r['source_horse_id'],r['event_date'],r['state'],r['track'],r['heat_number'],r['horse_name'],archive['payload_hash'],archive['collected_at'],r['source_url'],json.dumps(r,sort_keys=True)]
            inserted+=c.execute('INSERT OR IGNORE INTO trial_official_observations VALUES ('+','.join('?' for _ in values)+')',values).rowcount
    return inserted

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ['database','registry-database','archive','run-directory','plan']:p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--cached-only',action='store_true');p.add_argument('--retry-access-failures',action='store_true',help='Use only after normal access is restored; retain the earlier raw challenge evidence.');p.add_argument('--from-date',default='0001-01-01')
    a=p.parse_args();validate_review_target(a.database,a.registry_database);a.run_directory.mkdir(parents=True,exist_ok=True)
    items={source_url(m):m for m in json.loads(a.plan.read_text())['meetings'] if m['isTrial'] and not m['isJumpOut'] and m['date']>=a.from_date}
    c=sqlite3.connect(a.database);c.executescript(SCHEMA);reports=[]
    # One request at a time; stop on access/rate-limit responses, retain resumable work.
    for n,(url,item) in enumerate(sorted(items.items(),key=lambda x:x[1]['date'],reverse=True),1):
        path=a.run_directory/(digest(url)+'.json');r=json.loads(path.read_text()) if path.exists() else {'meeting':item,'source_url':url}
        try:
            archive=r.get('archive')
            if a.retry_access_failures and r.get('error')=='source_access_challenge' and not a.cached_only:archive=None
            if archive:
                raw=Path(archive['payload_path']).read_bytes()
                if hashlib.sha256(raw).hexdigest()!=archive['payload_hash']:raise MeetingError('official_archive_hash_mismatch')
            else:
                if a.cached_only:continue
                time.sleep(.75);raw=fetch(url);archive=archive_payload(a.archive,source_id='racing_australia_trials',source_url=url,payload=raw,collected_at=utc_now());r['archive']=archive
            result=parse(raw,item,url,archive['collected_at']);r.update(status=result['status'],source_rows=len(result['rows']),heats=result['heats'],inserted=install(c,result['rows'],archive));r.pop('error',None)
        except HTTPError as exc:
            r.update(status='failed',error='HTTP_'+str(exc.code));save(path,r)
            if exc.code in {401,403,429}:reports.append(r);break
        except Exception as exc:
            r.update(status='failed',error=str(exc) if isinstance(exc,MeetingError) else type(exc).__name__)
            if r['error']=='source_access_challenge':
                if not a.cached_only:
                    save(path,r);reports.append(r);break
        save(path,r);reports.append(r)
        if n%25==0:print(json.dumps({'processed':n,'expected':len(items),'statuses':dict(Counter(x['status'] for x in reports))}),flush=True)
    summary={'expected':len(items),'processed':len(reports),'statuses':dict(Counter(x['status'] for x in reports)),'errors':dict(Counter(x.get('error') for x in reports if x.get('error'))),'source_rows':sum(x.get('source_rows',0) for x in reports),'inserted':sum(x.get('inserted',0) for x in reports)}
    save(a.run_directory/'summary.json',summary);print(json.dumps(summary),flush=True);c.close()

if __name__=='__main__':main()
