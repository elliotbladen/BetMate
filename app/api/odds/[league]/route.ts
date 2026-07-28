import { NextResponse } from 'next/server';
import { readLatestOddsSnapshot } from '@/lib/oddsSnapshotFallback';

export const dynamic = 'force-dynamic';
export const revalidate = 300; // 5-min server cache

// Soccer leagues served by this dynamic route. NRL/AFL keep their existing
// static routes (/api/odds/nrl, /api/odds/afl) which take precedence.
// Middleware note: '/api/odds' is already in PUBLIC_PATHS with prefix
// matching, so /api/odds/{epl|championship|ucl} is public automatically.
const LEAGUES: Record<string, { oddsApiKey: string; snapshotSport: 'EPL' | 'CHAMPIONSHIP' | 'UCL' }> = {
  epl:          { oddsApiKey: 'soccer_epl',                snapshotSport: 'EPL' },
  championship: { oddsApiKey: 'soccer_efl_champ',          snapshotSport: 'CHAMPIONSHIP' },
  ucl:          { oddsApiKey: 'soccer_uefa_champs_league', snapshotSport: 'UCL' },
};

export async function GET(
  _request: Request,
  { params }: { params: { league: string } },
) {
  const { league } = params;
  const config = LEAGUES[league?.toLowerCase() ?? ''];
  if (!config) {
    return NextResponse.json({ error: `Unknown league: ${league}` }, { status: 404 });
  }

  const apiKey = process.env.ODDS_API_KEY;
  const fallback = readLatestOddsSnapshot(config.snapshotSport);
  if (!apiKey) {
    return NextResponse.json(fallback, {
      headers: {
        'x-betmate-odds-source': fallback.length > 0 ? 'local-snapshot' : 'empty-fallback',
        'x-betmate-upstream-status': 'missing-api-key',
      },
    });
  }

  const url = new URL(`https://api.the-odds-api.com/v4/sports/${config.oddsApiKey}/odds/`);
  url.searchParams.set('apiKey', apiKey);
  url.searchParams.set('regions', 'au');
  url.searchParams.set('markets', 'h2h,spreads,totals');
  url.searchParams.set('oddsFormat', 'decimal');

  const res = await fetch(url.toString(), { next: { revalidate: 300 } });
  if (!res.ok) {
    return NextResponse.json(fallback, {
      headers: {
        'x-betmate-odds-source': fallback.length > 0 ? 'local-snapshot' : 'empty-fallback',
        'x-betmate-upstream-status': String(res.status),
      },
    });
  }

  const data = await res.json();
  return NextResponse.json(data);
}
