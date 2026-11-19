import React, { useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { Ionicons } from '@expo/vector-icons';
import { SafeAreaProvider, SafeAreaView } from 'react-native-safe-area-context';
import { DashboardScreen } from './src/screens/DashboardScreen';
import { InboxScreen } from './src/screens/InboxScreen';
import { SettingsScreen } from './src/screens/SettingsScreen';
import { VerifyScreen } from './src/screens/VerifyScreen';
import { ScamShieldProvider } from './src/store/ScamShieldContext';

type Tab = 'inbox' | 'verify' | 'dashboard' | 'settings';

const TABS: { key: Tab; label: string; icon: keyof typeof Ionicons.glyphMap }[] = [
  { key: 'inbox', label: 'Mesaje', icon: 'chatbubbles' },
  { key: 'verify', label: 'Verifică', icon: 'shield-checkmark' },
  { key: 'dashboard', label: 'Tablou', icon: 'stats-chart' },
  { key: 'settings', label: 'Setări', icon: 'settings' },
];

function MainShell() {
  const [tab, setTab] = useState<Tab>('inbox');

  return (
    <SafeAreaView style={styles.root} edges={['top', 'bottom']}>
      <StatusBar style="dark" />
      <View style={styles.body}>
        {tab === 'inbox' ? <InboxScreen /> : null}
        {tab === 'verify' ? <VerifyScreen onOpenInbox={() => setTab('inbox')} /> : null}
        {tab === 'dashboard' ? <DashboardScreen onOpenInbox={() => setTab('inbox')} /> : null}
        {tab === 'settings' ? <SettingsScreen /> : null}
      </View>

      <View style={styles.tabBar}>
        {TABS.map((t) => {
          const active = tab === t.key;
          return (
            <Pressable key={t.key} style={styles.tabBtn} onPress={() => setTab(t.key)}>
              <Ionicons name={t.icon} size={22} color={active ? '#2563EB' : '#64748B'} />
              <Text style={[styles.tabLabel, active && styles.tabLabelActive]}>{t.label}</Text>
            </Pressable>
          );
        })}
      </View>
    </SafeAreaView>
  );
}

export default function App() {
  return (
    <SafeAreaProvider>
      <ScamShieldProvider>
        <MainShell />
      </ScamShieldProvider>
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#FFFFFF' },
  body: { flex: 1, backgroundColor: '#F8FAFC' },
  tabBar: {
    flexDirection: 'row',
    backgroundColor: '#FFFFFF',
    borderTopWidth: 1,
    borderTopColor: '#E2E8F0',
    paddingTop: 6,
    paddingBottom: 6,
  },
  tabBtn: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 2, paddingVertical: 4 },
  tabLabel: { fontSize: 12, fontWeight: '600', color: '#64748B' },
  tabLabelActive: { color: '#2563EB', fontWeight: '800' },
});
