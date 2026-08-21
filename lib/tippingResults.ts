import { createServerClient } from '@/lib/supabaseServer';
import { EPL_GW1_FIXTURES, getActualResult, scoreResult, type Fixture } from '@/lib/tipping';

type ApiScore = { name: string; score: string };
type ApiGame = {
  completed: boolean;
  commence_time: string;
  home_team: string;
  away_team: string;
  scores: ApiScore[] | null;
};

export type CompletedFixture = {
  game_id: string;
  home_score: number;
  away_score: number;
};

function normaliseTeam(name: string): string {
  return name.toLowerCase().replace(/[^a-z0-9]/g, '');
}

export function matchCompletedFixtures(fixtures: Fixture[], games: ApiGame[]): CompletedFixture[] {
  const completed: CompletedFixture[] = [];
  for (const fixture of fixtures) {
    const match = games.find(game =>
      game.completed &&
      normaliseTeam(game.home_team) === normaliseTeam(fixture.home_team) &&
      normaliseTeam(game.away_team) === normaliseTeam(fixture.away_team) &&
      Math.abs(new Date(game.commence_time).getTime() - new Date(fixture.kickoff).getTime()) <= 24 * 60 * 60 * 1000
    );
    if (!match?.scores) continue;
    const home = match.scores.find(score => normaliseTeam(score.name) === normaliseTeam(fixture.home_team));
    const away = match.scores.find(score => normaliseTeam(score.name) === normaliseTeam(fixture.away_team));
    const homeScore = Number(home?.score);
    const awayScore = Number(away?.score);
    if (!Number.isInteger(homeScore) || !Number.isInteger(awayScore)) continue;
    completed.push({ game_id: fixture.id, home_score: homeScore, away_score: awayScore });
  }
  return completed;
}

function fixturesForGameweek(gameweek: number): Fixture[] {
  return gameweek === 1 ? EPL_GW1_FIXTURES : [];
}

export async function syncTippingResults(gameweek: number): Promise<CompletedFixture[]> {
  const fixtures = fixturesForGameweek(gameweek);
  const apiKey = process.env.ODDS_API_KEY;
  if (!apiKey || fixtures.length === 0) return [];

  const supabase = createServerClient();
  const { data: pendingTips } = await supabase.from('tipping_tips')
    .select('id, comp_id, user_id, game_id, selection, result')
    .eq('gameweek', gameweek)
    .is('result', null);
  if (!pendingTips?.length) return [];

  const now = Date.now();
  const hasPotentiallyFinishedGame = fixtures.some(fixture =>
    new Date(fixture.kickoff).getTime() + 90 * 60 * 1000 <= now &&
    pendingTips.some(tip => tip.game_id === fixture.id)
  );
  if (!hasPotentiallyFinishedGame) return [];

  const url = new URL('https://api.the-odds-api.com/v4/sports/soccer_epl/scores/');
  url.searchParams.set('apiKey', apiKey);
  url.searchParams.set('daysFrom', '3');
  url.searchParams.set('dateFormat', 'iso');
  const response = await fetch(url.toString(), { next: { revalidate: 300 } });
  if (!response.ok) return [];
  const completed = matchCompletedFixtures(fixtures, await response.json() as ApiGame[]);
  if (completed.length === 0) return [];

  const touched = new Set<string>();
  for (const game of completed) {
    const actual = getActualResult(game.home_score, game.away_score);
    for (const tip of pendingTips.filter(row => row.game_id === game.game_id)) {
      const points = scoreResult(tip.selection, game.home_score, game.away_score);
      const { error } = await supabase.from('tipping_tips')
        .update({ result: actual, points }).eq('id', tip.id).is('result', null);
      if (!error) touched.add(`${tip.comp_id}:${tip.user_id}`);
    }
  }

  for (const key of Array.from(touched)) {
    const [compId, userId] = key.split(':');
    const { data: scoredTips } = await supabase.from('tipping_tips').select('points')
      .eq('comp_id', compId).eq('user_id', userId).not('result', 'is', null);
    const total = (scoredTips ?? []).reduce((sum, tip) => sum + (tip.points ?? 0), 0);
    await supabase.from('tipping_entries').update({ total_points: total })
      .eq('comp_id', compId).eq('user_id', userId);
  }
  return completed;
}

export function applyCompletedScores(fixtures: Fixture[], completed: CompletedFixture[]): Fixture[] {
  return fixtures.map(fixture => {
    const score = completed.find(game => game.game_id === fixture.id);
    return score ? {
      ...fixture,
      home_score: score.home_score,
      away_score: score.away_score,
      status: 'finished' as const,
    } : fixture;
  });
}
