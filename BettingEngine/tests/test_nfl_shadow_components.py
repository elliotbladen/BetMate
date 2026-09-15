import unittest

from ml.nfl.shadow_components import SHADOW_COMPONENTS, apply_research_caps, component_names


class ShadowComponentTests(unittest.TestCase):
    def test_four_tracks_are_registered_once(self):
        self.assertEqual(len(component_names()), 4)
        self.assertEqual(len(component_names()), len(set(component_names())))
        self.assertTrue(all(item.status == "shadow_only" for item in SHADOW_COMPONENTS))

    def test_caps_are_individual_and_not_official_pricing(self):
        value = apply_research_caps(40.0, {
            "drive_red_zone_residual": 99,
            "turnover_luck_residual": -99,
        })
        self.assertEqual(value, 41.5)

    def test_unknown_component_is_rejected(self):
        with self.assertRaises(KeyError):
            apply_research_caps(0, {"t7_scheme": 1})


if __name__ == "__main__":
    unittest.main()
