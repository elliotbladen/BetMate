import { NextResponse } from 'next/server';
import { getDataStore } from '@/lib/supabaseServer';

export const dynamic = 'force-dynamic';

export async function GET() {
  const data = await getDataStore('odds_movements');
  if (data) return NextResponse.json(data);
  return NextResponse.json({});
}
