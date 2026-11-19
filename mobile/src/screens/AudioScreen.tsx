import React, { useEffect, useState } from 'react';
import { ActivityIndicator, Image, Linking, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { getStoredApiUrls, mobileApi } from '../api';
import { VERDICT_LABEL, VERDICT_THEME } from '../labels';
import { AnalysisResult, Scenario } from '../types';

/* Same endpoints as the web Audio page (audio service, port 8002): /claim and /demo?scenario=. */

interface ClaimPlace {
  label: string;
  match: boolean;
}
interface ClaimResult {
  ok: boolean;
  transcript: string;
  claimed: ClaimPlace;
  actual: ClaimPlace;
  event?: { t_cpa_s: number; speed_kmh: number; distance_m: number };
  spectrogram?: string;
}
interface DemoResult {
  ok: boolean;
  reason?: string;
  scenario: string;
  country: string;
  place: string;
  truth: { lat: number; lon: number };
  estimate: { lat: number; lon: number };
  error_m: number;
  region_radius_m: number;
  spectrogram: string;
  heatmap: string;
}

const SCENARIOS: { key: string; flag: string; label: string }[] = [
  { key: 'uk', flag: '🇬🇧', label: 'Londra' },
  { key: 'de', flag: '🇩🇪', label: 'München' },
  { key: 'us', flag: '🇺🇸', label: 'Seattle' },
];

const n = (v: number) => Math.round(v).toLocaleString('ro-RO');
const osm = (lat: number, lon: number) =>
  `https://www.openstreetmap.org/?mlat=${lat.toFixed(5)}&mlon=${lon.toFixed(5)}#map=16/${lat.toFixed(5)}/${lon.toFixed(5)}`;

async function getJson<T>(url: string): Promise<T> {
  let res: Response;
  try {
    res = await fetch(url);
  } catch {
    throw new Error('Serviciul audio nu răspunde. Verificați că rulează pe laptop (port 8002) și Wi-Fi.');
  }
  if (!res.ok) throw new Error(`Eroare ${res.status}`);
  return (await res.json()) as T;
}

/** Audio tab: „Nepotul e în Spania?” claim check + the simulated localisation demo (like the web Audio page). */
export function AudioScreen() {
  const [audioBase, setAudioBase] = useState<string | null>(null);

  // claim check
  const [claim, setClaim] = useState<ClaimResult | null>(null);
  const [scam, setScam] = useState<AnalysisResult | null>(null);
  const [claimError, setClaimError] = useState<string | null>(null);
  const [claimBusy, setClaimBusy] = useState(true);
  const [showDetails, setShowDetails] = useState(false);

  // demo
  const [scenario, setScenario] = useState<string | null>(null);
  const [demo, setDemo] = useState<DemoResult | null>(null);
  const [demoBusy, setDemoBusy] = useState(false);
  const [demoError, setDemoError] = useState<string | null>(null);

  async function loadClaim() {
    setClaimBusy(true);
    setClaimError(null);
    try {
      const { apiBase, audioBase: ab } = await getStoredApiUrls();
      setAudioBase(ab);
      const c = await getJson<ClaimResult>(`${ab}/claim`);
      setClaim(c);
      const s: Scenario = {
        id: 'AUDIO-CLAIM',
        channel: 'whatsapp',
        sender: { name: null, address: 'număr necunoscut', known_contact: false },
        messages: [{ n: 1, from: 'sender', text: c.transcript }],
      };
      try {
        setScam((await mobileApi.analyze(apiBase, s, false)).result);
      } catch {
        setScam(null); // the place check still works without the scam verdict
      }
    } catch (e) {
      setClaimError(e instanceof Error ? e.message : 'Analiza nu a reușit.');
    } finally {
      setClaimBusy(false);
    }
  }

  async function runDemo(key: string) {
    setScenario(key);
    setDemo(null);
    setDemoError(null);
    setDemoBusy(true);
    try {
      const { audioBase: ab } = await getStoredApiUrls();
      const d = await getJson<DemoResult>(`${ab}/demo?scenario=${key}`);
      if (!d.ok) throw new Error(d.reason ?? 'Demonstrația nu a reușit.');
      setDemo(d);
    } catch (e) {
      setDemoError(e instanceof Error ? e.message : 'Demonstrația nu a reușit.');
    } finally {
      setDemoBusy(false);
    }
  }

  useEffect(() => {
    loadClaim();
  }, []);

  return (
    <ScrollView contentContainerStyle={styles.container}>
      {/* ---------------- „Nepotul e în Spania?” ---------------- */}
      <View style={styles.card}>
        <View style={styles.titleRow}>
          <Text style={styles.h2}>„Nepotul e în Spania?” — verificăm locul declarat</Text>
          <Text style={styles.sim}>SIMULAT</Text>
        </View>
        <Text style={styles.p}>
          Escrocul spune că e în altă țară. Din avioanele care se aud în fundalul mesajului vocal și din ora
          mesajului verificăm dacă locul declarat se potrivește cu sunetul.
        </Text>

        {claimBusy ? (
          <View style={styles.busy}>
            <ActivityIndicator color="#2563EB" />
            <Text style={styles.p}>Analizăm mesajul vocal…</Text>
          </View>
        ) : claimError ? (
          <View style={styles.errBox}>
            <Text style={styles.err}>{claimError}</Text>
            <Pressable onPress={loadClaim}>
              <Text style={styles.link}>Reîncearcă</Text>
            </Pressable>
          </View>
        ) : claim ? (
          <>
            {audioBase ? (
              <Pressable style={styles.play} onPress={() => Linking.openURL(`${audioBase}/claim/recording.wav`)}>
                <Ionicons name="play-circle" size={24} color="#2563EB" />
                <Text style={styles.playText}>Ascultă mesajul vocal</Text>
              </Pressable>
            ) : null}
            <Text style={styles.label}>Ce spune:</Text>
            <Text style={styles.quote}>„{claim.transcript}”</Text>

            {scam ? (
              <View
                style={[
                  styles.verdict,
                  { backgroundColor: VERDICT_THEME[scam.verdict].bg, borderColor: VERDICT_THEME[scam.verdict].border },
                ]}
              >
                <Text style={[styles.verdictText, { color: VERDICT_THEME[scam.verdict].fg }]}>
                  {VERDICT_LABEL[scam.verdict]}
                </Text>
              </View>
            ) : null}

            <View style={styles.place}>
              <Ionicons name={claim.claimed.match ? 'checkmark-circle' : 'close-circle'} size={26}
                color={claim.claimed.match ? '#16A34A' : '#DC2626'} />
              <Text style={styles.placeText}>
                Spune că este în <Text style={styles.bold}>{claim.claimed.label}</Text>
              </Text>
            </View>
            <View style={styles.place}>
              <Ionicons name={claim.actual.match ? 'checkmark-circle' : 'close-circle'} size={26}
                color={claim.actual.match ? '#16A34A' : '#DC2626'} />
              <Text style={styles.placeText}>
                Sunetul se potrivește cu <Text style={styles.bold}>{claim.actual.label}</Text>
              </Text>
            </View>

            <Text style={styles.label}>Ce să faceți:</Text>
            <Text style={styles.p}>
              nu trimiteți bani. Sunați-l pe nepot la numărul lui vechi, pe care îl cunoașteți.
            </Text>
            <Text style={styles.small}>
              Nu arătăm unde se află persoana, doar dacă sunetul se potrivește cu locul pe care îl declară.
              Detaliile tehnice pot fi anexate plângerii către poliție.
            </Text>

            <Pressable onPress={() => setShowDetails(!showDetails)}>
              <Text style={styles.link}>{showDetails ? 'Ascunde detaliile tehnice' : 'Detalii tehnice'}</Text>
            </Pressable>
            {showDetails && claim.spectrogram ? (
              <>
                <Image source={{ uri: claim.spectrogram }} style={styles.img} resizeMode="contain" />
                {claim.event ? (
                  <Text style={styles.small}>
                    Avion la secunda {n(claim.event.t_cpa_s)}: ~{n(claim.event.speed_kmh)} km/h, la ~
                    {n(claim.event.distance_m)} m. Ora mesajului cunoscută (±30 s). Mesaj, voce și zboruri simulate.
                  </Text>
                ) : null}
              </>
            ) : null}
          </>
        ) : null}
      </View>

      {/* ---------------- Demo ---------------- */}
      <View style={styles.card}>
        <Text style={styles.h2}>Demonstrație: cum se află locul</Text>
        <Text style={styles.p}>
          Pe o înregistrare <Text style={styles.bold}>simulată</Text> cu două avioane cu elice, comparăm sunetul cu
          traseele zborurilor și găsim locul microfonului. Nu localizăm nicio persoană reală.
        </Text>
        <View style={styles.scenarios}>
          {SCENARIOS.map((s) => (
            <Pressable
              key={s.key}
              style={[styles.scBtn, scenario === s.key && styles.scBtnActive]}
              onPress={() => runDemo(s.key)}
              disabled={demoBusy}
            >
              <Text style={[styles.scText, scenario === s.key && styles.scTextActive]}>
                {s.flag} {s.label}
              </Text>
            </Pressable>
          ))}
        </View>
        {demoBusy ? (
          <View style={styles.busy}>
            <ActivityIndicator color="#2563EB" />
            <Text style={styles.p}>Calculăm… dacă serviciul abia a pornit, durează până la un minut.</Text>
          </View>
        ) : null}
        {demoError ? <Text style={styles.err}>{demoError}</Text> : null}
        {demo ? (
          <>
            <View style={styles.titleRow}>
              <Text style={styles.where}>
                {demo.country} · {demo.place}
              </Text>
              <Text style={styles.sim}>SIMULAT</Text>
            </View>
            <Text style={styles.big}>{n(demo.error_m)} m</Text>
            <Text style={styles.p}>
              între locul găsit și locul real · zona de incertitudine ±{n(demo.region_radius_m)} m
            </Text>
            <Pressable style={styles.mapBtn} onPress={() => Linking.openURL(osm(demo.estimate.lat, demo.estimate.lon))}>
              <Ionicons name="close" size={22} color="#DC2626" />
              <Text style={styles.mapText}>Locul găsit din sunet — deschide pe hartă</Text>
            </Pressable>
            <Pressable style={styles.mapBtn} onPress={() => Linking.openURL(osm(demo.truth.lat, demo.truth.lon))}>
              <Ionicons name="ellipse" size={18} color="#16A34A" />
              <Text style={styles.mapText}>Locul real al microfonului (simulat) — deschide pe hartă</Text>
            </Pressable>
            {audioBase ? (
              <Pressable style={styles.play} onPress={() => Linking.openURL(`${audioBase}/demo/${demo.scenario}/recording.wav`)}>
                <Ionicons name="play-circle" size={24} color="#2563EB" />
                <Text style={styles.playText}>Ascultă înregistrarea simulată</Text>
              </Pressable>
            ) : null}
            <Image source={{ uri: demo.spectrogram }} style={styles.img} resizeMode="contain" />
            <Text style={styles.small}>Cele două curbe Doppler găsite în zgomot.</Text>
            <Image source={{ uri: demo.heatmap }} style={styles.imgSquare} resizeMode="contain" />
            <Text style={styles.small}>Cât de bine explică fiecare loc din jur sunetul înregistrat.</Text>
          </>
        ) : null}
      </View>

      <Text style={styles.small}>
        Verificarea propriului mesaj vocal (dacă dezvăluie unde sunteți) e în tab-ul Setări.
      </Text>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: 16, gap: 16, paddingBottom: 32 },
  card: { backgroundColor: '#fff', borderRadius: 16, borderWidth: 1, borderColor: '#E2E8F0', padding: 16, gap: 10 },
  titleRow: { flexDirection: 'row', alignItems: 'center', flexWrap: 'wrap', gap: 8 },
  h2: { fontSize: 20, fontWeight: '800', color: '#0F172A', flexShrink: 1 },
  sim: {
    fontSize: 12, fontWeight: '800', color: '#92400E', backgroundColor: '#FEF3C7', paddingHorizontal: 8,
    paddingVertical: 2, borderRadius: 999, overflow: 'hidden',
  },
  p: { fontSize: 18, color: '#334155', lineHeight: 26 },
  small: { fontSize: 15, color: '#64748B', lineHeight: 21 },
  label: { fontSize: 18, fontWeight: '800', color: '#0F172A', marginTop: 4 },
  quote: { fontSize: 18, fontStyle: 'italic', color: '#0F172A', lineHeight: 26 },
  bold: { fontWeight: '800', color: '#0F172A' },
  busy: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  errBox: { gap: 6 },
  err: { fontSize: 17, color: '#DC2626' },
  link: { fontSize: 18, color: '#2563EB', textDecorationLine: 'underline', paddingVertical: 4 },
  play: { flexDirection: 'row', alignItems: 'center', gap: 8, paddingVertical: 6 },
  playText: { fontSize: 18, fontWeight: '700', color: '#2563EB' },
  verdict: { borderWidth: 1, borderRadius: 12, padding: 12 },
  verdictText: { fontSize: 19, fontWeight: '800' },
  place: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  placeText: { flex: 1, fontSize: 18, color: '#334155' },
  scenarios: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  scBtn: { borderWidth: 1, borderColor: '#CBD5E1', borderRadius: 12, paddingVertical: 12, paddingHorizontal: 14 },
  scBtnActive: { backgroundColor: '#2563EB', borderColor: '#2563EB' },
  scText: { fontSize: 18, fontWeight: '700', color: '#0F172A' },
  scTextActive: { color: '#fff' },
  where: { fontSize: 18, fontWeight: '800', color: '#0F172A', flexShrink: 1 },
  big: { fontSize: 36, fontWeight: '900', color: '#0F172A' },
  mapBtn: {
    flexDirection: 'row', alignItems: 'center', gap: 10, padding: 12, borderRadius: 12, borderWidth: 1,
    borderColor: '#E2E8F0', backgroundColor: '#F8FAFC',
  },
  mapText: { flex: 1, fontSize: 17, fontWeight: '700', color: '#0F172A' },
  img: { width: '100%', aspectRatio: 2.6, backgroundColor: '#fff', borderRadius: 8 },
  imgSquare: { width: '100%', aspectRatio: 1.1, backgroundColor: '#fff', borderRadius: 8 },
});
