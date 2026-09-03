import unittest

from racing_engine.rnsw import validate_report_date


class RacingNswReportDateTests(unittest.TestCase):
    def test_accepts_requested_report_date(self):
        validate_report_date("29 August 2026 - 12:05", "2026-08-29")

    def test_rejects_recycled_archive_date(self):
        with self.assertRaisesRegex(ValueError, "archive returned 2020-08-29"):
            validate_report_date("29 August 2020 - 12:05", "2026-08-29")

    def test_legacy_report_without_extractable_date_is_unchanged(self):
        validate_report_date("Race 1: Example Handicap - 1200m", "2026-08-29")


if __name__ == "__main__":
    unittest.main()
