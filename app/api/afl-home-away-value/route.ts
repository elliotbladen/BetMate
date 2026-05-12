import { NextResponse } from 'next/server';
import path from 'path';
import fs from 'fs';

export const revalidate = 3600;

export async function GET() {
  const filePath = path.join(process.cwd(), 'data', 'afl', 'home-away', 'processed', 'latest-home-away.json');

  try {
    const raw = fs.readFileSync(filePath, 'utf-8');
    const data = JSON.parse(raw);
    return NextResponse.json(data);
  } catch {
    return NextResponse.json({ teams: {}, updated: null, error: 'AFL home/away value data not yet scraped' }, { status: 200 });
  }
}
