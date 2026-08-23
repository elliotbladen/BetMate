from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from racing_engine.horse_identity import build_registry, clean_name, durable_id, identity_key
from racing_engine.storage import RacingStore


class HorseIdentityTests(unittest.TestCase):
    def test_rnsw_layout_debris_and_country_suffix_are_removed(self) -> None:
        cleaned, changes = clean_name("rnsw-authorised", "LIFESAVER 3 67.1")
        self.assertEqual(cleaned, "LIFESAVER")
        self.assertIn("removed_rnsw_position_time_layout_suffix", changes)
        self.assertEqual(clean_name("racing-com-rv-authorised", "Palmetto (NZ)")[0], "Palmetto")

    def test_identity_key_handles_case_spacing_and_punctuation(self) -> None:
        self.assertEqual(identity_key("Here To Shock"), identity_key("Here to Shock"))
        self.assertEqual(identity_key("Bois D'argent"), "boisdargent")
        self.assertNotEqual(identity_key("Red Star"), identity_key("Blue Star"))
        self.assertEqual(durable_id("palmetto"), durable_id("palmetto"))

    def test_registry_links_variants_without_rewriting_source_names(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            store = RacingStore(Path(temporary_directory) / "test.sqlite")
            try:
                self._race(store, "rnsw-authorised", "2026-01-01", "PALMETTO 1 70.0")
                self._race(store, "racing-com-rv-authorised", "2026-02-01", "Palmetto (NZ)")
                first = build_registry(store)
                second = build_registry(store)
                self.assertEqual(first["horses"], 2)  # Palmetto plus each race's Other horse
                self.assertEqual(second["new_horses"], 0)
                links = store.connection.execute(
                    "SELECT horse_id,source_horse_name,cleaned_horse_name FROM runner_horse_links WHERE source_horse_name LIKE 'PALMETTO%' OR source_horse_name LIKE 'Palmetto%'"
                ).fetchall()
                self.assertEqual(len({row["horse_id"] for row in links}), 1)
                self.assertEqual({row["source_horse_name"] for row in links}, {"PALMETTO 1 70.0", "Palmetto (NZ)"})
                self.assertEqual({row["cleaned_horse_name"].lower() for row in links}, {"palmetto"})
                self.assertEqual(store.connection.execute("SELECT count(*) FROM runner_horse_links").fetchone()[0], 4)
                store.connection.execute(
                    "UPDATE horse_aliases SET canonical_name='Reviewed Palmetto',review_status='reviewed' WHERE source_horse_name='Palmetto (NZ)'")
                store.connection.commit()
                build_registry(store)
                reviewed = store.connection.execute(
                    "SELECT canonical_name,review_status FROM horse_aliases WHERE source_horse_name='Palmetto (NZ)'").fetchone()
                self.assertEqual(tuple(reviewed), ("Reviewed Palmetto", "reviewed"))
            finally:
                store.close()

    def test_too_short_identity_is_sent_to_review(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            store = RacingStore(Path(temporary_directory) / "test.sqlite")
            try:
                self._race(store, "test", "2026-01-01", "X")
                report = build_registry(store)
                self.assertEqual(report["open_reviews"], 1)
                self.assertEqual(store.connection.execute(
                    "SELECT reason FROM horse_identity_reviews").fetchone()[0], "empty_or_too_short_identity_key")
            finally:
                store.close()

    @staticmethod
    def _race(store: RacingStore, source: str, race_date: str, name: str) -> None:
        store.upsert_result(source=source, race_date=race_date, state="NSW", track_slug="test", race_number=1,
            official_time_seconds=70.0, track_condition="Good 4", rail_position="True", source_url=None,
            raw_race={}, runners=[
                {"runner_number": 1, "runner_name": name, "finish_position": 1,
                 "finish_time_seconds": 70.0, "beaten_lengths": 0.0},
                {"runner_number": 2, "runner_name": "Other", "finish_position": 2,
                 "finish_time_seconds": 70.2, "beaten_lengths": 1.0},
            ])


if __name__ == "__main__":
    unittest.main()
