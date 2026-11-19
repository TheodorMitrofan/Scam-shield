import React, { useEffect, useMemo, useState } from 'react';
import {
  ActivityIndicator,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  TextInput,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { mobileApi } from '../api';
import { useScamShield } from '../store/ScamShieldContext';
import { AnalysisResult, FraudReportDraft, PersonalData, PersonalField, Scenario } from '../types';

const EMPTY_PERSON: PersonalData = {
  last_name: null,
  first_name: null,
  cnp: null,
  id_series_number: null,
  address: null,
  phone: null,
  email: null,
  incident_date: null,
  incident_time: null,
  lost_money: false,
  amount_lost: null,
  bank: null,
  additional_details: null,
};

export function ReportModal({
  visible,
  onClose,
  scenario,
  result,
}: {
  visible: boolean;
  onClose: () => void;
  scenario: Scenario;
  result: AnalysisResult;
}) {
  const { apiBase } = useScamShield();
  const [draft, setDraft] = useState<FraudReportDraft | null>(null);
  const [person, setPerson] = useState<PersonalData>({ ...EMPTY_PERSON });
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [tried, setTried] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sentTo, setSentTo] = useState<string | null>(null);

  useEffect(() => {
    if (!visible) {
      setDraft(null);
      setPerson({ ...EMPTY_PERSON });
      setTried(false);
      setError(null);
      setSentTo(null);
      return;
    }
    let alive = true;
    setLoading(true);
    setError(null);
    mobileApi
      .reportDraft(apiBase, scenario, result)
      .then((d) => {
        if (alive) setDraft(d);
      })
      .catch((e) => {
        if (alive) setError(e instanceof Error ? e.message : 'Nu am putut pregăti sesizarea.');
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [apiBase, result, scenario, visible]);

  const missing = useMemo(() => {
    if (!draft) return [];
    return draft.personal_fields
      .filter((f) => f.required && (person[f.key] === null || person[f.key] === ''))
      .map((f) => f.label);
  }, [draft, person]);

  const updateField = (f: PersonalField, v: string | boolean) => {
    let val: string | number | boolean | null = v;
    if (f.type === 'number') val = v === '' ? null : Number(v);
    else if (typeof v === 'string' && f.type !== 'checkbox') val = v.trim() === '' ? null : v;
    setPerson((prev) => ({ ...prev, [f.key]: val }));
  };

  const onSend = async () => {
    if (!draft) return;
    setTried(true);
    if (missing.length > 0) return;
    setSending(true);
    setError(null);
    try {
      const res = await mobileApi.reportSend(apiBase, draft, person);
      setSentTo(res.recipient);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Trimiterea nu a reușit.');
    } finally {
      setSending(false);
    }
  };

  return (
    <Modal visible={visible} animationType="slide" onRequestClose={onClose}>
      <SafeAreaView style={styles.root}>
        <View style={styles.header}>
          <Text style={styles.title}>Raportează frauda</Text>
          <Pressable onPress={onClose} style={styles.closeBtn} accessibilityLabel="Închide">
            <Ionicons name="close" size={24} color="#0F172A" />
          </Pressable>
        </View>

        <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
          {loading ? (
            <View style={styles.center}>
              <ActivityIndicator size="large" color="#2563EB" />
              <Text style={styles.muted}>Pregătim datele incidentului…</Text>
            </View>
          ) : null}

          {error ? (
            <View style={styles.errorBox}>
              <Ionicons name="warning" size={18} color="#B91C1C" />
              <Text style={styles.errorText}>{error}</Text>
            </View>
          ) : null}

          {sentTo ? (
            <View style={styles.successBox}>
              <Ionicons name="checkmark-circle" size={22} color="#059669" />
              <Text style={styles.successText}>
                Sesizarea a fost trimisă către inbox-ul demo: {sentTo}. Datele personale nu au fost salvate.
              </Text>
            </View>
          ) : null}

          {draft ? (
            <>
              <View style={styles.card}>
                <Text style={styles.sectionTitle}>Rezumat incident (generat automat)</Text>
                <Text style={styles.body}>{draft.incident.summary_ro}</Text>
                {draft.incident.indicators.length > 0 ? (
                  <View style={styles.indicators}>
                    <Text style={styles.subLabel}>Indicatori neutralizați:</Text>
                    {draft.incident.indicators.map((ind, idx) => (
                      <Text key={`${ind.kind}-${idx}`} style={styles.codeLine}>
                        • {ind.kind.toUpperCase()}: {ind.display}
                      </Text>
                    ))}
                  </View>
                ) : null}
              </View>

              <View style={styles.card}>
                <Text style={styles.sectionTitle}>Datele dumneavoastră (nu se stochează)</Text>
                {draft.personal_fields.map((f) => {
                  const val = person[f.key];
                  const isInvalid = tried && f.required && (val === null || val === '');
                  if (f.type === 'checkbox') {
                    return (
                      <View key={f.key} style={styles.switchRow}>
                        <Text style={styles.fieldLabel}>{f.label}</Text>
                        <Switch value={Boolean(val)} onValueChange={(b) => updateField(f, b)} />
                      </View>
                    );
                  }
                  return (
                    <View key={f.key} style={styles.field}>
                      <Text style={styles.fieldLabel}>
                        {f.label}
                        {f.required ? ' *' : ''}
                      </Text>
                      <TextInput
                        style={[
                          styles.input,
                          f.type === 'textarea' && styles.textarea,
                          isInvalid && styles.inputInvalid,
                        ]}
                        value={val == null ? '' : String(val)}
                        onChangeText={(txt) => updateField(f, txt)}
                        placeholder={f.hint ?? ''}
                        placeholderTextColor="#94A3B8"
                        multiline={f.type === 'textarea'}
                        keyboardType={
                          f.type === 'number' || f.type === 'tel'
                            ? 'phone-pad'
                            : f.type === 'email'
                              ? 'email-address'
                              : 'default'
                        }
                        autoCapitalize={f.type === 'email' ? 'none' : 'sentences'}
                      />
                    </View>
                  );
                })}
                {tried && missing.length > 0 ? (
                  <Text style={styles.missingText}>Completați câmpurile obligatorii: {missing.join(', ')}</Text>
                ) : null}

                <Pressable
                  style={[styles.sendBtn, sending && styles.disabled]}
                  onPress={onSend}
                  disabled={sending}
                >
                  {sending ? (
                    <ActivityIndicator color="#fff" />
                  ) : (
                    <>
                      <Ionicons name="send" size={18} color="#fff" />
                      <Text style={styles.sendText}>Trimite sesizarea (demo)</Text>
                    </>
                  )}
                </Pressable>
              </View>
            </>
          ) : null}
        </ScrollView>
      </SafeAreaView>
    </Modal>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#F8FAFC' },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 12,
    backgroundColor: '#FFFFFF',
    borderBottomWidth: 1,
    borderBottomColor: '#E2E8F0',
  },
  title: { fontSize: 19, fontWeight: '800', color: '#0F172A' },
  closeBtn: { padding: 6 },
  content: { padding: 16, gap: 14, paddingBottom: 40 },
  center: { alignItems: 'center', paddingVertical: 24, gap: 8 },
  muted: { color: '#64748B', fontSize: 15 },
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 14,
    padding: 14,
    borderWidth: 1,
    borderColor: '#E2E8F0',
    gap: 10,
  },
  sectionTitle: { fontSize: 16, fontWeight: '800', color: '#0F172A' },
  body: { fontSize: 15, lineHeight: 22, color: '#334155' },
  indicators: { backgroundColor: '#F8FAFC', padding: 10, borderRadius: 10, gap: 4 },
  subLabel: { fontSize: 13, fontWeight: '700', color: '#475569' },
  codeLine: { fontSize: 13, color: '#0F172A' },
  field: { gap: 4 },
  fieldLabel: { fontSize: 14, fontWeight: '700', color: '#334155' },
  input: {
    borderWidth: 1,
    borderColor: '#CBD5E1',
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 16,
    color: '#0F172A',
    backgroundColor: '#FFFFFF',
  },
  textarea: { minHeight: 84, textAlignVertical: 'top' },
  inputInvalid: { borderColor: '#DC2626', backgroundColor: '#FEF2F2' },
  switchRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingVertical: 4 },
  missingText: { color: '#B91C1C', fontSize: 13, fontWeight: '600' },
  sendBtn: {
    marginTop: 6,
    backgroundColor: '#DC2626',
    borderRadius: 12,
    paddingVertical: 14,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
  },
  disabled: { opacity: 0.6 },
  sendText: { color: '#fff', fontSize: 16, fontWeight: '800' },
  errorBox: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    backgroundColor: '#FEF2F2',
    borderWidth: 1,
    borderColor: '#FCA5A5',
    borderRadius: 12,
    padding: 12,
  },
  errorText: { flex: 1, color: '#991B1B', fontSize: 14, fontWeight: '600' },
  successBox: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    backgroundColor: '#ECFDF5',
    borderWidth: 1,
    borderColor: '#6EE7B7',
    borderRadius: 12,
    padding: 12,
  },
  successText: { flex: 1, color: '#065F46', fontSize: 14, fontWeight: '600' },
});
