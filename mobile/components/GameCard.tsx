import React, { useState } from 'react';
import {
  View, Text, StyleSheet, ScrollView, TouchableOpacity, Image, Pressable,
} from 'react-native';
import { C } from '../constants/colors';
import { BOOKMAKER_META, BOOKMAKER_ORDER, effectivePrice } from '../lib/bookmakers';
import { getTeamMeta } from '../lib/teams';
import TeamBadge from './TeamBadge';
import Countdown from './Countdown';
import type { ParsedGame } from '../lib/oddsParser';

type MarketTab = 'H2H' | 'HANDICAP' | 'TOTALS';
type Movement = { direction: 'up' | 'down'; changePct: number };
type MovementMap = Record<string, Movement>;

interface Props {
  game: ParsedGame;
  movements?: MovementMap;
  onAskBaz?: () => void;
}

function bmKey(game: ParsedGame, tab: MarketTab) {
  if (tab === 'H2H') return 'h2h';
  if (tab === 'HANDICAP') return 'spreads';
  return 'totals';
}

function sortedBookmakers<T>(map: Record<string, T>): [string, T][] {
  return [...Object.entries(map)].sort(([a], [b]) => {
    const ia = BOOKMAKER_ORDER.indexOf(a);
    const ib = BOOKMAKER_ORDER.indexOf(b);
    const na = ia === -1 ? 999 : ia;
    const nb = ib === -1 ? 999 : ib;
    return na - nb;
  });
}

function getBestH2H(game: ParsedGame, side: 'home' | 'away'): number {
  const prices = Object.entries(game.h2h).map(([k, v]) => effectivePrice(k, v[side]));
  return prices.length ? Math.max(...prices) : 0;
}

function MovementArrow({ dir }: { dir: 'up' | 'down' }) {
  return (
    <Text style={{ color: dir === 'down' ? C.orange : C.accent, fontSize: 10, fontWeight: '700' }}>
      {dir === 'up' ? '↑' : '↓'}
    </Text>
  );
}

function BookmakerTile({
  bmk, price, point, isBest, showPoint, movement,
}: {
  bmk: string; price: number; point?: number | null; isBest: boolean; showPoint?: boolean; movement?: Movement;
}) {
  const meta = BOOKMAKER_META[bmk] ?? { abbr: bmk.slice(0, 3).toUpperCase(), name: bmk, domain: bmk };
  const adj = effectivePrice(bmk, price);

  return (
    <View style={[styles.tile, isBest && styles.tileBest]}>
      {movement && (
        <View style={styles.tileArrow}>
          <MovementArrow dir={movement.direction} />
        </View>
      )}
      <Image
        source={{ uri: `https://www.google.com/s2/favicons?domain=${meta.domain}&sz=64` }}
        style={styles.favicon}
      />
      <Text style={styles.tileAbbr}>{meta.abbr}</Text>
      {showPoint && point != null && (
        <Text style={styles.tilePoint}>{point > 0 ? `+${point}` : point}</Text>
      )}
      <Text style={[styles.tilePrice, isBest && styles.tilePriceBest]}>
        ${adj.toFixed(2)}
      </Text>
    </View>
  );
}

function H2HSection({ game, movements }: { game: ParsedGame; movements?: MovementMap }) {
  const entries = sortedBookmakers(game.h2h);
  const bestHome = getBestH2H(game, 'home');
  const bestAway = getBestH2H(game, 'away');

  if (entries.length === 0) {
    return <Text style={styles.unavail}>H2H markets unavailable</Text>;
  }

  return (
    <View style={styles.section}>
      <View style={styles.sideHeader}>
        <TeamBadge name={game.homeTeam} size="sm" />
        <Text style={styles.sideLabel}>{game.homeShort}</Text>
      </View>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.tileScroll} contentContainerStyle={styles.tileRow}>
        {entries.map(([k, v]) => {
          const adj = effectivePrice(k, v.home);
          const mv = movements?.[`${game.id}:h2h:${k}:home`];
          return <BookmakerTile key={k} bmk={k} price={v.home} isBest={adj === bestHome} movement={mv} />;
        })}
      </ScrollView>

      <View style={[styles.sideHeader, { marginTop: 12 }]}>
        <TeamBadge name={game.awayTeam} size="sm" />
        <Text style={styles.sideLabel}>{game.awayShort}</Text>
      </View>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.tileScroll} contentContainerStyle={styles.tileRow}>
        {entries.map(([k, v]) => {
          const adj = effectivePrice(k, v.away);
          const mv = movements?.[`${game.id}:h2h:${k}:away`];
          return <BookmakerTile key={k} bmk={k} price={v.away} isBest={adj === bestAway} movement={mv} />;
        })}
      </ScrollView>
    </View>
  );
}

