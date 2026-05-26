import { NextRequest, NextResponse } from 'next/server';
import { getDataStore } from '@/lib/supabaseServer';

interface MatchRecord {
  date: string;
  homeTeam: string;
  awayTeam: string;
  homeScore: number;
  awayScore: number;
  venue: string;
}

interface FormGame {
  date: string;
  opponent: string;
  teamScore: number;
  oppScore: number;
  won: boolean;
  isHome: boolean;
  venue: string;
}

// Last word of full team name (the "nickname") used for fuzzy matching
function nickname(fullName: string): string {
  return fullName.split(' ').pop()!.toLowerCase();
}

function teamMatches(record: string, nick: string): boolean {
  return record.toLowerCase().includes(nick);
}

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const home = searchParams.get('home') ?? '';
  const away = searchParams.get('away') ?? '';
  const sport = searchParams.get('sport') ?? 'NRL';

  if (sport !== 'NRL') {
    return NextResponse.json({ homeForm: [], awayForm: [], h2h: [], note: 'AFL history coming soon' });
  }

  const allMatches = await getDataStore('nrl_match_history') as MatchRecord[] | null;
  if (!allMatches) {
    return NextResponse.json({ homeForm: [], awayForm: [], h2h: [] });
  }

  const homeNick = nickname(home);
  const awayNick = nickname(away);

  function toFormGame(m: MatchRecord, perspective: string): FormGame {
    const perspNick = nickname(perspective);
    const isHome = teamMatches(m.homeTeam, perspNick);
    const teamScore = isHome ? m.homeScore : m.awayScore;
    const oppScore  = isHome ? m.awayScore : m.homeScore;
    const oppTeam   = isHome ? m.awayTeam  : m.homeTeam;
    return {
      date: m.date,
      opponent: oppTeam,
      teamScore,
      oppScore,
      won: teamScore > oppScore,
      isHome,
      venue: m.venue,
    };
  }

  const homeMatches = allMatches
    .filter(m => teamMatches(m.homeTeam, homeNick) || teamMatches(m.awayTeam, homeNick))
    .slice(0, 6)
    .map(m => toFormGame(m, home));

  const awayMatches = allMatches
    .filter(m => teamMatches(m.homeTeam, awayNick) || teamMatches(m.awayTeam, awayNick))
    .slice(0, 6)
    .map(m => toFormGame(m, away));

  const h2hMatches = allMatches
    .filter(m =>
      (teamMatches(m.homeTeam, homeNick) && teamMatches(m.awayTeam, awayNick)) ||
      (teamMatches(m.homeTeam, awayNick) && teamMatches(m.awayTeam, homeNick))
    )
    .slice(0, 6);

  return NextResponse.json({
    homeForm: homeMatches,
    awayForm: awayMatches,
    h2h: h2hMatches,
  });
}
