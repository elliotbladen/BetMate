import { NextResponse } from 'next/server';
import { createServerClient } from '@/lib/supabaseServer';
import { scoreResult, getActualResult, getEplFixtures } from '@/lib/tipping';
import { getAuthenticatedUser } from '@/lib/authServer';
import { isOwnerEmail } from '@/lib/owner';

// Get fixtures for a gameweek (MVP: only GW1)
function getFixtures(gw: number) {
  return getEplFixtures(gw);
}

// POST /api/tipping/results
// Submit results for a gameweek, score all tips, update leaderboard.
//
// Body: { gameweek: number, results: [{ game_id, home_score, away_score }] }
//
export async function POST(request: Request) {
  try {
    const user = await getAuthenticatedUser();
    if (!user) return NextResponse.json({ error: 'Unauthorised' }, { status: 401 });
    if (!isOwnerEmail(user.email)) {
      return NextResponse.json({ error: 'Forbidden' }, { status: 403 });
    }
    const body = await request.json();
    const { gameweek, results } = body;

    if (!gameweek || !Array.isArray(results) || results.length === 0) {
      return NextResponse.json({ error: 'Missing gameweek or results array' }, { status: 400 });
    }

    const fixtures = getFixtures(gameweek);
    if (fixtures.length === 0) {
      return NextResponse.json({ error: `No fixtures found for GW${gameweek}` }, { status: 404 });
    }

    const supabase = createServerClient();

    // Build a map of game_id -> { home_score, away_score }
    const resultMap = new Map<string, { home_score: number; away_score: number }>();
    for (const r of results) {
      if (r.game_id && typeof r.home_score === 'number' && typeof r.away_score === 'number') {
        resultMap.set(r.game_id, { home_score: r.home_score, away_score: r.away_score });
      }
    }

    if (resultMap.size === 0) {
      return NextResponse.json({ error: 'No valid results provided' }, { status: 400 });
    }

    // Fetch ALL tips for this gameweek across all comps
    const { data: allTips, error: tipsErr } = await supabase
      .from('tipping_tips')
      .select('*')
      .eq('gameweek', gameweek);

    if (tipsErr) {
      return NextResponse.json({ error: tipsErr.message }, { status: 500 });
    }

    // Score each tip
    let scored = 0;
    const pointsByCompUser = new Map<string, number>(); // "comp_id:user_id" -> points delta

    for (const tip of allTips ?? []) {
      const result = resultMap.get(tip.game_id);
      if (!result) continue;

      const actual = getActualResult(result.home_score, result.away_score);
      const points = scoreResult(tip.selection, result.home_score, result.away_score);

      // Update the tip row with result + points
      await supabase
        .from('tipping_tips')
        .update({ result: actual, points })
        .eq('id', tip.id);

      const key = `${tip.comp_id}:${tip.user_id}`;
      pointsByCompUser.set(key, (pointsByCompUser.get(key) ?? 0) + points);
      scored++;
    }

    // Update total_points in tipping_entries
    for (const [key] of Array.from(pointsByCompUser.entries())) {
      const [compId, userId] = key.split(':');

      // Recalculate total from all scored tips (safer than incrementing)
      const { data: userTips } = await supabase
        .from('tipping_tips')
        .select('points')
        .eq('comp_id', compId)
        .eq('user_id', userId)
        .not('result', 'is', null);

      const total = (userTips ?? []).reduce((sum, t) => sum + (t.points ?? 0), 0);

      await supabase
        .from('tipping_entries')
        .update({ total_points: total })
        .eq('comp_id', compId)
        .eq('user_id', userId);
    }

    return NextResponse.json({
      scored,
      results_submitted: resultMap.size,
      entries_updated: pointsByCompUser.size,
    });
  } catch {
    return NextResponse.json({ error: 'Invalid request body' }, { status: 400 });
  }
}
