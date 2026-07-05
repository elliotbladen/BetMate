import { NextResponse } from 'next/server';
import { readLatestOddsSnapshot } from '@/lib/oddsSnapshotFallback';

export const dynamic = 'force-dynamic';
export const revalidate = 300; // 5-min server cache

export async function GET() {
  const apiKey = process.env.ODDS_API_KEY;
  const fallback = readLatestOddsSnapshot('NRL');
  if (!apiKey) {
    if (fallback.length > 0) {
      return NextResponse.json(fallback, {
        headers: {
          'x-betmate-odds-source': 'local-snapshot',
          'x-betmate-upstream-status': 'missing-api-key',
        },
      });
    }

    return NextResponse.json([], {
      headers: {
        'x-betmate-odds-source': 'empty-fallback',
        'x-betmate-upstream-status': 'missing-api-key',
      },
    });
  }

  const url = new URL('https://api.the-odds-api.com/v4/sports/rugbyleague_nrl/odds/');
  url.searchParams.set('apiKey', apiKey);
  url.searchParams.set('regions', 'au');
  url.searchParams.set('markets', 'h2h,spreads,totals');
  url.searchParams.set('oddsFormat', 'decimal');

  const res = await fetch(url.toString(), { next: { revalidate: 300 } });
  if (!res.ok) {
    if (fallback.length > 0) {
      return NextResponse.json(fallback, {
        headers: {
          'x-betmate-odds-source': 'local-snapshot',
          'x-betmate-upstream-status': String(res.status),
        },
      });
    }

    return NextResponse.json([], {
      headers: {
        'x-betmate-odds-source': 'empty-fallback',
        'x-betmate-upstream-status': String(res.status),
      },
    });
  }

  const data = await res.json();
  return NextResponse.json(data);
}
