# NFL Step 8H — timestamped live-weather collector

## Outcome

The Open-Meteo forecast collector, immutable archive and Week 1 stadium registry
are implemented. Collection is currently blocked by design because none of the
16 stadium coordinates has been independently verified.

The registry already contains canonical game, stadium ID, stadium name and roof
from the frozen nflverse schedule. Latitude, longitude, coordinate source,
verification timestamp and verification flag remain blank. City-centre weather
and unverified third-party coordinate lists are not accepted substitutes.

## Forecast contract

For each verified stadium the collector requests hourly temperature,
precipitation, 10-metre wind and wind gusts from kickoff through the following
three hours. Kickoff is converted from NFL Eastern schedule time to UTC before
matching. Raw provider responses and normalized game rows are written once with
a capture timestamp and SHA-256 manifest.

The normalized row records provider, coordinates, kickoff, capture time,
forecast window, mean temperature, precipitation sum, maximum wind and maximum
gust. It is always a T6 totals shadow with staking disabled.

## Current fail-closed result

- Week 1 games: 16.
- Verified stadium coordinates: 0.
- Forecast API calls made: 0.
- Forecasts archived: 0.
- Status: `unresolved_no_weather_capture`.

## Evidence and limitations

Open-Meteo's official forecast API accepts WGS84 latitude/longitude and returns
hourly forecasts including temperature, precipitation, wind speed and gusts.
Its default forecast is continuously updated, so BetMate's own capture timestamp
is essential. nflverse does not currently maintain a stadium-location mapping;
its public tracker contains an open feature request for one.

The next safe action is a one-time coordinate review from authoritative stadium
or mapping records. Forecast collection can start after all registry rows pass.
