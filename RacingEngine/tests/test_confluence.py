import unittest

from racing_engine.confluence import EdgeEvidence, score_confluence
from racing_engine.confluence_backtest import evaluate


def edge(edge_id, family, direction=1, strength=0.8, reliability=0.9, observed_at="2026-08-20T00:00:00Z"):
    return EdgeEvidence(edge_id, family, direction, strength, reliability, observed_at, edge_id, "test")


class ConfluenceTests(unittest.TestCase):
    def test_correlated_edges_are_capped_inside_family(self):
        card = score_confluence(model_probability=.25, market_probability=.20,
            evidence=[edge("track-1", "track_distance_going"), edge("track-2", "track_distance_going")],
            cutoff_at="2026-08-21T00:00:00Z")
        self.assertEqual(card.positive_families, 1)
        self.assertLess(card.family_scores[0].score, 1.0)
        self.assertFalse(card.qualifies)

    def test_requires_market_edge_and_two_independent_families(self):
        card = score_confluence(model_probability=.25, market_probability=.20,
            evidence=[edge("horse", "horse_profile"), edge("map", "race_setup")],
            cutoff_at="2026-08-21T00:00:00Z")
        self.assertTrue(card.qualifies)
        self.assertEqual(card.confidence_tier, "C")

    def test_rejects_lookahead(self):
        with self.assertRaisesRegex(ValueError, "look-ahead"):
            score_confluence(model_probability=.25, market_probability=.20,
                evidence=[edge("late", "horse_profile", observed_at="2026-08-22T00:00:00Z")],
                cutoff_at="2026-08-21T00:00:00Z")

    def test_backtest_reports_market_lift_and_roi(self):
        report = evaluate([
            {"tier": "A", "market_probability": .25, "outcome": 1, "decimal_odds": 4.0},
            {"tier": "A", "market_probability": .25, "outcome": 0, "decimal_odds": 4.0},
        ])
        self.assertEqual(report["segments"]["A"]["actual_wins"], 1)
        self.assertAlmostEqual(report["segments"]["A"]["market_lift"], 1.0)
        self.assertAlmostEqual(report["segments"]["A"]["roi"], 1.0)


if __name__ == "__main__":
    unittest.main()
