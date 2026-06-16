import { NextResponse } from 'next/server';
import { getDataStore } from '@/lib/supabaseServer';

export const dynamic = 'force-dynamic';

export async function GET() {
  const data = await getDataStore('odds_movements');
  const headers = { 'Cache-Control': 'no-store, no-cache' };
  if (data) return NextResponse.json(data, { headers });
  return NextResponse.json({}, { headers });
}
