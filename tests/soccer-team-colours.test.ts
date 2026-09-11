import assert from 'node:assert/strict';
import test from 'node:test';
import { getTeamMeta, NRL_TEAMS, AFL_TEAMS } from '../lib/teams';

// Names captured from the live /api/odds/championship feed, 2026-09-10.
const championship = [
  'Birmingham City', 'Blackburn Rovers', 'Bolton Wanderers', 'Bristol City',
  'Burnley', 'Cardiff City', 'Charlton Athletic', 'Derby County', 'Lincoln City',
  'Middlesbrough', 'Millwall', 'Norwich City', 'Portsmouth', 'Preston North End',
  'Queens Park Rangers', 'Sheffield United', 'Southampton', 'Stoke City',
  'Swansea City', 'Watford', 'West Bromwich Albion', 'West Ham United',
  'Wolverhampton Wanderers', 'Wrexham AFC',
];
// UEFA's complete league-phase draw, including teams not in today's odds.
const ucl = [
  'AEK Athens', 'Arsenal', 'Aston Villa', 'Atleti', 'B. Dortmund', 'Barcelona',
  'Bayern München', 'Bodø/Glimt', 'Club Brugge', 'Como', 'Fenerbahçe', 'Feyenoord',
  'Galatasaray', 'Inter', 'LASK', 'Leipzig', 'Lens', 'Lille', 'Liverpool',
  'Man City', 'Man United', 'Napoli', 'Paris', 'Porto', 'PSV', 'Real Betis',
  'Real Madrid', 'Roma', 'S. Bratislava', 'Sabah', 'Shakhtar', 'Slavia Praha',
  'Sporting CP', 'Stuttgart', 'Viking', 'Villarreal',
];

test('every current Championship and UCL club has a colour badge', () => {
  assert.equal(new Set(championship).size, 24);
  assert.equal(new Set(ucl).size, 36);
  for (const name of [...championship, ...ucl]) {
    const meta = getTeamMeta(name);
    assert.ok(meta, `Missing colours for ${name}`);
    assert.match(meta.primary, /^#[0-9A-F]{6}$/i);
    assert.match(meta.secondary, /^#[0-9A-F]{6}$/i);
    assert.notEqual(meta.primary, meta.secondary, name);
  }
});

test('live feed names and spelling variants share the same club identity', () => {
  for (const [canonical, variants] of [
    ['Wrexham', ['Wrexham AFC', 'Wrexham A.F.C.']],
    ['Bodø/Glimt', ['Bodo/Glimt', 'FK Bodø/Glimt', '  BODØ / GLIMT  ']],
    ['Fenerbahce', ['Fenerbahçe', 'Fenerbahçe SK']],
    ['Slavia Praha', ['Slavia Prague', 'SK Slavia Praha']],
    ['AS Roma', ['Roma']], ['RC Lens', ['Lens']],
    ['Sabah FK', ['Sabah']], ['Shakhtar Donetsk', ['Shakhtar']],
    ['Sporting Lisbon', ['Sporting CP']],
    ['Paris Saint Germain', ['Paris Saint-Germain', 'PSG']],
    ['Brighton and Hove Albion', ['Brighton & Hove Albion']],
  ] as const) {
    for (const variant of variants) assert.equal(getTeamMeta(variant), getTeamMeta(canonical), variant);
  }
});

test('verified colour details and distinct clubs are preserved', () => {
  assert.deepEqual(getTeamMeta('Bodo/Glimt'), { abbr: 'BOD', primary: '#F8DD00', secondary: '#120F0A' });
  assert.equal(getTeamMeta('Sabah FK')?.primary, '#000000');
  assert.notDeepEqual(getTeamMeta('Manchester City'), getTeamMeta('Manchester United'));
  assert.equal(getTeamMeta('Manchester'), null);
  assert.equal(getTeamMeta('Sabah FC Malaysia'), null);
  assert.equal(getTeamMeta('Unknown FC'), null);
  assert.equal(getTeamMeta('constructor'), null);
  assert.equal(getTeamMeta(''), null);
  for (const [name, meta] of Object.entries({ ...NRL_TEAMS, ...AFL_TEAMS })) {
    assert.equal(getTeamMeta(name), meta, name);
  }
});
