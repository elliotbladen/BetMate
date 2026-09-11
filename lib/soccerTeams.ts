// lib/soccerTeams.ts
//
// Team badge metadata for the soccer tabs (EPL / Championship / UCL).
// Same shape as NRL_TEAMS / AFL_TEAMS in lib/teams.ts.
//
// Resolve feed/UEFA spelling variants through getSoccerTeamMeta below.
// Palettes represent club identity/home colours, never a seasonal away kit.
// Audit and official colour references: docs/football-team-colours.md.

import type { TeamMeta } from './teams';

export const EPL_TEAMS: Record<string, TeamMeta> = {
  'Arsenal':                    { abbr: 'ARS', primary: '#EF0107', secondary: '#FFFFFF' },
  'Aston Villa':                { abbr: 'AVL', primary: '#670E36', secondary: '#95BFE5' },
  'AFC Bournemouth':            { abbr: 'BOU', primary: '#DA291C', secondary: '#000000' },
  'Bournemouth':                { abbr: 'BOU', primary: '#DA291C', secondary: '#000000' },
  'Brentford':                  { abbr: 'BRE', primary: '#E30613', secondary: '#FFFFFF' },
  'Brighton and Hove Albion':   { abbr: 'BHA', primary: '#0057B8', secondary: '#FFFFFF' },
  'Burnley':                    { abbr: 'BUR', primary: '#6C1D45', secondary: '#99D6EA' },
  'Chelsea':                    { abbr: 'CHE', primary: '#034694', secondary: '#FFFFFF' },
  'Coventry City':              { abbr: 'COV', primary: '#78D0F3', secondary: '#FFFFFF' },
  'Crystal Palace':             { abbr: 'CRY', primary: '#1B458F', secondary: '#C4122E' },
  'Everton':                    { abbr: 'EVE', primary: '#003399', secondary: '#FFFFFF' },
  'Fulham':                     { abbr: 'FUL', primary: '#000000', secondary: '#FFFFFF' },
  'Hull City':                  { abbr: 'HUL', primary: '#F5A12D', secondary: '#000000' },
  'Ipswich Town':               { abbr: 'IPS', primary: '#0044A9', secondary: '#FFFFFF' },
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
  'Bolton Wanderers':           { abbr: 'BOL', primary: '#FFFFFF', secondary: '#001B48' },
  'Bristol City':               { abbr: 'BRC', primary: '#E21C38', secondary: '#FFFFFF' },
  'Burnley':                    { abbr: 'BUR', primary: '#6C1D45', secondary: '#99D6EA' },
  'Cardiff City':               { abbr: 'CAR', primary: '#0070B5', secondary: '#D51116' },
  'Charlton Athletic':          { abbr: 'CHA', primary: '#D4021D', secondary: '#FFFFFF' },
  'Coventry City':              { abbr: 'COV', primary: '#78D0F3', secondary: '#FFFFFF' },
  'Derby County':               { abbr: 'DER', primary: '#FFFFFF', secondary: '#000000' },
  'Hull City':                  { abbr: 'HUL', primary: '#F5A12D', secondary: '#000000' },
  'Ipswich Town':               { abbr: 'IPS', primary: '#0044A9', secondary: '#FFFFFF' },
  'Leicester City':             { abbr: 'LEI', primary: '#003090', secondary: '#FDBE11' },
  'Lincoln City':               { abbr: 'LIN', primary: '#E21017', secondary: '#FFFFFF' },
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
  'West Ham United':            { abbr: 'WHU', primary: '#7A263A', secondary: '#1BB1E7' },
  'Wolverhampton Wanderers':    { abbr: 'WOL', primary: '#FDB913', secondary: '#231F20' },
  'Wrexham':                    { abbr: 'WRX', primary: '#CE1126', secondary: '#FFFFFF' },
};

