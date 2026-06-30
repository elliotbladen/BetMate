import { appendFile, access, mkdir, writeFile } from 'fs/promises';
import { NextRequest, NextResponse } from 'next/server';
import { join } from 'path';

export const revalidate = 1800; // 30-min server cache

export interface WeatherData {
  temperature: number;
  windSpeed: number;   // km/h
  windGust: number;    // km/h
  precipProbability: number;   // %
  precipIntensity: number;     // mm/hr
  dewPoint: number;    // °C
  humidity: number;    // %
  condition: 'good' | 'average' | 'poor' | 'bad';
  flags: string[];     // e.g. ['RAIN', 'DEW RISK', 'STRONG WIND']
}

function classifyCondition(
  windSpeed: number,
  windGust: number,
  precipIntensity: number,
  precipProbability: number,
  dewSpread: number,  // temp - dewPoint
  localHour: number | null,
  humidity: number,
  temperature: number,
): { condition: WeatherData['condition']; flags: string[] } {
  const flags: string[] = [];
  const isDewWindow = localHour == null || localHour >= 18 || localHour <= 7;
  const effectiveWind = Math.max(windSpeed, windGust * 0.65);

  if (precipIntensity > 2 || precipProbability > 60) flags.push('RAIN');
  else if (precipProbability > 20 || precipIntensity > 0.2) flags.push('SHOWERS');

  if (effectiveWind > 60 || windGust >= 70) flags.push('STRONG WIND');
  else if (effectiveWind > 35 || windGust >= 45) flags.push('WIND');
  else if (windGust >= 35) flags.push('GUSTS');

  // Dew is irrelevant when it's already raining
  const hasRain = flags.includes('RAIN') || flags.includes('SHOWERS');
  const hasDewConditions = !hasRain && isDewWindow && humidity >= 80 && temperature <= 22;
  if (hasDewConditions && dewSpread < 3) flags.push('DEW RISK');
  else if (hasDewConditions && dewSpread < 5) flags.push('MILD DEW');

  // Score: 0 = perfect, higher = worse
  let score = 0;
  if (precipIntensity > 5)        score += 3;
  else if (precipIntensity > 2)   score += 2;
  else if (precipProbability > 60) score += 2;
  else if (precipProbability > 30) score += 1;

  if (effectiveWind > 60 || windGust >= 70)      score += 3;
  else if (effectiveWind > 40 || windGust >= 55) score += 2;
  else if (effectiveWind > 25 || windGust >= 35) score += 1;

  if (hasDewConditions && dewSpread < 3)  score += 2;
  else if (hasDewConditions && dewSpread < 5) score += 1;

  const condition =
    score === 0 ? 'good' :
    score <= 2  ? 'average' :
    score <= 4  ? 'poor' : 'bad';

  return { condition, flags };
}

async function logWeatherPing(lat: string, lon: string, commenceTime: string | null, data: WeatherData) {
  try {
    const now = new Date();
    const year = now.getFullYear().toString();
    const date = now.toISOString().slice(0, 10);
    const timestamp = now.toISOString();
    const dir = join(process.cwd(), 'data', 'weather', year);
    await mkdir(dir, { recursive: true });
    const file = join(dir, `${date}.csv`);
    const header = 'timestamp,lat,lon,commence_time,temperature,wind_speed,wind_gust,precip_prob,precip_intensity,dew_point,humidity,condition,flags\n';
    const row = [
      timestamp,
      lat,
      lon,
      commenceTime ?? '',
      data.temperature,
      data.windSpeed,
      data.windGust,
      data.precipProbability,
      data.precipIntensity,
      data.dewPoint,
      data.humidity,
      data.condition,
      `"${data.flags.join('|')}"`,
    ].join(',') + '\n';

    const fileExists = await access(file).then(() => true).catch(() => false);
    if (!fileExists) {
      await writeFile(file, header + row);
    } else {
      await appendFile(file, row);
    }
  } catch {
    // Logging failure must never break the weather response
  }
}

