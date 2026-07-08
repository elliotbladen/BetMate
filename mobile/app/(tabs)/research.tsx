import React from 'react';
import { View, Text, StyleSheet, ScrollView, SafeAreaView, Pressable, Linking } from 'react-native';
import { C } from '../../constants/colors';

const CLV_DATA = [
  { period: 'NRL R8–R11', clv: '+7.94%', sport: 'NRL', note: 'Running CLV — rules model' },
  { period: 'AFL R8–R9',  clv: '+0.72%', sport: 'AFL', note: 'Running CLV — rules model' },
];

const MODEL_NOTES = [
  { label: 'NRL H2H home bias',     detail: 'Rules overrates home teams +9–11% vs market. ML shadow much better (+1–6%).' },
  { label: 'AFL totals',            detail: 'Rules model underprices AFL totals by 8–25pts. Multiplicative formula fix pending.' },
  { label: 'AFL home advantage',    detail: 'Recalibrating — home_advantage_points zeroed pending evidence-based value (4–6 pts expected).' },
];

const RECENT = [
  { round: 'NRL R12', signal: 'Cowboys vs Rabbitohs: triple matrix confluence → Cowboys. Bet signal.', outcome: 'Pending CLV' },
  { round: 'NRL R12', signal: 'Bulldogs vs Storm: handicap triple confluence → Bulldogs cover. H2H conflicted.', outcome: 'Pending CLV' },
  { round: 'AFL R11', signal: 'Cats/Swans UNDERS — ML 158 vs rules 209, 51pt gap.', outcome: 'Pending CLV' },
  { round: 'AFL R11', signal: 'Giants cover vs Lions. Kangaroos cover vs Suns.', outcome: 'Pending CLV' },
];

export default function ResearchScreen() {
  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.header}>
        <Text style={styles.logo}>Bet<Text style={styles.logoAccent}>MATE</Text></Text>
        <Text style={styles.pageTitle}>Research</Text>
      </View>

      <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>

        {/* CLV Running */}
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>Closing Line Value — Running</Text>
          {CLV_DATA.map((row) => (
            <View key={row.period} style={styles.card}>
              <View style={styles.cardRow}>
                <View>
                  <Text style={styles.cardTitle}>{row.period}</Text>
                  <Text style={styles.cardSub}>{row.note}</Text>
                </View>
                <Text style={[styles.clv, { color: row.clv.startsWith('+') ? C.accent : C.red }]}>
                  {row.clv}
                </Text>
              </View>
            </View>
          ))}
        </View>

        {/* Model notes */}
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>Model Calibration Notes</Text>
          {MODEL_NOTES.map((n) => (
            <View key={n.label} style={styles.card}>
              <Text style={styles.noteLabel}>{n.label}</Text>
              <Text style={styles.noteDetail}>{n.detail}</Text>
            </View>
          ))}
        </View>

        {/* Recent signals */}
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>Recent Signals</Text>
          {RECENT.map((r, i) => (
            <View key={i} style={styles.card}>
              <View style={styles.roundChip}>
                <Text style={styles.roundChipText}>{r.round}</Text>
              </View>
              <Text style={styles.signalText}>{r.signal}</Text>
              <Text style={styles.outcomeText}>{r.outcome}</Text>
            </View>
          ))}
        </View>

        {/* Link to web */}
        <Pressable
          style={styles.webLink}
          onPress={() => Linking.openURL('https://bet-mate-ten.vercel.app/research')}
        >
          <Text style={styles.webLinkText}>View full research on web →</Text>
        </Pressable>

      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: C.bg,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    paddingHorizontal: 16,
    paddingVertical: 14,
    borderBottomWidth: 1,
    borderBottomColor: C.cardBorder,
  },
  logo: {
    color: C.white,
    fontSize: 20,
    fontWeight: '900',
    letterSpacing: -0.5,
  },
  logoAccent: {
    color: C.accent,
  },
  pageTitle: {
    color: C.textMuted,
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 1.5,
    textTransform: 'uppercase',
  },
  content: {
    padding: 14,
    paddingBottom: 40,
    gap: 20,
  },
  section: {
    gap: 8,
  },
  sectionLabel: {
    color: C.textMuted,
    fontSize: 9,
    fontWeight: '800',
    letterSpacing: 1.5,
    textTransform: 'uppercase',
    marginBottom: 2,
  },
  card: {
    backgroundColor: C.card,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: C.cardBorder,
    padding: 14,
    gap: 6,
  },
  cardRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  cardTitle: {
    color: C.textPrimary,
    fontSize: 13,
    fontWeight: '700',
  },
  cardSub: {
    color: C.textMuted,
    fontSize: 10,
    marginTop: 2,
  },
  clv: {
    fontSize: 22,
    fontWeight: '900',
    letterSpacing: -0.5,
  },
  noteLabel: {
    color: C.textPrimary,
    fontSize: 12,
    fontWeight: '700',
  },
  noteDetail: {
    color: C.textSecondary,
    fontSize: 12,
    lineHeight: 17,
  },
  roundChip: {
    alignSelf: 'flex-start',
    backgroundColor: '#1E1E1E',
    borderRadius: 4,
    paddingHorizontal: 8,
    paddingVertical: 3,
  },
  roundChipText: {
    color: C.accent,
    fontSize: 9,
    fontWeight: '800',
    letterSpacing: 1,
    textTransform: 'uppercase',
  },
  signalText: {
    color: C.textPrimary,
    fontSize: 13,
    lineHeight: 18,
  },
  outcomeText: {
    color: C.textMuted,
    fontSize: 11,
    fontWeight: '600',
    letterSpacing: 0.3,
  },
  webLink: {
    alignSelf: 'center',
    paddingVertical: 12,
    paddingHorizontal: 20,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: C.cardBorder,
  },
  webLinkText: {
    color: C.accent,
    fontSize: 12,
    fontWeight: '700',
    letterSpacing: 0.5,
  },
});
