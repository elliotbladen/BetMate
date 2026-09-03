import unittest
import pandas as pd

from ml.nfl.step8_t6_weather import weather_features


class NFLStep8T6Tests(unittest.TestCase):
    def test_dome_weather_is_not_treated_as_outdoor_weather(self):
        rows = pd.DataFrame([{"game_id": "g1", "roof": "dome", "temp": 20, "wind": 30}])
        result = weather_features(rows).iloc[0]
        self.assertEqual(result.open_air, 0)
        self.assertEqual(result.weather_available, 0)
        self.assertEqual(result.wind_mph_open_air, 0)

    def test_missing_open_air_weather_has_explicit_availability_zero(self):
        rows = pd.DataFrame([{"game_id": "g1", "roof": "outdoors", "temp": None, "wind": None}])
        result = weather_features(rows).iloc[0]
        self.assertEqual(result.open_air, 1)
        self.assertEqual(result.weather_available, 0)


if __name__ == "__main__":
    unittest.main()
