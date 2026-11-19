import { AnalysisResult, CHANNELS, Channel, Message, Scenario, Verdict } from './types';

export const REPORT_MIN_SCORE = 50;

export const VERDICT_LABEL: Record<Verdict, string> = {
  SCAM: 'Pare o țeapă! Nu răspundeți',
  SUSPICIOUS: 'Atenție, verificați înainte să răspundeți',
  SAFE: 'Pare în regulă',
};

export const VERDICT_SHORT: Record<Verdict, string> = {
  SCAM: 'SCAM',
  SUSPICIOUS: 'SUSPECT',
  SAFE: 'SIGUR',
};

export const VERDICT_THEME: Record<
  Verdict,
  { bg: string; border: string; fg: string; pill: string; icon: 'close-circle' | 'warning' | 'checkmark-circle' }
> = {
  SCAM: { bg: '#FEF2F2', border: '#FCA5A5', fg: '#991B1B', pill: '#DC2626', icon: 'close-circle' },
  SUSPICIOUS: { bg: '#FFFBEB', border: '#FCD34D', fg: '#92400E', pill: '#D97706', icon: 'warning' },
  SAFE: { bg: '#ECFDF5', border: '#6EE7B7', fg: '#065F46', pill: '#059669', icon: 'checkmark-circle' },
};

export const CHANNEL_LABEL: Record<Channel, string> = {
  sms: 'SMS',
  whatsapp: 'WhatsApp',
  email: 'E-mail',
  chat: 'Chat',
  call_transcript: 'Apel telefonic',
};

export const CHANNEL_COLOR: Record<Channel, string> = {
  sms: '#2563EB',
  whatsapp: '#16A34A',
  email: '#7C3AED',
  chat: '#0284C7',
  call_transcript: '#EA580C',
};

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

export function flagLabel(code: string): string {
  return FLAG_LABEL[code] ?? code;
}

export function scamTypeLabel(code: string): string {
  return SCAM_TYPE_LABEL[code] ?? code;
}

export function senderOf(s: Scenario): string {
  return s.sender.name ?? s.sender.address ?? 'Expeditor necunoscut';
}

export function flagsAt(result: AnalysisResult | null | undefined, n: number): string[] {
  return result?.flags_by_message.find((m) => m.n === n)?.flags ?? [];
}

export function isFirstAlert(result: AnalysisResult | null | undefined, n: number): boolean {
  return !!result && result.first_alert === n;
}

/** Lowercase + strip diacritics for search & speaker detection. */
export function normalizeText(s: string): string {
  return s
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase();
}

export function parseScenario(raw: unknown, fallbackId: string): Scenario {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) {
    throw new Error('Fișierul nu conține un scenariu (obiect JSON).');
  }
  const o = raw as Record<string, unknown>;
  const channel: Channel = CHANNELS.includes(o.channel as Channel) ? (o.channel as Channel) : 'sms';
  const s = (o.sender ?? {}) as Record<string, unknown>;
  const rawMessages = Array.isArray(o.messages) ? o.messages : [];
  const messages: Message[] = rawMessages.map((m, i) => {
    const mm = (m ?? {}) as Record<string, unknown>;
    return {
      n: typeof mm.n === 'number' ? mm.n : i + 1,
      from: mm.from === 'reader' ? 'reader' : 'sender',
      text: typeof mm.text === 'string' ? mm.text : String(mm.text ?? ''),
      ...(typeof mm.start_s === 'number' ? { start_s: mm.start_s } : {}),
      ...(typeof mm.end_s === 'number' ? { end_s: mm.end_s } : {}),
    };
  });
  return {
    id: typeof o.id === 'string' && o.id ? o.id : fallbackId,
    channel,
    sender: {
      name: typeof s.name === 'string' ? s.name : null,
      address: typeof s.address === 'string' ? s.address : null,
      known_contact: s.known_contact === true,
    },
    messages,
    ...(o.audio ? { audio: o.audio as Scenario['audio'] } : {}),
  };
}

const READER_LABELS = new Set([
  'eu', 'eu1', 'eu2', 'dvs', 'dumneavoastra', 'cititor', 'reader', 'me', 'raspuns', 'victima',
]);
const SPEAKER_RE = /^\s*([A-Za-zĂÂÎȘȚăâîșț][A-Za-zĂÂÎȘȚăâîșț0-9 ._-]{0,24}?)\s*:\s+(.*)$/;

export function scenarioFromText(
  text: string,
  opts: { channel: Channel; senderName?: string; senderAddress?: string; knownContact?: boolean },
  id = 'PASTE',
): Scenario {
  const lines = text.replace(/\r\n?/g, '\n').split('\n');
  const labelled = lines.filter((l) => SPEAKER_RE.test(l)).length;
  const sender = {
    name: opts.senderName?.trim() || null,
    address: opts.senderAddress?.trim() || null,
    known_contact: !!opts.knownContact,
  };
  if (labelled < 2) {
    return {
      id,
      channel: opts.channel,
      sender,
      messages: [{ n: 1, from: 'sender', text: text.trim() }],
    };
  }
  const speakerRoles = new Map<string, 'sender' | 'reader'>();
  const messages: Message[] = [];
  for (const line of lines) {
    const m = SPEAKER_RE.exec(line);
    if (m) {
      const key = normalizeText(m[1]).trim();
      let role = speakerRoles.get(key);
      if (!role) {
        if (READER_LABELS.has(key)) role = 'reader';
        else role = speakerRoles.size === 0 ? 'sender' : 'reader';
        speakerRoles.set(key, role);
      }
      messages.push({ n: messages.length + 1, from: role, text: m[2].trim() });
    } else if (messages.length && line.trim()) {
      messages[messages.length - 1].text += '\n' + line.trim();
    }
  }
  return { id, channel: opts.channel, sender, messages };
}

function csvCell(v: string | number | null | undefined): string {
  const s = v == null ? '' : String(v);
  return /[",\r\n]/.test(s) ? `"${s.replaceAll('"', '""')}"` : s;
}

export function resultsToCsv(results: AnalysisResult[]): string {
  const header = 'id,verdict,scam_type,risk_score,first_alert,red_flags';
  const rows = [...results]
    .sort((a, b) => a.id.localeCompare(b.id))
    .map((r) =>
      [
        csvCell(r.id),
        csvCell(r.verdict),
        csvCell(r.scam_type),
        csvCell(r.risk_score),
        csvCell(r.verdict === 'SAFE' ? '' : (r.first_alert ?? '')),
        csvCell(r.red_flags.join(';')),
      ].join(','),
    );
  return [header, ...rows].join('\n');
}
