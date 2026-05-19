import Link from 'next/link';
import { ArrowRight, BarChart3, ShieldCheck } from 'lucide-react';
import LiveOddsPreview from '@/components/home/LiveOddsPreview';

export default function Home() {
  return (
    <div className="bg-[#F0F2F5]">
      <section className="border-b border-[#E2E8F0] bg-[#0B1014] text-white min-h-[calc(100dvh-60px)] flex items-center">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-12 lg:py-16 w-full">
          <div className="grid lg:grid-cols-[0.9fr_1.1fr] gap-8 lg:gap-12 items-center">
            <div>
              <div className="inline-flex items-center gap-2 rounded border border-[#00DEB8]/40 bg-[#00DEB8]/12 px-3 py-1.5 mb-6">
                <span className="w-1.5 h-1.5 rounded-full bg-[#00DEB8] pulse-dot" />
                <span className="text-[10px] font-mono font-bold uppercase tracking-widest text-[#A7F3D0]">
                  NRL · AFL · Live odds
                </span>
              </div>

              <h1 className="font-display text-[42px] sm:text-[58px] lg:text-[68px] leading-[0.92] font-extrabold tracking-tight text-white max-w-xl">
                Compare odds. Spot moves. Ask Baz.
              </h1>

              <p className="mt-6 text-[16px] sm:text-[18px] leading-7 text-[#CBD5E1] max-w-sm">
                The best-price comparison tool for Australian punters. Free to use.
              </p>

              <div className="mt-8">
                <Link
                  href="/odds"
                  className="inline-flex items-center justify-center gap-2 bg-[#00DEB8] hover:bg-[#00C9A6] text-black font-bold px-6 py-3.5 rounded-md transition-colors"
                >
                  Check today&apos;s odds
                  <ArrowRight className="w-4 h-4" />
                </Link>
              </div>
            </div>

            <LiveOddsPreview />
          </div>
        </div>
      </section>

      {/* Market intelligence ticker */}
      <div className="bg-[#0B1014] border-b border-[#1E2A35] overflow-hidden">
        <div className="ticker-track flex whitespace-nowrap py-2.5">
          {[
            'BULLDOGS shortening detected on H2H — best price gap is 9.2%. Ask Baz for the plain-English read before kickoff.',
            'STORM drifted +18% on handicap vs Tigers. Market turning hard. Cover rate on hammered teams: 28%.',
            'DOLPHINS H2H shortened from 2.40 → 1.95. Sharp money or public? Baz has the read.',
            'Best H2H gap right now: Sportsbet vs TAB on the Panthers — 6.4% edge available.',
            'RAIDERS opening price held. No significant move 48hrs out. Market neutral.',
            'BRONCOS drifted out 22% since Tuesday open. Check line movement before locking in.',
            'NRL R11 — 3 games with price gaps above 5%. Odds board updated.',
          ].concat([
            'BULLDOGS shortening detected on H2H — best price gap is 9.2%. Ask Baz for the plain-English read before kickoff.',
            'STORM drifted +18% on handicap vs Tigers. Market turning hard. Cover rate on hammered teams: 28%.',
            'DOLPHINS H2H shortened from 2.40 → 1.95. Sharp money or public? Baz has the read.',
            'Best H2H gap right now: Sportsbet vs TAB on the Panthers — 6.4% edge available.',
            'RAIDERS opening price held. No significant move 48hrs out. Market neutral.',
            'BRONCOS drifted out 22% since Tuesday open. Check line movement before locking in.',
            'NRL R11 — 3 games with price gaps above 5%. Odds board updated.',
          ]).map((msg, i) => (
            <span key={i} className="inline-flex items-center gap-3 px-6">
              <span className="w-1 h-1 rounded-full bg-[#00DEB8] shrink-0" />
              <span className="text-[11px] font-mono text-[#94A3B8] tracking-wide">{msg}</span>
            </span>
          ))}
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-5">
        <div className="border border-[#E2E8F0] rounded-lg bg-white px-5 py-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-md bg-[#111827] flex items-center justify-center shrink-0">
              <BarChart3 className="w-4 h-4 text-[#00DEB8]" />
            </div>
            <p className="text-sm text-[#6B7280]">
              Odds comparison, market movement, and AI context for NRL and AFL.
            </p>
          </div>
          <span className="inline-flex items-center gap-1.5 rounded border border-[#E2E8F0] px-3 py-1.5 text-[11px] font-mono uppercase tracking-widest text-[#6B7280] shrink-0">
            <ShieldCheck className="w-3.5 h-3.5" />
            Informational only. 18+
          </span>
        </div>
      </div>
    </div>
  );
}
