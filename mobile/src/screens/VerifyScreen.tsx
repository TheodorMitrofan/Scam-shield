import React, { useState } from 'react';
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  TextInput,
  View,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { CHANNEL_LABEL } from '../labels';
import { useScamShield } from '../store/ScamShieldContext';
import { CHANNELS, Channel } from '../types';

const SAMPLE_SCAM =
  'Banca Dunărea: Contul dvs. a fost blocat temporar! Accesați https://bancadunarea-securitate.com în 2 ore și confirmați datele cardului și codul SMS pentru deblocare.';

export function VerifyScreen({ onOpenInbox }: { onOpenInbox: () => void }) {
  const { addPastedScenario } = useScamShield();
  const [channel, setChannel] = useState<Channel>('sms');
  const [senderName, setSenderName] = useState('');
  const [senderAddress, setSenderAddress] = useState('');
  const [knownContact, setKnownContact] = useState(false);
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);

  const onCheck = async () => {
    if (!text.trim() || busy) return;
    setBusy(true);
    try {
      await addPastedScenario(text, { channel, senderName, senderAddress, knownContact });
      onOpenInbox();
    } finally {
      setBusy(false);
    }
  };

  return (
    <ScrollView contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
      <View style={styles.hero}>
        <Ionicons name="search-circle" size={32} color="#2563EB" />
        <View style={styles.heroText}>
          <Text style={styles.title}>Verifică un mesaj</Text>
          <Text style={styles.subtitle}>
            Lipiți mesajul suspect sau o conversație (ex. „Exp: … / Eu: …”) și vedeți imediat dacă pare o țeapă.
          </Text>
        </View>
      </View>

      <Text style={styles.label}>Unde ați primit mesajul?</Text>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.channelRow}>
        {CHANNELS.map((c) => {
          const active = channel === c;
          return (
            <Pressable
              key={c}
              onPress={() => setChannel(c)}
              style={[styles.channelChip, active && styles.channelChipActive]}
            >
              <Text style={[styles.channelText, active && styles.channelTextActive]}>
                {CHANNEL_LABEL[c]}
              </Text>
            </Pressable>
          );
        })}
      </ScrollView>

      <View style={styles.card}>
        <Text style={styles.label}>Expeditor (opțional)</Text>
        <TextInput
          style={styles.input}
          value={senderName}
          onChangeText={setSenderName}
          placeholder="Nume (ex. Curier, Bancă, Nepotul)"
          placeholderTextColor="#94A3B8"
        />
        <TextInput
          style={styles.input}
          value={senderAddress}
          onChangeText={setSenderAddress}
          placeholder={channel === 'email' ? 'Adresă e-mail' : 'Număr de telefon'}
          placeholderTextColor="#94A3B8"
          autoCapitalize="none"
        />
        <View style={styles.switchRow}>
          <Text style={styles.switchLabel}>Expeditorul este salvat în agendă</Text>
          <Switch value={knownContact} onValueChange={setKnownContact} />
        </View>
      </View>

      <View style={styles.card}>
        <View style={styles.msgHeader}>
          <Text style={styles.label}>Textul mesajului *</Text>
          <Pressable onPress={() => setText(SAMPLE_SCAM)}>
            <Text style={styles.sampleLink}>Încarcă exemplu</Text>
          </Pressable>
        </View>
        <TextInput
          style={styles.textarea}
          value={text}
          onChangeText={setText}
          placeholder="Lipiți mesajul primit aici…"
          placeholderTextColor="#94A3B8"
          multiline
          textAlignVertical="top"
        />
      </View>

      <Pressable
        style={[styles.checkBtn, (!text.trim() || busy) && styles.disabled]}
        disabled={!text.trim() || busy}
        onPress={() => void onCheck()}
      >
        {busy ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <>
            <Ionicons name="shield-checkmark" size={22} color="#fff" />
            <Text style={styles.checkBtnText}>Verifică mesajul</Text>
          </>
        )}
      </Pressable>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: 16, gap: 14, backgroundColor: '#F8FAFC', paddingBottom: 40 },
  hero: { flexDirection: 'row', gap: 12, alignItems: 'flex-start' },
  heroText: { flex: 1, gap: 4 },
  title: { fontSize: 22, fontWeight: '800', color: '#0F172A' },
  subtitle: { fontSize: 15, lineHeight: 21, color: '#475569' },
  label: { fontSize: 14, fontWeight: '700', color: '#334155' },
  channelRow: { gap: 8 },
  channelChip: {
    paddingHorizontal: 14,
    paddingVertical: 9,
    borderRadius: 999,
    backgroundColor: '#FFFFFF',
    borderWidth: 1,
    borderColor: '#CBD5E1',
  },
  channelChipActive: { backgroundColor: '#2563EB', borderColor: '#2563EB' },
  channelText: { fontSize: 14, fontWeight: '700', color: '#334155' },
  channelTextActive: { color: '#FFFFFF' },
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 14,
    padding: 14,
    borderWidth: 1,
    borderColor: '#E2E8F0',
    gap: 10,
  },
  input: {
    borderWidth: 1,
    borderColor: '#CBD5E1',
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 16,
    color: '#0F172A',
  },
  switchRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  switchLabel: { fontSize: 14, color: '#334155', fontWeight: '600', flex: 1 },
  msgHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  sampleLink: { fontSize: 14, fontWeight: '700', color: '#2563EB' },
  textarea: {
    minHeight: 140,
    borderWidth: 1,
    borderColor: '#CBD5E1',
    borderRadius: 10,
    padding: 12,
    fontSize: 16,
    lineHeight: 22,
    color: '#0F172A',
  },
  checkBtn: {
    backgroundColor: '#2563EB',
    borderRadius: 14,
    paddingVertical: 16,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 10,
  },
  disabled: { opacity: 0.5 },
  checkBtnText: { color: '#fff', fontSize: 18, fontWeight: '800' },
});
