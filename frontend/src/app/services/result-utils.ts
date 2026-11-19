import { AnalysisResult, CHANNEL_LABEL, Scenario, Verdict } from '../models/scenario';

export type TagSeverity = 'success' | 'warn' | 'danger' | 'info' | 'secondary';

export const VERDICT_LABEL: Record<Verdict, string> = {
  SCAM: 'Pare o țeapă',
  SUSPICIOUS: 'Atenție',
  SAFE: 'Pare în regulă',
};

const VERDICT_SEVERITY: Record<Verdict, TagSeverity> = {
  SCAM: 'danger',
  SUSPICIOUS: 'warn',
  SAFE: 'success',
};

/** Tag shown on a card / detail: the verdict when analysed, otherwise the channel. */
export function tagOf(
  s: Scenario,
  result: AnalysisResult | null | undefined,
): { label: string; severity: TagSeverity } {
  return result
    ? { label: VERDICT_LABEL[result.verdict], severity: VERDICT_SEVERITY[result.verdict] }
    : { label: CHANNEL_LABEL[s.channel], severity: 'info' };
}

export function senderOf(s: Scenario): string {
  return s.sender.name ?? s.sender.address ?? 'Expeditor necunoscut';
}

/** Red flags first detected in message n (empty until the detector is wired in). */
export function flagsAt(result: AnalysisResult | null | undefined, n: number): string[] {
  return result?.flags_by_message.find((m) => m.n === n)?.flags ?? [];
}

export function isFirstAlert(result: AnalysisResult | null | undefined, n: number): boolean {
  return !!result && result.first_alert === n;
}
