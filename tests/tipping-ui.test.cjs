// Local synthetic browser regression tests. See docs/change-workflow.md.
const assert = require('node:assert/strict');
const { test } = require('node:test');
const { chromium } = require('playwright');
const fixtures = require('../lib/epl-2026-27-fixtures.json');
const baseURL = process.env.TIPPING_TEST_URL || 'http://localhost:3101';
if (!['localhost', '127.0.0.1'].includes(new URL(baseURL).hostname)) throw new Error('Run these synthetic tests against localhost only');

const uid = '00000000-0000-4000-8000-000000000001';
const user = { id: uid, email: 'tester@example.test', aud: 'authenticated', role: 'authenticated' };
const encode = value => Buffer.from(JSON.stringify(value)).toString('base64url');
const session = {
  access_token: encode({ alg: 'HS256', typ: 'JWT' }) + '.' + encode({ sub: uid, exp: 2200000000, role: 'authenticated' }) + '.synthetic',
  refresh_token: 'synthetic-refresh', expires_at: 2200000000, expires_in: 3600, token_type: 'bearer', user,
};
function deferred() {
  let resolve;
  const promise = new Promise(done => { resolve = done; });
  return { promise, resolve };
}
const roundFixtures = gw => fixtures.filter(f => f.gameweek === gw).map(f => ({ ...f, kickoff: '2030-08-01T15:00:00Z' }));
const roundTips = gw => roundFixtures(gw).map(f => ({ game_id: f.id, gameweek: gw, selection: 'home', result: null, points: 0 }));

async function setup(t, intercept = async () => false) {
  const browser = await chromium.launch();
  t.after(() => browser.close());
  const context = await browser.newContext();
  await context.addCookies([{ name: 'sb-tipping-test-auth-token', value: 'base64-' + encode(session), domain: new URL(baseURL).hostname, path: '/' }]);
  const page = await context.newPage();
  page.setDefaultTimeout(15000);
  await page.clock.install({ time: new Date('2026-09-10T00:00:00Z') });
  const stored = new Map([[1, roundTips(1)], [3, roundTips(3)], [4, roundTips(4)]]);
  const saves = [];
  await page.route('https://tipping-test.supabase.co/**', route => route.fulfill({ json: user }));
  await page.route('**/api/tipping/**', async route => {
    const url = new URL(route.request().url());
    const gw = Number(url.searchParams.get('gameweek') || 1);
    const kind = url.pathname.split('/').pop();
    // Aborted requests may already be closed when a deliberately delayed
    // response is released. Only suppress that expected fixture condition.
    const reply = body => route.fulfill(body).catch(error => {
      if (!/closed|already handled|Invalid InterceptionId/i.test(error.message)) throw error;
    });
    if (await intercept({ page, kind, gw, route, reply, stored, saves })) return;
    if (kind === 'join') return reply({ json: { comp: { id: 'test-comp', name: 'Test competition', invite_code: 'TEST' }, display_name: 'Tester' } });
    if (kind === 'gameweeks') return reply({ json: { current_gameweek: 3, season_complete: false } });
    if (kind === 'fixtures') return reply({ json: { gameweek: gw, fixtures: roundFixtures(gw), round_complete: false } });
    if (kind === 'leaderboard') return reply({ json: { leaderboard: [] } });
    if (kind === 'tips' && route.request().method() === 'POST') {
      const body = route.request().postDataJSON();
      saves.push(body);
      stored.set(body.gameweek, body.tips.map(tip => ({ ...tip, gameweek: body.gameweek, result: null, points: 0 })));
      return reply({ json: { results: body.tips.map(tip => ({ game_id: tip.game_id, success: true })) } });
    }
    if (kind === 'tips') return reply({ json: { tips: stored.get(gw) || [] } });
    throw new Error('Unexpected test request: ' + kind);
  });
  await page.goto(baseURL + '/tipping', { waitUntil: 'domcontentloaded' });
  return { page, stored, saves };
}
async function expectRound(page, gw) {
  await page.getByText('Gameweek ' + gw, { exact: true }).waitFor();
  await page.getByText('10/10 tipped', { exact: true }).waitFor();
  assert.equal(await page.locator('[data-fixture-id] button[aria-pressed="true"]').count(), 10);
  assert.deepEqual(await page.locator('[data-fixture-id]').evaluateAll(nodes => nodes.map(n => n.dataset.fixtureId)), roundFixtures(gw).map(f => f.id));
}

test('late initial-round tips cannot erase saved highlights or inflate the count; edits survive save/reload', { timeout: 60000 }, async t => {
  const oldSeen = deferred(), oldGate = deferred();
  const { page, saves } = await setup(t, async ({ kind, gw, reply, route }) => {
    if (kind === 'gameweeks') { await oldSeen.promise; await reply({ json: { current_gameweek: 3, season_complete: false } }); return true; }
    if (kind === 'tips' && gw === 1 && route.request().method() === 'GET') { oldSeen.resolve(); await oldGate.promise; await reply({ json: { tips: roundTips(1) } }); return true; }
    return false;
  });
  t.after(() => oldGate.resolve());
  await expectRound(page, 3);
  oldGate.resolve();
  await page.waitForTimeout(100);
  await expectRound(page, 3);
  await page.getByRole('button', { name: 'Draw', exact: true }).first().click();
  await expectRound(page, 3);
  await page.getByRole('button', { name: 'Save Tips (10/10)', exact: true }).click();
  await page.getByRole('button', { name: 'Saved!', exact: true }).waitFor();
  assert.equal(saves.length, 1);
  assert.equal(saves[0].gameweek, 3);
  assert.equal(saves[0].tips.length, 10);
  assert.equal(new Set(saves[0].tips.map(tip => tip.game_id)).size, 10);
  assert.ok(saves[0].tips.every(tip => tip.game_id.startsWith('epl-2627-gw3-')));
  await page.reload({ waitUntil: 'domcontentloaded' });
  await expectRound(page, 3);
  assert.equal(await page.getByRole('button', { name: 'Draw', exact: true }).first().getAttribute('aria-pressed'), 'true');
  if (process.env.TIPPING_REVIEW_SCREENSHOT) await page.screenshot({ path: process.env.TIPPING_REVIEW_SCREENSHOT, fullPage: true });
});

