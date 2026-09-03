import unittest

from ml.nfl.step12_promotion_ledger import _empty, promotion_status, validate_row


class NFLStep12PromotionLedgerTests(unittest.TestCase):
    def test_empty_ledger_cannot_promote(self):
        result = promotion_status(_empty())
        self.assertEqual(result["status"], "no_prospective_evidence")
        self.assertFalse(result["promotion_allowed"])

    def test_invalid_coverage_is_rejected(self):
        row = {field: "x" for field in ["prediction_id", "game_id", "threshold_version"]}
        row.update({"season": 2026, "week": 1, "captured_at_utc": "x", "cutoff_utc": "x",
                    "true_opener_verified": False, "obtainable_price_verified": False,
                    "market_coverage": 1.2, "model_edge_points": 1, "closing_line_value": 0,
                    "opening_line_beat": 0, "result": "pending"})
        with self.assertRaisesRegex(ValueError, "market_coverage"):
            validate_row(row)

    def test_threshold_version_is_required(self):
        with self.assertRaisesRegex(ValueError, "missing ledger fields"):
            validate_row({field: "x" for field in ["prediction_id", "game_id"]})


if __name__ == "__main__":
    unittest.main()
