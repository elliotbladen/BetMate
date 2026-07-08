import { Tabs } from 'expo-router';
import { Text, StyleSheet } from 'react-native';
import { C } from '../../constants/colors';

function TabIcon({ label, active }: { label: string; active: boolean }) {
  const icons: Record<string, string> = {
    Odds: '📊',
    Baz: '🤖',
    Research: '📈',
  };
  return <Text style={{ fontSize: active ? 22 : 20, opacity: active ? 1 : 0.45 }}>{icons[label]}</Text>;
}

export default function TabLayout() {
  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarStyle: styles.tabBar,
        tabBarActiveTintColor: C.accent,
        tabBarInactiveTintColor: C.textMuted,
        tabBarLabelStyle: styles.label,
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: 'Odds',
          tabBarIcon: ({ focused }) => <TabIcon label="Odds" active={focused} />,
        }}
      />
      <Tabs.Screen
        name="baz"
        options={{
          title: 'Baz',
          tabBarIcon: ({ focused }) => <TabIcon label="Baz" active={focused} />,
        }}
      />
      <Tabs.Screen
        name="research"
        options={{
          title: 'Research',
          tabBarIcon: ({ focused }) => <TabIcon label="Research" active={focused} />,
        }}
      />
    </Tabs>
  );
}

const styles = StyleSheet.create({
  tabBar: {
    backgroundColor: C.tabBar,
    borderTopColor: C.tabBarBorder,
    borderTopWidth: 1,
    height: 80,
    paddingBottom: 20,
    paddingTop: 8,
  },
  label: {
    fontSize: 10,
    fontWeight: '700',
    letterSpacing: 0.5,
    marginTop: 2,
  },
});
