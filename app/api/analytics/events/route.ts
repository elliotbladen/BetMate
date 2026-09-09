import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';
import { getAuthenticatedUser } from '@/lib/authServer';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const EVENT_NAMES = new Set([
  'page_view', 'page_exit', 'page_visibility_change', 'click', 'search_submitted',
  'filter_changed', 'market_selected', 'odds_card_expanded', 'baz_opened',
  'baz_question_submitted', 'baz_response_rendered', 'sign_in_started',
  'sign_in_completed', 'registration_started', 'registration_completed',
  'subscription_viewed', 'subscription_action',
]);
const DEVICE_CLASSES = new Set(['mobile', 'tablet', 'desktop']);
const CONSENT_STATES = new Set(['granted', 'denied', 'not_required']);
const requestWindows = new Map<string, { startedAt: number; count: number }>();
const RATE_LIMIT = 30;
const RATE_WINDOW_MS = 60_000;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

export function validAnalyticsEvent(event: unknown): event is Record<string, unknown> {
  if (!isRecord(event)) return false;
  if (typeof event.event_name !== 'string' || !EVENT_NAMES.has(event.event_name)) return false;
  if (typeof event.occurred_at_utc !== 'string' || typeof event.session_id !== 'string') return false;
  if (typeof event.route !== 'string' || event.route.length < 1 || event.route.length > 200) return false;
  if (typeof event.app_version !== 'string' || event.app_version.length < 1 || event.app_version.length > 80) return false;
  if (typeof event.consent_state !== 'string' || !CONSENT_STATES.has(event.consent_state)) return false;
  if (event.device_class !== undefined && event.device_class !== null &&
      (typeof event.device_class !== 'string' || !DEVICE_CLASSES.has(event.device_class))) return false;
  if (event.duration_seconds !== undefined && event.duration_seconds !== null &&
      (typeof event.duration_seconds !== 'number' || !Number.isInteger(event.duration_seconds) ||
       event.duration_seconds < 0 || event.duration_seconds > 86400)) return false;
  if (event.metadata !== undefined && !isRecord(event.metadata)) return false;
  return true;
}

function adminClient() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL?.trim();
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY?.trim();
  return url && key ? createClient(url, key, { auth: { persistSession: false } }) : null;
}

export async function POST(req: NextRequest) {
  const now = Date.now();
  const address = req.headers.get('x-forwarded-for')?.split(',')[0]?.trim() ||
    req.headers.get('x-real-ip') || 'unknown';
  const window = requestWindows.get(address);
  if (!window || now - window.startedAt >= RATE_WINDOW_MS) {
    requestWindows.set(address, { startedAt: now, count: 1 });
  } else {
    window.count += 1;
    if (window.count > RATE_LIMIT) return NextResponse.json({ error: 'rate limit exceeded' }, { status: 429 });
  }
  requestWindows.forEach((value, key) => {
    if (now - value.startedAt >= RATE_WINDOW_MS * 2) requestWindows.delete(key);
  });
  const contentLength = Number(req.headers.get('content-length') || 0);
  if (contentLength > 100_000) return NextResponse.json({ error: 'payload too large' }, { status: 413 });
  let body: unknown;
  try { body = await req.json(); } catch { return NextResponse.json({ error: 'invalid JSON' }, { status: 400 }); }
  const events = Array.isArray(body) ? body : [body];
  if (events.length < 1 || events.length > 20 || !events.every(validAnalyticsEvent)) {
    return NextResponse.json({ error: 'invalid analytics event' }, { status: 400 });
  }
  const consented = events.filter((event) => event.consent_state !== 'denied');
  if (consented.length === 0) return NextResponse.json({ accepted: 0 });
  const user = await getAuthenticatedUser();
  const client = adminClient();
  if (!client) return NextResponse.json({ error: 'analytics storage unavailable' }, { status: 503 });
  const rows = consented.map((event) => ({
    event_name: event.event_name, occurred_at_utc: event.occurred_at_utc,
    session_id: event.session_id, user_id: user?.id ?? null, route: event.route,
    source_component: typeof event.source_component === 'string' ? event.source_component.slice(0, 100) : null,
    metadata: event.metadata ?? {}, duration_seconds: event.duration_seconds ?? null,
    device_class: event.device_class ?? null, app_version: event.app_version,
    consent_state: event.consent_state,
  }));
  const { error } = await client.from('product_events').insert(rows);
  if (error) {
    console.error('[analytics/events]', error.message);
    return NextResponse.json({ error: 'analytics write failed' }, { status: 500 });
  }
  return NextResponse.json({ accepted: rows.length });
}
