"""Download the NSW trial meetings actually listed on the official calendar."""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import time
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qs, quote, urljoin, urlparse

from .storage import RacingStore, utc_now
from .trial_ingest import archive_payload, fetch
from .trial_meeting import MeetingError, SOURCE, VERSION, copy_registry, ingest_meeting, parse_meeting, validate_review_target

CALENDAR_URL = 'https://mdata.racingnsw.com.au/FreeFields/Calendar_Results.aspx'


class _Links(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == 'a' and dict(attrs).get('href'):
            self.links.append(dict(attrs)['href'])


def discover_meetings(payload: bytes) -> dict:
    parser = _Links()
    parser.feed(payload.decode('utf-8-sig'))
    meetings, excluded = {}, {}
    for href in parser.links:
        url = urlparse(urljoin(CALENDAR_URL, href))
        if url.hostname != 'mdata.racingnsw.com.au' or url.path != '/FreeFields/Results.aspx':
            continue
        key = parse_qs(url.query).get('Key', [])
        if len(key) != 1:
            continue
        parts = key[0].split(',')
        if len(parts) != 4 or parts[3] != 'Trial':
            continue
        event_date = datetime.strptime(parts[0], '%Y%b%d').date().isoformat()
        item = {'date': event_date, 'state': parts[1], 'track': parts[2],
                'url': quote(url.geturl(), safe=':/?=&,%')}
        target = meetings if parts[1] == 'NSW' else excluded
        target[(event_date, parts[1], parts[2])] = item
    if not meetings:
        raise MeetingError('calendar_has_no_nsw_trial_meetings')
    return {'meetings': [meetings[k] for k in sorted(meetings)],
            'excluded_other_states': [excluded[k] for k in sorted(excluded)]}


def _save(path, value):
    with path.open('x') as out:
        out.write(json.dumps(value, indent=2, sort_keys=True) + '\n')


def collect_batch(store, plan, *, archive_root, run_directory, fetcher=fetch, delay=1.0, replay_directory=None):
    """One transaction/report per meeting; a failure cannot disappear from coverage."""
    reports = []
    for index, item in enumerate(plan['meetings']):
        report = {**item, 'parser_version': VERSION, 'status': 'failed'}
        filename = f'meeting_{index:03d}.json'
        try:
            if replay_directory is None:
                payload = fetcher(item['url'])
                archive = archive_payload(archive_root, source_id=SOURCE, source_url=item['url'], payload=payload, collected_at=utc_now())
            else:
                previous = json.loads((replay_directory / filename).read_text())
                if any(previous[k] != item[k] for k in ('url', 'date', 'track')):
                    raise MeetingError('replay_manifest_identity_mismatch')
                archive = previous.get('archive')
                if not archive:
                    raise MeetingError('previous_download_unavailable')
                payload = Path(archive['payload_path']).read_bytes()
                if hashlib.sha256(payload).hexdigest() != archive['payload_hash']:
                    raise MeetingError('archive_hash_mismatch')
            report['archive'] = archive
            meeting = parse_meeting(payload, item['url'], expected_date=item['date'],
                expected_track=item['track'], collected_at=archive['collected_at'])
            report.update(ingest_meeting(store, meeting, raw_payload_hash=archive['payload_hash']))
            report['status'] = 'reconciled_with_quarantine' if report['identity_quarantined'] or report['quality_quarantined'] else 'reconciled'
            if report.get('meeting_status') == 'abandoned':
                report['status'] = 'abandoned'
        except (ValueError, OSError, sqlite3.Error) as exc:
            report['error_type'] = type(exc).__name__
            if isinstance(exc, MeetingError):
                report['error'] = str(exc)
        _save(run_directory / filename, report)
        reports.append(report)
        print(json.dumps({'meeting': index + 1, 'of': len(plan['meetings']),
            'date': item['date'], 'track': item['track'], 'status': report['status'],
            **{k: report[k] for k in ('parsed_rows', 'inserted', 'unchanged', 'error') if k in report}}), flush=True)
        if replay_directory is None and index + 1 < len(plan['meetings']):
            time.sleep(delay)
    summary = {'parser_version': VERSION, 'expected_meetings': len(plan['meetings']),
        'reconciled_meetings': sum(r['status'] != 'failed' for r in reports),
        'abandoned_meetings': sum(r['status'] == 'abandoned' for r in reports),
        'failed_meetings': [{k: r[k] for k in ('date','track','error_type','error') if k in r}
                            for r in reports if r['status'] == 'failed'],
        'excluded_other_states': plan['excluded_other_states'],
        'meeting_reports': len(reports)}
    for key in ('advertised_starters', 'parsed_rows', 'non_starters', 'inserted', 'unchanged', 'identity_quarantined', 'quality_quarantined'):
        summary[key] = sum(r.get(key, 0) for r in reports)
    summary['status'] = 'completed_with_gaps' if summary['failed_meetings'] else 'reconciled'
    _save(run_directory / 'summary.json', summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', required=True, type=Path)
    parser.add_argument('--registry-database', required=True, type=Path)
    parser.add_argument('--archive', required=True, type=Path)
    parser.add_argument('--run-directory', required=True, type=Path, help='New directory for immutable plan and meeting reports')
    parser.add_argument('--replay-directory', type=Path, help='Replay a previous batch from archived payloads without downloading')
    args = parser.parse_args()
    validate_review_target(args.database, args.registry_database)
    args.run_directory.mkdir(parents=True, exist_ok=False)
    if args.replay_directory:
        plan = json.loads((args.replay_directory / 'plan.json').read_text())
    else:
        payload = fetch(CALENDAR_URL)
        archive = archive_payload(args.archive, source_id=SOURCE, source_url=CALENDAR_URL, payload=payload, collected_at=utc_now())
        plan = {**discover_meetings(payload), 'calendar_archive': archive}
    _save(args.run_directory / 'plan.json', plan)
    store = RacingStore(args.database)
    try:
        _save(args.run_directory / 'registry.json', copy_registry(args.registry_database, store))
        summary = collect_batch(store, plan, archive_root=args.archive, run_directory=args.run_directory,
                                replay_directory=args.replay_directory)
    finally:
        store.close()
    print(json.dumps(summary, sort_keys=True), flush=True)
    if summary['failed_meetings']:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
