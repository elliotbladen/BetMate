'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { ArrowUpRight, ChevronRight, Clock3, MapPin, Trophy } from 'lucide-react';

type State = 'NSW' | 'VIC';

const CARDS: Record<State, { meeting: string; venue: string; surface: string; rail: string; first: string; races: { number: number; time: string; name: string; distance: string; status?: string }[] }> = {
  NSW: {
    meeting: 'Sydney Saturday', venue: 'Royal Randwick', surface: 'Good 4', rail: 'True', first: '12:35 PM',
    races: [
      { number: 1, time: '12:35 PM', name: 'Maiden Plate', distance: '1400m' },
      { number: 2, time: '1:10 PM', name: 'Benchmark 72 Handicap', distance: '1200m' },
      { number: 3, time: '1:45 PM', name: 'Benchmark 78 Handicap', distance: '1600m' },
      { number: 4, time: '2:20 PM', name: 'Fillies & Mares BM78', distance: '1100m' },
      { number: 5, time: '2:55 PM', name: 'Highway Handicap', distance: '1500m' },
      { number: 6, time: '3:35 PM', name: 'Group 3 Feature', distance: '1400m', status: 'Feature' },
      { number: 7, time: '4:15 PM', name: 'Group 1 Feature', distance: '2000m', status: 'Feature' },
      { number: 8, time: '4:55 PM', name: 'Benchmark 88 Handicap', distance: '1300m' },
      { number: 9, time: '5:30 PM', name: 'Benchmark 78 Handicap', distance: '1800m' },
      { number: 10, time: '6:05 PM', name: 'Benchmark 72 Handicap', distance: '1200m' },
    ],
  },
  VIC: {
    meeting: 'Melbourne Saturday', venue: 'Caulfield', surface: 'Good 4', rail: 'True', first: '12:50 PM',
    races: [
      { number: 1, time: '12:50 PM', name: 'Maiden Plate', distance: '1100m' },
      { number: 2, time: '1:25 PM', name: 'Benchmark 70 Handicap', distance: '1400m' },
      { number: 3, time: '2:00 PM', name: 'Fillies & Mares BM70', distance: '1200m' },
      { number: 4, time: '2:35 PM', name: 'Benchmark 78 Handicap', distance: '1600m' },
      { number: 5, time: '3:10 PM', name: 'Listed Feature', distance: '1100m', status: 'Feature' },
      { number: 6, time: '3:50 PM', name: 'Group 3 Feature', distance: '1400m', status: 'Feature' },
      { number: 7, time: '4:30 PM', name: 'Group 1 Feature', distance: '2000m', status: 'Feature' },
      { number: 8, time: '5:10 PM', name: 'Benchmark 84 Handicap', distance: '1200m' },
      { number: 9, time: '5:45 PM', name: 'Benchmark 78 Handicap', distance: '1400m' },
      { number: 10, time: '6:20 PM', name: 'Benchmark 70 Handicap', distance: '1600m' },
    ],
  },
};

