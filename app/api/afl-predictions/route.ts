import { NextResponse } from 'next/server';
import path from 'path';
import fs from 'fs';
import { getDataStore } from '@/lib/supabaseServer';

export const revalidate = 3600;

export async function GET() {
  // Try Supabase first (works on Vercel)
  const remote = await getDataStore('afl_predictions');
  if (remote) return NextResponse.json(remote);

  // Local fallback (dev / offline)
  try {
    const filePath = path.join(process.cwd(), 'data', 'afl', 'predictions', 'latest.json');
    const data = JSON.parse(fs.readFileSync(filePath, 'utf-8'));
    return NextResponse.json({ predictions: data });
  } catch {
    return NextResponse.json({ predictions: [] });
  }
}
