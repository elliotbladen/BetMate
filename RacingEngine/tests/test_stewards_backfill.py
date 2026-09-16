import sqlite3
import tempfile
import unittest
from pathlib import Path
from racing_engine.stewards_backfill import (
    archive, cached, expected_races, read_source, report_keys,
    validate_pdf_header, validate_runner_identity, validate_vic_meeting, write_audit,
)


class BackfillTests(unittest.TestCase):
    def test_inventory_deduplicates_sources_and_limits_scope(self):
        db = sqlite3.connect(':memory:')
        db.execute('CREATE TABLE race_results (state, race_date, track_slug, race_number)')
        db.executemany('INSERT INTO race_results VALUES (?,?,?,?)', [
            ('NSW', '2026-09-12', 'rosehill', 1), ('NSW', '2026-09-12', 'rosehill', 1),
            ('NSW', '2026-09-13', 'rosehill', 1), ('NSW', '2026-09-12', 'newcastle', 1),
            ('VIC', '2026-09-12', 'the-valley', 2)])
        rows = expected_races(db, '2026-09-01', '2026-09-15')
        self.assertEqual(len(rows), 2)
        self.assertEqual({r['track'] for r in rows}, {'rosehill', 'the-valley'})
        db.close()

    def test_actual_text_not_ingestion_flag(self):
        db = sqlite3.connect(':memory:')
        db.execute('CREATE TABLE steward_reports (race_date, track_slug, race_number, report_text)')
        db.executemany('INSERT INTO steward_reports VALUES (?,?,?,?)', [
            ('2026-09-12', 'rosehill', 1, ''), ('2026-09-12', 'rosehill', 2, ' '),
            ('2026-09-12', 'rosehill', 3, 'Example Runner - Slow away.')])
        self.assertEqual(report_keys(db), {('2026-09-12', 'rosehill', 3)})
        db.row_factory = sqlite3.Row
        self.assertEqual(report_keys(db), {('2026-09-12', 'rosehill', 3)})
        db.close()

    def test_wrong_year_or_supplementary_identity_rejected(self):
        text = 'ROYAL RANDWICK RACECOURSE\nSaturday 16 September 2023\nCOMMITTEE\nSupplementary 16 September 2026'
        validate_pdf_header(text, '2023-09-16', 'randwick')
        with self.assertRaises(ValueError):
            validate_pdf_header(text, '2026-09-16', 'randwick')
        with self.assertRaises(ValueError):
            validate_pdf_header(text, '2023-09-16', 'rosehill')

    def test_runner_anchor_and_country_suffix(self):
        validate_runner_identity('Example Runner – slow away.', ['Example Runner (NZ)'])
        with self.assertRaises(ValueError):
            validate_runner_identity('Other Runner - slow away.', ['Example Runner'])
        with self.assertRaises(ValueError):
            validate_runner_identity('Rapidfire - slow away.', ['Rapid'])

    def test_vic_identity(self):
        meet = {'date': '2023-09-16', 'state': 'VIC', 'venue': 'Flemington'}
        validate_vic_meeting(meet, '2023-09-16', 'flemington')
        for day, track in [('2024-09-16', 'flemington'), ('2023-09-16', 'caulfield')]:
            with self.assertRaises(ValueError):
                validate_vic_meeting(meet, day, track)

    def test_archive_integrity_and_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'report.pdf'
            archive(path, b'example bytes', 'https://example.test/report')
            self.assertEqual(cached(path), (b'example bytes', 'https://example.test/report'))
            path.write_bytes(b'changed')
            with self.assertRaises(ValueError):
                cached(path)

    def test_source_is_read_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'source.sqlite'
            sqlite3.connect(path).close()
            db = read_source(path)
            with self.assertRaises(sqlite3.OperationalError):
                db.execute('CREATE TABLE forbidden (id)')
            db.close()

    def test_audit_keeps_missing_races_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            rows = [dict(state='NSW', date='2026-09-12', track='rosehill', race=n) for n in (1, 2, 3)]
            summary = write_audit(rows, {('2026-09-12', 'rosehill', 1)},
                                  {('2026-09-12', 'rosehill', 2)}, {}, Path(tmp), '2023-09-16', '2026-09-15')
            self.assertEqual(summary['counts'], {'existing_text': 1, 'staged_verified': 1, 'missing': 1})


if __name__ == '__main__':
    unittest.main()
