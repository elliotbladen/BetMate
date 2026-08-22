// lib/tipping.ts
//
// EPL Tipping Competition — types, fixtures, and scoring logic.
// MVP: pick home/draw/away for each EPL game. 3pts correct result.
// Supabase tables: tipping_comps, tipping_entries, tipping_tips

import seasonFixtures from '@/lib/epl-2026-27-fixtures.json';

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

export const EPL_SEASON_FIXTURES: Fixture[] = seasonFixtures as Fixture[];

export function getEplFixtures(gameweek: number): Fixture[] {
  if (!Number.isInteger(gameweek) || gameweek < 1 || gameweek > 38) return [];
  return EPL_SEASON_FIXTURES.filter(fixture => fixture.gameweek === gameweek);
}

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