// UCL: 36-club league phase. English/covered clubs resolve via EPL map first.
// Includes the full 2026/27 league-phase roster, plus previously covered clubs.
export const UCL_TEAMS: Record<string, TeamMeta> = {
  'AEK Athens':                  { abbr: 'AEK', primary: '#FFC600', secondary: '#000000' },
  'AS Roma':                     { abbr: 'ROM', primary: '#862633', secondary: '#F2A900' },
  'Bodø/Glimt':                  { abbr: 'BOD', primary: '#F8DD00', secondary: '#120F0A' },
  'Como':                        { abbr: 'COM', primary: '#003DA5', secondary: '#FFFFFF' },
  'Fenerbahce':                  { abbr: 'FEN', primary: '#FFED00', secondary: '#002D72' },
  'LASK':                        { abbr: 'LAS', primary: '#000000', secondary: '#FFFFFF' },
  'RC Lens':                     { abbr: 'LEN', primary: '#F9D616', secondary: '#C8102E' },
  'Real Betis':                  { abbr: 'BET', primary: '#00954C', secondary: '#FFFFFF' },
  'Sabah FK':                    { abbr: 'SAB', primary: '#000000', secondary: '#E77DA8' },
  'Shakhtar Donetsk':            { abbr: 'SHA', primary: '#F47920', secondary: '#000000' },
  'Slavia Praha':                { abbr: 'SLA', primary: '#E30613', secondary: '#FFFFFF' },
  'Slovan Bratislava':           { abbr: 'SLO', primary: '#6BBBE8', secondary: '#FFFFFF' },
  'VfB Stuttgart':               { abbr: 'VFB', primary: '#FFFFFF', secondary: '#E32219' },
  'Viking FK':                   { abbr: 'VIK', primary: '#00205B', secondary: '#FFFFFF' },
  'Villarreal':                  { abbr: 'VIL', primary: '#FFE667', secondary: '#005DAA' },
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

/** Deliberately avoid fuzzy matching or removing FC/AFC from arbitrary names. */
function normalizeSoccerTeamName(name: string): string {
  return name.normalize('NFKD').replace(/[\u0300-\u036f]/g, '')
    .toLowerCase().replace(/ø/g, 'o').replace(/&/g, 'and')
    .replace(/[^a-z0-9]+/g, ' ').trim().replace(/\s+/g, ' ');
}

// Explicit aliases keep similarly named clubs (e.g. Manchester clubs) distinct.
const SOCCER_TEAM_ALIASES: Record<string, string> = {
  'Wrexham AFC': 'Wrexham',
  'Wrexham A.F.C.': 'Wrexham',
  'QPR': 'Queens Park Rangers',
  'West Brom': 'West Bromwich Albion',
  'Wolves': 'Wolverhampton Wanderers',
  'Sheffield Utd': 'Sheffield United',
  'Sheffield Weds': 'Sheffield Wednesday',
  'Birmingham': 'Birmingham City',
  'Blackburn': 'Blackburn Rovers',
  'Preston': 'Preston North End',
  'Norwich': 'Norwich City',
  'Swansea': 'Swansea City',
  'Stoke': 'Stoke City',
  'Cardiff': 'Cardiff City',
  'Derby': 'Derby County',
  'Bayern München': 'Bayern Munich',
  'Bayern Munchen': 'Bayern Munich',
  'FC Bayern München': 'Bayern Munich',
  'B. Dortmund': 'Borussia Dortmund',
  'Borussia Dortmund 09': 'Borussia Dortmund',
  'Atleti': 'Atletico Madrid',
  'Atlético de Madrid': 'Atletico Madrid',
  'FC Barcelona': 'Barcelona',
  'Paris Saint-Germain': 'Paris Saint Germain',
  'Paris': 'Paris Saint Germain',
  'PSG': 'Paris Saint Germain',
  'Inter': 'Inter Milan',
  'Internazionale': 'Inter Milan',
  'FC Internazionale Milano': 'Inter Milan',
  'Sporting CP': 'Sporting Lisbon',
  'Sporting Clube de Portugal': 'Sporting Lisbon',
  'FC Porto': 'Porto',
  'PSV': 'PSV Eindhoven',
  'Leipzig': 'RB Leipzig',
  'Man City': 'Manchester City',
  'Man United': 'Manchester United',
  'Roma': 'AS Roma',
  'AS Rome': 'AS Roma',
  'FK Bodø/Glimt': 'Bodø/Glimt',
  'Bodoe/Glimt': 'Bodø/Glimt',
  'Bodoglimt': 'Bodø/Glimt',
  'Como 1907': 'Como',
  'Fenerbahçe SK': 'Fenerbahce',
  'Fenerbahce Istanbul': 'Fenerbahce',
  'Lens': 'RC Lens',
  'Racing Club de Lens': 'RC Lens',
  'LOSC Lille': 'Lille',
  'Sabah': 'Sabah FK',
  'Shakhtar': 'Shakhtar Donetsk',
  'FC Shakhtar Donetsk': 'Shakhtar Donetsk',
  "Shakhtar Donets'k": 'Shakhtar Donetsk',
  'Slavia Prague': 'Slavia Praha',
  'SK Slavia Praha': 'Slavia Praha',
  'SK Slavia Prague': 'Slavia Praha',
  'S. Bratislava': 'Slovan Bratislava',
  'ŠK Slovan Bratislava': 'Slovan Bratislava',
  'Stuttgart': 'VfB Stuttgart',
  'Viking': 'Viking FK',
  'LASK Linz': 'LASK',
  'AEK Athens FC': 'AEK Athens',
  'Real Betis Balompié': 'Real Betis',
  'Villarreal CF': 'Villarreal',
  'Club Brugge KV': 'Club Brugge',
};

const canonicalSoccerTeams = { ...UCL_TEAMS, ...CHAMPIONSHIP_TEAMS, ...EPL_TEAMS };
const soccerTeamLookup = new Map(
  Object.entries(canonicalSoccerTeams).map(([name, meta]) => [normalizeSoccerTeamName(name), meta]),
);
for (const [alias, canonical] of Object.entries(SOCCER_TEAM_ALIASES)) {
  soccerTeamLookup.set(normalizeSoccerTeamName(alias), canonicalSoccerTeams[canonical]);
}

export function getSoccerTeamMeta(name: string): TeamMeta | null {
  return soccerTeamLookup.get(normalizeSoccerTeamName(name)) ?? null;
}
