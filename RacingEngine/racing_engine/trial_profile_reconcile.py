"""Verify archived profile evidence, replay meetings, and record resolutions."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from .storage import RacingStore
from .trial_batch import collect_batch
from .trial_meeting import MeetingError, validate_review_target
from .trial_profiles import SCHEMA, parse_profile, profile_url, record_resolutions, verify_anchors


def fingerprint(rows):
    return hashlib.sha256(json.dumps([tuple(r) for r in rows], sort_keys=True).encode()).hexdigest()


def reconcile(store, *, profile_directory, meeting_directory, run_directory, archive_root):
    plan = json.loads((profile_directory/'plan.json').read_text())
    # Validate every archived source before promoting any unresolved meeting row.
    checked = 0
    unresolved = []
    for item in plan['horses']:
        report = json.loads((profile_directory/(hashlib.sha256(item['code'].encode()).hexdigest()+'.json')).read_text())
        if report['status'] != 'verified':
            if store.connection.execute('SELECT 1 FROM trial_profile_evidence WHERE source_horse_id=?',(item['code'],)).fetchone():
                raise MeetingError('installed_profile_failed_revalidation')
            unresolved.append({'source_horse_id':item['code'],'reason':report.get('error','unverified')})
            continue
        archive = report['archive']
        payload = Path(archive['payload_path']).read_bytes()
        if hashlib.sha256(payload).hexdigest() != archive['payload_hash']:
            raise MeetingError('profile_archive_hash_mismatch')
        profile = parse_profile(payload,code=item['code'],expected_names=item['names'],source_url=profile_url(item['code']),
            observed_at=archive['collected_at'],from_date=plan['from_date'],to_date=plan['to_date'])
        verify_anchors(store,profile)
        evidence = store.connection.execute('SELECT * FROM trial_profile_evidence WHERE source_horse_id=?',(item['code'],)).fetchone()
        if not evidence or evidence['payload_hash'] != archive['payload_hash'] or evidence['birth_date'] != profile['birth_date']:
            raise MeetingError('installed_profile_evidence_mismatch')
        expected = {(r['event_date'],r['meeting_url'],r['heat_number'],r['field_size'],r['finish_position']) for r in profile['history']}
        installed = {tuple(r) for r in store.connection.execute('SELECT event_date,meeting_url,heat_number,field_size,finish_position FROM trial_history_observations WHERE source_horse_id=? AND payload_hash=?',(item['code'],archive['payload_hash']))}
        if expected != installed:
            raise MeetingError('installed_profile_history_mismatch')
        checked += 1
    original = store.connection.execute('SELECT * FROM fitness_events ORDER BY event_id').fetchall()
    ids = {r['event_id'] for r in original}
    quarantine = fingerprint(store.connection.execute('SELECT * FROM fitness_identity_quarantine ORDER BY review_key'))
    run_directory.mkdir(parents=True,exist_ok=False)
    meeting_plan = json.loads((meeting_directory/'plan.json').read_text())
    (run_directory/'plan.json').write_text(json.dumps(meeting_plan,indent=2,sort_keys=True)+'\n')
    summary = collect_batch(store,meeting_plan,archive_root=archive_root,run_directory=run_directory,replay_directory=meeting_directory)
    if summary['failed_meetings']:
        raise MeetingError('meeting_replay_has_gaps')
    if fingerprint(original) != fingerprint([r for r in store.connection.execute('SELECT * FROM fitness_events ORDER BY event_id') if r['event_id'] in ids]):
        raise MeetingError('original_event_changed')
    if quarantine != fingerprint(store.connection.execute('SELECT * FROM fitness_identity_quarantine ORDER BY review_key')):
        raise MeetingError('original_identity_quarantine_changed')
    new_resolutions = record_resolutions(store)
    audit = {'expected_profiles':len(plan['horses']),'unresolved_profiles':unresolved,'verified_profiles':checked,'new_resolutions':new_resolutions,'original_events_preserved':len(original),
        'original_quarantine_preserved':True,'integrity_check':store.connection.execute('PRAGMA integrity_check').fetchone()[0],
        'foreign_key_violations':len(store.connection.execute('PRAGMA foreign_key_check').fetchall())}
    for table in ('fitness_events','fitness_identity_quarantine','fitness_quality_quarantine','trial_profile_evidence','trial_history_observations','trial_identity_resolutions'):
        audit[table] = store.connection.execute(f'SELECT count(*) FROM {table}').fetchone()[0]
    audit['outstanding_identity_quarantine'] = store.connection.execute('SELECT count(*) FROM fitness_identity_quarantine q LEFT JOIN trial_identity_resolutions r USING(review_key) WHERE r.review_key IS NULL').fetchone()[0]
    (run_directory/'resolution_audit.json').write_text(json.dumps(audit,indent=2,sort_keys=True)+'\n')
    if audit['integrity_check'] != 'ok' or audit['foreign_key_violations']:
        raise MeetingError('database_integrity_failure')
    return audit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ('database','registry-database','profile-directory','meeting-directory','run-directory','archive'):
        parser.add_argument('--'+option,type=Path,required=True)
    args = parser.parse_args()
    validate_review_target(args.database,args.registry_database)
    store = RacingStore(args.database)
    try:
        store.connection.executescript(SCHEMA)
        print(json.dumps(reconcile(store,profile_directory=args.profile_directory,meeting_directory=args.meeting_directory,
            run_directory=args.run_directory,archive_root=args.archive),sort_keys=True),flush=True)
    finally:
        store.close()


if __name__ == '__main__':
    main()
