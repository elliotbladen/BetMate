import unittest

from racing_engine.expected_tempo_live import meeting_state, observation_weight


class ExpectedTempoLiveTests(unittest.TestCase):
    def setUp(self):
        self.prior = {
            "going_bucket": "good", "distance_metres": 1200, "race_number": 1,
            "sectional_coverage": 1.0, "early_score": 1.5, "middle_score": 0.5, "late_score": -0.5,
        }
        self.target = {"going_bucket": "good", "distance_metres": 1200, "race_number": 2}

    def test_only_completed_prior_races_create_state(self):
        empty = meeting_state([], self.target)
        updated = meeting_state([self.prior], self.target)
        self.assertEqual(empty["state_reliability"], 0.0)
        self.assertGreater(updated["state_early"], 0.0)
        self.assertEqual(updated["completed_races"], 1.0)

    def test_going_change_starts_new_regime(self):
        heavy = {**self.target, "going_bucket": "heavy"}
        self.assertEqual(observation_weight(self.prior, heavy), 0.0)
        state = meeting_state([self.prior], heavy)
        self.assertEqual(state["same_regime_races"], 0.0)
        self.assertEqual(state["state_early"], 0.0)

    def test_distance_and_recency_reduce_relevance(self):
        close = observation_weight(self.prior, self.target)
        distant = observation_weight(self.prior, {**self.target, "distance_metres": 2400, "race_number": 5})
        self.assertGreater(close, distant)


if __name__ == "__main__":
    unittest.main()
