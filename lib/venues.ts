// NRL home team → venue coordinates for weather lookups.
// Coords are stadium-level for hyperlocal accuracy.

export interface Venue {
  name: string;
  lat: number;
  lon: number;
}

const VENUES: Record<string, Venue> = {
  'Brisbane Broncos':              { name: 'Suncorp Stadium',              lat: -27.4648, lon: 153.0095 },
  'Melbourne Storm':               { name: 'AAMI Park',                    lat: -37.8248, lon: 144.9836 },
  'Sydney Roosters':               { name: 'Allianz Stadium',              lat: -33.8915, lon: 151.2248 },
  'South Sydney Rabbitohs':        { name: 'Accor Stadium',                lat: -33.8472, lon: 151.0631 },
  'Parramatta Eels':               { name: 'CommBank Stadium',             lat: -33.8136, lon: 150.9856 },
  'Wests Tigers':                  { name: 'CommBank Stadium',             lat: -33.8136, lon: 150.9856 },
  'Canterbury Bulldogs':           { name: 'Accor Stadium',                lat: -33.8472, lon: 151.0631 },
  'Canterbury-Bankstown Bulldogs': { name: 'Accor Stadium',                lat: -33.8472, lon: 151.0631 },
  'Penrith Panthers':              { name: 'BlueBet Stadium',              lat: -33.7500, lon: 150.6942 },
  'Manly Warringah Sea Eagles':    { name: '4 Pines Park',                 lat: -33.7681, lon: 151.2647 },
  'Newcastle Knights':             { name: 'McDonald Jones Stadium',       lat: -32.9271, lon: 151.7540 },
  'Canberra Raiders':              { name: 'GIO Stadium',                  lat: -35.2454, lon: 149.0901 },
  'St George Illawarra Dragons':   { name: 'Netstrata Jubilee Oval',       lat: -33.9697, lon: 151.1322 },
  'St. George Illawarra Dragons':  { name: 'Netstrata Jubilee Oval',       lat: -33.9697, lon: 151.1322 },
  'North Queensland Cowboys':      { name: 'Queensland Country Bank Stadium', lat: -19.2590, lon: 146.8169 },
  'Gold Coast Titans':             { name: 'Cbus Super Stadium',           lat: -27.9697, lon: 153.3808 },
  'New Zealand Warriors':          { name: 'Go Media Stadium',             lat: -36.9021, lon: 174.7618 },
  'Cronulla Sutherland Sharks':    { name: 'PointsBet Stadium',            lat: -34.0398, lon: 151.1232 },
  'Cronulla-Sutherland Sharks':    { name: 'PointsBet Stadium',            lat: -34.0398, lon: 151.1232 },
  'Dolphins':                      { name: 'Suncorp Stadium',              lat: -27.4648, lon: 153.0095 },
};

// Venue name → coords. Used when we have the actual venue name from fixture data.
// Covers all current NRL stadiums including neutral/special-event venues.
const VENUE_COORDS: Record<string, Venue> = {
  'Suncorp Stadium':                    { name: 'Suncorp Stadium',                    lat: -27.4648, lon: 153.0095 },
  'AAMI Park':                          { name: 'AAMI Park',                          lat: -37.8248, lon: 144.9836 },
  'Allianz Stadium':                    { name: 'Allianz Stadium',                    lat: -33.8915, lon: 151.2248 },
  'Accor Stadium':                      { name: 'Accor Stadium',                      lat: -33.8472, lon: 151.0631 },
  'CommBank Stadium':                   { name: 'CommBank Stadium',                   lat: -33.8136, lon: 150.9856 },
  'BlueBet Stadium':                    { name: 'BlueBet Stadium',                    lat: -33.7500, lon: 150.6942 },
  '4 Pines Park':                       { name: '4 Pines Park',                       lat: -33.7681, lon: 151.2647 },
  'McDonald Jones Stadium':             { name: 'McDonald Jones Stadium',             lat: -32.9271, lon: 151.7540 },
  'GIO Stadium':                        { name: 'GIO Stadium',                        lat: -35.2454, lon: 149.0901 },
  'Netstrata Jubilee Oval':             { name: 'Netstrata Jubilee Oval',             lat: -33.9697, lon: 151.1322 },
  'WIN Stadium':                        { name: 'WIN Stadium',                        lat: -34.4247, lon: 150.8943 },
  'Queensland Country Bank Stadium':    { name: 'Queensland Country Bank Stadium',    lat: -19.2590, lon: 146.8169 },
  'QCBS Stadium':                       { name: 'Queensland Country Bank Stadium',    lat: -19.2590, lon: 146.8169 },
  'Cbus Super Stadium':                 { name: 'Cbus Super Stadium',                 lat: -27.9697, lon: 153.3808 },
  'Polytec Stadium':                    { name: 'Polytec Stadium',                    lat: -27.9697, lon: 153.3808 },
  'Go Media Stadium':                   { name: 'Go Media Stadium',                   lat: -36.9021, lon: 174.7618 },
  'PointsBet Stadium':                  { name: 'PointsBet Stadium',                  lat: -34.0398, lon: 151.1232 },
  'Shark Park':                         { name: 'PointsBet Stadium',                  lat: -34.0398, lon: 151.1232 },
  'Adelaide Oval':                      { name: 'Adelaide Oval',                      lat: -34.9156, lon: 138.5961 },
  'Optus Stadium':                      { name: 'Optus Stadium',                      lat: -31.9505, lon: 115.8890 },
  'SCG':                                { name: 'SCG',                                lat: -33.8914, lon: 151.2242 },
  'Sydney Cricket Ground':              { name: 'SCG',                                lat: -33.8914, lon: 151.2242 },
  'Campbelltown Stadium':               { name: 'Campbelltown Stadium',               lat: -34.0552, lon: 150.8192 },
  'Leichhardt Oval':                    { name: 'Leichhardt Oval',                    lat: -33.8817, lon: 151.1547 },
  'Central Coast Stadium':              { name: 'Central Coast Stadium',              lat: -33.4272, lon: 151.3421 },
  'Sunshine Coast Stadium':             { name: 'Sunshine Coast Stadium',             lat: -26.6500, lon: 153.0667 },
  'Moreton Daily Stadium':              { name: 'Moreton Daily Stadium',              lat: -27.3272, lon: 153.0297 },
};

export function getVenue(homeTeam: string): Venue | null {
  return VENUES[homeTeam] ?? null;
}

// Look up venue by its name (use when you have actual venue from fixture data).
export function getVenueByName(venueName: string): Venue | null {
  return VENUE_COORDS[venueName] ?? null;
}
