import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { CHANNEL_COLOR, CHANNEL_LABEL, flagLabel, flagsAt, isFirstAlert, senderOf } from '../labels';
import { AnalysisResult, Message, Scenario } from '../types';

function FlagList({ flags }: { flags: string[] }) {
  if (!flags.length) return null;
  return (
    <View style={styles.flagWrap}>
      {flags.map((f) => (
        <View key={f} style={styles.flagPill}>
          <Ionicons name="alert-circle" size={13} color="#B45309" />
          <Text style={styles.flagText}>{flagLabel(f)}</Text>
        </View>
      ))}
    </View>
  );
}

function FirstAlertTag({ active }: { active: boolean }) {
  if (!active) return null;
  return (
    <View style={styles.alertBanner}>
      <Ionicons name="warning" size={14} color="#B91C1C" />
      <Text style={styles.alertText}>Aici apare prima alertă</Text>
    </View>
  );
}

function ChatRenderer({ scenario, result }: { scenario: Scenario; result: AnalysisResult | null }) {
  const accent = CHANNEL_COLOR[scenario.channel];
  const title = senderOf(scenario);
  const subtitle = scenario.sender.name && scenario.sender.address ? scenario.sender.address : null;
  return (
    <View style={styles.phoneCard}>
      <View style={[styles.chatHeader, { backgroundColor: scenario.channel === 'whatsapp' ? '#075E54' : accent }]}>
        <View style={styles.avatar}>
          <Text style={styles.avatarLetter}>{title.slice(0, 1).toUpperCase()}</Text>
        </View>
        <View style={styles.chatWho}>
          <Text style={styles.chatName} numberOfLines={1}>{title}</Text>
          {subtitle ? <Text style={styles.chatAddr}>{subtitle}</Text> : null}
        </View>
        <View style={[styles.contactTag, scenario.sender.known_contact ? styles.knownTag : styles.unknownTag]}>
          <Text style={styles.contactTagText}>
            {scenario.sender.known_contact ? '✓ În agendă' : '⚠ Necunoscut'}
          </Text>
        </View>
      </View>

      <View style={styles.channelBar}>
        <Text style={styles.channelBarText}>{CHANNEL_LABEL[scenario.channel]}</Text>
      </View>

      <View style={styles.thread}>
        {scenario.messages.length === 0 ? (
          <Text style={styles.emptyMsg}>Conversația nu are mesaje.</Text>
        ) : (
          scenario.messages.map((m: Message) => {
            const me = m.from === 'reader';
            const alert = isFirstAlert(result, m.n);
            const flags = flagsAt(result, m.n);
            return (
              <View key={m.n} style={[styles.bubbleRow, me ? styles.rowRight : styles.rowLeft]}>
                <View
                  style={[
                    styles.bubble,
                    me ? styles.bubbleMe : styles.bubbleThem,
                    alert && styles.bubbleAlert,
                  ]}
                >
                  <FirstAlertTag active={alert} />
                  <Text style={styles.msgText}>{m.text || '(mesaj gol)'}</Text>
                  <FlagList flags={flags} />
                </View>
              </View>
            );
          })
        )}
      </View>
    </View>
  );
}

function EmailRenderer({ scenario, result }: { scenario: Scenario; result: AnalysisResult | null }) {
  const sender = senderOf(scenario);
  const firstText = scenario.messages[0]?.text ?? '';
  const subject = firstText.split('\n')[0]?.slice(0, 64) || 'Mesaj primit pe e-mail';
  return (
    <View style={styles.emailCard}>
      <View style={styles.emailBar}>
        <Ionicons name="mail" size={16} color="#5B21B6" />
        <Text style={styles.emailBarText}>Căsuța de e-mail</Text>
      </View>
      <Text style={styles.emailSubject}>{subject}</Text>
      {scenario.messages.map((m) => {
        const me = m.from === 'reader';
        const alert = isFirstAlert(result, m.n);
        const flags = flagsAt(result, m.n);
        return (
          <View key={m.n} style={[styles.emailItem, alert && styles.bubbleAlert]}>
            <FirstAlertTag active={alert} />
            <Text style={styles.emailFrom}>{me ? 'Dumneavoastră' : sender}</Text>
            <Text style={styles.emailAddr}>
              {me
                ? `către: ${scenario.sender.address ?? sender}`
                : `<${scenario.sender.address ?? 'adresă necunoscută'}> · ${scenario.sender.known_contact ? '✓ În agendă' : '⚠ Expeditor necunoscut'}`}
            </Text>
            <Text style={styles.msgText}>{m.text || '(e-mail gol)'}</Text>
            <FlagList flags={flags} />
          </View>
        );
      })}
    </View>
  );
}

function CallRenderer({ scenario, result }: { scenario: Scenario; result: AnalysisResult | null }) {
  const caller = senderOf(scenario);
  const fmt = (s: number) => {
    const m = Math.floor(s / 60);
    const r = Math.floor(s % 60);
    return `${m}:${String(r).padStart(2, '0')}`;
  };
  return (
    <View style={styles.callCard}>
      <View style={styles.callHeader}>
        <View style={styles.callAvatar}>
          <Ionicons name="call" size={24} color="#fff" />
        </View>
        <Text style={styles.callName}>{caller}</Text>
        {scenario.sender.name && scenario.sender.address ? (
          <Text style={styles.callNumber}>{scenario.sender.address}</Text>
        ) : null}
        <Text style={styles.callStatus}>
          {scenario.audio ? 'Mesaj vocal' : 'Apel — transcriere'} ·{' '}
          {scenario.sender.known_contact ? '✓ În agendă' : '⚠ Număr necunoscut'}
        </Text>
      </View>
      <View style={styles.thread}>
        {scenario.messages.map((m) => {
          const me = m.from === 'reader';
          const alert = isFirstAlert(result, m.n);
          const flags = flagsAt(result, m.n);
          return (
            <View key={m.n} style={[styles.callLine, me && styles.callLineMe, alert && styles.bubbleAlert]}>
              <FirstAlertTag active={alert} />
              <Text style={styles.callSpeaker}>
                {me ? 'Dumneavoastră' : 'Apelantul'}
                {m.start_s != null ? ` · ${fmt(m.start_s)}` : ''}
              </Text>
              <Text style={styles.msgText}>{m.text || '(liniște)'}</Text>
              <FlagList flags={flags} />
            </View>
          );
        })}
      </View>
    </View>
  );
}