export default function RacingPage() {
  const [state, setState] = useState<State>('NSW');

  useEffect(() => {
    const requestedState = new URLSearchParams(window.location.search).get('state');
    if (requestedState === 'NSW' || requestedState === 'VIC') setState(requestedState);
  }, []);

  const card = CARDS[state];

  return (
    <div className="min-h-[calc(100dvh-60px)] bg-[#F0F2F5]">
      <div className="border-b border-[#1E2A35] bg-[#0B1014] text-white">
        <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 sm:py-10">
          <div className="flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <div className="mb-3 flex items-center gap-2 text-[10px] font-mono font-bold uppercase tracking-[0.2em] text-[#7DE9D4]"><Trophy className="h-3.5 w-3.5" /> BetMate Racing</div>
              <h1 className="font-display text-4xl font-extrabold tracking-tight sm:text-5xl">Saturday racing, made clear.</h1>
              <p className="mt-3 max-w-xl text-sm leading-6 text-[#A9B6C7]">NSW and Victorian thoroughbred meetings. Odds, form and BetMate pricing will appear here as the Racing Engine comes online.</p>
            </div>
            <div className="inline-flex rounded-md border border-[#283440] bg-[#111820] p-1">
              {(['NSW', 'VIC'] as State[]).map((item) => <button key={item} onClick={() => setState(item)} className={`min-w-24 rounded px-4 py-2.5 text-[11px] font-mono font-bold uppercase tracking-widest transition-colors ${state === item ? 'bg-[#00DEB8] text-[#06120F]' : 'text-[#7E8A9A] hover:text-white'}`}>{item === 'VIC' ? 'Victoria' : 'NSW'}</button>)}
            </div>
          </div>
        </div>
      </div>

      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 sm:py-8">
        <section className="overflow-hidden rounded-xl border border-[#DCE3EA] bg-white shadow-sm">
          <div className="flex flex-col gap-4 border-b border-[#E2E8F0] px-5 py-5 sm:flex-row sm:items-center sm:justify-between sm:px-6">
            <div className="flex items-start gap-3">
              <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-md bg-[#111827] text-[11px] font-mono font-bold tracking-wider text-[#00DEB8]">{state}</div>
              <div><p className="section-label">Saturday · card preview</p><h2 className="mt-1 text-xl font-bold tracking-tight text-[#111827]">{card.meeting}</h2><div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-[12px] text-[#718096]"><span className="inline-flex items-center gap-1"><MapPin className="h-3.5 w-3.5" />{card.venue}</span><span>{card.surface}</span><span>Rail {card.rail}</span></div></div>
            </div>
            <div className="flex items-center gap-2 rounded-md bg-[#F4F7F9] px-3 py-2 text-[11px] font-mono font-bold uppercase tracking-wider text-[#667085]"><Clock3 className="h-3.5 w-3.5 text-[#00A98E]" /> First race {card.first}</div>
          </div>

          <div className="grid divide-y divide-[#E8EDF2] sm:grid-cols-2 sm:divide-x sm:divide-y-0 lg:grid-cols-5">
            {card.races.map((race) => <Link href="#" onClick={(event) => event.preventDefault()} key={race.number} className="group flex min-h-[128px] flex-col justify-between p-5 transition-colors hover:bg-[#F7FFFC] sm:border-b sm:border-[#E8EDF2] lg:[&:nth-last-child(-n+5)]:border-b-0">
              <div className="flex items-start justify-between gap-3"><div className="flex h-8 min-w-8 items-center justify-center rounded bg-[#101820] text-[12px] font-mono font-bold text-white">R{race.number}</div><div className="flex items-center gap-1 text-[11px] font-mono text-[#8793A2]">{race.time}<ChevronRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" /></div></div>
              <div className="mt-4"><p className="text-sm font-bold leading-5 text-[#172033]">{race.name}</p><div className="mt-2 flex items-center justify-between"><span className="text-[11px] font-mono font-bold tracking-wide text-[#6E7B8C]">{race.distance}</span>{race.status ? <span className="rounded border border-[#00DEB8]/40 bg-[#E8FCF7] px-1.5 py-0.5 text-[9px] font-mono font-bold uppercase tracking-widest text-[#008D77]">{race.status}</span> : <span className="text-[10px] font-mono uppercase tracking-widest text-[#A4AFBC]">Coming soon</span>}</div></div>
            </Link>)}
          </div>
          <div className="flex flex-col gap-2 border-t border-[#E2E8F0] bg-[#F8FAFC] px-5 py-4 text-[11px] text-[#6B7280] sm:flex-row sm:items-center sm:justify-between sm:px-6"><span>Preview card only — fixtures, runners, prices and ratings are not connected yet.</span><span className="inline-flex items-center gap-1 font-mono font-bold uppercase tracking-wider text-[#008D77]">Racing Engine in build <ArrowUpRight className="h-3.5 w-3.5" /></span></div>
        </section>
      </main>
    </div>
  );
}
