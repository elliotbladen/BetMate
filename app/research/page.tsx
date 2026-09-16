'use client';

import { useState, useMemo } from 'react';
import { LEGACY_BETS, MODEL_BETS, AFL_MODEL_BETS, FOOTBALL_MODEL_BETS, NFL_BETS } from '@/lib/researchData';
import type { Sport, BetResult, LegacyBet, ModelBet, Competition } from '@/lib/researchData';

// The latest screenshot ledger spans the NRL, football and NFL tabs. Keep a
// single landing view so newly recorded bets are visible without changing tabs.
const RECENT_BETS: ModelBet[] = [...MODEL_BETS.slice(-3), ...FOOTBALL_MODEL_BETS, ...NFL_BETS]
  .sort((a, b) => a.date.localeCompare(b.date) || a.id - b.id)
  .reduce<ModelBet[]>((rows, bet) => {
    const runningTotal = (rows.at(-1)?.runningTotal ?? 0) + bet.plUnits;
    rows.push({ ...bet, runningTotal: Number(runningTotal.toFixed(2)) });
    return rows;
  }, []);

const RECENT_BETS_AS_LEGACY: LegacyBet[] = RECENT_BETS.reduce<LegacyBet[]>((rows, bet, index) => {
  const previousPL = rows.at(-1)?.cumPL ?? LEGACY_BETS.at(-1)?.cumPL ?? 0;
  rows.push({
    id: LEGACY_BETS.length + index + 1,
    date: bet.date,
    match: bet.match,
    market: bet.market,
    odds: bet.takenPrice,
    closingOdds: bet.closingPrice,
    clv: bet.clv,
    clvLabel: bet.clvLabel,
    result: bet.result,
    cumPL: Number((previousPL + bet.plUnits).toFixed(2)),
    sport: bet.sport ?? (bet.competition ? 'FOOTBALL' : 'NRL'),
    notes: '',
  });
  return rows;
}, []);

const SPORTS_BETTING_BETS: LegacyBet[] = [...LEGACY_BETS, ...RECENT_BETS_AS_LEGACY];

