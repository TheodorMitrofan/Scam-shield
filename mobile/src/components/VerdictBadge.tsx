import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { CHANNEL_COLOR, CHANNEL_LABEL, VERDICT_LABEL, VERDICT_THEME } from '../labels';
import { AnalysisResult, Scenario } from '../types';

export function VerdictBadge({
  scenario,
  result,
  compact = false,
}: {
  scenario: Scenario;
  result: AnalysisResult | null | undefined;
  compact?: boolean;
}) {
  if (!result) {
    const color = CHANNEL_COLOR[scenario.channel];
    return (
      <View style={[styles.badge, { backgroundColor: `${color}18`, borderColor: `${color}44` }]}>
        <Text style={[styles.text, { color }]}>{CHANNEL_LABEL[scenario.channel]}</Text>
      </View>
    );
  }
  const theme = VERDICT_THEME[result.verdict];
  return (
    <View style={[styles.badge, { backgroundColor: theme.bg, borderColor: theme.border }]}>
      <Ionicons name={theme.icon} size={14} color={theme.fg} />
      <Text style={[styles.text, { color: theme.fg }]} numberOfLines={1}>
        {compact ? result.verdict : VERDICT_LABEL[result.verdict]}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 999,
    borderWidth: 1,
    alignSelf: 'flex-start',
    maxWidth: '100%',
  },
  text: {
    fontSize: 13,
    fontWeight: '700',
    flexShrink: 1,
  },
});
