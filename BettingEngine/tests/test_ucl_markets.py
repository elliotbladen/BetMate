import unittest

from ml.football.ucl_markets import no_vig_probabilities, validate_quote, validate_unverified_closing_quote


class UCLMarketsTests(unittest.TestCase):
    def quote(self):
        return {"quote_id": "q1", "market_id": "m1", "market_type": "h2h",
                "captured_at_utc": "2026-09-01T10:00:00Z", "published_at_utc": "2026-09-01T09:00:00Z",
                "source": "book", "outcomes": [{"name": "A", "decimal_odds": 2.0}, {"name": "B", "decimal_odds": 2.0}]}

    def test_no_vig_probabilities_sum_to_one(self):
        self.assertAlmostEqual(sum(no_vig_probabilities([2.0, 3.0])), 1.0)

    def test_quote_is_downstream_only(self):
        result = validate_quote(self.quote(), "2026-09-01T12:00:00Z", "2026-09-08T19:00:00Z")
        self.assertFalse(result["market_fields_used_in_model"])
        self.assertAlmostEqual(result["no_vig_probability"][0], .5)

    def test_quote_after_cutoff_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "timing"):
            validate_quote(self.quote(), "2026-09-01T08:00:00Z", "2026-09-08T19:00:00Z")

    def test_unverified_static_close_is_explicit(self):
        result = validate_unverified_closing_quote({"quote_id": "q1", "market_id": "m1", "market_type": "h2h", "source": "footiqo_1xbet", "outcomes": [{"decimal_odds": 2}, {"decimal_odds": 3}]})
        self.assertEqual(result["closing_status"], "unverified_static_close")


if __name__ == "__main__":
    unittest.main()
