export interface BookmakerLinks {
  web: string;
  ios?: string;
  android?: string;
}

export const APP_STORE_LINKS: Record<string, { ios?: string; android?: string }> = {
  sportsbet:     { ios: 'https://apps.apple.com/au/app/sportsbet/id391598866',              android: 'https://play.google.com/store/apps/details?id=com.sportsbet.android' },
  tab:           { ios: 'https://apps.apple.com/au/app/tab/id470604524',                    android: 'https://play.google.com/store/apps/details?id=com.tab.au' },
  tabtouch:      { ios: 'https://apps.apple.com/au/app/tabtouch/id596892983' },
  neds:          { ios: 'https://apps.apple.com/au/app/neds/id1278740918',                  android: 'https://play.google.com/store/apps/details?id=com.neds.android' },
  betfair_ex_au: { ios: 'https://apps.apple.com/au/app/betfair-sports-betting/id470087655', android: 'https://play.google.com/store/apps/details?id=com.betfair.android.betfairapp' },
  ladbrokes_au:  { ios: 'https://apps.apple.com/au/app/ladbrokes-sports-betting/id1049758611', android: 'https://play.google.com/store/apps/details?id=com.ladbrokes.android' },
  unibet:        { ios: 'https://apps.apple.com/au/app/unibet-sports-betting/id528884178',  android: 'https://play.google.com/store/apps/details?id=com.unibet.android' },
  pointsbetau:   { ios: 'https://apps.apple.com/au/app/pointsbet-sports-betting/id1434916360', android: 'https://play.google.com/store/apps/details?id=com.pointsbet.android' },
  betr_au:       { ios: 'https://apps.apple.com/au/app/betr-sports-racing-betting/id1637444944', android: 'https://play.google.com/store/apps/details?id=com.betr.android' },
};

// Bookmaker NRL competition URLs.
// These link to the NRL market on each bookmaker — one click from the specific game.
// True per-game deep links require each bookmaker's internal event ID,
// which would need their affiliate API or a nightly scrape. Add those here
// once you have affiliate codes and event ID ingestion in place.

const NRL_URLS: Record<string, string> = {
  sportsbet:     'https://www.sportsbet.com.au/betting/rugby-league/nrl',
  tab:           'https://www.tab.com.au/sports/betting/Rugby%20League/competitions/NRL',
  tabtouch:      'https://www.tabtouch.com.au/sports/rugby-league/national-rugby-league',
  neds:          'https://www.neds.com.au/sports/rugby-league/nrl',
  betfair_ex_au: 'https://www.betfair.com.au/exchange/plus/rugby-league',
  ladbrokes_au:  'https://www.ladbrokes.com.au/sport/rugby-league/nrl',
  unibet:        'https://www.unibet.com.au/sports/rugby-league/national-rugby-league',
  pointsbetau:   'https://pointsbet.com.au/sports/rugby-league/national-rugby-league',
  betr_au:       'https://betr.com.au/sport/rugby-league/nrl',
  betright:      'https://betright.com.au/sports/rugby-league/nrl',
  playup:        'https://www.playup.com.au/sports/rugby-league/nrl',
};

const AFL_URLS: Record<string, string> = {
  sportsbet:     'https://www.sportsbet.com.au/betting/australian-rules/afl',
  tab:           'https://www.tab.com.au/sports/betting/Australian%20Rules/competitions/AFL',
  tabtouch:      'https://www.tabtouch.com.au/sports/australian-rules/afl',
  neds:          'https://www.neds.com.au/sports/afl',
  betfair_ex_au: 'https://www.betfair.com.au/exchange/plus/australian-rules-betting',
  ladbrokes_au:  'https://www.ladbrokes.com.au/sport/afl',
  unibet:        'https://www.unibet.com.au/sports/australian-rules/afl',
  pointsbetau:   'https://pointsbet.com.au/sports/australian-rules/afl',
  betr_au:       'https://betr.com.au/sport/afl',
  betright:      'https://betright.com.au/sports/afl',
  playup:        'https://www.playup.com.au/sports/afl',
};

