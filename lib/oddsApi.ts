export interface OddsApiEvent {
  id: string;
  sport_key: string;
  sport_title: string;
  commence_time: string;
  home_team: string;
  away_team: string;
  bookmakers: {
    key: string;
    title: string;
    last_update: string;
    markets: {
      key: string;
      last_update: string;
      outcomes: { name: string; price: number; point?: number }[];
    }[];
  }[];
}

export type BookmakerRegion = 'au' | 'uk' | 'eu';

export const BOOKMAKER_META: Record<string, { abbr: string; name: string; color: string; domain: string; region: BookmakerRegion }> = {
  // Australian bookmakers
  sportsbet:       { abbr: 'SB',  name: 'Sportsbet',   color: 'text-orange-400',  domain: 'sportsbet.com.au',    region: 'au' },
  tab:             { abbr: 'TAB', name: 'TAB',          color: 'text-cyan-400',    domain: 'tab.com.au',          region: 'au' },
  tabtouch:        { abbr: 'TBT', name: 'TABtouch',     color: 'text-cyan-300',    domain: 'tabtouch.com.au',     region: 'au' },
  neds:            { abbr: 'NED', name: 'Neds',         color: 'text-red-400',     domain: 'neds.com.au',         region: 'au' },
  betfair_ex_au:   { abbr: 'BF',  name: 'Betfair',      color: 'text-amber-400',   domain: 'betfair.com.au',      region: 'au' },
  ladbrokes_au:    { abbr: 'LAD', name: 'Ladbrokes',    color: 'text-rose-400',    domain: 'ladbrokes.com.au',    region: 'au' },
  unibet:          { abbr: 'UNI', name: 'Unibet',       color: 'text-green-400',   domain: 'unibet.com.au',       region: 'au' },
  pointsbetau:     { abbr: 'PB',  name: 'PointsBet',    color: 'text-purple-400',  domain: 'pointsbet.com.au',    region: 'au' },
  betr_au:         { abbr: 'BTR', name: 'Betr',         color: 'text-yellow-400',  domain: 'betr.com.au',         region: 'au' },
  betright:        { abbr: 'BR',  name: 'BetRight',     color: 'text-blue-400',    domain: 'betright.com.au',     region: 'au' },
  playup:          { abbr: 'PU',  name: 'PlayUp',       color: 'text-pink-400',    domain: 'playup.com.au',       region: 'au' },
  // UK bookmakers
  pinnacle:        { abbr: 'PIN', name: 'Pinnacle',     color: 'text-blue-500',    domain: 'pinnacle.com',        region: 'uk' },
  betfair:         { abbr: 'BF',  name: 'Betfair',      color: 'text-amber-400',   domain: 'betfair.com',         region: 'uk' },
  betfair_ex_uk:   { abbr: 'BF',  name: 'Betfair',      color: 'text-amber-400',   domain: 'betfair.com',         region: 'uk' },
  betfair_sb_uk:   { abbr: 'BFs', name: 'Betfair SB',   color: 'text-amber-300',   domain: 'betfair.com',         region: 'uk' },
  williamhill:     { abbr: 'WH',  name: 'Wm Hill',      color: 'text-blue-600',    domain: 'williamhill.com',     region: 'uk' },
  bet365:          { abbr: '365', name: 'Bet365',       color: 'text-green-500',   domain: 'bet365.com',          region: 'uk' },
  paddypower:      { abbr: 'PP',  name: 'Paddy P',      color: 'text-green-400',   domain: 'paddypower.com',      region: 'uk' },
  betway:          { abbr: 'BW',  name: 'Betway',       color: 'text-slate-400',   domain: 'betway.com',          region: 'uk' },
  sport888:        { abbr: '888', name: '888sport',     color: 'text-orange-500',  domain: '888sport.com',        region: 'uk' },
  betfred_uk:      { abbr: 'BFR', name: 'Betfred',      color: 'text-red-500',     domain: 'betfred.com',         region: 'uk' },
  betvictor:       { abbr: 'BV',  name: 'BetVictor',    color: 'text-red-400',     domain: 'betvictor.com',       region: 'uk' },
  coral:           { abbr: 'COR', name: 'Coral',        color: 'text-yellow-500',  domain: 'coral.co.uk',         region: 'uk' },
  skybet:          { abbr: 'SKY', name: 'Sky Bet',      color: 'text-blue-500',    domain: 'skybet.com',          region: 'uk' },
  boylesports:     { abbr: 'BOY', name: 'Boyles',       color: 'text-green-500',   domain: 'boylesports.com',     region: 'uk' },
  ladbrokes_uk:    { abbr: 'LAD', name: 'Ladbrokes',    color: 'text-rose-400',    domain: 'ladbrokes.com',       region: 'uk' },
  unibet_uk:       { abbr: 'UNI', name: 'Unibet',       color: 'text-green-400',   domain: 'unibet.co.uk',        region: 'uk' },
  betano_uk:       { abbr: 'BAN', name: 'Betano',       color: 'text-blue-400',    domain: 'betano.com',          region: 'uk' },
  livescorebet:    { abbr: 'LSB', name: 'LiveScore',    color: 'text-pink-400',    domain: 'livescorebet.com',    region: 'uk' },
  grosvenor:       { abbr: 'GRO', name: 'Grosvenor',    color: 'text-yellow-400',  domain: 'grosvenorcasinos.com', region: 'uk' },
  virginbet:       { abbr: 'VIR', name: 'VirginBet',    color: 'text-red-500',     domain: 'virginbet.com',       region: 'uk' },
  smarkets:        { abbr: 'SMK', name: 'Smarkets',     color: 'text-blue-300',    domain: 'smarkets.com',        region: 'uk' },
  // EU bookmakers
  onexbet:         { abbr: '1xB', name: '1xBet',        color: 'text-blue-400',    domain: '1xbet.com',           region: 'eu' },
  betfair_ex_eu:   { abbr: 'BF',  name: 'Betfair',      color: 'text-amber-400',   domain: 'betfair.com',         region: 'eu' },
  unibet_eu:       { abbr: 'UNI', name: 'Unibet',       color: 'text-green-400',   domain: 'unibet.com',          region: 'eu' },
  unibet_fr:       { abbr: 'UNI', name: 'Unibet',       color: 'text-green-400',   domain: 'unibet.fr',           region: 'eu' },
  unibet_se:       { abbr: 'UNI', name: 'Unibet',       color: 'text-green-400',   domain: 'unibet.se',           region: 'eu' },
  unibet_nl:       { abbr: 'UNI', name: 'Unibet',       color: 'text-green-400',   domain: 'unibet.nl',           region: 'eu' },
  betsson:         { abbr: 'BSN', name: 'Betsson',      color: 'text-orange-400',  domain: 'betsson.com',         region: 'eu' },
  betclic_fr:      { abbr: 'BC',  name: 'Betclic',      color: 'text-red-300',     domain: 'betclic.fr',          region: 'eu' },
  betonlineag:     { abbr: 'BOL', name: 'BetOnline',    color: 'text-orange-400',  domain: 'betonline.ag',        region: 'eu' },
  codere_it:       { abbr: 'COD', name: 'Codere',       color: 'text-green-300',   domain: 'codere.it',           region: 'eu' },
  marathonbet:     { abbr: 'MAR', name: 'Marathon',     color: 'text-blue-400',    domain: 'marathonbet.com',     region: 'eu' },
  tipico_de:       { abbr: 'TIP', name: 'Tipico',       color: 'text-blue-400',    domain: 'tipico.de',           region: 'eu' },
  winamax_de:      { abbr: 'WMX', name: 'Winamax',      color: 'text-red-400',     domain: 'winamax.de',          region: 'eu' },
  winamax_fr:      { abbr: 'WMX', name: 'Winamax',      color: 'text-red-400',     domain: 'winamax.fr',          region: 'eu' },
  casumo:          { abbr: 'CAS', name: 'Casumo',       color: 'text-green-400',   domain: 'casumo.com',          region: 'eu' },
  leovegas:        { abbr: 'LEO', name: 'LeoVegas',     color: 'text-orange-500',  domain: 'leovegas.com',        region: 'eu' },
  leovegas_se:     { abbr: 'LEO', name: 'LeoVegas',     color: 'text-orange-500',  domain: 'leovegas.se',         region: 'eu' },
  coolbet:         { abbr: 'COL', name: 'Coolbet',      color: 'text-cyan-400',    domain: 'coolbet.com',         region: 'eu' },
  nordicbet:       { abbr: 'NOR', name: 'NordicBet',    color: 'text-green-400',   domain: 'nordicbet.com',       region: 'eu' },
  everygame:       { abbr: 'EG',  name: 'Everygame',    color: 'text-red-400',     domain: 'everygame.eu',        region: 'eu' },
  pmu_fr:          { abbr: 'PMU', name: 'PMU',          color: 'text-green-500',   domain: 'pmu.fr',              region: 'eu' },
};

