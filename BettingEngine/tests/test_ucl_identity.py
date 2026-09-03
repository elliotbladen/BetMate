import unittest

from ml.football.ucl_identity import build_alias_index, normalize_club, validate_match


CLUBS = [{"club_id": "arsenal", "canonical_name": "Arsenal", "aliases": ["Arsenal FC"],
          "country": "England", "domestic_league": "EPL", "valid_from": "2014/15", "valid_to": ""},
         {"club_id": "psg", "canonical_name": "Paris Saint-Germain", "aliases": ["PSG"],
          "country": "France", "domestic_league": "Ligue 1", "valid_from": "2014/15", "valid_to": ""}]


class UCLIdentityTests(unittest.TestCase):
    def test_aliases_resolve_to_one_canonical_id(self):
        index = build_alias_index(CLUBS)
        self.assertEqual(normalize_club("Arsenal FC", index), "arsenal")
        self.assertEqual(normalize_club("PSG", index), "psg")

    def test_ambiguous_alias_is_rejected(self):
        clubs = CLUBS + [{"club_id": "other", "canonical_name": "Other", "aliases": ["PSG"],
                          "country": "X", "domestic_league": "Y", "valid_from": "2020/21", "valid_to": ""}]
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            build_alias_index(clubs)

    def test_match_contract_requires_utc_and_distinct_clubs(self):
        match = {"match_id": "ucl-2026-01", "season": "2026/27", "stage": "league_phase",
                 "kickoff_utc": "2026-09-08T19:00:00Z", "home_club_id": "arsenal", "away_club_id": "psg",
                 "home_goals": 2, "away_goals": 1, "source": "uefa", "source_published_at_utc": "2026-09-09T00:00:00Z"}
        self.assertEqual(validate_match(match)["identity_contract_version"], "ucl-identity-v1")


if __name__ == "__main__":
    unittest.main()
