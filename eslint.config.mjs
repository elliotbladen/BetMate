// Next 16 removed `next lint` and ships @next/eslint-plugin-next as native ESLint
// Flat Config, so `npm run lint` calls the ESLint CLI directly against this file.
//
// Import the flat config from eslint-config-next directly — do NOT route it
// through @eslint/eslintrc FlatCompat, which throws a circular-reference error
// on ESLint 10 ("property 'react' closes the circle").
//
// This project had no ESLint config at all before the Next 16 upgrade; `next lint`
// would have scaffolded one on first run.
import coreWebVitals from 'eslint-config-next/core-web-vitals';
import typescript from 'eslint-config-next/typescript';

export default [
  {
    ignores: [
      '.next/**',
      'node_modules/**',
      // Python engines and data dirs — not JS, and huge
      'BettingEngine/**',
      'RacingEngine/**',
      'data/**',
      'cloud/**',
      'scrapers/**',
    ],
  },
  ...coreWebVitals,
  ...typescript,
];
