import unittest

from racing_engine.performance_par_v2 import (
    MAX_ABS_TIME_LENGTHS,
    NEUTRAL,
    PACE_SLOW_ADDBACK_CAP,
    SECONDS_PER_LENGTH,
    WEIGHT_MERIT_CAP,
    WEIGHT_MERIT_PTS_PER_KG_HCP,
    WEIGHT_MERIT_PTS_PER_KG_WFA,
    class_anchor,
    clock_is_sane,
    compose_figure,
    enforce_winner_ceiling,
    pace_adjustment,
    weight_merit,
    weight_race_factor,
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


class WeightMeritTests(unittest.TestCase):
    def test_handicap_gets_the_full_factor(self):
        self.assertEqual(weight_race_factor("Handicap. BenchMark 78."), WEIGHT_MERIT_PTS_PER_KG_HCP)
        self.assertEqual(weight_race_factor("Quality. Listed."), WEIGHT_MERIT_PTS_PER_KG_HCP)

    def test_wfa_and_set_weights_get_the_small_factor(self):
        self.assertEqual(weight_race_factor("Standard Weight for Age. Group 2."), WEIGHT_MERIT_PTS_PER_KG_WFA)
        self.assertEqual(weight_race_factor("Set Weights plus Penalties. Group 2."), WEIGHT_MERIT_PTS_PER_KG_WFA)

    def test_carrying_over_the_median_is_credited(self):
        # +3 kg over the field median in a handicap
        self.assertAlmostEqual(weight_merit(60.0, 57.0, "Handicap."), 3.0 * WEIGHT_MERIT_PTS_PER_KG_HCP)

    def test_carrying_under_the_median_is_docked(self):
        self.assertAlmostEqual(weight_merit(54.0, 57.0, "Handicap."), -3.0 * WEIGHT_MERIT_PTS_PER_KG_HCP)

    def test_wfa_weight_difference_barely_matters(self):
        self.assertAlmostEqual(weight_merit(59.0, 57.0, "Weight for Age."), 2.0 * WEIGHT_MERIT_PTS_PER_KG_WFA)

    def test_capped(self):
        self.assertEqual(weight_merit(72.0, 54.0, "Handicap."), WEIGHT_MERIT_CAP)

    def test_missing_data_is_zero(self):
        self.assertEqual(weight_merit(None, 57.0, "Handicap."), 0.0)
        self.assertEqual(weight_merit(58.0, None, "Handicap."), 0.0)


class ClassAnchorTests(unittest.TestCase):
    def test_figure_at_or_above_standard_is_never_pulled(self):
        self.assertEqual(class_anchor(112.0, 110.0, 3, has_variant=False), 0.0)
        self.assertEqual(class_anchor(110.0, 110.0, 3, has_variant=False), 0.0)

    def test_thick_par_with_variant_is_a_noop(self):
        self.assertEqual(class_anchor(95.0, 110.0, par_sample_size=136, has_variant=True), 0.0)

    def test_thin_par_pulls_a_low_figure_up(self):
        adj = class_anchor(90.0, 110.0, par_sample_size=4, has_variant=False)
        self.assertGreater(adj, 0.0)
        self.assertLessEqual(adj, 4.0)

    def test_pull_is_capped(self):
        self.assertEqual(class_anchor(40.0, 115.0, par_sample_size=1, has_variant=False), 4.0)

    def test_pull_is_upward_only(self):
        # a figure below standard never gets a negative adjustment
        self.assertGreaterEqual(class_anchor(80.0, 110.0, 6, has_variant=False), 0.0)


class WinnerCeilingTests(unittest.TestCase):
    def _rows(self):
        return [
            {"finish_position": 1, "beaten_lengths": 0.0, "performance_rating": 99.3},
            {"finish_position": 2, "beaten_lengths": 1.8, "performance_rating": 100.3},
            {"finish_position": 3, "beaten_lengths": 4.0, "performance_rating": 95.0},
        ]

    def test_beaten_horse_cannot_out_rate_the_winner(self):
        rows = enforce_winner_ceiling(self._rows())
        self.assertLess(rows[1]["performance_rating"], rows[0]["performance_rating"])
        # capped at 99.3 - 0.15*1.8
        self.assertAlmostEqual(rows[1]["performance_rating"], 99.3 - 0.15 * 1.8)
        self.assertEqual(rows[1]["winner_ceiling_applied"], round(100.3 - (99.3 - 0.15 * 1.8), 2))

    def test_beaten_horse_below_the_ceiling_is_untouched(self):
        rows = enforce_winner_ceiling(self._rows())
        self.assertEqual(rows[2]["performance_rating"], 95.0)
        self.assertNotIn("winner_ceiling_applied", rows[2])

    def test_no_winner_row_is_a_noop(self):
        rows = [{"finish_position": 2, "beaten_lengths": 1.0, "performance_rating": 110.0}]
        self.assertEqual(enforce_winner_ceiling(rows)[0]["performance_rating"], 110.0)

    def test_dead_heat_uses_the_higher_winner_figure(self):
        rows = [
            {"finish_position": 1, "beaten_lengths": 0.0, "performance_rating": 105.0},
            {"finish_position": 1, "beaten_lengths": 0.0, "performance_rating": 103.0},
            {"finish_position": 3, "beaten_lengths": 2.0, "performance_rating": 108.0},
        ]
        out = enforce_winner_ceiling(rows)
        self.assertEqual(out[0]["performance_rating"], 105.0)
        self.assertEqual(out[1]["performance_rating"], 103.0)
        self.assertAlmostEqual(out[2]["performance_rating"], 105.0 - 0.15 * 2.0)

    def test_beaten_topweight_allowed_through_on_weight(self):
        rows = [
            {"finish_position": 1, "beaten_lengths": 0.0, "performance_rating": 100.0, "weight_merit": -1.0},
            {"finish_position": 2, "beaten_lengths": 0.5, "performance_rating": 102.0, "weight_merit": 2.6},
        ]
        out = enforce_winner_ceiling(rows)
        # weight-for-weight it gave the winner 3.6 L; ceiling = 100 + 3.6 - 0.1 = 103.5
        self.assertEqual(out[1]["performance_rating"], 102.0)  # under the relaxed ceiling, untouched


if __name__ == "__main__":
    unittest.main()
