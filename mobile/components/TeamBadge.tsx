import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { getTeamMeta } from '../lib/teams';

export default function TeamBadge({ name, size = 'md' }: { name: string; size?: 'sm' | 'md' | 'lg' }) {
  const meta = getTeamMeta(name);
  const dim = size === 'sm' ? 28 : size === 'lg' ? 44 : 36;
  const font = size === 'sm' ? 8 : size === 'lg' ? 11 : 9;

  if (!meta) return null;

  return (
    <View
      style={[
        styles.badge,
        {
          width: dim,
          height: dim,
          backgroundColor: meta.primary,
          borderColor: meta.secondary + '44',
        },
      ]}
    >
      <Text style={[styles.text, { color: meta.secondary, fontSize: font }]}>{meta.abbr}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    borderRadius: 6,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  text: {
    fontWeight: '900',
    letterSpacing: 0.5,
  },
});
