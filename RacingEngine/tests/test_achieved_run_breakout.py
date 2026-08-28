import unittest

from racing_engine.achieved_run_breakout import eligible_breakout


class AchievedRunBreakoutTests(unittest.TestCase):
    def test_requires_all_predeclared_conditions(self):
        self.assertTrue(eligible_breakout(finish_position=1,winning_margin=4,
            prior_starts=1,opposition_reliability=.44))
        self.assertFalse(eligible_breakout(finish_position=2,winning_margin=4,
            prior_starts=1,opposition_reliability=.44))
        self.assertFalse(eligible_breakout(finish_position=1,winning_margin=2.9,
            prior_starts=1,opposition_reliability=.44))
        self.assertFalse(eligible_breakout(finish_position=1,winning_margin=4,
            prior_starts=9,opposition_reliability=.44))
        self.assertFalse(eligible_breakout(finish_position=1,winning_margin=4,
            prior_starts=1,opposition_reliability=.50))


if __name__=="__main__":unittest.main()
