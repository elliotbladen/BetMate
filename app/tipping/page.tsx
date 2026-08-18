'use client';

import { useState, useEffect, useCallback } from 'react';
import { createClient } from '@/lib/supabase';
import type { Fixture, TipSelection, LeaderboardRow, TippingComp } from '@/lib/tipping';
import { EPL_TEAMS } from '@/lib/soccerTeams';

// ─── Team badge helper ───────────────────────────────────────────────────────
function TeamBadge({ name, selected, onClick, label }: {
  name: string;
  selected: boolean;
  onClick: () => void;
  label: string;
}) {
  const meta = EPL_TEAMS[name];
  const bg = meta?.primary ?? '#6B7280';
  const fg = meta?.secondary ?? '#FFFFFF';
  const abbr = meta?.abbr ?? name.slice(0, 3).toUpperCase();

  return (
    <button
      onClick={onClick}
      className={`flex flex-col items-center gap-1 p-2 rounded-lg transition-all min-w-[72px] ${
        selected
          ? 'ring-2 ring-[#00DEB8] bg-[#00DEB8]/10 scale-105'
          : 'hover:bg-gray-100'
      }`}
    >
      <div
        className="w-10 h-10 rounded-full flex items-center justify-center text-xs font-bold shadow-sm"
        style={{ backgroundColor: bg, color: fg }}
      >
        {abbr}
      </div>
      <span className="text-[10px] text-gray-500 font-medium uppercase tracking-wide">{label}</span>
    </button>
  );
}

// ─── Fixture Card ────────────────────────────────────────────────────────────
function FixtureCard({ fixture, tip, onTip, locked }: {
  fixture: Fixture;
  tip: TipSelection | null;
  onTip: (sel: TipSelection) => void;
  locked: boolean;
}) {
  const kickoff = new Date(fixture.kickoff);
  const isFinished = fixture.status === 'finished';
  const timeStr = kickoff.toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short' })
    + ' ' + kickoff.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });

  return (
    <div className={`bg-white rounded-xl shadow-sm border p-4 ${isFinished ? 'opacity-75' : ''}`}>
      {/* Header */}
      <div className="flex justify-between items-center mb-3">
        <span className="text-[11px] text-gray-400 font-mono">{fixture.venue}</span>
        <span className="text-[11px] text-gray-400 font-mono">{timeStr}</span>
      </div>

      {/* Teams + Draw picker */}
      <div className="flex items-center justify-between gap-2">
        <TeamBadge
          name={fixture.home_team}
          selected={tip === 'home'}
          onClick={() => !locked && onTip('home')}
          label={fixture.home_team.split(' ').pop() ?? ''}
        />

        <button
          onClick={() => !locked && onTip('draw')}
          className={`flex flex-col items-center gap-1 p-2 rounded-lg transition-all min-w-[56px] ${
            tip === 'draw'
              ? 'ring-2 ring-[#00DEB8] bg-[#00DEB8]/10 scale-105'
              : 'hover:bg-gray-100'
          }`}
        >
          <div className="w-10 h-10 rounded-full bg-gray-200 flex items-center justify-center text-xs font-bold text-gray-600">
            X
          </div>
          <span className="text-[10px] text-gray-500 font-medium uppercase tracking-wide">Draw</span>
        </button>

        <TeamBadge
          name={fixture.away_team}
          selected={tip === 'away'}
          onClick={() => !locked && onTip('away')}
          label={fixture.away_team.split(' ').pop() ?? ''}
        />
      </div>

      {/* Score if finished */}
      {isFinished && fixture.home_score !== null && fixture.away_score !== null && (
        <div className="mt-3 text-center">
          <span className="font-mono font-bold text-lg">
            {fixture.home_score} — {fixture.away_score}
          </span>
        </div>
      )}

      {/* Lock indicator */}
      {locked && !isFinished && (
        <div className="mt-2 text-center text-[11px] text-amber-600 font-medium">
          Locked — kickoff passed
        </div>
      )}
    </div>
  );
}