/** Map ISO country code to bookmaker region */
export function countryToRegion(countryCode: string | null | undefined): BookmakerRegion {
  if (!countryCode) return 'au';
  const cc = countryCode.toUpperCase();
  if (cc === 'AU' || cc === 'NZ') return 'au';
  if (cc === 'GB' || cc === 'IE') return 'uk';
  // EU countries
  const euCodes = ['AT','BE','BG','HR','CY','CZ','DK','EE','FI','FR','DE','GR','HU','IS','IT','LV','LT','LU','MT','NL','NO','PL','PT','RO','SK','SI','ES','SE','CH'];
  if (euCodes.includes(cc)) return 'eu';
  return 'au'; // default to AU
}

/** Map BookmakerRegion to The Odds API regions parameter value */
export function regionToOddsApiParam(region: BookmakerRegion): string {
  // The Odds API uses 'uk' for UK bookmakers, 'au' for AU, 'eu' for EU
  return region;
}

/**
 * Extract the Odds API regions param from an incoming request.
 * Reads the betmate-country cookie (set by middleware from Vercel geo header),
 * maps it to a region, then returns the Odds API regions string.
 *
 * Always includes 'au' as a base region so games are always shown
 * (UK bookmakers don't cover NRL/AFL). The visitor's region is added
 * alongside AU so they see their local bookmakers where available.
 * Frontend filtering handles showing the right bookmakers per region.
 *
 * Falls back to 'au' only if no cookie is present (localhost / non-Vercel).
 */