test('switching rounds ignores delayed fixtures and never exposes mixed-round cards', { timeout: 60000 }, async t => {
  const seen = deferred(), gate = deferred();
  const { page } = await setup(t, async ({ kind, gw, reply }) => {
    if (kind === 'fixtures' && gw === 4) { seen.resolve(); await gate.promise; await reply({ json: { gameweek: 4, fixtures: roundFixtures(4), round_complete: false } }); return true; }
    return false;
  });
  t.after(() => gate.resolve());
  await expectRound(page, 3);
  await page.getByRole('button', { name: 'Next', exact: true }).click();
  await seen.promise;
  assert.equal(await page.locator('[data-fixture-id]').count(), 0);
  await page.getByRole('button', { name: 'Prev', exact: true }).click();
  await expectRound(page, 3);
  gate.resolve();
  await page.waitForTimeout(100);
  await expectRound(page, 3);
  await page.getByRole('button', { name: 'Next', exact: true }).click();
  await expectRound(page, 4);
});

test('foreign/invalid tip rows do not inflate progress or highlight the wrong fixture', { timeout: 60000 }, async t => {
  const { page } = await setup(t, async ({ kind, gw, reply }) => {
    if (kind === 'tips' && gw === 3) { await reply({ json: { tips: [...roundTips(3), ...roundTips(1), roundTips(3)[0], { gameweek: 3, game_id: 'obsolete-id', selection: 'away' }] } }); return true; }
    return false;
  });
  await expectRound(page, 3);
  await page.getByRole('button', { name: 'Draw', exact: true }).first().click();
  await expectRound(page, 3);
});

test('background refresh cannot overwrite a choice made and saved while it was pending', { timeout: 60000 }, async t => {
  let holdRefresh = false;
  const seen = deferred(), gate = deferred();
  const { page } = await setup(t, async ({ kind, gw, route, reply }) => {
    if (kind === 'tips' && gw === 3 && route.request().method() === 'GET' && holdRefresh) {
      seen.resolve(); await gate.promise; await reply({ json: { tips: roundTips(3) } }); return true;
    }
    return false;
  });
  t.after(() => gate.resolve());
  await expectRound(page, 3);
  holdRefresh = true;
  await page.clock.fastForward(5 * 60 * 1000);
  await seen.promise;
  const draw = page.getByRole('button', { name: 'Draw', exact: true }).first();
  await draw.click();
  await page.getByRole('button', { name: 'Save Tips (10/10)', exact: true }).click();
  await page.getByRole('button', { name: 'Saved!', exact: true }).waitFor();
  gate.resolve();
  await page.waitForTimeout(100);
  assert.equal(await draw.getAttribute('aria-pressed'), 'true');
  await expectRound(page, 3);
  // The next automatic refresh must also leave an unsaved choice alone.
  await page.getByRole('button', { name: roundFixtures(3)[0].away_team, exact: true }).click();
  await page.clock.fastForward(5 * 60 * 1000);
  assert.equal(await page.getByRole('button', { name: roundFixtures(3)[0].away_team, exact: true }).getAttribute('aria-pressed'), 'true');
});

test('failed tip loads offer retry and failed saves never show Saved', { timeout: 60000 }, async t => {
  let failLoad = true, failSave = true;
  const { page } = await setup(t, async ({ kind, gw, route, reply }) => {
    if (kind === 'tips' && route.request().method() === 'POST' && failSave) { await reply({ json: { results: [{ game_id: roundFixtures(3)[0].id, error: 'synthetic write failure' }] } }); return true; }
    if (kind === 'tips' && gw === 3 && failLoad) { await reply({ status: 500, json: { error: 'synthetic read failure' } }); return true; }
    return false;
  });
  await page.getByRole('alert').filter({ hasText: /Could not|Some tips/ }).waitFor();
  assert.equal(await page.locator('[data-fixture-id]').count(), 0);
  failLoad = false;
  await page.getByRole('button', { name: 'Retry', exact: true }).click();
  await expectRound(page, 3);
  await page.getByRole('button', { name: 'Draw', exact: true }).first().click();
  await page.getByRole('button', { name: 'Save Tips (10/10)', exact: true }).click();
  await page.getByRole('alert').filter({ hasText: /Could not|Some tips/ }).waitFor();
  assert.equal(await page.getByRole('button', { name: 'Saved!', exact: true }).count(), 0);
  assert.equal(await page.getByRole('button', { name: 'Draw', exact: true }).first().getAttribute('aria-pressed'), 'true');
  failSave = false;
  await page.getByRole('button', { name: 'Save Tips (10/10)', exact: true }).click();
  await page.getByRole('button', { name: 'Saved!', exact: true }).waitFor();
});
