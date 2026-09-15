import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from ml.nfl.features import ewma_features
from ml.nfl.next_round import OVERLAY_POLICY, build


class NextRoundTests(unittest.TestCase):
    def test_overlay_policy_has_no_ambiguous_tier_membership(self):
        groups = [set(OVERLAY_POLICY[name]) for name in ("t1_included_points", "t2_included_points",
                                                         "t3_included_gate_zero_points", "shadow_no_price",
                                                         "execution_only", "discarded")]
        self.assertEqual(sum(map(len, groups)), len(set().union(*groups)))
        self.assertEqual(OVERLAY_POLICY["t1_included_points"][0], "t1_team_strength")
        self.assertEqual(OVERLAY_POLICY["t3_included_gate_zero_points"], ("t3_confluence",))

    def test_retention_accepts_full_prior_state(self):
        stats = pd.DataFrame([
            {"season": 2024, "week": 18, "team": "A", "off_epa": 2.0},
            {"season": 2025, "week": 1, "team": "A", "off_epa": 0.0},
        ])
        result = ewma_features(stats, prior_season_retention=1.0)
        row = result[(result.season == 2025) & (result.team == "A")].iloc[0]
        self.assertGreater(row.off_epa, 0.0)

    def test_next_round_fails_closed_without_timestamped_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            predictions = root / "predictions.csv"
            live = root / "live.json"
            output = root / "output.json"
            pd.DataFrame([{"game_id": "g1", "ridge_total": 44.0}]).to_csv(predictions, index=False)
            live.write_text(json.dumps({"games": []}), encoding="utf-8")
            result = build(predictions, live, output)
            self.assertEqual(result["status"], "blocked_live_inputs_incomplete")
            self.assertFalse(result["staking_enabled"])
            self.assertTrue(output.exists())


if __name__ == "__main__":
    unittest.main()
