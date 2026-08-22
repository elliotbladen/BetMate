import { NextResponse } from 'next/server';
import { getEplFixtures } from '@/lib/tipping';
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

  const gameweekFixtures = getEplFixtures(gw);
  if (gameweekFixtures.length > 0) {
    try {
      const completed = await syncTippingResults(gw);
      return NextResponse.json({
        gameweek: gw,
        fixtures: applyCompletedScores(gameweekFixtures, completed),
        round_complete: completed.length === gameweekFixtures.length,
      },
        { headers: { 'Cache-Control': 'private, no-store, max-age=0' } });
    } catch (error) {
      console.error('Tipping result refresh failed', error);
      return NextResponse.json({ error: 'Scores are temporarily unavailable' }, { status: 503 });
    }
  }

  return NextResponse.json({ gameweek: gw, fixtures: [] });
}