function localHourFromCommenceTime(commenceTime: string | null): number | null {
  if (!commenceTime) return null;
  const hour = Number(
    new Intl.DateTimeFormat('en-AU', {
      hour: 'numeric',
      hourCycle: 'h23',
      timeZone: 'Australia/Sydney',
    }).format(new Date(commenceTime)),
  );
  return Number.isNaN(hour) ? null : hour;
}

function buildWeatherData(values: {
  temperature?: number;
  windSpeedKmh?: number;
  windGustKmh?: number;
  precipProbability?: number;
  precipIntensity?: number;
  dewPoint?: number;
  humidity?: number;
}, commenceTime: string | null): WeatherData {
  const temperature = values.temperature ?? 0;
  const windSpeedKmh = values.windSpeedKmh ?? 0;
  const windGustKmh = values.windGustKmh ?? 0;
  const precipProbability = values.precipProbability ?? 0;
  const precipIntensity = values.precipIntensity ?? 0;
  const dewPoint = values.dewPoint ?? 0;
  const humidity = values.humidity ?? 0;
  const dewSpread = temperature - dewPoint;

  const { condition, flags } = classifyCondition(
    windSpeedKmh,
    windGustKmh,
    precipIntensity,
    precipProbability,
    dewSpread,
    localHourFromCommenceTime(commenceTime),
    humidity,
    temperature,
  );

  return {
    temperature: Math.round(temperature),
    windSpeed: Math.round(windSpeedKmh),
    windGust: Math.round(windGustKmh),
    precipProbability: Math.round(precipProbability),
    precipIntensity: Math.round(precipIntensity * 10) / 10,
    dewPoint: Math.round(dewPoint),
    humidity: Math.round(humidity),
    condition,
    flags,
  };
}

function unavailableWeather(): WeatherData {
  return {
    temperature: 0,
    windSpeed: 0,
    windGust: 0,
    precipProbability: 0,
    precipIntensity: 0,
    dewPoint: 0,
    humidity: 0,
    condition: 'average',
    flags: ['WEATHER UNAVAILABLE'],
  };
}

