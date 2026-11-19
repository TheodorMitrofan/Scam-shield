import React, { useEffect, useState } from 'react';
import { Linking, Pressable, StyleSheet, Text, TextInput, View } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Ionicons } from '@expo/vector-icons';

interface TrustedContact {
  name: string;
  phone: string;
}

const STORAGE_KEY = 'scamshield-trusted-contact';

/**
 * HACK (hackathon demo, same as the web app): pre-filled trusted contact so the jury can tap once and see it
 * ring. It is the team member's own number, used with his consent; "Schimbă persoana" changes it. Remove after.
 */
const DEMO_CONTACT: TrustedContact = { name: 'Theodor', phone: '0760 042 470' };

/**
 * „Sunați pe cineva de încredere” (brief nice-to-have): one big button that opens the phone's dialer for a
 * person the USER chose — never a number taken from the suspicious message.
 */
export function TrustedCall() {
  const [contact, setContact] = useState<TrustedContact>(DEMO_CONTACT);
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    AsyncStorage.getItem(STORAGE_KEY)
      .then((raw) => {
        const c = raw ? JSON.parse(raw) : null;
        if (c && typeof c.name === 'string' && typeof c.phone === 'string') setContact(c);
      })
      .catch(() => undefined);
  }, []);

  function call() {
    const tel = 'tel:' + contact.phone.replace(/(?!^\+)[^\d]/g, '');
    Linking.openURL(tel).catch(() => setError('Telefonul nu poate iniția apelul.'));
  }

  function startEdit() {
    setName(contact.name);
    setPhone(contact.phone);
    setError(null);
    setEditing(true);
  }

  async function save() {
    const n = name.trim();
    const p = phone.trim();
    const digits = p.replace(/\D/g, '');
    if (!n || digits.length < 6 || digits.length > 15 || !/^\+?[\d\s().-]+$/.test(p)) {
      setError('Scrieți un număr de telefon valid.');
      return;
    }
    const c = { name: n, phone: p };
    setContact(c);
    setEditing(false);
    try {
      await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(c));
    } catch {
      /* storage unavailable: kept for this session */
    }
  }

  if (editing) {
    return (
      <View style={styles.form}>
        <Text style={styles.label}>Numele persoanei</Text>
        <TextInput style={styles.input} value={name} onChangeText={setName} />
        <Text style={styles.label}>Numărul de telefon</Text>
        <TextInput style={styles.input} value={phone} onChangeText={setPhone} keyboardType="phone-pad" />
        {error ? <Text style={styles.error}>{error}</Text> : null}
        <View style={styles.row}>
          <Pressable style={styles.save} onPress={save}>
            <Text style={styles.saveText}>Salvează</Text>
          </Pressable>
          <Pressable onPress={() => setEditing(false)}>
            <Text style={styles.link}>Renunță</Text>
          </Pressable>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.wrap}>
      <Pressable style={styles.call} onPress={call} accessibilityRole="button">
        <Ionicons name="call" size={24} color="#fff" />
        <Text style={styles.callText}>Sunați acum: {contact.name}</Text>
      </Pressable>
      <Pressable onPress={startEdit}>
        <Text style={styles.link}>Schimbă persoana</Text>
      </Pressable>
      <Text style={styles.hint}>
        Înainte să faceți ceva, vorbiți cu cineva apropiat. Numărul rămâne doar pe acest telefon.
      </Text>
      {error ? <Text style={styles.error}>{error}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { gap: 8, marginTop: 12 },
  call: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 12, minHeight: 58,
    borderRadius: 14, backgroundColor: '#16A34A', paddingHorizontal: 18,
  },
  callText: { color: '#fff', fontSize: 20, fontWeight: '800' },
  link: { fontSize: 18, color: '#2563EB', textDecorationLine: 'underline', paddingVertical: 4 },
  hint: { fontSize: 17, color: '#475569', lineHeight: 24 },
  form: {
    gap: 8, marginTop: 12, padding: 14, borderRadius: 12, borderWidth: 1, borderColor: '#E2E8F0',
    backgroundColor: '#F8FAFC',
  },
  label: { fontSize: 18, fontWeight: '700', color: '#0F172A' },
  input: {
    borderWidth: 1, borderColor: '#CBD5E1', borderRadius: 10, paddingHorizontal: 12, paddingVertical: 10,
    fontSize: 18, backgroundColor: '#fff',
  },
  row: { flexDirection: 'row', alignItems: 'center', gap: 16, marginTop: 4 },
  save: { backgroundColor: '#16A34A', borderRadius: 12, paddingVertical: 12, paddingHorizontal: 20 },
  saveText: { color: '#fff', fontSize: 18, fontWeight: '800' },
  error: { fontSize: 17, color: '#DC2626' },
});
