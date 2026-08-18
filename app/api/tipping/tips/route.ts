import { NextResponse } from 'next/server';
import { createServerClient } from '@/lib/supabaseServer';
import type { TipSelection } from '@/lib/tipping';

// GET /api/tipping/tips?comp_id=X&user_id=Y&gameweek=1
// Returns tips for a user in a comp for a gameweek.
export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const compId = searchParams.get('comp_id');
  const userId = searchParams.get('user_id');
  const gw = searchParams.get('gameweek');

  if (!compId || !userId) {
    return NextResponse.json({ tips: [] });
  }

  const supabase = createServerClient();
  let query = supabase
    .from('tipping_tips')
    .select('*')
    .eq('comp_id', compId)
    .eq('user_id', userId);

  if (gw) {
    query = query.eq('gameweek', parseInt(gw, 10));
  }

  const { data, error } = await query;
  if (error) {
    return NextResponse.json({ tips: [], error: error.message }, { status: 500 });
  }

  return NextResponse.json({ tips: data ?? [] });
}

// POST /api/tipping/tips
// Submit or update tips. Body: { comp_id, user_id, gameweek, tips: [{ game_id, home_team, away_team, selection }] }
export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { comp_id, user_id, gameweek, tips } = body;

    if (!comp_id || !user_id || !gameweek || !Array.isArray(tips)) {
      return NextResponse.json({ error: 'Missing required fields' }, { status: 400 });
    }

    const supabase = createServerClient();

    // Upsert each tip
    const results = [];
    for (const tip of tips) {
      const { game_id, home_team, away_team, selection } = tip;
      if (!game_id || !selection) continue;

      const validSelections: TipSelection[] = ['home', 'draw', 'away'];
      if (!validSelections.includes(selection)) continue;

      const { data, error } = await supabase
        .from('tipping_tips')
        .upsert(
          {
            comp_id,
            user_id,
            gameweek,
            game_id,
            home_team,
            away_team,
            selection,
            submitted_at: new Date().toISOString(),
          },
          { onConflict: 'comp_id,user_id,game_id' }
        )
        .select();

      if (error) {
        results.push({ game_id, error: error.message });
      } else {
        results.push({ game_id, success: true, data });
      }
    }

    return NextResponse.json({ results });
  } catch {
    return NextResponse.json({ error: 'Invalid request body' }, { status: 400 });
  }
}
