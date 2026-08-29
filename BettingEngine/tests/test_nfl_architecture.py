from datetime import datetime, timezone
import unittest

from ml.nfl.contracts import GameFeatures, MarketSnapshot, SnapshotStage, TierAdjustment, TierMode
from ml.nfl.evaluation import grade_spread_against_open, summarise
from ml.nfl.market import consensus_snapshot
from ml.nfl.tiers import apply_tiers


UTC = timezone.utc


class NFLArchitectureTests(unittest.TestCase):
    def test_feature_contract_rejects_information_after_cutoff(self):
        with self.assertRaisesRegex(ValueError, "newer than as_of"):
            GameFeatures(
                game_id="2026_01_DAL_PHI",
                season=2026,
                week=1,
                home_team="PHI",
                away_team="DAL",
                kickoff_at=datetime(2026, 9, 11, tzinfo=UTC),
                as_of=datetime(2026, 9, 7, tzinfo=UTC),
                values={"home_pass_epa": 0.1},
                source_timestamps={"injury_report": datetime(2026, 9, 8, tzinfo=UTC)},
            )

    def test_home_recommendation_earns_positive_clv_when_home_shortens(self):
        result = grade_spread_against_open(-5.0, -3.0, -4.0)
        self.assertEqual(result.recommended_side, "home")
        self.assertEqual(result.clv_points, 1.0)
        self.assertTrue(result.push)  # model and opener are equally far from the close

    def test_model_beats_open_when_closer_to_close(self):
        result = grade_spread_against_open(-3.5, -1.5, -3.0)
        self.assertTrue(result.beat_open)
        self.assertEqual(result.improvement_points, 1.0)

    def test_summary_reports_rmse_and_decision_rate(self):
        rows = [
            grade_spread_against_open(-3.5, -1.5, -3.0),
            grade_spread_against_open(2.0, 1.0, 1.5),
        ]
        summary = summarise(rows)
        self.assertEqual(summary.games, 2)
        self.assertEqual(summary.wins, 1)
        self.assertEqual(summary.pushes, 1)
        self.assertEqual(summary.win_rate_ex_pushes, 1.0)

    def test_consensus_uses_median_and_rejects_mixed_games(self):
        captured = datetime(2026, 9, 1, tzinfo=UTC)
        rows = [
            MarketSnapshot("g1", captured, SnapshotStage.OPEN, home_spread=-3.0, total=47.5, bookmaker="a"),
            MarketSnapshot("g1", captured, SnapshotStage.OPEN, home_spread=-3.5, total=48.0, bookmaker="b"),
            MarketSnapshot("g1", captured, SnapshotStage.OPEN, home_spread=-4.0, total=48.5, bookmaker="c"),
        ]
        consensus = consensus_snapshot(rows, stage=SnapshotStage.OPEN, captured_at=captured)
        self.assertEqual(consensus.home_spread, -3.5)
        self.assertEqual(consensus.total, 48.0)

    def test_only_active_tiers_change_price_and_scores_remain_coherent(self):
        result = apply_tiers(3.0, 47.0, [
            TierAdjustment("home", margin_points=1.0, cap_points=2.0, mode=TierMode.ACTIVE),
            TierAdjustment("qb-shadow", margin_points=-4.0, cap_points=7.0, mode=TierMode.SHADOW),
        ])
        self.assertEqual(result.home_margin, 4.0)
        self.assertEqual(result.expected_home_points, 25.5)
        self.assertEqual(result.expected_away_points, 21.5)
        self.assertEqual(len(result.shadow), 1)

    def test_tier_cap_is_enforced(self):
        with self.assertRaisesRegex(ValueError, "exceeds its cap"):
            TierAdjustment("weather", total_points=-6.0, cap_points=5.0)


if __name__ == "__main__":
    unittest.main()
