import { NextResponse } from 'next/server';
import { createServerClient } from '@/lib/supabaseServer';
import type { TipSelection } from '@/lib/tipping';
import { EPL_GW1_FIXTURES } from '@/lib/tipping';

// Get fixtures for a gameweek (MVP: only GW1)
function getFixtures(gw: number) {
  if (gw === 1) return EPL_GW1_FIXTURES;
  return [];
}

// GET /api/tipping/tips?comp_id=X&user_id=Y&gameweek=1
// Returns tips for a user in a comp for a gameweek.
// Auto-fills untipped games as "away" once the first kickoff passes.
export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const compId = searchParams.get('comp_id');
  const userId = searchParams.get('user_id');
  const gw = searchParams.get('gameweek');

  if (!compId || !userId) {
    return NextResponse.json({ tips: [] });
  }

  const gameweek = gw ? parseInt(gw, 10) : 1;
  const supabase = createServerClient();

  const { data, error } = await supabase
    .from('tipping_tips')
    .select('*')
    .eq('comp_id', compId)
    .eq('user_id', userId)
    .eq('gameweek', gameweek);

  if (error) {
    return NextResponse.json({ tips: [], error: error.message }, { status: 500 });
  }

  const tips = data ?? [];
  const fixtures = getFixtures(gameweek);

  // Auto-fill untipped games as "away" once the first kickoff has passed
  if (fixtures.length > 0) {
    const firstKickoff = new Date(Math.min(...fixtures.map(f => new Date(f.kickoff).getTime())));
    const now = new Date();

    if (now > firstKickoff) {
      const tippedGameIds = new Set(tips.map(t => t.game_id));
      const missing = fixtures.filter(f => !tippedGameIds.has(f.id));

      if (missing.length > 0) {
        for (const fix of missing) {
          const { data: inserted } = await supabase
            .from('tipping_tips')
            .upsert(
              {
                comp_id: compId,
                user_id: userId,
                gameweek,
                game_id: fix.id,
                home_team: fix.home_team,
                away_team: fix.away_team,
                selection: 'away',
                submitted_at: new Date().toISOString(),
              },
              { onConflict: 'comp_id,user_id,game_id' }
            )
            .select();

          if (inserted?.[0]) {
            tips.push(inserted[0]);
          }
        }
      }
    }
  }

  return NextResponse.json({ tips });
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
