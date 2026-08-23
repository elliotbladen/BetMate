import unittest
from racing_engine.sectional_forward_test import _adjust,_softmax,COEFFICIENTS

class SectionalForwardTest(unittest.TestCase):
    def test_frozen_coefficients_are_distance_and_jurisdiction_specific(self):
        row={"jurisdiction":"VIC","distance_band":"middle","achievement_signal":9,"compensation_signal":2}
        self.assertEqual(_adjust(row),1.6)
        row.update(jurisdiction="NSW")
        self.assertEqual(_adjust(row),0.0)

    def test_adjustment_is_capped_and_staying_is_not_silently_scored(self):
        row={"jurisdiction":"VIC","distance_band":"sprint","achievement_signal":0,"compensation_signal":100}
        self.assertEqual(_adjust(row),3)
        row["distance_band"]="staying"
        self.assertIsNone(_adjust(row))

    def test_softmax_is_a_probability_distribution(self):
        values=_softmax([1,2,3])
        self.assertAlmostEqual(sum(values),1.0)
        self.assertGreater(values[2],values[1])

    def test_frozen_values_have_not_drifted(self):
        self.assertEqual(COEFFICIENTS["NSW"]["sprint"],{"achievement":.1,"compensation":.1})
        self.assertEqual(COEFFICIENTS["VIC"]["middle"],{"achievement":0.,"compensation":.8})
