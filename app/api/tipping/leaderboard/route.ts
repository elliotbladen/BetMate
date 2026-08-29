import { NextResponse } from 'next/server';
import { createServerClient } from '@/lib/supabaseServer';
import { getAuthenticatedUser } from '@/lib/authServer';

export async function GET(request: Request) {
  if (!await getAuthenticatedUser()) {
    return NextResponse.json({ error: 'Unauthorised' }, { status: 401 });
  }
  const { searchParams } = new URL(request.url);
  const compId = searchParams.get('comp_id');
  const gw = searchParams.get('gameweek');
  if (!compId) return NextResponse.json({ leaderboard: [] });
  const supabase = createServerClient();
  const { data: entries, error: entriesErr } = await supabase.from('tipping_entries')
    .select('user_id, display_name, total_points').eq('comp_id', compId)
    .order('total_points', { ascending: false });
  if (entriesErr) {
    return NextResponse.json({ leaderboard: [], error: entriesErr.message }, { status: 500 });
  }
  let tipsQuery = supabase.from('tipping_tips').select('user_id, points').eq('comp_id', compId);
  if (gw) tipsQuery = tipsQuery.eq('gameweek', parseInt(gw, 10));
  const { data: tips } = await tipsQuery;
  const tipStats: Record<string, { correct: number; total: number }> = {};
  for (const tip of tips ?? []) {
    if (!tipStats[tip.user_id]) tipStats[tip.user_id] = { correct: 0, total: 0 };
    tipStats[tip.user_id].total++;
    if (tip.points > 0) tipStats[tip.user_id].correct++;
  }
  const leaderboard = (entries ?? []).map((entry, index) => ({
    rank: index + 1,
    display_name: entry.display_name,
    user_id: entry.user_id,
    total_points: entry.total_points,
    correct: tipStats[entry.user_id]?.correct ?? 0,
    total_tips: tipStats[entry.user_id]?.total ?? 0,
    strike_rate: tipStats[entry.user_id]?.total
      ? Math.round((tipStats[entry.user_id].correct / tipStats[entry.user_id].total) * 100) : 0,
  }));
  return NextResponse.json({ leaderboard });
}
