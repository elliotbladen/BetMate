'use client';

import { Suspense, useEffect, useMemo, useRef, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import {
  AlertTriangle,
  ArrowDown,
  ArrowRight,
  BarChart3,
  Bot,
  ChevronDown,
  CloudRain,
  Flame,
  History,
  Info,

  LineChart,
  MessageCircle,

  ShieldAlert,
  Sparkles,
  Stethoscope,
  Trophy,
  Wind,
  X,
} from 'lucide-react';
import { createClient } from '@/lib/supabase';
import ChatPanel from '@/components/chat/ChatPanel';
import type { Game } from '@/components/odds/GameCard';
import type { OddsApiEvent } from '@/lib/oddsApi';
import { buildGameUrl } from '@/lib/affiliate';
import { BOOKMAKER_META, extractH2HOdds, extractSpreadsOdds, extractTotalsOdds } from '@/lib/oddsApi';
import { computeMovementsFromOpening } from '@/lib/oddsMovement';
import type { Movement, MovementMap, OpeningPriceMap } from '@/lib/oddsMovement';
import { buildRefMap, getRefForGame } from '@/lib/referees';
import { getAFLVenue } from '@/lib/aflVenues';
import { getTeamMeta } from '@/lib/teams';
import { getVenue, getVenueByName } from '@/lib/venues';
import { getSpecialRoundVenue } from '@/lib/specialRounds';

type Sport = 'NRL' | 'AFL';
type MarketTab = 'H2H' | 'Line' | 'Totals';
type BviTier = 'value' | 'neutral' | 'fade';
interface BviEntry { rank: number; score: number; tier: BviTier; fav_profit: number; und_profit: number; }
type BviMap = Record<string, BviEntry>;
interface HomeAwayValueEntry {
  rank: number;
  home_win_pct: number;
  away_win_pct: number;
  difference_pct: number;
  home_record?: { wins: number; games: number } | null;
  away_record?: { wins: number; games: number } | null;
}
type HomeAwayValueMap = Record<string, HomeAwayValueEntry>;
interface TeamNewsItem {
  type: 'injury' | 'suspension';
  player: string;
  detail: string;
  severity: 'high' | 'medium' | 'low';
}
interface TeamNewsEntry {
  status: 'alert' | 'monitor';
  items: TeamNewsItem[];
}
type TeamNewsMap = Record<string, TeamNewsEntry>;
type DetailTab = 'Intelligence' | 'Team News' | 'Weather / Ref' | 'History';

interface WeatherData {
  temperature: number;
  windSpeed: number;
  windGust: number;
  precipProbability: number;
  precipIntensity: number;
  dewPoint: number;
  humidity: number;
  condition: 'good' | 'average' | 'poor' | 'bad';
  flags: string[];
}

const SPORT_TABS: Sport[] = ['NRL', 'AFL'];
const MARKET_TABS: MarketTab[] = ['H2H', 'Line', 'Totals'];
const DETAIL_TABS: DetailTab[] = ['Intelligence', 'Team News', 'Weather / Ref', 'History'];

function makeTransform(sport: Sport) {
  return function transformEvents(events: OddsApiEvent[]): Game[] {
    return events.map((event) => {
      const odds = extractH2HOdds(event);
      const spreadsOdds = extractSpreadsOdds(event);
      const totalsOdds = extractTotalsOdds(event);
      const homeShort = event.home_team.split(' ').pop()!.toUpperCase();
      const awayShort = event.away_team.split(' ').pop()!.toUpperCase();

      const kickoff = new Date(event.commence_time);
      const kickoffTime = kickoff
        .toLocaleString('en-AU', {
          weekday: 'short',
          hour: '2-digit',
          minute: '2-digit',
          hour12: true,
          timeZone: 'Australia/Sydney',
        })
        .toUpperCase() + ' AEST';

      return {
        id: event.id,
        sport,
        round: `${sport} 2026`,
        homeTeam: event.home_team,
        homeShort,
        awayTeam: event.away_team,
        awayShort,
        kickoffTime,
        commenceTime: event.commence_time,
        odds,
        spreadsOdds,
        totalsOdds,
        referee: getRefForGame(event.home_team, sport)?.name,
        refereeBucket: getRefForGame(event.home_team, sport)?.bucket,
        lastUpdated: new Date().toISOString(),
      };
    });
  };
}

const transformNRL = makeTransform('NRL');
const transformAFL = makeTransform('AFL');

interface FixtureGame { home_team: string; away_team: string; venue: string; }
interface FixtureData { season: number | null; round: number | null; games: FixtureGame[]; }

// Apply actual venues to NRL games.
// Priority: special round override → fixture match → leave undefined (falls back to home team in card)
function applyNRLVenues(games: Game[], fixture: FixtureData): Game[] {
  const special = fixture.season && fixture.round
    ? getSpecialRoundVenue(fixture.season, fixture.round, 'NRL')
    : null;

  if (special) {
    return games.map((g) => ({ ...g, venue: special.venue }));
  }

  const fixtureMap = new Map<string, string>();
  for (const fg of fixture.games ?? []) {
    fixtureMap.set(`${fg.home_team}|${fg.away_team}`, fg.venue);
    fixtureMap.set(`${fg.away_team}|${fg.home_team}`, fg.venue);
  }

  return games.map((g) => {
    const venue = fixtureMap.get(`${g.homeTeam}|${g.awayTeam}`);
    return venue ? { ...g, venue } : g;
  });
}

async function fetchOpeningPrices(sport: Sport): Promise<OpeningPriceMap> {
  const response = await fetch(`/api/odds/opening?sport=${sport}`);
  if (!response.ok) return {};
  const data = await response.json();
  return data.openingPrices ?? {};
}

async function fetchSupabaseMovements(): Promise<MovementMap> {
  try {
    const res = await fetch('/api/odds/movements');
    if (!res.ok) return {};
    return await res.json();
  } catch {
    return {};
  }
}

function bookmakerEntries(game: Game, market: MarketTab) {
  if (market === 'H2H') {
    return Object.entries(game.odds).map(([key, value]) => ({
      key,
      home: { label: game.homeTeam, point: null as number | null, price: value.home, side: 'home' as const },
      away: { label: game.awayTeam, point: null as number | null, price: value.away, side: 'away' as const },
    }));
  }

  if (market === 'Line') {
    return Object.entries(game.spreadsOdds ?? {}).map(([key, value]) => ({
      key,
      home: { label: game.homeTeam, point: value.homePoint, price: value.home, side: 'home' as const },
      away: { label: game.awayTeam, point: value.awayPoint, price: value.away, side: 'away' as const },
    }));
  }

  return Object.entries(game.totalsOdds ?? {}).map(([key, value]) => ({
    key,
    home: { label: `Over ${value.point}`, point: value.point, price: value.over, side: 'over' as const },
    away: { label: `Under ${value.point}`, point: value.point, price: value.under, side: 'under' as const },
  }));
}

function movementKey(gameId: string, market: MarketTab, bookmaker: string, side: string) {
  if (market === 'H2H') return `${gameId}:h2h:${bookmaker}:${side}`;
  if (market === 'Line') return `${gameId}:spreads:${bookmaker}:${side}`;
  return `${gameId}:totals:${bookmaker}:${side}`;
}

function movementStats(game: Game, market: MarketTab, movements: MovementMap) {
  const entries = bookmakerEntries(game, market);
  let homeMax = 0;
  let awayMax = 0;
  let totalCount = 0;

  for (const entry of entries) {
    const homeMove = movements[movementKey(game.id, market, entry.key, entry.home.side)];
    const awayMove = movements[movementKey(game.id, market, entry.key, entry.away.side)];
    if (homeMove?.direction === 'down') { homeMax = Math.max(homeMax, Math.abs(homeMove.changePct)); totalCount++; }
    if (awayMove?.direction === 'down') { awayMax = Math.max(awayMax, Math.abs(awayMove.changePct)); totalCount++; }
  }

  const biggest = Math.max(homeMax, awayMax);
  const isMoving = biggest > 0;
  const isStrong = biggest >= 10;

  let label = 'Quiet';
  if (isMoving) {
    const leadingSide = homeMax >= awayMax ? 'home' : 'away';
    const sideName = market === 'Totals'
      ? (leadingSide === 'home' ? 'Over' : 'Under')
      : (leadingSide === 'home' ? game.homeShort : game.awayShort);
    label = isStrong ? `${sideName} hammered` : `${sideName} shortening`;
  }

  return {
    label,
    tone: isStrong ? 'hot' : isMoving ? 'warn' : 'neutral',
    biggest,
    count: totalCount,
  };
}

function netPrice(price: number, key: string): number {
  if (key === 'betfair_ex_au' && price > 1) return 1 + (price - 1) * 0.95;
  return price;
}

function sideGap(prices: number[]): number {
  const valid = prices.filter((p) => p > 0);
  if (valid.length < 2) return 0;
  const max = Math.max(...valid);
  const min = Math.min(...valid);
  return ((max - min) / min) * 100;
}

function bestGap(entries: ReturnType<typeof bookmakerEntries>) {
  const homePrices = entries.map((e) => netPrice(e.home.price, e.key));
  const awayPrices = entries.map((e) => netPrice(e.away.price, e.key));
  return Math.max(sideGap(homePrices), sideGap(awayPrices));
}

function commonPoint(points: Array<number | null>): number | null {
  const counts = new Map<number, number>();
  for (const point of points) {
    if (point == null) continue;
    counts.set(point, (counts.get(point) ?? 0) + 1);
  }

  let selected: number | null = null;
  let selectedCount = 0;
  for (const [point, count] of Array.from(counts.entries())) {
    if (count > selectedCount || (count === selectedCount && selected != null && Math.abs(point) < Math.abs(selected))) {
      selected = point;
      selectedCount = count;
    }
  }
  return selected;
}

function comparableBest(
  entries: ReturnType<typeof bookmakerEntries>,
  side: 'home' | 'away',
  lineAware: boolean,
) {
  if (!lineAware) {
    return {
      point: null as number | null,
      price: entries.length > 0 ? Math.max(...entries.map((entry) => entry[side].price)) : 0,
    };
  }

  const point = commonPoint(entries.map((entry) => entry[side].point));
  const comparable = point == null ? entries : entries.filter((entry) => entry[side].point === point);
  return {
    point,
    price: comparable.length > 0 ? Math.max(...comparable.map((entry) => entry[side].price)) : 0,
  };
}

function TotalSelectionLabel({ side, point }: { side: 'Over' | 'Under'; point: number | null }) {
  return (
    <div>
      <span className={[
        'inline-flex h-8 min-w-[54px] items-center justify-center rounded px-2 text-[10px] font-black uppercase tracking-wider shadow-sm',
        side === 'Over'
          ? 'bg-[#DCFCE7] text-[#166534] ring-1 ring-[#16A34A]/20'
          : 'bg-[#FEE2E2] text-[#991B1B] ring-1 ring-[#DC2626]/20',
      ].join(' ')}>
        {side}
      </span>
      <span className="mt-1 block text-[10px] font-mono font-bold text-[#6B7280]">
        {point != null ? point : 'Total'}
      </span>
    </div>
  );
}

function displayPrice(price: number, point: number | null, isTotal = false) {
  if (point == null) return price.toFixed(2);
  if (isTotal) return `${point}  ${price.toFixed(2)}`;
  return `${point > 0 ? '+' : ''}${point}  ${price.toFixed(2)}`;
}

function TeamBadge({ name, label }: { name: string; label?: string }) {
  const meta = getTeamMeta(name);
  if (!meta) return <span className="truncate">{label ?? name}</span>;

  return (
    <span className="inline-flex min-w-0 items-center gap-2">
      <span
        className="inline-flex h-8 w-11 shrink-0 items-center justify-center rounded text-[10px] font-black tracking-wide shadow-sm"
        style={{ backgroundColor: meta.primary, color: meta.secondary, border: `1px solid ${meta.secondary}33` }}
      >
        {meta.abbr}
      </span>
      <span className="truncate">{label ?? name}</span>
    </span>
  );
}

function BookLogo({ bmKey, homeTeam, awayTeam, sport }: { bmKey: string; homeTeam: string; awayTeam: string; sport: string }) {
  const meta = BOOKMAKER_META[bmKey] ?? { abbr: bmKey.slice(0, 3).toUpperCase(), name: bmKey, domain: bmKey, color: '' };
  const href = buildGameUrl(bmKey, sport as 'NRL' | 'AFL', homeTeam, awayTeam);
  const inner = (
    <div className="flex flex-col items-center justify-center gap-1">
      <span className="flex h-8 w-8 items-center justify-center rounded-md bg-white shadow-sm ring-1 ring-black/5">
        <img
          src={`https://www.google.com/s2/favicons?domain=${meta.domain}&sz=64`}
          alt={meta.name}
          className="h-5 w-5 rounded-sm"
        />
      </span>
      <span className="text-[9px] font-mono font-black uppercase tracking-wide text-[#6B7280]">{meta.abbr}</span>
    </div>
  );
  return href ? (
    <a href={href} target="_blank" rel="noopener noreferrer" className="block hover:opacity-80 transition-opacity" title={`Bet at ${meta.name}`}>{inner}</a>
  ) : inner;
}

function Chip({
  icon: Icon,
  label,
  value,
  tone = 'neutral',
  tooltip,
}: {
  icon: React.ElementType;
  label: string;
  value: string;
  tone?: 'neutral' | 'hot' | 'good' | 'warn';
  tooltip?: string;
}) {
  const styles = {
    neutral: 'border-[#E2E8F0] bg-white text-[#4B5563]',
    hot: 'border-[#F97316]/30 bg-[#FFF7ED] text-[#EA580C]',
    good: 'border-[#00DEB8]/35 bg-[#00DEB8]/10 text-[#00866F]',
    warn: 'border-amber-400/35 bg-amber-50 text-amber-700',
  };

  return (
    <span className={`relative inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1.5 text-[11px] font-mono font-bold uppercase tracking-wide ${styles[tone]}`}>
      <Icon className="h-3.5 w-3.5" />
      {label}: {value}
      {tooltip && (
        <span className="group relative ml-0.5 cursor-default">
          <span className="flex h-3.5 w-3.5 items-center justify-center rounded-full border border-current text-[8px] opacity-50 group-hover:opacity-100">i</span>
          <span className="pointer-events-none absolute bottom-full left-1/2 z-50 mb-2 w-52 -translate-x-1/2 rounded-md bg-[#111827] px-3 py-2 text-[10px] font-normal normal-case leading-relaxed tracking-normal text-white opacity-0 shadow-lg transition-opacity group-hover:opacity-100">
            {tooltip}
            <span className="absolute left-1/2 top-full -translate-x-1/2 border-4 border-transparent border-t-[#111827]" />
          </span>
        </span>
      )}
    </span>
  );
}

function PriceCell({
  price,
  point,
  isBest,
  movement,
  isTotal = false,
}: {
  price: number;
  point: number | null;
  isBest: boolean;
  movement?: Movement;
  isTotal?: boolean;
}) {
  return (
    <div
      className={[
        'relative flex min-h-[50px] items-center justify-center border-t border-r border-[#E2E8F0] px-2 py-2 font-mono tabular-nums transition-colors last:border-r-0',
        isBest ? 'bg-[#00DEB8]/16 text-[#00866F] shadow-[inset_0_0_0_1px_rgba(0,222,184,0.35)]' : 'bg-white text-[#111827] hover:bg-[#F8FAFC]',
      ].join(' ')}
    >
      {movement && (
        <span className={`absolute right-1 top-1 ${movement.direction === 'down' ? 'text-[#F97316]' : 'text-[#00B899]'}`}>
          <ArrowDown className={`h-3.5 w-3.5 ${movement.direction === 'up' ? 'rotate-180' : ''}`} />
        </span>
      )}
      {isTotal && point != null ? (
        <span className={['flex flex-col items-center leading-tight', isBest ? 'rounded bg-white/75 px-2 py-1 shadow-sm' : ''].join(' ')}>
          <span className="text-[10px] font-bold text-[#9CA3AF]">{point}</span>
          <span className="text-sm font-bold">{price.toFixed(2)}</span>
        </span>
      ) : (
        <span className={['text-sm font-bold', isBest ? 'rounded bg-white/75 px-2 py-1 shadow-sm' : ''].join(' ')}>
          {displayPrice(price, point, isTotal)}
        </span>
      )}
    </div>
  );
}

function MobilePriceTile({
  bmKey, price, point, isBest, movement, isTotal = false, homeTeam, awayTeam, sport,
}: {
  bmKey: string; price: number; point: number | null; isBest: boolean; movement?: Movement; isTotal?: boolean; homeTeam: string; awayTeam: string; sport: string;
}) {
  const meta = BOOKMAKER_META[bmKey] ?? { abbr: bmKey.slice(0, 3).toUpperCase(), name: bmKey, domain: bmKey, color: '' };
  const adj = netPrice(price, bmKey);
  const href = buildGameUrl(bmKey, sport as 'NRL' | 'AFL', homeTeam, awayTeam);
  const Tag = href ? 'a' : 'div';
  const tagProps = href ? { href, target: '_blank', rel: 'noopener noreferrer' } : {};
  return (
    <Tag {...tagProps as any} className={[
      'relative flex shrink-0 w-[72px] flex-col items-center gap-1.5 rounded-xl border px-2 py-3',
      isBest
        ? 'border-[#00DEB8]/50 bg-[#00DEB8]/10 shadow-[inset_0_0_0_1px_rgba(0,222,184,0.3)]'
        : 'border-[#E2E8F0] bg-[#F8FAFC]',
    ].join(' ')}>
      {movement && (
        <span className={`absolute top-1.5 right-1.5 ${movement.direction === 'down' ? 'text-[#F97316]' : 'text-[#00B899]'}`}>
          <ArrowDown className={`h-3 w-3 ${movement.direction === 'up' ? 'rotate-180' : ''}`} />
        </span>
      )}
      <span className="flex h-6 w-6 items-center justify-center overflow-hidden rounded bg-white shadow-sm ring-1 ring-black/5">
        <img src={`https://www.google.com/s2/favicons?domain=${meta.domain}&sz=64`} alt={meta.abbr} className="h-4 w-4" />
      </span>
      <span className="text-[8px] font-mono font-black uppercase tracking-wide text-[#9CA3AF]">{meta.abbr}</span>
      {point != null && (
        <span className="text-[10px] font-mono font-bold text-[#9CA3AF] leading-none">
          {isTotal ? point : (point > 0 ? `+${point}` : point)}
        </span>
      )}
      <span className={`text-[15px] font-bold font-mono tabular-nums leading-tight ${isBest ? 'text-[#00866F]' : 'text-[#111827]'}`}>
        {adj.toFixed(2)}
      </span>
    </Tag>
  );
}

function MarketUnavailable({ market }: { market: MarketTab }) {
  return (
    <div className="rounded-lg border border-[#E2E8F0] bg-white px-4 py-10 text-center">
      <p className="font-mono text-xs font-bold uppercase tracking-widest text-[#9CA3AF]">{market} markets unavailable</p>
      <p className="mt-2 text-sm text-[#6B7280]">Check back closer to kickoff.</p>
    </div>
  );
}

function BviBadge({ tier }: { tier: BviTier | null }) {
  if (!tier || tier === 'neutral') return null;
  const isValue = tier === 'value';
  return (
    <span className={[
      'inline-flex items-center gap-0.5 rounded px-1.5 py-0.5 text-[9px] font-mono font-black uppercase tracking-widest',
      isValue ? 'bg-[#dcfce7] text-[#16a34a]' : 'bg-[#fee2e2] text-[#dc2626]',
    ].join(' ')}>
      {isValue ? '▲' : '▼'} {isValue ? 'Value' : 'Fade'}
    </span>
  );
}

function HomeAwayValueBadge({ type, pct }: { type: 'home' | 'away'; pct: number | null }) {
  const threshold = type === 'home' ? 70 : 65;
  if (pct == null || pct < threshold) return null;
  const isHome = type === 'home';
  return (
    <span
      title={`${isHome ? 'Home' : 'Away'} win rate ${pct.toFixed(1)}%`}
      className={[
        'inline-flex animate-pulse items-center gap-1 rounded px-1.5 py-0.5 text-[9px] font-mono font-black uppercase tracking-widest',
        isHome ? 'bg-[#dbeafe] text-[#2563eb]' : 'bg-[#fef3c7] text-[#b45309]',
      ].join(' ')}
    >
      {isHome ? '⌂' : '↗'} {isHome ? 'Home Value' : 'Away Value'}
    </span>
  );
}

function OddsBoardCard({
  game,
  market,
  movements,
  expanded,
  onToggleDetails,
  onAskBaz,
  bviHomeEntry,
  bviAwayEntry,
  homeAwayHomeEntry,
  homeAwayAwayEntry,
  teamNewsHomeEntry,
  teamNewsAwayEntry,
}: {
  game: Game;
  market: MarketTab;
  movements: MovementMap;
  expanded: boolean;
  onToggleDetails: () => void;
  onAskBaz: () => void;
  bviHomeEntry?: BviEntry | null;
  bviAwayEntry?: BviEntry | null;
  homeAwayHomeEntry?: HomeAwayValueEntry | null;
  homeAwayAwayEntry?: HomeAwayValueEntry | null;
  teamNewsHomeEntry?: TeamNewsEntry | null;
  teamNewsAwayEntry?: TeamNewsEntry | null;
}) {
  const [weather, setWeather] = useState<WeatherData | null>(null);
  const [weatherLoading, setWeatherLoading] = useState(true);
  const [showBVI, setShowBVI] = useState(false);
  const [showBVIInfo, setShowBVIInfo] = useState(false);
  const [showHaValue, setShowHaValue] = useState(false);
  const [showHaInfo, setShowHaInfo] = useState(false);
  const bviInfoRef = useRef<HTMLDivElement>(null);
  const haInfoRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!showBVIInfo && !showHaInfo) return;
    function handle(e: MouseEvent | TouchEvent) {
      if (showBVIInfo && !bviInfoRef.current?.contains(e.target as Node)) setShowBVIInfo(false);
      if (showHaInfo && !haInfoRef.current?.contains(e.target as Node)) setShowHaInfo(false);
    }
    document.addEventListener('mousedown', handle);
    document.addEventListener('touchstart', handle);
    return () => {
      document.removeEventListener('mousedown', handle);
      document.removeEventListener('touchstart', handle);
    };
  }, [showBVIInfo, showHaInfo]);

  const entries = bookmakerEntries(game, market);
  const venue = game.sport === 'AFL'
    ? getAFLVenue(game.homeTeam)
    : (game.venue ? getVenueByName(game.venue) : null) ?? getVenue(game.homeTeam);
  const stats = movementStats(game, market, movements);
  const gap = bestGap(entries);
  const refBucket = game.refereeBucket ?? 'Neutral';
  const teamMetaHome = getTeamMeta(game.homeTeam);
  const teamMetaAway = getTeamMeta(game.awayTeam);

  // Role-aware BVI: determine fav/dog from average H2H price, then use the
  // team's role-specific profit (fav_profit or und_profit) to drive the badge.
  // Positive role profit → ▲ Value. Negative → ▼ Fade. No entry → no badge.
  const h2hVals = Object.values(game.odds);
  const avgHome = h2hVals.length > 0 ? h2hVals.reduce((s, e) => s + e.home, 0) / h2hVals.length : 1;
  const avgAway = h2hVals.length > 0 ? h2hVals.reduce((s, e) => s + e.away, 0) / h2hVals.length : 1;
  const homeIsFav = avgHome <= avgAway;

  function roleProfit(entry: BviEntry | null | undefined, isFav: boolean): number | null {
    if (!entry) return null;
    return isFav ? entry.fav_profit : entry.und_profit;
  }
  function profitToTier(profit: number | null): BviTier | null {
    if (profit == null) return null;
    if (profit > 0) return 'value';
    if (profit < 0) return 'fade';
    return null;
  }

  const rawBviHome = profitToTier(roleProfit(bviHomeEntry, homeIsFav));
  const rawBviAway = profitToTier(roleProfit(bviAwayEntry, !homeIsFav));

  // Suppress both badges when the signal is the same on both sides —
  // two fades or two values in the same game gives you nothing to act on.
  const bothSame = rawBviHome != null && rawBviHome === rawBviAway;
  const displayBviHome: BviTier | null = showBVI && !bothSame ? rawBviHome : null;
  const displayBviAway: BviTier | null = showBVI && !bothSame ? rawBviAway : null;
  const homeValuePct = showHaValue ? (homeAwayHomeEntry?.home_win_pct ?? null) : null;
  const awayValuePct = showHaValue ? (homeAwayAwayEntry?.away_win_pct ?? null) : null;

  useEffect(() => {
    if (!venue) { setWeatherLoading(false); return; }

    function fetchWeather() {
      fetch(`/api/weather?lat=${venue!.lat}&lon=${venue!.lon}&time=${encodeURIComponent(game.commenceTime)}`)
        .then((r) => (r.ok ? r.json() : null))
        .then((data) => { if (data) setWeather(data as WeatherData); })
        .catch(() => {})
        .finally(() => setWeatherLoading(false));
    }

    fetchWeather();

    const kickoff = new Date(game.commenceTime).getTime();
    const now = Date.now();
    const ids: ReturnType<typeof setTimeout>[] = [];

    // 1 hour before kickoff
    const msToPreGame = kickoff - 60 * 60 * 1000 - now;
    if (msToPreGame > 0) ids.push(setTimeout(fetchWeather, msToPreGame));

    // Halftime: NRL ~45 min in, AFL ~65 min in
    const halftimeOffset = (game.sport === 'AFL' ? 65 : 45) * 60 * 1000;
    const msToHalftime = kickoff + halftimeOffset - now;
    if (msToHalftime > 0) ids.push(setTimeout(fetchWeather, msToHalftime));

    return () => ids.forEach(clearTimeout);
  }, [venue?.lat, venue?.lon, game.commenceTime, game.sport]);

  if (entries.length === 0) return <MarketUnavailable market={market} />;

  const lineAware = market !== 'H2H';
  const bestHome = comparableBest(entries, 'home', lineAware);
  const bestAway = comparableBest(entries, 'away', lineAware);
  const selected = market === 'Totals' ? 'Over / Under' : `${game.homeShort} / ${game.awayShort}`;
  const displayEntries = entries.slice(0, 10);
  const mobileEntries = entries;
  const bookmakerColumnCount = Math.max(displayEntries.length, 1);
  const labelCol = 150;
  const bookCol  = 72;
  const gridMinWidth = labelCol + bookmakerColumnCount * (bookCol + 10);

  return (
    <article className={['relative overflow-hidden rounded-xl border bg-white transition-all duration-200', expanded ? 'border-[#00DEB8] shadow-[0_0_0_3px_rgba(0,222,184,0.10)]' : 'border-[#E2E8F0]', (showBVIInfo || showHaInfo) ? 'z-10' : ''].join(' ')}>
      <div className="overflow-hidden rounded-t-xl">
        <div
          className="h-1.5"
          style={{
            background: `linear-gradient(90deg, ${teamMetaHome?.primary ?? '#111827'} 0%, ${teamMetaHome?.primary ?? '#111827'} 45%, #E2E8F0 45%, #E2E8F0 55%, ${teamMetaAway?.primary ?? '#111827'} 55%, ${teamMetaAway?.primary ?? '#111827'} 100%)`,
          }}
        />
      </div>

      {/* ── Mobile header (hidden on sm+) ── */}
      <div className="sm:hidden px-3 pt-3 pb-2">
        <div className="mb-1.5 flex items-center gap-2 flex-wrap">
          <span className="rounded bg-[#111827] px-2 py-0.5 text-[9px] font-mono font-bold uppercase tracking-widest text-white">{game.sport}</span>
          <span className="text-[10px] font-mono uppercase tracking-wide text-[#6B7280]">{game.kickoffTime}</span>
          <span className="text-[10px] text-[#9CA3AF]">{market}</span>
        </div>
        <div className="mb-0.5 flex flex-wrap items-center gap-x-2 gap-y-1">
          <TeamBadge name={game.homeTeam} label={game.homeTeam.split(' ').pop()} />
          <BviBadge tier={displayBviHome} />
          <HomeAwayValueBadge type="home" pct={homeValuePct} />
          <span className="text-[9px] font-mono font-black uppercase tracking-widest text-[#9CA3AF]">vs</span>
          <TeamBadge name={game.awayTeam} label={game.awayTeam.split(' ').pop()} />
          <BviBadge tier={displayBviAway} />
          <HomeAwayValueBadge type="away" pct={awayValuePct} />
        </div>
        {venue && <p className="mb-2 text-[10px] text-[#9CA3AF]">{venue.name}</p>}
        <div className="flex w-full gap-2 mt-2">
          <button
            onClick={onAskBaz}
            className="flex-1 inline-flex items-center justify-center gap-1.5 rounded-lg bg-[#00DEB8] py-2.5 text-xs font-bold text-black"
          >
            <Bot className="h-3.5 w-3.5" />
            Ask Baz
          </button>
          <button
            onClick={onToggleDetails}
            className="flex-1 inline-flex items-center justify-center gap-1 rounded-lg border border-[#E2E8F0] bg-white py-2.5 text-xs font-mono font-bold uppercase tracking-widest text-[#6B7280]"
          >
            Details
            <ChevronDown className={`h-3.5 w-3.5 transition-transform ${expanded ? 'rotate-180' : ''}`} />
          </button>
        </div>
        {(bviHomeEntry || bviAwayEntry || homeAwayHomeEntry || homeAwayAwayEntry) && (
          <div className="flex gap-2 mt-2">
            {(bviHomeEntry || bviAwayEntry) && (
              <button
                type="button"
                onClick={() => setShowBVI(v => !v)}
                className={[
                  'flex-1 inline-flex items-center justify-center gap-1.5 rounded-lg border py-2 text-[10px] font-mono font-bold uppercase tracking-widest transition-colors',
                  showBVI ? 'border-[#22c55e]/50 bg-[#22c55e]/10 text-[#16a34a]' : 'border-[#E2E8F0] bg-[#F8FAFC] text-[#9CA3AF]',
                ].join(' ')}
              >
                <span className={['flex h-2.5 w-2.5 items-center justify-center rounded-sm border text-[7px]', showBVI ? 'border-[#16a34a] bg-[#22c55e] text-white' : 'border-[#D1D5DB]'].join(' ')}>
                  {showBVI ? '✓' : ''}
                </span>
                BVI
              </button>
            )}
            {(homeAwayHomeEntry || homeAwayAwayEntry) && (
              <button
                type="button"
                onClick={() => setShowHaValue(v => !v)}
                className={[
                  'flex-1 inline-flex items-center justify-center gap-1.5 rounded-lg border py-2 text-[10px] font-mono font-bold uppercase tracking-widest transition-colors',
                  showHaValue ? 'border-[#2563eb]/50 bg-[#dbeafe] text-[#2563eb]' : 'border-[#E2E8F0] bg-[#F8FAFC] text-[#9CA3AF]',
                ].join(' ')}
              >
                <span className={['flex h-2.5 w-2.5 items-center justify-center rounded-sm border text-[7px]', showHaValue ? 'border-[#2563eb] bg-[#2563eb] text-white' : 'border-[#D1D5DB]'].join(' ')}>
                  {showHaValue ? '✓' : ''}
                </span>
                H/A Value
              </button>
            )}
          </div>
        )}
      </div>

      {/* ── Desktop header (hidden on mobile) ── */}
      <div className="hidden sm:block px-4 py-4">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0">
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <span className="rounded bg-[#111827] px-2 py-1 text-[10px] font-mono font-bold uppercase tracking-widest text-white">{game.sport}</span>
              <span className="text-[11px] font-mono uppercase tracking-wide text-[#6B7280]">{game.kickoffTime}</span>
              <span className="text-[11px] text-[#9CA3AF]">{market} - {selected}</span>
            </div>
            <h2 className="flex flex-wrap items-center gap-x-2 gap-y-1 font-display text-lg font-extrabold leading-tight text-[#111827] sm:text-xl">
              <TeamBadge name={game.homeTeam} />
              <BviBadge tier={displayBviHome} />
              <HomeAwayValueBadge type="home" pct={homeValuePct} />
              <span className="text-[10px] font-mono font-black uppercase tracking-widest text-[#9CA3AF]">vs</span>
              <TeamBadge name={game.awayTeam} />
              <BviBadge tier={displayBviAway} />
              <HomeAwayValueBadge type="away" pct={awayValuePct} />
            </h2>
            {venue && <p className="mt-1 text-xs text-[#9CA3AF]">{venue.name}</p>}
          </div>

          <div className="flex flex-col gap-2 lg:items-end">
            <div className="flex gap-2">
              <button
                onClick={onAskBaz}
                className="inline-flex items-center justify-center gap-2 rounded-md bg-[#00DEB8] px-3 py-2 text-xs font-bold text-black shadow-[0_8px_24px_rgba(0,222,184,0.22)] transition-all hover:-translate-y-0.5 hover:bg-[#00C9A6]"
              >
                <Bot className="h-4 w-4" />
                Ask Baz
              </button>
              <button
                onClick={onToggleDetails}
                className="inline-flex items-center justify-center gap-1 rounded-md border border-[#E2E8F0] bg-white px-3 py-2 text-xs font-mono font-bold uppercase tracking-widest text-[#6B7280] transition-colors hover:border-[#00DEB8]/60 hover:text-[#00866F]"
              >
                Details
                <ChevronDown className={`h-3.5 w-3.5 transition-transform ${expanded ? 'rotate-180' : ''}`} />
              </button>
            </div>

            {(bviHomeEntry || bviAwayEntry || homeAwayHomeEntry || homeAwayAwayEntry) && (
              <div className="flex flex-wrap justify-end gap-2">

                {(bviHomeEntry || bviAwayEntry) && (
                  <div className="relative" ref={bviInfoRef}>
                    <div className="inline-flex items-stretch overflow-hidden rounded border border-[#E2E8F0] bg-white text-[11px] font-mono font-bold uppercase tracking-widest">
                      <button
                        type="button"
                        onClick={() => setShowBVI(v => !v)}
                        className={['inline-flex items-center gap-1.5 px-2.5 py-1.5 transition-colors', showBVI ? 'bg-[#22c55e]/10 text-[#16a34a]' : 'text-[#6B7280] hover:bg-[#F8FAFC]'].join(' ')}
                      >
                        <span className={['flex h-3 w-3 items-center justify-center rounded-sm border text-[8px]', showBVI ? 'border-[#16a34a] bg-[#22c55e] text-white' : 'border-[#D1D5DB]'].join(' ')}>
                          {showBVI ? '✓' : ''}
                        </span>
                        BVI
                      </button>
                      <div className="w-px bg-[#E2E8F0]" />
                      <button
                        type="button"
                        onClick={() => setShowBVIInfo(v => !v)}
                        className="flex items-center px-2 py-1.5 text-[#9CA3AF] transition-colors hover:bg-[#F8FAFC] hover:text-[#6B7280]"
                      >
                        <Info className="h-3 w-3" />
                      </button>
                    </div>
                    {showBVIInfo && (
                      <div className="absolute right-0 top-full mt-1 z-50 w-72 rounded-xl border border-[#E2E8F0] bg-white p-4 shadow-xl">
                        <p className="mb-2 text-[11px] font-mono font-black uppercase tracking-widest text-[#111827]">Betting Value Index</p>
                        <p className="mb-3 text-xs leading-relaxed text-[#6B7280]">
                          The <strong className="text-[#111827]">AFL Betting Value Index</strong> ranks all 18 teams by their current betting value — a composite of recent form, market pricing, and public perception gaps.
                        </p>
                        <div className="mb-3 space-y-1.5">
                          <div className="flex items-center gap-2"><span className="inline-flex items-center gap-0.5 rounded bg-[#dcfce7] px-1.5 py-0.5 text-[9px] font-mono font-black uppercase tracking-widest text-[#16a34a]">▲ Value</span><span className="text-xs text-[#6B7280]">Top 6 — market underrating them</span></div>
                          <div className="flex items-center gap-2"><span className="inline-flex items-center rounded bg-[#F3F4F6] px-1.5 py-0.5 text-[9px] font-mono font-black uppercase tracking-widest text-[#9CA3AF]">Neutral</span><span className="text-xs text-[#6B7280]">Mid 6 — no strong lean</span></div>
                          <div className="flex items-center gap-2"><span className="inline-flex items-center gap-0.5 rounded bg-[#fee2e2] px-1.5 py-0.5 text-[9px] font-mono font-black uppercase tracking-widest text-[#dc2626]">▼ Fade</span><span className="text-xs text-[#6B7280]">Bottom 6 — market overrating them</span></div>
                        </div>
                        <p className="text-[10px] leading-relaxed text-[#9CA3AF]">Badges appear when teams are in different tiers — same-tier matchups are suppressed. Updated weekly.</p>
                      </div>
                    )}
                  </div>
                )}

                {(homeAwayHomeEntry || homeAwayAwayEntry) && (
                  <div className="relative" ref={haInfoRef}>
                    <div className="inline-flex items-stretch overflow-hidden rounded border border-[#E2E8F0] bg-white text-[11px] font-mono font-bold uppercase tracking-widest">
                      <button
                        type="button"
                        onClick={() => setShowHaValue(v => !v)}
                        className={['inline-flex items-center gap-1.5 px-2.5 py-1.5 transition-colors', showHaValue ? 'bg-[#dbeafe] text-[#2563eb]' : 'text-[#6B7280] hover:bg-[#F8FAFC]'].join(' ')}
                      >
                        <span className={['flex h-3 w-3 items-center justify-center rounded-sm border text-[8px]', showHaValue ? 'border-[#2563eb] bg-[#2563eb] text-white' : 'border-[#D1D5DB]'].join(' ')}>
                          {showHaValue ? '✓' : ''}
                        </span>
                        H/A Value
                      </button>
                      <div className="w-px bg-[#E2E8F0]" />
                      <button
                        type="button"
                        onClick={() => setShowHaInfo(v => !v)}
                        className="flex items-center px-2 py-1.5 text-[#9CA3AF] transition-colors hover:bg-[#F8FAFC] hover:text-[#6B7280]"
                      >
                        <Info className="h-3 w-3" />
                      </button>
                    </div>
                    {showHaInfo && (
                      <div className="absolute right-0 top-full mt-1 z-50 w-72 rounded-xl border border-[#E2E8F0] bg-white p-4 shadow-xl">
                        <p className="mb-2 text-[11px] font-mono font-black uppercase tracking-widest text-[#111827]">Home / Away Value</p>
                        <p className="mb-3 text-xs leading-relaxed text-[#6B7280]">Flags AFL teams with a strong venue split based on home-field advantage data.</p>
                        <div className="mb-3 space-y-1.5">
                          <div className="flex items-center gap-2"><span className="inline-flex items-center gap-1 rounded bg-[#dbeafe] px-1.5 py-0.5 text-[9px] font-mono font-black uppercase tracking-widest text-[#2563eb]">⌂ Home Value</span><span className="text-xs text-[#6B7280]">Home team wins 70%+ at home</span></div>
                          <div className="flex items-center gap-2"><span className="inline-flex items-center gap-1 rounded bg-[#fef3c7] px-1.5 py-0.5 text-[9px] font-mono font-black uppercase tracking-widest text-[#b45309]">↗ Away Value</span><span className="text-xs text-[#6B7280]">Away team wins 65%+ away</span></div>
                        </div>
                        <p className="text-[10px] leading-relaxed text-[#9CA3AF]">Updated weekly.</p>
                      </div>
                    )}
                  </div>
                )}

              </div>
            )}
          </div>
        </div>
      </div>

      {/* Mobile tile view — CSS hidden at sm+ so server renders this first */}
      <div className="sm:hidden border-t border-[#E2E8F0] px-3 py-4 space-y-4">
        {/* Home / Over */}
        <div>
          <div className="mb-2 flex items-center gap-2">
            {market === 'Totals' ? (
              <TotalSelectionLabel side="Over" point={bestHome.point} />
            ) : market === 'Line' ? (
              <div className="flex items-center gap-2">
                <TeamBadge name={game.homeTeam} label={game.homeTeam.split(' ').pop()} />
                {bestHome.point != null && (
                  <span className="text-[11px] font-mono font-bold text-[#6B7280]">
                    {bestHome.point > 0 ? '+' : ''}{bestHome.point}
                  </span>
                )}
              </div>
            ) : (
              <TeamBadge name={game.homeTeam} label={game.homeTeam.split(' ').pop()} />
            )}
          </div>
          <div className="flex gap-2 overflow-x-auto pb-2 no-scrollbar">
            {mobileEntries.map((entry) => (
              <MobilePriceTile
                key={entry.key}
                bmKey={entry.key}
                price={entry.home.price}
                point={entry.home.point}
                isBest={entry.home.price === bestHome.price && (!lineAware || entry.home.point === bestHome.point)}
                movement={movements[movementKey(game.id, market, entry.key, entry.home.side)]}
                isTotal={market === 'Totals'}
                homeTeam={game.homeTeam}
                awayTeam={game.awayTeam}
                sport={game.sport}
              />
            ))}
          </div>
        </div>
        {/* Away / Under */}
        <div>
          <div className="mb-2 flex items-center gap-2">
            {market === 'Totals' ? (
              <TotalSelectionLabel side="Under" point={bestAway.point} />
            ) : market === 'Line' ? (
              <div className="flex items-center gap-2">
                <TeamBadge name={game.awayTeam} label={game.awayTeam.split(' ').pop()} />
                {bestAway.point != null && (
                  <span className="text-[11px] font-mono font-bold text-[#6B7280]">
                    {bestAway.point > 0 ? '+' : ''}{bestAway.point}
                  </span>
                )}
              </div>
            ) : (
              <TeamBadge name={game.awayTeam} label={game.awayTeam.split(' ').pop()} />
            )}
          </div>
          <div className="flex gap-2 overflow-x-auto pb-2 no-scrollbar">
            {mobileEntries.map((entry) => (
              <MobilePriceTile
                key={entry.key}
                bmKey={entry.key}
                price={entry.away.price}
                point={entry.away.point}
                isBest={entry.away.price === bestAway.price && (!lineAware || entry.away.point === bestAway.point)}
                movement={movements[movementKey(game.id, market, entry.key, entry.away.side)]}
                isTotal={market === 'Totals'}
                homeTeam={game.homeTeam}
                awayTeam={game.awayTeam}
                sport={game.sport}
              />
            ))}
          </div>
        </div>
      </div>

      {/* Desktop grid — hidden on mobile */}
      <div className="hidden sm:block overflow-x-auto">
        <div
          className="grid"
          style={{
            minWidth: `${gridMinWidth}px`,
            gridTemplateColumns: `minmax(${labelCol}px,1.1fr) repeat(${bookmakerColumnCount}, minmax(${bookCol}px,1fr))`,
          }}
        >
          <div className="border-t border-r border-[#E2E8F0] bg-[#F8FAFC] px-4 py-2 text-[10px] font-mono uppercase tracking-widest text-[#9CA3AF]">Selection</div>
          {displayEntries.map((entry) => (
            <div key={entry.key} className="border-t border-r border-[#E2E8F0] bg-[#FBFCFE] px-2 py-2 text-center last:border-r-0">
              <BookLogo bmKey={entry.key} homeTeam={game.homeTeam} awayTeam={game.awayTeam} sport={game.sport} />
            </div>
          ))}

          <div className="border-t border-r border-[#E2E8F0] px-4 py-3">
            {market === 'Totals' ? (
              <TotalSelectionLabel side="Over" point={bestHome.point} />
            ) : market === 'Line' ? (
              <div>
                <TeamBadge name={game.homeTeam} label={game.homeTeam.split(' ').pop()} />
                {bestHome.point != null && (
                  <span className="mt-1 block text-[10px] font-mono font-bold text-[#6B7280]">
                    {bestHome.point > 0 ? '+' : ''}{bestHome.point}
                  </span>
                )}
              </div>
            ) : (
              <TeamBadge name={game.homeTeam} label={game.homeTeam.split(' ').pop()} />
            )}
          </div>
          {displayEntries.map((entry) => (
            <PriceCell
              key={`${entry.key}-home`}
              price={entry.home.price}
              point={entry.home.point}
              isBest={entry.home.price === bestHome.price && (!lineAware || entry.home.point === bestHome.point)}
              movement={movements[movementKey(game.id, market, entry.key, entry.home.side)]}
              isTotal={market === 'Totals'}
            />
          ))}

          <div className="border-t border-r border-[#E2E8F0] px-4 py-3">
            {market === 'Totals' ? (
              <TotalSelectionLabel side="Under" point={bestAway.point} />
            ) : market === 'Line' ? (
              <div>
                <TeamBadge name={game.awayTeam} label={game.awayTeam.split(' ').pop()} />
                {bestAway.point != null && (
                  <span className="mt-1 block text-[10px] font-mono font-bold text-[#6B7280]">
                    {bestAway.point > 0 ? '+' : ''}{bestAway.point}
                  </span>
                )}
              </div>
            ) : (
              <TeamBadge name={game.awayTeam} label={game.awayTeam.split(' ').pop()} />
            )}
          </div>
          {displayEntries.map((entry) => (
            <PriceCell
              key={`${entry.key}-away`}
              price={entry.away.price}
              point={entry.away.point}
              isBest={entry.away.price === bestAway.price && (!lineAware || entry.away.point === bestAway.point)}
              movement={movements[movementKey(game.id, market, entry.key, entry.away.side)]}
              isTotal={market === 'Totals'}
            />
          ))}
        </div>
      </div>

      <div className="border-t border-[#E2E8F0] bg-[#F8FAFC] px-3 py-3">
        <div className="flex gap-2 overflow-x-auto no-scrollbar pb-1 sm:flex-wrap sm:overflow-visible sm:pb-0">
          <Chip icon={Flame} label="Move" value={stats.label} tone={stats.tone as 'neutral' | 'hot' | 'warn'} />
          <Chip icon={Trophy} label="Best price gap" value={gap > 0 ? `${gap.toFixed(1)}%` : 'N/A'} tone={gap >= 3 ? 'good' : 'neutral'} tooltip="The % difference between the best and worst price across all bookmakers. Betfair prices are adjusted for 5% commission. A gap above 3% means real money is being left on the table." />
          <Chip
            icon={CloudRain}
            label="Weather"
            value={
              !venue ? 'N/A' :
              weatherLoading ? '...' :
              !weather ? 'N/A' :
              weather.flags.length > 0 ? `${weather.flags[0]} · ${weather.temperature}°` :
              `${weather.temperature}° · Clear`
            }
            tone={
              !weather ? 'neutral' :
              weather.condition === 'good' ? 'good' :
              weather.condition === 'bad' ? 'hot' :
              weather.condition === 'poor' ? 'warn' : 'neutral'
            }
          />
          {game.sport === 'NRL' && <Chip icon={ShieldAlert} label="Ref" value={game.referee ? `${game.referee} · ${refBucket}` : refBucket} />}
          <Chip icon={Stethoscope} label="Team news" value={(teamNewsHomeEntry?.status === 'alert' || teamNewsAwayEntry?.status === 'alert') ? 'Alert' : 'Monitor'} tone={(teamNewsHomeEntry?.status === 'alert' || teamNewsAwayEntry?.status === 'alert') ? 'hot' : 'warn'} />
        </div>
        <p className="hidden sm:block mt-3 text-sm leading-6 text-[#4B5563]">
          {stats.label === 'Quiet' ? 'No major market move flagged yet.' : `${stats.label} detected on ${market}. Best price gap is ${gap.toFixed(1)}%.`} Ask Baz for the plain-English read before kickoff.
        </p>
      </div>

      {expanded && <DetailDrawer game={game} market={market} entries={entries} movements={movements} weather={weather} venue={venue} teamNewsHomeEntry={teamNewsHomeEntry} teamNewsAwayEntry={teamNewsAwayEntry} />}
    </article>
  );
}

