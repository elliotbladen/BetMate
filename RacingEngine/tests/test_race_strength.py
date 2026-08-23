from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from racing_engine.race_strength import build_race_strength, combine_components
from racing_engine.storage import RacingStore


class RaceStrengthTests(unittest.TestCase):
    def test_reliability_blend_moves_with_field_coverage(self) -> None:
        low = combine_components(class_prior=90, global_prior=80, class_reliability=1,
            field_median=95, field_top4=96, rated_coverage=0.1, field_uncertainty=12)
        high = combine_components(class_prior=90, global_prior=80, class_reliability=1,
            field_median=95, field_top4=96, rated_coverage=1.0, field_uncertainty=4)
        self.assertEqual(low["class_only_rating"], 110)
        self.assertAlmostEqual(low["field_only_rating"], 95.4)
        self.assertLess(abs(low["combined_rating"] - 110), abs(high["combined_rating"] - 110))

    def test_no_evidence_returns_neutral(self) -> None:
        result = combine_components(class_prior=None, global_prior=None, class_reliability=0,
            field_median=100, field_top4=100, rated_coverage=0, field_uncertainty=12)
        self.assertEqual(result["combined_rating"], 100)

    def test_build_uses_prior_class_races_and_separates_result_evidence(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            store = RacingStore(Path(temporary_directory) / "test.sqlite")
            try:
                self._race(store, "2024-01-01", 1, [88, 90, 92, 94])
                self._race(store, "2024-02-01", 2, [80, 82, 84, 86])
                store.connection.execute(
                    """INSERT INTO pre_race_field_strengths
                       (field_model_version,source,race_date,track_slug,race_number,starters,rated_runners,rated_coverage,
                        field_median_rating,rated_only_median_rating,top_four_mean_rating,top_rating,depth_within_five,
                        field_uncertainty,information_cutoff,detail_json,created_at)
                       VALUES ('pre-race-field-v1.0','test','2024-02-01','randwick',2,4,3,.75,101,101,103,105,3,6,
                               '2024-02-01','{}','now')""")
                store.connection.commit()
                first = build_race_strength(store, from_date="2024-02-01", to_date="2024-02-01")
                rating = store.connection.execute("SELECT * FROM race_strength_ratings").fetchone()
                evidence = store.connection.execute("SELECT * FROM post_race_strength_evidence").fetchone()
                self.assertEqual(first["races"], 1)
                self.assertEqual(rating["information_cutoff"], "2024-02-01")
                self.assertEqual(rating["class_prior_level"], "subtype")
                self.assertEqual(evidence["margin_observations"], 4)
                combined_before = rating["combined_rating"]
                store.connection.execute(
                    "UPDATE runner_results SET beaten_lengths=99,finish_time_seconds=999 WHERE race_date='2024-02-01'")
                store.connection.commit()
                build_race_strength(store, from_date="2024-02-01", to_date="2024-02-01")
                combined_after = store.connection.execute("SELECT combined_rating FROM race_strength_ratings").fetchone()[0]
                changed_evidence = store.connection.execute("SELECT winner_time_seconds FROM post_race_strength_evidence").fetchone()[0]
                self.assertEqual(combined_before, combined_after)
                self.assertEqual(changed_evidence, 999)
                self.assertEqual(store.connection.execute("SELECT count(*) FROM race_strength_ratings").fetchone()[0], 1)
            finally:
                store.close()

    @staticmethod
    def _race(store: RacingStore, race_date: str, number: int, ratings: list[float]) -> None:
        store.upsert_result(source="test", race_date=race_date, state="NSW", track_slug="randwick", race_number=number,
            official_time_seconds=70.0, track_condition="Good 4", rail_position="True", source_url=None, raw_race={},
            runners=[{"runner_number": index, "runner_name": f"Horse {number} {index}", "finish_position": index,
                      "beaten_lengths": index - 1, "finish_time_seconds": 70 + index / 10,
                      "official_handicap_rating": rating}
                     for index, rating in enumerate(ratings, start=1)])
        store.upsert_race_classification({"source": "test", "race_date": race_date, "track_slug": "randwick",
            "race_number": number, "class_family": "group", "group_grade": 2,
            "raw_class_text": "Group 2", "parser_version": "test"})


if __name__ == "__main__":
    unittest.main()
