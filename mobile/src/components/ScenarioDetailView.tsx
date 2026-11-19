import React, { useEffect, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import * as Speech from 'expo-speech';
import {
  CHANNEL_LABEL,
  REPORT_MIN_SCORE,
  VERDICT_LABEL,
  VERDICT_THEME,
  flagLabel,
  scamTypeLabel,
  senderOf,
} from '../labels';
import { useScamShield } from '../store/ScamShieldContext';
import { AnalysisResult, Scenario } from '../types';
import { ChannelConversation } from './ChannelConversation';
import { ReportModal } from './ReportModal';
import { VerdictBadge } from './VerdictBadge';

export function ScenarioDetailView({
  scenario,
  result,
  onBack,
}: {
  scenario: Scenario;
  result: AnalysisResult | null;
  onBack: () => void;
}) {
  const { scenarios, analyzingIds, apiError, analyzeScenarios, removeScenario } = useScamShield();
  const [reportOpen, setReportOpen] = useState(false);
  const [speaking, setSpeaking] = useState(false);

  const analyzing = analyzingIds.has(scenario.id);
  const index = scenarios.findIndex((s) => s.id === scenario.id) + 1;

  useEffect(() => {
    return () => {
      Speech.stop();
    };
  }, [scenario.id]);

  const toggleSpeak = () => {
    if (!result?.warning.ro) return;
    if (speaking) {
      Speech.stop();
      setSpeaking(false);
      return;
    }
    const text = `${VERDICT_LABEL[result.verdict]}. ${result.warning.ro}`;
    setSpeaking(true);
    Speech.speak(text, {
      language: 'ro-RO',
      rate: 0.95,
      onDone: () => setSpeaking(false),
      onStopped: () => setSpeaking(false),
      onError: () => setSpeaking(false),
    });
  };

  return (
    <View style={styles.root}>
      <View style={styles.topBar}>
        <Pressable onPress={onBack} style={styles.backBtn} accessibilityLabel="Înapoi la listă">
          <Ionicons name="arrow-back" size={22} color="#0F172A" />
          <Text style={styles.backText}>Înapoi</Text>
        </Pressable>
        <Text style={styles.pos}>
          Scenariul {index}/{scenarios.length}
        </Text>
        <Pressable
          onPress={() => {
            removeScenario(scenario.id);
            onBack();
          }}
          style={styles.iconBtn}
          accessibilityLabel="Șterge scenariul"
        >
          <Ionicons name="trash-outline" size={20} color="#64748B" />
        </Pressable>
      </View>

      <ScrollView contentContainerStyle={styles.scroll}>
        <View style={styles.metaRow}>
          <VerdictBadge scenario={scenario} result={result} />
          <Text style={styles.metaId}>
            {scenario.id} · {CHANNEL_LABEL[scenario.channel]}
          </Text>
        </View>
        <Text style={styles.title}>{senderOf(scenario)}</Text>

        {analyzing ? (
          <View style={styles.analyzingBox}>
            <ActivityIndicator color="#2563EB" />
            <Text style={styles.analyzingText}>Se analizează mesajul…</Text>
          </View>
        ) : result ? (
          <>
            <View
              style={[
                styles.warningBox,
                {
                  backgroundColor: VERDICT_THEME[result.verdict].bg,
                  borderColor: VERDICT_THEME[result.verdict].border,
                },
              ]}
            >
              <View style={styles.warningHeader}>
                <Ionicons
                  name={VERDICT_THEME[result.verdict].icon}
                  size={26}
                  color={VERDICT_THEME[result.verdict].fg}
                />
                <Text style={[styles.verdictTitle, { color: VERDICT_THEME[result.verdict].fg }]}>
                  {VERDICT_LABEL[result.verdict]}
                </Text>
              </View>
              <Text style={styles.warningBody}>{result.warning.ro}</Text>
              <Pressable onPress={toggleSpeak} style={styles.speakBtn}>
                <Ionicons name={speaking ? 'stop-circle' : 'volume-high'} size={18} color="#1E293B" />
                <Text style={styles.speakText}>
                  {speaking ? 'Oprește citirea' : 'Ascultă avertismentul'}
                </Text>
              </Pressable>
            </View>

            <View style={styles.factsGrid}>
              <View style={styles.factCard}>
                <Text style={styles.factLabel}>Risc</Text>
                <Text style={styles.factVal}>
                  {result.risk_score}
                  <Text style={styles.factSub}>/100</Text>
                </Text>
                <View style={styles.barTrack}>
                  <View
                    style={[
                      styles.barFill,
                      {
                        width: `${Math.min(100, Math.max(0, result.risk_score))}%`,
                        backgroundColor: VERDICT_THEME[result.verdict].pill,
                      },
                    ]}
                  />
                </View>
              </View>
              <View style={styles.factCard}>
                <Text style={styles.factLabel}>Tip</Text>
                <Text style={styles.factType}>{scamTypeLabel(result.scam_type)}</Text>
              </View>
              <View style={styles.factCard}>
                <Text style={styles.factLabel}>Prima alertă</Text>
                <Text style={styles.factType}>
                  {result.first_alert ? `mesajul ${result.first_alert}` : '—'}
                </Text>
              </View>
            </View>

            {result.risk_score >= REPORT_MIN_SCORE ? (
              <Pressable style={styles.reportBtn} onPress={() => setReportOpen(true)}>
                <Ionicons name="flag" size={18} color="#fff" />
                <Text style={styles.reportBtnText}>Raportează frauda</Text>
              </Pressable>
            ) : null}

            {result.red_flags.length > 0 ? (
              <View style={styles.flagsSection}>
                <Text style={styles.flagsTitle}>De ce:</Text>
                <View style={styles.flagsWrap}>
                  {result.red_flags.map((f) => (
                    <View key={f} style={styles.flagChip}>
                      <Text style={styles.flagChipText}>{flagLabel(f)}</Text>
                    </View>
                  ))}
                </View>
              </View>
            ) : null}
          </>
        ) : apiError ? (
          <View style={styles.offlineBox}>
            <Ionicons name="wifi" size={18} color="#B45309" />
            <Text style={styles.offlineText}>Mesajul nu a putut fi verificat acum (backend offline).</Text>
            <Pressable onPress={() => void analyzeScenarios([scenario])} style={styles.retryBtn}>
              <Text style={styles.retryText}>Reîncearcă</Text>
            </Pressable>
          </View>
        ) : null}

        <ChannelConversation scenario={scenario} result={result} />
      </ScrollView>

      {result ? (
        <ReportModal
          visible={reportOpen}
          onClose={() => setReportOpen(false)}
          scenario={scenario}
          result={result}
        />
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#F8FAFC' },
  topBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 14,
    paddingVertical: 10,
    backgroundColor: '#FFFFFF',
    borderBottomWidth: 1,
    borderBottomColor: '#E2E8F0',
  },
  backBtn: { flexDirection: 'row', alignItems: 'center', gap: 6, paddingVertical: 4, paddingRight: 8 },
  backText: { fontSize: 16, fontWeight: '700', color: '#0F172A' },
  pos: { fontSize: 14, fontWeight: '600', color: '#64748B' },
  iconBtn: { padding: 6 },
  scroll: { padding: 14, gap: 14, paddingBottom: 36 },
  metaRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 8 },
  metaId: { fontSize: 13, color: '#64748B', fontWeight: '600' },
  title: { fontSize: 22, fontWeight: '800', color: '#0F172A' },
  analyzingBox: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    backgroundColor: '#EFF6FF',
    padding: 14,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: '#BFDBFE',
  },
  analyzingText: { fontSize: 15, color: '#1E40AF', fontWeight: '600' },
  warningBox: { borderRadius: 16, borderWidth: 1.5, padding: 15, gap: 10 },
  warningHeader: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  verdictTitle: { fontSize: 18, fontWeight: '800', flex: 1 },
  warningBody: { fontSize: 17, lineHeight: 24, color: '#0F172A' },
  speakBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    alignSelf: 'flex-start',
    backgroundColor: 'rgba(255,255,255,0.8)',
    borderWidth: 1,
    borderColor: '#CBD5E1',
    borderRadius: 999,
    paddingHorizontal: 12,
    paddingVertical: 7,
  },
  speakText: { fontSize: 14, fontWeight: '700', color: '#1E293B' },
  factsGrid: { flexDirection: 'row', gap: 8 },
  factCard: {
    flex: 1,
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#E2E8F0',
    padding: 10,
    gap: 4,
  },
  factLabel: { fontSize: 12, color: '#64748B', fontWeight: '600' },
  factVal: { fontSize: 20, fontWeight: '800', color: '#0F172A' },
  factSub: { fontSize: 13, fontWeight: '600', color: '#64748B' },
  factType: { fontSize: 14, fontWeight: '700', color: '#0F172A' },
  barTrack: { height: 6, borderRadius: 3, backgroundColor: '#E2E8F0', overflow: 'hidden', marginTop: 2 },
  barFill: { height: '100%', borderRadius: 3 },
  reportBtn: {
    backgroundColor: '#DC2626',
    borderRadius: 12,
    paddingVertical: 13,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
  },
  reportBtnText: { color: '#fff', fontSize: 16, fontWeight: '800' },
  flagsSection: { gap: 6 },
  flagsTitle: { fontSize: 14, fontWeight: '700', color: '#475569' },
  flagsWrap: { flexDirection: 'row', flexWrap: 'wrap', gap: 6 },
  flagChip: {
    backgroundColor: '#F1F5F9',
    borderWidth: 1,
    borderColor: '#CBD5E1',
    borderRadius: 999,
    paddingHorizontal: 10,
    paddingVertical: 5,
  },
  flagChipText: { fontSize: 13, color: '#1E293B', fontWeight: '600' },
  offlineBox: {
    flexDirection: 'row',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: 8,
    backgroundColor: '#FFFBEB',
    borderWidth: 1,
    borderColor: '#FCD34D',
    borderRadius: 12,
    padding: 12,
  },
  offlineText: { flex: 1, fontSize: 14, color: '#92400E', fontWeight: '600' },
  retryBtn: { paddingHorizontal: 10, paddingVertical: 6, backgroundColor: '#FEF3C7', borderRadius: 8 },
  retryText: { fontSize: 13, fontWeight: '700', color: '#92400E' },
});