export function ChannelConversation({
  scenario,
  result,
}: {
  scenario: Scenario;
  result: AnalysisResult | null;
}) {
  if (scenario.channel === 'email') return <EmailRenderer scenario={scenario} result={result} />;
  if (scenario.channel === 'call_transcript') return <CallRenderer scenario={scenario} result={result} />;
  return <ChatRenderer scenario={scenario} result={result} />;
}

const styles = StyleSheet.create({
  phoneCard: {
    borderRadius: 16,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: '#E2E8F0',
    backgroundColor: '#F8FAFC',
  },
  chatHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    paddingHorizontal: 14,
    paddingVertical: 12,
  },
  avatar: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: 'rgba(255,255,255,0.22)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  avatarLetter: { color: '#fff', fontWeight: '800', fontSize: 16 },
  chatWho: { flex: 1 },
  chatName: { color: '#fff', fontWeight: '700', fontSize: 16 },
  chatAddr: { color: 'rgba(255,255,255,0.85)', fontSize: 13 },
  contactTag: { paddingHorizontal: 8, paddingVertical: 4, borderRadius: 999 },
  knownTag: { backgroundColor: 'rgba(16,185,129,0.25)' },
  unknownTag: { backgroundColor: 'rgba(245,158,11,0.3)' },
  contactTagText: { color: '#fff', fontSize: 12, fontWeight: '700' },
  channelBar: {
    backgroundColor: '#E2E8F0',
    paddingVertical: 4,
    alignItems: 'center',
  },
  channelBarText: { fontSize: 12, fontWeight: '700', color: '#475569' },
  thread: { padding: 12, gap: 10 },
  emptyMsg: { textAlign: 'center', color: '#64748B', paddingVertical: 16, fontSize: 15 },
  bubbleRow: { flexDirection: 'row' },
  rowLeft: { justifyContent: 'flex-start' },
  rowRight: { justifyContent: 'flex-end' },
  bubble: {
    maxWidth: '88%',
    borderRadius: 14,
    paddingHorizontal: 13,
    paddingVertical: 10,
    borderWidth: 1,
  },
  bubbleThem: { backgroundColor: '#FFFFFF', borderColor: '#E2E8F0' },
  bubbleMe: { backgroundColor: '#DCFCE7', borderColor: '#BBF7D0' },
  bubbleAlert: { borderColor: '#EF4444', borderWidth: 2, backgroundColor: '#FEF2F2' },
  msgText: { fontSize: 16, lineHeight: 23, color: '#0F172A' },
  alertBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    marginBottom: 6,
    paddingBottom: 5,
    borderBottomWidth: 1,
    borderBottomColor: '#FECACA',
  },
  alertText: { color: '#B91C1C', fontSize: 12, fontWeight: '800', textTransform: 'uppercase' },
  flagWrap: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginTop: 8 },
  flagPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    backgroundColor: '#FEF3C7',
    borderColor: '#FCD34D',
    borderWidth: 1,
    borderRadius: 999,
    paddingHorizontal: 8,
    paddingVertical: 3,
  },
  flagText: { fontSize: 12, color: '#92400E', fontWeight: '600' },
  emailCard: {
    borderRadius: 16,
    borderWidth: 1,
    borderColor: '#DDD6FE',
    backgroundColor: '#FFFFFF',
    overflow: 'hidden',
  },
  emailBar: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    backgroundColor: '#F5F3FF',
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#DDD6FE',
  },
  emailBarText: { color: '#5B21B6', fontWeight: '700', fontSize: 14 },
  emailSubject: { fontSize: 17, fontWeight: '700', color: '#0F172A', paddingHorizontal: 14, paddingTop: 12 },
  emailItem: {
    margin: 12,
    padding: 12,
    borderRadius: 12,
    backgroundColor: '#F8FAFC',
    borderWidth: 1,
    borderColor: '#E2E8F0',
  },
  emailFrom: { fontSize: 15, fontWeight: '700', color: '#0F172A' },
  emailAddr: { fontSize: 13, color: '#64748B', marginBottom: 8 },
  callCard: {
    borderRadius: 16,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: '#E2E8F0',
    backgroundColor: '#F8FAFC',
  },
  callHeader: {
    backgroundColor: '#1E293B',
    paddingVertical: 18,
    paddingHorizontal: 16,
    alignItems: 'center',
    gap: 4,
  },
  callAvatar: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: '#EA580C',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 4,
  },
  callName: { color: '#fff', fontSize: 18, fontWeight: '800' },
  callNumber: { color: '#CBD5E1', fontSize: 14 },
  callStatus: { color: '#94A3B8', fontSize: 13, marginTop: 2 },
  callLine: {
    padding: 12,
    borderRadius: 12,
    backgroundColor: '#FFFFFF',
    borderWidth: 1,
    borderColor: '#E2E8F0',
  },
  callLineMe: { backgroundColor: '#EFF6FF', borderColor: '#BFDBFE' },
  callSpeaker: { fontSize: 12, fontWeight: '700', color: '#475569', marginBottom: 4 },
});
