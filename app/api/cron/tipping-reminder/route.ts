import { createHash, timingSafeEqual } from 'node:crypto';
import { NextResponse } from 'next/server';
import { createAdminClient } from '@/lib/supabaseAdmin';
import { EPL_SEASON_FIXTURES, getEplFixtures, isGameweekLocked } from '@/lib/tipping';

export const dynamic = 'force-dynamic';

// Target: roughly 24 hours before the first kickoff of the gameweek.
//
// Nobody is emailed twice - tipping_reminders dedupes per person per gameweek - so
// the daily cron is only how often we CHECK, not how often anyone is nagged. The
// send happens on the first check where the lock is within LEAD_HOURS.
//
// Vercel Hobby caps cron at once per day (more frequent expressions fail to
// deploy) with +/-59 min precision, so an exact 24h trigger is not available. The
// pair below was chosen by running every (hour, lead) combination against all 38
// real gameweek kickoffs in lib/epl-2026-27-fixtures.json:
//
//   15:00 UTC + 30h  ->  20.5h to 29.0h notice, MEDIAN EXACTLY 24.0h, 0 rounds under 20h
//   09:00 UTC + 48h  ->  26.5h to 35.0h notice, median 30.0h          (the old setting)
//   any hour  + 24h  ->   2.5h to 11.0h notice                        (looks right, is not)
//
// That last line is the trap: setting the lead to 24 to get "24 hours notice"
// makes it far WORSE, because the first daily check under 24h can be minutes
// before kickoff. The lead has to exceed the gap between checks.
//
// Re-run that comparison if the fixture list changes shape (a midweek round, or
// Friday-night kickoffs moving).
const LEAD_HOURS = Number(process.env.TIPPING_REMINDER_LEAD_HOURS ?? 30);

const RESEND_ENDPOINT = 'https://api.resend.com/emails';

/** Constant-time header comparison. Hashing first keeps length from leaking too. */
function timingSafeMatch(candidate: string | null, expected: string): boolean {
  if (!candidate) return false;
  const a = createHash('sha256').update(candidate).digest();
  const b = createHash('sha256').update(expected).digest();
  return timingSafeEqual(a, b);
}

type Missing = { userId: string; displayName: string; email: string; tipped: number };

/** The next gameweek that has not locked yet, or null if the season is done. */
function nextOpenGameweek(now: Date): { gameweek: number; locksAt: Date } | null {
  const gameweeks = [...new Set(EPL_SEASON_FIXTURES.map(f => f.gameweek))].sort((a, b) => a - b);
  for (const gameweek of gameweeks) {
    const fixtures = getEplFixtures(gameweek);
    if (fixtures.length === 0 || isGameweekLocked(fixtures, now)) continue;
    const locksAt = new Date(Math.min(...fixtures.map(f => new Date(f.kickoff).getTime())));
    return { gameweek, locksAt };
  }
  return null;
}

