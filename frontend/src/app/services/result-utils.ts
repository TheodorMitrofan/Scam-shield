import { AnalysisResult, CHANNEL_LABEL, Scenario, Verdict } from '../models/scenario';

export type TagSeverity = 'success' | 'warn' | 'danger' | 'info' | 'secondary';

/** Exact UI labels required by the brief („Scoring system” → verdict bands). Do not reword. */
export const VERDICT_LABEL: Record<Verdict, string> = {
  SCAM: 'Pare o țeapă! Nu răspundeți',
  SUSPICIOUS: 'Atenție, verificați înainte să răspundeți',
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

/** Plain-Romanian names for the official scam types (no jargon in the UI). */
export const SCAM_TYPE_LABEL: Record<string, string> = {
  BANK_IMPERSONATION: 'Se dă drept bancă',
  COURIER_FEE: 'Taxă falsă de curier',
  AUTHORITY_IMPERSONATION: 'Se dă drept o instituție',
  FAMILY_EMERGENCY: 'Rudă în necaz (număr nou)',
  TECH_SUPPORT: 'Fals suport tehnic',
  MARKETPLACE: 'Cumpărător fals',
  ACCOUNT_TAKEOVER: 'Cont furat, cere un cod',
  INVESTMENT: 'Investiție falsă',
  ROMANCE: 'Prietenie falsă, cere bani',
  JOB_OFFER: 'Ofertă de muncă falsă',
  PRIZE_LOTTERY: 'Premiu fals',
  OTHER: 'Altă înșelătorie',
  NONE: 'Mesaj obișnuit',
};

/** Plain-Romanian names for the official red flags, shown on each message. */
export const FLAG_LABEL: Record<string, string> = {
  RF_CODE_REQUEST: 'Cere un cod primit prin SMS',
  RF_REMOTE_ACCESS: 'Cere să instalați un program',
  RF_DATA_REQUEST: 'Cere datele cardului sau parole',
  RF_PAYMENT_REQUEST: 'Cere bani',
  RF_SUSPICIOUS_CONTACT: 'Adresă sau număr neoficial',
  RF_NEW_NUMBER: 'Număr nou, se dă drept rudă',
  RF_SECRECY: 'Cere să păstrați secretul',
  RF_TOO_GOOD: 'Prea frumos ca să fie adevărat',
  RF_IMPERSONATION: 'Se dă drept altcineva',
  RF_URGENCY: 'Vă grăbește',
  RF_THREAT: 'Vă sperie (cont blocat, amendă)',
  RF_EMOTIONAL_PRESSURE: 'Joacă pe emoții',
  RF_CHANNEL_SWITCH: 'Vă mută pe altă aplicație',
};

export interface TextSegment {
  text: string;
  /** Red flag that made this piece dangerous, or null for ordinary text. */
  flag: string | null;
}

/**
 * Splits a message into ordinary and dangerous pieces, using the detector's evidence spans
 * ([start, end) character offsets into the ORIGINAL message text). Overlapping spans are merged;
 * out-of-range spans are clipped, so bad offsets can never break the text.
 */
export function evidenceSegments(
  result: AnalysisResult | null | undefined,
  n: number,
  text: string,
): TextSegment[] {
  const spans = (result?.evidence ?? [])
    .filter((e) => e.n === n && Array.isArray(e.span))
    .map((e) => ({
      start: Math.max(0, Math.min(text.length, e.span[0])),
      end: Math.max(0, Math.min(text.length, e.span[1])),
      flag: e.flag,
    }))
    .filter((s) => s.end > s.start)
    .sort((a, b) => a.start - b.start);
  if (!spans.length) return [{ text, flag: null }];
  const out: TextSegment[] = [];
  let pos = 0;
  for (const s of spans) {
    if (s.end <= pos) continue; // fully inside an earlier span
    const start = Math.max(s.start, pos);
    if (start > pos) out.push({ text: text.slice(pos, start), flag: null });
    out.push({ text: text.slice(start, s.end), flag: s.flag });
    pos = s.end;
  }
  if (pos < text.length) out.push({ text: text.slice(pos), flag: null });
  return out;
}

export function flagLabel(code: string): string {
  return FLAG_LABEL[code] ?? code;
}

export function scamTypeLabel(code: string): string {
  return SCAM_TYPE_LABEL[code] ?? code;
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
