import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';
export const revalidate = 300; // 5-min server cache

export async function GET() {
  const apiKey = process.env.ODDS_API_KEY;
  if (!apiKey) {
    return NextResponse.json([], {
      headers: {
        'x-betmate-odds-source': 'empty-fallback',
        'x-betmate-upstream-status': 'missing-api-key',
      },
    });
  }

  const url = new URL('https://api.the-odds-api.com/v4/sports/soccer_epl/odds/');
  url.searchParams.set('apiKey', apiKey);
  url.searchParams.set('regions', 'au,uk,eu');
  url.searchParams.set('markets', 'h2h,spreads,totals,btts');
  url.searchParams.set('oddsFormat', 'decimal');

  const res = await fetch(url.toString(), { next: { revalidate: 300 } });
  if (!res.ok) {
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