function HandicapSection({ game, movements }: { game: ParsedGame; movements?: MovementMap }) {
  const entries = sortedBookmakers(game.spreads);
  if (entries.length === 0) return <Text style={styles.unavail}>Handicap markets unavailable</Text>;

  const bestHome = Math.max(...entries.map(([k, v]) => effectivePrice(k, v.home)));
  const bestAway = Math.max(...entries.map(([k, v]) => effectivePrice(k, v.away)));

  return (
    <View style={styles.section}>
      <View style={styles.sideHeader}>
        <TeamBadge name={game.homeTeam} size="sm" />
        <Text style={styles.sideLabel}>{game.homeShort}</Text>
      </View>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.tileScroll} contentContainerStyle={styles.tileRow}>
        {entries.map(([k, v]) => {
          const adj = effectivePrice(k, v.home);
          const mv = movements?.[`${game.id}:spreads:${k}:home`];
          return <BookmakerTile key={k} bmk={k} price={v.home} point={v.homePoint} isBest={adj === bestHome} showPoint movement={mv} />;
        })}
      </ScrollView>

      <View style={[styles.sideHeader, { marginTop: 12 }]}>
        <TeamBadge name={game.awayTeam} size="sm" />
        <Text style={styles.sideLabel}>{game.awayShort}</Text>
      </View>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.tileScroll} contentContainerStyle={styles.tileRow}>
        {entries.map(([k, v]) => {
          const adj = effectivePrice(k, v.away);
          const mv = movements?.[`${game.id}:spreads:${k}:away`];
          return <BookmakerTile key={k} bmk={k} price={v.away} point={v.awayPoint} isBest={adj === bestAway} showPoint movement={mv} />;
        })}
      </ScrollView>
    </View>
  );
}

function TotalsSection({ game, movements }: { game: ParsedGame; movements?: MovementMap }) {
  const entries = sortedBookmakers(game.totals);
  if (entries.length === 0) return <Text style={styles.unavail}>Totals markets unavailable</Text>;

  const line = entries[0]?.[1].point;
  const bestOver = Math.max(...entries.map(([k, v]) => effectivePrice(k, v.over)));
  const bestUnder = Math.max(...entries.map(([k, v]) => effectivePrice(k, v.under)));

  return (
    <View style={styles.section}>
      {line != null && (
        <Text style={styles.totalsLine}>Line: <Text style={styles.totalsLineNum}>{line}</Text></Text>
      )}
      <Text style={styles.sideLabel}>OVER {line}</Text>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.tileScroll} contentContainerStyle={styles.tileRow}>
        {entries.map(([k, v]) => {
          const adj = effectivePrice(k, v.over);
          const mv = movements?.[`${game.id}:totals:${k}:over`];
          return <BookmakerTile key={k} bmk={k} price={v.over} isBest={adj === bestOver} movement={mv} />;
        })}
      </ScrollView>

      <Text style={[styles.sideLabel, { marginTop: 12 }]}>UNDER {line}</Text>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.tileScroll} contentContainerStyle={styles.tileRow}>
        {entries.map(([k, v]) => {
          const adj = effectivePrice(k, v.under);
          const mv = movements?.[`${game.id}:totals:${k}:under`];
          return <BookmakerTile key={k} bmk={k} price={v.under} isBest={adj === bestUnder} movement={mv} />;
        })}
      </ScrollView>
    </View>
  );
}

