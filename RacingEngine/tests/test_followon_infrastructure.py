import csv
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from racing_engine.expansion_readiness import report
from racing_engine.market_prices import coverage, import_csv, normalized_book
from racing_engine.probability_calibration import fit_temperature, temperature_book
from racing_engine.storage import RacingStore


class FollowonInfrastructureTests(unittest.TestCase):
    def test_market_import_is_append_only_and_normalizes_overround(self):
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory); store = RacingStore(root / "test.sqlite")
            try:
                path = root / "prices.csv"
                fields = ["market_source", "source", "race_date", "track_slug", "race_number",
                          "runner_number", "captured_at", "price_type", "decimal_odds"]
                with path.open("w", newline="") as handle:
                    writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader()
                    writer.writerows([
                        dict(zip(fields, ["exchange", "test", "2026-01-01", "x", 1, 1,
                                         "2026-01-01T01:00:00Z", "back", 2.0])),
                        dict(zip(fields, ["exchange", "test", "2026-01-01", "x", 1, 2,
                                         "2026-01-01T01:00:00Z", "back", 2.0]))])
                self.assertEqual(import_csv(store, path)["rows_inserted"], 2)
                self.assertEqual(import_csv(store, path)["rows_inserted"], 0)
                self.assertEqual(coverage(store)["comparison_status"], "READY")
                book = normalized_book([{"decimal_odds": 1.8}, {"decimal_odds": 2.2}])
                self.assertAlmostEqual(sum(row["normalized_probability"] for row in book), 1)
            finally: store.close()

    def test_calibration_is_book_coherent_and_training_gated(self):
        self.assertAlmostEqual(sum(temperature_book([.7, .2, .1], 1.5)), 1)
        self.assertEqual(fit_temperature([])["status"], "INSUFFICIENT_TRAINING_PREDICTIONS")
        fitted = fit_temperature([([.9, .1], 1), ([.8, .2], 1)], [.5, 1, 2])
        self.assertEqual(fitted["temperature"], 2)

    def test_expansion_is_not_ready_with_only_two_states(self):
        with TemporaryDirectory() as temporary_directory:
            store = RacingStore(Path(temporary_directory) / "test.sqlite")
            try:
                self.assertFalse(report(store)["ready_for_national_class_priors"])
            finally: store.close()


if __name__ == "__main__": unittest.main()
