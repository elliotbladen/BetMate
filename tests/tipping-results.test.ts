import assert from 'node:assert/strict';
import test from 'node:test';
import { findCurrentGameweek, gameweeksToSyncOnTransition, mapEspnGames, matchCompletedFixtures, type ApiGame } from '../lib/tippingResults';
import { EPL_SEASON_FIXTURES, getEplFixtures } from '../lib/tipping';

const EPL_GW1_FIXTURES = getEplFixtures(1);

test('maps ESPN aliases and home/away scores to the canonical fixture', () => {
  const games = mapEspnGames([{ date: '2026-08-23T13:00:00Z', status: { type: { completed: true } },
    competitions: [{ competitors: [
      { homeAway: 'home', score: '2', team: { displayName: 'Manchester City' } },
      { homeAway: 'away', score: '1', team: { displayName: 'AFC Bournemouth' } },
    ] }] }]);
  assert.deepEqual(matchCompletedFixtures(EPL_GW1_FIXTURES, games), [
    { game_id: 'epl-2627-gw1-8', home_score: 2, away_score: 1 },
  ]);
});

test('matches Brighton & Hove Albion (ESPN) to Brighton and Hove Albion (fixture)', () => {
  const games = mapEspnGames([{ date: '2026-08-23T13:00:00Z', status: { type: { completed: true } },
    competitions: [{ competitors: [
      { homeAway: 'home', score: '4', team: { displayName: 'Brighton & Hove Albion' } },
      { homeAway: 'away', score: '0', team: { displayName: 'Aston Villa' } },
    ] }] }]);
  assert.deepEqual(matchCompletedFixtures(EPL_GW1_FIXTURES, games), [
    { game_id: 'epl-2627-gw1-7', home_score: 4, away_score: 0 },
  ]);
});

test('does not score an unfinished game', () => {
  const games = mapEspnGames([{ date: '2026-08-23T13:00:00Z', status: { type: { completed: false } },
    competitions: [{ competitors: [
      { homeAway: 'home', score: '0', team: { displayName: 'Brighton & Hove Albion' } },
      { homeAway: 'away', score: '0', team: { displayName: 'Aston Villa' } },
    ] }] }]);
  assert.deepEqual(matchCompletedFixtures(EPL_GW1_FIXTURES, games), []);
});

test('a postponed match still resolves by its unique home-away pairing', () => {
  const games = [{ completed: true, commence_time: '2026-09-21T19:00:00Z',
    home_team: 'Arsenal', away_team: 'Coventry City',
    scores: [{ name: 'Arsenal', score: '2' }, { name: 'Coventry City', score: '0' }] }];
  assert.deepEqual(matchCompletedFixtures(EPL_GW1_FIXTURES, games), [
    { game_id: 'epl-2627-gw1-1', home_score: 2, away_score: 0 },
  ]);
});

test('primary and fallback provider shapes produce the same result', () => {
  const expected = [{ game_id: 'epl-2627-gw1-1', home_score: 3, away_score: 0 }];
  const primary = [{ completed: true, commence_time: '2026-08-21T19:00:00Z',
    home_team: 'Arsenal', away_team: 'Coventry City',
    scores: [{ name: 'Arsenal', score: '3' }, { name: 'Coventry City', score: '0' }] }];
  const fallback = mapEspnGames([{ date: '2026-08-21T19:00:00Z', status: { type: { completed: true } },
    competitions: [{ competitors: [
      { homeAway: 'home', score: '3', team: { displayName: 'Arsenal' } },
      { homeAway: 'away', score: '0', team: { displayName: 'Coventry City' } },
    ] }] }]);
  assert.deepEqual(matchCompletedFixtures(EPL_GW1_FIXTURES, primary), expected);
  assert.deepEqual(matchCompletedFixtures(EPL_GW1_FIXTURES, fallback), expected);
});

test('the active round and its next round both have complete fixture cards', () => {
  assert.equal(EPL_SEASON_FIXTURES.length, 380);
  for (let gameweek = 1; gameweek <= 38; gameweek++) {
    const fixtures = getEplFixtures(gameweek);
    assert.equal(fixtures.length, 10);
    assert.equal(new Set(fixtures.flatMap(fixture => [fixture.home_team, fixture.away_team])).size, 20);
  }
  assert.equal(getEplFixtures(39).length, 0);
  assert.equal(getEplFixtures(1).find(fixture => fixture.id === 'epl-2627-gw1-3')?.home_team, 'Everton');
  assert.equal(getEplFixtures(1).find(fixture => fixture.id === 'epl-2627-gw1-5')?.home_team, 'Nottingham Forest');
});

test('rolling window advances only after the final match and stops after week 38', () => {
  const games: ApiGame[] = EPL_SEASON_FIXTURES.map(fixture => ({
    completed: false, commence_time: fixture.kickoff, home_team: fixture.home_team,
    away_team: fixture.away_team, scores: [{ name: fixture.home_team, score: '1' }, { name: fixture.away_team, score: '0' }],
  }));
  assert.equal(findCurrentGameweek(games), 1);
  games.slice(0, 9).forEach(game => { game.completed = true; });
  assert.equal(findCurrentGameweek(games), 1);
  games[9].completed = true;
  assert.equal(findCurrentGameweek(games), 2);
  games.forEach(game => { game.completed = true; });
  assert.equal(findCurrentGameweek(games), null);
});

test('round transition resynchronises the round that just finished', () => {
  assert.deepEqual(gameweeksToSyncOnTransition(1), []);
  assert.deepEqual(gameweeksToSyncOnTransition(2), [1]);
  assert.deepEqual(gameweeksToSyncOnTransition(3), [2]);
  assert.deepEqual(gameweeksToSyncOnTransition(38), [37]);
  assert.deepEqual(gameweeksToSyncOnTransition(null), [38]);
});
