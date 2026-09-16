"""Audit stored Saturday metro races and stage missing official steward reports.

The source database is read-only. Applying staged rows is a separate reviewed
operation. A meeting's old 'complete' flag is not evidence of race coverage.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import re
import sqlite3
import time
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from . import post_stewards
from .racing_com import request_meeting
from .stewards import PARSER_VERSION, REPORT_SOURCE, classify_report, plain_text
from .storage import RacingStore

TRACKS = {
    'NSW': {'randwick', 'rosehill'},
    'VIC': {'caulfield', 'caulfield-heath', 'flemington', 'the-valley',
            'sportsbet-sandown-hillside', 'sportsbet-sandown-lakeside'},
}
VENUES = {
    'randwick': ('royal randwick', 'randwick'), 'rosehill': ('rosehill gardens', 'rosehill'),
    'caulfield': ('caulfield',), 'caulfield-heath': ('caulfield heath',),
    'flemington': ('flemington',), 'the-valley': ('the valley', 'moonee valley'),
    'sportsbet-sandown-hillside': ('sportsbet sandown hillside', 'sandown hillside'),
    'sportsbet-sandown-lakeside': ('sportsbet sandown lakeside', 'sandown lakeside'),
}


def normal(value: str) -> str:
    return re.sub(r'[^a-z0-9]', '', value.lower())


def read_source(path: Path):
    return sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)


def expected_races(connection, start: str, end: str) -> list[dict]:
    rows = connection.execute('''SELECT DISTINCT state, race_date, track_slug, race_number
        FROM race_results WHERE race_date BETWEEN ? AND ?
        ORDER BY race_date, track_slug, race_number''', (start, end))
    return [dict(zip(('state', 'date', 'track', 'race'), row)) for row in rows
            if row[2] in TRACKS.get(row[0], set()) and date.fromisoformat(row[1]).weekday() == 5]


def report_keys(connection) -> set[tuple]:
    return {tuple(row) for row in connection.execute('''SELECT race_date, track_slug, race_number
        FROM steward_reports WHERE length(trim(report_text)) > 0''')}


def key(row: dict) -> tuple:
    return row['date'], row['track'], row['race']


def runner_names(connection, day: str, track: str, number: int) -> list[str]:
    return [row[0] for row in connection.execute('''SELECT DISTINCT runner_name
        FROM runner_results WHERE race_date=? AND track_slug=? AND race_number=?''',
        (day, track, number))]


def validate_pdf_header(text: str, day: str, track: str) -> None:
    # Supplementary sections can mention other dates/venues; only use the header.
    header = re.split(r'COMMITTEE|Supplementary|RACE\s+1\s*:', text, maxsplit=1, flags=re.I)[0]
    expected = date.fromisoformat(day)
    # PDF extraction sometimes removes spaces (``11November2023``).
    stamp = rf'\b0?{expected.day}\s*{expected.strftime("%B")}\s*{expected.year}\b'
    if not re.search(stamp, header, re.I) or not any(normal(v) in normal(header) for v in VENUES[track]):
        raise ValueError('PDF header date/venue does not match requested meeting')


def validate_runner_identity(text: str, names: list[str]) -> None:
    # Only incident runners are mentioned; require a name anchor, not full-field coverage.
    folded = re.sub(r'[^a-z0-9 ]', '', text.lower().replace('’', "'").replace('\n', ' '))
    folded = re.sub(r'\s+', ' ', folded)
    for name in names:
        name = re.sub(r'\s*\([A-Z]{2,4}\)\s*$', '', name)
        folded_name = re.sub(r'[^a-z0-9 ]', '', name.lower())
        if re.search(r'(?<!\w)' + re.escape(folded_name) + r'(?!\w)', folded):
            return
    raise ValueError('No expected runner identified in report; manual review required')


def archive(path: Path, content: bytes, url: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    path.with_suffix(path.suffix + '.metadata.json').write_text(json.dumps({
        'source_url': url, 'sha256': hashlib.sha256(content).hexdigest(),
        'collected_at': datetime.now(timezone.utc).isoformat(), 'bytes': len(content),
    }, indent=2) + '\n')


def cached(path: Path) -> tuple[bytes, str] | None:
    metadata = path.with_suffix(path.suffix + '.metadata.json')
    if not path.exists() or not metadata.exists():
        return None
    content, info = path.read_bytes(), json.loads(metadata.read_text())
    if hashlib.sha256(content).hexdigest() != info['sha256']:
        raise ValueError(f'Archive checksum mismatch: {path}')
    return content, info['source_url']


def fetch_nsw(day: str, track: str, output: Path, source_raw: Path):
    path = output / 'raw' / day / f'{track}.pdf'
    hit = cached(path)
    if hit:
        content, url = hit
    else:
        old = source_raw / 'post_stewards' / day / f'{track}.pdf'
        if old.exists():
            content = old.read_bytes()
            stamp = date.fromisoformat(day).strftime('%d%m%Y')
            url = f'{post_stewards.BASE}/{stamp}{post_stewards.VENUE_CODES[track][0]}.pdf'
        else:
            content, url = post_stewards.fetch_report_pdf(day, track)
        archive(path, content, url)
    text = post_stewards.pdf_text(content)
    validate_pdf_header(text, day, track)
    races = post_stewards.parse_races(text)
    numbers = [r['race_number'] for r in races]
    if not numbers or len(numbers) != len(set(numbers)):
        raise ValueError('Empty or duplicate race sections in PDF')
    return {r['race_number']: post_stewards.paragraphs_to_html(r['paragraphs']) for r in races}, url


def validate_vic_meeting(meet: dict, day: str, track: str) -> None:
    if (str(meet.get('date', ''))[:10] != day or meet.get('state') != 'VIC'
            or normal(meet.get('venue', '')) not in {normal(v) for v in VENUES[track]}):
        raise ValueError('Racing.com meeting date/state/venue mismatch')


def fetch_vic(day: str, track: str, output: Path, source_raw: Path):
    path = output / 'raw' / day / f'{track}.json'
    hit = cached(path)
    url = f'https://www.racing.com/form/{day}/{track}'
    if hit:
        content, url = hit
        payload = json.loads(content)
    else:
        old = source_raw / 'racing_com' / day / track / 'meeting.json'
        if not old.exists():
            raise ValueError('No archived meeting identity; calendar discovery required')
        old_races = json.loads(old.read_text())['data']['getNoCacheRacesForMeet']
        meet = old_races[0]['meet']
        validate_vic_meeting(meet, day, track)
        payload = request_meeting(str(meet['id']))
        content = json.dumps(payload).encode()
        archive(path, content, url)
    races = payload['data']['getNoCacheRacesForMeet']
    if not races:
        raise ValueError('Empty Racing.com meeting')
    reports = {}
    for race in races:
        validate_vic_meeting(race['meet'], day, track)
        number = int(race['raceNumber'])
        if number in reports:
            raise ValueError('Duplicate race number in Racing.com response')
        reports[number] = (race.get('stewardsReport') or {}).get('htmlCode') or ''
    return reports, url


def write_audit(rows, existing, staged, reasons, output: Path, start: str, end: str):
    records = []
    for row in rows:
        k = key(row)
        status = 'existing_text' if k in existing else 'staged_verified' if k in staged else 'missing'
        records.append({**row, 'status': status, 'detail': reasons.get('|'.join(map(str, k)), '')})
    with (output / 'coverage.csv').open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=['state', 'date', 'track', 'race', 'status', 'detail'])
        writer.writeheader(); writer.writerows(records)
    summary = {'start': start, 'end': end, 'scope': 'Stored Saturday metro race inventory; not all race days or calendar completeness',
               'races': len(rows), 'meetings': len({(r['date'], r['track']) for r in rows}),
               'counts': dict(Counter(r['status'] for r in records)),
               'by_state': {state: dict(Counter(r['status'] for r in records if r['state'] == state)) for state in TRACKS}}
    (output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    (output / 'reasons.json').write_text(json.dumps(reasons, indent=2) + '\n')
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-db', type=Path, required=True)
    parser.add_argument('--source-raw', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--start', required=True)
    parser.add_argument('--end', required=True)
    parser.add_argument('--collect', action='store_true')
    parser.add_argument('--max-meetings', type=int, default=0)
    parser.add_argument('--state', choices=['NSW', 'VIC', 'ALL'], default='ALL')
    args = parser.parse_args()
    if date.fromisoformat(args.start) > date.fromisoformat(args.end):
        parser.error('start must precede end')
    args.output.mkdir(parents=True, exist_ok=True)
    stage_path = args.output / 'staged.sqlite'
    if args.source_db.resolve() == stage_path.resolve():
        parser.error('staging database must differ from source database')
    source = read_source(args.source_db)
    store = RacingStore(stage_path)
    reasons_path = args.output / 'reasons.json'
    reasons = json.loads(reasons_path.read_text()) if reasons_path.exists() else {}
    try:
        rows = expected_races(source, args.start, args.end)
        existing, staged = report_keys(source), report_keys(store.connection)
        summary = write_audit(rows, existing, staged, reasons, args.output, args.start, args.end)
        if not args.collect:
            print(json.dumps(summary)); return
        meetings = defaultdict(list)
        for row in rows:
            if key(row) not in existing | staged and args.state in ('ALL', row['state']):
                meetings[(row['state'], row['date'], row['track'])].append(row)
        for index, ((state, day, track), missing) in enumerate(meetings.items()):
            if args.max_meetings and index >= args.max_meetings:
                break
            try:
                reports, url = (fetch_nsw if state == 'NSW' else fetch_vic)(day, track, args.output, args.source_raw)
                for row in missing:
                    k = key(row); reason_key = '|'.join(map(str, k))
                    try:
                        html = reports.get(row['race'], '')
                        text = plain_text(html)
                        if not text.strip():
                            raise ValueError('Source has no report text for this race')
                        names = runner_names(source, day, track, row['race'])
                        validate_runner_identity(text, names)
                        store.upsert_steward_report(
                            report_source=post_stewards.REPORT_SOURCE if state == 'NSW' else REPORT_SOURCE,
                            race_date=day, track_slug=track, race_number=row['race'], source_race_code=None,
                            report_html=html, report_text=text, source_updated_at=None, source_url=url,
                            parser_version=post_stewards.PARSER_VERSION if state == 'NSW' else PARSER_VERSION,
                            events=classify_report(html, names))
                        staged.add(k); reasons.pop(reason_key, None)
                    except ValueError as exc:
                        reasons[reason_key] = str(exc)
                print(f'{day} {track}: {sum(key(r) in staged for r in missing)}/{len(missing)} missing races staged', flush=True)
            except Exception as exc:
                for row in missing:
                    reasons['|'.join(map(str, key(row)))] = str(exc)[:400]
                print(f'{day} {track}: {type(exc).__name__}: {exc}', flush=True)
            summary = write_audit(rows, existing, staged, reasons, args.output, args.start, args.end)
            time.sleep(0.5)
        print(json.dumps(summary), flush=True)
    finally:
        source.close(); store.close()


if __name__ == '__main__':
    main()
