import { createServerClient } from '@supabase/ssr';
import { NextRequest } from 'next/server';
import { isOwnerEmail } from '@/lib/owner';

// ── Rate limiting ─────────────────────────────────────────────────────────────
const rateLimits = new Map<string, { count: number; resetAt: number }>();
const RATE_LIMIT = 20;
const RATE_WINDOW_MS = 60 * 60 * 1000;

function checkRateLimit(userId: string): boolean {
  const now = Date.now();
  const record = rateLimits.get(userId);
  if (!record || now > record.resetAt) {
    rateLimits.set(userId, { count: 1, resetAt: now + RATE_WINDOW_MS });
    return true;
  }
  if (record.count >= RATE_LIMIT) return false;
  record.count++;
  return true;
}

function emailFromToken(token: string): string | null {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    return payload.email ?? null;
  } catch {
    return null;
  }
}

async function getRequestUserEmail(req: NextRequest): Promise<string | null> {
  const legacyToken = req.cookies.get('sb-access-token')?.value;
  const legacyEmail = legacyToken ? emailFromToken(legacyToken) : null;
  if (legacyEmail) return legacyEmail;

  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL?.trim();
  const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY?.trim();
  if (!supabaseUrl || !supabaseAnonKey) return null;

  const supabase = createServerClient(supabaseUrl, supabaseAnonKey, {
    cookies: {
      getAll() {
        return req.cookies.getAll();
      },
      setAll() {
        // API chat only needs to identify the current user for owner/rate-limit checks.
      },
    },
  });

  const {
    data: { user },
  } = await supabase.auth.getUser();
  return user?.email ?? null;
}

// ── Guard replies ────────────────────────────────────────────────────────────
const OFF_TOPIC_REPLY =
  "Mate, I'm only here for NRL and AFL. Ask me about a game, market, team, ref, injury or model read.";
const IP_GUARD_REPLY =
  "Can't give away the recipe, mate. I can explain the read, the risk factors, what changed, and what to avoid, but not the engine under the bonnet.";
const WEEKLY_SCOPE_REPLY =
  "Mate, hard no on that one. I only cover this week's AFL/NRL teams and games. Origin is fine if it just played or is inside the next week.";

const UNSUPPORTED_TOPIC_PATTERNS = [
  /\b(epl|premier league|soccer|football club|champions league|uefa|fifa)\b/i,
  /\b(nba|nfl|mlb|nhl|ufc|mma|boxing|tennis|cricket|bbl|ipl|f1|formula 1|golf)\b/i,
  /\b(racing|horse racing|greyhound|dogs|trots|harness racing)\b/i,
  /\b(crypto|bitcoin|ethereum|solana|token|coin|stocks?|shares?|forex)\b/i,
  /\b(politics|election|government|trump|biden|albanese|dutton)\b/i,
  /\b(code|coding|programming|javascript|typescript|python|react|next\.?js|supabase|vercel)\b/i,
  /\b(recipe|cook|cooking|movie|music|song|lyrics|travel|hotel|restaurant)\b/i,
];

const IP_DISCLOSURE_PATTERNS = [
  /\b(how|why)\s+(do|does|did|is|are|was|were)\s+(you|baz|betmate|the model|model|engine)\s+(calculate|work out|score|weight|rank|price|derive|build|make|decide)\b/i,
  /\b(formula|equation|algorithm|weights?|weighting|thresholds?|coefficients?|features?|feature list|model architecture)\b/i,
  /\b(scraper|scraping|data source|data sources|where do you get|where.*data|raw data|database|schema|pipeline|ETL)\b/i,
  /\b(source code|codebase|github|prompt|system prompt|instructions|jailbreak|developer message|tool output)\b/i,
  /\b(reverse engineer|replicate|copy your model|build the same|clone betmate|under the bonnet)\b/i,
  /\b(T1|T2|T3|T4|T5|T6|T7|T8|T9|tier\s*[1-9])\b/i,
];

function latestUserMessage(messages: { role: string; content: string }[]): string {
  return [...messages].reverse().find((m) => m.role === 'user')?.content ?? '';
}

function isClearlyOffTopic(messages: { role: string; content: string }[]): boolean {
  const latest = latestUserMessage(messages);
  if (!latest.trim()) return false;
  return UNSUPPORTED_TOPIC_PATTERNS.some((pattern) => pattern.test(latest));
}

