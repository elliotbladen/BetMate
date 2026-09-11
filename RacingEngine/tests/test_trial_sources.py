import json, tempfile, unittest
from pathlib import Path
import sys
sys.path.insert(0, '/private/tmp/fitness_step2')
import trial_sources

class TrialSourceRegistryTests(unittest.TestCase):
    def test_registry_has_official_entrypoints_and_provenance(self):
        data = trial_sources.load_registry(Path('/private/tmp/fitness_step2/trial_sources.json'))
        ids = {row['source_id'] for row in data['sources']}
        self.assertTrue({'racing_australia','racing_nsw','racing_com_vic'} <= ids)
        self.assertTrue(data['policy']['no_api_assumption'])
        self.assertIn('payload_hash', data['policy']['source_provenance_required'])

    def test_url_rendering_is_encoded(self):
        source = next(row for row in trial_sources.load_registry(Path('/private/tmp/fitness_step2/trial_sources.json'))['sources'] if row['source_id']=='racing_nsw')
        url = trial_sources.render_form_url(source, date='2026-08-17', state='NSW', track='Royal Randwick')
        self.assertIn('Royal%20Randwick', url)
        self.assertIn('Trial', url)

if __name__ == '__main__': unittest.main()
