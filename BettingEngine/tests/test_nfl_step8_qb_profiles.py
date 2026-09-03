from datetime import datetime, timezone
import unittest

from ml.nfl.step8_live_tiers import _parse_aware


class NFLStep8QBProfileTests(unittest.TestCase):
    def test_timestamp_parser_rejects_naive_values(self):
        with self.assertRaisesRegex(ValueError, "timezone-aware"):
            _parse_aware("2026-09-01T12:00:00", "source")

    def test_timestamp_parser_normalises_to_utc(self):
        stamp = _parse_aware("2026-09-01T12:00:00+10:00", "source")
        self.assertEqual(stamp, datetime(2026, 9, 1, 2, tzinfo=timezone.utc))


if __name__ == "__main__":
    unittest.main()
