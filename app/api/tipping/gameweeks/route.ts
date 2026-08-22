import { NextResponse } from 'next/server';
import { getAuthenticatedUser } from '@/lib/authServer';
import { getCurrentEplGameweek } from '@/lib/tippingResults';

export async function GET() {
  if (!await getAuthenticatedUser()) {
    return NextResponse.json({ error: 'Unauthorised' }, { status: 401 });
  }
  try {
    const currentGameweek = await getCurrentEplGameweek();
    return NextResponse.json({
      current_gameweek: currentGameweek,
      next_gameweek: currentGameweek && currentGameweek < 38 ? currentGameweek + 1 : null,
      season_complete: currentGameweek === null,
    }, { headers: { 'Cache-Control': 'private, no-store, max-age=0' } });
  } catch (error) {
    console.error('Could not determine current tipping gameweek', error);
    return NextResponse.json({ error: 'Gameweek status is temporarily unavailable' }, { status: 503 });
  }
}
