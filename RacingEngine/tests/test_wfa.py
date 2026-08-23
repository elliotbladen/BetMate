import unittest

from racing_engine.wfa import carried_vs_wfa, northern_hemisphere_allowance, standard_weight


class WfaTests(unittest.TestCase):
    def test_ar168_sprint_and_month_boundaries(self):
        self.assertEqual(standard_weight("2026-08-01", 1200, 3, "G"), 51.5)
        self.assertEqual(standard_weight("2027-07-01", 1200, 3, "G"), 58.0)
        self.assertEqual(standard_weight("2027-01-01", 1200, 2, "C"), 45.0)

    def test_ar169_filly_and_mare_allowance(self):
        self.assertEqual(standard_weight("2026-08-01", 1400, 5, "M"), 57.0)
        self.assertEqual(standard_weight("2026-08-01", 1400, 5, "G"), 59.0)

    def test_long_distance_and_ineligible_cells(self):
        self.assertEqual(standard_weight("2026-08-01", 2400, 3, "C"), 48.5)
        self.assertEqual(standard_weight("2026-08-01", 2401, 5, "H"), 59.5)
        self.assertIsNone(standard_weight("2026-08-01", 2400, 2, "C"))
        self.assertIsNone(standard_weight("2026-08-01", 900, 4, "G"))

    def test_carried_weight_difference_uses_wfa_reference(self):
        self.assertEqual(carried_vs_wfa(54.0, race_date="2026-08-01", distance_metres=1200,
                                        racing_age=3, sex="F"), 4.5)

    def test_ar170_is_explicitly_gated_by_northern_sire_and_foal_month(self):
        self.assertEqual(northern_hemisphere_allowance("2026-08-01", 2200, 3), 3.5)
        self.assertEqual(standard_weight("2026-08-01", 2200, 3, "C",
                                         northern_sired_jan_jul_foal=True), 45.0)
        self.assertEqual(standard_weight("2026-08-01", 2200, 3, "C"), 48.5)


if __name__ == "__main__":
    unittest.main()
