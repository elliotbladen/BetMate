import { NextResponse } from 'next/server';
import { readFileSync } from 'fs';
import { join } from 'path';
import { getDataStore } from '@/lib/supabaseServer';

export const dynamic = 'force-dynamic';
export const revalidate = 3600;

export async function GET() {
  // Try Supabase first (works on Vercel)
  const remote = await getDataStore('nrl_fixture');
  if (remote) return NextResponse.json(remote);

  // Local fallback (dev / offline)
  try {
    const fixturePath = join(process.cwd(), 'data', 'nrl', 'fixture', 'processed', 'latest-fixture.json');
    const fixture = JSON.parse(readFileSync(fixturePath, 'utf-8'));
    return NextResponse.json(fixture);
  } catch {
    return NextResponse.json({ season: null, round: null, games: [] });
  }
}
