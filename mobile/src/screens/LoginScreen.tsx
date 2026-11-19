import React, { useState } from 'react';
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { getStoredApiUrls } from '../api';
import { DEMO_ACCOUNTS, UserInfo, login } from '../auth';

/** Login like the web app (POST /api/auth/login), with one-tap demo accounts from the database. */
export function LoginScreen({ onLoggedIn }: { onLoggedIn: (u: UserInfo) => void }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(u = username.trim(), p = password) {
    if (!u || !p || busy) return;
    setBusy(true);
    setError(null);
    try {
      const { apiBase } = await getStoredApiUrls();
      onLoggedIn(await login(apiBase, u, p));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Autentificarea nu a reușit.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <KeyboardAvoidingView style={styles.flex} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <ScrollView contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
        <View style={styles.logo}>
          <Ionicons name="shield-checkmark" size={40} color="#fff" />
        </View>
        <Text style={styles.title}>Scam Shield</Text>
        <Text style={styles.sub}>Intrați în cont ca să vă verificați mesajele.</Text>

        <Text style={styles.label}>Utilizator</Text>
        <TextInput
          style={styles.input}
          value={username}
          onChangeText={setUsername}
          autoCapitalize="none"
          autoCorrect={false}
          placeholder="ex. user"
          textContentType="username"
        />
        <Text style={styles.label}>Parolă</Text>
        <TextInput
          style={styles.input}
          value={password}
          onChangeText={setPassword}
          secureTextEntry
          placeholder="••••"
          textContentType="password"
          onSubmitEditing={() => submit()}
        />
        {error ? <Text style={styles.error}>{error}</Text> : null}

        <Pressable
          style={[styles.btn, (!username.trim() || !password || busy) && styles.btnDisabled]}
          onPress={() => submit()}
          disabled={!username.trim() || !password || busy}
        >
          {busy ? <ActivityIndicator color="#fff" /> : <Text style={styles.btnText}>Intră în cont</Text>}
        </Pressable>

        <Text style={styles.demoTitle}>Conturi demo (apăsați pentru acces rapid):</Text>
        {DEMO_ACCOUNTS.map((a) => (
          <Pressable key={a.username} style={styles.demo} onPress={() => submit(a.username, a.password)} disabled={busy}>
            <View style={[styles.role, a.role === 'admin' ? styles.roleAdmin : styles.roleUser]}>
              <Text style={styles.roleText}>{a.role.toUpperCase()}</Text>
            </View>
            <View style={styles.flex}>
              <Text style={styles.demoUser}>{a.username}</Text>
              <Text style={styles.demoLabel}>
                {a.label} · parola: {a.password}
              </Text>
            </View>
            <Ionicons name="arrow-forward" size={20} color="#64748B" />
          </Pressable>
        ))}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  container: { padding: 24, paddingTop: 40, gap: 8 },
  logo: {
    alignSelf: 'center', width: 72, height: 72, borderRadius: 36, backgroundColor: '#2563EB',
    alignItems: 'center', justifyContent: 'center', marginBottom: 8,
  },
  title: { fontSize: 28, fontWeight: '800', color: '#0F172A', textAlign: 'center' },
  sub: { fontSize: 18, color: '#475569', textAlign: 'center', marginBottom: 16 },
  label: { fontSize: 18, fontWeight: '700', color: '#0F172A', marginTop: 8 },
  input: {
    borderWidth: 1, borderColor: '#CBD5E1', borderRadius: 12, paddingHorizontal: 14, paddingVertical: 12,
    fontSize: 18, backgroundColor: '#fff', color: '#0F172A',
  },
  error: { fontSize: 18, color: '#DC2626', marginTop: 4 },
  btn: {
    marginTop: 16, backgroundColor: '#2563EB', borderRadius: 14, paddingVertical: 16, alignItems: 'center',
  },
  btnDisabled: { opacity: 0.5 },
  btnText: { color: '#fff', fontSize: 20, fontWeight: '800' },
  demoTitle: { fontSize: 18, fontWeight: '700', color: '#334155', marginTop: 24, marginBottom: 4 },
  demo: {
    flexDirection: 'row', alignItems: 'center', gap: 12, padding: 14, borderRadius: 14,
    backgroundColor: '#fff', borderWidth: 1, borderColor: '#E2E8F0',
  },
  role: { paddingHorizontal: 10, paddingVertical: 4, borderRadius: 999 },
  roleAdmin: { backgroundColor: '#FEF3C7' },
  roleUser: { backgroundColor: '#DBEAFE' },
  roleText: { fontSize: 13, fontWeight: '800', color: '#1E293B' },
  demoUser: { fontSize: 18, fontWeight: '800', color: '#0F172A' },
  demoLabel: { fontSize: 15, color: '#475569' },
});
