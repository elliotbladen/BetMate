import { createServerClient } from '@supabase/ssr';
import { NextRequest, NextResponse } from 'next/server';
import { isOwnerEmail } from '@/lib/owner';

export const dynamic = 'force-dynamic';
export const revalidate = 0;

const TRACKS = {
  NSW: ['randwick', 'rosehill'],
  VIC: ['caulfield', 'flemington', 'moonee-valley'],
} as const;

type State = keyof typeof TRACKS;

async function requestEmail(request: NextRequest): Promise<string | null> {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL?.trim();
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY?.trim();
  if (!url || !key) return null;

  const supabase = createServerClient(url, key, {
    cookies: { getAll: () => request.cookies.getAll(), setAll: () => {} },
  });
  const { data: { user } } = await supabase.auth.getUser();
  return user?.email ?? null;
}

async function formFav(path: string, params: Record<string, string>): Promise<Record<string, unknown>> {
  const apiKey = process.env.FORMFAV_API_KEY?.trim();
  if (!apiKey) throw new Error('FormFav is not configured.');

  const url = new URL(`https://api.formfav.com/v1${path}`);
  Object.entries(params).forEach(([key, value]) => url.searchParams.set(key, value));
  const response = await fetch(url, {
    headers: {
      'X-API-Key': apiKey,
      Accept: 'application/json',
      'User-Agent': 'BetMate-RacingEngine/0.1 (owner beta)',
    },
    cache: 'no-store',
  });
  if (!response.ok) throw new Error(`FormFav request failed (${response.status}).`);
  return response.json();
}

export async function GET(request: NextRequest) {
  const email = await requestEmail(request);
  if (!isOwnerEmail(email)) {
    return NextResponse.json({ error: 'Owner access required.' }, { status: 403 });
  }

  const stateParam = request.nextUrl.searchParams.get('state');
  const date = request.nextUrl.searchParams.get('date');
  if ((stateParam !== 'NSW' && stateParam !== 'VIC') || !date || !/^\d{4}-\d{2}-\d{2}$/.test(date)) {
    return NextResponse.json({ error: 'A valid state and date are required.' }, { status: 400 });
  }
  const state = stateParam as State;

  try {
    const meetingsPayload = await formFav('/form/meetings', { date, race_code: 'gallops', timezone: 'Australia/Sydney' });
    const meetings = Array.isArray(meetingsPayload.meetings) ? meetingsPayload.meetings : [];
    const meeting = meetings.find((item) => {
      const candidate = item as { slug?: string };
      return candidate.slug ? TRACKS[state].includes(candidate.slug as never) : false;
    }) as { track: string; slug: string; races?: Array<{ raceNumber?: number }> } | undefined;

    if (!meeting) {
      return NextResponse.json({ meeting: null, date, state }, { headers: { 'Cache-Control': 'private, no-store' } });
    }

    const races = await Promise.all(
      (meeting.races ?? [])
        .filter((race) => Number.isInteger(race.raceNumber))
        .map((race) => formFav('/form', {
          date, track: meeting.slug, race: String(race.raceNumber), race_code: 'gallops', country: 'au', timezone: 'Australia/Sydney',
        })),
    );

    return NextResponse.json(
      { date, state, meeting: { track: meeting.track, slug: meeting.slug, races } },
      { headers: { 'Cache-Control': 'private, no-store' } },
    );
  } catch (error) {
    console.error('Owner racing card request failed:', error);
    return NextResponse.json({ error: 'Unable to load the owner racecard right now.' }, { status: 502 });
  }
}
