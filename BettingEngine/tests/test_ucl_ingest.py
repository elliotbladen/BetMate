import tempfile
import unittest
from pathlib import Path

from ml.football.ucl_ingest import parse_file


class UCLIngestTests(unittest.TestCase):
    def test_parser_preserves_stage_and_score(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "cl.txt"
            path.write_text("= UEFA Champions League 2024/25\n▪ League, Matchday 1\n  Tue Sep 17 2024\n    18:45  Arsenal FC (ENG) v Paris Saint-Germain FC (FRA) 2-0 (1-0)\n", encoding="utf-8")
            rows = parse_file(path, "2024/25")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["stage"], "league_phase")
        self.assertEqual(rows[0]["home_goals"], 2)
        self.assertEqual(rows[0]["kickoff_precision"], "date_only")


if __name__ == "__main__":
    unittest.main()
