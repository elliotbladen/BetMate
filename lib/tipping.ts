// lib/tipping.ts
//
// EPL Tipping Competition — types, fixtures, and scoring logic.
// MVP: pick home/draw/away for each EPL game. 3pts correct result.
// Supabase tables: tipping_comps, tipping_entries, tipping_tips

export interface TippingComp {
  id: string;
  name: string;
  sport: string;
  season: string;
  invite_code: string;
  created_by: string;
  prize_pool: string | null;
  created_at: string;
}

export interface TippingEntry {
  id: string;
  comp_id: string;
  user_id: string;
  display_name: string;
  total_points: number;
  joined_at: string;
}

export type TipSelection = 'home' | 'draw' | 'away';

export interface TippingTip {
  id: string;
  comp_id: string;
  user_id: string;
  gameweek: number;
  game_id: string;
  home_team: string;
  away_team: string;
  selection: TipSelection;
  result: TipSelection | null;
  points: number;
  submitted_at: string;
}

export interface Fixture {
  id: string;
  gameweek: number;
  home_team: string;
  away_team: string;
  kickoff: string; // ISO datetime
  venue: string;
  home_score: number | null;
  away_score: number | null;
  status: 'upcoming' | 'live' | 'finished';
}

export interface LeaderboardRow {
  display_name: string;
  user_id: string;
  total_points: number;
  correct: number;
  total_tips: number;
  strike_rate: number;
  rank: number;
}

// Scoring: 3 points for correct result prediction
export function scoreResult(
  selection: TipSelection,
  home_score: number,
  away_score: number
): number {
  const actual: TipSelection =
    home_score > away_score ? 'home' :
    away_score > home_score ? 'away' : 'draw';
  return selection === actual ? 3 : 0;
}

export function getActualResult(
  home_score: number,
  away_score: number
): TipSelection {
  if (home_score > away_score) return 'home';
  if (away_score > home_score) return 'away';
  return 'draw';
}

// The entire gameweek locks at its earliest kickoff. The optional `now` makes
// the rule deterministic in tests and keeps client/server behaviour identical.
export function isGameweekLocked(fixtures: Fixture[], now = new Date()): boolean {
  if (fixtures.length === 0) return false;

  const kickoffs = fixtures.map(fixture => new Date(fixture.kickoff).getTime());
  if (kickoffs.some(Number.isNaN)) return true;

  return now.getTime() >= Math.min(...kickoffs);
}

// EPL 2026-27 Gameweek 1 fixtures — verified from Odds API 2026-08-18
export const EPL_GW1_FIXTURES: Fixture[] = [
  {
    id: 'epl-2627-gw1-1',
    gameweek: 1,
    home_team: 'Arsenal',
    away_team: 'Coventry City',
    kickoff: '2026-08-21T19:00:00Z',
    venue: 'Emirates Stadium',
    home_score: null,
    away_score: null,
    status: 'upcoming',
  },
  {
    id: 'epl-2627-gw1-2',
    gameweek: 1,
    home_team: 'Hull City',
    away_team: 'Manchester United',
    kickoff: '2026-08-22T11:30:00Z',
    venue: 'MKM Stadium',
    home_score: null,
    away_score: null,
    status: 'upcoming',
  },
  {
    id: 'epl-2627-gw1-3',
    gameweek: 1,
    home_team: 'Everton',
    away_team: 'Crystal Palace',
    kickoff: '2026-08-22T14:00:00Z',
    venue: 'Goodison Park',
    home_score: null,
    away_score: null,
    status: 'upcoming',
  },
  {
    id: 'epl-2627-gw1-4',
    gameweek: 1,
    home_team: 'Ipswich Town',
    away_team: 'Sunderland',
    kickoff: '2026-08-22T14:00:00Z',
    venue: 'Portman Road',
    home_score: null,
    away_score: null,
    status: 'upcoming',
  },
  {
    id: 'epl-2627-gw1-5',
    gameweek: 1,
    home_team: 'Nottingham Forest',
    away_team: 'Leeds United',
    kickoff: '2026-08-22T14:00:00Z',
    venue: 'City Ground',
    home_score: null,
    away_score: null,
    status: 'upcoming',
  },
  {
    id: 'epl-2627-gw1-6',
    gameweek: 1,
    home_team: 'Brentford',
    away_team: 'Tottenham Hotspur',
    kickoff: '2026-08-22T16:30:00Z',
    venue: 'Gtech Community Stadium',
    home_score: null,
    away_score: null,
    status: 'upcoming',
  },
  {
    id: 'epl-2627-gw1-7',
    gameweek: 1,
    home_team: 'Brighton and Hove Albion',
    away_team: 'Aston Villa',
    kickoff: '2026-08-23T13:00:00Z',
    venue: 'Amex Stadium',
    home_score: null,
    away_score: null,
    status: 'upcoming',
  },
  {
    id: 'epl-2627-gw1-8',
    gameweek: 1,
    home_team: 'Manchester City',
    away_team: 'Bournemouth',
    kickoff: '2026-08-23T13:00:00Z',
    venue: 'Etihad Stadium',
    home_score: null,
    away_score: null,
    status: 'upcoming',
  },
  {
    id: 'epl-2627-gw1-9',
    gameweek: 1,
    home_team: 'Newcastle United',
    away_team: 'Liverpool',
    kickoff: '2026-08-23T15:30:00Z',
    venue: "St James' Park",
    home_score: null,
    away_score: null,
    status: 'upcoming',
  },
  {
    id: 'epl-2627-gw1-10',
    gameweek: 1,
    home_team: 'Fulham',
    away_team: 'Chelsea',
    kickoff: '2026-08-24T19:00:00Z',
    venue: 'Craven Cottage',
    home_score: null,
    away_score: null,
    status: 'upcoming',
  },
];

// Supabase SQL for table creation (run once in Supabase SQL editor):
//
// CREATE TABLE tipping_comps (
//   id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
//   name TEXT NOT NULL,
//   sport TEXT NOT NULL DEFAULT 'EPL',
//   season TEXT NOT NULL DEFAULT '2026-27',
//   invite_code TEXT NOT NULL UNIQUE,
//   created_by TEXT NOT NULL,
//   prize_pool TEXT,
//   created_at TIMESTAMPTZ DEFAULT NOW()
// );
//
// CREATE TABLE tipping_entries (
//   id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
//   comp_id UUID REFERENCES tipping_comps(id),
//   user_id TEXT NOT NULL,
//   display_name TEXT NOT NULL,
//   total_points INTEGER DEFAULT 0,
//   joined_at TIMESTAMPTZ DEFAULT NOW(),
//   UNIQUE(comp_id, user_id)
// );
//
// CREATE TABLE tipping_tips (
//   id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
//   comp_id UUID REFERENCES tipping_comps(id),
//   user_id TEXT NOT NULL,
//   gameweek INTEGER NOT NULL,
//   game_id TEXT NOT NULL,
//   home_team TEXT NOT NULL,
//   away_team TEXT NOT NULL,
//   selection TEXT NOT NULL CHECK (selection IN ('home', 'draw', 'away')),
//   result TEXT CHECK (result IN ('home', 'draw', 'away')),
//   points INTEGER DEFAULT 0,
//   submitted_at TIMESTAMPTZ DEFAULT NOW(),
//   UNIQUE(comp_id, user_id, game_id)
// );
