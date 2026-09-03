import importlib.util
import json
import sys
import types
import unittest
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "cloud"))
sys.path.insert(0, str(ROOT / "RacingEngine"))
if "requests" not in sys.modules:
    sys.modules["requests"] = types.SimpleNamespace()
SPEC = importlib.util.spec_from_file_location("race_day_tempo_worker", ROOT / "cloud" / "race_day_tempo_worker.py")
tempo = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(tempo)


class CloudTempoWorkerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = json.loads((ROOT / "cloud" / "tempo_model_bundle.json").read_text())

    def test_group_and_going_parsing(self):
        self.assertEqual(tempo.going_bucket("Heavy 9"), "heavy")
        self.assertEqual(tempo.group_grade("Group 1 WFA"), 1)
        self.assertIsNone(tempo.group_grade("BM 78"))

    def test_v0_probabilities_sum_to_one(self):
        probabilities, scores = tempo.v0(self.bundle, "NSW", 1200, "good", 1)
        self.assertAlmostEqual(sum(probabilities.values()), 1.0)
        self.assertEqual(set(scores), {"early", "middle", "late"})

    def test_going_change_resets_shadow_evidence(self):
        prior = [{"going_bucket":"good","distance_metres":1200,"race_number":1,"coverage":1,
                  "scores":{"early":1,"middle":1,"late":1}}]
        target = {"going_bucket":"heavy","distance_metres":1200,"race_number":2,
                  "v0_scores":{"early":0,"middle":0,"late":0}}
        scores, reliability, count = tempo.shadow_state(prior, target, 0.5)
        self.assertEqual(count, 0); self.assertEqual(reliability, 0)
        self.assertEqual(scores, target["v0_scores"])

    def test_early_is_held_and_middle_late_are_capped(self):
        prior = [{"going_bucket":"good","distance_metres":1200,"race_number":1,"coverage":1,
                  "scores":{"early":2,"middle":4,"late":-4}}]
        target = {"going_bucket":"good","distance_metres":1200,"race_number":2,
                  "v0_scores":{"early":0.2,"middle":0.1,"late":-0.1}}
        scores, _, count = tempo.shadow_state(prior, target, 0.5)
        self.assertEqual(count, 1); self.assertEqual(scores["early"], 0.2)
        self.assertLessEqual(abs(scores["middle"]-0.1), 0.5)
        self.assertLessEqual(abs(scores["late"]+0.1), 0.5)

    def test_polling_window_uses_card_times(self):
        card = [{"time":"2026-09-05T02:00:00Z"},{"time":"2026-09-05T06:00:00Z"}]
        config = {"active_window_minutes_before_first":90,"active_window_minutes_after_last":120}
        self.assertTrue(tempo.card_is_active(card, datetime(2026,9,5,1,0,tzinfo=timezone.utc), config))
        self.assertFalse(tempo.card_is_active(card, datetime(2026,9,4,20,0,tzinfo=timezone.utc), config))


if __name__ == "__main__": unittest.main()
