import { NextResponse } from 'next/server';
import { createServerClient } from '@/lib/supabaseServer';

// POST /api/tipping/join
// Join a comp by invite code. Body: { invite_code, user_id, display_name }
export async function POST(request: Request) {
  try {
    const { invite_code, user_id, display_name } = await request.json();

    if (!invite_code || !user_id || !display_name) {
      return NextResponse.json({ error: 'Missing required fields' }, { status: 400 });
    }

    const supabase = createServerClient();

    // Find comp by invite code
    const { data: comps, error: compErr } = await supabase
      .from('tipping_comps')
      .select('*')
      .eq('invite_code', invite_code.toUpperCase())
      .limit(1);

    if (compErr || !comps || comps.length === 0) {
      return NextResponse.json({ error: 'Invalid invite code' }, { status: 404 });
    }

    const comp = comps[0];

    // Upsert entry (idempotent join)
    const { data: entry, error: entryErr } = await supabase
      .from('tipping_entries')
      .upsert(
        {
          comp_id: comp.id,
          user_id,
          display_name,
        },
        { onConflict: 'comp_id,user_id' }
      )
      .select();

    if (entryErr) {
      return NextResponse.json({ error: entryErr.message }, { status: 500 });
    }

    return NextResponse.json({ comp, entry: entry?.[0] });
  } catch {
    return NextResponse.json({ error: 'Invalid request body' }, { status: 400 });
  }
}