function resultBadge(r: BetResult) {
  if (r === 'win')  return <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold uppercase tracking-widest bg-[#00DEB8]/15 text-[#00DEB8]">W</span>;
  if (r === 'loss') return <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold uppercase tracking-widest bg-red-500/15 text-red-500">L</span>;
  return <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold uppercase tracking-widest bg-[#E2E8F0] text-[#9CA3AF]">P</span>;
}

function sportPill(s: Sport) {
  const colors: Record<Sport, string> = {
    NRL:      'bg-[#00DEB8]/10 text-[#00DEB8]',
    NFL:      'bg-orange-500/10 text-orange-600',
    AFL:      'bg-blue-500/10 text-blue-500',
    FOOTBALL: 'bg-purple-500/10 text-purple-500',
    OTHER:    'bg-[#E2E8F0] text-[#9CA3AF]',
  };
  return (
    <span className={`px-1.5 py-0.5 rounded text-[10px] font-mono uppercase tracking-wider ${colors[s]}`}>
      {s}
    </span>
  );
}

function compPill(c: Competition) {
  const colors: Record<Competition, string> = {
    EPL: 'bg-purple-500/10 text-purple-500',
    EFL: 'bg-amber-500/10 text-amber-600',
    UCL: 'bg-blue-500/10 text-blue-500',
  };
  return (
    <span className={`px-1.5 py-0.5 rounded text-[10px] font-mono font-bold uppercase tracking-wider ${colors[c]}`}>
      {c}
    </span>
  );
}

function clvDelta(taken: number, closing: number | null) {
  if (!closing) return <span className="text-[#D1D5DB]">—</span>;
  const delta = ((taken - closing) / closing) * 100;
  const cls = delta > 0 ? 'text-[#00DEB8]' : delta < 0 ? 'text-red-500' : 'text-[#9CA3AF]';
  return <span className={`font-mono text-xs ${cls}`}>{delta > 0 ? '+' : ''}{delta.toFixed(1)}%</span>;
}

function clvCell(bet: { takenPrice?: number | null; closingPrice?: number | null; odds?: number | null; closingOdds?: number | null; clv?: number | null; clvLabel?: string }) {
  if (bet.clvLabel) {
    const value = bet.clv ?? 0;
    const cls = value > 0 ? 'text-[#00DEB8]' : value < 0 ? 'text-red-500' : 'text-[#9CA3AF]';
    return <span className={`font-mono text-xs ${cls}`}>{bet.clvLabel}</span>;
  }

  const taken = bet.takenPrice ?? bet.odds ?? null;
  const closing = bet.closingPrice ?? bet.closingOdds ?? null;
  if (taken === null) return <span className="text-[#D1D5DB]">—</span>;
  return clvDelta(taken, closing);
}

function clvScore(bet: ModelBet) {
  if (bet.clv !== undefined && bet.clv !== null) return bet.clv;
  if (bet.takenPrice === null || bet.closingPrice === null) return null;
  return ((bet.takenPrice - bet.closingPrice) / bet.closingPrice) * 100;
}

function statsFor(bets: LegacyBet[]) {
  const wins     = bets.filter(b => b.result === 'win').length;
  const losses   = bets.filter(b => b.result === 'loss').length;
  const total    = bets.length;
  const decisive = wins + losses;
  const winRate  = decisive > 0 ? (wins / decisive) * 100 : 0;
  return { total, wins, losses, decisive, winRate };
}

function modelStatsFor(bets: ModelBet[]) {
  const wins     = bets.filter(b => b.result === 'win').length;
  const losses   = bets.filter(b => b.result === 'loss').length;
  const total    = bets.length;
  const decisive = wins + losses;
  const winRate  = decisive > 0 ? (wins / decisive) * 100 : 0;
  const totalPL  = bets.reduce((sum, b) => sum + b.plUnits, 0);
  const roi      = decisive > 0 ? (totalPL / decisive) * 100 : 0;
  return { total, wins, losses, winRate, totalPL, roi };
}

// -- P&L Chart ----------------------------------------------------------------
function PLChart({ points, color = '#00DEB8' }: { points: number[]; color?: string }) {
  if (points.length < 2) return null;
  const W = 800, H = 200, PAD = 40, PADR = 16, PADT = 16, PADB = 28;
  const chartW = W - PAD - PADR, chartH = H - PADT - PADB;
  const minY = Math.min(0, ...points), maxY = Math.max(0, ...points);
  const range = maxY - minY || 1;
  const x = (i: number) => PAD + (i / (points.length - 1)) * chartW;
  const y = (v: number) => PADT + (1 - (v - minY) / range) * chartH;
  const line = points.map((v, i) => `${i === 0 ? 'M' : 'L'}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ');
  const zeroY = y(0);

  const ticks: number[] = [];
  const step = Math.ceil(range / 4);
  for (let t = Math.floor(minY); t <= Math.ceil(maxY); t += step) ticks.push(t);
  if (!ticks.includes(0)) ticks.push(0);
  ticks.sort((a, b) => a - b);

  const gradId = `plGrad-${color.replace('#', '')}`;
  const areaPath = `${line} L${x(points.length - 1).toFixed(1)},${y(minY).toFixed(1)} L${x(0).toFixed(1)},${y(minY).toFixed(1)} Z`;

  return (
    <div className="border border-[#E2E8F0] rounded-lg bg-white p-4 mb-5 overflow-x-auto">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ minWidth: 400 }}>
        <defs>
          <linearGradient id={gradId} x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity="0.15" />
            <stop offset="100%" stopColor={color} stopOpacity="0" />
          </linearGradient>
        </defs>
        {ticks.map(t => (
          <g key={t}>
            <line x1={PAD} x2={W - PADR} y1={y(t)} y2={y(t)} stroke={t === 0 ? '#9CA3AF' : '#F3F4F6'} strokeWidth={t === 0 ? 0.8 : 0.5} />
            <text x={PAD - 6} y={y(t) + 3} textAnchor="end" className="fill-[#9CA3AF]" style={{ fontSize: 9, fontFamily: 'monospace' }}>{t > 0 ? `+${t}` : t}</text>
          </g>
        ))}
        <path d={areaPath} fill={`url(#${gradId})`} />
        <path d={line} fill="none" stroke={color} strokeWidth="2" strokeLinejoin="round" />
        <circle cx={x(points.length - 1)} cy={y(points[points.length - 1])} r="3.5" fill={color} />
        <text x={PAD + chartW / 2} y={H - 4} textAnchor="middle" className="fill-[#9CA3AF]" style={{ fontSize: 9, fontFamily: 'monospace' }}>BET #</text>
      </svg>
    </div>
  );
}

// -- All Bets tab --------------------------------------------------------------
function AllBetsTab() {
  const filtered = SPORTS_BETTING_BETS;
  const stats  = statsFor(filtered);
  const finalPL = filtered.length > 0 ? filtered[filtered.length - 1].cumPL : 0;
  const roi     = stats.decisive > 0 ? (finalPL / stats.decisive) * 100 : 0;

  return (
    <>
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 mb-5">
        {[
          { label: 'Bets',     value: stats.total.toString(),                                          color: '' },
          { label: 'Win Rate', value: `${stats.winRate.toFixed(1)}%`,                                  color: '' },
          { label: 'Cum P&L',  value: `${finalPL >= 0 ? '+' : ''}${finalPL.toFixed(2)}u`,             color: finalPL >= 0 ? 'text-[#00DEB8]' : 'text-red-500' },
          { label: 'W / L',    value: `${stats.wins} / ${stats.losses}`,                               color: '' },
          { label: 'ROI',      value: `${roi >= 0 ? '+' : ''}${roi.toFixed(1)}%`,                     color: roi >= 0 ? 'text-[#00DEB8]' : 'text-red-500' },
        ].map(s => (
          <div key={s.label} className="border border-[#E2E8F0] rounded-lg px-4 py-3 bg-white">
            <p className="text-[10px] font-mono text-[#9CA3AF] uppercase tracking-widest mb-1">{s.label}</p>
            <p className={`text-[18px] font-mono font-bold leading-none ${s.color || 'text-[#111827]'}`}>{s.value}</p>
          </div>
        ))}
      </div>

      <PLChart points={filtered.map(b => b.cumPL)} />

      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-[#E2E8F0]">
              {['#', 'Date', 'Match', 'Market', 'Odds', 'Result', 'Cum P&L', 'Sport'].map(h => (
                <th key={h} className="pb-2 pr-4 text-[10px] font-mono text-[#9CA3AF] uppercase tracking-widest whitespace-nowrap">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filtered.map((bet: LegacyBet) => (
              <tr key={bet.id} className="border-b border-[#E2E8F0] hover:bg-[#F8FAFC] transition-colors">
                <td className="py-2 pr-4 text-[11px] font-mono text-[#9CA3AF]">{bet.id}</td>
                <td className="py-2 pr-4 text-[11px] font-mono text-[#9CA3AF] whitespace-nowrap">{bet.date ?? '—'}</td>
                <td className="py-2 pr-4 text-[12px] font-mono text-[#111827] whitespace-nowrap max-w-[180px] truncate">{bet.match}</td>
                <td className="py-2 pr-4 text-[11px] font-mono text-[#6B7280] whitespace-nowrap">{bet.market}</td>
                <td className="py-2 pr-4 text-[11px] font-mono text-[#6B7280]">{bet.odds ?? '—'}</td>
                <td className="py-2 pr-4">{resultBadge(bet.result)}</td>
                <td className={`py-2 pr-4 text-[12px] font-mono font-bold ${bet.cumPL >= 0 ? 'text-[#00DEB8]' : 'text-red-500'}`}>
                  {bet.cumPL > 0 ? '+' : ''}{bet.cumPL.toFixed(2)}u
                </td>
                <td className="py-2 pr-4">{sportPill(bet.sport)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

// -- Model tab (shared by NRL + AFL) ------------------------------------------
function ModelTab({ bets, byCompetition = false, showCash = false }: { bets: ModelBet[]; byCompetition?: boolean; showCash?: boolean }) {
  const [comp, setComp] = useState<'ALL' | Competition>('ALL');
  const filtered = byCompetition && comp !== 'ALL' ? bets.filter(b => b.competition === comp) : bets;
  const stats = modelStatsFor(filtered);

  const clvBets   = filtered.filter(b => { const s = clvScore(b); return s !== null && s !== 0; });
  const clvBeaten = clvBets.filter(b => (clvScore(b) ?? 0) > 0).length;
  const clvPct    = clvBets.length > 0 ? (clvBeaten / clvBets.length) * 100 : 0;
  // The count alone is misleading: AFL beat the close on 61% of bets and was still
  // NET NEGATIVE, because the 39% it lost were nearly twice the size of the 61% it
  // won (+3.97 pts per winner vs -7.17 per loser). Show the average beside it.
  const clvPts    = filtered.filter(b => b.clv !== undefined && b.clv !== null && b.clvLabel?.includes('pts'));
  const clvPtsAvg = clvPts.length > 0 ? clvPts.reduce((t, b) => t + (b.clv ?? 0), 0) / clvPts.length : null;

  return (
    <>
      {showCash && <p className="text-[12px] text-[#6B7280] mb-4">
        $25 = 1 unit · ${filtered.reduce((sum, bet) => sum + (bet.stake ?? 0), 0).toFixed(2)} staked
        {' · '}${filtered.reduce((sum, bet) => sum + (bet.returnAmount ?? 0), 0).toFixed(2)} returned
        {' · '}Net P&amp;L {stats.totalPL < 0 ? '−' : '+'}${Math.abs(stats.totalPL * 25).toFixed(2)}. Returns include stake.
      </p>}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3 mb-5">
        {[
          { label: 'Bets',        value: stats.total.toString(),                                                          color: '' },
          { label: 'Win Rate',    value: `${stats.winRate.toFixed(1)}%`,                                                  color: '' },
          { label: 'Running P&L', value: `${stats.totalPL >= 0 ? '+' : ''}${stats.totalPL.toFixed(2)}u`,                 color: stats.totalPL >= 0 ? 'text-[#00DEB8]' : 'text-red-500' },
          { label: 'W / L',       value: `${stats.wins} / ${stats.losses}`,                                               color: '' },
          { label: 'Beat CLV',    value: clvBets.length > 0 ? `${clvPct.toFixed(0)}%` : 'N/A',                           color: '' },
          { label: 'Avg CLV',     value: clvPtsAvg === null ? 'N/A' : `${clvPtsAvg > 0 ? '+' : ''}${clvPtsAvg.toFixed(2)} pts`,
            color: clvPtsAvg === null ? '' : clvPtsAvg > 0 ? 'text-[#00DEB8]' : clvPtsAvg < 0 ? 'text-red-500' : '' },
          { label: 'ROI',         value: `${stats.roi >= 0 ? '+' : ''}${stats.roi.toFixed(1)}%`,                         color: stats.roi >= 0 ? 'text-[#00DEB8]' : 'text-red-500' },
        ].map(s => (
          <div key={s.label} className="border border-[#E2E8F0] rounded-lg px-4 py-3 bg-white">
            <p className="text-[10px] font-mono text-[#9CA3AF] uppercase tracking-widest mb-1">{s.label}</p>
            <p className={`text-[18px] font-mono font-bold leading-none ${s.color || 'text-[#111827]'}`}>
              {s.value}
            </p>
          </div>
        ))}
      </div>

      {byCompetition && (
        <div className="flex flex-wrap gap-2 mb-4">
          {(['ALL', 'EPL', 'EFL', 'UCL'] as const).map(c => {
            const n = c === 'ALL' ? bets.length : bets.filter(b => b.competition === c).length;
            return (
              <button
                key={c}
                onClick={() => setComp(c)}
                className={`px-3 py-1.5 rounded-lg border text-[11px] font-mono uppercase tracking-widest transition-colors ${
                  comp === c
                    ? 'border-[#00DEB8] bg-[#00DEB8]/10 text-[#00DEB8]'
                    : 'border-[#E2E8F0] bg-white text-[#9CA3AF] hover:text-[#111827]'
                }`}
              >
                {c} <span className="opacity-60">{n}</span>
              </button>
            );
          })}
        </div>
      )}

      {filtered.length === 0 ? (
        <div className="border border-[#E2E8F0] rounded-lg bg-white px-6 py-10 text-center mb-5">
          <p className="text-[13px] text-[#6B7280]">
            {bets.length === 0
              ? 'No bets placed yet this season.'
              : `No ${comp} bets placed yet this season.`}
          </p>
          <p className="text-[11px] text-[#9CA3AF] mt-1 font-mono">
            Tracking starts from zero — real placed bets only.
          </p>
        </div>
      ) : (
      <>
      <PLChart points={filtered.map(b => b.runningTotal)} />

      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-[#E2E8F0]">
              {(byCompetition
                ? ['#', 'Date', 'Comp', 'Match', 'Market', 'Taken', 'Close', 'CLV', 'Result', 'P&L', 'Running']
                : ['#', 'Date', 'Match', 'Market', 'Taken', ...(showCash ? ['Stake', 'Return'] : []), 'Close', 'CLV', 'Result', 'P&L', 'Running']).map(h => (
                <th key={h} className="pb-2 pr-4 text-[10px] font-mono text-[#9CA3AF] uppercase tracking-widest whitespace-nowrap">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filtered.map((bet: ModelBet) => (
              <tr key={bet.id} className="border-b border-[#E2E8F0] hover:bg-[#F8FAFC] transition-colors">
                <td className="py-2 pr-4 text-[11px] font-mono text-[#9CA3AF]">{bet.id}</td>
                <td className="py-2 pr-4 text-[11px] font-mono text-[#9CA3AF] whitespace-nowrap">{bet.date || '—'}</td>
                {byCompetition && (
                  <td className="py-2 pr-4">{bet.competition ? compPill(bet.competition) : '—'}</td>
                )}
                <td className="py-2 pr-4 text-[12px] font-mono text-[#111827] whitespace-nowrap max-w-[180px] truncate" title={bet.match}>{bet.match || '—'}</td>
                <td className="py-2 pr-4 text-[11px] font-mono text-[#6B7280] whitespace-nowrap">{bet.market || '—'}</td>
                <td className="py-2 pr-4 text-[12px] font-mono text-[#111827]">{bet.takenPrice?.toFixed(2) ?? '—'}</td>
                {showCash && <>
                  <td className="py-2 pr-4 text-[12px] font-mono">${bet.stake?.toFixed(2)}</td>
                  <td className="py-2 pr-4 text-[12px] font-mono">${bet.returnAmount?.toFixed(2)}</td>
                </>}
                <td className="py-2 pr-4 text-[12px] font-mono text-[#6B7280]">{bet.closingPrice?.toFixed(2) ?? '—'}</td>
                <td className="py-2 pr-4">{clvCell(bet)}</td>
                <td className="py-2 pr-4">{resultBadge(bet.result)}</td>
                <td className={`py-2 pr-4 text-[12px] font-mono font-bold ${bet.plUnits >= 0 ? 'text-[#00DEB8]' : 'text-red-500'}`}>
                  {bet.plUnits > 0 ? '+' : ''}{bet.plUnits.toFixed(2)}u
                </td>
                <td className={`py-2 pr-4 text-[12px] font-mono font-bold ${bet.runningTotal >= 0 ? 'text-[#00DEB8]' : 'text-red-500'}`}>
                  {bet.runningTotal > 0 ? '+' : ''}{bet.runningTotal.toFixed(2)}u
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      </>
      )}
    </>
  );
}

// -- Page ----------------------------------------------------------------------
const TABS = ['Sports Betting', 'NRL Model', 'AFL Model', 'Football Model', 'NFL'] as const;
type Tab = typeof TABS[number];

export default function ResearchPage() {
  const [activeTab, setActiveTab] = useState<Tab>('Sports Betting');

  const allBets = useMemo(() => {
    const combined = [...LEGACY_BETS, ...MODEL_BETS, ...NFL_BETS];
    const wins   = combined.filter(b => b.result === 'win').length;
    const losses = combined.filter(b => b.result === 'loss').length;
    const total  = combined.length;
    return { total, wins, losses, winRate: (wins + losses) > 0 ? (wins / (wins + losses)) * 100 : 0 };
  }, []);

  return (
    <div className="min-h-screen">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6">

        {/* Header */}
        <div className="mb-6">
          <p className="text-[11px] font-mono text-[#9CA3AF] uppercase tracking-[0.2em] mb-1">Research</p>
          <h1 className="text-2xl font-display font-bold text-[#111827]">Baz Results</h1>
          <p className="text-[13px] font-mono text-[#6B7280] mt-1">
            {allBets.total} bets · {allBets.winRate.toFixed(1)}% win rate · {allBets.wins}W / {allBets.losses}L
          </p>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 overflow-x-auto border-b border-[#E2E8F0] mb-5">
          {TABS.map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={[
                'shrink-0 whitespace-nowrap px-4 py-2 text-[12px] font-mono font-bold uppercase tracking-widest transition-colors border-b-2 -mb-px',
                activeTab === tab
                  ? 'text-[#111827] border-[#00DEB8]'
                  : 'text-[#9CA3AF] border-transparent hover:text-[#6B7280]',
              ].join(' ')}
            >
              {tab}
            </button>
          ))}
        </div>

        {activeTab === 'Sports Betting' && <AllBetsTab />}
        {activeTab === 'NFL' && <ModelTab bets={NFL_BETS} showCash />}
        {activeTab === 'NRL Model'      && <ModelTab bets={MODEL_BETS} />}
        {activeTab === 'AFL Model'      && <ModelTab bets={AFL_MODEL_BETS} />}
        {activeTab === 'Football Model' && <ModelTab bets={FOOTBALL_MODEL_BETS} byCompetition />}

      </div>
    </div>
  );
}
