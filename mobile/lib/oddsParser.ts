export interface OddsApiEvent {
  id: string;
  sport_key: string;
  commence_time: string;
  home_team: string;
  away_team: string;
  bookmakers: {
    key: string;
    title: string;
    last_update: string;
    markets: {
      key: string;
      outcomes: { name: string; price: number; point?: number }[];
    }[];
  }[];
}

export interface ParsedGame {
  id: string;
  sport: 'NRL' | 'AFL';
  homeTeam: string;
  awayTeam: string;
  homeShort: string;
  awayShort: string;
  commenceTime: string;
  kickoffTime: string;
  h2h: Record<string, { home: number; away: number }>;
  spreads: Record<string, { home: number; away: number; homePoint: number; awayPoint: number }>;
  totals: Record<string, { over: number; under: number; point: number }>;
}

function normalize(v: string): string {
  return v.toLowerCase().replace(/&/g, 'and').replace(/\bfc\b/g, '').replace(/[^a-z0-9]+/g, ' ').trim();
}

function findOutcome(outcomes: { name: string; price: number; point?: number }[], team: string) {
  const t = normalize(team);
  return outcomes.find((o) => normalize(o.name) === t);
}

export function parseEvents(events: OddsApiEvent[], sport: 'NRL' | 'AFL'): ParsedGame[] {
  return events.map((ev) => {
    const h2h: ParsedGame['h2h'] = {};
    const spreads: ParsedGame['spreads'] = {};
    const totals: ParsedGame['totals'] = {};

    for (const bm of ev.bookmakers) {
      const h2hMkt = bm.markets.find((m) => m.key === 'h2h');
      if (h2hMkt) {
        const home = findOutcome(h2hMkt.outcomes, ev.home_team);
        const away = findOutcome(h2hMkt.outcomes, ev.away_team);
        if (home && away) h2h[bm.key] = { home: home.price, away: away.price };
      }

      const spreadsMkt = bm.markets.find((m) => m.key === 'spreads');
      if (spreadsMkt) {
        const home = findOutcome(spreadsMkt.outcomes, ev.home_team);
        const away = findOutcome(spreadsMkt.outcomes, ev.away_team);
        if (home && away && home.point != null && away.point != null) {
          spreads[bm.key] = { home: home.price, away: away.price, homePoint: home.point, awayPoint: away.point };
        }
      }

      const totalsMkt = bm.markets.find((m) => m.key === 'totals');
      if (totalsMkt) {
        const over = totalsMkt.outcomes.find((o) => o.name === 'Over');
        const under = totalsMkt.outcomes.find((o) => o.name === 'Under');
        if (over && under && over.point != null) {
          totals[bm.key] = { over: over.price, under: under.price, point: over.point };
        }
      }
    }

    const kickoff = new Date(ev.commence_time);
    const kickoffTime = kickoff.toLocaleString('en-AU', {
      weekday: 'short', hour: '2-digit', minute: '2-digit', hour12: true, timeZone: 'Australia/Sydney',
    }).toUpperCase() + ' AEST';

    return {
      id: ev.id,
      sport,
      homeTeam: ev.home_team,
      awayTeam: ev.away_team,
      homeShort: ev.home_team.split(' ').pop()!.toUpperCase(),
      awayShort: ev.away_team.split(' ').pop()!.toUpperCase(),
      commenceTime: ev.commence_time,
      kickoffTime,
      h2h,
      spreads,
      totals,
    };
  });
}
