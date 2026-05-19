import { NextResponse } from 'next/server';
import path from 'path';
import fs from 'fs';
import { getDataStore } from '@/lib/supabaseServer';

export const revalidate = 3600;

export async function GET() {
  // Try Supabase first (works on Vercel)
  const remote = await getDataStore('afl_bvi');
  if (remote) return NextResponse.json(remote);

  // Local fallback (dev / offline)
  try {
    const filePath = path.join(process.cwd(), 'data', 'afl', 'bvi', 'processed', 'latest-bvi.json');
    const data = JSON.parse(fs.readFileSync(filePath, 'utf-8'));
    return NextResponse.json(data);
  } catch {
    return NextResponse.json({ teams: {}, updated: null, error: 'BVI data not yet scraped' }, { status: 200 });
  }
}
