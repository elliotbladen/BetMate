# Wind-adjusted ratings review and rollout plan

**Status:** Randwick tester approved by user; full historical rollout not yet run.  
**Test model:** `dan-aligned-wind-test-randwick-v0.2`  
**Meeting tested:** Royal Randwick, 5 September 2026

## What the Randwick test changed

The test left the Dan-aligned base rating intact and added a separate wind
component to the achieved run. The first version treated wind as a race-wide
correction. Version 0.2 added a simple exposure proxy using the runner's last
available sectional position: runners nearer the front were treated as more
exposed to a headwind or tailwind, while rearward runners received partial
shelter.

The test used the observed Rosebery Sydney Station series as a nearby proxy for
Randwick. It matched the nearest half-hour observation to each scheduled race,
converted source miles per hour to kilometres per hour, and retained source,
station, timestamp, direction, speed and gust fields in `race_weather`.

The Randwick wind pattern was:

* Races 1–3: northerly, about 32–35 km/h;
* Races 4–5: northerly, with stronger gusts;
* Race 6: a shift toward westerly wind;
* Races 7–9: westerly wind around 53–66 km/h, with gusts near 85 km/h;
* Race 10: westerly wind eased to about 34 km/h.

Under the conservative test geometry, the leading changes were:

| Horse | Base | Wind test | Change | Race |
|---|---:|---:|---:|---:|
| Tempted | 103.8 | 102.7 | -1.1 | R8 |
| Headwall | 103.0 | 101.9 | -1.0 | R8 |
| Lindermann | 101.9 | 100.3 | -1.6 | R9 |
| Headley Grange | 101.0 | 100.3 | -0.8 | R7 |
| Soothsayer | 100.2 | 98.9 | -1.3 | R7 |
| Ceolwulf | 99.2 | 98.1 | -1.0 | R9 |

The top ordering did not change materially. That is expected: this is a
weather correction to achieved merit, not a new class or form assessment.

## What will change in the full model

The full implementation will add four separate, auditable fields to each run:

1. **Weather observation:** source, station, timestamp, wind speed, gust and
   direction.
2. **Track-vector exposure:** the wind component parallel to the horse's travel
   direction for each major course segment.
3. **Runner exposure:** the share of each segment spent exposed, based on
   available sectional positions, in-running data and field-relative position.
4. **Wind-adjusted achieved rating:** the base rating plus or minus the
   calibrated weather correction.

The correction will follow this sign convention:

```text
wind_component = wind_speed × cos(wind_toward_bearing − race_segment_bearing)
positive component = tailwind
negative component = headwind
wind rating correction = − calibrated wind component × runner exposure
```

A tailwind therefore reduces the achieved rating and a headwind increases it.
Crosswind produces a small or zero along-track correction. Gusts will be used
to increase uncertainty and exposure risk, not simply added to the mean wind
speed.

## How Melbourne courses will be calculated

The model will not use one Melbourne direction for every course. Each track
gets a versioned geometry profile with:

* course direction: clockwise or anti-clockwise;
* start-to-first-turn bearing;
* back-straight bearing;
* home-straight bearing;
* approximate distance of each segment;
* chute bearing for sprint starts;
* separate profiles for different courses at the same venue, such as Sandown
  Hillside and Lakeside.

