from datetime import datetime, timezone
import unittest

import pandas as pd

from ml.nfl.contracts import GameFeatures, MarketSnapshot, SnapshotStage, TierAdjustment, TierMode
from ml.nfl.data_contract import (
    HISTORICAL_FEATURE_TIMING,
    prepare_odds_for_schedule_join,
    schedule_team_code,
    validate_feature_store,
)
from ml.nfl.evaluation import grade_spread_against_open, summarise
from ml.nfl.market import consensus_snapshot
from ml.nfl.tiers import apply_tiers
from ml.nfl.baselines import elo_predictions, fit_ridge
from ml.nfl.rule_eras import rule_era_features
from ml.nfl.personnel import starter_mixture
from ml.nfl.qb_lab import paid_qb_schema
from ml.nfl.challenger import _normal_win_probability
from ml.nfl.step5_vault import _spread_bet_summary
from ml.nfl.step6_paper import LABEL_COLUMNS


UTC = timezone.utc


class NFLArchitectureTests(unittest.TestCase):
    def test_step6_forbids_markets_and_results_in_pre_market_card(self):
        self.assertIn("margin", LABEL_COLUMNS)
        self.assertIn("spread_line", LABEL_COLUMNS)
        self.assertIn("h2h_home_close", LABEL_COLUMNS)

    def test_opening_spread_bet_grades_home_and_away_consistently(self):
        rows = pd.DataFrame([
            {"fair": -5.0, "spread_home_open": -3.0, "margin": 7.0},
            {"fair": 4.0, "spread_home_open": 2.0, "margin": -4.0},
        ])
        result = _spread_bet_summary(rows, "fair", 0.0)
        self.assertEqual(result["wins"], 2)
        self.assertEqual(result["losses"], 0)

    def test_margin_probability_is_symmetric_and_monotonic(self):
        probabilities = _normal_win_probability(pd.Series([-7.0, 0.0, 7.0]).to_numpy(), 13.0)
        self.assertLess(probabilities[0], 0.5)
        self.assertEqual(probabilities[1], 0.5)
        self.assertGreater(probabilities[2], 0.5)
        self.assertAlmostEqual(probabilities[0] + probabilities[2], 1.0)

    def test_paid_qb_adapter_requires_timestamp_and_provider(self):
        schema = paid_qb_schema()
        self.assertIn("captured_at", schema["identity"])
        self.assertIn("provider", schema["identity"])
        self.assertIn("turnover_worthy_rate", schema["decisions"])

    def test_uncertain_qb_uses_probability_mixture(self):
        self.assertEqual(starter_mixture(5.0, -2.0, 0.75), 3.25)
        with self.assertRaisesRegex(ValueError, "between zero and one"):
            starter_mixture(5.0, -2.0, 1.1)

    def test_uncertain_qb_endpoints_equal_named_players(self):
        self.assertEqual(starter_mixture(4.0, -1.0, 1.0), 4.0)
        self.assertEqual(starter_mixture(4.0, -1.0, 0.0), -1.0)

    def test_onside_rule_era_is_known_before_kickoff(self):
        self.assertEqual(rule_era_features(2024)["onside_anytime_when_trailing"], 0)
        self.assertEqual(rule_era_features(2025)["onside_anytime_when_trailing"], 1)
        self.assertEqual(rule_era_features(2026)["onside_2026_alignment_rule"], 1)

    def test_ridge_handles_a_constant_rule_era_column(self):
        frame = pd.DataFrame({"epa": [0.0, 1.0, 2.0], "era": [0.0, 0.0, 0.0]})
        model = fit_ridge(frame, pd.Series([1.0, 2.0, 3.0]), ["epa", "era"], alpha=1.0)
        predictions = model.predict(frame)
        self.assertEqual(len(predictions), 3)
        self.assertTrue(pd.Series(predictions).notna().all())

    def test_elo_prediction_is_made_before_current_result_update(self):
        games = pd.DataFrame([
            {"game_id": "g1", "gameday": "2020-01-01", "home_team": "A", "away_team": "B", "margin": 20},
            {"game_id": "g2", "gameday": "2020-01-02", "home_team": "A", "away_team": "B", "margin": -3},
        ])
        predictions = elo_predictions(games)
        self.assertAlmostEqual(predictions.iloc[0], 2.2)
        self.assertGreater(predictions.iloc[1], predictions.iloc[0])

    def test_game_identity_must_match_row_teams(self):
        with self.assertRaisesRegex(ValueError, "do not match"):
            GameFeatures(
                game_id="2026_01_DAL_PHI",
                season=2026,
                week=1,
                home_team="DAL",
                away_team="PHI",
                kickoff_at=datetime(2026, 9, 11, tzinfo=UTC),
                as_of=datetime(2026, 9, 7, tzinfo=UTC),
                values={},
            )

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

    def test_market_snapshot_requires_a_market_and_sensible_range(self):
        captured = datetime(2026, 9, 1, tzinfo=UTC)
        with self.assertRaisesRegex(ValueError, "spread or total"):
            MarketSnapshot("g1", captured, SnapshotStage.OPEN)
        with self.assertRaisesRegex(ValueError, "contract range"):
            MarketSnapshot("g1", captured, SnapshotStage.OPEN, home_spread=-50.0)

    def test_relocation_aliases_follow_schedule_season(self):
        self.assertEqual(schedule_team_code("LA", 2015), "STL")
        self.assertEqual(schedule_team_code("LAC", 2016), "SD")
        self.assertEqual(schedule_team_code("LV", 2019), "OAK")
        self.assertEqual(schedule_team_code("LA", 2016), "LA")

    def test_odds_join_is_date_aware_and_rejects_duplicate_quotes(self):
        rows = pd.DataFrame([
            {"date": "2015-09-13", "season": 2015, "home_team": "LA", "away_team": "SEA"},
            {"date": "2016-01-03", "season": 2015, "home_team": "LA", "away_team": "SEA"},
        ])
        prepared = prepare_odds_for_schedule_join(rows)
        self.assertEqual(set(prepared.home_team), {"STL"})
        duplicate = pd.concat([rows.iloc[[0]], rows.iloc[[0]]], ignore_index=True)
        with self.assertRaisesRegex(ValueError, "not unique"):
            prepare_odds_for_schedule_join(duplicate)

    def test_feature_store_contract_rejects_duplicate_or_unshifted_rows(self):
        base = {
            "game_id": "2025_01_DAL_PHI", "season": 2025, "week": 1,
            "gameday": "2025-09-04", "home_team": "PHI", "away_team": "DAL",
            "home_score": 20, "away_score": 17, "margin": 3, "total": 37,
            "schedule_away_spread": 2.5, "spread_line": -2.5,
            "total_line": 45.5, "home_rest": 7,
            "away_rest": 7, "roof": "outdoors", "surface": "grass", "div_game": 1,
            "home_games_in_ewma": 1, "away_games_in_ewma": 1,
            "stats_through_week": 0, "feature_timing_rule": HISTORICAL_FEATURE_TIMING,
        }
        valid = validate_feature_store(pd.DataFrame([base]), season_from=2014, season_to=2025)
        self.assertTrue(valid["passed"])
        invalid = validate_feature_store(pd.DataFrame([base, base]), season_from=2014, season_to=2025)
        self.assertFalse(invalid["passed"])
        self.assertTrue(any("duplicate game_id" in error for error in invalid["errors"]))

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
