from datetime import date
import unittest

from racing_engine.horse_profiles import age_from_observation, australian_racing_age, normalise_country, normalise_sex


class HorseProfileTests(unittest.TestCase):
    def test_ar161_age_changes_on_first_august(self):
        self.assertEqual(australian_racing_age("2021-09-10", "2024-07-31"), 2)
        self.assertEqual(australian_racing_age("2021-09-10", "2024-08-01"), 3)
        self.assertEqual(australian_racing_age("2021-03-10", "2024-08-01"), 4)

    def test_observed_age_can_be_moved_back_without_current_age_leakage(self):
        self.assertEqual(age_from_observation(5, "2026-08-08", "2024-07-20"), 2)
        self.assertEqual(age_from_observation(5, "2026-08-08", "2024-08-20"), 3)

    def test_profile_normalisation_and_invalid_dates(self):
        self.assertEqual(normalise_sex("Gelding"), "G")
        self.assertEqual(normalise_country("(NZ)"), "NZ")
        with self.assertRaises(ValueError):
            australian_racing_age(date(2025, 1, 1), date(2024, 1, 1))


if __name__ == "__main__":
    unittest.main()