export default function GameCard({ game, movements, onAskBaz }: Props) {
  const [tab, setTab] = useState<MarketTab>('H2H');
  const homeMetaColor = getTeamMeta(game.homeTeam)?.primary ?? '#111827';
  const awayMetaColor = getTeamMeta(game.awayTeam)?.primary ?? '#111827';

  return (
    <View style={styles.card}>
      {/* Team colour stripe */}
      <View style={styles.stripe}>
        <View style={[styles.stripeHalf, { backgroundColor: homeMetaColor }]} />
        <View style={[styles.stripeHalf, { backgroundColor: awayMetaColor }]} />
      </View>

      {/* Header */}
      <View style={styles.header}>
        <View style={styles.teams}>
          <View style={styles.teamRow}>
            <TeamBadge name={game.homeTeam} size="lg" />
            <View style={styles.teamInfo}>
              <Text style={styles.teamName} numberOfLines={1}>{game.homeTeam}</Text>
              <Text style={styles.teamLabel}>HOME</Text>
            </View>
          </View>
          <View style={styles.vsBlock}>
            <Text style={styles.vs}>VS</Text>
          </View>
          <View style={styles.teamRow}>
            <TeamBadge name={game.awayTeam} size="lg" />
            <View style={styles.teamInfo}>
              <Text style={styles.teamName} numberOfLines={1}>{game.awayTeam}</Text>
              <Text style={styles.teamLabel}>AWAY</Text>
            </View>
          </View>
        </View>

        <View style={styles.meta}>
          <Text style={styles.kickoff}>{game.kickoffTime}</Text>
          <Countdown commenceTime={game.commenceTime} />
        </View>
      </View>

      {/* Market tabs */}
      <View style={styles.tabs}>
        {(['H2H', 'HANDICAP', 'TOTALS'] as MarketTab[]).map((t) => (
          <Pressable key={t} onPress={() => setTab(t)} style={[styles.tabBtn, tab === t && styles.tabBtnActive]}>
            <Text style={[styles.tabText, tab === t && styles.tabTextActive]}>{t}</Text>
          </Pressable>
        ))}
      </View>

      {/* Market content */}
      <View style={styles.content}>
        {tab === 'H2H' && <H2HSection game={game} movements={movements} />}
        {tab === 'HANDICAP' && <HandicapSection game={game} movements={movements} />}
        {tab === 'TOTALS' && <TotalsSection game={game} movements={movements} />}
      </View>

      {/* Footer */}
      <View style={styles.footer}>
        <TouchableOpacity style={styles.bazBtn} onPress={onAskBaz} activeOpacity={0.8}>
          <Text style={styles.bazBtnText}>Ask Baz</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: C.card,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: C.cardBorder,
    marginBottom: 12,
    overflow: 'hidden',
  },
  stripe: {
    height: 4,
    flexDirection: 'row',
  },
  stripeHalf: {
    flex: 1,
  },
  header: {
    padding: 14,
    paddingBottom: 10,
  },
  teams: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 8,
  },
  teamRow: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  teamInfo: {
    flex: 1,
    minWidth: 0,
  },
  teamName: {
    color: C.textPrimary,
    fontSize: 13,
    fontWeight: '700',
    letterSpacing: 0.2,
  },
  teamLabel: {
    color: C.textMuted,
    fontSize: 9,
    fontWeight: '700',
    letterSpacing: 1,
    marginTop: 1,
  },
  vsBlock: {
    paddingHorizontal: 4,
  },
  vs: {
    color: C.textMuted,
    fontSize: 9,
    fontWeight: '900',
    letterSpacing: 2,
  },
  meta: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  kickoff: {
    color: C.textMuted,
    fontSize: 10,
    fontWeight: '500',
    letterSpacing: 0.3,
  },
  tabs: {
    flexDirection: 'row',
    borderTopWidth: 1,
    borderTopColor: C.cardBorder,
  },
  tabBtn: {
    flex: 1,
    paddingVertical: 11,
    alignItems: 'center',
    borderRightWidth: 1,
    borderRightColor: C.cardBorder,
  },
  tabBtnActive: {
    borderBottomWidth: 2,
    borderBottomColor: C.accent,
  },
  tabText: {
    color: C.textMuted,
    fontSize: 10,
    fontWeight: '700',
    letterSpacing: 1.2,
  },
  tabTextActive: {
    color: C.textPrimary,
  },
  content: {
    paddingHorizontal: 14,
    paddingVertical: 12,
  },
  section: {
    gap: 6,
  },
  sideHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginBottom: 4,
  },
  sideLabel: {
    color: C.textSecondary,
    fontSize: 9,
    fontWeight: '700',
    letterSpacing: 1.2,
    textTransform: 'uppercase',
  },
  tileScroll: {
    flexGrow: 0,
  },
  tileRow: {
    flexDirection: 'row',
    gap: 6,
    paddingBottom: 2,
  },
  tile: {
    width: 72,
    paddingVertical: 8,
    paddingHorizontal: 4,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: C.cardBorder,
    backgroundColor: '#161616',
    alignItems: 'center',
    gap: 3,
  },
  tileBest: {
    borderColor: C.orange + '80',
    backgroundColor: C.orange + '0D',
  },
  tileArrow: {
    position: 'absolute',
    top: 4,
    right: 4,
  },
  favicon: {
    width: 22,
    height: 22,
    borderRadius: 4,
  },
  tileAbbr: {
    color: C.textMuted,
    fontSize: 8,
    fontWeight: '700',
    letterSpacing: 0.5,
  },
  tilePoint: {
    color: C.textSecondary,
    fontSize: 10,
    fontWeight: '700',
  },
  tilePrice: {
    color: C.textPrimary,
    fontSize: 15,
    fontWeight: '800',
    letterSpacing: -0.3,
  },
  tilePriceBest: {
    color: C.orange,
  },
  unavail: {
    color: C.textMuted,
    fontSize: 12,
    textAlign: 'center',
    paddingVertical: 20,
    letterSpacing: 0.5,
  },
  totalsLine: {
    color: C.textMuted,
    fontSize: 10,
    marginBottom: 4,
    letterSpacing: 0.3,
  },
  totalsLineNum: {
    color: C.textSecondary,
    fontWeight: '700',
  },
  footer: {
    borderTopWidth: 1,
    borderTopColor: C.cardBorder,
    padding: 12,
  },
  bazBtn: {
    backgroundColor: C.accent,
    borderRadius: 8,
    paddingVertical: 10,
    alignItems: 'center',
  },
  bazBtnText: {
    color: '#000',
    fontSize: 12,
    fontWeight: '800',
    letterSpacing: 0.5,
  },
});
