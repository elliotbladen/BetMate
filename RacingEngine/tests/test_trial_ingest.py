import tempfile, unittest
from pathlib import Path
from racing_engine.trial_ingest import archive_payload, collect_explicit_urls, discover_trial_links, extract_trial_rows

HTML=b'''<html><a href="/form/race-trial">Trial</a><table><tr><th>Horse</th><th>Trainer</th><th>Jockey</th><th>Barrier</th><th>Position</th></tr><tr><td>Test Horse</td><td>T Trainer</td><td>J Rider</td><td>3</td><td>1</td></tr></table></html>'''
class TrialIngestTests(unittest.TestCase):
 def test_extracts_rows_and_links(self):
  self.assertEqual(discover_trial_links(HTML,'https://example.test/calendar'),['https://example.test/form/race-trial'])
  rows=extract_trial_rows(HTML,'https://example.test/form/race-trial')
  self.assertEqual(rows[0]['horse'],'Test Horse'); self.assertEqual(rows[0]['position'],'1'); self.assertTrue(rows[0]['source_row_hash'])
 def test_archive_is_idempotent_and_manifest_captures_counts(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td); first=archive_payload(root,source_id='test',source_url='https://example.test',payload=HTML,collected_at='2026-01-01T00:00:00Z'); second=archive_payload(root,source_id='test',source_url='https://example.test',payload=HTML,collected_at='2026-01-01T00:00:01Z')
   self.assertEqual(first['payload_hash'],second['payload_hash']); self.assertEqual(len(list((root/'test').rglob('*.html'))),1)
   result=collect_explicit_urls('test',['https://example.test'],root,fetcher=lambda _:HTML)
   self.assertEqual(result['pages'][0]['status'],'ok');self.assertEqual(result['pages'][0]['row_count'],1)
if __name__=='__main__':unittest.main()
