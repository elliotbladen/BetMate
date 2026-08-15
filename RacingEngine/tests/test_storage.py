from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from racing_engine.storage import RacingStore
from racing_engine.results_import import import_results, import_sectionals
from racing_engine.ratings import build_ratings
from racing_engine.price_card import price_card
from racing_engine.performance import run_pipeline


class RacingStoreTests(unittest.TestCase):
    def test_upsert_card_stores_runner_metadata(self) -> None:
        meeting = {"track": "Rosehill", "slug": "rosehill"}
        card = {
            "raceNumber": 1,
            "raceName": "Midway Handicap",
            "distance": "1500m",
            "condition": "Soft 5",
            "runners": [
                {"number": 1, "name": "Example Runner", "jockey": "J. Rider", "trainer": "T. Trainer", "barrier": 4, "weight": 58.5, "form": "1121", "scratched": False}
            ],
        }
        with TemporaryDirectory() as temporary_directory:
            store = RacingStore(Path(temporary_directory) / "racing.sqlite")
            try:
                self.assertEqual(store.upsert_card("2026-08-15", "NSW", meeting, [card]), 1)
                row = store.connection.execute("SELECT runner_name, jockey, trainer, barrier FROM runners").fetchone()
                self.assertEqual(tuple(row), ("Example Runner", "J. Rider", "T. Trainer", 4))
            finally:
                store.close()

    def test_result_and_sectional_records_are_stored_separately_from_card(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            store = RacingStore(Path(temporary_directory) / "racing.sqlite")
            try:
                store.upsert_result(
                    source="test", race_date="2026-08-01", state="NSW", track_slug="randwick", race_number=1,
                    official_time_seconds=82.44, track_condition="Good 4", rail_position="True", source_url="https://example.test/result",
                    raw_race={"race": 1}, runners=[{"runner_number": 1, "runner_name": "Example Winner", "finish_position": 1, "beaten_lengths": 0.0}],
                )
                store.upsert_sectionals([{
                    "source": "test", "race_date": "2026-08-01", "state": "NSW", "track_slug": "randwick", "race_number": 1,
                    "runner_number": 1, "marker_metres": 600, "section_seconds": 11.2, "position_at_marker": 1,
                    "distance_travelled_metres": 0.0, "speed_kmh": 64.3, "source_url": "https://example.test/sectionals",
                }])
                result = store.connection.execute("SELECT official_time_seconds FROM race_results").fetchone()
                sectional = store.connection.execute("SELECT section_seconds FROM runner_sectionals").fetchone()
                self.assertEqual(result[0], 82.44)
                self.assertEqual(sectional[0], 11.2)
            finally:
                store.close()

    def test_canonical_csv_templates_import(self) -> None:
        root = Path(__file__).resolve().parents[1]
        with TemporaryDirectory() as temporary_directory:
            store = RacingStore(Path(temporary_directory) / "racing.sqlite")
            try:
                self.assertEqual(import_results(store, root / "templates" / "results.csv", "test"), 1)
                self.assertEqual(import_sectionals(store, root / "templates" / "sectionals.csv", "test"), 2)
                self.assertEqual(store.connection.execute("SELECT count(*) FROM runner_results").fetchone()[0], 2)
                self.assertEqual(store.connection.execute("SELECT count(*) FROM runner_sectionals").fetchone()[0], 2)
            finally:
                store.close()

    def test_lengths_rating_and_price_book(self) -> None:
        meeting = {"track": "Rosehill", "slug": "rosehill"}
        card = {"raceNumber": 1, "raceName": "Example", "distance": "1200m", "runners": [
            {"number": 1, "name": "Fast Horse", "scratched": False},
            {"number": 2, "name": "Slow Horse", "scratched": False},
        ]}
        with TemporaryDirectory() as temporary_directory:
            store = RacingStore(Path(temporary_directory) / "racing.sqlite")
            try:
                store.upsert_result(
                    source="test", race_date="2026-08-01", state="NSW", track_slug="randwick", race_number=1,
                    official_time_seconds=70.0, track_condition="Good 4", rail_position="True", source_url=None, raw_race={},
                    runners=[
                        {"runner_number": 1, "runner_name": "Fast Horse", "finish_position": 1, "beaten_lengths": 0.0},
                        {"runner_number": 2, "runner_name": "Slow Horse", "finish_position": 2, "beaten_lengths": 5.0},
                    ],
                )
                ratings = build_ratings(store, "2026-08-15")
                self.assertGreater(ratings["fasthorse"].rating, ratings["slowhorse"].rating)
                store.upsert_card("2026-08-15", "NSW", meeting, [card])
                priced = price_card(store, "2026-08-15", "NSW")
                probabilities = [runner["win_probability"] for runner in priced[0]["runners"]]
                self.assertAlmostEqual(sum(probabilities), 1.0, places=4)
                self.assertLess(priced[0]["runners"][0]["fair_odds"], priced[0]["runners"][1]["fair_odds"])
            finally:
                store.close()

    def test_historical_performance_pipeline_stores_pars_and_states(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            store = RacingStore(Path(temporary_directory) / "racing.sqlite")
            try:
                store.upsert_result(
                    source="test", race_date="2026-08-01", state="VIC", track_slug="flemington", race_number=1,
                    distance_metres=1200, official_time_seconds=70.0, track_condition="Good 4", rail_position="True",
                    source_url=None, raw_race={}, runners=[
                        {"runner_number": 1, "runner_name": "Rated Horse", "finish_position": 1, "beaten_lengths": 0.0, "finish_time_seconds": 70.0},
                        {"runner_number": 2, "runner_name": "Other Horse", "finish_position": 2, "beaten_lengths": 2.0, "finish_time_seconds": 70.34},
                    ],
                )
                store.upsert_sectionals([
                    {"source": "test", "race_date": "2026-08-01", "track_slug": "flemington", "race_number": 1, "runner_number": 1, "marker_metres": 0, "section_seconds": 22.1},
                    {"source": "test", "race_date": "2026-08-01", "track_slug": "flemington", "race_number": 1, "runner_number": 2, "marker_metres": 0, "section_seconds": 22.5},
                    {"source": "test", "race_date": "2026-08-01", "track_slug": "flemington", "race_number": 1, "runner_number": 3, "marker_metres": 0, "section_seconds": 22.3},
                ])
                result = run_pipeline(store, "2026-08-15", min_par_sample=1)
                self.assertEqual(result["performances"], 2)
                self.assertEqual(result["horse_states"], 2)
                self.assertEqual(store.connection.execute("SELECT count(*) FROM track_pars").fetchone()[0], 1)
                state = store.connection.execute("SELECT overall_rating FROM horse_rating_states WHERE horse_key = 'ratedhorse'").fetchone()[0]
                self.assertGreater(state, 100.0)
            finally:
                store.close()


if __name__ == "__main__":
    unittest.main()
