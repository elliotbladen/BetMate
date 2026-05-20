import { NextResponse } from 'next/server';
import { getDataStore } from '@/lib/supabaseServer';

export const dynamic = 'force-dynamic';

export async function GET() {
  const data = await getDataStore('nrl_refs');
  if (data) return NextResponse.json(data);
  return NextResponse.json({ records: [] });
}
