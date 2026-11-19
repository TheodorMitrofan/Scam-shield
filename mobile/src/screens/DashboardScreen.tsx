import React, { useMemo } from 'react';
import { Pressable, ScrollView, Share, StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { VERDICT_THEME, resultsToCsv, scamTypeLabel } from '../labels';
import { useScamShield } from '../store/ScamShieldContext';

export function DashboardScreen({ onOpenInbox }: { onOpenInbox: () => void }) {
  const { scenarios, results, analyzingIds, selectScenario } = useScamShield();

  const summary = useMemo(() => {
    let scam = 0;
    let suspicious = 0;
    let safe = 0;
    let pending = 0;
    for (const s of scenarios) {
      const r = results[s.id];
      if (analyzingIds.has(s.id) || !r) pending++;
      else if (r.verdict === 'SCAM') scam++;
      else if (r.verdict === 'SUSPICIOUS') suspicious++;
      else safe++;
    }
    return { total: scenarios.length, scam, suspicious, safe, pending };
  }, [analyzingIds, results, scenarios]);

  const onExportCsv = async () => {
    const list = Object.values(results);
    if (!list.length) return;
    await Share.share({
      title: 'scam-shield-results.csv',
      message: resultsToCsv(list),
    });
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <View style={styles.headerRow}>
        <Text style={styles.title}>Tablou rezultate</Text>
        <Pressable
          style={[styles.exportBtn, !Object.keys(results).length && styles.disabled]}
          disabled={!Object.keys(results).length}
          onPress={() => void onExportCsv()}
        >
          <Ionicons name="share-outline" size={16} color="#1E293B" />
          <Text style={styles.exportText}>Export CSV</Text>
        </Pressable>
      </View>

      <View style={styles.statsRow}>
        <View style={styles.statBox}>
          <Text style={styles.statNum}>{summary.total}</Text>
          <Text style={styles.statLbl}>Total</Text>
        </View>
        <View style={[styles.statBox, { backgroundColor: '#FEF2F2', borderColor: '#FCA5A5' }]}>
          <Text style={[styles.statNum, { color: '#991B1B' }]}>{summary.scam}</Text>
          <Text style={[styles.statLbl, { color: '#991B1B' }]}>SCAM</Text>
        </View>
        <View style={[styles.statBox, { backgroundColor: '#FFFBEB', borderColor: '#FCD34D' }]}>
          <Text style={[styles.statNum, { color: '#92400E' }]}>{summary.suspicious}</Text>
          <Text style={[styles.statLbl, { color: '#92400E' }]}>SUSPECT</Text>
        </View>
        <View style={[styles.statBox, { backgroundColor: '#ECFDF5', borderColor: '#6EE7B7' }]}>
          <Text style={[styles.statNum, { color: '#065F46' }]}>{summary.safe}</Text>
          <Text style={[styles.statLbl, { color: '#065F46' }]}>SIGUR</Text>
        </View>
      </View>

      <View style={styles.table}>
        {scenarios.map((s) => {
          const r = results[s.id];
          const theme = r ? VERDICT_THEME[r.verdict] : null;
          return (
            <Pressable
              key={s.id}
              style={styles.row}
              onPress={() => {
                selectScenario(s.id);
                onOpenInbox();
              }}
            >
              <View style={styles.rowTop}>
                <Text style={styles.rowId}>{s.id}</Text>
                {r && theme ? (
                  <View style={[styles.pill, { backgroundColor: theme.bg, borderColor: theme.border }]}>
                    <Text style={[styles.pillText, { color: theme.fg }]}>
                      {r.verdict} · {r.risk_score}/100
                    </Text>
                  </View>
                ) : (
                  <Text style={styles.muted}>{analyzingIds.has(s.id) ? 'Analiză…' : 'Neanalizat'}</Text>
                )}
              </View>
              {r ? (
                <>
                  <Text style={styles.rowType}>
                    {scamTypeLabel(r.scam_type)}
                    {r.verdict !== 'SAFE' && r.first_alert ? ` · prima alertă: #${r.first_alert}` : ''}
                  </Text>
                  {r.red_flags.length > 0 ? (
                    <Text style={styles.rowFlags} numberOfLines={2}>
                      {r.red_flags.join(', ')}
                    </Text>
                  ) : null}
                </>
              ) : null}
            </Pressable>
          );
        })}
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: 14, gap: 12, backgroundColor: '#F8FAFC', paddingBottom: 36 },
  headerRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  title: { fontSize: 22, fontWeight: '800', color: '#0F172A' },
  exportBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    backgroundColor: '#FFFFFF',
    borderWidth: 1,
    borderColor: '#CBD5E1',
    borderRadius: 999,
    paddingHorizontal: 12,
    paddingVertical: 7,
  },
  disabled: { opacity: 0.45 },
  exportText: { fontSize: 13, fontWeight: '700', color: '#1E293B' },
  statsRow: { flexDirection: 'row', gap: 8 },
  statBox: {
    flex: 1,
    backgroundColor: '#FFFFFF',
    borderWidth: 1,
    borderColor: '#E2E8F0',
    borderRadius: 12,
    paddingVertical: 10,
    alignItems: 'center',
  },
  statNum: { fontSize: 22, fontWeight: '800', color: '#0F172A' },
  statLbl: { fontSize: 11, fontWeight: '700', color: '#64748B' },
  table: { gap: 8 },
  row: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 12,
    borderWidth: 1,
    borderColor: '#E2E8F0',
    gap: 4,
  },
  rowTop: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  rowId: { fontSize: 16, fontWeight: '800', color: '#0F172A' },
  pill: { borderWidth: 1, borderRadius: 999, paddingHorizontal: 10, paddingVertical: 3 },
  pillText: { fontSize: 12, fontWeight: '800' },
  rowType: { fontSize: 14, fontWeight: '600', color: '#334155' },
  rowFlags: { fontSize: 12, color: '#64748B' },
  muted: { fontSize: 13, color: '#94A3B8' },
});
