import { createServerClient } from '@supabase/ssr';
import { NextRequest, NextResponse } from 'next/server';

// Routes that don't require a logged-in session
const PUBLIC_PATHS = [
  '/',
  '/baz-concept',
  '/mobile-concept',
  '/odds',
  '/racing',
  '/odds-concept',
  '/odds-detail-concept',
  '/research',
  '/tools',
  '/auth/login',
  '/auth/register',
  '/auth/callback',
  '/api/odds',
  '/api/odds/movements',
  '/api/weather',
  '/api/ev-signals',
  '/api/team-news',
  '/api/odds/fixture',
  '/api/referees/nrl',
  '/api/chat',
  '/api/form',
  '/api/odds/nrl',
  '/api/odds/afl',
  '/api/odds/opening',
  '/api/nrl-predictions',
  '/api/afl-predictions',
  '/api/odds/epl',
  '/api/epl-predictions',
  '/api/championship-predictions',
  '/api/racing',
  '/tipping',
];

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Supabase PKCE stores its verifier in a host-scoped cookie. Starting OAuth on
  // www.betmate.au and returning to betmate.au loses that cookie, so canonicalise
  // the host before any auth page is rendered.
  if (request.nextUrl.hostname === 'www.betmate.au') {
    const canonicalUrl = request.nextUrl.clone();
    canonicalUrl.protocol = 'https:';
    canonicalUrl.hostname = 'betmate.au';
    canonicalUrl.port = '';
    return NextResponse.redirect(canonicalUrl, 308);
  }

  // Geo cookie — Vercel injects x-vercel-ip-country on every request
  const country = request.headers.get('x-vercel-ip-country') ?? '';

  // Always allow public auth routes
  if (PUBLIC_PATHS.some(p => pathname === p || pathname.startsWith(`${p}/`))) {
    const res = NextResponse.next();
    if (country) res.cookies.set('betmate-country', country, { path: '/', maxAge: 86400 });
    return res;
  }

  const response = NextResponse.next({
    request: { headers: request.headers },
  });

  if (country) response.cookies.set('betmate-country', country, { path: '/', maxAge: 86400 });

  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL?.trim();
  const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY?.trim();
  if (!supabaseUrl || !supabaseAnonKey) {
    return response;
  }

  const supabase = createServerClient(
    supabaseUrl,
    supabaseAnonKey,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll();
        },
        setAll(cookiesToSet: { name: string; value: string; options?: object }[]) {
          cookiesToSet.forEach(({ name, value, options }) => {
            response.cookies.set(name, value, options);
          });
        },
      },
    }
  );

  const { data: { user } } = await supabase.auth.getUser();

  // No session — API routes return 401, pages redirect to login
  if (!user) {
    if (pathname.startsWith('/api/')) {
      return NextResponse.json({ error: 'Unauthorised' }, { status: 401 });
    }
    const loginUrl = new URL('/auth/login', request.url);
    loginUrl.searchParams.set('next', pathname);
    return NextResponse.redirect(loginUrl);
  }

  return response;
}

export const config = {
  // Run on all routes except Next.js internals and static files
  matcher: ['/((?!_next/static|_next/image|favicon.ico|robots\\.txt|sitemap\\.xml|.*\\.png$).*)'],
};
