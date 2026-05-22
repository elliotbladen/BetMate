import { NextResponse } from 'next/server';
import path from 'path';
import fs from 'fs';
import { getDataStore } from '@/lib/supabaseServer';

export const revalidate = 3600;

export async function GET() {
  // Try Supabase first (works on Vercel)
  const remote = await getDataStore('nrl_home_away');
  if (remote) return NextResponse.json(remote);

  // Local fallback (dev / offline)
  try {
    const filePath = path.join(process.cwd(), 'data', 'nrl', 'home-away', 'processed', 'latest-home-away.json');
    const data = JSON.parse(fs.readFileSync(filePath, 'utf-8'));
    return NextResponse.json(data);
  } catch {
    return NextResponse.json({ teams: {}, updated: null, error: 'NRL home/away value data not yet scraped' }, { status: 200 });
  }
}
