// lib/soccerTeams.ts
//
// Team badge metadata for the soccer tabs (EPL / Championship / UCL).
// Same shape as NRL_TEAMS / AFL_TEAMS in lib/teams.ts.
//
// CRITICAL (same rule as AFL): keys must match The Odds API team names
// EXACTLY or badges silently fall back to plain text. These lists were
// seeded 2026-07-10 from the expected 2026-27 season lineups BEFORE the
// odds feed was live (API key lapsed) - VERIFY EVERY NAME against the
// first real /api/odds/epl response at hook-up, especially:
//   - "AFC Bournemouth" vs "Bournemouth"
//   - "Brighton and Hove Albion" vs "Brighton & Hove Albion"
//   - "Wolverhampton Wanderers" vs "Wolves"
// Promotions/relegations for 2026-27 must also be reconciled at hook-up.
//
// Unknown teams are safe: TeamBadge renders the raw name as text.

import type { TeamMeta } from './teams';

export const EPL_TEAMS: Record<string, TeamMeta> = {
  'Arsenal':                    { abbr: 'ARS', primary: '#EF0107', secondary: '#FFFFFF' },
  'Aston Villa':                { abbr: 'AVL', primary: '#670E36', secondary: '#95BFE5' },
  'AFC Bournemouth':            { abbr: 'BOU', primary: '#DA291C', secondary: '#000000' },
  'Brentford':                  { abbr: 'BRE', primary: '#E30613', secondary: '#FFFFFF' },
  'Brighton and Hove Albion':   { abbr: 'BHA', primary: '#0057B8', secondary: '#FFFFFF' },
  'Burnley':                    { abbr: 'BUR', primary: '#6C1D45', secondary: '#99D6EA' },
  'Chelsea':                    { abbr: 'CHE', primary: '#034694', secondary: '#FFFFFF' },
  'Crystal Palace':             { abbr: 'CRY', primary: '#1B458F', secondary: '#C4122E' },
  'Everton':                    { abbr: 'EVE', primary: '#003399', secondary: '#FFFFFF' },
  'Fulham':                     { abbr: 'FUL', primary: '#000000', secondary: '#FFFFFF' },
  'Leeds United':               { abbr: 'LEE', primary: '#FFCD00', secondary: '#1D428A' },
  'Liverpool':                  { abbr: 'LIV', primary: '#C8102E', secondary: '#F6EB61' },
  'Manchester City':            { abbr: 'MCI', primary: '#6CABDD', secondary: '#1C2C5B' },
  'Manchester United':          { abbr: 'MUN', primary: '#DA291C', secondary: '#FBE122' },
  'Newcastle United':           { abbr: 'NEW', primary: '#241F20', secondary: '#FFFFFF' },
  'Nottingham Forest':          { abbr: 'NFO', primary: '#DD0000', secondary: '#FFFFFF' },
  'Sunderland':                 { abbr: 'SUN', primary: '#EB172B', secondary: '#FFFFFF' },
  'Tottenham Hotspur':          { abbr: 'TOT', primary: '#132257', secondary: '#FFFFFF' },
  'West Ham United':            { abbr: 'WHU', primary: '#7A263A', secondary: '#1BB1E7' },
  'Wolverhampton Wanderers':    { abbr: 'WOL', primary: '#FDB913', secondary: '#231F20' },
};

export const CHAMPIONSHIP_TEAMS: Record<string, TeamMeta> = {
  'Birmingham City':            { abbr: 'BIR', primary: '#0000FF', secondary: '#FFFFFF' },
  'Blackburn Rovers':           { abbr: 'BLB', primary: '#009EE0', secondary: '#FFFFFF' },
  'Bristol City':               { abbr: 'BRC', primary: '#E21C38', secondary: '#FFFFFF' },
  'Cardiff City':               { abbr: 'CAR', primary: '#0070B5', secondary: '#D51116' },
  'Charlton Athletic':          { abbr: 'CHA', primary: '#D4021D', secondary: '#FFFFFF' },
  'Coventry City':              { abbr: 'COV', primary: '#78D0F3', secondary: '#FFFFFF' },
  'Derby County':               { abbr: 'DER', primary: '#FFFFFF', secondary: '#000000' },
  'Hull City':                  { abbr: 'HUL', primary: '#F5A12D', secondary: '#000000' },
  'Ipswich Town':               { abbr: 'IPS', primary: '#0044A9', secondary: '#FFFFFF' },
  'Leicester City':             { abbr: 'LEI', primary: '#003090', secondary: '#FDBE11' },
  'Luton Town':                 { abbr: 'LUT', primary: '#F78F1E', secondary: '#002D62' },
  'Middlesbrough':              { abbr: 'MID', primary: '#DE1B22', secondary: '#FFFFFF' },
  'Millwall':                   { abbr: 'MIL', primary: '#001D5E', secondary: '#FFFFFF' },
  'Norwich City':               { abbr: 'NOR', primary: '#00A650', secondary: '#FFF200' },
  'Oxford United':              { abbr: 'OXF', primary: '#FFF200', secondary: '#002147' },
  'Portsmouth':                 { abbr: 'POR', primary: '#001489', secondary: '#FFFFFF' },
  'Preston North End':          { abbr: 'PNE', primary: '#FFFFFF', secondary: '#1B449C' },
  'Queens Park Rangers':        { abbr: 'QPR', primary: '#1D5BA4', secondary: '#FFFFFF' },
  'Sheffield United':           { abbr: 'SHU', primary: '#EE2737', secondary: '#FFFFFF' },
  'Sheffield Wednesday':        { abbr: 'SHW', primary: '#0066B3', secondary: '#FFFFFF' },
  'Southampton':                { abbr: 'SOU', primary: '#D71920', secondary: '#FFFFFF' },
  'Stoke City':                 { abbr: 'STK', primary: '#E03A3E', secondary: '#FFFFFF' },
  'Swansea City':               { abbr: 'SWA', primary: '#FFFFFF', secondary: '#000000' },
  'Watford':                    { abbr: 'WAT', primary: '#FBEE23', secondary: '#ED2127' },
  'West Bromwich Albion':       { abbr: 'WBA', primary: '#122F67', secondary: '#FFFFFF' },
  'Wrexham':                    { abbr: 'WRX', primary: '#CE1126', secondary: '#FFFFFF' },
};

