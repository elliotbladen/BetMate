import unittest

import numpy as np
import pandas as pd

from racing_engine.expected_tempo_model import LABELS, chronological_folds, classification_metrics


class ExpectedTempoModelTests(unittest.TestCase):
    def test_folds_are_strictly_chronological_and_keep_dates_together(self):
        frame = pd.DataFrame({"race_date": pd.to_datetime([
            "2024-08-31", "2024-09-01", "2024-09-01", "2025-03-01"
        ])})
        folds = chronological_folds(frame)
        _, _, train, test = folds[0]
        self.assertEqual(train.tolist(), [True, False, False, False])
        self.assertEqual(test.tolist(), [False, True, True, False])

    def test_probability_metrics_reward_correct_forecast(self):
        y = np.array(LABELS)
        strong = np.full((4, 4), 0.01)
        for index in range(4):
            strong[index, index] = 0.97
        weak = np.full((4, 4), 0.25)
        self.assertLess(classification_metrics(y, strong)["log_loss"], classification_metrics(y, weak)["log_loss"])
        self.assertEqual(classification_metrics(y, strong)["accuracy"], 1.0)


if __name__ == "__main__":
    unittest.main()
