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
  precipIntensity: number,
  precipProbability: number,
  dewSpread: number,  // temp - dewPoint
  localHour: number | null,
  humidity: number,
  temperature: number,
): { condition: WeatherData['condition']; flags: string[] } {
  const flags: string[] = [];
  const isDewWindow = localHour == null || localHour >= 18 || localHour <= 7;

  if (precipIntensity > 2 || precipProbability > 60) flags.push('RAIN');
  else if (precipProbability > 20 || precipIntensity > 0.2) flags.push('SHOWERS');

  if (windSpeed > 60) flags.push('STRONG WIND');
  else if (windSpeed > 35) flags.push('WIND');

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

  if (windSpeed > 60)      score += 3;
  else if (windSpeed > 40) score += 2;
  else if (windSpeed > 25) score += 1;

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

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const lat = searchParams.get('lat');
  const lon = searchParams.get('lon');
  const commenceTime = searchParams.get('time'); // ISO string

  const apiKey = process.env.TOMORROW_API_KEY;
  if (!lat || !lon) return NextResponse.json({ error: 'lat/lon required' }, { status: 400 });

  if (!apiKey) {
    return NextResponse.json({
      temperature: 0,
      windSpeed: 0,
      windGust: 0,
      precipProbability: 0,
      precipIntensity: 0,
      dewPoint: 0,
      humidity: 0,
      condition: 'good',
      flags: [],
    } satisfies WeatherData, {
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

  const res = await fetch(url, { cache: 'no-store' });
  if (!res.ok) {
    return NextResponse.json({
      temperature: 0,
      windSpeed: 0,
      windGust: 0,
      precipProbability: 0,
      precipIntensity: 0,
      dewPoint: 0,
      humidity: 0,
      condition: 'good',
      flags: [],
    } satisfies WeatherData, {
      headers: {
        'x-betmate-weather-source': 'local-placeholder',
        'x-betmate-upstream-status': String(res.status),
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
    return NextResponse.json({
      temperature: 0,
      windSpeed: 0,
      windGust: 0,
      precipProbability: 0,
      precipIntensity: 0,
      dewPoint: 0,
      humidity: 0,
      condition: 'good',
      flags: [],
    } satisfies WeatherData, {
      headers: {
        'x-betmate-weather-source': 'local-placeholder',
        'x-betmate-upstream-status': 'no-weather-data',
      },
    });
  }

  const v = target.values;
  const windSpeedKmh = (v.windSpeed ?? 0) * 3.6;
  const windGustKmh  = (v.windGust  ?? 0) * 3.6;
  const dewSpread    = (v.temperature ?? 20) - (v.dewPoint ?? 10);
  const localHour = commenceTime
    ? Number(
        new Intl.DateTimeFormat('en-AU', {
          hour: 'numeric',
          hourCycle: 'h23',
          timeZone: 'Australia/Sydney',
        }).format(new Date(commenceTime)),
      )
    : null;

  const { condition, flags } = classifyCondition(
    windSpeedKmh,
    v.precipitationIntensity ?? 0,
    v.precipitationProbability ?? 0,
    dewSpread,
    Number.isNaN(localHour) ? null : localHour,
    v.humidity ?? 0,
    v.temperature ?? 0,
  );

  const data: WeatherData = {
    temperature:      Math.round(v.temperature ?? 0),
    windSpeed:        Math.round(windSpeedKmh),
    windGust:         Math.round(windGustKmh),
    precipProbability: Math.round(v.precipitationProbability ?? 0),
    precipIntensity:   Math.round((v.precipitationIntensity ?? 0) * 10) / 10,
    dewPoint:          Math.round(v.dewPoint ?? 0),
    humidity:          Math.round(v.humidity ?? 0),
    condition,
    flags,
  };

  // Fire-and-forget — don't await so it never delays the response
  logWeatherPing(lat, lon, commenceTime, data);

  return NextResponse.json(data);
}
