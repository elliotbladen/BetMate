import gzip
import sqlite3
import tempfile
import unittest
from pathlib import Path

from build_seed import build_seed


class BuildSeedTests(unittest.TestCase):
    def test_excludes_only_derived_row_data_and_retains_schemas(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.sqlite"
            output = root / "seed.sql.gz"
            connection = sqlite3.connect(source)
            connection.executescript(
                """
                CREATE TABLE horses (id INTEGER PRIMARY KEY, name TEXT NOT NULL);
                CREATE TABLE run_performances (id INTEGER PRIMARY KEY, rating REAL);
                CREATE TABLE horse_rating_states (id INTEGER PRIMARY KEY, rating REAL);
                INSERT INTO horses VALUES (1, 'Test Horse');
                INSERT INTO run_performances VALUES (1, 101.0);
                INSERT INTO horse_rating_states VALUES (1, 102.0);
                """
            )
            connection.commit()
            connection.close()

            build_seed(source, output)

            restored = sqlite3.connect(":memory:")
            with gzip.open(output, "rt", encoding="utf-8") as seed:
                restored.executescript(seed.read())
            self.assertEqual(restored.execute("SELECT name FROM horses").fetchone()[0], "Test Horse")
            self.assertEqual(restored.execute("SELECT count(*) FROM run_performances").fetchone()[0], 0)
            self.assertEqual(restored.execute("SELECT count(*) FROM horse_rating_states").fetchone()[0], 0)
            restored.close()


if __name__ == "__main__":
    unittest.main()
