import unittest

from racing_engine.horse_ability_v2_3 import CONFIGS,configured_state


class HorseAbilityV23Tests(unittest.TestCase):
    def test_configs_are_predeclared_and_named(self):
        self.assertEqual(len({config.name for config in CONFIGS}),len(CONFIGS))
        self.assertEqual(CONFIGS[0].name,"baseline")

    def test_recent_improvement_raises_trajectory_candidate(self):
        history=[("2026-01-01",90),("2026-02-01",95),("2026-03-01",110)]
        baseline=configured_state(history,"2026-03-02",CONFIGS[0])
        trajectory=configured_state(history,"2026-03-02",CONFIGS[3])
        self.assertGreater(trajectory.ability_rating,baseline.ability_rating)

    def test_future_run_is_excluded(self):
        config=CONFIGS[1];base=configured_state([("2026-01-01",100)],"2026-02-01",config)
        future=configured_state([("2026-01-01",100),("2026-03-01",150)],"2026-02-01",config)
        self.assertEqual(base,future)


if __name__=="__main__":unittest.main()
