import unittest

from racing_engine.handicap_weight_rematch import predicted_gap


class HandicapWeightRematchTests(unittest.TestCase):
    def test_coefficient_interpolates_only_weight_component(self):
        first={"rating":118.0,"weight":20.0};second={"rating":113.0,"weight":0.0}
        self.assertEqual(predicted_gap(first,second,0),-15.0)
        self.assertEqual(predicted_gap(first,second,.5),-5.0)
        self.assertEqual(predicted_gap(first,second,1),5.0)


if __name__=="__main__":unittest.main()
