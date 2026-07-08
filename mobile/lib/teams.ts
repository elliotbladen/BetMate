export interface TeamMeta {
  abbr: string;
  primary: string;
  secondary: string;
}

export const NRL_TEAMS: Record<string, TeamMeta> = {
  'Brisbane Broncos':            { abbr: 'BRI', primary: '#4E0D3A', secondary: '#F5A623' },
  'Melbourne Storm':             { abbr: 'MEL', primary: '#420091', secondary: '#E4C91B' },
  'Sydney Roosters':             { abbr: 'SYD', primary: '#0B2266', secondary: '#C41230' },
  'South Sydney Rabbitohs':      { abbr: 'SSR', primary: '#C41230', secondary: '#006B3F' },
  'Parramatta Eels':             { abbr: 'PAR', primary: '#013CA6', secondary: '#FFCD00' },
  'Wests Tigers':                { abbr: 'WST', primary: '#F7941D', secondary: '#000000' },
  'Canterbury Bulldogs':         { abbr: 'CBY', primary: '#0038A8', secondary: '#FFFFFF' },
  'Penrith Panthers':            { abbr: 'PEN', primary: '#2B2B2B', secondary: '#FFFFFF' },
  'Manly Warringah Sea Eagles':  { abbr: 'MAN', primary: '#4E0D3A', secondary: '#FFFFFF' },
  'Newcastle Knights':           { abbr: 'NEW', primary: '#003B8E', secondary: '#C41230' },
  'Canberra Raiders':            { abbr: 'CAN', primary: '#79BC00', secondary: '#000000' },
  'St George Illawarra Dragons': { abbr: 'SGI', primary: '#C41230', secondary: '#FFFFFF' },
  'North Queensland Cowboys':    { abbr: 'NQC', primary: '#003087', secondary: '#FFCF00' },
  'Gold Coast Titans':           { abbr: 'GCT', primary: '#009FDF', secondary: '#F5A623' },
  'New Zealand Warriors':        { abbr: 'NZW', primary: '#1A1A1A', secondary: '#808080' },
  'Cronulla Sutherland Sharks':  { abbr: 'CSH', primary: '#009FDF', secondary: '#000000' },
  'Dolphins':                    { abbr: 'DOL', primary: '#B5252B', secondary: '#FFFFFF' },
};

export const AFL_TEAMS: Record<string, TeamMeta> = {
  'Adelaide Crows':                   { abbr: 'ADE', primary: '#002B5C', secondary: '#E21937' },
  'Brisbane Lions':                   { abbr: 'BRL', primary: '#A00026', secondary: '#F2A900' },
  'Carlton Blues':                    { abbr: 'CAR', primary: '#001B3F', secondary: '#FFFFFF' },
  'Collingwood Magpies':              { abbr: 'COL', primary: '#000000', secondary: '#FFFFFF' },
  'Essendon Bombers':                 { abbr: 'ESS', primary: '#CC2031', secondary: '#000000' },
  'Fremantle Dockers':                { abbr: 'FRE', primary: '#2C1654', secondary: '#FFFFFF' },
  'Geelong Cats':                     { abbr: 'GEE', primary: '#001F5B', secondary: '#FFFFFF' },
  'Gold Coast Suns':                  { abbr: 'GCS', primary: '#E8233B', secondary: '#F5A623' },
  'Greater Western Sydney Giants':    { abbr: 'GWS', primary: '#F47920', secondary: '#111111' },
  'Hawthorn Hawks':                   { abbr: 'HAW', primary: '#4D2004', secondary: '#FBBF15' },
  'Melbourne Demons':                 { abbr: 'MEL', primary: '#061A33', secondary: '#CC2031' },
  'North Melbourne Kangaroos':        { abbr: 'NME', primary: '#003B99', secondary: '#FFFFFF' },
  'Port Adelaide Power':              { abbr: 'POR', primary: '#008AAB', secondary: '#000000' },
  'Richmond Tigers':                  { abbr: 'RIC', primary: '#111111', secondary: '#FED102' },
  'St Kilda Saints':                  { abbr: 'STK', primary: '#ED0F05', secondary: '#FFFFFF' },
  'Sydney Swans':                     { abbr: 'SYD', primary: '#E4122E', secondary: '#FFFFFF' },
  'West Coast Eagles':                { abbr: 'WCE', primary: '#002B71', secondary: '#F2A71B' },
  'Western Bulldogs':                 { abbr: 'WBD', primary: '#0039A6', secondary: '#CC2031' },
};

export function getTeamMeta(teamName: string): TeamMeta | null {
  return NRL_TEAMS[teamName] ?? AFL_TEAMS[teamName] ?? null;
}