export function getOddsRegionFromRequest(_request: Request): string {
  // Always fetch au,uk so the server-side cached response works for both
  // AU and UK visitors. Frontend filtering handles showing the right
  // bookmakers per region. Cost: 2 regions × 3 markets = 6 credits/call.
  // When EU support is needed: read betmate-country cookie from _request,
  // map via countryToRegion(), and add eu to the string.
  return 'au,uk';
}

function normalizeOutcomeName(value: string): string {
  return value
    .toLowerCase()
    .replace(/&/g, 'and')
    .replace(/\bfc\b/g, '')
    .replace(/[^a-z0-9]+/g, ' ')
    .trim()
    .replace(/\s+/g, ' ');
}

function findOutcome(
  outcomes: { name: string; price: number; point?: number }[],
  teamName: string,
) {
  const target = normalizeOutcomeName(teamName);
  return outcomes.find((outcome) => normalizeOutcomeName(outcome.name) === target);
}

export function extractH2HOdds(
  event: OddsApiEvent,
): Record<string, { home: number; draw?: number; away: number }> {
  const odds: Record<string, { home: number; draw?: number; away: number }> = {};
  for (const bm of event.bookmakers) {
    const h2h = bm.markets.find((m) => m.key === 'h2h');
    if (!h2h) continue;
    const homeOutcome = findOutcome(h2h.outcomes, event.home_team);
    const awayOutcome = findOutcome(h2h.outcomes, event.away_team);
    if (homeOutcome && awayOutcome) {
      const drawOutcome = h2h.outcomes.find((o) => normalizeOutcomeName(o.name) === 'draw');
      odds[bm.key] = {
        home: homeOutcome.price,
        ...(drawOutcome ? { draw: drawOutcome.price } : {}),
        away: awayOutcome.price,
      };
    }
  }
  return odds;
}

export function extractSpreadsOdds(
  event: OddsApiEvent,
): Record<string, { home: number; away: number; homePoint: number; awayPoint: number }> {
  const odds: Record<string, { home: number; away: number; homePoint: number; awayPoint: number }> = {};
  for (const bm of event.bookmakers) {
    const spreads = bm.markets.find((m) => m.key === 'spreads');
    if (!spreads) continue;
    const homeOutcome = findOutcome(spreads.outcomes, event.home_team);
    const awayOutcome = findOutcome(spreads.outcomes, event.away_team);
    if (homeOutcome && awayOutcome && homeOutcome.point != null && awayOutcome.point != null) {
      odds[bm.key] = {
        home: homeOutcome.price,
        away: awayOutcome.price,
        homePoint: homeOutcome.point,
        awayPoint: awayOutcome.point,
      };
    }
  }
  return odds;
}

export function extractTotalsOdds(
  event: OddsApiEvent,
): Record<string, { over: number; under: number; point: number }> {
  const odds: Record<string, { over: number; under: number; point: number }> = {};
  for (const bm of event.bookmakers) {
    const totals = bm.markets.find((m) => m.key === 'totals');
    if (!totals) continue;
    const overOutcome  = totals.outcomes.find((o) => o.name === 'Over');
    const underOutcome = totals.outcomes.find((o) => o.name === 'Under');
    if (overOutcome && underOutcome && overOutcome.point != null) {
      odds[bm.key] = {
        over:  overOutcome.price,
        under: underOutcome.price,
        point: overOutcome.point,
      };
    }
  }
  return odds;
}

export function extractBTTSOdds(
  event: OddsApiEvent,
): Record<string, { yes: number; no: number }> {
  const odds: Record<string, { yes: number; no: number }> = {};
  for (const bm of event.bookmakers) {
    const btts = bm.markets.find((m) => m.key === 'btts');
    if (!btts) continue;
    const yesOutcome = btts.outcomes.find((o) => o.name === 'Yes');
    const noOutcome  = btts.outcomes.find((o) => o.name === 'No');
    if (yesOutcome && noOutcome) {
      odds[bm.key] = {
        yes: yesOutcome.price,
        no:  noOutcome.price,
      };
    }
  }
  return odds;
}
