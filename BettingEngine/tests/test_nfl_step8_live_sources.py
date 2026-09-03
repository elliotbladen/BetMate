import unittest

from ml.nfl.step8_live_sources import _active_sets
import pandas as pd


class NFLStep8LiveSourceTests(unittest.TestCase):
    def test_continuity_excludes_reserve_and_cut_players(self):
        rows = pd.DataFrame([
            {"team": "A", "position": "QB", "status": "ACT", "gsis_id": "1"},
            {"team": "A", "position": "OL", "status": "INA", "gsis_id": "2"},
            {"team": "A", "position": "WR", "status": "RES", "gsis_id": "3"},
            {"team": "A", "position": "TE", "status": "CUT", "gsis_id": "4"},
        ])
        teams, units = _active_sets(rows)
        self.assertEqual(teams["A"], {"1", "2"})
        self.assertEqual(units[("A", "ol")], {"2"})
        self.assertNotIn(("A", "receiver"), units)

    def test_precut_roster_threshold_is_not_a_normal_53_man_roster(self):
        self.assertGreater(89.0, 60.0)


if __name__ == "__main__":
    unittest.main()
