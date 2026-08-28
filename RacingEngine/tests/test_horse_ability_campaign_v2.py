import unittest

from racing_engine.horse_ability_campaign_v2 import CONFIGS_CAMPAIGN,campaign_state


class HorseAbilityCampaignV2Tests(unittest.TestCase):
    def test_no_decay_preserves_base_state(self):
        history=[("2025-01-01",115),("2025-02-01",116),("2025-03-01",117)]
        state=campaign_state(history,"2026-01-01",CONFIGS_CAMPAIGN[0])
        self.assertGreater(state.ability_rating,110)

    def test_layoff_decay_moves_toward_neutral_and_adds_uncertainty(self):
        history=[("2025-01-01",115),("2025-02-01",116),("2025-03-01",117)]
        base=campaign_state(history,"2026-01-01",CONFIGS_CAMPAIGN[0])
        decayed=campaign_state(history,"2026-01-01",CONFIGS_CAMPAIGN[2])
        self.assertLess(decayed.ability_rating,base.ability_rating)
        self.assertGreater(decayed.uncertainty,base.uncertainty)


if __name__=="__main__":unittest.main()
