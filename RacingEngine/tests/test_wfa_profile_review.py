import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from racing_engine.wfa_profile_review import build, observation, reference


def runner(**changes):
    row = {'source': 'racing-com-nsw-authorised-v2', 'horse_name': 'Example (NZ)',
           'raw_json': json.dumps({'raw_entry': {'horse': {'id': '123', 'fullName': 'Example (NZ)', 'age': '4YO', 'sex': 'Mare'}}}),
           'imported_at': '2026-09-09T03:00:00+00:00', 'race_date': '2025-02-01',
           'distance_metres': 1000, 'weight_carried_kg': 54.5, 'old_birth_date': None}
    return {**row, **changes}


class ProfileReviewTests(unittest.TestCase):
    def test_fetch_age_is_projected_to_race_season(self):
        row = runner()
        obs, error = observation(row)
        self.assertIsNone(error)
        out = reference(row, [obs])
        self.assertEqual(out['racing_age'], 2)
        self.assertEqual(out['base_wfa_kg'], 44)
        self.assertTrue(out['retrospective'])
        self.assertFalse(out['pit_eligible'])
        self.assertTrue(out['observation_after_race'])
        self.assertNotIn('historical_gelding_status', out)

    def test_august_boundary_uses_australian_observation_date(self):
        obs, _ = observation(runner(imported_at='2026-07-31T15:00:00+00:00'))
        self.assertEqual(obs['observed_date'], '2026-08-01')
        self.assertEqual(reference(runner(race_date='2026-07-31'), [obs])['racing_age'], 3)

    def test_missing_timestamp_is_not_replaced_by_race_date(self):
        for stamp in (None, 'bad', '2026-09-09T03:00:00'):
            obs, reason = observation(runner(imported_at=stamp))
            self.assertIsNone(obs)
            self.assertIsNotNone(reason)

    def test_wrong_horse_and_unsupported_source_are_rejected(self):
        self.assertEqual(observation(runner(horse_name='Someone Else'))[1], 'identity_not_verified')
        self.assertEqual(observation(runner(source='rnsw-authorised'))[1], 'unsupported_source')

    def test_age_and_gender_conflicts_are_not_averaged(self):
        obs, _ = observation(runner())
        self.assertEqual(reference(runner(), [obs, {**obs, 'season_origin': 1900}])['status'], 'conflicting_provider_profile')
        self.assertEqual(reference(runner(), [obs, {**obs, 'sex_group': 'male'}])['status'], 'conflicting_provider_profile')

    def test_unknown_sex_does_not_default_to_male(self):
        obs, _ = observation(runner())
        out = reference(runner(), [{**obs, 'sex_group': None}])
        self.assertEqual(out['status'], 'missing_age_or_sex')
        self.assertNotIn('base_wfa_kg', out)

    def test_birth_date_disagreement_blocks_reference(self):
        row = runner(old_birth_date='2019-09-01')
        obs, _ = observation(row)
        out = reference(row, [obs])
        self.assertEqual(out['status'], 'birth_date_age_conflict')
        self.assertIsNone(out['base_wfa_kg'])
        self.assertEqual(out['component_sensitivity_points'], {})

    def test_components_are_separate_from_total_ratings(self):
        row = runner(race_date='2026-09-05', weight_carried_kg=58.)
        obs, _ = observation(row)
        out = reference(row, [obs])
        self.assertEqual(out['base_wfa_kg'], 56.5)
        self.assertEqual(out['component_sensitivity_points']['0.65'], .975)
        self.assertNotIn('performance_rating', out)
        self.assertEqual(out['ar170_status'], 'not_assessed_base_reference_only')

    def test_invalid_projected_age_and_distance_stay_missing(self):
        obs, _ = observation(runner())
        self.assertEqual(reference(runner(race_date='2015-01-01'), [obs])['status'], 'implausible_reconstructed_racing_age')
        self.assertEqual(reference(runner(distance_metres=900), [obs])['status'], 'outside_schedule')


class BuildReviewTests(unittest.TestCase):
    def test_exact_source_recovery_cutoffs_and_read_only_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'source.sqlite'
            row = runner()
            with sqlite3.connect(source) as conn:
                conn.executescript('''
                  CREATE TABLE v2_clean_races (race_id TEXT,source TEXT,race_date TEXT,state TEXT,distance_metres INTEGER,track_slug TEXT,race_number INTEGER);
                  CREATE TABLE v2_clean_runner_results (race_id TEXT,runner_number INTEGER,horse_name TEXT,weight_carried_kg REAL,result_status TEXT,finish_position INTEGER);
                  CREATE TABLE runner_results (source TEXT,race_date TEXT,track_slug TEXT,race_number INTEGER,runner_number INTEGER,raw_json TEXT,imported_at TEXT);
                  CREATE TABLE runner_derived_profiles (derivation_version TEXT,source TEXT,race_date TEXT,track_slug TEXT,race_number INTEGER,runner_number INTEGER,racing_age INTEGER,sex TEXT,birth_date TEXT);
                ''')
                conn.execute('INSERT INTO v2_clean_races VALUES (?,?,?,?,?,?,?)', ('race',row['source'],row['race_date'],'NSW',1000,'test',1))
                conn.execute('INSERT INTO v2_clean_runner_results VALUES (?,?,?,?,?,?)', ('race',1,row['horse_name'],54.5,'finished',1))
                conn.execute('INSERT INTO runner_results VALUES (?,?,?,?,?,?,?)', (row['source'],row['race_date'],'test',1,1,row['raw_json'],row['imported_at']))
            before = source.read_bytes()
            report = build(source, root / 'review.sqlite', '2025-02-02', '2026-09-10')
            self.assertEqual(report['counts']['reconstructed_base_reference_available'], 1)
            self.assertEqual(report['counts']['old_base_reference_available'], 0)
            self.assertEqual(report['pit_eligible_runs'], 0)
            self.assertEqual(source.read_bytes(), before)
            cutoff = build(source, root / 'cutoff.sqlite', '2025-02-02', '2026-09-08')
            self.assertEqual(cutoff['status_counts'], {'observation_after_review_cutoff': 1})
            empty = build(source, root / 'empty.sqlite', '2025-02-01', '2026-09-10')
            self.assertEqual(empty['counts'], {})
            with self.assertRaises(FileExistsError):
                build(source, root / 'review.sqlite', '2025-02-02', '2026-09-10')
            with self.assertRaises(ValueError):
                build(source, source, '2025-02-02', '2026-09-10')


if __name__ == '__main__':
    unittest.main()