// Soccer landing pages — AU and UK bookmakers.
const SOCCER_URLS: Record<string, string> = {
  // AU
  sportsbet:     'https://www.sportsbet.com.au/betting/soccer',
  tab:           'https://www.tab.com.au/sports/betting/Soccer',
  tabtouch:      'https://www.tabtouch.com.au/sports/soccer',
  neds:          'https://www.neds.com.au/sports/soccer',
  betfair_ex_au: 'https://www.betfair.com.au/exchange/plus/football',
  ladbrokes_au:  'https://www.ladbrokes.com.au/sport/soccer',
  unibet:        'https://www.unibet.com.au/sports/football',
  pointsbetau:   'https://pointsbet.com.au/sports/soccer',
  betr_au:       'https://betr.com.au/sport/soccer',
  betright:      'https://betright.com.au/sports/soccer',
  playup:        'https://www.playup.com.au/sports/soccer',
  // UK
  bet365:        'https://www.bet365.com/#/AC/B1/C1/D13/',
  williamhill:   'https://sports.williamhill.com/betting/en-gb/football',
  paddypower:    'https://www.paddypower.com/football',
  skybet:        'https://www.skybet.com/football',
  coral:         'https://sports.coral.co.uk/football',
  ladbrokes_uk:  'https://sports.ladbrokes.com/football',
  betfair_ex_uk: 'https://www.betfair.com/exchange/plus/football',
  betfair_sb_uk: 'https://www.betfair.com/sport/football',
  betway:        'https://www.betway.com/en-gb/sports/soccer',
  sport888:      'https://www.888sport.com/football/',
  betfred_uk:    'https://www.betfred.com/sports/football',
  betvictor:     'https://www.betvictor.com/en-gb/football',
  boylesports:   'https://www.boylesports.com/football',
  unibet_uk:     'https://www.unibet.co.uk/sports/football',
};

export function getAffiliateUrl(bookmaker: string, sport: string): string | null {
  const upper = sport.toUpperCase();
  const map = upper === 'AFL' ? AFL_URLS : upper === 'NRL' ? NRL_URLS : SOCCER_URLS;
  return map[bookmaker] ?? null;
}

function slugify(name: string): string {
  return name.trim().replace(/\s+/g, '-');
}

// Short name = last word (e.g. "North Queensland Cowboys" → "Cowboys")
function shortName(name: string): string {
  return name.trim().split(/\s+/).pop() ?? name;
}

// Best game-specific URL we can construct per bookmaker.
// TAB uses full-name slug URLs (no event ID needed).
// Sportsbet/Neds use event IDs we don't have — search is the next best option.
// All others fall back to the competition-level URL.
// Soccer sports (EPL/CHAMPIONSHIP/UCL) get a bookmaker search URL where the
// bookie supports it, otherwise the bookmaker homepage — per-competition soccer
// deep links are a hook-up task.
export function buildGameUrl(
  bookmaker: string,
  sport: 'NRL' | 'AFL' | 'EPL' | 'CHAMPIONSHIP' | 'UCL',
  homeTeam: string,
  awayTeam: string,
): string {
  if (sport !== 'NRL' && sport !== 'AFL') {
    if (bookmaker === 'neds' || bookmaker === 'ladbrokes_au') {
      const q = encodeURIComponent(`${shortName(homeTeam)} ${shortName(awayTeam)}`);
      const host = bookmaker === 'neds' ? 'www.neds.com.au' : 'www.ladbrokes.com.au';
      return `https://${host}/search?q=${q}`;
    }
    return SOCCER_URLS[bookmaker] ?? '';
  }

  const isAFL = sport === 'AFL';

  if (bookmaker === 'tab') {
    const comp = isAFL
      ? 'Australian%20Rules/competitions/AFL'
      : 'Rugby%20League/competitions/NRL';
    return `https://www.tab.com.au/sports/betting/${comp}/matches/${slugify(homeTeam)}-v-${slugify(awayTeam)}`;
  }

  if (bookmaker === 'tabtouch') {
    const comp = isAFL ? 'australian-rules/afl' : 'rugby-league/national-rugby-league';
    return `https://www.tabtouch.com.au/sports/${comp}/${slugify(homeTeam).toLowerCase()}-vs-${slugify(awayTeam).toLowerCase()}`;
  }

  if (bookmaker === 'sportsbet') {
    return isAFL
      ? 'https://www.sportsbet.com.au/betting/australian-rules/afl'
      : 'https://www.sportsbet.com.au/betting/rugby-league/nrl';
  }

  if (bookmaker === 'neds') {
    const q = encodeURIComponent(`${shortName(homeTeam)} ${shortName(awayTeam)}`);
    return `https://www.neds.com.au/search?q=${q}`;
  }

  if (bookmaker === 'ladbrokes_au') {
    const q = encodeURIComponent(`${shortName(homeTeam)} ${shortName(awayTeam)}`);
    return `https://www.ladbrokes.com.au/search?q=${q}`;
  }

  // Betright, Betr, PointsBet, Unibet, Betfair all use internal event IDs — competition page is best we can do
  const map = isAFL ? AFL_URLS : NRL_URLS;
  return map[bookmaker] ?? '';
}
