'use client';

import { useState, useMemo } from 'react';
import { LEGACY_BETS, MODEL_BETS, AFL_MODEL_BETS } from '@/lib/researchData';
import type { Sport, BetResult, LegacyBet, ModelBet } from '@/lib/researchData';

function resultBadge(r: BetResult) {
  if (r === 'win')  return <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold uppercase tracking-widest bg-[#00DEB8]/15 text-[#00DEB8]">W</span>;
  if (r === 'loss') return <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold uppercase tracking-widest bg-red-500/15 text-red-500">L</span>;
  return <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold uppercase tracking-widest bg-[#E2E8F0] text-[#9CA3AF]">P</span>;
}

function sportPill(s: Sport) {
  const colors: Record<Sport, string> = {
    NRL:      'bg-[#00DEB8]/10 text-[#00DEB8]',
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

// -- All Bets tab --------------------------------------------------------------
function AllBetsTab() {
  const filtered = LEGACY_BETS;
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

      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-[#E2E8F0]">
              {['#', 'Date', 'Match', 'Market', 'Odds', 'CLV', 'Result', 'Cum P&L', 'Sport'].map(h => (
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
                <td className="py-2 pr-4">{clvCell(bet)}</td>
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
function ModelTab({ bets }: { bets: ModelBet[] }) {
  const stats = modelStatsFor(bets);

  const clvBets   = bets.filter(b => clvScore(b) !== null);
  const clvBeaten = clvBets.filter(b => (clvScore(b) ?? 0) > 0).length;
  const clvPct    = clvBets.length > 0 ? (clvBeaten / clvBets.length) * 100 : 0;

  return (
    <>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mb-5">
        {[
          { label: 'Bets',        value: stats.total.toString(),                                                          color: '' },
          { label: 'Win Rate',    value: `${stats.winRate.toFixed(1)}%`,                                                  color: '' },
          { label: 'Running P&L', value: `${stats.totalPL >= 0 ? '+' : ''}${stats.totalPL.toFixed(2)}u`,                 color: stats.totalPL >= 0 ? 'text-[#00DEB8]' : 'text-red-500' },
          { label: 'W / L',       value: `${stats.wins} / ${stats.losses}`,                                               color: '' },
          { label: 'Beat CLV',    value: clvBets.length > 0 ? `${clvPct.toFixed(0)}%` : 'N/A',                           color: '' },
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

      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-[#E2E8F0]">
              {['#', 'Date', 'Match', 'Market', 'Predicted', 'Taken', 'Close', 'CLV', 'Result', 'P&L', 'Running'].map(h => (
                <th key={h} className="pb-2 pr-4 text-[10px] font-mono text-[#9CA3AF] uppercase tracking-widest whitespace-nowrap">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {bets.map((bet: ModelBet) => (
              <tr key={bet.id} className="border-b border-[#E2E8F0] hover:bg-[#F8FAFC] transition-colors">
                <td className="py-2 pr-4 text-[11px] font-mono text-[#9CA3AF]">{bet.id}</td>
                <td className="py-2 pr-4 text-[11px] font-mono text-[#9CA3AF] whitespace-nowrap">{bet.date || '—'}</td>
                <td className="py-2 pr-4 text-[12px] font-mono text-[#111827] whitespace-nowrap max-w-[180px] truncate" title={bet.match}>{bet.match || '—'}</td>
                <td className="py-2 pr-4 text-[11px] font-mono text-[#6B7280] whitespace-nowrap">{bet.market || '—'}</td>
                <td className="py-2 pr-4 text-[11px] font-mono text-[#6B7280]">{bet.predictedLine ?? '—'}</td>
                <td className="py-2 pr-4 text-[12px] font-mono text-[#111827]">{bet.takenPrice?.toFixed(2) ?? '—'}</td>
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
  );
}

// -- Page ----------------------------------------------------------------------
const TABS = ['Sports Betting', 'NRL Model', 'AFL Model'] as const;
type Tab = typeof TABS[number];

export default function ResearchPage() {
  const [activeTab, setActiveTab] = useState<Tab>('Sports Betting');

  const allBets = useMemo(() => {
    const combined = [...LEGACY_BETS, ...MODEL_BETS];
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
        <div className="flex gap-1 border-b border-[#E2E8F0] mb-5">
          {TABS.map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={[
                'px-4 py-2 text-[12px] font-mono font-bold uppercase tracking-widest transition-colors border-b-2 -mb-px',
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
        {activeTab === 'NRL Model'      && <ModelTab bets={MODEL_BETS} />}
        {activeTab === 'AFL Model'      && <ModelTab bets={AFL_MODEL_BETS} />}

      </div>
    </div>
  );
}

