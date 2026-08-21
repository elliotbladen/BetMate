import { NextResponse } from 'next/server';
import { EPL_GW1_FIXTURES } from '@/lib/tipping';
import { getAuthenticatedUser } from '@/lib/authServer';
import { applyCompletedScores, syncTippingResults } from '@/lib/tippingResults';

// GET /api/tipping/fixtures?gameweek=1
// Returns EPL fixtures for a gameweek.
// MVP: static GW1 data. Later: pull from Odds API or Supabase.
export async function GET(request: Request) {
  if (!await getAuthenticatedUser()) {
    return NextResponse.json({ error: 'Unauthorised' }, { status: 401 });
  }
  const { searchParams } = new URL(request.url);
  const gw = parseInt(searchParams.get('gameweek') ?? '1', 10);

  // MVP: only GW1 seeded
  if (gw === 1) {
    const completed = await syncTippingResults(gw);
    return NextResponse.json({
      gameweek: gw,
      fixtures: applyCompletedScores(EPL_GW1_FIXTURES, completed),
    }, { headers: { 'Cache-Control': 'private, no-store, max-age=0' } });
  }

  return NextResponse.json({ gameweek: gw, fixtures: [] });
}
