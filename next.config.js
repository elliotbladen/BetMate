const path = require('path');

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,

  // Turbopack (the default builder in Next 16) infers the workspace root from the
  // nearest lockfile. There is a stray package-lock.json in the HOME directory, so
  // it inferred ~/ as the root and tried to watch every file under it — the dev
  // server OOM'd at 8GB. Pin the root to this repo.
  turbopack: {
    root: __dirname,
  },

  // Vercel bundles every file a function might read. A route that reads
  // BettingEngine spreadsheets from disk made the tracer pull in the whole
  // engine: 2.49GB against a 250MB limit, and the deploy was REJECTED for days.
  // The build always succeeded, which is why this looked like a build problem
  // and was not - it failed at "Deploying outputs".
  //
  // The route that caused it (/api/ev-signals, backed by lib/matrixEV.ts) was
  // REMOVED 2026-09-14 when the NRL matrices feeding it were retired. These
  // exclusions stay as a repo-wide guard: any future route doing dynamic
  // filesystem access would reintroduce the same failure.
  //
  // Nothing here is needed at runtime on Vercel. data/ and the engine outputs are
  // gitignored so they never reach the deployment in the first place; these
  // patterns stop the tracer from reserving space for them regardless.
  outputFileTracingExcludes: {
    '*': [
      './BettingEngine/**',
      './RacingEngine/**',
      './ml/**',
      './data/**',
      './handover/**',
      './outputs/**',
      './**/*.xlsx',
      './**/*.csv',
      './**/*.parquet',
      './**/*.sqlite',
      './**/*.pkl',
      './**/*.db',
    ],
  },

  // Response headers applied to every route. Deliberately NOT including a
  // Content-Security-Policy yet: Next injects inline scripts, so a useful CSP
  // needs nonces wired through the app, and a wrong one breaks the site silently.
  // Everything here is safe to set today.
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          // Tell browsers to stay on HTTPS for two years, subdomains included.
          { key: 'Strict-Transport-Security', value: 'max-age=63072000; includeSubDomains; preload' },
          // Stop MIME sniffing turning a data file into executable script.
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          // No framing: the site has no embed use case, so clickjacking has none either.
          { key: 'X-Frame-Options', value: 'SAMEORIGIN' },
          // Send the origin cross-site, never the full path - odds URLs carry query state.
          { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
          // Nothing here needs these devices; deny them rather than leave them open.
          { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=(), payment=()' },
        ],
      },
    ];
  },

  images: {
    // images.domains was deprecated in Next 16 in favour of remotePatterns,
    // which is host- AND path-scoped rather than host-only.
    remotePatterns: [
      { protocol: 'https', hostname: 'www.google.com' },
    ],
  },
};

module.exports = nextConfig;
