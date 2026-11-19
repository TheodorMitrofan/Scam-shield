// Mirrors CLAUDE.md §4.2 — keep in sync with the contract, do not invent fields here.

export type Channel = 'sms' | 'whatsapp' | 'email' | 'chat' | 'call_transcript';
export const CHANNELS: Channel[] = ['sms', 'whatsapp', 'email', 'chat', 'call_transcript'];

export interface Sender {
  name: string | null;
  address: string | null;
  known_contact: boolean;
}

export interface Message {
  n: number;
  from: 'sender' | 'reader';
  text: string;
  /** Stage 4 extension: position of this utterance inside the audio file. */
  start_s?: number;
  end_s?: number;
}

/** Stage 4 extension: a scenario produced from an uploaded audio file. */
export interface AudioRef {
  audio_id: string;
  mime: string;
  duration_s: number;
  location?: { region: string; confidence: number };
}

export interface Scenario {
  id: string;
  channel: Channel;
  sender: Sender;
  messages: Message[];
  audio?: AudioRef;
}

export type Verdict = 'SAFE' | 'SUSPICIOUS' | 'SCAM';

export interface AnalysisResult {
  id: string;
  verdict: Verdict;
  scam_type: string;
  risk_score: number;
  first_alert: number | null;
  red_flags: string[];
  flags_by_message: { n: number; flags: string[]; score_after: number }[];
  warning: { ro: string; en?: string };
  evidence?: { n: number; flag: string; span: [number, number] }[];
}

/** UI grouping: how a channel is rendered. Audio scenarios reuse the call layout. */
export type ViewKind = 'chat' | 'email' | 'call';

export function viewKindOf(channel: Channel): ViewKind {
  switch (channel) {
    case 'email':
      return 'email';
    case 'call_transcript':
      return 'call';
    default:
      return 'chat';
  }
}

export const CHANNEL_LABEL: Record<Channel, string> = {
  sms: 'SMS',
  whatsapp: 'WhatsApp',
  email: 'E-mail',
  chat: 'Chat',
  call_transcript: 'Apel telefonic',
};
