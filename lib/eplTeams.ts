/**
 * EPL 2025/26 team metadata — maps the-odds-api team names to display info.
 *
 * Promoted: Coventry City, Hull City, Leeds United, Sunderland
 * Relegated: Burnley, West Ham, Wolves
 */

export interface EPLTeamMeta {
  short: string;       // e.g. "ARSENAL"
  abbr: string;        // e.g. "ARS"
  color: string;       // Tailwind text color
  badgeColor: string;  // Tailwind bg color for badge/chip
}

export const EPL_TEAMS: Record<string, EPLTeamMeta> = {
  'Arsenal':                    { short: 'ARSENAL',     abbr: 'ARS', color: 'text-red-500',     badgeColor: 'bg-red-500' },
  'Aston Villa':                { short: 'ASTON VILLA', abbr: 'AVL', color: 'text-purple-500',  badgeColor: 'bg-purple-500' },
  'Bournemouth':                { short: 'BOURNEMOUTH', abbr: 'BOU', color: 'text-red-600',     badgeColor: 'bg-red-600' },
  'Brentford':                  { short: 'BRENTFORD',   abbr: 'BRE', color: 'text-red-400',     badgeColor: 'bg-red-400' },
  'Brighton and Hove Albion':   { short: 'BRIGHTON',    abbr: 'BHA', color: 'text-blue-400',    badgeColor: 'bg-blue-400' },
  'Chelsea':                    { short: 'CHELSEA',     abbr: 'CHE', color: 'text-blue-600',    badgeColor: 'bg-blue-600' },
  'Coventry City':              { short: 'COVENTRY',    abbr: 'COV', color: 'text-sky-500',     badgeColor: 'bg-sky-500' },
  'Crystal Palace':             { short: 'C PALACE',    abbr: 'CRY', color: 'text-blue-500',    badgeColor: 'bg-blue-500' },
  'Everton':                    { short: 'EVERTON',     abbr: 'EVE', color: 'text-blue-500',    badgeColor: 'bg-blue-500' },
  'Fulham':                     { short: 'FULHAM',      abbr: 'FUL', color: 'text-neutral-100', badgeColor: 'bg-neutral-800' },
  'Hull City':                  { short: 'HULL',        abbr: 'HUL', color: 'text-amber-500',   badgeColor: 'bg-amber-500' },
  'Ipswich Town':               { short: 'IPSWICH',     abbr: 'IPS', color: 'text-blue-500',    badgeColor: 'bg-blue-500' },
  'Leeds United':               { short: 'LEEDS',       abbr: 'LEE', color: 'text-yellow-400',  badgeColor: 'bg-yellow-400' },
  'Liverpool':                  { short: 'LIVERPOOL',   abbr: 'LIV', color: 'text-red-500',     badgeColor: 'bg-red-500' },
  'Manchester City':            { short: 'MAN CITY',    abbr: 'MCI', color: 'text-sky-400',     badgeColor: 'bg-sky-400' },
  'Manchester United':          { short: 'MAN UTD',     abbr: 'MUN', color: 'text-red-600',     badgeColor: 'bg-red-600' },
  'Newcastle United':           { short: 'NEWCASTLE',   abbr: 'NEW', color: 'text-neutral-100', badgeColor: 'bg-neutral-800' },
  'Nottingham Forest':          { short: 'FOREST',      abbr: 'NFO', color: 'text-red-500',     badgeColor: 'bg-red-500' },
  'Sunderland':                 { short: 'SUNDERLAND',  abbr: 'SUN', color: 'text-red-500',     badgeColor: 'bg-red-500' },
  'Tottenham Hotspur':          { short: 'SPURS',       abbr: 'TOT', color: 'text-neutral-100', badgeColor: 'bg-neutral-800' },
};

export function getEPLTeamMeta(name: string): EPLTeamMeta {
  return EPL_TEAMS[name] ?? { short: name.toUpperCase(), abbr: name.slice(0, 3).toUpperCase(), color: 'text-gray-400', badgeColor: 'bg-gray-400' };
}

export function getEPLShortName(name: string): string {
  return EPL_TEAMS[name]?.short ?? name.split(' ').pop()!.toUpperCase();
}
