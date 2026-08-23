from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from racing_engine.class_prior_research import research
from racing_engine.storage import RacingStore


class ClassPriorResearchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        self.store = RacingStore(Path(self.temporary_directory.name) / "test.sqlite")

    def tearDown(self) -> None:
        self.store.close(); self.temporary_directory.cleanup()

    def add_race(self, date: str, number: int, state: str, track: str, family: str,
                 ratings: list[float | None], benchmark: int | None = None) -> None:
        source = "test"
        self.store.upsert_result(source=source, race_date=date, state=state, track_slug=track,
            race_number=number, official_time_seconds=70.0, track_condition="Good 4", rail_position="True",
            source_url=None, raw_race={}, runners=[
                {"runner_number": index, "runner_name": f"Horse {number} {index}",
                 "finish_position": index, "beaten_lengths": index - 1,
                 "official_handicap_rating": rating}
                for index, rating in enumerate(ratings, start=1)])
        self.store.upsert_race_classification({"source": source, "race_date": date, "track_slug": track,
            "race_number": number, "class_family": family, "benchmark": benchmark,
            "raw_class_text": family, "parser_version": "test"})

    def test_sparse_child_is_shrunk_toward_parent(self) -> None:
        for number in range(1, 7):
            self.add_race("2024-01-01", number, "NSW", "randwick", "benchmark", [70, 72, 74, 76], 78)
        self.add_race("2024-01-02", 1, "NSW", "rosehill", "benchmark", [95, 96, 97, 98], 78)
        report = research(self.store, "2025-01-01")
        sparse = next(row for row in report["levels"]["venue_class"] if row["group_key"].endswith("rosehill"))
        parent = next(row for row in report["levels"]["class_family"] if row["group_key"] == "NSW|benchmark")
        self.assertLess(sparse["shrinkage_weight"], 0.5)
        self.assertLess(abs(sparse["shrunk_field_rating"] - parent["shrunk_field_rating"]),
                        abs(sparse["raw_mean_field_rating"] - parent["shrunk_field_rating"]))

    def test_missing_rating_races_are_explicitly_excluded(self) -> None:
        self.add_race("2024-01-01", 1, "NSW", "randwick", "benchmark", [70, None, None, None])
        report = research(self.store, "2025-01-01")
        self.assertEqual(report["eligible_races"], 0)
        self.assertEqual(report["exclusion_reasons"]["fewer_than_three_rated_runners"], 1)

    def test_future_race_does_not_change_prior_cutoff(self) -> None:
        self.add_race("2024-01-01", 1, "NSW", "randwick", "benchmark", [70, 72, 74, 76])
        before = research(self.store, "2025-01-01")
        self.add_race("2026-01-01", 2, "NSW", "randwick", "group", [110, 112, 114, 116])
        after = research(self.store, "2025-01-01")
        self.assertEqual(before["levels"], after["levels"])

    def test_research_rows_are_idempotent_and_versioned(self) -> None:
        self.add_race("2024-01-01", 1, "VIC", "flemington", "listed", [82, 84, 86, 88])
        first = research(self.store, "2025-01-01")
        second = research(self.store, "2025-01-01")
        self.assertEqual(first["levels"], second["levels"])
        count = self.store.connection.execute("SELECT count(*) FROM class_prior_research").fetchone()[0]
        self.assertEqual(count, 5)


if __name__ == "__main__":
    unittest.main()
