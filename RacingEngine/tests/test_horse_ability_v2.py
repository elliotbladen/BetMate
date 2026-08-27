import unittest

from racing_engine.horse_ability_v2 import (
    NEUTRAL,
    ability_state,
    probabilities,
    rejected_v2_state,
)


class HorseAbilityV21Tests(unittest.TestCase):
    def test_future_and_same_day_runs_cannot_change_prior_state(self):
        history = [
            ("2025-01-01", 101.0),
            ("2025-02-01", 105.0),
            ("2025-03-01", 140.0),
        ]
        before = ability_state(history, "2025-03-01")
        control = ability_state(history[:2], "2025-03-01")
        self.assertEqual(before, control)
        self.assertEqual(rejected_v2_state(history, "2025-03-01"), 103.0)

    def test_sustainable_peak_is_bounded_by_repeatability_and_shrinkage(self):
        one = ability_state([("2025-01-01", 130.0)], "2025-02-01")
        repeated = ability_state(
            [("2025-01-01", 120.0), ("2025-01-15", 122.0), ("2025-02-01", 121.0)],
            "2025-03-01",
        )
        self.assertLess(one.ability_rating, 115.0)
        self.assertGreater(repeated.ability_rating, one.ability_rating)
        self.assertLess(repeated.uncertainty, one.uncertainty)

    def test_empty_history_is_neutral_and_uncertain(self):
        state = ability_state([], "2025-01-01")
        self.assertEqual(state.ability_rating, NEUTRAL)
        self.assertEqual(state.rated_runs, 0)
        self.assertEqual(state.uncertainty, 12.0)

    def test_probability_book_is_coherent(self):
        book = probabilities([100.0, 105.0, 110.0], 10.0)
        self.assertAlmostEqual(sum(book), 1.0)
        self.assertGreater(book[2], book[1])
        self.assertGreater(book[1], book[0])


if __name__ == "__main__":
    unittest.main()
