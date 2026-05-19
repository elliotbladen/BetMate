import { NextResponse } from 'next/server';
import { readFileSync } from 'fs';
import { join } from 'path';
import { getDataStore } from '@/lib/supabaseServer';

export const dynamic = 'force-dynamic';

export async function GET() {
  // Try Supabase first (works on Vercel)
  const remote = await getDataStore('team_news_afl');
  if (remote) return NextResponse.json(remote);

  // Local fallback (dev / offline)
  try {
    const filePath = join(process.cwd(), 'data', 'afl', 'team-news', 'latest.json');
    const data = JSON.parse(readFileSync(filePath, 'utf-8'));
    return NextResponse.json(data);
  } catch {
    return NextResponse.json({ sport: 'AFL', round: null, teams: {} });
  }
}
