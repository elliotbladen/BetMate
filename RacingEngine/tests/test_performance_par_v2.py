import unittest

from racing_engine.performance_par_v2 import (
    MAX_ABS_TIME_LENGTHS,
    NEUTRAL,
    PACE_SLOW_ADDBACK_CAP,
    SECONDS_PER_LENGTH,
    clock_is_sane,
    compose_figure,
    pace_adjustment,
)


class ClockSanityTests(unittest.TestCase):
    def test_missing_clock_is_not_sane(self):
        self.assertFalse(clock_is_sane(None, 96.0, 96.5))

    def test_runner_faster_than_official_winner_is_rejected(self):
        # 0.5s inside the winner's time is a timing error, not a run.
        self.assertFalse(clock_is_sane(95.5, 96.0, 96.5))

    def test_small_lead_over_official_time_is_tolerated(self):
        # within the 0.20s tolerance (hand-time rounding)
        self.assertTrue(clock_is_sane(95.9, 96.0, 96.5))

    def test_absurd_time_is_rejected(self):
        blown = 96.5 + (MAX_ABS_TIME_LENGTHS + 5) * SECONDS_PER_LENGTH
        self.assertFalse(clock_is_sane(blown, 96.0, 96.5))

    def test_normal_run_is_sane(self):
        self.assertTrue(clock_is_sane(95.8, 96.0, 96.5))


class ComposeFigureTests(unittest.TestCase):
    def test_neutral_run_at_par_with_no_adjustments(self):
        self.assertEqual(compose_figure(0, 0, 0, 0, 0, 0, 0), NEUTRAL)

    def test_fast_track_is_subtracted(self):
        # ran 6 lengths under par but the meeting ran 4 lengths fast -> +2 net
        self.assertAlmostEqual(compose_figure(6.0, 4.0, 0, 0, 0, 0, 0), NEUTRAL + 2.0)

    def test_all_terms_add_except_variant(self):
        got = compose_figure(5.0, 1.0, -2.0, 0.9, 1.5, 0.4, 0.3)
        self.assertAlmostEqual(got, NEUTRAL + 5.0 - 1.0 - 2.0 + 0.9 + 1.5 + 0.4 + 0.3)


class PaceAdjustmentTests(unittest.TestCase):
    def test_no_shape_no_runner_is_zero(self):
        adj, note = pace_adjustment(None, None, None, None)
        self.assertEqual(adj, 0.0)
        self.assertEqual(note, "no pace shape")

    def test_slow_race_adds_back_to_the_field(self):
        # sprint-home, early ~2 SD slow, full confidence -> positive add-back
        adj, note = pace_adjustment("sprint_home", -2.0, 0.95, None)
        self.assertGreater(adj, 3.0)
        self.assertLess(adj, PACE_SLOW_ADDBACK_CAP + 0.01)
        self.assertIn("slow_tempo", note)

    def test_fast_race_gets_no_race_level_addback(self):
        adj, note = pace_adjustment("sustained_high_pressure", 1.5, 0.95, None)
        self.assertEqual(adj, 0.0)
        self.assertIn("time trusted", note)

    def test_runner_term_is_bounded_and_signed(self):
        # a horse the shape flattered (soft lead) carries a negative shadow adj
        adj, _ = pace_adjustment("sprint_home", -2.0, 0.95, -1.25)
        base, _ = pace_adjustment("sprint_home", -2.0, 0.95, None)
        self.assertAlmostEqual(adj, base - 1.25)

    def test_runner_term_clamped(self):
        adj, _ = pace_adjustment(None, None, None, 9.0)
        self.assertEqual(adj, 2.0)

    def test_even_race_only_runner_term(self):
        adj, note = pace_adjustment("even", 0.0, 0.9, 0.5)
        self.assertAlmostEqual(adj, 0.5)
        self.assertIn("even", note)


if __name__ == "__main__":
    unittest.main()
