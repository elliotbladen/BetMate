'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { createClient } from '@/lib/supabase';
import type { Fixture, TipSelection, LeaderboardRow, TippingComp } from '@/lib/tipping';
import { isGameweekLocked } from '@/lib/tipping';
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
function FixtureCard({ fixture, tip, tipResult, tipPoints, onTip, locked }: {
  fixture: Fixture;
  tip: TipSelection | null;
  tipResult: TipSelection | null;
  tipPoints: number | null;
  onTip: (sel: TipSelection) => void;
  locked: boolean;
}) {
  const kickoff = new Date(fixture.kickoff);
  const isFinished = fixture.status === 'finished' || tipResult !== null;
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

      {tipResult !== null && tipPoints !== null && (
        <div className={`mt-3 rounded-lg px-3 py-2 text-center text-sm font-semibold ${
          tipPoints > 0 ? 'bg-emerald-50 text-emerald-700' : 'bg-gray-100 text-gray-600'
        }`}>
          {tipPoints > 0 ? `Correct — +${tipPoints} points` : 'Incorrect — 0 points'}
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

// ─── User Picks Panel ────────────────────────────────────────────────────────
function UserPicksPanel({ userName, userId, compId, gameweek, fixtures, onClose }: {
  userName: string;
  userId: string;
  compId: string;
  gameweek: number;
  fixtures: Fixture[];
  onClose: () => void;
}) {
  const [picks, setPicks] = useState<Record<string, TipSelection>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`/api/tipping/tips?comp_id=${compId}&user_id=${userId}&gameweek=${gameweek}`)
      .then(r => r.json())
      .then(d => {
        const map: Record<string, TipSelection> = {};
        for (const t of d.tips ?? []) map[t.game_id] = t.selection;
        setPicks(map);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [compId, userId, gameweek]);

  return (
    <div className="bg-white rounded-xl shadow-sm border p-4 mb-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-bold text-gray-900">{userName}&apos;s Picks — GW{gameweek}</h3>
        <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-lg">✕</button>
      </div>
      {loading ? (
        <div className="text-center text-gray-400 text-sm py-4">Loading...</div>
      ) : (
        <div className="space-y-2">
          {fixtures.map(f => {
            const pick = picks[f.id];
            const homeMeta = EPL_TEAMS[f.home_team];
            const awayMeta = EPL_TEAMS[f.away_team];
            const homeAbbr = homeMeta?.abbr ?? f.home_team.slice(0, 3).toUpperCase();
            const awayAbbr = awayMeta?.abbr ?? f.away_team.slice(0, 3).toUpperCase();
            const label = pick === 'home' ? homeAbbr : pick === 'away' ? awayAbbr : pick === 'draw' ? 'DRAW' : '—';
            const bg = pick === 'home' ? (homeMeta?.primary ?? '#6B7280')
              : pick === 'away' ? (awayMeta?.primary ?? '#6B7280')
              : pick === 'draw' ? '#9CA3AF' : '#E5E7EB';
            const fg = pick === 'home' ? (homeMeta?.secondary ?? '#FFF')
              : pick === 'away' ? (awayMeta?.secondary ?? '#FFF')
              : '#FFF';

            return (
              <div key={f.id} className="flex items-center justify-between text-sm">
                <span className="text-gray-600 flex-1">{homeAbbr} vs {awayAbbr}</span>
                <span
                  className="px-2 py-0.5 rounded text-[11px] font-bold"
                  style={{ backgroundColor: bg, color: fg }}
                >
                  {label}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ─── Leaderboard ─────────────────────────────────────────────────────────────
function Leaderboard({ rows, compId, gameweek, fixtures, locked }: {
  rows: LeaderboardRow[];
  compId: string;
  gameweek: number;
  fixtures: Fixture[];
  locked: boolean;
}) {
  const [viewingUser, setViewingUser] = useState<{ id: string; name: string } | null>(null);

  if (rows.length === 0) {
    return (
      <div className="text-center text-gray-400 py-8 text-sm">
        No entries yet. Share the invite code to get started.
      </div>
    );
  }

  return (
    <>
      {viewingUser && (
        <UserPicksPanel
          userName={viewingUser.name}
          userId={viewingUser.id}
          compId={compId}
          gameweek={gameweek}
          fixtures={fixtures}
          onClose={() => setViewingUser(null)}
        />
      )}
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
                <td className="px-4 py-2">
                  {locked ? (
                    <button
                      onClick={() => setViewingUser({ id: r.user_id, name: r.display_name })}
                      className="text-[#00DEB8] hover:underline font-medium"
                    >
                      {r.display_name}
                    </button>
                  ) : (
                    r.display_name
                  )}
                </td>
                <td className="px-4 py-2 text-right font-mono font-bold">{r.total_points}</td>
                <td className="px-4 py-2 text-right font-mono text-gray-500">{r.correct}/{r.total_tips}</td>
                <td className="px-4 py-2 text-right font-mono text-gray-500">{r.strike_rate}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

// ─── Main Page ───────────────────────────────────────────────────────────────
export default function TippingPage() {
  const [tab, setTab] = useState<'tips' | 'leaderboard'>('tips');
  const [gameweek, setGameweek] = useState(1);
  const [fixtures, setFixtures] = useState<Fixture[]>([]);
  const [tips, setTips] = useState<Record<string, TipSelection>>({});
  const [tipGrades, setTipGrades] = useState<Record<string, { result: TipSelection | null; points: number | null }>>({});
  const [leaderboard, setLeaderboard] = useState<LeaderboardRow[]>([]);
  const [comp, setComp] = useState<TippingComp | null>(null);
  const [userId, setUserId] = useState<string | null>(null);
  const [displayName, setDisplayName] = useState('');
  const [inviteCode, setInviteCode] = useState('');
  const [joined, setJoined] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [authChecked, setAuthChecked] = useState(false);

  // Get auth state + check comp membership from database
  useEffect(() => {
    const supabase = createClient();
    supabase.auth.getSession().then(({ data }) => {
      if (data.session?.user) {
        const uid = data.session.user.id;
        const name = data.session.user.email?.split('@')[0] ?? 'Anon';
        setUserId(uid);
        setDisplayName(name);

        // Check database for existing membership (survives hard refresh / cache clear)
        fetch(`/api/tipping/join?user_id=${uid}`)
          .then(r => r.json())
          .then(d => {
            if (d.comp) {
              setComp(d.comp);
              if (d.display_name) setDisplayName(d.display_name);
              setJoined(true);
            }
          })
          .catch(() => {});
      }
    }).finally(() => setAuthChecked(true));

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      if (!session?.user) {
        setUserId(null);
        setComp(null);
        setJoined(false);
        setTips({});
        setLeaderboard([]);
        setAuthChecked(true);
      }
    });

    return () => subscription.unsubscribe();
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
        const grades: Record<string, { result: TipSelection | null; points: number | null }> = {};
        for (const t of d.tips ?? []) {
          existing[t.game_id] = t.selection;
          grades[t.game_id] = {
            result: t.result ?? null,
            points: t.result == null ? null : Number(t.points ?? 0),
          };
        }
        setTips(existing);
        setTipGrades(grades);
      })
      .catch(() => {});
  }, [comp, userId, gameweek]);

  useEffect(() => {
    if (joined) loadTips();
  }, [joined, loadTips]);

  // Load leaderboard
  useEffect(() => {
    if (!comp) return;
    fetch(`/api/tipping/leaderboard?comp_id=${comp.id}&gameweek=${gameweek}`)
      .then(r => r.json())
      .then(d => setLeaderboard(d.leaderboard ?? []))
      .catch(() => {});
  }, [comp, tab, gameweek]);

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
          display_name: displayName,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        if (res.status === 401) {
          setUserId(null);
          setComp(null);
          setJoined(false);
          setTips({});
          setLeaderboard([]);
          return;
        }
        setError(data.error ?? 'Failed to join');
        return;
      }
      setComp(data.comp);
      setJoined(true);
      localStorage.setItem('tipping_invite_code', inviteCode.toUpperCase());
      localStorage.setItem('tipping_display_name', displayName);
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
          gameweek,
          tips: tipArray,
        }),
      });
      if (res.ok) {
        setSaved(true);
        setTimeout(() => setSaved(false), 3000);
      } else {
        const data = await res.json().catch(() => ({}));
        setError(data.error ?? 'Failed to save tips');
      }
    } catch {
      setError('Failed to save tips');
    }
    setSaving(false);
  };

  const tippedCount = Object.keys(tips).length;
  const totalGames = fixtures.length;
  const gameweekLocked = isGameweekLocked(fixtures);

  if (!authChecked) {
    return (
      <div className="max-w-lg mx-auto px-4 py-16 text-center text-sm text-gray-500">
        Checking your account…
      </div>
    );
  }

  if (!userId) {
    return (
      <div className="max-w-lg mx-auto px-4 py-16">
        <div className="bg-white rounded-xl shadow-sm border p-8 text-center">
          <h1 className="text-2xl font-bold text-gray-900 mb-3">Sign in to play EPL Tipping</h1>
          <p className="text-gray-600 text-sm mb-6">
            You must be signed in or signed up before you can join and play in a tipping competition.
          </p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <Link
              href="/auth/login?next=/tipping"
              className="px-5 py-2.5 bg-[#00DEB8] text-black font-semibold rounded-lg hover:bg-[#00C9A7] transition-colors"
            >
              Sign in
            </Link>
            <Link
              href="/auth/register"
              className="px-5 py-2.5 border border-gray-300 text-gray-900 font-semibold rounded-lg hover:bg-gray-50 transition-colors"
            >
              Sign up
            </Link>
          </div>
        </div>
      </div>
    );
  }

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
                tipResult={null}
                tipPoints={null}
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

          {gameweekLocked && (
            <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-center text-sm font-medium text-amber-700">
              Tipping is locked — the first game of this round has started.
            </div>
          )}

          {/* Fixtures */}
          <div className="grid gap-3 mb-6">
            {fixtures.map(f => (
              <FixtureCard
                key={f.id}
                fixture={f}
                tip={tips[f.id] ?? null}
                tipResult={tipGrades[f.id]?.result ?? null}
                tipPoints={tipGrades[f.id]?.points ?? null}
                onTip={(sel) => setTips(prev => ({ ...prev, [f.id]: sel }))}
                locked={gameweekLocked}
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
              disabled={saving || gameweekLocked}
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
        <Leaderboard
          rows={leaderboard}
          compId={comp?.id ?? ''}
          gameweek={gameweek}
          fixtures={fixtures}
          locked={gameweekLocked}
        />
      )}
    </div>
  );
}
