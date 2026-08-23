import { createServerClient } from '@/lib/supabaseServer';
import { getActualResult, getEplFixtures, scoreResult, type Fixture } from '@/lib/tipping';

type ApiScore = { name: string; score: string };
export type ApiGame = { completed: boolean; commence_time: string; home_team: string; away_team: string; scores: ApiScore[] | null };
type EspnCompetitor = { homeAway: 'home' | 'away'; score: string; team?: { displayName?: string } };
type EspnEvent = { date: string; status?: { type?: { completed?: boolean } }; competitions?: Array<{ competitors?: EspnCompetitor[] }> };

export type CompletedFixture = { game_id: string; home_score: number; away_score: number };

function normaliseTeam(name: string): string {
  return name.toLowerCase().replace(/&/g, 'and').replace(/\b(afc|fc)\b/g, '').replace(/[^a-z0-9]/g, '');
}

export function matchCompletedFixtures(fixtures: Fixture[], games: ApiGame[]): CompletedFixture[] {
  const completed: CompletedFixture[] = [];
  for (const fixture of fixtures) {
    const match = games.find(game => game.completed &&
      normaliseTeam(game.home_team) === normaliseTeam(fixture.home_team) &&
      normaliseTeam(game.away_team) === normaliseTeam(fixture.away_team));
    if (!match?.scores) continue;
    const homeScore = Number(match.scores.find(score => normaliseTeam(score.name) === normaliseTeam(fixture.home_team))?.score);
    const awayScore = Number(match.scores.find(score => normaliseTeam(score.name) === normaliseTeam(fixture.away_team))?.score);
    if (Number.isInteger(homeScore) && Number.isInteger(awayScore)) completed.push({ game_id: fixture.id, home_score: homeScore, away_score: awayScore });
  }
  return completed;
}

export function mapEspnGames(events: EspnEvent[]): ApiGame[] {
  return events.map(event => {
    const competitors = event.competitions?.[0]?.competitors ?? [];
    const home = competitors.find(team => team.homeAway === 'home');
    const away = competitors.find(team => team.homeAway === 'away');
    return {
      completed: event.status?.type?.completed === true, commence_time: event.date,
      home_team: home?.team?.displayName ?? '', away_team: away?.team?.displayName ?? '',
      scores: home && away ? [{ name: home.team?.displayName ?? '', score: home.score }, { name: away.team?.displayName ?? '', score: away.score }] : null,
    };
  });
}

async function fetchOddsApiScores(): Promise<ApiGame[]> {
  const apiKey = process.env.ODDS_API_KEY;
  if (!apiKey) throw new Error('ODDS_API_KEY is not configured');
  const url = new URL('https://api.the-odds-api.com/v4/sports/soccer_epl/scores/');
  url.searchParams.set('apiKey', apiKey); url.searchParams.set('daysFrom', '3'); url.searchParams.set('dateFormat', 'iso');
  const response = await fetch(url.toString(), { cache: 'no-store' });
  if (!response.ok) throw new Error(`The Odds API returned ${response.status}`);
  return await response.json() as ApiGame[];
}

async function fetchEspnScores(fixtures: Fixture[]): Promise<ApiGame[]> {
  const dates = fixtures.map(fixture => fixture.kickoff.slice(0, 10).replaceAll('-', '')).sort();
  const url = new URL('https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/scoreboard');
  url.searchParams.set('dates', `${dates[0]}-${dates[dates.length - 1]}`); url.searchParams.set('limit', '100');
  const response = await fetch(url.toString(), { cache: 'no-store' });
  if (!response.ok) throw new Error(`ESPN scores returned ${response.status}`);
  const payload = await response.json() as { events?: EspnEvent[] };
  return mapEspnGames(payload.events ?? []);
}

