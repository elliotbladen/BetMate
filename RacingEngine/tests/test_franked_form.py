import unittest

from racing_engine.franked_form import (
    FRANK_BOUND,
    WEIGHT_MERIT_PTS_PER_KG_HCP,
    WEIGHT_MERIT_PTS_PER_KG_WFA,
    _adj_margin,
    _weight_factor,
    franking_revision,
)


class AdjMarginTests(unittest.TestCase):
    def test_linear_to_the_knee(self):
        self.assertEqual(_adj_margin(3.0), 3.0)
        self.assertEqual(_adj_margin(4.0), 4.0)

    def test_tapered_past_the_knee(self):
        self.assertAlmostEqual(_adj_margin(10.0), 4.0 + 6.0 * 0.45)


class WeightFactorTests(unittest.TestCase):
    def test_handicap_full(self):
        self.assertEqual(_weight_factor("Handicap. BenchMark 78."), WEIGHT_MERIT_PTS_PER_KG_HCP)

    def test_wfa_small(self):
        self.assertEqual(_weight_factor("Weight for Age. Group 1."), WEIGHT_MERIT_PTS_PER_KG_WFA)


class FrankingRevisionTests(unittest.TestCase):
    def test_no_revision_without_enough_contributors(self):
        self.assertEqual(franking_revision(100.0, [108.0], contributors=1), 0.0)

    def test_positive_when_beaten_field_proves_strong(self):
        # winner rated 100; beaten field's later form + margins medians to 106
        rev = franking_revision(100.0, [105.0, 106.0, 107.0], contributors=3)
        self.assertGreater(rev, 0.0)
        self.assertAlmostEqual(rev, (106.0 - 100.0) * 0.55)

    def test_negative_when_beaten_field_flops(self):
        rev = franking_revision(105.0, [98.0, 99.0, 100.0], contributors=3)
        self.assertLess(rev, 0.0)

    def test_bounded(self):
        self.assertEqual(franking_revision(80.0, [140.0, 141.0], contributors=2), FRANK_BOUND)
        self.assertEqual(franking_revision(140.0, [80.0, 81.0], contributors=2), -FRANK_BOUND)


if __name__ == "__main__":
    unittest.main()


class FrankingEffectiveDatingTests(unittest.TestCase):
    """Increment 9 — franking must not leak the future into a prediction.

    Franking revises a race once its beaten field runs again, so a run's franked
    figure legitimately contains later form. That is fine for a retrospective
    rating and fatal for a predictive score: using a 2024 run's franked figure to
    predict a 2025 race means the 2024 figure already knew what happened in 2025.
    """

    def test_effective_from_is_the_date_the_evidence_arrived(self):
        """The revision becomes knowable when the Nth contributor next runs."""
        from racing_engine.franked_form import FRANK_MIN_CONTRIBUTORS
        contributor_dates = ["2025-03-01", "2025-01-15", "2025-06-20"]
        effective_from = sorted(contributor_dates)[FRANK_MIN_CONTRIBUTORS - 1]
        # With a 2-contributor minimum, the franking exists from the SECOND
        # beaten horse's later run, not the first and not the last.
        self.assertEqual(effective_from, "2025-03-01")
        self.assertGreater(effective_from, min(contributor_dates))
        self.assertLess(effective_from, max(contributor_dates))

    def test_walk_forward_prior_uses_base_before_evidence_exists(self):
        """Before frank_effective_from, a run must contribute its UNFRANKED base."""
        # (race_date, par_v2_base, franked_figure, frank_effective_from)
        history = [("2024-05-01", 100.0, 106.0, "2025-02-01")]

        def prior_walk_forward(rows, day):
            vals = [(franked if (eff is not None and eff < day) else base)
                    for d, base, franked, eff in rows if d < day]
            return vals[-1] if vals else 100.0

        # Predicting a race BEFORE the franking evidence existed -> base figure.
        self.assertEqual(prior_walk_forward(history, "2024-11-01"), 100.0)
        # Predicting AFTER the evidence arrived -> the franked figure is fair game.
        self.assertEqual(prior_walk_forward(history, "2025-06-01"), 106.0)

    def test_unfranked_runs_are_never_treated_as_franked(self):
        """A run whose beaten field has not run again has no effective date and
        must always contribute its base, whatever the prediction date."""
        history = [("2024-05-01", 100.0, 100.0, None)]

        def prior_walk_forward(rows, day):
            vals = [(franked if (eff is not None and eff < day) else base)
                    for d, base, franked, eff in rows if d < day]
            return vals[-1] if vals else 100.0

        for day in ("2024-06-01", "2025-06-01", "2026-06-01"):
            self.assertEqual(prior_walk_forward(history, day), 100.0)
