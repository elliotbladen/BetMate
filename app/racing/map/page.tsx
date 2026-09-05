import Link from 'next/link';
import card from '@/data/racing/chelmsford-map-2026.json';

type State = 'leader' | 'on_pace' | 'midfield' | 'backmarker';
const lanes: Array<{ key: State; label: string; subtitle: string }> = [
  { key: 'leader', label: 'Leader', subtitle: 'Controls the rail' },
  { key: 'on_pace', label: 'On pace', subtitle: 'Within 2–3 lengths' },
  { key: 'midfield', label: 'Midfield', subtitle: 'Covered behind speed' },
  { key: 'backmarker', label: 'Backmarker', subtitle: 'Settles in rear group' },
];

function pct(value: number) { return `${Math.round(value * 100)}%`; }

export default function RacingMapPage() {
  const runners = card.runners.map((runner) => {
    const entries = Object.entries(runner.probabilities) as Array<[State, number]>;
    const likely = entries.sort((a, b) => b[1] - a[1])[0];
    return { ...runner, likelyState: likely[0], likelyProbability: likely[1] };
  });

  return (
    <main className="min-h-screen bg-[#eef1f5] text-[#142033]">
      <header className="border-b border-white/10 bg-[#0b1118] text-white">
        <div className="mx-auto max-w-[1500px] px-4 py-6 sm:px-7">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <div className="mb-2 flex items-center gap-2 text-[10px] font-mono font-bold uppercase tracking-[.2em] text-[#6ee7cf]">
                <span className="h-2 w-2 rounded-full bg-[#f5a524]" /> Map Position · Shadow V1
              </div>
              <h1 className="text-3xl font-black tracking-tight sm:text-4xl">{card.raceName}</h1>
              <p className="mt-2 text-sm text-[#aeb9c7]">{card.meeting} · R{card.raceNumber} · {card.distance}m · {card.class} · {card.startTime}</p>
            </div>
            <div className="grid grid-cols-3 gap-px overflow-hidden rounded-lg border border-white/10 bg-white/10 text-center">
              <div className="bg-[#111a24] px-4 py-3"><div className="text-[9px] font-mono uppercase tracking-widest text-[#758395]">Going</div><div className="mt-1 text-sm font-bold">{card.trackCondition}</div></div>
              <div className="bg-[#111a24] px-4 py-3"><div className="text-[9px] font-mono uppercase tracking-widest text-[#758395]">Rail</div><div className="mt-1 text-sm font-bold">{card.rail}</div></div>
              <div className="bg-[#111a24] px-4 py-3"><div className="text-[9px] font-mono uppercase tracking-widest text-[#758395]">Weather</div><div className="mt-1 text-sm font-bold">{card.weather}</div></div>
            </div>
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-[1500px] px-4 py-5 sm:px-7">
        <div className="mb-4 flex flex-col gap-3 rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-amber-950 sm:flex-row sm:items-center sm:justify-between">
          <div><strong className="text-xs uppercase tracking-wide">Visual research only.</strong> <span className="text-xs">V1 failed its historical baseline, so this map is not used in prices or bets.</span></div>
          <div className="text-[10px] font-mono uppercase tracking-widest">Attica scratched · card refreshed 4 Sep</div>
        </div>

        <section className="overflow-hidden rounded-xl border border-[#cbd4df] bg-white shadow-sm">
          <div className="flex items-center justify-between border-b border-[#dce3eb] px-5 py-4">
            <div><p className="text-[10px] font-mono font-bold uppercase tracking-[.18em] text-[#7a8899]">Expected settling map</p><p className="mt-1 text-xs text-[#647386]">Position after the field establishes order. Cards show the most likely state, not certainty.</p></div>
            <div className="hidden text-right sm:block"><p className="text-[10px] font-mono uppercase tracking-widest text-[#8b98a7]">Simulation</p><p className="text-sm font-bold">10,000 starts</p></div>
          </div>

          <div className="grid min-w-[960px] grid-cols-4 gap-px overflow-x-auto bg-white">
            {lanes.map((lane, laneIndex) => {
              const laneRunners = runners.filter(r => r.likelyState === lane.key).sort((a,b) => a.expected_rank - b.expected_rank);
              return (
                <div key={lane.key} className="relative min-h-[590px] bg-[#e9edf3]">
                  <div className="absolute inset-0 opacity-50" style={{backgroundImage:'linear-gradient(to bottom, transparent 95%, white 95%), linear-gradient(to right, transparent 96%, white 96%)',backgroundSize:'100% 92px, 78px 100%'}} />
                  <div className="relative space-y-3 p-3" style={{paddingTop: `${34 + laneIndex * 42}px`}}>
                    {laneRunners.map((runner) => (
                      <article key={runner.runner_number} className={`relative overflow-hidden rounded-lg border bg-white shadow-sm ${runner.confidence < .4 ? 'border-amber-400' : 'border-[#cbd7e3]'}`}>
                        <div className="flex items-start gap-3 p-3">
                          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-md bg-[#12345b] font-mono text-lg font-black text-white">{runner.runner_number}</div>
                          <div className="min-w-0 flex-1"><div className="flex items-start justify-between gap-2"><h3 className="truncate text-sm font-extrabold">{runner.horse_name}</h3><span className="rounded bg-[#edf3f8] px-1.5 py-1 font-mono text-[9px] font-bold">B{runner.barrier}</span></div><p className="mt-0.5 truncate text-[10px] text-[#68778a]">{runner.jockey} · {runner.weight}kg</p><p className="mt-0.5 truncate text-[9px] text-[#8a97a6]">{runner.trainer}</p></div>
                        </div>
                        <div className="grid grid-cols-3 gap-px border-y border-[#e6ebf0] bg-[#e6ebf0] text-center">
                          <div className="bg-[#f8fafc] py-2"><div className="text-[8px] font-mono uppercase text-[#8a97a6]">Settle</div><div className="text-sm font-black">{runner.expected_rank.toFixed(1)}</div></div>
                          <div className="bg-[#f8fafc] py-2"><div className="text-[8px] font-mono uppercase text-[#8a97a6]">Map</div><div className="text-sm font-black text-[#008c76]">{pct(runner.likelyProbability)}</div></div>
                          <div className="bg-[#f8fafc] py-2"><div className="text-[8px] font-mono uppercase text-[#8a97a6]">Wide</div><div className={`text-sm font-black ${runner.wide_risk > .35 ? 'text-[#d94b3d]' : ''}`}>{pct(runner.wide_risk)}</div></div>
                        </div>
                        <div className="space-y-1.5 p-3">
                          {lanes.map(option => <div key={option.key} className="grid grid-cols-[55px_1fr_30px] items-center gap-2 text-[8px] font-mono uppercase text-[#7b8998]"><span>{option.label}</span><div className="h-1.5 overflow-hidden rounded-full bg-[#e8edf2]"><div className="h-full rounded-full bg-[#16b89b]" style={{width:pct(runner.probabilities[option.key])}} /></div><span className="text-right font-bold text-[#334155]">{pct(runner.probabilities[option.key])}</span></div>)}
                        </div>
                        {runner.confidence < .4 && <div className="border-t border-amber-200 bg-amber-50 px-3 py-2 text-[9px] font-bold uppercase tracking-wide text-amber-800">Low data · treat position as uncertain</div>}
                      </article>
                    ))}
                  </div>
                  <div className="absolute inset-x-0 bottom-0 border-t border-white bg-[#586985] px-4 py-4 text-white"><div className="text-base font-black">{lane.label}</div><div className="text-[9px] font-mono uppercase tracking-widest text-white/60">{lane.subtitle}</div></div>
                </div>
              );
            })}
          </div>
        </section>

        <footer className="mt-4 flex flex-col gap-3 rounded-lg border border-[#d6dee7] bg-white px-4 py-4 text-xs text-[#667588] sm:flex-row sm:items-center sm:justify-between">
          <span>Historical data depth varies by horse. The Euphrates is currently the low-data runner.</span>
          <Link href="/racing" className="font-mono text-[10px] font-bold uppercase tracking-widest text-[#008d77]">← Back to racing</Link>
        </footer>
      </div>
    </main>
  );
}
