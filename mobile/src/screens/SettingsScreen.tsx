import React, { useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import * as DocumentPicker from 'expo-document-picker';
import { defaultApiBase, defaultAudioBase, defaultHost, mobileApi } from '../api';
import { useScamShield } from '../store/ScamShieldContext';
import { AudioAuditResult } from '../types';

export function SettingsScreen() {
  const { apiBase, audioBase, health, updateServerUrls, loadValidationSet } = useScamShield();
  const [apiInput, setApiInput] = useState(apiBase);
  const [audioInput, setAudioInput] = useState(audioBase);
  const [checking, setChecking] = useState(false);
  const [audioStatus, setAudioStatus] = useState<string | null>(null);
  const [auditBusy, setAuditBusy] = useState(false);
  const [auditResult, setAuditResult] = useState<AudioAuditResult | null>(null);
  const [auditErr, setAuditErr] = useState<string | null>(null);

  const onSaveUrls = async () => {
    setChecking(true);
    try {
      await updateServerUrls(apiInput, audioInput);
      const ah = await mobileApi.audioHealth(audioInput.trim().replace(/\/+$/, ''));
      setAudioStatus(ah ? `OK (${ah.demo_ready.join(', ') || 'pregătit'})` : 'indisponibil');
    } finally {
      setChecking(false);
    }
  };

  const onResetDetected = async () => {
    const a = defaultApiBase();
    const b = defaultAudioBase();
    setApiInput(a);
    setAudioInput(b);
    await updateServerUrls(a, b);
  };

  const onPickAudio = async () => {
    const res = await DocumentPicker.getDocumentAsync({
      type: ['audio/*', 'video/mp4', '*/*'],
      copyToCacheDirectory: true,
    });
    if (res.canceled || !res.assets?.[0]) return;
    const f = res.assets[0];
    setAuditBusy(true);
    setAuditErr(null);
    setAuditResult(null);
    try {
      const out = await mobileApi.audioAudit(audioBase, {
        uri: f.uri,
        name: f.name,
        mimeType: f.mimeType,
      });
      setAuditResult(out);
    } catch (e) {
      setAuditErr(e instanceof Error ? e.message : 'Verificarea audio nu a reușit.');
    } finally {
      setAuditBusy(false);
    }
  };

  return (
    <ScrollView contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
      <Text style={styles.title}>Setări & Server</Text>

      <View style={styles.card}>
        <Text style={styles.sectionTitle}>Adresă Backend (FastAPI :8000)</Text>
        <Text style={styles.hint}>
          Pe iPhone / Android în Expo Go (aceeași rețea Wi-Fi), folosiți IP-ul calculatorului (detectat automat:{' '}
          {defaultHost()}).
        </Text>
        <TextInput
          style={styles.input}
          value={apiInput}
          onChangeText={setApiInput}
          autoCapitalize="none"
          autoCorrect={false}
        />

        <Text style={styles.sectionTitle}>Adresă Audio Side-Feature (:8002)</Text>
        <TextInput
          style={styles.input}
          value={audioInput}
          onChangeText={setAudioInput}
          autoCapitalize="none"
          autoCorrect={false}
        />

        <View style={styles.btnRow}>
          <Pressable style={styles.primaryBtn} onPress={() => void onSaveUrls()} disabled={checking}>
            {checking ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={styles.primaryBtnText}>Salvează & Testează</Text>
            )}
          </Pressable>
          <Pressable style={styles.secondaryBtn} onPress={() => void onResetDetected()}>
            <Text style={styles.secondaryBtnText}>Auto-detect</Text>
          </Pressable>
        </View>

        <View style={styles.statusBox}>
          <Text style={styles.statusLine}>
            Backend (:8000):{' '}
            {health
              ? `Conectat · model=${health.model_loaded ? 'încărcat' : 'neîncărcat'} · db=${health.db_connected ? 'OK' : 'offline'}`
              : 'Neconectat (aplicația folosește datele locale)'}
          </Text>
          {audioStatus ? <Text style={styles.statusLine}>Serviciu audio (:8002): {audioStatus}</Text> : null}
        </View>

        <Pressable style={styles.secondaryBtn} onPress={() => void loadValidationSet()}>
          <Text style={styles.secondaryBtnText}>Reîncarcă și reanalizează setul de validare</Text>
        </Pressable>
      </View>

      <View style={styles.card}>
        <View style={styles.cardTitleRow}>
          <Ionicons name="mic-outline" size={20} color="#2563EB" />
          <Text style={styles.sectionTitle}>Verificare confidențialitate audio</Text>
        </View>
        <Text style={styles.hint}>
          Verificați dacă o înregistrare audio conține treceri de avioane care pot dezvălui locația (port 8002).
        </Text>
        <Pressable style={styles.primaryBtn} onPress={() => void onPickAudio()} disabled={auditBusy}>
          {auditBusy ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.primaryBtnText}>Alege fișier audio (.wav / .mp3 / .m4a)</Text>
          )}
        </Pressable>
        {auditErr ? <Text style={styles.errText}>{auditErr}</Text> : null}
        {auditResult ? (
          <View style={styles.statusBox}>
            <Text style={styles.statusLine}>
              Risc locație: {auditResult.risk.toUpperCase()} · Avioane detectate: {auditResult.flyovers} · Durată:{' '}
              {auditResult.duration_s.toFixed(1)} s
            </Text>
          </View>
        ) : null}
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: 14, gap: 14, backgroundColor: '#F8FAFC', paddingBottom: 36 },
  title: { fontSize: 22, fontWeight: '800', color: '#0F172A' },
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 14,
    padding: 14,
    borderWidth: 1,
    borderColor: '#E2E8F0',
    gap: 10,
  },
  cardTitleRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  sectionTitle: { fontSize: 15, fontWeight: '800', color: '#0F172A' },
  hint: { fontSize: 13, lineHeight: 19, color: '#64748B' },
  input: {
    borderWidth: 1,
    borderColor: '#CBD5E1',
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 14,
    color: '#0F172A',
  },
  btnRow: { flexDirection: 'row', gap: 8 },
  primaryBtn: {
    flex: 1,
    backgroundColor: '#2563EB',
    borderRadius: 10,
    paddingVertical: 12,
    alignItems: 'center',
    justifyContent: 'center',
  },
  primaryBtnText: { color: '#fff', fontSize: 14, fontWeight: '800' },
  secondaryBtn: {
    borderWidth: 1,
    borderColor: '#CBD5E1',
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 12,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#F8FAFC',
  },
  secondaryBtnText: { color: '#1E293B', fontSize: 14, fontWeight: '700' },
  statusBox: { backgroundColor: '#F1F5F9', borderRadius: 10, padding: 10, gap: 4 },
  statusLine: { fontSize: 13, color: '#334155', fontWeight: '600' },
  errText: { fontSize: 13, color: '#B91C1C', fontWeight: '600' },
});
