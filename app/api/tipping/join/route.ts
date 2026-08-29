import { NextResponse } from 'next/server';
import { createServerClient } from '@/lib/supabaseServer';
import { getAuthenticatedUser } from '@/lib/authServer';

export async function GET() {
  const user = await getAuthenticatedUser();
  if (!user) return NextResponse.json({ error: 'Unauthorised' }, { status: 401 });
  const supabase = createServerClient();
  const { data: entries } = await supabase.from('tipping_entries')
    .select('comp_id, display_name').eq('user_id', user.id).limit(1);
  if (!entries?.length) return NextResponse.json({ comp: null });
  const entry = entries[0];
  const { data: comps } = await supabase.from('tipping_comps')
    .select('*').eq('id', entry.comp_id).limit(1);
  if (!comps?.length) return NextResponse.json({ comp: null });
  return NextResponse.json({ comp: comps[0], display_name: entry.display_name });
}

export async function POST(request: Request) {
  try {
    const user = await getAuthenticatedUser();
    if (!user) return NextResponse.json({ error: 'Unauthorised' }, { status: 401 });
    const { invite_code, display_name } = await request.json();
    if (!invite_code || !display_name) {
      return NextResponse.json({ error: 'Missing required fields' }, { status: 400 });
    }
    const supabase = createServerClient();
    const { data: comps, error: compErr } = await supabase.from('tipping_comps')
      .select('*').eq('invite_code', invite_code.toUpperCase()).limit(1);
    if (compErr || !comps?.length) {
      return NextResponse.json({ error: 'Invalid invite code' }, { status: 404 });
    }
    const comp = comps[0];
    const { data: entry, error: entryErr } = await supabase.from('tipping_entries').upsert(
      { comp_id: comp.id, user_id: user.id, display_name },
      { onConflict: 'comp_id,user_id' }
    ).select();
    if (entryErr) return NextResponse.json({ error: entryErr.message }, { status: 500 });
    return NextResponse.json({ comp, entry: entry?.[0] });
  } catch {
    return NextResponse.json({ error: 'Invalid request body' }, { status: 400 });
  }
}
