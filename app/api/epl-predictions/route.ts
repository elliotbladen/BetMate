import { NextResponse } from 'next/server';

export const revalidate = 0;

export async function GET() {
  // EPL predictions not yet wired — return empty until price_match.py integration
  return NextResponse.json({ predictions: [] });
}