function HistoryTab({ homeTeam, awayTeam, sport }: { homeTeam: string; awayTeam: string; sport: string }) {
  interface FG { date: string; opponent: string; teamScore: number; oppScore: number; won: boolean; isHome: boolean; venue: string; }
  interface RM { date: string; homeTeam: string; awayTeam: string; homeScore: number; awayScore: number; venue: string; }
  const [formData, setFormData] = useState<{ homeForm: FG[]; awayForm: FG[]; h2h: RM[]; note?: string } | null>(null);
  const [formLoading, setFormLoading] = useState(true);

  useEffect(() => {
    setFormLoading(true);
    fetch('/api/form?home=' + encodeURIComponent(homeTeam) + '&away=' + encodeURIComponent(awayTeam) + '&sport=' + sport)
      .then(r => r.json())
      .then(d => { setFormData(d); setFormLoading(false); })
      .catch(() => setFormLoading(false));
  }, [homeTeam, awayTeam, sport]);

  const homeNick = homeTeam.split(' ').pop() ?? homeTeam;
  const awayNick = awayTeam.split(' ').pop() ?? awayTeam;

  function FormTable({ games, label }: { games: FG[]; label: string }) {
    if (games.length === 0) {
      return <div className="text-[10px] font-mono text-[#9CA3AF] text-center py-2">No data</div>;
    }
    return (
      <div>
        <p className="text-[9px] font-mono text-[#9CA3AF] uppercase tracking-widest mb-1.5">{label} — Last {games.length}</p>
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-[#E2E8F0]">
              {['Date', 'Opponent', 'Score', 'H/A', 'Res'].map(h => (
                <th key={h} className="pb-1 pr-2 text-[9px] font-mono text-[#9CA3AF] uppercase tracking-widest whitespace-nowrap">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {games.map((g, i) => (
              <tr key={i} className="border-b border-[#E2E8F0] hover:bg-[#F8FAFC]">
                <td className="py-1 pr-2 text-[10px] font-mono text-[#9CA3AF] whitespace-nowrap">{g.date.slice(5)}</td>
                <td className="py-1 pr-2 text-[10px] font-mono text-[#374151] max-w-[100px] truncate" title={g.opponent}>{g.opponent.split(' ').pop()}</td>
                <td className="py-1 pr-2 text-[10px] font-mono tabular-nums text-[#374151] whitespace-nowrap">{g.teamScore}&#8211;{g.oppScore}</td>
                <td className="py-1 pr-2 text-[9px] font-mono text-[#9CA3AF]">{g.isHome ? 'H' : 'A'}</td>
                <td className="py-1">
                  {g.won
                    ? <span className="px-1 py-0.5 rounded text-[9px] font-mono font-bold bg-[#00DEB8]/15 text-[#00DEB8]">W</span>
                    : <span className="px-1 py-0.5 rounded text-[9px] font-mono font-bold bg-red-500/15 text-red-500">L</span>
                  }
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  function H2HTable({ matches }: { matches: RM[] }) {
    if (matches.length === 0) {
      return <div className="text-[10px] font-mono text-[#9CA3AF] text-center py-2">No H2H data</div>;
    }
    const hNick = homeTeam.split(' ').pop()!.toLowerCase();
    return (
      <div>
        <p className="text-[9px] font-mono text-[#9CA3AF] uppercase tracking-widest mb-1.5">H2H — Last {matches.length}</p>
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-[#E2E8F0]">
              {['Date', 'Home', 'Away', 'Score'].map(h => (
                <th key={h} className="pb-1 pr-2 text-[9px] font-mono text-[#9CA3AF] uppercase tracking-widest whitespace-nowrap">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {matches.map((m, i) => {
              const ourHomeWon = m.homeTeam.toLowerCase().includes(hNick) ? m.homeScore > m.awayScore : m.awayScore > m.homeScore;
              return (
                <tr key={i} className="border-b border-[#E2E8F0] hover:bg-[#F8FAFC]">
                  <td className="py-1 pr-2 text-[10px] font-mono text-[#9CA3AF] whitespace-nowrap">{m.date.slice(5)}</td>
                  <td className="py-1 pr-2 text-[10px] font-mono text-[#374151] max-w-[80px] truncate" title={m.homeTeam}>{m.homeTeam.split(' ').pop()}</td>
                  <td className="py-1 pr-2 text-[10px] font-mono text-[#374151] max-w-[80px] truncate" title={m.awayTeam}>{m.awayTeam.split(' ').pop()}</td>
                  <td className="py-1">
                    <span className={ourHomeWon ? 'text-[#00DEB8] font-bold text-[10px] font-mono tabular-nums' : 'text-red-400 font-bold text-[10px] font-mono tabular-nums'}>
                      {m.homeScore}&#8211;{m.awayScore}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    );
  }

  if (formLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <p className="text-[10px] font-mono text-[#9CA3AF] uppercase tracking-widest">Loading form data...</p>
      </div>
    );
  }

  if (!formData) {
    return (
      <div className="rounded-lg border border-[#E2E8F0] bg-[#F8FAFC] p-6 text-center">
        <History className="h-5 w-5 text-[#9CA3AF] mx-auto mb-2" />
        <p className="text-xs text-[#9CA3AF] font-mono uppercase tracking-widest">Could not load form data</p>
      </div>
    );
  }

  if (formData.note) {
    return (
      <div className="rounded-lg border border-[#E2E8F0] bg-[#F8FAFC] p-6 text-center">
        <History className="h-5 w-5 text-[#9CA3AF] mx-auto mb-2" />
        <p className="text-xs text-[#9CA3AF] font-mono uppercase tracking-widest">{formData.note}</p>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <FormTable games={formData.homeForm} label={homeNick} />
      <FormTable games={formData.awayForm} label={awayNick} />
      <H2HTable matches={formData.h2h} />
    </div>
  );
}
function DetailDrawer({
  game,
  market,
  entries,
  movements,
  weather,
  venue,
  teamNewsHomeEntry,
  teamNewsAwayEntry,
}: {
  game: Game;
  market: MarketTab;
  entries: ReturnType<typeof bookmakerEntries>;
  movements: MovementMap;
  weather: WeatherData | null;
  venue: { name: string; lat: number; lon: number } | null;
  teamNewsHomeEntry?: TeamNewsEntry | null;
  teamNewsAwayEntry?: TeamNewsEntry | null;
}) {
  const [tab, setTab] = useState<DetailTab>('Intelligence');
  const stats = movementStats(game, market, movements);
  const gap = bestGap(entries);

  return (
    <div className="border-t border-[#E2E8F0] bg-white">
      <div className="flex gap-1 overflow-x-auto border-b border-[#E2E8F0] bg-[#111827] p-2 no-scrollbar">
        {DETAIL_TABS.map((item) => (
          <button
            key={item}
            onClick={() => setTab(item)}
            className={[
              'shrink-0 rounded px-3 py-2 text-[10px] font-mono font-bold uppercase tracking-widest transition-colors',
              tab === item ? 'bg-[#00DEB8] text-black' : 'text-[#CBD5E1] hover:bg-white/8',
            ].join(' ')}
          >
            {item}
          </button>
        ))}
      </div>

      <div className="p-4">
        {tab === 'Intelligence' && (
          <div className="grid gap-4 lg:grid-cols-[1fr_1fr]">
            <div>
              <div className="mb-3 flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-[#00B899]" />
                <h3 className="font-display font-bold text-[#111827]">Intelligence layer</h3>
              </div>
              <div className="grid gap-3 sm:grid-cols-3">
                {[
                  ['Move score', stats.label, `${stats.count} price signals`],
                  ['Best gap', `${gap.toFixed(1)}%`, 'Difference across books'],
                  ['Public read', stats.label === 'Quiet' ? 'Wait' : 'Watch', 'Signal, not a tip'],
                ].map(([label, value, copy]) => (
                  <div key={label} className="rounded-lg border border-[#E2E8F0] bg-[#F8FAFC] p-3">
                    <p className="text-[10px] font-mono uppercase tracking-widest text-[#9CA3AF]">{label}</p>
                    <p className="mt-1 text-lg font-mono font-black text-[#111827]">{value}</p>
                    <p className="mt-1 text-xs leading-5 text-[#6B7280]">{copy}</p>
                  </div>
                ))}
              </div>
            </div>
            <div className="rounded-lg border border-[#00DEB8]/35 bg-[#00DEB8]/8 p-4">
              <p className="mb-2 text-[10px] font-mono uppercase tracking-widest text-[#00866F]">Why this matters</p>
              <p className="text-sm leading-6 text-[#374151]">
                BetMATE keeps the odds board simple, then uses movement, price gaps, referee, weather and team-news context to explain what may matter before kickoff.
              </p>
            </div>
          </div>
        )}

        {tab === 'Team News' && (
          <div className="grid gap-3 md:grid-cols-2">
            {([
              [game.homeTeam, teamNewsHomeEntry],
              [game.awayTeam, teamNewsAwayEntry],
            ] as [string, TeamNewsEntry | null | undefined][]).map(([team, newsEntry]) => {
              const hasAlert = newsEntry?.status === 'alert' && (newsEntry.items?.length ?? 0) > 0;
              return (
                <div key={team} className={`rounded-lg border p-3 ${hasAlert ? 'border-amber-300 bg-amber-50' : 'border-[#E2E8F0] bg-[#F8FAFC]'}`}>
                  <div className="mb-2 flex items-center gap-2">
                    <Stethoscope className={`h-4 w-4 ${hasAlert ? 'text-amber-700' : 'text-[#00B899]'}`} />
                    <p className="text-sm font-bold text-[#111827]">{team}</p>
                  </div>
                  {hasAlert ? (
                    <ul className="space-y-2">
                      {newsEntry!.items.map((item, i) => (
                        <li key={i} className="flex items-start gap-2">
                          <span className={`mt-0.5 shrink-0 rounded px-1 py-0.5 text-[9px] font-mono font-bold uppercase tracking-widest ${item.type === 'suspension' ? 'bg-amber-200 text-amber-900' : 'bg-red-100 text-red-700'}`}>
                            {item.type === 'suspension' ? 'SUSP' : 'OUT'}
                          </span>
                          <div>
                            <span className={`text-xs font-bold ${item.severity === 'high' ? 'text-red-700' : item.severity === 'medium' ? 'text-amber-700' : 'text-[#374151]'}`}>{item.player}</span>
                            <span className="ml-1 text-xs text-[#6B7280]">{item.detail}</span>
                          </div>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-xs leading-5 text-[#6B7280]">Monitor — no significant news flagged.</p>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {tab === 'Weather / Ref' && (
          <div className="grid gap-3 md:grid-cols-2">
            <div className={`rounded-lg border p-3 ${weather && weather.condition !== 'good' ? 'border-amber-300 bg-amber-50' : 'border-[#E2E8F0] bg-[#F8FAFC]'}`}>
              <div className="mb-2 flex items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <Wind className={`h-4 w-4 ${weather && weather.condition !== 'good' ? 'text-amber-600' : 'text-[#00B899]'}`} />
                  <p className="text-sm font-bold text-[#111827]">{venue ? venue.name : 'Weather'}</p>
                </div>
                {weather && (
                  <span className={`text-[10px] font-mono font-bold uppercase tracking-widest ${weather.condition === 'good' ? 'text-[#00866F]' : weather.condition === 'bad' ? 'text-[#EA580C]' : 'text-amber-700'}`}>
                    {weather.condition}
                  </span>
                )}
              </div>
              {!venue && <p className="text-xs text-[#9CA3AF]">Venue not available.</p>}
              {venue && !weather && <p className="text-xs text-[#9CA3AF]">Loading weather...</p>}
              {weather && (
                <div className="space-y-1.5">
                  <div className="grid grid-cols-2 gap-2">
                    {[
                      ['Temp', `${weather.temperature}°C`],
                      ['Humidity', `${weather.humidity}%`],
                      ['Wind', `${weather.windSpeed} km/h`],
                      ['Gusts', `${weather.windGust} km/h`],
                      ['Rain prob', `${weather.precipProbability}%`],
                      ['Dew point', `${weather.dewPoint}°C`],
                    ].map(([label, value]) => (
                      <div key={label}>
                        <p className="text-[10px] font-mono uppercase tracking-widest text-[#9CA3AF]">{label}</p>
                        <p className="text-sm font-mono font-bold text-[#111827]">{value}</p>
                      </div>
                    ))}
                  </div>
                  {weather.flags.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {weather.flags.map((flag) => (
                        <span key={flag} className="rounded bg-amber-100 px-2 py-0.5 text-[10px] font-mono font-bold uppercase tracking-wide text-amber-800">{flag}</span>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
            <div className="rounded-lg border border-[#E2E8F0] bg-[#F8FAFC] p-3">
              <div className="mb-2 flex items-center gap-2">
                <ShieldAlert className="h-4 w-4 text-[#00B899]" />
                <p className="text-sm font-bold text-[#111827]">Referee</p>
              </div>
              <p className="text-xs leading-5 text-[#6B7280]">{game.referee ? `${game.referee}. Profile: ${game.refereeBucket ?? 'Neutral'}.` : 'Referee data not available for this match.'}</p>
            </div>
          </div>
        )}

        {tab === 'History' && (
          <HistoryTab homeTeam={game.homeTeam} awayTeam={game.awayTeam} sport={game.sport} />
        )}
      </div>
    </div>
  );
}

function BoardSummary({ games, market, movements }: { games: Game[]; market: MarketTab; movements: MovementMap }) {
  const moveCount = games.filter((game) => movementStats(game, market, movements).label !== 'Quiet').length;
  return (
    <aside className="hidden xl:block xl:sticky xl:top-[76px]">
      <div className="space-y-4">
        <div className="rounded-xl border border-[#E2E8F0] bg-white p-4">
          <p className="section-label mb-2">Board summary</p>
          <div className="grid grid-cols-2 gap-3">
            {[
              ['Games', games.length.toString()],
              ['Movers', moveCount.toString()],
              ['Market', market],
              ['Sports', '2'],
            ].map(([label, value]) => (
              <div key={label} className="rounded-md border border-[#E2E8F0] bg-[#F8FAFC] px-3 py-3">
                <p className="text-[10px] font-mono uppercase tracking-widest text-[#9CA3AF]">{label}</p>
                <p className="mt-1 text-xl font-mono font-black text-[#111827]">{value}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-xl border border-[#E2E8F0] bg-white p-4">
          <p className="section-label mb-2">BetMATE brain</p>
          <div className="rounded-lg border border-[#00DEB8]/35 bg-[#00DEB8]/8 p-3">
            <div className="mb-2 flex items-center gap-2">
              <Bot className="h-5 w-5 text-[#00B899]" />
              <p className="font-display font-bold text-[#111827]">Ask Baz about the board</p>
            </div>
            <p className="text-sm leading-6 text-[#6B7280]">Use Baz when a move, team-news flag or market gap needs explaining.</p>
          </div>
        </div>

        <div className="rounded-xl border border-[#E2E8F0] bg-white p-4">
          <p className="section-label mb-2">Legend</p>
          <div className="space-y-2 text-sm text-[#4B5563]">
            <p className="flex gap-2"><Flame className="mt-0.5 h-4 w-4 text-[#F97316]" />Hot move means the price has shortened materially from open.</p>
            <p className="flex gap-2"><LineChart className="mt-0.5 h-4 w-4 text-[#00B899]" />Best gap shows the spread between available prices.</p>
            <p className="flex gap-2"><AlertTriangle className="mt-0.5 h-4 w-4 text-amber-600" />Team news remains a monitor until confirmed.</p>
          </div>
        </div>
      </div>
    </aside>
  );
}

function CompletedCard({ game, market }: { game: Game; market: MarketTab }) {
  const entries = bookmakerEntries(game, market);
  const displayEntries = entries.length > 0 ? entries : bookmakerEntries(game, 'H2H');
  const cols = Math.min(displayEntries.length, 5);
  const lineAware = market !== 'H2H' && entries.length > 0;

  const bestHome = comparableBest(displayEntries, 'home', lineAware);
  const bestAway = comparableBest(displayEntries, 'away', lineAware);
  const homeLabel = market === 'Totals' ? 'Over' : game.homeShort;
  const awayLabel = market === 'Totals' ? 'Under' : game.awayShort;

  return (
    <article className="overflow-hidden rounded-xl border border-[#E2E8F0] bg-white opacity-60">
      <div className="flex items-center justify-between gap-2 border-b border-[#E2E8F0] px-4 py-3">
        <div className="min-w-0">
          <p className="text-[10px] font-mono uppercase tracking-widest text-[#9CA3AF]">{game.kickoffTime}</p>
          <p className="truncate font-display text-sm font-bold text-[#111827] sm:text-base">
            {game.homeShort} <span className="text-[10px] font-mono font-black text-[#9CA3AF]">vs</span> {game.awayShort}
          </p>
        </div>
        <span className="shrink-0 rounded bg-[#F0F2F5] px-2 py-1 text-[10px] font-mono font-bold uppercase tracking-widest text-[#9CA3AF]">Kicked off</span>
      </div>

      {displayEntries.length > 0 && (
        <>
          {/* Mobile: compact horizontal scroll tiles */}
          <div className="sm:hidden border-t border-[#E2E8F0] px-3 py-3">
            <div className="mb-1.5 flex items-center gap-1.5 text-[10px] font-mono font-bold text-[#9CA3AF]">
              <span>{homeLabel}</span><span className="text-[#D1D5DB]">/</span><span>{awayLabel}</span>
            </div>
            <div className="flex gap-3 overflow-x-auto no-scrollbar">
              {displayEntries.slice(0, cols).map((entry) => {
                const meta = BOOKMAKER_META[entry.key] ?? { abbr: entry.key.slice(0, 3).toUpperCase() };
                return (
                  <div key={entry.key} className="shrink-0 flex flex-col items-center gap-1 min-w-[40px]">
                    <span className="text-[8px] font-mono font-black uppercase tracking-wide text-[#9CA3AF]">{meta.abbr}</span>
                    <span className={`text-[12px] font-mono font-bold tabular-nums ${entry.home.price === bestHome.price && (!lineAware || entry.home.point === bestHome.point) ? 'text-[#00866F]' : 'text-[#9CA3AF]'}`}>
                      {entry.home.price > 0 ? entry.home.price.toFixed(2) : '—'}
                    </span>
                    <span className={`text-[12px] font-mono font-bold tabular-nums ${entry.away.price === bestAway.price && (!lineAware || entry.away.point === bestAway.point) ? 'text-[#00866F]' : 'text-[#9CA3AF]'}`}>
                      {entry.away.price > 0 ? entry.away.price.toFixed(2) : '—'}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
          {/* Desktop: full grid */}
          <div className="hidden sm:block overflow-x-auto">
            <div className="min-w-[480px]" style={{ display: 'grid', gridTemplateColumns: `minmax(100px,1fr) repeat(${cols}, minmax(72px,1fr))` }}>
              <div className="border-t border-r border-[#E2E8F0] bg-[#F8FAFC] px-3 py-2 text-[10px] font-mono uppercase tracking-widest text-[#9CA3AF]">Selection</div>
              {displayEntries.slice(0, cols).map((entry) => {
                const meta = BOOKMAKER_META[entry.key] ?? { abbr: entry.key.slice(0, 3).toUpperCase() };
                return <div key={entry.key} className="border-t border-r border-[#E2E8F0] bg-[#FBFCFE] px-2 py-2 text-center text-[10px] font-mono font-bold text-[#9CA3AF] last:border-r-0">{meta.abbr}</div>;
              })}

              <div className="border-t border-r border-[#E2E8F0] px-3 py-2 text-xs font-bold text-[#6B7280]">{homeLabel}</div>
              {displayEntries.slice(0, cols).map((entry) => (
                <div key={`${entry.key}-h`} className={`border-t border-r border-[#E2E8F0] px-2 py-2 text-center text-sm font-mono font-bold last:border-r-0 ${entry.home.price === bestHome.price && (!lineAware || entry.home.point === bestHome.point) ? 'text-[#00866F]' : 'text-[#9CA3AF]'}`}>
                  {entry.home.price > 0 ? entry.home.price.toFixed(2) : '—'}
                </div>
              ))}

              <div className="border-t border-r border-[#E2E8F0] px-3 py-2 text-xs font-bold text-[#6B7280]">{awayLabel}</div>
              {displayEntries.slice(0, cols).map((entry) => (
                <div key={`${entry.key}-a`} className={`border-t border-r border-[#E2E8F0] px-2 py-2 text-center text-sm font-mono font-bold last:border-r-0 ${entry.away.price === bestAway.price && (!lineAware || entry.away.point === bestAway.point) ? 'text-[#00866F]' : 'text-[#9CA3AF]'}`}>
                  {entry.away.price > 0 ? entry.away.price.toFixed(2) : '—'}
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </article>
  );
}

function CompletedSection({ games, market }: { games: Game[]; market: MarketTab }) {
  const [open, setOpen] = useState(false);
  if (games.length === 0) return null;

  return (
    <div className="mt-4">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between rounded-xl border border-[#E2E8F0] bg-white px-4 py-3 text-left transition-colors hover:border-[#CBD5E1]"
      >
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs font-bold uppercase tracking-widest text-[#6B7280]">Completed</span>
          <span className="rounded-full bg-[#F0F2F5] px-2 py-0.5 text-[10px] font-mono font-bold text-[#9CA3AF]">{games.length}</span>
        </div>
        <ChevronDown className={`h-4 w-4 text-[#9CA3AF] transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && (
        <div className="mt-2 space-y-2">
          {games.map((game) => <CompletedCard key={game.id} game={game} market={market} />)}
        </div>
      )}
    </div>
  );
}

function OddsBoard({
  activeSport,
  market,
  games,
  loading,
  error,
  movements,
  expandedGameId,
  onToggleDetails,
  onAskBaz,
  bviData,
  homeAwayValueData,
  teamNewsData,
}: {
  activeSport: Sport;
  market: MarketTab;
  games: Game[];
  loading: boolean;
  error: string | null;
  movements: MovementMap;
  expandedGameId: string | null;
  onToggleDetails: (gameId: string) => void;
  onAskBaz: (gameId: string) => void;
  bviData?: BviMap;
  homeAwayValueData?: HomeAwayValueMap;
  teamNewsData?: TeamNewsMap;
}) {
  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center rounded-xl border border-[#E2E8F0] bg-white py-24">
        <span className="font-mono text-sm uppercase tracking-widest text-[#9CA3AF] animate-pulse">Fetching odds...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center rounded-xl border border-red-200 bg-white py-24 text-center">
        <span className="font-mono text-sm uppercase tracking-widest text-red-500">{error}</span>
      </div>
    );
  }

  if (games.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center rounded-xl border border-[#E2E8F0] bg-white py-24 text-center">
        <span className="font-mono text-sm uppercase tracking-widest text-[#9CA3AF]">No {activeSport} games available</span>
        <span className="mt-2 font-mono text-[11px] text-[#9CA3AF]">Check back closer to game day</span>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {games.map((game) => (
        <OddsBoardCard
          key={game.id}
          game={game}
          market={market}
          movements={movements}
          expanded={expandedGameId === game.id}
          onToggleDetails={() => onToggleDetails(game.id)}
          onAskBaz={() => onAskBaz(game.id)}
          bviHomeEntry={bviData?.[game.homeTeam] ?? null}
          bviAwayEntry={bviData?.[game.awayTeam] ?? null}
          homeAwayHomeEntry={homeAwayValueData?.[game.homeTeam] ?? null}
          homeAwayAwayEntry={homeAwayValueData?.[game.awayTeam] ?? null}
          teamNewsHomeEntry={teamNewsData?.[game.homeTeam] ?? null}
          teamNewsAwayEntry={teamNewsData?.[game.awayTeam] ?? null}
        />
      ))}
    </div>
  );
}

function OddsPageContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [activeSport, setActiveSport] = useState<Sport>('NRL');
  const [market, setMarket] = useState<MarketTab>('H2H');
  const [bazOpen, setBazOpen] = useState(false);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [expandedGameId, setExpandedGameId] = useState<string | null>(null);
  const [selectedGameId, setSelectedGameId] = useState<string | null>(null);

  const [nrlGames, setNrlGames] = useState<Game[]>([]);
  const [aflGames, setAflGames] = useState<Game[]>([]);
  const [nrlCompleted, setNrlCompleted] = useState<Game[]>([]);
  const [aflCompleted, setAflCompleted] = useState<Game[]>([]);
  const [movements, setMovements] = useState<MovementMap>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [bviData, setBviData] = useState<BviMap>({});
  const [homeAwayValueData, setHomeAwayValueData] = useState<HomeAwayValueMap>({});
  const [nrlBviData, setNrlBviData] = useState<BviMap>({});
  const [nrlHomeAwayValueData, setNrlHomeAwayValueData] = useState<HomeAwayValueMap>({});
  const [nrlTeamNews, setNrlTeamNews] = useState<TeamNewsMap>({});
  const [aflTeamNews, setAflTeamNews] = useState<TeamNewsMap>({});

  const movementsRef = useRef<MovementMap>({});
  const aflMovRef = useRef<MovementMap>({});

  useEffect(() => {
    try {
      const nrl = localStorage.getItem('BetMATE_nrl_completed');
      if (nrl) setNrlCompleted(JSON.parse(nrl));
    } catch { /* ignore */ }
    try {
      const afl = localStorage.getItem('BetMATE_afl_completed');
      if (afl) setAflCompleted(JSON.parse(afl));
    } catch { /* ignore */ }
  }, []);

  useEffect(() => {
    const sport = searchParams.get('sport')?.toUpperCase();
    setActiveSport(sport === 'AFL' ? 'AFL' : 'NRL');
  }, [searchParams]);

  useEffect(() => {
    const supabase = createClient();
    supabase.auth.getSession().then(({ data }) => {
      setIsLoggedIn(!!data.session);
    });
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_e, session) => {
      setIsLoggedIn(!!session);
    });
    return () => subscription.unsubscribe();
  }, []);

  useEffect(() => {
    if (activeSport !== 'NRL') return;

    function fetchOdds(isInitial = false) {
      if (isInitial) setLoading(true);
      setError(null);
      Promise.all([
        fetch('/api/odds/nrl').then((response) => {
          if (!response.ok) throw new Error(`Failed to load odds (${response.status})`);
          return response.json();
        }),
        fetchOpeningPrices('NRL'),
        fetch('/api/odds/fixture').then((r) => r.ok ? r.json() : { season: null, round: null, games: [] }),
        fetch('/api/referees/nrl').then((r) => r.ok ? r.json() : { records: [] }),
      ])
        .then(async ([events, openingPrices, fixture, refsData]: [OddsApiEvent[], OpeningPriceMap, FixtureData, { records?: unknown[] }]) => {
          const refMap = buildRefMap(refsData.records as Parameters<typeof buildRefMap>[0]);
          const newGames = applyNRLVenues(transformNRL(events), fixture).map((g) => ({
            ...g,
            referee: refMap[g.homeTeam]?.name ?? g.referee,
            refereeBucket: refMap[g.homeTeam]?.bucket ?? g.refereeBucket,
          }));
          const now = new Date();
          const upcoming = newGames.filter((g) => new Date(g.commenceTime) > now);
          const done = newGames.filter((g) => new Date(g.commenceTime) <= now);
          const openingMovements = computeMovementsFromOpening(openingPrices, upcoming);
          const hasLocal = Object.keys(openingMovements).length > 0;
          const resolvedMovements = hasLocal ? openingMovements : await fetchSupabaseMovements();
          movementsRef.current = resolvedMovements;
          setMovements(resolvedMovements);
          try { localStorage.setItem('BetMATE_nrl_odds', JSON.stringify(upcoming)); } catch { /* ignore */ }
          setNrlGames(upcoming);
          if (done.length > 0) {
            setNrlCompleted((prev) => {
              const merged = [...done, ...prev.filter((p) => !done.find((d) => d.id === p.id))].slice(0, 30);
              try { localStorage.setItem('BetMATE_nrl_completed', JSON.stringify(merged)); } catch { /* ignore */ }
              return merged;
            });
          }
        })
        .catch((e) => setError(e.message))
        .finally(() => { if (isInitial) setLoading(false); });
    }

    fetchOdds(true);
    const interval = setInterval(() => fetchOdds(false), 60_000);
    return () => clearInterval(interval);
  }, [activeSport]);

  useEffect(() => {
    if (activeSport !== 'AFL') return;

    function fetchAFL(isInitial = false) {
      if (isInitial) setLoading(true);
      setError(null);
      Promise.all([
        fetch('/api/odds/afl').then((response) => {
          if (!response.ok) throw new Error(`Failed to load odds (${response.status})`);
          return response.json();
        }),
        fetchOpeningPrices('AFL'),
      ])
        .then(async ([events, openingPrices]: [OddsApiEvent[], OpeningPriceMap]) => {
          const newGames = transformAFL(events);
          const now = new Date();
          const upcoming = newGames.filter((g) => new Date(g.commenceTime) > now);
          const done = newGames.filter((g) => new Date(g.commenceTime) <= now);
          const openingMovements = computeMovementsFromOpening(openingPrices, upcoming);
          const hasLocal = Object.keys(openingMovements).length > 0;
          const resolvedMovements = hasLocal ? openingMovements : await fetchSupabaseMovements();
          aflMovRef.current = resolvedMovements;
          setMovements(resolvedMovements);
          try { localStorage.setItem('BetMATE_afl_odds', JSON.stringify(upcoming)); } catch { /* ignore */ }
          setAflGames(upcoming);
          if (done.length > 0) {
            setAflCompleted((prev) => {
              const merged = [...done, ...prev.filter((p) => !done.find((d) => d.id === p.id))].slice(0, 30);
              try { localStorage.setItem('BetMATE_afl_completed', JSON.stringify(merged)); } catch { /* ignore */ }
              return merged;
            });
          }
        })
        .catch((e) => setError(e.message))
        .finally(() => { if (isInitial) setLoading(false); });
    }

    fetchAFL(true);
    const interval = setInterval(() => fetchAFL(false), 60_000);
    return () => clearInterval(interval);
  }, [activeSport]);

  useEffect(() => {
    fetch('/api/afl-bvi')
      .then((r) => r.ok ? r.json() : null)
      .then((data) => { if (data?.teams) setBviData(data.teams); })
      .catch(() => {});
  }, []);

  useEffect(() => {
    fetch('/api/afl-home-away-value')
      .then((r) => r.ok ? r.json() : null)
      .then((data) => { if (data?.teams) setHomeAwayValueData(data.teams); })
      .catch(() => {});
  }, []);

  useEffect(() => {
    fetch('/api/nrl-bvi')
      .then((r) => r.ok ? r.json() : null)
      .then((data) => { if (data?.teams) setNrlBviData(data.teams); })
      .catch(() => {});
  }, []);

  useEffect(() => {
    fetch('/api/nrl-home-away-value')
      .then((r) => r.ok ? r.json() : null)
      .then((data) => { if (data?.teams) setNrlHomeAwayValueData(data.teams); })
      .catch(() => {});
  }, []);

  useEffect(() => {
    fetch('/api/team-news/nrl')
      .then((r) => r.ok ? r.json() : null)
      .then((data) => { if (data?.teams) setNrlTeamNews(data.teams); })
      .catch(() => {});
  }, []);

  useEffect(() => {
    fetch('/api/team-news/afl')
      .then((r) => r.ok ? r.json() : null)
      .then((data) => { if (data?.teams) setAflTeamNews(data.teams); })
      .catch(() => {});
  }, []);


  useEffect(() => {
    setError(null);
    setLoading(true);
    setExpandedGameId(null);
    setSelectedGameId(null);
    setMovements(activeSport === 'NRL' ? movementsRef.current : aflMovRef.current);
  }, [activeSport]);

  function switchSport(sport: Sport) {
    router.replace(`/odds?sport=${sport}`, { scroll: false });
  }

  function askBaz(gameId: string) {
    setSelectedGameId(gameId);
    setBazOpen(true);
  }

  const rawGames = activeSport === 'NRL' ? nrlGames : aflGames;
  const games = rawGames;
  const selectedGame = useMemo(() => games.find((game) => game.id === selectedGameId), [games, selectedGameId]);
  const chatGames = selectedGame ? [selectedGame, ...games.filter((game) => game.id !== selectedGame.id)] : games;

  return (
    <div className="min-h-[calc(100dvh-60px)] bg-[#F0F2F5]">
      <div className="sticky top-[60px] z-30 border-b border-[#E2E8F0] bg-white/95 backdrop-blur">
        <div className="mx-auto max-w-7xl px-4 py-2 sm:px-6 sm:py-3">
          <div className="flex items-center gap-3 xl:justify-between">
            {/* Title — desktop only */}
            <div className="hidden xl:block min-w-0 shrink-0">
              <p className="section-label mb-1">Live odds board</p>
              <h1 className="font-display text-2xl font-extrabold tracking-tight text-[#111827]">Betting Intelligence.</h1>
            </div>
            {/* All tabs in one scrollable row */}
            <div className="flex flex-1 items-center gap-1 overflow-x-auto no-scrollbar xl:flex-none">
              {/* Sport tabs — hidden on mobile (header already has them) */}
              {SPORT_TABS.map((sport) => (
                <button
                  key={sport}
                  onClick={() => switchSport(sport)}
                  className={[
                    'hidden sm:flex h-9 shrink-0 items-center justify-center rounded px-3 text-[11px] font-mono font-bold uppercase tracking-widest transition-colors sm:h-10 sm:px-4',
                    activeSport === sport ? 'bg-[#111827] text-white' : 'border border-[#E2E8F0] bg-white text-[#6B7280] hover:border-[#00DEB8]/60',
                  ].join(' ')}
                >
                  {sport}
                </button>
              ))}
              <div className="hidden sm:block mx-1 h-5 w-px shrink-0 bg-[#E2E8F0]" />
              {MARKET_TABS.map((item) => (
                <button
                  key={item}
                  onClick={() => setMarket(item)}
                  className={[
                    'h-9 shrink-0 rounded px-3 text-[11px] font-mono font-bold uppercase tracking-widest transition-colors sm:h-10 sm:px-4',
                    market === item ? 'bg-[#00DEB8] text-black' : 'border border-[#E2E8F0] bg-white text-[#6B7280] hover:border-[#00DEB8]/60',
                  ].join(' ')}
                >
                  {item}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      <main className="mx-auto grid max-w-7xl gap-5 px-4 py-5 pb-28 sm:px-6 xl:grid-cols-[1fr_320px]">
        <div className="min-w-0">
          <OddsBoard
            activeSport={activeSport}
            market={market}
            games={games}
            loading={loading}
            error={error}
            movements={movements}
            expandedGameId={expandedGameId}
            onToggleDetails={(gameId) => setExpandedGameId((current) => current === gameId ? null : gameId)}
            onAskBaz={askBaz}
            bviData={activeSport === 'AFL' ? bviData : nrlBviData}
            homeAwayValueData={activeSport === 'AFL' ? homeAwayValueData : nrlHomeAwayValueData}
            teamNewsData={activeSport === 'NRL' ? nrlTeamNews : aflTeamNews}
          />
          <CompletedSection
            games={activeSport === 'NRL' ? nrlCompleted : aflCompleted}
            market={market}
          />
        </div>
        <BoardSummary games={games} market={market} movements={movements} />
      </main>

      <button
        onClick={() => setBazOpen(true)}
        aria-label="Open Baz"
        className={[
          'fixed bottom-6 right-5 z-40 flex h-14 w-14 items-center justify-center rounded-full bg-[#00DEB8] shadow-[0_10px_35px_rgba(0,222,184,0.35)] transition-all duration-200 hover:bg-[#00C9A6]',
          bazOpen ? 'pointer-events-none scale-90 opacity-0' : 'scale-100 opacity-100',
        ].join(' ')}
      >
        <MessageCircle className="h-6 w-6 text-black" strokeWidth={2} />
      </button>

      <div
        onClick={() => setBazOpen(false)}
        className={[
          'fixed inset-0 z-40 bg-black/40 transition-opacity duration-300',
          bazOpen ? 'opacity-100' : 'pointer-events-none opacity-0',
        ].join(' ')}
      />

      <div
        className={[
          'fixed inset-x-0 bottom-0 z-50 flex flex-col rounded-t-2xl border-t border-[#E2E8F0] bg-white shadow-xl transition-transform duration-300 ease-out lg:hidden',
          bazOpen ? 'translate-y-0' : 'translate-y-full',
        ].join(' ')}
        style={{ height: '78vh' }}
      >
        <div className="flex shrink-0 justify-center pt-3 pb-1">
          <div className="h-1 w-10 rounded-full bg-[#E2E8F0]" />
        </div>
        <ChatPanel
          games={chatGames}
          userPlan="free"
          isLoggedIn={isLoggedIn}
          onClose={() => setBazOpen(false)}
          className="min-h-0 flex-1"
        />
      </div>

      <div
        className={[
          'fixed top-[60px] right-0 z-50 hidden w-[420px] flex-col border-l border-[#E2E8F0] bg-white shadow-2xl transition-transform duration-300 ease-out lg:flex',
          bazOpen ? 'translate-x-0' : 'translate-x-full',
        ].join(' ')}
        style={{ height: 'calc(100dvh - 60px)' }}
      >
        <div className="flex items-center justify-between border-b border-[#E2E8F0] px-4 py-3">
          <div>
            <p className="font-display font-bold text-[#111827]">Baz</p>
            <p className="text-[10px] font-mono uppercase tracking-widest text-[#9CA3AF]">
              {selectedGame ? `${selectedGame.homeShort} vs ${selectedGame.awayShort}` : 'BetMATE AI betting brain'}
            </p>
          </div>
          <button onClick={() => setBazOpen(false)} aria-label="Close Baz" className="rounded-md border border-[#E2E8F0] p-2 text-[#6B7280] hover:text-[#111827]">
            <X className="h-4 w-4" />
          </button>
        </div>
        <ChatPanel
          games={chatGames}
          userPlan="free"
          isLoggedIn={isLoggedIn}
          onClose={() => setBazOpen(false)}
          className="min-h-0 flex-1"
        />
      </div>
    </div>
  );
}

export default function OddsPage() {
  return (
    <Suspense fallback={null}>
      <OddsPageContent />
    </Suspense>
  );
}
