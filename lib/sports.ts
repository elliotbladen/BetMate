// lib/sports.ts
//
// SINGLE SOURCE OF TRUTH for every sport/league BetMate supports.
// Added 2026-07-10 for the EPL / Championship / Champions League expansion.
//
// To add a league: add an entry here, add team meta (lib/soccerTeams.ts or a
// new file), and confirm the Odds API sport key. The odds board tabs, the
// /api/odds/[league] route allowlist, and feature gating all read from this.
//
// NOTE (hook-up week): soccer H2H is 3-way (home/draw/away). The current
// extractH2HOdds() drops the Draw outcome, so soccer H2H cells show home/away
// only. Draw column is a hook-up task, not wired yet.

export type SportId = 'NRL' | 'AFL' | 'EPL' | 'CHAMPIONSHIP' | 'UCL';

export interface SportFeatures {
  weather: boolean;      // venue coords + Tomorrow.io wired
  referees: boolean;     // referee badges (NRL only)
  teamNews: boolean;     // /api/team-news/{sport} exists
  predictions: boolean;  // /api/{sport}-predictions exists
  history: boolean;      // /api/form has match history for this sport
  bvi: boolean;          // BVI / H-A value toggles
  movements: boolean;    // opening-baseline movement arrows
}

export interface SportConfig {
  id: SportId;
  tabLabel: string;        // short label for the sport tab pill
  fullName: string;
  group: 'footy' | 'soccer';
  oddsApiKey: string;      // The Odds API sport key
  oddsEndpoint: string;    // BetMate API route serving raw OddsApiEvent[]
  enabled: boolean;        // show the tab at all
  features: SportFeatures;
}

const FOOTY_FEATURES: SportFeatures = {
  weather: true, referees: false, teamNews: true,
  predictions: true, history: true, bvi: true, movements: true,
};

// Soccer starts with everything off — pure odds board. Flip flags as each
// piece is hooked up (predictions come from BettingEngine ml/football).
const SOCCER_FEATURES: SportFeatures = {
  weather: false, referees: false, teamNews: false,
  predictions: false, history: false, bvi: false, movements: false,
};

export const SPORTS: Record<SportId, SportConfig> = {
  NRL: {
    id: 'NRL', tabLabel: 'NRL', fullName: 'National Rugby League',
    group: 'footy', oddsApiKey: 'rugbyleague_nrl', oddsEndpoint: '/api/odds/nrl',
    enabled: true,
    features: { ...FOOTY_FEATURES, referees: true },
  },
  AFL: {
    id: 'AFL', tabLabel: 'AFL', fullName: 'Australian Football League',
    group: 'footy', oddsApiKey: 'aussierules_afl', oddsEndpoint: '/api/odds/afl',
    enabled: true,
    features: { ...FOOTY_FEATURES },
  },
  EPL: {
    id: 'EPL', tabLabel: 'EPL', fullName: 'English Premier League',
    group: 'soccer', oddsApiKey: 'soccer_epl', oddsEndpoint: '/api/odds/epl',
    enabled: true,
    features: { ...SOCCER_FEATURES },
  },
  CHAMPIONSHIP: {
    id: 'CHAMPIONSHIP', tabLabel: 'Champ', fullName: 'EFL Championship',
    group: 'soccer', oddsApiKey: 'soccer_efl_champ', oddsEndpoint: '/api/odds/championship',
    enabled: true,
    features: { ...SOCCER_FEATURES },
  },
  UCL: {
    id: 'UCL', tabLabel: 'UCL', fullName: 'UEFA Champions League',
    group: 'soccer', oddsApiKey: 'soccer_uefa_champs_league', oddsEndpoint: '/api/odds/ucl',
    enabled: true,
    features: { ...SOCCER_FEATURES },
  },
};

export const SPORT_TAB_ORDER: SportId[] = ['NRL', 'AFL', 'EPL', 'CHAMPIONSHIP', 'UCL'];

export function enabledSports(): SportId[] {
  return SPORT_TAB_ORDER.filter((id) => SPORTS[id].enabled);
}

export function isSoccer(sport: SportId): boolean {
  return SPORTS[sport].group === 'soccer';
}

export function isSportId(value: string | null | undefined): value is SportId {
  return !!value && value in SPORTS;
}

// URL path segment for /api/odds/[league] (soccer sports only)
export function leaguePath(sport: SportId): string {
  return sport.toLowerCase();
}
