'use client';

import { useEffect, useState, useCallback, useRef } from 'react';

// Heavy bias toward fire
const EMOJIS = ['\u{1F525}', '\u{1F525}', '\u{1F525}', '\u{1F525}', '\u{1F525}', '\u{2B50}', '\u{2728}'];

const TIERS = [
  { min: 10, title: 'UNSTOPPABLE!', icon: '\u{1F451}', count: 80, color: '#A855F7', glow: '#7C3AED' },
  { min: 7,  title: 'ON A HEATER!', icon: '\u{1F525}', count: 65, color: '#EF4444', glow: '#DC2626' },
  { min: 5,  title: 'ON FIRE!',     icon: '\u{1F525}', count: 50, color: '#F97316', glow: '#EA580C' },
];

interface Flame {
  id: number;
  emoji: string;
  x: number;       // % from left
  drift: number;   // horizontal drift in px
  rot: number;
  size: number;
  dur: number;
  del: number;
}

function makeFlames(n: number): Flame[] {
  return Array.from({ length: n }, (_, i) => ({
    id: i,
    emoji: EMOJIS[Math.floor(Math.random() * EMOJIS.length)],
    x: Math.random() * 100,
    drift: -40 + Math.random() * 80,
    rot: -30 + Math.random() * 60,
    size: 22 + Math.random() * 30,
    dur: 1.5 + Math.random() * 2.0,
    del: Math.random() * 1.8,
  }));
}

export default function StreakCelebration({
  streak,
  onDismiss,
}: {
  streak: number;
  onDismiss: () => void;
}) {
  const tier = TIERS.find(t => streak >= t.min);
  const [flames] = useState(() => makeFlames(tier?.count ?? 50));
  const [fading, setFading] = useState(false);
  const dismissed = useRef(false);

  const dismiss = useCallback(() => {
    if (dismissed.current) return;
    dismissed.current = true;
    setFading(true);
    setTimeout(onDismiss, 500);
  }, [onDismiss]);

  useEffect(() => {
    const id = setTimeout(dismiss, 4500);
    return () => clearTimeout(id);
  }, [dismiss]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') dismiss(); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [dismiss]);

  useEffect(() => {
    try { navigator.vibrate?.([80, 40, 80, 40, 160]); } catch { /* unsupported */ }
  }, []);

  if (!tier) return null;

  return (
    <div
      role="status"
      aria-label={`${streak} correct tips in a row`}
      className="fixed inset-0 z-50 pointer-events-none overflow-hidden"
      style={{ opacity: fading ? 0 : 1, transition: 'opacity 0.4s ease-out' }}
    >
      {/* Flames rising from bottom */}
      {flames.map(f => (
        <span
          key={f.id}
          className="absolute pointer-events-none"
          style={{
            left: `${f.x}%`,
            bottom: '-40px',
            fontSize: f.size,
            animation: `flame-rise ${f.dur}s ease-out ${f.del}s both`,
            ['--flame-drift' as string]: `${f.drift}px`,
            ['--flame-rot' as string]: `${f.rot}deg`,
          }}
        >
          {f.emoji}
        </span>
      ))}

      {/* Central text badge — compact, doesn't block the page */}
      <div className="absolute inset-0 flex items-center justify-center">
        <div
          className="pointer-events-auto cursor-pointer rounded-2xl px-10 py-6 text-center"
          onClick={dismiss}
          style={{
            backgroundColor: 'rgba(0, 0, 0, 0.88)',
            border: `2px solid ${tier.color}`,
            boxShadow: `0 0 40px ${tier.glow}50, 0 0 80px ${tier.glow}25`,
            animation: 'streak-pop 0.6s cubic-bezier(0.34,1.56,0.64,1) forwards',
          }}
        >
          <div
            className="text-6xl mb-2"
            style={{ animation: 'streak-pulse 1.2s ease-in-out infinite' }}
          >
            {tier.icon}
          </div>
          <h2
            className="text-4xl font-black tracking-tight mb-1"
            style={{
              color: tier.color,
              textShadow: `0 0 20px ${tier.glow}, 0 0 40px ${tier.glow}80`,
            }}
          >
            {tier.title}
          </h2>
          <p className="text-white/90 text-lg font-bold">{streak} in a row!</p>
        </div>
      </div>

      <style>{`
        @keyframes flame-rise {
          0% {
            transform: translateY(0) translateX(0) scale(1) rotate(0deg);
            opacity: 0;
          }
          8% {
            opacity: 1;
          }
          60% {
            opacity: 0.7;
          }
          100% {
            transform: translateY(-110vh) translateX(var(--flame-drift)) scale(0.15) rotate(var(--flame-rot));
            opacity: 0;
          }
        }
        @keyframes streak-pop {
          0%   { transform: scale(0.3); opacity: 0; }
          60%  { transform: scale(1.1); opacity: 1; }
          100% { transform: scale(1); opacity: 1; }
        }
        @keyframes streak-pulse {
          0%, 100% { transform: scale(1); }
          50%      { transform: scale(1.2); }
        }
        @media (prefers-reduced-motion: reduce) {
          [role="status"] * { animation-duration: 0.01s !important; }
        }
      `}</style>
    </div>
  );
}
