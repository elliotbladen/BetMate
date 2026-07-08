import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  View, Text, StyleSheet, FlatList, Pressable, ActivityIndicator,
  SafeAreaView, RefreshControl,
} from 'react-native';
import { useRouter } from 'expo-router';
import { C } from '../../constants/colors';
import { fetchNRL, fetchAFL, fetchMovements } from '../../lib/api';
import type { ParsedGame } from '../../lib/oddsParser';
import GameCard from '../../components/GameCard';

type Sport = 'NRL' | 'AFL';
type Market = 'H2H' | 'HANDICAP' | 'TOTALS';

export default function OddsScreen() {
  const router = useRouter();
  const [sport, setSport] = useState<Sport>('NRL');
  const [market, setMarket] = useState<Market>('H2H');
  const [games, setGames] = useState<ParsedGame[]>([]);
  const [movements, setMovements] = useState<Record<string, { direction: 'up' | 'down'; changePct: number }>>({});
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const load = useCallback(async (showLoading = true) => {
    if (showLoading) setLoading(true);
    setError(null);
    try {
      const [evs, movs] = await Promise.all([
        sport === 'NRL' ? fetchNRL() : fetchAFL(),
        fetchMovements(),
      ]);
      const now = Date.now();
      setGames(evs.filter((g) => new Date(g.commenceTime).getTime() > now));
      setMovements(movs);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load odds');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [sport]);

  useEffect(() => {
    load(true);
    intervalRef.current = setInterval(() => load(false), 60_000);
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [load]);

  const onRefresh = () => {
    setRefreshing(true);
    load(false);
  };

  const goToBaz = (game: ParsedGame) => {
    router.push({ pathname: '/baz', params: { gameId: game.id, home: game.homeTeam, away: game.awayTeam } });
  };

  return (
    <SafeAreaView style={styles.safe}>
      {/* Header */}
      <View style={styles.header}>
        <View style={styles.titleRow}>
          <Text style={styles.logo}>Bet<Text style={styles.logoAccent}>MATE</Text></Text>
          <Text style={styles.tagline}>Betting Intelligence</Text>
        </View>

        {/* Sport toggle */}
        <View style={styles.sportRow}>
          {(['NRL', 'AFL'] as Sport[]).map((s) => (
            <Pressable key={s} onPress={() => setSport(s)} style={[styles.sportBtn, sport === s && styles.sportBtnActive]}>
              <Text style={[styles.sportBtnText, sport === s && styles.sportBtnTextActive]}>{s}</Text>
            </Pressable>
          ))}
        </View>

        {/* Market tabs */}
        <View style={styles.marketRow}>
          {(['H2H', 'HANDICAP', 'TOTALS'] as Market[]).map((m) => (
            <Pressable key={m} onPress={() => setMarket(m)} style={[styles.marketBtn, market === m && styles.marketBtnActive]}>
              <Text style={[styles.marketBtnText, market === m && styles.marketBtnTextActive]}>{m}</Text>
            </Pressable>
          ))}
        </View>
      </View>

      {/* Content */}
      {loading ? (
        <View style={styles.center}>
          <ActivityIndicator color={C.accent} size="large" />
          <Text style={styles.loadingText}>Fetching odds...</Text>
        </View>
      ) : error ? (
        <View style={styles.center}>
          <Text style={styles.errorText}>{error}</Text>
          <Pressable onPress={() => load(true)} style={styles.retryBtn}>
            <Text style={styles.retryText}>Retry</Text>
          </Pressable>
        </View>
      ) : (
        <FlatList
          data={games}
          keyExtractor={(g) => g.id}
          contentContainerStyle={styles.list}
          showsVerticalScrollIndicator={false}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={C.accent} />
          }
          ListEmptyComponent={
            <View style={styles.center}>
              <Text style={styles.emptyText}>No {sport} games available</Text>
              <Text style={styles.emptySubText}>Check back closer to game day</Text>
            </View>
          }
          renderItem={({ item }) => (
            <GameCard
              game={item}
              movements={movements}
              onAskBaz={() => goToBaz(item)}
            />
          )}
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: C.bg,
  },
  header: {
    backgroundColor: C.bg,
    borderBottomWidth: 1,
    borderBottomColor: C.tabBarBorder,
    paddingHorizontal: 16,
    paddingTop: 8,
    paddingBottom: 10,
    gap: 10,
  },
  titleRow: {
    flexDirection: 'row',
    alignItems: 'baseline',
    gap: 8,
  },
  logo: {
    color: C.white,
    fontSize: 22,
    fontWeight: '900',
    letterSpacing: -0.5,
  },
  logoAccent: {
    color: C.accent,
  },
  tagline: {
    color: C.textMuted,
    fontSize: 10,
    fontWeight: '600',
    letterSpacing: 1,
    textTransform: 'uppercase',
  },
  sportRow: {
    flexDirection: 'row',
    gap: 6,
  },
  sportBtn: {
    paddingHorizontal: 16,
    paddingVertical: 7,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: C.cardBorder,
    backgroundColor: 'transparent',
  },
  sportBtnActive: {
    backgroundColor: C.accent,
    borderColor: C.accent,
  },
  sportBtnText: {
    color: C.textMuted,
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 1,
  },
  sportBtnTextActive: {
    color: '#000',
  },
  marketRow: {
    flexDirection: 'row',
    gap: 6,
  },
  marketBtn: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: C.cardBorder,
  },
  marketBtnActive: {
    backgroundColor: C.card,
    borderColor: C.accent,
  },
  marketBtnText: {
    color: C.textMuted,
    fontSize: 10,
    fontWeight: '700',
    letterSpacing: 0.8,
  },
  marketBtnTextActive: {
    color: C.accent,
  },
  list: {
    padding: 14,
    paddingBottom: 30,
  },
  center: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 10,
    padding: 40,
  },
  loadingText: {
    color: C.textMuted,
    fontSize: 12,
    letterSpacing: 1,
    textTransform: 'uppercase',
    marginTop: 12,
  },
  errorText: {
    color: C.red,
    fontSize: 13,
    textAlign: 'center',
    letterSpacing: 0.3,
  },
  retryBtn: {
    backgroundColor: C.accent,
    paddingHorizontal: 20,
    paddingVertical: 9,
    borderRadius: 8,
    marginTop: 6,
  },
  retryText: {
    color: '#000',
    fontSize: 12,
    fontWeight: '800',
    letterSpacing: 0.5,
  },
  emptyText: {
    color: C.textSecondary,
    fontSize: 14,
    fontWeight: '600',
    textAlign: 'center',
  },
  emptySubText: {
    color: C.textMuted,
    fontSize: 12,
    textAlign: 'center',
  },
});
