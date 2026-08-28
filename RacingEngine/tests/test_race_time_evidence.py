import unittest

from racing_engine.race_time_evidence import going_bucket, median_mad, rail_bucket


class RaceTimeEvidenceTests(unittest.TestCase):
    def test_context_buckets_are_source_honest(self):
        self.assertEqual(going_bucket("Soft 6"), "soft")
        self.assertEqual(rail_bucket("True Entire Circuit"), "true")
        self.assertEqual(rail_bucket("Out 6m Entire Circuit"), "out_5_8m")
        self.assertEqual(rail_bucket(None), "unknown")

    def test_robust_par(self):
        self.assertEqual(median_mad([60,61,62]), (61,1))


if __name__ == "__main__": unittest.main()
