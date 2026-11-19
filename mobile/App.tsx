import React, { useEffect, useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { Ionicons } from '@expo/vector-icons';
import { SafeAreaProvider, SafeAreaView } from 'react-native-safe-area-context';
import { DashboardScreen } from './src/screens/DashboardScreen';
import { InboxScreen } from './src/screens/InboxScreen';
import { SettingsScreen } from './src/screens/SettingsScreen';
import { VerifyScreen } from './src/screens/VerifyScreen';
import { ScamShieldProvider } from './src/store/ScamShieldContext';
import { LoginScreen } from './src/screens/LoginScreen';
import { AudioScreen } from './src/screens/AudioScreen';
import { UserInfo, loadStoredUser, logout } from './src/auth';

type Tab = 'inbox' | 'verify' | 'dashboard' | 'audio' | 'settings';

const TABS: { key: Tab; label: string; icon: keyof typeof Ionicons.glyphMap }[] = [
  { key: 'inbox', label: 'Mesaje', icon: 'chatbubbles' },
  { key: 'verify', label: 'Verifică', icon: 'shield-checkmark' },
  { key: 'dashboard', label: 'Tablou', icon: 'stats-chart' },
  { key: 'audio', label: 'Audio', icon: 'volume-high' },
  { key: 'settings', label: 'Setări', icon: 'settings' },
];

function MainShell({ user, onLogout }: { user: UserInfo; onLogout: () => void }) {
  const [tab, setTab] = useState<Tab>('inbox');

  return (
    <SafeAreaView style={styles.root} edges={['top', 'bottom']}>
      <StatusBar style="dark" />
      <View style={styles.userBar}>
        <Ionicons name="person-circle" size={22} color="#334155" />
        <Text style={styles.userName} numberOfLines={1}>
          {user.display_name || user.username}
        </Text>
        <View style={[styles.role, user.role === 'admin' ? styles.roleAdmin : styles.roleUser]}>
          <Text style={styles.roleText}>{user.role.toUpperCase()}</Text>
        </View>
        <Pressable onPress={onLogout} style={styles.logout} accessibilityRole="button">
          <Ionicons name="log-out-outline" size={20} color="#DC2626" />
          <Text style={styles.logoutText}>Ieșire</Text>
        </Pressable>
      </View>
      <View style={styles.body}>
        {tab === 'inbox' ? <InboxScreen /> : null}
        {tab === 'verify' ? <VerifyScreen onOpenInbox={() => setTab('inbox')} /> : null}
        {tab === 'dashboard' ? <DashboardScreen onOpenInbox={() => setTab('inbox')} /> : null}
        {tab === 'audio' ? <AudioScreen /> : null}
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
  const [user, setUser] = useState<UserInfo | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    loadStoredUser().then((u) => {
      setUser(u);
      setReady(true);
    });
  }, []);

  async function handleLogout() {
    await logout();
    setUser(null);
  }

  return (
    <SafeAreaProvider>
      {!ready ? (
        <SafeAreaView style={[styles.root, styles.center]}>
          <ActivityIndicator size="large" color="#2563EB" />
        </SafeAreaView>
      ) : user ? (
        // Keyed by user: logging out / switching account resets the in-memory scenarios and results.
        <ScamShieldProvider key={user.id}>
          <MainShell user={user} onLogout={handleLogout} />
        </ScamShieldProvider>
      ) : (
        <SafeAreaView style={styles.root} edges={['top', 'bottom']}>
          <StatusBar style="dark" />
          <LoginScreen onLoggedIn={setUser} />
        </SafeAreaView>
      )}
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#FFFFFF' },
  center: { alignItems: 'center', justifyContent: 'center' },
  userBar: {
    flexDirection: 'row', alignItems: 'center', gap: 8, paddingHorizontal: 14, paddingVertical: 8,
    borderBottomWidth: 1, borderBottomColor: '#E2E8F0', backgroundColor: '#FFFFFF',
  },
  userName: { flex: 1, fontSize: 17, fontWeight: '700', color: '#0F172A' },
  role: { paddingHorizontal: 8, paddingVertical: 2, borderRadius: 999 },
  roleAdmin: { backgroundColor: '#FEF3C7' },
  roleUser: { backgroundColor: '#DBEAFE' },
  roleText: { fontSize: 12, fontWeight: '800', color: '#1E293B' },
  logout: { flexDirection: 'row', alignItems: 'center', gap: 4, paddingVertical: 4, paddingLeft: 6 },
  logoutText: { fontSize: 16, fontWeight: '700', color: '#DC2626' },
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
