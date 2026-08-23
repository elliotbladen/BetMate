import unittest
from racing_engine.sectional_adjustment import _clip
from racing_engine.sectional_adjustment_evaluation import _adjust, _fit


class SectionalAdjustmentTests(unittest.TestCase):
    def test_zero_is_available_and_selected_for_unhelpful_signal(self):
        rows=[({"achievement":1.0,"trip":0.0,"steward":0.0},-1.0) for _ in range(10)]
        self.assertEqual(_fit(rows,("achievement",))["achievement"],0.0)

    def test_adjustment_is_capped(self):
        row={"achievement":4.0,"trip":4.0,"steward":4.0}
        self.assertEqual(_adjust(row,{"achievement":1.5,"trip":1.5,"steward":1.0}),3)

    def test_clip_is_symmetric(self):
        self.assertEqual(_clip(-5,-3,3),-3)
        self.assertEqual(_clip(5,-3,3),3)


if __name__ == "__main__": unittest.main()
