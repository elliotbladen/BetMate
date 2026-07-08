export const BOOKMAKER_META: Record<string, { abbr: string; name: string; domain: string }> = {
  sportsbet:     { abbr: 'SB',  name: 'Sportsbet', domain: 'sportsbet.com.au'   },
  tab:           { abbr: 'TAB', name: 'TAB',        domain: 'tab.com.au'         },
  tabtouch:      { abbr: 'TBT', name: 'TABtouch',   domain: 'tabtouch.com.au'    },
  neds:          { abbr: 'NED', name: 'Neds',       domain: 'neds.com.au'        },
  betfair_ex_au: { abbr: 'BF',  name: 'Betfair',    domain: 'betfair.com.au'     },
  ladbrokes_au:  { abbr: 'LAD', name: 'Ladbrokes',  domain: 'ladbrokes.com.au'   },
  unibet:        { abbr: 'UNI', name: 'Unibet',     domain: 'unibet.com.au'      },
  pointsbetau:   { abbr: 'PB',  name: 'PointsBet',  domain: 'pointsbet.com.au'   },
  betr_au:       { abbr: 'BTR', name: 'Betr',       domain: 'betr.com.au'        },
  betright:      { abbr: 'BR',  name: 'BetRight',   domain: 'betright.com.au'    },
  playup:        { abbr: 'PU',  name: 'PlayUp',     domain: 'playup.com.au'      },
};

export const BOOKMAKER_ORDER = Object.keys(BOOKMAKER_META);

export function effectivePrice(key: string, price: number): number {
  if (key === 'betfair_ex_au') return 1 + (price - 1) * 0.95;
  return price;
}