// ─── Leaderboard ─────────────────────────────────────────────────────────────
function Leaderboard({ rows }: { rows: LeaderboardRow[] }) {
  if (rows.length === 0) {
    return (
      <div className="text-center text-gray-400 py-8 text-sm">
        No entries yet. Share the invite code to get started.
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-gray-50 text-gray-500 text-[11px] uppercase tracking-wider">
            <th className="px-4 py-2 text-left">#</th>
            <th className="px-4 py-2 text-left">Tipper</th>
            <th className="px-4 py-2 text-right">Pts</th>
            <th className="px-4 py-2 text-right">W/T</th>
            <th className="px-4 py-2 text-right">%</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={r.user_id} className={i === 0 ? 'bg-[#00DEB8]/5 font-semibold' : ''}>
              <td className="px-4 py-2 font-mono text-gray-400">{r.rank}</td>
              <td className="px-4 py-2">{r.display_name}</td>
              <td className="px-4 py-2 text-right font-mono font-bold">{r.total_points}</td>
              <td className="px-4 py-2 text-right font-mono text-gray-500">{r.correct}/{r.total_tips}</td>
              <td className="px-4 py-2 text-right font-mono text-gray-500">{r.strike_rate}%</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ─── Main Page ───────────────────────────────────────────────────────────────
export default function TippingPage() {
  const [tab, setTab] = useState<'tips' | 'leaderboard'>('tips');
  const [gameweek, setGameweek] = useState(1);
  const [fixtures, setFixtures] = useState<Fixture[]>([]);
  const [tips, setTips] = useState<Record<string, TipSelection>>({});
  const [leaderboard, setLeaderboard] = useState<LeaderboardRow[]>([]);
  const [comp, setComp] = useState<TippingComp | null>(null);
  const [userId, setUserId] = useState<string | null>(null);
  const [displayName, setDisplayName] = useState('');
  const [inviteCode, setInviteCode] = useState('');
  const [joined, setJoined] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Get auth state
  useEffect(() => {
    const supabase = createClient();
    supabase.auth.getSession().then(({ data }) => {
      if (data.session?.user) {
        setUserId(data.session.user.id);
        setDisplayName(data.session.user.email?.split('@')[0] ?? 'Anon');
      }
    });
  }, []);

  // Load fixtures
  useEffect(() => {
    fetch(`/api/tipping/fixtures?gameweek=${gameweek}`)
      .then(r => r.json())
      .then(d => setFixtures(d.fixtures ?? []))
      .catch(() => setFixtures([]));
  }, [gameweek]);

  // Load existing tips if joined
  const loadTips = useCallback(() => {
    if (!comp || !userId) return;
    fetch(`/api/tipping/tips?comp_id=${comp.id}&user_id=${userId}&gameweek=${gameweek}`)
      .then(r => r.json())
      .then(d => {
        const existing: Record<string, TipSelection> = {};
        for (const t of d.tips ?? []) {
          existing[t.game_id] = t.selection;
        }
        setTips(existing);
      })
      .catch(() => {});
  }, [comp, userId, gameweek]);

  useEffect(() => {
    if (joined) loadTips();
  }, [joined, loadTips]);

  // Load leaderboard
  useEffect(() => {
    if (!comp) return;
    fetch(`/api/tipping/leaderboard?comp_id=${comp.id}`)
      .then(r => r.json())
      .then(d => setLeaderboard(d.leaderboard ?? []))
      .catch(() => {});
  }, [comp, tab]);

  // Join comp
  const handleJoin = async () => {
    if (!inviteCode || !userId) {
      setError(userId ? 'Enter an invite code' : 'Please sign in first');
      return;
    }
    setError(null);
    try {
      const res = await fetch('/api/tipping/join', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          invite_code: inviteCode.toUpperCase(),
          user_id: userId,
          display_name: displayName,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.error ?? 'Failed to join');
        return;
      }
      setComp(data.comp);
      setJoined(true);
    } catch {
      setError('Network error');
    }
  };

  // Save tips
  const handleSave = async () => {
    if (!comp || !userId) return;
    setSaving(true);
    setSaved(false);

    const tipArray = Object.entries(tips).map(([game_id, selection]) => {
      const fix = fixtures.find(f => f.id === game_id);
      return {
        game_id,
        home_team: fix?.home_team ?? '',
        away_team: fix?.away_team ?? '',
        selection,
      };
    });

    try {
      const res = await fetch('/api/tipping/tips', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          comp_id: comp.id,
          user_id: userId,
          gameweek,
          tips: tipArray,
        }),
      });
      if (res.ok) {
        setSaved(true);
        setTimeout(() => setSaved(false), 3000);
      }
    } catch {
      setError('Failed to save tips');
    }
    setSaving(false);
  };

  const tippedCount = Object.keys(tips).length;
  const totalGames = fixtures.length;

  // ─── Not joined yet ──────────────────────────────────────────────────────
  if (!joined) {
    return (
      <div className="max-w-lg mx-auto px-4 py-12">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-gray-900 mb-2">EPL Tipping</h1>
          <p className="text-gray-500 text-sm">Join a comp with an invite code to start tipping.</p>
        </div>

        <div className="bg-white rounded-xl shadow-sm border p-6 space-y-4">
          {!userId && (
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-sm text-amber-700">
              Sign in first to join a tipping comp.
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Your Display Name</label>
            <input
              type="text"
              value={displayName}
              onChange={e => setDisplayName(e.target.value)}
              placeholder="e.g. Elliot"
              className="w-full px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-[#00DEB8] focus:border-transparent outline-none"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Invite Code</label>
            <input
              type="text"
              value={inviteCode}
              onChange={e => setInviteCode(e.target.value.toUpperCase())}
              placeholder="e.g. BETMATE26"
              className="w-full px-3 py-2 border rounded-lg text-sm font-mono uppercase tracking-wider focus:ring-2 focus:ring-[#00DEB8] focus:border-transparent outline-none"
            />
          </div>

          {error && (
            <div className="text-red-500 text-sm">{error}</div>
          )}

          <button
            onClick={handleJoin}
            disabled={!userId}
            className="w-full py-2.5 bg-[#00DEB8] text-white font-semibold rounded-lg hover:bg-[#00C9A7] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Join Comp
          </button>
        </div>

        {/* Preview fixtures below the join form */}
        <div className="mt-8">
          <h2 className="text-lg font-bold text-gray-900 mb-4">GW{gameweek} Fixtures</h2>
          <div className="grid gap-3">
            {fixtures.map(f => (
              <FixtureCard
                key={f.id}
                fixture={f}
                tip={null}
                onTip={() => {}}
                locked={true}
              />
            ))}
          </div>
        </div>
      </div>
    );
  }

  // ─── Joined — main tipping view ──────────────────────────────────────────
  return (
    <div className="max-w-2xl mx-auto px-4 py-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-xl font-bold text-gray-900">{comp?.name ?? 'EPL Tipping'}</h1>
          {comp?.prize_pool && (
            <p className="text-sm text-[#00DEB8] font-semibold">{comp.prize_pool}</p>
          )}
        </div>
        <div className="text-right text-sm text-gray-500">
          <div className="font-mono">{displayName}</div>
          <div className="text-[11px]">Code: {comp?.invite_code}</div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-100 rounded-lg p-1 mb-6">
        <button
          onClick={() => setTab('tips')}
          className={`flex-1 py-2 text-sm font-medium rounded-md transition-colors ${
            tab === 'tips' ? 'bg-white shadow-sm text-gray-900' : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          Tips
        </button>
        <button
          onClick={() => setTab('leaderboard')}
          className={`flex-1 py-2 text-sm font-medium rounded-md transition-colors ${
            tab === 'leaderboard' ? 'bg-white shadow-sm text-gray-900' : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          Leaderboard
        </button>
      </div>

      {tab === 'tips' ? (
        <>
          {/* Gameweek selector */}
          <div className="flex items-center justify-between mb-4">
            <button
              onClick={() => setGameweek(Math.max(1, gameweek - 1))}
              disabled={gameweek <= 1}
              className="px-3 py-1 text-sm border rounded-lg hover:bg-gray-50 disabled:opacity-30"
            >
              Prev
            </button>
            <span className="font-bold text-gray-900">Gameweek {gameweek}</span>
            <button
              onClick={() => setGameweek(gameweek + 1)}
              className="px-3 py-1 text-sm border rounded-lg hover:bg-gray-50"
            >
              Next
            </button>
          </div>

          {/* Progress */}
          <div className="flex items-center justify-between mb-4 text-sm text-gray-500">
            <span>{tippedCount}/{totalGames} tipped</span>
            <div className="flex-1 mx-4 h-1.5 bg-gray-200 rounded-full overflow-hidden">
              <div
                className="h-full bg-[#00DEB8] rounded-full transition-all"
                style={{ width: totalGames > 0 ? `${(tippedCount / totalGames) * 100}%` : '0%' }}
              />
            </div>
          </div>

          {/* Fixtures */}
          <div className="grid gap-3 mb-6">
            {fixtures.map(f => (
              <FixtureCard
                key={f.id}
                fixture={f}
                tip={tips[f.id] ?? null}
                onTip={(sel) => setTips(prev => ({ ...prev, [f.id]: sel }))}
                locked={!canTipFixture(f)}
              />
            ))}
            {fixtures.length === 0 && (
              <div className="text-center text-gray-400 py-12 text-sm">
                No fixtures loaded for GW{gameweek} yet.
              </div>
            )}
          </div>

          {/* Save button */}
          {tippedCount > 0 && (
            <button
              onClick={handleSave}
              disabled={saving}
              className={`w-full py-3 font-semibold rounded-xl transition-all ${
                saved
                  ? 'bg-[#00DEB8] text-white'
                  : 'bg-gray-900 text-white hover:bg-gray-800'
              } disabled:opacity-50`}
            >
              {saving ? 'Saving...' : saved ? 'Saved!' : `Save Tips (${tippedCount}/${totalGames})`}
            </button>
          )}
        </>
      ) : (
        <Leaderboard rows={leaderboard} />
      )}
    </div>
  );
}

function canTipFixture(fixture: Fixture): boolean {
  return new Date(fixture.kickoff) > new Date();
}
