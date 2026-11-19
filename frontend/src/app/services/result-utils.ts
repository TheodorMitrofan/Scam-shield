import { AnalysisResult } from '../models/scenario';

/** Red flags first detected in message n (empty until the detector is wired in). */
export function flagsAt(result: AnalysisResult | null | undefined, n: number): string[] {
  return result?.flags_by_message.find((m) => m.n === n)?.flags ?? [];
}

export function isFirstAlert(result: AnalysisResult | null | undefined, n: number): boolean {
  return !!result && result.first_alert === n;
}
