"""Archive official horse histories and resolve identities in a local review DB."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from datetime import date, datetime
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urljoin, urlparse

from .fitness_identity import _candidates, _provider_ids
from .horse_identity import clean_name, durable_id, identity_key
from .storage import RacingStore, utc_now
from .trial_ingest import archive_payload, fetch
from .trial_meeting import MeetingError, _class_block, _text, validate_review_target

VERSION = 'rnsw-trial-profiles-v1'
BASE = 'https://mdata.racingnsw.com.au/InteractiveForm/'
SCHEMA = '''
CREATE TABLE IF NOT EXISTS trial_profile_evidence (
 source_horse_id TEXT PRIMARY KEY, horse_id TEXT NOT NULL REFERENCES horses(horse_id),
 birth_date TEXT NOT NULL, source_url TEXT NOT NULL, payload_hash TEXT NOT NULL,
 observed_at TEXT NOT NULL, profile_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS trial_history_observations (
 observation_id TEXT PRIMARY KEY, source_horse_id TEXT NOT NULL,
 horse_id TEXT NOT NULL REFERENCES horses(horse_id), event_date TEXT NOT NULL,
 meeting_url TEXT NOT NULL, heat_number INTEGER NOT NULL, field_size INTEGER NOT NULL,
 finish_position INTEGER, payload_hash TEXT NOT NULL, observed_at TEXT NOT NULL,
 detail_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS trial_identity_resolutions (
 review_key TEXT PRIMARY KEY REFERENCES fitness_identity_quarantine(review_key),
 horse_id TEXT NOT NULL REFERENCES horses(horse_id), payload_hash TEXT NOT NULL,
 resolved_at TEXT NOT NULL);
'''

for _table in ('trial_profile_evidence', 'trial_history_observations', 'trial_identity_resolutions'):
    for _action in ('UPDATE', 'DELETE'):
        SCHEMA += f"CREATE TRIGGER IF NOT EXISTS {_table}_no_{_action.lower()} BEFORE {_action} ON {_table} BEGIN SELECT RAISE(ABORT, 'trial evidence is append-only'); END;\n"


def profile_url(code):
    return BASE + 'HorseAllForm.aspx?' + urlencode({'HorseCode': code, 'src': 'horseform'})


def name_key(name):
    return identity_key(clean_name('racing_nsw', name)[0])


def parse_profile(payload, *, code, expected_names, source_url, observed_at, from_date, to_date):
    url = urlparse(source_url)
    if (url.scheme != 'https' or url.netloc != 'mdata.racingnsw.com.au' or
        url.path != '/InteractiveForm/HorseAllForm.aspx' or
        parse_qs(url.query).get('HorseCode') != [code]):
        raise MeetingError('profile_url_identity_mismatch')
    observed = datetime.fromisoformat(observed_at)
    if observed.tzinfo is None or not date.fromisoformat(from_date) <= date.fromisoformat(to_date) <= observed.date():
        raise MeetingError('invalid_profile_date_window')
    html = payload.decode('utf-8-sig')
    tables = re.findall(_class_block('table', 'horse-search-details'), html, re.I | re.S)
    if not tables:
        raise MeetingError('missing_profile_identity')
    # Subsequent tables contain owners and other unrelated personal details.
    identity = _text(tables[0])
    match = re.match(r'(.+?)\s+(\d+)yo\s+(.+?)\s+(Colt|Filly|Gelding|Mare|Horse|Entire|Rig)\s+D\.O\.B:\s*(\d{2}-[A-Za-z]{3}-\d{4})\s+by\s+(.+?)\s+from\s+(.+?)(?:\s+View Pedigree Report|\s*\|?\s*$)', identity, re.I)
    if not match:
        raise MeetingError('unrecognised_profile_identity')
    name, age, colour, sex, dob, sire, dam = match.groups()
    if not expected_names or any(name_key(name) != name_key(n) for n in expected_names):
        raise MeetingError('profile_name_disagreement')
    birth_date = datetime.strptime(dob, '%d-%b-%Y').date()
    if birth_date >= observed.date() or not 0 < int(age) < 40:
        raise MeetingError('invalid_profile_birth_date')
    history_tables = re.findall(_class_block('table', 'horse-last-start'), html, re.I | re.S)
    if len(history_tables) != 1:
        raise MeetingError('missing_or_duplicate_full_history')
    history, excluded = [], 0
    seen = set()
    for tr in re.findall(r'<tr\b[^>]*>(.*?)</tr>', history_tables[0], re.I | re.S):
        pos = re.search(_class_block('td', 'Pos'), tr, re.I | re.S)
        if not pos or not re.match(r'^T\s', _text(pos[1])):
            continue
        position = re.fullmatch(r'T\s+(?:(\d+)(?:st|nd|rd|th)|([A-Z]+|Failed to Finish|Lost Rider))\s+of\s+(\d+)', _text(pos[1]))
        links = re.findall(r'<a\b[^>]*href=[\'"]([^\'"]+)[\'"][^>]*>(.*?)</a>', tr, re.I | re.S)
        meetings = [(urlparse(urljoin(source_url, href)), _text(label)) for href, label in links
                    if urlparse(urljoin(source_url, href)).path == '/InteractiveForm/Meeting.aspx']
        if not position or len(meetings) != 1:
            raise MeetingError('unrecognised_trial_history_row')
        meeting, label = meetings[0]
        stamp = re.search(r'\b(\d{2}[A-Za-z]{3}\d{2})$', label)
        heat = re.fullmatch(r'Race(\d+)', meeting.fragment)
        if (meeting.scheme != 'https' or meeting.netloc != 'mdata.racingnsw.com.au' or
            len(parse_qs(meeting.query).get('meetcode', [])) != 1 or not stamp or not heat):
            raise MeetingError('invalid_trial_meeting_link')
        event_date = datetime.strptime(stamp[1], '%d%b%y').date().isoformat()
        if not from_date <= event_date <= to_date:
            excluded += 1
            continue
        field = int(position[3]); finish = int(position[1]) if position[1] else None
        if field < 1 or (finish is not None and not 1 <= finish <= field) or event_date <= birth_date.isoformat():
            raise MeetingError('invalid_history_result')
        key = (event_date,meeting.geturl(),int(heat[1]))
        if key in seen:
            raise MeetingError('duplicate_profile_trial_row')
        seen.add(key)
        history.append({'event_date': event_date, 'meeting_url': meeting._replace(fragment='').geturl(),
            'heat_number': int(heat[1]), 'field_size': field, 'finish_position': finish,
            'result_status': {'Failed to Finish':'dnf','Lost Rider':'lr'}.get(position[2], position[2] or 'finished'), 'track_label': label[:stamp.start()].strip(),
            'source_text': _text(tr)})
    return {'source_horse_id': code, 'name': name, 'birth_date': birth_date.isoformat(),
        'observed_racing_age': int(age), 'sex': sex.lower(), 'colour': colour,
        'sire': sire, 'dam': dam, 'source_url': source_url, 'observed_at': observed_at,
        'history': history, 'outside_window': excluded, 'parser_version': VERSION,
        'from_date': from_date, 'to_date': to_date}


def verify_anchors(store, profile):
    """Corroborate the profile against already archived meeting results."""
    history = {(r['event_date'],r['heat_number'],r['field_size'],r['finish_position']) for r in profile['history']}
    count = 0
    for table in ('fitness_events','fitness_identity_quarantine'):
        for record in store.connection.execute(f'SELECT raw_json FROM {table} WHERE source="racing_nsw"'):
            row = json.loads(record[0])
            if row.get('source_horse_id') != profile['source_horse_id']:
                continue
            if not profile['from_date'] <= row['event_date'] <= profile['to_date']:
                continue
            if (row['event_date'],row['heat_number'],row['field_size'],row['finish_position']) not in history:
                raise MeetingError('profile_history_meeting_disagreement')
            count += 1
    return count


def install_profile(store, profile, payload_hash):
    verify_anchors(store, profile)
    db = store.connection
    code = profile['source_horse_id']
    names = _candidates(store).get(name_key(profile['name']), set())
    providers = _provider_ids(store).get(('racing_nsw', code), set())
    if len(names) > 1 or len(providers) > 1 or (providers and names and providers != names):
        raise MeetingError('ambiguous_profile_registry_identity')
    hid = next(iter(providers or names), durable_id('racing_nsw:' + code))
    existing = db.execute('SELECT detail_json FROM horses WHERE horse_id=?', (hid,)).fetchone()
    detail = json.loads(existing[0]) if existing else {}
    if not isinstance(detail,dict) or not isinstance(detail.get('racing_nsw',{}),dict):
        raise MeetingError('invalid_registry_profile_metadata')
    previous = detail.get('racing_nsw', {})
    if previous.get('source_horse_id') not in (None, code) or previous.get('birth_date') not in (None, profile['birth_date']):
        raise MeetingError('conflicting_registry_profile')
    known = db.execute('SELECT DISTINCT birth_date FROM horse_profile_observations WHERE horse_id=? AND birth_date IS NOT NULL', (hid,)).fetchall()
    if any(r[0] != profile['birth_date'] for r in known):
        raise MeetingError('conflicting_observed_birth_date')
    saved = db.execute('SELECT * FROM trial_profile_evidence WHERE source_horse_id=?', (code,)).fetchone()
    if saved and (saved['horse_id'] != hid or saved['birth_date'] != profile['birth_date']):
        raise MeetingError('conflicting_saved_profile')
    now = utc_now()
    evidence = {k: profile[k] for k in ('source_horse_id','birth_date','source_url','observed_at')}
    evidence['payload_hash'] = payload_hash
    inserted = 0
    with db:
        if not saved:
            detail['racing_nsw'] = {**previous, **evidence}
            if existing:
                db.execute('UPDATE horses SET detail_json=?,updated_at=? WHERE horse_id=?', (json.dumps(detail, sort_keys=True), now, hid))
            else:
                db.execute('INSERT INTO horses VALUES (?,?,?,?,?,?,?)', (hid, profile['name'], 'racing_nsw:' + code,
                    'source_verified', json.dumps(detail, sort_keys=True), now, now))
            db.execute('INSERT INTO trial_profile_evidence VALUES (?,?,?,?,?,?,?)',
                (code,hid,profile['birth_date'],profile['source_url'],payload_hash,profile['observed_at'],
                 json.dumps({k:v for k,v in profile.items() if k != 'history'}, sort_keys=True)))
        for row in profile['history']:
            observation = hashlib.sha256(json.dumps([code, row, payload_hash], sort_keys=True).encode()).hexdigest()
            inserted += db.execute('INSERT OR IGNORE INTO trial_history_observations VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                (observation,code,hid,row['event_date'],row['meeting_url'],row['heat_number'],row['field_size'],row['finish_position'],
                 payload_hash,profile['observed_at'],json.dumps(row,sort_keys=True))).rowcount
    return {'horse_id': hid, 'new_horse': not bool(existing), 'history_inserted': inserted}


def record_resolutions(store):
    """Mark only quarantined observations now backed by an accepted event."""
    count = 0
    with store.connection:
        for row in store.connection.execute('SELECT review_key,source_event_id,raw_json FROM fitness_identity_quarantine WHERE source="racing_nsw"').fetchall():
            raw = json.loads(row['raw_json'])
            evidence = store.connection.execute('SELECT * FROM trial_profile_evidence WHERE source_horse_id=?', (raw.get('source_horse_id'),)).fetchone()
            if not evidence:
                continue
            event = store.connection.execute('SELECT raw_json FROM fitness_events WHERE source="racing_nsw" AND source_event_id=? AND horse_id=?', (row['source_event_id'], evidence['horse_id'])).fetchone()
            if not event or json.loads(event[0]).get('source_horse_id') != raw.get('source_horse_id'):
                continue
            count += store.connection.execute('INSERT OR IGNORE INTO trial_identity_resolutions VALUES (?,?,?,?)',
                (row['review_key'], evidence['horse_id'], evidence['payload_hash'], utc_now())).rowcount
    return count


def cohort(db):
    result = {}
    for table in ('fitness_events', 'fitness_identity_quarantine'):
        for record in db.execute(f'SELECT raw_json FROM {table} WHERE source="racing_nsw"'):
            row = json.loads(record[0])
            result.setdefault(row['source_horse_id'], set()).add(row['horse_name'])
    return [{'code': code, 'names': sorted(names)} for code,names in sorted(result.items())]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ('database','registry-database','archive','run-directory'):
        parser.add_argument('--' + option, type=Path, required=True)
    parser.add_argument('--from-date', required=True)
    parser.add_argument('--to-date', required=True)
    parser.add_argument('--delay', type=float, default=1.0)
    parser.add_argument('--recheck', action='store_true', help='Revalidate and replay all saved profile archives')
    args = parser.parse_args()
    validate_review_target(args.database, args.registry_database)
    args.run_directory.mkdir(parents=True, exist_ok=True)
    store = RacingStore(args.database)
    store.connection.executescript(SCHEMA)
    plan_path = args.run_directory / 'plan.json'
    if plan_path.exists():
        plan = json.loads(plan_path.read_text())
        if any(plan[k] != v for k,v in {'database':str(args.database.resolve()), 'from_date':args.from_date,'to_date':args.to_date}.items()):
            raise MeetingError('resume_plan_mismatch')
    else:
        plan = {'database':str(args.database.resolve()),'from_date':args.from_date,'to_date':args.to_date,'horses':cohort(store.connection)}
        plan_path.write_text(json.dumps(plan,indent=2,sort_keys=True)+'\n')
    counts = {'expected_profiles':len(plan['horses']), 'verified':0, 'failed':0, 'history_observations':0}
    throttle = Lock()
    def download(item):
        path = args.run_directory / (hashlib.sha256(item['code'].encode()).hexdigest()+'.json')
        report = json.loads(path.read_text()) if path.exists() else {'source_horse_id':item['code'],'status':'pending'}
        profile = None
        if report['status'] != 'verified' or args.recheck:
            try:
                url = profile_url(item['code'])
                if report.get('archive'):
                    archive = report['archive']; payload = Path(archive['payload_path']).read_bytes()
                    if hashlib.sha256(payload).hexdigest() != archive['payload_hash']:
                        raise MeetingError('archive_hash_mismatch')
                else:
                    # Bound concurrent connections and space request starts globally.
                    with throttle:
                        time.sleep(max(0,args.delay))
                    payload = fetch(url)
                    archive = archive_payload(args.archive, source_id='racing_nsw_profiles',source_url=url,payload=payload,collected_at=utc_now())
                    report['archive'] = archive
                profile = parse_profile(payload,code=item['code'],expected_names=item['names'],source_url=url,
                    observed_at=archive['collected_at'],from_date=args.from_date,to_date=args.to_date)
            except (ValueError,OSError) as exc:
                report.update(status='failed',error=str(exc) if isinstance(exc,MeetingError) else type(exc).__name__)
        return path, report, profile

    with ThreadPoolExecutor(max_workers=4) as pool:
        for index,(path,report,profile) in enumerate(pool.map(download,plan['horses'])):
            if profile is not None:
                try:
                    report.update(install_profile(store, profile, report['archive']['payload_hash']))
                    report.update(status='verified', history_rows=len(profile['history']), outside_window=profile['outside_window'])
                    report.pop('error',None)
                except (ValueError,sqlite3.Error) as exc:
                    report.update(status='failed',error=str(exc) if isinstance(exc,MeetingError) else type(exc).__name__)
            tmp = path.with_suffix('.tmp'); tmp.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n'); tmp.replace(path)
            counts[report['status']] += 1
            if report['status'] == 'verified':
                counts['history_observations'] += report.get('history_rows',0)
            if (index+1)%25 == 0 or index+1 == len(plan['horses']):
                print(json.dumps({'processed':index+1,**counts}),flush=True)
    (args.run_directory/'summary.json').write_text(json.dumps(counts,indent=2,sort_keys=True)+'\n')
    store.close()
    if counts['failed']:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
