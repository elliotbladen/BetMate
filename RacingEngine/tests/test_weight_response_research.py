import unittest
from racing_engine.weight_response_research import distance_segment, ifha_points_per_kg, race_type


class WeightResponseTests(unittest.TestCase):
    def test_ifha_curve_is_distance_dependent(self):
        self.assertAlmostEqual(ifha_points_per_kg(1000),1/(3*.45359237))
        self.assertAlmostEqual(ifha_points_per_kg(1600),1/(2*.45359237))
        self.assertAlmostEqual(ifha_points_per_kg(2800),1/.45359237)
        self.assertLess(ifha_points_per_kg(1000),ifha_points_per_kg(1600))

    def test_segments_separate_race_conditions(self):
        self.assertEqual(race_type("Handicap. Benchmark 78"),"handicap")
        self.assertEqual(race_type("Standard Weight for Age. Group 1"),"wfa")
        self.assertEqual(race_type("Set Weights plus Penalties"),"set_weight")
        self.assertEqual(distance_segment(2001),"staying")


if __name__=="__main__":unittest.main()
