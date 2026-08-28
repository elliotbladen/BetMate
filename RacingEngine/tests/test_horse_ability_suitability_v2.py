import unittest

from racing_engine.horse_ability_suitability_v2 import (ContextRun,distance_band,going_bucket,
    suitability_signals)


class HorseAbilitySuitabilityV2Tests(unittest.TestCase):
    def test_context_buckets_are_deterministic(self):
        self.assertEqual(distance_band(1400),"sprint")
        self.assertEqual(distance_band(1600),"mile")
        self.assertEqual(distance_band(2000),"middle")
        self.assertEqual(distance_band(3200),"staying")
        self.assertEqual(going_bucket("Soft 6"),"soft")
        self.assertEqual(going_bucket("Good 4"),"dry")

    def test_sparse_context_is_neutral(self):
        history=[ContextRun("2025-01-01",110,"sprint","dry"),ContextRun("2025-02-01",100,"mile","soft")]
        result=suitability_signals(history,"sprint","dry")
        self.assertEqual(result["distance"],0)
        self.assertEqual(result["going"],0)

    def test_repeated_context_is_shrunk_and_bounded(self):
        history=[ContextRun(f"2025-01-{i:02d}",rating,band,going) for i,(rating,band,going) in enumerate([
            (120,"sprint","dry"),(118,"sprint","dry"),(100,"mile","soft"),(98,"mile","soft")],1)]
        result=suitability_signals(history,"sprint","dry")
        self.assertGreater(result["distance"],0)
        self.assertGreater(result["going"],0)
        self.assertLessEqual(result["distance"],6)


if __name__=="__main__":unittest.main()