// UCL: 36-club league phase. English/covered clubs resolve via EPL map first.
// This list covers the regulars; anyone missing renders as plain text, which
// is acceptable for the outline. Extend when the draw is known.
export const UCL_TEAMS: Record<string, TeamMeta> = {
  'Real Madrid':                { abbr: 'RMA', primary: '#FFFFFF', secondary: '#FEBE10' },
  'Barcelona':                  { abbr: 'BAR', primary: '#A50044', secondary: '#004D98' },
  'Atletico Madrid':            { abbr: 'ATM', primary: '#CB3524', secondary: '#FFFFFF' },
  'Athletic Bilbao':            { abbr: 'ATH', primary: '#EE2523', secondary: '#FFFFFF' },
  'Bayern Munich':              { abbr: 'BAY', primary: '#DC052D', secondary: '#FFFFFF' },
  'Borussia Dortmund':          { abbr: 'BVB', primary: '#FDE100', secondary: '#000000' },
  'Bayer Leverkusen':           { abbr: 'LEV', primary: '#E32221', secondary: '#000000' },
  'RB Leipzig':                 { abbr: 'RBL', primary: '#DD0741', secondary: '#FFFFFF' },
  'Paris Saint Germain':        { abbr: 'PSG', primary: '#004170', secondary: '#DA291C' },
  'Marseille':                  { abbr: 'MAR', primary: '#2FAEE0', secondary: '#FFFFFF' },
  'Monaco':                     { abbr: 'MON', primary: '#E63312', secondary: '#FFFFFF' },
  'Lille':                      { abbr: 'LIL', primary: '#E01E13', secondary: '#FFFFFF' },
  'Inter Milan':                { abbr: 'INT', primary: '#0068A8', secondary: '#000000' },
  'AC Milan':                   { abbr: 'ACM', primary: '#FB090B', secondary: '#000000' },
  'Juventus':                   { abbr: 'JUV', primary: '#000000', secondary: '#FFFFFF' },
  'Napoli':                     { abbr: 'NAP', primary: '#12A0D7', secondary: '#FFFFFF' },
  'Atalanta':                   { abbr: 'ATA', primary: '#1E71B8', secondary: '#000000' },
  'Benfica':                    { abbr: 'BEN', primary: '#E83030', secondary: '#FFFFFF' },
  'Porto':                      { abbr: 'POR', primary: '#003E7E', secondary: '#FFFFFF' },
  'Sporting Lisbon':            { abbr: 'SCP', primary: '#008057', secondary: '#FFFFFF' },
  'Ajax':                       { abbr: 'AJX', primary: '#D2122E', secondary: '#FFFFFF' },
  'PSV Eindhoven':              { abbr: 'PSV', primary: '#ED1C24', secondary: '#FFFFFF' },
  'Feyenoord':                  { abbr: 'FEY', primary: '#C8102E', secondary: '#FFFFFF' },
  'Celtic':                     { abbr: 'CEL', primary: '#018749', secondary: '#FFFFFF' },
  'Rangers':                    { abbr: 'RAN', primary: '#1B458F', secondary: '#FFFFFF' },
  'Galatasaray':                { abbr: 'GAL', primary: '#A90432', secondary: '#FDB912' },
  'Club Brugge':                { abbr: 'BRU', primary: '#0055A2', secondary: '#000000' },
  'Red Bull Salzburg':          { abbr: 'RBS', primary: '#DD0741', secondary: '#FFFFFF' },
};
