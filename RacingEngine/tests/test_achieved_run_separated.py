import unittest

from racing_engine.achieved_run_separated import achieved_margin, reliable_race_level


class AchievedRunSeparatedTests(unittest.TestCase):
    def test_weak_opposition_evidence_borrows_from_class_prior(self):
        level,reliability=reliable_race_level(105.0,77.5,[.39,.60,0,.77],1.0)
        self.assertGreater(level,90.0)
        self.assertLess(level,105.0)
        self.assertAlmostEqual(reliability,.44,places=2)

    def test_reliable_opposition_has_bounded_authority(self):
        level,reliability=reliable_race_level(105.0,115.0,[1,1,1,1],1.0)
        self.assertEqual(reliability,.8)
        self.assertEqual(level,113.0)

    def test_winner_margin_is_positive_and_capped(self):
        self.assertAlmostEqual(achieved_margin(1,4.0,2.8333333333),11.3333333332)
        self.assertEqual(achieved_margin(1,20,3),12.0)
        self.assertEqual(achieved_margin(2,4,3),-12.0)


if __name__=="__main__":unittest.main()
