import assert from 'node:assert/strict';
import test from 'node:test';
import { mapEspnGames, matchCompletedFixtures } from '../lib/tippingResults';
import { EPL_GW1_FIXTURES } from '../lib/tipping';

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

test('does not score an unfinished game', () => {
  const games = mapEspnGames([{ date: '2026-08-23T13:00:00Z', status: { type: { completed: false } },
    competitions: [{ competitors: [
      { homeAway: 'home', score: '0', team: { displayName: 'Brighton & Hove Albion' } },
      { homeAway: 'away', score: '0', team: { displayName: 'Aston Villa' } },
    ] }] }]);
  assert.deepEqual(matchCompletedFixtures(EPL_GW1_FIXTURES, games), []);
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
