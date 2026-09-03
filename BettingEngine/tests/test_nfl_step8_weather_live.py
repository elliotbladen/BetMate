from datetime import datetime, timezone
import unittest

from ml.nfl.step8_weather_live import normalize_forecast


class NFLStep8WeatherLiveTests(unittest.TestCase):
    def test_kickoff_window_uses_only_nearby_forecast_hours(self):
        payload = {"hourly": {
            "time": ["2026-09-10T00:00", "2026-09-10T01:00", "2026-09-10T02:00", "2026-09-10T03:00", "2026-09-10T04:00"],
            "temperature_2m": [60, 61, 62, 63, 64], "precipitation": [0, .1, .2, .3, .4],
            "wind_speed_10m": [5, 10, 15, 20, 25], "wind_gusts_10m": [8, 13, 18, 23, 28],
        }}
        result = normalize_forecast(payload, datetime(2026, 9, 10, 1, tzinfo=timezone.utc))
        self.assertEqual(result["forecast_hours"], 4)
        self.assertEqual(result["wind_mph_max"], 25)
        self.assertAlmostEqual(result["precipitation_in_sum"], 1.0)


if __name__ == "__main__":
    unittest.main()