async function fetchEspnSeasonScores(): Promise<ApiGame[]> {
  const url = new URL('https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/scoreboard');
  url.searchParams.set('dates', '20260801-20270531');
  url.searchParams.set('limit', '500');
  const response = await fetch(url.toString(), { cache: 'no-store' });
  if (!response.ok) throw new Error(`ESPN season scores returned ${response.status}`);
  const payload = await response.json() as { events?: EspnEvent[] };
  return mapEspnGames(payload.events ?? []);
}

export function findCurrentGameweek(games: ApiGame[]): number | null {
  for (let gameweek = 1; gameweek <= 38; gameweek++) {
    const fixtures = getEplFixtures(gameweek);
    if (matchCompletedFixtures(fixtures, games).length !== fixtures.length) return gameweek;
  }
  return null;
}

export async function getCurrentEplGameweek(): Promise<number | null> {
  return findCurrentGameweek(await fetchEspnSeasonScores());
}

async function completedScores(fixtures: Fixture[]): Promise<CompletedFixture[]> {
  const failures: string[] = [];
  let providerResponded = false;
  for (const provider of [fetchOddsApiScores, () => fetchEspnScores(fixtures)]) {
    try {
      const games = await provider();
      providerResponded = true;
      const completed = matchCompletedFixtures(fixtures, games);
      if (completed.length > 0) return completed;
      failures.push('provider returned no matching completed fixtures');
    } catch (error) { failures.push(error instanceof Error ? error.message : 'unknown provider error'); }
  }
  if (providerResponded) return [];
  throw new Error(`Unable to refresh tipping results: ${failures.join('; ')}`);
}

export async function syncTippingResults(gameweek: number): Promise<CompletedFixture[]> {
  const fixtures = getEplFixtures(gameweek);
  if (!fixtures.length || !fixtures.some(fixture => new Date(fixture.kickoff).getTime() + 5400000 <= Date.now())) return [];
  const completed = await completedScores(fixtures);
  const supabase = createServerClient();
  const { data: tips, error: tipsError } = await supabase.from('tipping_tips').select('id, comp_id, user_id, game_id, selection, result, points').eq('gameweek', gameweek);
  if (tipsError) throw new Error(`Could not read tipping tips: ${tipsError.message}`);

  for (const game of completed) {
    const actual = getActualResult(game.home_score, game.away_score);
    for (const tip of (tips ?? []).filter(row => row.game_id === game.game_id)) {
      const points = scoreResult(tip.selection, game.home_score, game.away_score);
      if (tip.result === actual && tip.points === points) continue;
      const { error } = await supabase.from('tipping_tips').update({ result: actual, points }).eq('id', tip.id);
      if (error) throw new Error(`Could not score tip ${tip.id}: ${error.message}`);
    }
  }

  // Rebuild every entrant total from the scored-tip ledger. This idempotent
  // repair also heals totals left stale by an earlier provider/API failure.
  const entryKeys = new Set((tips ?? []).map(tip => `${tip.comp_id}:${tip.user_id}`));
  for (const key of Array.from(entryKeys)) {
    const separator = key.indexOf(':'); const compId = key.slice(0, separator); const userId = key.slice(separator + 1);
    const { data: scoredTips, error: scoredError } = await supabase.from('tipping_tips').select('points').eq('comp_id', compId).eq('user_id', userId).not('result', 'is', null);
    if (scoredError) throw new Error(`Could not total tips: ${scoredError.message}`);
    const total = (scoredTips ?? []).reduce((sum, tip) => sum + (tip.points ?? 0), 0);
    const { error: totalError } = await supabase.from('tipping_entries').update({ total_points: total }).eq('comp_id', compId).eq('user_id', userId);
    if (totalError) throw new Error(`Could not update leaderboard: ${totalError.message}`);
  }
  return completed;
}

export function applyCompletedScores(fixtures: Fixture[], completed: CompletedFixture[]): Fixture[] {
  return fixtures.map(fixture => { const score = completed.find(game => game.game_id === fixture.id); return score ? { ...fixture, home_score: score.home_score, away_score: score.away_score, status: 'finished' as const } : fixture; });
}