The first geometry source will be official or industry track maps. Racing
Victoria publishes Victorian track maps, and the VRC publishes a live Flemington
wind tracker using five track points and minute-level WeatherTrax data. The
VRC describes Flemington's wind data as logged every minute and refreshed during
the race day. ([Racing Victoria track maps](https://www.racingvictoria.com.au/racing/tracks-facilities),
[VRC Flemington wind tracker](https://vrc-failover.azurewebsites.net/track-and-weather-conditions/))

The geometry process will be:

1. Obtain the official map for Flemington, Caulfield, Sandown Hillside,
   Sandown Lakeside and Moonee Valley.
2. Georeference the map using the venue coordinates and winning-post location.
3. Trace the centreline into straight, bend and chute segments.
4. Calculate the bearing of each centreline segment in the actual racing
   direction.
5. Store the geometry version and map source with every calculation.
6. Validate the bearings against known course direction and at least one race
   with a strong, stable wind before using the profile historically.

For example, Flemington will need a long straight profile rather than a single
oval average. Caulfield and Sandown are anti-clockwise Victorian tracks, while
Randwick is clockwise. The bearing matters more than the clockwise label by
itself: a westerly wind can be a tailwind on one section and a headwind on
another. The public Victorian map pack identifies the separate Caulfield,
Moonee Valley and Sandown layouts and their distance markers. ([Victorian track
maps](https://dxp-cdn.racing.com/api/public/content/victorian-track-maps-without-jumps-maps-updated-aug-18-v2-628909.pdf?download=true&v=e0920d62))

## Weather-source hierarchy

The source hierarchy will be location-first and observation-first:

1. **Track-specific observed feed**, where available. Flemington's WeatherTrax
   feed is the preferred example.
2. **Nearest reliable station with historical observations**, selected by
   distance, exposure and continuity rather than city name alone.
3. **Official BOM observations** for validation and daily cross-checks. BOM's
   Melbourne page lists station observations and wind fields, while its daily
   observation products provide a stable historical record. ([BOM Melbourne
   observations](https://www.bom.gov.au/vic/observations/melbourne.shtml))
4. **Weather Underground or World Weather Online** when a track-specific
   historical hourly series is needed and the official station archive is not
   available. These are retained as source-labelled observations, not silently
   treated as track measurements.

Every row will include a source quality class. A race using a nearby station
will carry more uncertainty than a race using a track sensor. Missing or
model-only weather will never be silently converted into observed wind.

## Race-time matching

The matching timestamp will be the actual or scheduled race start in local
Australian time, converted to UTC in storage. The weather observation will be
selected by nearest time within a defined tolerance. For high-wind or rapidly
changing conditions, the model will interpolate the nearest observations and
store the time gap. If the gap is too large, the wind correction will be
reduced or withheld.

For a race lasting roughly two minutes, the start-time observation is a useful
anchor, but the full correction should use a short race window when data is
available. The window will be weighted toward the final 600m because that is
where the exposed home-straight wind most directly affects the achieved clock.

## Preventing double-counting

Wind will not be added on top of an unrestricted pace bonus. The order of
operations will be:

1. Build the clean raw-time and sectional evidence.
2. Adjust the race clock for the wind vector and observation confidence.
3. Assess race pace and sectional efficiency after that correction.
4. Calculate race strength and the individual WFA run rating.
5. Keep wind exposure, pace shape and trip context as separate ledger fields.

If a race already contains an explicit pace or sectional correction that
captures the same directional wind effect, the overlapping component will be
discounted. The detailed JSON will show the pre-wind clock figure, wind
component, pace component, final rating and any overlap flag.

## Calibration and validation before the three-year run

The constants used in the Randwick test are deliberately provisional. Before
historical application, the following checks are required:

* compare wind-adjusted and unadjusted figures on strong-wind meetings;
* test calm, crosswind, headwind and tailwind groups separately;
* check whether wind corrections improve prior-form concordance and
  run-to-run repeatability;
* verify that correction size is stable by distance, going and course;
* compare exposed leaders and sheltered closers using sectional positions;
* run placebo tests on calm meetings, where changes should be near zero;
* inspect top-end cases manually, especially sprint races and long Flemington
  straight races;
* preserve the original rating and the wind-adjusted candidate side by side.

The full historical model will begin as `dan-aligned-wind-v0.1-shadow`. It will
not replace `dan-aligned-wfa-v0.1`, accepted production, or any pricing input
until the walk-forward rating-quality checks pass. A later custom model may use
wind suitability for future prediction, but that will remain separate from the
achieved run rating.

## Current limitation

The Randwick tester uses a nearby Rosebery station and a simplified
eastbound-straight bearing. It is a useful directional and magnitude test, not
the final geometry model. The next step is to replace those assumptions with
venue-specific centreline vectors and to use the best available observed
station for each historical race before processing the three-year database.

