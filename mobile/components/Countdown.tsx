import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { C } from '../constants/colors';

export default function Countdown({ commenceTime }: { commenceTime: string }) {
  const [label, setLabel] = useState('');
  const [isLive, setIsLive] = useState(false);
  const [urgency, setUrgency] = useState<'normal' | 'soon' | 'imminent'>('normal');

  useEffect(() => {
    function tick() {
      const ms = new Date(commenceTime).getTime() - Date.now();
      if (ms <= 0) {
        setIsLive(true);
        setLabel('LIVE');
        return;
      }
      setIsLive(false);
      const d = Math.floor(ms / 86400000);
      const h = Math.floor((ms % 86400000) / 3600000);
      const m = Math.floor((ms % 3600000) / 60000);
      const s = Math.floor((ms % 60000) / 1000);
      if (ms <= 60 * 60_000) setUrgency('imminent');
      else if (ms <= 2 * 3600_000) setUrgency('soon');
      else setUrgency('normal');
      if (d > 0) setLabel(`${d}d ${h}h ${m}m`);
      else if (h > 0) setLabel(`${h}h ${m}m ${s}s`);
      else setLabel(`${m}m ${s}s`);
    }
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [commenceTime]);

  if (!label) return null;

  if (isLive) {
    return (
      <View style={styles.liveRow}>
        <View style={styles.liveDot} />
        <Text style={styles.liveText}>LIVE</Text>
      </View>
    );
  }

  const color =
    urgency === 'imminent' ? C.red :
    urgency === 'soon' ? C.orange :
    C.textMuted;

  return (
    <Text style={[styles.countdown, { color }]}>
      {label}
    </Text>
  );
}

const styles = StyleSheet.create({
  liveRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  liveDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: C.accent,
  },
  liveText: {
    color: C.accent,
    fontSize: 10,
    fontWeight: '700',
    letterSpacing: 1,
  },
  countdown: {
    fontSize: 11,
    fontWeight: '600',
    letterSpacing: 0.5,
  },
});