function isAskingForIpDisclosure(messages: { role: string; content: string }[]): boolean {
  const latest = latestUserMessage(messages);
  if (!latest.trim()) return false;
  return IP_DISCLOSURE_PATTERNS.some((pattern) => pattern.test(latest));
}

function mentionsOrigin(text: string): boolean {
  return /\b(origin|state of origin|soo|blues|maroons|nsw|queensland|qld)\b/i.test(text);
}

function mentionsFutureOutsideWeek(text: string): boolean {
  return /\b(two|three|four|five|six|seven|eight|nine|ten|\d+)\s+weeks?\b/i.test(text) ||
    /\bfortnight\b/i.test(text) ||
    /\bnext\s+month\b/i.test(text) ||
    /\b(month|august|september|october|november|december|2027)\b/i.test(text);
}

function isClearlyFutureOriginQuestion(messages: { role: string; content: string }[]): boolean {
  const latest = latestUserMessage(messages);
  return mentionsOrigin(latest) && mentionsFutureOutsideWeek(latest);
}

// ── Private Baz worker ──────────────────────────────────────────────────────
// Member chat goes exclusively through the private Baz worker -> MCP server ->
// published feed pipeline. The old Anthropic cloud tool-use path (BAZ_TOOLS,
// bazFetch, executeTool, format helpers) was removed 2026-07-31.
// See git history for the prior implementation if needed.

async function privateBazReply(
  messages: { role: string; content: string }[],
  sport: string,
): Promise<string> {
  const workerUrl = process.env.BAZ_AGENT_URL?.trim();
  const workerToken = process.env.BAZ_AGENT_TOKEN?.trim();
  if (!workerUrl || !workerToken) {
    throw new Error('Private Baz worker is not configured');
  }

  const res = await fetch(`${workerUrl.replace(/\/$/, '')}/v1/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Baz-Agent-Token': workerToken,
    },
    body: JSON.stringify({ messages, sport }),
    cache: 'no-store',
    signal: AbortSignal.timeout(130_000),
  }).catch(() => null);
  if (!res?.ok) throw new Error('Private Baz worker is unavailable');
  const payload = await res.json() as { answer?: unknown };
  if (typeof payload.answer !== 'string' || !payload.answer.trim()) {
    throw new Error('Private Baz worker returned an invalid reply');
  }
  return payload.answer;
}

// ── Request handler ───────────────────────────────────────────────────────────
export async function POST(req: NextRequest) {
  const userEmail = await getRequestUserEmail(req);
  const ownerUser = isOwnerEmail(userEmail);
  const userId = userEmail ?? req.headers.get('x-forwarded-for') ?? 'anon';
  if (!ownerUser && !checkRateLimit(userId)) {
    return new Response(JSON.stringify({ error: 'Rate limit reached — try again in an hour' }), {
      status: 429,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  let body: { messages: { role: string; content: string }[]; sport?: string };
  try {
    body = await req.json();
  } catch {
    return new Response(JSON.stringify({ error: 'Invalid JSON' }), { status: 400 });
  }

  const { messages, sport = 'NRL' } = body;
  if (isAskingForIpDisclosure(messages)) {
    return new Response(IP_GUARD_REPLY, {
      headers: {
        'Content-Type': 'text/plain; charset=utf-8',
        'X-Baz-Brain': 'ip-guard',
      },
    });
  }

  if (isClearlyFutureOriginQuestion(messages)) {
    return new Response(WEEKLY_SCOPE_REPLY, {
      headers: {
        'Content-Type': 'text/plain; charset=utf-8',
        'X-Baz-Brain': 'weekly-scope-guard',
      },
    });
  }

  if (isClearlyOffTopic(messages)) {
    return new Response(OFF_TOPIC_REPLY, {
      headers: {
        'Content-Type': 'text/plain; charset=utf-8',
        'X-Baz-Brain': 'topic-guard',
      },
    });
  }

  // Member chat is local/private only. Never fall back to a cloud model: the
  // private worker talks to the member-safe MCP server and published feeds.
  try {
    const answer = await privateBazReply(messages, sport);
    return new Response(answer, {
      headers: {
        'Content-Type': 'text/plain; charset=utf-8',
        'X-Content-Type-Options': 'nosniff',
        'X-Baz-Brain': 'online',
      },
    });
  } catch {
    return new Response('Baz is temporarily unavailable. Please try again shortly.', {
      status: 503,
      headers: {
        'Content-Type': 'text/plain; charset=utf-8',
        'X-Baz-Brain': 'offline',
      },
    });
  }
}
