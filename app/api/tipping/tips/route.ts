import { NextResponse } from 'next/server';
import { createAdminClient } from '@/lib/supabaseAdmin';
import { getEplFixtures, getValidTipSelections, isGameweekLocked } from '@/lib/tipping';
import { getAuthenticatedUser } from '@/lib/authServer';
import { syncTippingResults } from '@/lib/tippingResults';

function getFixtures(gw: number) {
  return getEplFixtures(gw);
}

export async function GET(request: Request) {
  const user = await getAuthenticatedUser();
  if (!user) return NextResponse.json({ error: 'Unauthorised' }, { status: 401 });
  const { searchParams } = new URL(request.url);
  const compId = searchParams.get('comp_id');
  const userId = searchParams.get('user_id');
  const gw = searchParams.get('gameweek');
  if (!compId || !userId) return NextResponse.json({ tips: [] });
  const gameweek = gw ? parseInt(gw, 10) : 1;
  const fixtures = getFixtures(gameweek);

  // Everyone in the comp can see everyone's tips ONCE THE ROUND LOCKS - that is
  // the intended feature. Before it locks they are private: this handler takes
  // user_id straight from the query string, so without this check any signed-in
  // entrant could read a rival's selections before kickoff and tip against them.
  // The route is the only thing enforcing this - the client below uses the
  // service role, which bypasses row level security by design.
  const roundLocked = fixtures.length > 0 && isGameweekLocked(fixtures);
  if (userId !== user.id && !roundLocked) {
    return NextResponse.json(
      { error: 'Tips stay private until the gameweek locks' },
      { status: 403 },
    );
  }

  await syncTippingResults(gameweek);
  const supabase = createAdminClient();
  const { data, error } = await supabase.from('tipping_tips').select('*')
    .eq('comp_id', compId).eq('user_id', userId).eq('gameweek', gameweek);
  if (error) return NextResponse.json({ tips: [], error: error.message }, { status: 500 });
  const tips = data ?? [];

  // Preserve the existing default-away rule once the full round locks.
  if (roundLocked) {
    const tippedGameIds = new Set(tips.map(t => t.game_id));
    for (const fix of fixtures.filter(f => !tippedGameIds.has(f.id))) {
      const { data: inserted } = await supabase.from('tipping_tips').upsert({
        comp_id: compId,
        user_id: userId,
        gameweek,
        game_id: fix.id,
        home_team: fix.home_team,
        away_team: fix.away_team,
        selection: 'away',
        submitted_at: new Date().toISOString(),
      }, { onConflict: 'comp_id,user_id,game_id' }).select();
      if (inserted?.[0]) tips.push(inserted[0]);
    }
  }
  return NextResponse.json({ tips });
}

export async function POST(request: Request) {
  try {
    const user = await getAuthenticatedUser();
    if (!user) return NextResponse.json({ error: 'Unauthorised' }, { status: 401 });
    const { comp_id, gameweek, tips } = await request.json();
    if (!comp_id || !Number.isInteger(gameweek) || !Array.isArray(tips)) {
      return NextResponse.json({ error: 'Missing required fields' }, { status: 400 });
    }
    const supabase = createAdminClient();
    const fixtures = getFixtures(gameweek);
    if (fixtures.length === 0) {
      return NextResponse.json({ error: `No fixtures found for GW${gameweek}` }, { status: 404 });
    }
    if (isGameweekLocked(fixtures)) {
      return NextResponse.json(
        { error: 'This gameweek is locked because the first game has kicked off' },
        { status: 423 }
      );
    }
    const validTips = getValidTipSelections(gameweek, tips);
    if (validTips.length !== tips.length) {
      return NextResponse.json({ error: 'One or more tips do not belong to this gameweek' }, { status: 400 });
    }
    const results = [];
    for (const { fixture, selection } of validTips) {
      const game_id = fixture.id;
      const { data, error } = await supabase.from('tipping_tips').upsert({
        comp_id,
        user_id: user.id,
        gameweek,
        game_id,
        home_team: fixture.home_team,
        away_team: fixture.away_team,
        selection,
        submitted_at: new Date().toISOString(),
      }, { onConflict: 'comp_id,user_id,game_id' }).select();
      results.push(error ? { game_id, error: error.message } : { game_id, success: true, data });
    }
    return NextResponse.json({ results });
  } catch {
    return NextResponse.json({ error: 'Invalid request body' }, { status: 400 });
  }
}
