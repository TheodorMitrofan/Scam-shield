import React from 'react';
import {
  ActivityIndicator,
  FlatList,
  Pressable,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  TextInput,
  View,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import * as DocumentPicker from 'expo-document-picker';
import { File as ExpoFile } from 'expo-file-system';
import { ScenarioDetailView } from '../components/ScenarioDetailView';
import { VerdictBadge } from '../components/VerdictBadge';
import { CHANNEL_LABEL, parseScenario, senderOf } from '../labels';
import { ChannelFilter, VerdictFilter, useScamShield } from '../store/ScamShieldContext';
import { CHANNELS, Scenario } from '../types';

const CHANNEL_FILTERS: { value: ChannelFilter; label: string }[] = [
  { value: 'all', label: 'Toate' },
  ...CHANNELS.map((c) => ({ value: c, label: CHANNEL_LABEL[c] })),
];

const VERDICT_FILTERS: { value: VerdictFilter; label: string }[] = [
  { value: 'all', label: 'Toate' },
  { value: 'SCAM', label: 'SCAM' },
  { value: 'SUSPICIOUS', label: 'Suspect' },
  { value: 'SAFE', label: 'Sigur' },
];

export function InboxScreen() {
  const {
    filtered,
    results,
    analyzingIds,
    readIds,
    selected,
    selectedResult,
    loading,
    errors,
    apiError,
    saveHistory,
    search,
    channelFilter,
    verdictFilter,
    setSearch,
    setChannelFilter,
    setVerdictFilter,
    setSaveHistory,
    selectScenario,
    loadValidationSet,
    importParsedScenarios,
  } = useScamShield();

  if (selected) {
    return (
      <ScenarioDetailView
        scenario={selected}
        result={selectedResult}
        onBack={() => selectScenario(null)}
      />
    );
  }

  const pickJsonFiles = async () => {
    const res = await DocumentPicker.getDocumentAsync({
      type: ['application/json', 'text/plain', '*/*'],
      multiple: true,
      copyToCacheDirectory: true,
    });
    if (res.canceled || !res.assets?.length) return;
    const parsed: Scenario[] = [];
    const errs: string[] = [];
    for (const asset of res.assets) {
      if (!asset.name.toLowerCase().endsWith('.json')) continue;
      try {
        const text = await new ExpoFile(asset.uri).text();
        const raw = JSON.parse(text);
        const list = Array.isArray(raw) ? raw : [raw];
        list.forEach((it, idx) =>
          parsed.push(parseScenario(it, asset.name.replace(/\.json$/i, '') + (idx ? `-${idx}` : ''))),
        );
      } catch (e) {
        errs.push(`${asset.name}: ${e instanceof Error ? e.message : 'nu poate fi citit'}`);
      }
    }
    if (!parsed.length && !errs.length) errs.push('Nu am găsit niciun fișier .json.');
    await importParsedScenarios(parsed, errs);
  };

  const hasResults = Object.keys(results).length > 0;

  return (
    <View style={styles.root}>
      <View style={styles.header}>
        <View style={styles.brandRow}>
          <Ionicons name="shield-checkmark" size={24} color="#2563EB" />
          <Text style={styles.headerTitle}>Scam Shield</Text>
          <View style={styles.headerActions}>
            <Pressable style={styles.pillBtn} onPress={() => void pickJsonFiles()}>
              <Ionicons name="folder-open-outline" size={16} color="#1E293B" />
              <Text style={styles.pillBtnText}>Import JSON</Text>
            </Pressable>
            <Pressable style={[styles.pillBtn, styles.primaryPill]} onPress={() => void loadValidationSet()}>
              <Ionicons name="refresh" size={16} color="#fff" />
              <Text style={[styles.pillBtnText, { color: '#fff' }]}>Validare</Text>
            </Pressable>
          </View>
        </View>

        <View style={styles.searchWrap}>
          <Ionicons name="search" size={18} color="#64748B" />
          <TextInput
            style={styles.searchInput}
            value={search}
            onChangeText={setSearch}
            placeholder="Caută după expeditor, ID sau text…"
            placeholderTextColor="#94A3B8"
          />
          {search ? (
            <Pressable onPress={() => setSearch('')}>
              <Ionicons name="close-circle" size={18} color="#94A3B8" />
            </Pressable>
          ) : null}
        </View>

        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.chipsRow}>
          {CHANNEL_FILTERS.map((c) => {
            const active = channelFilter === c.value;
            return (
              <Pressable
                key={c.value}
                onPress={() => setChannelFilter(c.value)}
                style={[styles.chip, active && styles.chipActive]}
              >
                <Text style={[styles.chipText, active && styles.chipTextActive]}>{c.label}</Text>
              </Pressable>
            );
          })}
        </ScrollView>

        {hasResults ? (
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.chipsRow}>
            {VERDICT_FILTERS.map((v) => {
              const active = verdictFilter === v.value;
              return (
                <Pressable
                  key={v.value}
                  onPress={() => setVerdictFilter(v.value)}
                  style={[styles.chip, active && styles.chipActive]}
                >
                  <Text style={[styles.chipText, active && styles.chipTextActive]}>{v.label}</Text>
                </Pressable>
              );
            })}
          </ScrollView>
        ) : null}

        <View style={styles.consentRow}>
          <Text style={styles.consentText}>Păstrează istoricul analizelor pe server</Text>
          <Switch value={saveHistory} onValueChange={setSaveHistory} />
        </View>
      </View>

      {apiError ? (
        <View style={styles.bannerWarn}>
          <Ionicons name="wifi-outline" size={16} color="#92400E" />
          <Text style={styles.bannerText} numberOfLines={2}>
            {apiError}
          </Text>
        </View>
      ) : null}

      {errors.length > 0 ? (
        <View style={styles.bannerErr}>
          <Text style={styles.bannerErrText}>{errors.join(' · ')}</Text>
        </View>
      ) : null}

      {loading ? (
        <View style={styles.center}>
          <ActivityIndicator size="large" color="#2563EB" />
          <Text style={styles.muted}>Se încarcă scenariile…</Text>
        </View>
      ) : (
        <FlatList
          data={filtered}
          keyExtractor={(item) => item.id}
          contentContainerStyle={styles.list}
          ListEmptyComponent={
            <View style={styles.center}>
              <Ionicons name="chatbubbles-outline" size={36} color="#94A3B8" />
              <Text style={styles.muted}>Nicio conversație nu corespunde filtrului.</Text>
            </View>
          }
          renderItem={({ item }) => {
            const r = results[item.id];
            const busy = analyzingIds.has(item.id);
            const unread = !readIds.has(item.id);
            const preview = item.messages[0]?.text ?? '(fără mesaje)';
            return (
              <Pressable style={styles.card} onPress={() => selectScenario(item.id)}>
                <View style={styles.cardTop}>
                  <View style={styles.cardIdRow}>
                    {unread ? <View style={styles.unreadDot} /> : null}
                    <Text style={styles.cardId}>{item.id}</Text>
                    <Text style={styles.cardChannel}>· {CHANNEL_LABEL[item.channel]}</Text>
                  </View>
                  {busy ? (
                    <ActivityIndicator size="small" color="#2563EB" />
                  ) : r ? (
                    <Text style={styles.scoreText}>{r.risk_score}/100</Text>
                  ) : null}
                </View>

                <Text style={styles.cardSender} numberOfLines={1}>
                  {senderOf(item)}
                </Text>
                <Text style={styles.cardPreview} numberOfLines={2}>
                  {preview}
                </Text>

                <View style={styles.cardBottom}>
                  <VerdictBadge scenario={item} result={r} compact />
                  <Text style={styles.msgCount}>{item.messages.length} mesaje</Text>
                </View>
              </Pressable>
            );
          }}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#F8FAFC' },
  header: {
    backgroundColor: '#FFFFFF',
    paddingHorizontal: 14,
    paddingTop: 10,
    paddingBottom: 10,
    gap: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#E2E8F0',
  },
  brandRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  headerTitle: { fontSize: 20, fontWeight: '800', color: '#0F172A', flex: 1 },
  headerActions: { flexDirection: 'row', gap: 6 },
  pillBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    paddingHorizontal: 10,
    paddingVertical: 7,
    borderRadius: 999,
    borderWidth: 1,
    borderColor: '#CBD5E1',
    backgroundColor: '#F8FAFC',
  },
  primaryPill: { backgroundColor: '#2563EB', borderColor: '#2563EB' },
  pillBtnText: { fontSize: 13, fontWeight: '700', color: '#1E293B' },
  searchWrap: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    backgroundColor: '#F1F5F9',
    borderRadius: 10,
    paddingHorizontal: 10,
    paddingVertical: 8,
  },
  searchInput: { flex: 1, fontSize: 15, color: '#0F172A', padding: 0 },
  chipsRow: { gap: 6, paddingVertical: 2 },
  chip: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 999,
    backgroundColor: '#F1F5F9',
    borderWidth: 1,
    borderColor: '#E2E8F0',
  },
  chipActive: { backgroundColor: '#1E293B', borderColor: '#1E293B' },
  chipText: { fontSize: 13, fontWeight: '600', color: '#475569' },
  chipTextActive: { color: '#FFFFFF' },
  consentRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingTop: 2,
  },
  consentText: { fontSize: 13, color: '#475569', fontWeight: '600' },
  bannerWarn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    backgroundColor: '#FFFBEB',
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#FDE68A',
  },
  bannerText: { flex: 1, fontSize: 13, color: '#92400E', fontWeight: '600' },
  bannerErr: { backgroundColor: '#FEF2F2', paddingHorizontal: 14, paddingVertical: 8 },
  bannerErrText: { fontSize: 13, color: '#991B1B' },
  center: { alignItems: 'center', justifyContent: 'center', paddingVertical: 48, gap: 10 },
  muted: { fontSize: 15, color: '#64748B' },
  list: { padding: 12, gap: 10, paddingBottom: 24 },
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 14,
    padding: 14,
    borderWidth: 1,
    borderColor: '#E2E8F0',
    gap: 6,
  },
  cardTop: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  cardIdRow: { flexDirection: 'row', alignItems: 'center', gap: 5 },
  unreadDot: { width: 8, height: 8, borderRadius: 4, backgroundColor: '#2563EB' },
  cardId: { fontSize: 13, fontWeight: '800', color: '#0F172A' },
  cardChannel: { fontSize: 13, color: '#64748B', fontWeight: '600' },
  scoreText: { fontSize: 14, fontWeight: '800', color: '#334155' },
  cardSender: { fontSize: 16, fontWeight: '700', color: '#0F172A' },
  cardPreview: { fontSize: 14, lineHeight: 20, color: '#475569' },
  cardBottom: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginTop: 4,
    gap: 8,
  },
  msgCount: { fontSize: 12, color: '#64748B', fontWeight: '600' },
});
