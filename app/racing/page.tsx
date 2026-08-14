'use client';

import { useEffect, useState } from 'react';
import { ArrowUpRight, ChevronDown, Clock3, MapPin, Trophy } from 'lucide-react';

type State = 'NSW' | 'VIC';
type Runner = { number: number; name: string; jockey?: string | null; trainer?: string | null; barrier?: number | null; weight?: number | null; form?: string | null; scratched?: boolean };
type Race = { number: number; time: string; name: string; distance: string; status?: string; condition?: string; raceClass?: string; runners?: Runner[] };
type RaceCardProps = { race: Race; venue: string; isOpen: boolean; onToggle: () => void };
type LiveResponse = { meeting: { track: string; races: Array<{ raceNumber: number; raceName?: string; startTime?: string; distance?: string; condition?: string; raceClass?: string; runners?: Array<{ number: number; name: string; jockey?: string; trainer?: string; barrier?: number; weight?: number; form?: string; last10Starts?: string; scratched?: boolean; isScratched?: boolean }> }> } | null };

const CARDS: Record<State, { meeting: string; venue: string; surface: string; rail: string; first: string; races: Race[] }> = {
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

function RaceCard({ race, venue, isOpen, onToggle }: RaceCardProps) {
  return (
    <article className={`overflow-hidden rounded-lg border bg-white transition-colors ${isOpen ? 'border-[#00DEB8] shadow-[0_0_0_1px_rgba(0,222,184,0.12)]' : 'border-[#DCE3EA] hover:border-[#B7C5D4]'}`}>
      <button onClick={onToggle} className="flex w-full items-center gap-3 px-4 py-4 text-left sm:px-5">
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded bg-[#101820] text-[12px] font-mono font-bold text-white">R{race.number}</span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
            <span className="text-sm font-bold text-[#172033]">{race.name}</span>
            {race.status && <span className="rounded border border-[#00DEB8]/40 bg-[#E8FCF7] px-1.5 py-0.5 text-[9px] font-mono font-bold uppercase tracking-widest text-[#008D77]">{race.status}</span>}
          </div>
          <p className="mt-1 text-[11px] font-mono font-bold uppercase tracking-wide text-[#7A8796]">{race.distance} <span className="mx-1.5 text-[#CBD5E1]">·</span> {race.time}</p>
        </div>
        <span className="hidden rounded border border-[#E2E8F0] px-2.5 py-1 text-[10px] font-mono font-bold uppercase tracking-widest text-[#718096] sm:inline">{isOpen ? 'Close' : 'Open race'}</span>
        <ChevronDown className={`h-5 w-5 shrink-0 text-[#718096] transition-transform ${isOpen ? 'rotate-180 text-[#008D77]' : ''}`} />
      </button>

      {isOpen && (
        <div className="border-t border-[#DDE7EC] bg-[#F8FAFC] px-4 py-4 sm:px-5">
          {race.runners?.length ? (
            <div className="overflow-x-auto rounded-md border border-[#E1E8EE] bg-white">
              <table className="w-full min-w-[660px] text-left">
                <thead className="border-b border-[#E1E8EE] bg-[#F8FAFC] text-[10px] font-mono font-bold uppercase tracking-widest text-[#7A8796]"><tr><th className="px-3 py-2.5">#</th><th className="px-3 py-2.5">Runner</th><th className="px-3 py-2.5">Jockey</th><th className="px-3 py-2.5">Trainer</th><th className="px-3 py-2.5">Bar</th><th className="px-3 py-2.5">Wgt</th><th className="px-3 py-2.5">Form</th></tr></thead>
                <tbody>{race.runners.map((runner) => <tr key={runner.number} className={`border-b border-[#EEF2F6] last:border-0 ${runner.scratched ? 'opacity-40 line-through' : ''}`}><td className="px-3 py-2.5 font-mono text-xs text-[#718096]">{runner.number}</td><td className="px-3 py-2.5 text-sm font-bold text-[#172033]">{runner.name}{runner.scratched && <span className="ml-2 text-[9px] font-mono uppercase tracking-widest text-red-500">Scratched</span>}</td><td className="px-3 py-2.5 text-xs text-[#526174]">{runner.jockey || '—'}</td><td className="px-3 py-2.5 text-xs text-[#526174]">{runner.trainer || '—'}</td><td className="px-3 py-2.5 font-mono text-xs text-[#526174]">{runner.barrier ?? '—'}</td><td className="px-3 py-2.5 font-mono text-xs text-[#526174]">{runner.weight ?? '—'}</td><td className="px-3 py-2.5 font-mono text-xs text-[#526174]">{runner.form || '—'}</td></tr>)}</tbody>
              </table>
            </div>
          ) : (
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="rounded-md border border-[#E1E8EE] bg-white px-3 py-3"><p className="section-label">Race profile</p><p className="mt-1 text-sm font-bold text-[#1B2738]">{venue} · {race.distance}</p></div>
            <div className="rounded-md border border-[#E1E8EE] bg-white px-3 py-3"><p className="section-label">Market</p><p className="mt-1 text-sm font-bold text-[#7A8796]">Odds feed connecting</p></div>
            <div className="rounded-md border border-[#E1E8EE] bg-white px-3 py-3"><p className="section-label">BetMate price</p><p className="mt-1 text-sm font-bold text-[#7A8796]">Racing Engine in build</p></div>
          </div>
          )}
          <div className="mt-3 flex items-center justify-between rounded-md border border-dashed border-[#CBD5E1] bg-white px-3 py-3"><span className="text-[11px] text-[#718096]">Runners, odds, form and race intelligence will load here.</span><span className="text-[10px] font-mono font-bold uppercase tracking-widest text-[#008D77]">Preview</span></div>
        </div>
      )}
    </article>
  );
}

export default function RacingPage() {
  const [state, setState] = useState<State>('NSW');
  const [expandedRace, setExpandedRace] = useState<number | null>(null);
  const [liveMeeting, setLiveMeeting] = useState<{ track: string; races: Race[] } | null>(null);
  const [liveLoading, setLiveLoading] = useState(false);
  const [liveError, setLiveError] = useState<string | null>(null);

  const saturday = (() => {
    const now = new Date();
    const daysUntilSaturday = (6 - now.getDay() + 7) % 7;
    now.setDate(now.getDate() + daysUntilSaturday);
    return now.toISOString().slice(0, 10);
  })();

  useEffect(() => {
    const requestedState = new URLSearchParams(window.location.search).get('state');
    if (requestedState === 'NSW' || requestedState === 'VIC') setState(requestedState);
  }, []);

  useEffect(() => {
    let cancelled = false;
    setLiveMeeting(null);
    setLiveError(null);
    setLiveLoading(true);
    fetch(`/api/racing/card?state=${state}&date=${saturday}`, { cache: 'no-store' })
      .then(async (response) => {
        const data = await response.json().catch(() => null) as (LiveResponse & { error?: string }) | null;
        if (!response.ok) {
          throw new Error(data?.error || `Owner racecard request failed (${response.status}).`);
        }
        return data;
      })
      .then((data) => {
        if (cancelled || !data?.meeting) return;
        setLiveMeeting({
          track: data.meeting.track,
          races: data.meeting.races.map((race) => ({
            number: race.raceNumber,
            name: race.raceName || `Race ${race.raceNumber}`,
            time: race.startTime ? new Date(race.startTime).toLocaleTimeString('en-AU', { hour: 'numeric', minute: '2-digit', hour12: true, timeZone: 'Australia/Sydney' }).toUpperCase() : 'TBA',
            distance: race.distance || '—', condition: race.condition, raceClass: race.raceClass,
            runners: (race.runners ?? []).map((runner) => ({ ...runner, form: runner.form || runner.last10Starts, scratched: Boolean(runner.scratched || runner.isScratched) })),
          })),
        });
      })
      .catch((error: Error) => { if (!cancelled) setLiveError(error.message); })
      .finally(() => { if (!cancelled) setLiveLoading(false); });
    return () => { cancelled = true; };
  }, [state, saturday]);

  const placeholderCard = CARDS[state];
  const card = liveMeeting
    ? { ...placeholderCard, meeting: `${liveMeeting.track} Saturday`, venue: liveMeeting.track, surface: liveMeeting.races[0]?.condition || 'Condition TBC', rail: 'TBC', races: liveMeeting.races }
    : placeholderCard;

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
              {(['NSW', 'VIC'] as State[]).map((item) => <button key={item} onClick={() => { setState(item); setExpandedRace(null); }} className={`min-w-24 rounded px-4 py-2.5 text-[11px] font-mono font-bold uppercase tracking-widest transition-colors ${state === item ? 'bg-[#00DEB8] text-[#06120F]' : 'text-[#7E8A9A] hover:text-white'}`}>{item === 'VIC' ? 'Victoria' : 'NSW'}</button>)}
            </div>
          </div>
        </div>
      </div>

      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 sm:py-8">
        <section className="overflow-hidden rounded-xl border border-[#DCE3EA] bg-white shadow-sm">
          <div className="flex flex-col gap-4 border-b border-[#E2E8F0] px-5 py-5 sm:flex-row sm:items-center sm:justify-between sm:px-6">
            <div className="flex items-start gap-3">
              <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-md bg-[#111827] text-[11px] font-mono font-bold tracking-wider text-[#00DEB8]">{state}</div>
              <div><p className="section-label">Saturday · {liveMeeting ? 'owner live card' : 'card preview'}</p><h2 className="mt-1 text-xl font-bold tracking-tight text-[#111827]">{card.meeting}</h2><div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-[12px] text-[#718096]"><span className="inline-flex items-center gap-1"><MapPin className="h-3.5 w-3.5" />{card.venue}</span><span>{card.surface}</span><span>Rail {card.rail}</span></div></div>
            </div>
            <div className="flex items-center gap-2 rounded-md bg-[#F4F7F9] px-3 py-2 text-[11px] font-mono font-bold uppercase tracking-wider text-[#667085]"><Clock3 className="h-3.5 w-3.5 text-[#00A98E]" /> First race {card.first}</div>
          </div>

          <div className="space-y-3 bg-[#F0F2F5] p-3 sm:p-4">
            {liveLoading && <div className="px-2 py-1 text-[10px] font-mono font-bold uppercase tracking-widest text-[#008D77]">Loading owner racecard…</div>}
            {liveError && <div className="rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-[11px] text-amber-900">Owner card not loaded: {liveError}</div>}
            {card.races.map((race) => <RaceCard key={race.number} race={race} venue={card.venue} isOpen={expandedRace === race.number} onToggle={() => setExpandedRace((open) => open === race.number ? null : race.number)} />)}
          </div>
          <div className="flex flex-col gap-2 border-t border-[#E2E8F0] bg-[#F8FAFC] px-5 py-4 text-[11px] text-[#6B7280] sm:flex-row sm:items-center sm:justify-between sm:px-6"><span>Preview only — select a race to open its detail card. Live runners, pricing and odds are not connected yet.</span><span className="inline-flex items-center gap-1 font-mono font-bold uppercase tracking-wider text-[#008D77]">Racing Engine in build <ArrowUpRight className="h-3.5 w-3.5" /></span></div>
        </section>
      </main>
    </div>
  );
}
