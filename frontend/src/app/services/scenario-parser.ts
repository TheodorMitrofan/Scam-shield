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

export function byId(a: Scenario, b: Scenario): number {
  return a.id.localeCompare(b.id, undefined, { numeric: true });
}
