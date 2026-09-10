import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from racing_engine.raw_race_strength import build, estimate, robust_level, sectional_balance


class EvidenceTests(unittest.TestCase):
    def test_huber_limits_an_isolated_outlier(self):
        normal = [('class', 100, .15), ('form', 100, .8)]
        modest, _, _ = robust_level(normal + [('clock', 125, .3)])
        extreme, weights, uncertainty = robust_level(normal + [('clock', 1000, .3)])
        self.assertAlmostEqual(modest, extreme)
        self.assertLess(weights['clock'], .01)
        self.assertGreater(uncertainty, 1)

    def test_clock_can_lower_and_raise_level(self):
        pars = [{'clock': 70, 'standard': 100, 'balance': 0} for _ in range(20)]
        anchors = [{'prior': 100, 'margin': 0, 'reliability': .7}] * 4
        slow = estimate(100, 1200, 71, pars, 0, anchors, 4)
        fast = estimate(100, 1200, 69, pars, 0, anchors, 4)
        self.assertLess(slow['race_strength'], 100)
        self.assertGreater(fast['race_strength'], 100)

    def test_sectionals_change_trust_not_clock_points(self):
        pars = [{'clock': 70, 'standard': 100, 'balance': 0} for _ in range(20)]
        even = estimate(100, 1200, 69, pars, 0, [], 4)
        tactical = estimate(100, 1200, 69, pars, 2, [], 4)
        self.assertEqual(even['clock_level'], tactical['clock_level'])
        self.assertGreater(tactical['margin_ppl'], even['margin_ppl'])
        self.assertLess(tactical['channels'][1][2], even['channels'][1][2])

    def test_stale_anchor_cannot_outvote_reliable_form(self):
        fresh = {'prior': 100, 'margin': 0, 'reliability': .7}
        stale = {'prior': 60, 'margin': 0, 'reliability': .01}
        result = estimate(100, 1200, None, [], None, [fresh, stale, stale], 3)
        self.assertGreater(result['form_level'], 99)

    def test_missing_clock_is_not_imputed(self):
        result = estimate(100, 1200, None, [], None, [], 4)
        self.assertEqual(result['race_strength'], 100)
        self.assertIsNone(result['clock_level'])
        self.assertEqual(result['evidence_status'], 'class_only')

    def test_source_specific_split_semantics(self):
        nsw = [{'marker_metres': m, 'section_seconds': 12., 'position_at_marker': 1}
               for m in [1000, 800, 600, 400, 200, 0]]
        vic = [{'marker_metres': m, 'section_seconds': 24., 'position_at_marker': 1}
               for m in [800, 400, 0]]
        self.assertEqual(sectional_balance('racing-com-nsw-authorised-v2', nsw, 1200, 72), 0)
        self.assertEqual(sectional_balance('racing-com-rv-authorised', vic, 1200, 72), 0)
        self.assertIsNone(sectional_balance('unknown', nsw, 1200, 72))
        self.assertIsNone(sectional_balance('racing-com-nsw-authorised-v2', nsw[:-1], 1200, 72))


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.db = self.root / 'source.sqlite'
        self.conn = sqlite3.connect(self.db)
        self.addCleanup(self.conn.close)
        self.conn.executescript('''
            CREATE TABLE v2_clean_races (race_id TEXT PRIMARY KEY,source TEXT,race_date TEXT,state TEXT,
                track_slug TEXT,race_number INTEGER,distance_metres INTEGER,class_family TEXT,
                official_time_seconds REAL,clock_status TEXT);
            CREATE TABLE race_results (source TEXT,race_date TEXT,track_slug TEXT,race_number INTEGER,track_condition TEXT);
            CREATE TABLE v2_clean_runner_results (race_id TEXT,runner_number INTEGER,horse_key TEXT,horse_name TEXT,
                result_status TEXT,finish_position INTEGER,beaten_lengths REAL);
            CREATE TABLE runner_sectionals (source TEXT,race_date TEXT,track_slug TEXT,race_number INTEGER,
                runner_number INTEGER,marker_metres INTEGER,section_seconds REAL,position_at_marker INTEGER);
        ''')
        for day in range(1, 10):
            self.add_race(f'2025-01-{day:02}', 1, 70 + (day % 3) * .1)
        self.conn.commit()

    def add_race(self, day, number, clock, track='test'):
        rid = f'{day}|{track}|{number}'
        self.conn.execute('INSERT INTO v2_clean_races VALUES (?,?,?,?,?,?,?,?,?,?)',
                          (rid, 'racing-com-nsw-authorised-v2', day, 'NSW', track, number, 1200, 'benchmark', clock, 'valid'))
        self.conn.execute('INSERT INTO race_results VALUES (?,?,?,?,?)',
                          ('racing-com-nsw-authorised-v2', day, track, number, 'Good 4'))
        for n in range(1, 5):
            self.conn.execute('INSERT INTO v2_clean_runner_results VALUES (?,?,?,?,?,?,?)',
                              (rid, n, f'horse{n}', f'Synthetic horse {n}', 'finished', n, 2 if n == 1 else n - 1))

    def run_build(self, name, cutoff='2025-01-10'):
        path = self.root / name
        report = build(self.db, path, cutoff)
        with sqlite3.connect(path) as conn:
            rows = conn.execute('SELECT * FROM race_strength_races ORDER BY race_id').fetchall()
            runs = conn.execute('SELECT * FROM race_strength_runs ORDER BY race_id,runner_number').fetchall()
        return report, rows, runs

    def test_future_races_do_not_rewrite_earlier_ratings(self):
        _, before, runs = self.run_build('before.sqlite')
        self.add_race('2025-02-01', 1, 68)
        self.conn.commit()
        _, after, later_runs = self.run_build('after.sqlite', '2025-02-02')
        self.assertEqual(before, after[:len(before)])
        self.assertEqual(runs, later_runs[:len(runs)])

    def test_exclusive_cutoff_and_same_day_isolation(self):
        _, before, _ = self.run_build('before.sqlite')
        self.add_race('2025-01-09', 2, 68)
        self.add_race('2025-01-10', 1, 68)
        self.conn.commit()
        report, after, _ = self.run_build('after.sqlite')
        self.assertEqual(report['counts']['races'], 10)
        for row in before:
            self.assertIn(row, after)
        for row in after:
            detail = json.loads(row[-1])
            if detail['par_latest_date']:
                self.assertLess(detail['par_latest_date'], row[2])
            for a in detail['anchors']:
                self.assertLess(a['latest_prior_date'], row[2])

    def test_invalid_clocks_excluded_from_par_and_rating(self):
        self.conn.execute("UPDATE v2_clean_races SET official_time_seconds=30 WHERE race_date='2025-01-01'")
        self.conn.execute("UPDATE v2_clean_races SET clock_status='quarantined' WHERE race_date='2025-01-02'")
        self.conn.commit()
        _, rows, _ = self.run_build('invalid.sqlite')
        self.assertIsNone(json.loads(rows[0][-1])['raw_clock_seconds'])
        self.assertIsNone(json.loads(rows[1][-1])['raw_clock_seconds'])
        self.assertEqual(json.loads(rows[6][-1])['par_n'], 4)
        self.assertIsNone(json.loads(rows[6][-1])['clock_level'])

    def test_at_weights_order_and_winner_margin(self):
        _, rows, runs = self.run_build('order.sqlite')
        levels = {r[1]: r[4] for r in rows}
        for run in runs:
            if run[2] == 1:
                self.assertEqual(run[5], levels[run[1]])
                self.assertEqual(run[6], 0)
            else:
                self.assertLess(run[5], levels[run[1]])

    def test_missing_loser_margin_is_not_zero(self):
        self.conn.execute('UPDATE v2_clean_runner_results SET beaten_lengths=NULL WHERE runner_number=4')
        self.conn.commit()
        report, _, runs = self.run_build('missing.sqlite')
        self.assertEqual(report['counts']['runs'], 27)
        self.assertTrue(all(r[2] != 4 for r in runs))

    def test_pars_do_not_cross_tracks_or_going(self):
        self.conn.execute("UPDATE race_results SET track_condition='Heavy 9' WHERE race_date='2025-01-08'")
        self.add_race('2025-01-09', 1, 70, track='different')
        self.conn.commit()
        _, rows, _ = self.run_build('buckets.sqlite')
        for row in rows:
            if row[2] == '2025-01-08' or 'different' in row[1]:
                self.assertEqual(json.loads(row[-1])['par_n'], 0)

    def test_source_unchanged_and_output_frozen(self):
        original = self.db.read_bytes()
        self.run_build('frozen.sqlite')
        self.assertEqual(original, self.db.read_bytes())
        with self.assertRaises(FileExistsError):
            self.run_build('frozen.sqlite')
        with self.assertRaises(ValueError):
            build(self.db, self.db, '2025-01-10')
        self.assertEqual(original, self.db.read_bytes())


if __name__ == '__main__':
    unittest.main()
