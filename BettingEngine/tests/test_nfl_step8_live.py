from datetime import datetime, timezone
import unittest

from ml.nfl.step8_live_tiers import LiveTierInput, _mixed_profile, validate_record


class NFLStep8LiveTests(unittest.TestCase):
    def test_source_newer_than_cutoff_is_rejected(self):
        item = LiveTierInput(
            game_id="g1", as_of_utc=datetime(2026, 9, 1, tzinfo=timezone.utc),
            kickoff_at_utc=datetime(2026, 9, 2, tzinfo=timezone.utc),
            source_timestamps={"qb": datetime(2026, 9, 1, 1, tzinfo=timezone.utc)},
            home_starter_probability=None, away_starter_probability=None,
        )
        with self.assertRaisesRegex(ValueError, "newer than as_of"):
            item.validate()

    def test_probability_requires_both_player_profiles(self):
        record = {
            "game_id": "g1", "as_of_utc": "2026-09-01T00:00:00Z",
            "kickoff_at_utc": "2026-09-02T00:00:00Z", "source_timestamps": {},
            "home": {"qb": {"starter_probability": 0.75, "starter_id": "a"}},
            "away": {"qb": {"starter_probability": None}},
        }
        errors = validate_record(record)
        self.assertTrue(any("backup_id" in error for error in errors))
        self.assertTrue(any("starter_profile" in error for error in errors))

    def test_starter_backup_profile_is_probability_weighted(self):
        profile = _mixed_profile({
            "starter_probability": 0.75, "qb_change_probability": 0.25,
            "starter_profile": {
                "qb_epa_posterior": 0.2, "qb_success_posterior": 0.5,
                "qb_sack_rate_posterior": 0.04, "qb_turnover_rate_posterior": 0.02,
                "qb_scramble_rate_posterior": 0.03, "qb_prior_dropbacks": 600,
            },
            "backup_profile": {
                "qb_epa_posterior": -0.2, "qb_success_posterior": 0.3,
                "qb_sack_rate_posterior": 0.08, "qb_turnover_rate_posterior": 0.04,
                "qb_scramble_rate_posterior": 0.01, "qb_prior_dropbacks": 100,
            },
        })
        self.assertAlmostEqual(profile["qb_epa_posterior"], 0.1)
        self.assertAlmostEqual(profile["qb_prior_dropbacks"], 475.0)
        self.assertEqual(profile["qb_change"], 0.25)


if __name__ == "__main__":
    unittest.main()
