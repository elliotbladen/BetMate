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

  images: {
    // images.domains was deprecated in Next 16 in favour of remotePatterns,
    // which is host- AND path-scoped rather than host-only.
    remotePatterns: [
      { protocol: 'https', hostname: 'www.google.com' },
    ],
  },
};

module.exports = nextConfig;