export async function GET(request: Request) {
  // Vercel Cron sends `Authorization: Bearer $CRON_SECRET`. Without the secret set
  // the route refuses outright rather than becoming a public mail trigger.
  const secret = process.env.CRON_SECRET;
  if (!secret) {
    return NextResponse.json({ error: 'CRON_SECRET not configured' }, { status: 503 });
  }
  if (!timingSafeMatch(request.headers.get('authorization'), `Bearer ${secret}`)) {
    return NextResponse.json({ error: 'Unauthorised' }, { status: 401 });
  }

  const dryRun = new URL(request.url).searchParams.get('dry_run') === '1';
  const now = new Date();
  const next = nextOpenGameweek(now);
  if (!next) return NextResponse.json({ status: 'no open gameweek' });

  const hoursToLock = (next.locksAt.getTime() - now.getTime()) / 3_600_000;
  if (hoursToLock > LEAD_HOURS) {
    return NextResponse.json({
      status: 'too early', gameweek: next.gameweek,
      locks_at: next.locksAt.toISOString(), hours_to_lock: Number(hoursToLock.toFixed(1)),
    });
  }

  // Service role: needs auth.users for emails and writes tipping_reminders.
  const supabase = createAdminClient();
  const fixtureCount = getEplFixtures(next.gameweek).length;

  const { data: comps } = await supabase.from('tipping_comps').select('id,name');
  const results: Array<Record<string, unknown>> = [];

  for (const comp of comps ?? []) {
    const [{ data: entries }, { data: tips }, { data: alreadySent }] = await Promise.all([
      supabase.from('tipping_entries').select('user_id,display_name').eq('comp_id', comp.id),
      supabase.from('tipping_tips').select('user_id').eq('comp_id', comp.id).eq('gameweek', next.gameweek),
      supabase.from('tipping_reminders').select('user_id')
        .eq('comp_id', comp.id).eq('gameweek', next.gameweek).eq('channel', 'email'),
    ]);

    const tipCount = new Map<string, number>();
    for (const tip of tips ?? []) tipCount.set(tip.user_id, (tipCount.get(tip.user_id) ?? 0) + 1);
    const sentTo = new Set((alreadySent ?? []).map(r => r.user_id));

    // Emails live in auth.users, which tipping_entries does not join to. Bot
    // entrants (baz-bot) are deliberately absent from auth and so are skipped.
    const { data: authUsers } = await supabase.auth.admin.listUsers({ page: 1, perPage: 1000 });
    const emailById = new Map((authUsers?.users ?? []).map(u => [u.id, u.email ?? '']));

    const missing: Missing[] = [];
    for (const entry of entries ?? []) {
      const tipped = tipCount.get(entry.user_id) ?? 0;
      if (tipped >= fixtureCount) continue;
      if (sentTo.has(entry.user_id)) continue;
      const email = emailById.get(entry.user_id);
      if (!email) continue;                       // bot or deleted account
      missing.push({ userId: entry.user_id, displayName: entry.display_name, email, tipped });
    }

    for (const person of missing) {
      const sent = dryRun
        ? { ok: true, id: 'dry-run' }
        : await sendReminder(person, next.gameweek, next.locksAt, fixtureCount);
      if (sent.ok && !dryRun) {
        await supabase.from('tipping_reminders').insert({
          comp_id: comp.id, user_id: person.userId, gameweek: next.gameweek,
          channel: 'email', provider_id: sent.id ?? null,
        });
      }
      results.push({
        comp: comp.name, display_name: person.displayName,
        tipped: `${person.tipped}/${fixtureCount}`, sent: sent.ok, error: sent.error ?? null,
      });
    }
  }

  return NextResponse.json({
    status: 'ok', dry_run: dryRun, gameweek: next.gameweek,
    locks_at: next.locksAt.toISOString(),
    hours_to_lock: Number(hoursToLock.toFixed(1)),
    reminded: results.length, results,
  });
}

async function sendReminder(
  person: Missing, gameweek: number, locksAt: Date, fixtureCount: number,
): Promise<{ ok: boolean; id?: string; error?: string }> {
  const apiKey = process.env.RESEND_API_KEY;
  const from = process.env.TIPPING_REMINDER_FROM ?? 'BetMate <tips@betmate.au>';
  if (!apiKey) return { ok: false, error: 'RESEND_API_KEY not configured' };

  const locks = locksAt.toLocaleString('en-GB', {
    weekday: 'long', day: 'numeric', month: 'long',
    hour: '2-digit', minute: '2-digit', timeZone: 'Europe/London',
  });
  const state = person.tipped === 0
    ? 'You have no tips in for this round.'
    : `You have ${person.tipped} of ${fixtureCount} tips in.`;

  const body = [
    `Hi ${person.displayName},`,
    '',
    `Gameweek ${gameweek} locks at the first kickoff — ${locks} UK time.`,
    '',
    state,
    '',
    'Anything missing at lock is defaulted to the away side, which is rarely what you want.',
    '',
    'https://betmate.au/tipping',
  ].join('\n');

  try {
    const resp = await fetch(RESEND_ENDPOINT, {
      method: 'POST',
      headers: { Authorization: `Bearer ${apiKey}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({
        from, to: [person.email],
        subject: `BetMate: GW${gameweek} tips lock ${locks}`,
        text: body,
      }),
    });
    if (!resp.ok) return { ok: false, error: `${resp.status} ${(await resp.text()).slice(0, 200)}` };
    const json = await resp.json();
    return { ok: true, id: json.id };
  } catch (error) {
    return { ok: false, error: String(error).slice(0, 200) };
  }
}