async function fetchOpenMeteoWeather(
  lat: string,
  lon: string,
  commenceTime: string | null,
): Promise<WeatherData | null> {
  const fields = [
    'temperature_2m',
    'relative_humidity_2m',
    'dew_point_2m',
    'precipitation',
    'precipitation_probability',
    'wind_speed_10m',
    'wind_gusts_10m',
  ].join(',');
  const url = `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&hourly=${fields}&wind_speed_unit=kmh&timezone=UTC`;

  const res = await fetch(url, { cache: 'no-store' });
  if (!res.ok) return null;

  const json = await res.json();
  const hourly = json.hourly ?? {};
  const times: string[] = hourly.time ?? [];
  if (!times.length) return null;

  let idx = 0;
  if (commenceTime) {
    const gameMs = new Date(commenceTime).getTime();
    idx = times.reduce((best, time, i) => {
      return Math.abs(new Date(time + 'Z').getTime() - gameMs) < Math.abs(new Date(times[best] + 'Z').getTime() - gameMs)
        ? i : best;
    }, 0);
  }

  return buildWeatherData({
    temperature: hourly.temperature_2m?.[idx],
    windSpeedKmh: hourly.wind_speed_10m?.[idx],
    windGustKmh: hourly.wind_gusts_10m?.[idx],
    precipProbability: hourly.precipitation_probability?.[idx],
    precipIntensity: hourly.precipitation?.[idx],
    dewPoint: hourly.dew_point_2m?.[idx],
    humidity: hourly.relative_humidity_2m?.[idx],
  }, commenceTime);
}

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const lat = searchParams.get('lat');
  const lon = searchParams.get('lon');
  const commenceTime = searchParams.get('time'); // ISO string

  const apiKey = process.env.TOMORROW_API_KEY;
  if (!lat || !lon) return NextResponse.json({ error: 'lat/lon required' }, { status: 400 });

  if (!apiKey) {
    const fallback = await fetchOpenMeteoWeather(lat, lon, commenceTime).catch(() => null);
    if (fallback) {
      logWeatherPing(lat, lon, commenceTime, fallback);
      return NextResponse.json(fallback, {
        headers: {
          'x-betmate-weather-source': 'open-meteo-fallback',
          'x-betmate-upstream-status': 'missing-tomorrow-api-key',
        },
      });
    }
    return NextResponse.json(unavailableWeather(), {
      headers: {
        'x-betmate-weather-source': 'local-placeholder',
        'x-betmate-upstream-status': 'missing-api-key',
      },
    });
  }

  const fields = [
    'temperature',
    'windSpeed',
    'windGust',
    'precipitationProbability',
    'precipitationIntensity',
    'dewPoint',
    'humidity',
  ].join(',');

  const url = `https://api.tomorrow.io/v4/weather/forecast?location=${lat},${lon}&apikey=${apiKey}&fields=${fields}&timesteps=1h&units=metric`;

  const res = await fetch(url, { cache: 'no-store' }).catch(() => null);
  if (!res || !res.ok) {
    const fallback = await fetchOpenMeteoWeather(lat, lon, commenceTime).catch(() => null);
    if (fallback) {
      logWeatherPing(lat, lon, commenceTime, fallback);
      return NextResponse.json(fallback, {
        headers: {
          'x-betmate-weather-source': 'open-meteo-fallback',
          'x-betmate-upstream-status': res ? String(res.status) : 'tomorrow-fetch-failed',
        },
      });
    }
    return NextResponse.json(unavailableWeather(), {
      headers: {
        'x-betmate-weather-source': 'local-placeholder',
        'x-betmate-upstream-status': res ? String(res.status) : 'tomorrow-fetch-failed',
      },
    });
  }

  const json = await res.json();
  const hourly: { time: string; values: Record<string, number> }[] = json.timelines?.hourly ?? [];

  // Find the hour closest to game time, fallback to first available
  let target = hourly[0];
  if (commenceTime && hourly.length > 0) {
    const gameMs = new Date(commenceTime).getTime();
    target = hourly.reduce((best, h) => {
      return Math.abs(new Date(h.time).getTime() - gameMs) < Math.abs(new Date(best.time).getTime() - gameMs)
        ? h : best;
    });
  }

  if (!target) {
    const fallback = await fetchOpenMeteoWeather(lat, lon, commenceTime).catch(() => null);
    if (fallback) {
      logWeatherPing(lat, lon, commenceTime, fallback);
      return NextResponse.json(fallback, {
        headers: {
          'x-betmate-weather-source': 'open-meteo-fallback',
          'x-betmate-upstream-status': 'no-tomorrow-weather-data',
        },
      });
    }
    return NextResponse.json(unavailableWeather(), {
      headers: {
        'x-betmate-weather-source': 'local-placeholder',
        'x-betmate-upstream-status': 'no-weather-data',
      },
    });
  }

  const v = target.values;
  const data = buildWeatherData({
    temperature: v.temperature,
    windSpeedKmh: (v.windSpeed ?? 0) * 3.6,
    windGustKmh: (v.windGust ?? 0) * 3.6,
    precipProbability: v.precipitationProbability,
    precipIntensity: v.precipitationIntensity,
    dewPoint: v.dewPoint,
    humidity: v.humidity,
  }, commenceTime);

  // Fire-and-forget — don't await so it never delays the response
  logWeatherPing(lat, lon, commenceTime, data);

  return NextResponse.json(data, {
    headers: {
      'x-betmate-weather-source': 'tomorrow-io',
      'x-betmate-upstream-status': 'ok',
    },
  });
}
