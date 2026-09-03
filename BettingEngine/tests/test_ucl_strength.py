import unittest

from ml.football.ucl_strength import cross_league_strength, shrink_to_uefa_prior, validate_strength_row


class UCLStrengthTests(unittest.TestCase):
    def test_sparse_domestic_sample_shrinks_to_uefa_prior(self):
        self.assertAlmostEqual(shrink_to_uefa_prior(10.0, 2.0, 0), 2.0)
        self.assertAlmostEqual(shrink_to_uefa_prior(10.0, 2.0, 12), 6.0)

    def test_strength_requires_utc_state(self):
        with self.assertRaisesRegex(ValueError, "timezone"):
            cross_league_strength(1, 1, 0, 0, 10, "2026-09-01")

    def test_strength_row_is_market_independent(self):
        row = {"club_id": "arsenal", "season": "2026/27", "as_of_utc": "2026-09-01T00:00:00Z",
               "attack": 1, "defence": 1, "league_adjustment": .2, "uefa_prior": .4, "matches": 10}
        self.assertFalse(validate_strength_row(row)["market_fields_used"])


if __name__ == "__main__":
    unittest.main()
