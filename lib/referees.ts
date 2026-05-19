// Referee/umpire assignments per game.
// Data loaded at runtime via /api/referees — static JSON imports removed
// so this module works on Vercel (client component can't read local files).

export type RefBucket = 'WHISTLE HEAVY' | 'FLOW HEAVY' | 'NEUTRAL';

export interface RefAssignment {
  name: string;
  bucket: RefBucket;
}

interface RefRecord {
  home_team: string;
  away_team?: string;
  referee?: string;
  field_umpires?: string;
}

const REF_BUCKETS: Record<string, RefBucket> = {
  'Ashley Klein': 'WHISTLE HEAVY',
  'Grant Atkins': 'FLOW HEAVY',
  'Peter Gough': 'FLOW HEAVY',
  'Belinda Sharpe': 'NEUTRAL',
  'Wyatt Raymond': 'NEUTRAL',
  'Liam Kennedy': 'NEUTRAL',
  'Adam Gee': 'NEUTRAL',
  'Gerard Sutton': 'NEUTRAL',
};

function bucketFor(name: string): RefBucket {
  const first = name.split(';')[0]?.trim();
  return REF_BUCKETS[first] ?? 'NEUTRAL';
}

export function buildRefMap(records: RefRecord[] | undefined): Record<string, RefAssignment> {
  const map: Record<string, RefAssignment> = {};
  for (const row of records ?? []) {
    const name = (row.referee || row.field_umpires || '').trim();
    if (!row.home_team || !name) continue;
    map[row.home_team] = { name, bucket: bucketFor(name) };
  }
  return map;
}

// Returns null when refs not loaded yet — callers must handle gracefully
export function getRefForGame(
  homeTeam: string,
  sport: 'NRL' | 'AFL' = 'NRL',
  refMap?: Record<string, RefAssignment>,
): RefAssignment | null {
  return refMap?.[homeTeam] ?? null;
}
