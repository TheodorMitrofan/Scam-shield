import { CHANNELS, Channel, Message, Scenario } from '../models/scenario';

/**
 * Turns arbitrary JSON into a Scenario without ever throwing on content
 * (brief: empty / very long / emoji-only / diacritic-free input must not crash).
 * Throws only when the file is not a scenario at all, with a readable message.
 */
export function parseScenario(raw: unknown, fallbackId: string): Scenario {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) {
    throw new Error('Fișierul nu conține un scenariu (obiect JSON).');
  }
  const o = raw as Record<string, unknown>;

  const channel: Channel = CHANNELS.includes(o['channel'] as Channel)
    ? (o['channel'] as Channel)
    : 'sms';

  const s = (o['sender'] ?? {}) as Record<string, unknown>;
  const sender = {
    name: typeof s['name'] === 'string' ? s['name'] : null,
    address: typeof s['address'] === 'string' ? s['address'] : null,
    known_contact: s['known_contact'] === true,
  };

  const rawMessages = Array.isArray(o['messages']) ? o['messages'] : [];
  const messages: Message[] = rawMessages.map((m, i) => {
    const mm = (m ?? {}) as Record<string, unknown>;
    return {
      n: typeof mm['n'] === 'number' ? mm['n'] : i + 1,
      from: mm['from'] === 'reader' ? 'reader' : 'sender',
      text: typeof mm['text'] === 'string' ? mm['text'] : String(mm['text'] ?? ''),
      ...(typeof mm['start_s'] === 'number' ? { start_s: mm['start_s'] } : {}),
      ...(typeof mm['end_s'] === 'number' ? { end_s: mm['end_s'] } : {}),
    };
  });

  return {
    id: typeof o['id'] === 'string' && o['id'] ? o['id'] : fallbackId,
    channel,
    sender,
    messages,
    ...(o['audio'] ? { audio: o['audio'] as Scenario['audio'] } : {}),
  };
}

/** Wraps pasted free text as a 1-message scenario (same shape as POST /api/analyze/text). */
export function scenarioFromText(text: string, channel: Channel = 'sms'): Scenario {
  return {
    id: 'PASTE',
    channel,
    sender: { name: null, address: null, known_contact: false },
    messages: [{ n: 1, from: 'sender', text }],
  };
}

export interface PastedConversation {
  channel: Channel;
  senderName: string;
  senderAddress: string;
  knownContact: boolean;
  /** Flip who is the sender and who is the reader. */
  swap: boolean;
}

/** Labels that always mean "the person we protect" (normalised: lowercase, no diacritics). */
const READER_LABELS = new Set([
  'eu', 'eu1', 'eu2', 'dvs', 'dumneavoastra', 'cititor', 'reader', 'me', 'raspuns', 'victima',
]);

// "Exp1: text", "Banca Dunărea: text" — the label starts with a letter, so "12:00" and URLs never match.
const SPEAKER = /^\s*([\p{L}][\p{L}\p{N} ._-]{0,24}?)\s*:\s+(.*)$/u;

const norm = (s: string) => s.normalize('NFD').replace(/\p{M}/gu, '').toLowerCase().trim();

/**
 * Turns pasted text into a scenario. A conversation is written one message per line with the speaker
 * in front ("exp1: …" ⏎ "exp2: …"). The first speaker is the sender, the second the reader (or any
 * label like "Eu:" / "Dvs:"). Lines without a label continue the previous message. With fewer than two
 * labelled lines, the whole text is kept as a single message, so "Banca Dunărea: Codul…" stays intact.
 */
export function scenarioFromConversation(text: string, opts: PastedConversation, id = 'PASTE'): Scenario {
  const lines = text.replace(/\r\n?/g, '\n').split('\n');
  const labelled = lines.filter((l) => SPEAKER.test(l)).length;

  const sender = {
    name: opts.senderName.trim() || null,
    address: opts.senderAddress.trim() || null,
    known_contact: opts.knownContact,
  };

  if (labelled < 2) {
    return {
      id,
      channel: opts.channel,
      sender,
      messages: [{ n: 1, from: opts.swap ? 'reader' : 'sender', text: text.trim() }],
    };
  }

  // Decide which labels belong to the reader.
  const order: string[] = [];
  for (const l of lines) {
    const m = l.match(SPEAKER);
    if (m && !order.includes(norm(m[1]))) order.push(norm(m[1]));
  }
  // Use the reader keywords only if they split the speakers into two sides; otherwise go by order.
  const explicitReader =
    order.some((k) => READER_LABELS.has(k)) && order.some((k) => !READER_LABELS.has(k));
  const isReader = (key: string) => {
    const r = explicitReader ? READER_LABELS.has(key) : key === order[1];
    return opts.swap ? !r : r;
  };

  const messages: Message[] = [];
  let firstSenderLabel: string | null = null;
  for (const line of lines) {
    const m = line.match(SPEAKER);
    if (m) {
      const from = isReader(norm(m[1])) ? 'reader' : 'sender';
      if (from === 'sender' && !firstSenderLabel) firstSenderLabel = m[1].trim();
      messages.push({ n: messages.length + 1, from, text: m[2].trim() });
    } else if (line.trim()) {
      const last = messages.at(-1);
      if (last) last.text = `${last.text}\n${line.trim()}`;
      else messages.push({ n: 1, from: opts.swap ? 'reader' : 'sender', text: line.trim() });
    }
  }

  // Generic labels like "exp1" say nothing about who the sender is; real names do.
  if (!sender.name && firstSenderLabel && !/^(exp|expeditor|el|ea|tu|dl|dna)\s*\d*$/i.test(norm(firstSenderLabel))) {
    sender.name = firstSenderLabel;
  }
  return { id, channel: opts.channel, sender, messages };
}

export function byId(a: Scenario, b: Scenario): number {
  return a.id.localeCompare(b.id, undefined, { numeric: true });
}
