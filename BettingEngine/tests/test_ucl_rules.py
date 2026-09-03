import unittest

from ml.football.ucl_rules import RULES, placement_route, validate_fixture


class UCLRulesTests(unittest.TestCase):
    def test_league_phase_allocation_is_frozen(self):
        self.assertEqual(RULES.league_phase_teams, 36)
        self.assertEqual(RULES.league_phase_matches_per_team, 8)
        self.assertEqual(RULES.opponents_per_pot * RULES.coefficient_pots, 8)
        self.assertFalse(RULES.away_goals_rule)

    def test_placement_routes(self):
        self.assertEqual(placement_route(1), "direct_round_of_16")
        self.assertEqual(placement_route(8), "direct_round_of_16")
        self.assertEqual(placement_route(9), "knockout_phase_play_off")
        self.assertEqual(placement_route(24), "knockout_phase_play_off")
        self.assertEqual(placement_route(25), "eliminated")

    def test_fixture_is_tagged_with_rules_version(self):
        fixture = {"fixture_id": "g1", "season": "2026/27", "stage": "league_phase",
                   "home_club": "ARS", "away_club": "PSG", "kickoff_utc": "2026-09-08T19:00:00Z"}
        result = validate_fixture(fixture)
        self.assertEqual(result["rules_version"], "ucl-2026-27-regulations-v1")
        self.assertEqual(result["qualification_resolution"], "league_table")

    def test_same_club_is_invalid(self):
        fixture = {"fixture_id": "g1", "season": "2026/27", "stage": "final",
                   "home_club": "ARS", "away_club": "ARS", "kickoff_utc": "2027-05-29T19:00:00Z"}
        with self.assertRaisesRegex(ValueError, "must differ"):
            validate_fixture(fixture)


if __name__ == "__main__":
    unittest.main()
