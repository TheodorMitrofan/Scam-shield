/** Data contracts mirroring CLAUDE.md §4.2. */

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
  start_s?: number;
  end_s?: number;
}

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

export interface AnalyzeResponse {
  result: AnalysisResult;
  saved: boolean;
  conversation_id: string | null;
  client_id: string | null;
}

export interface HealthResponse {
  status: string;
  model_loaded: boolean;
  detector_stub: boolean;
  db_connected: boolean;
}

export interface PersonalField {
  key: keyof PersonalData;
  label: string;
  type: 'text' | 'email' | 'tel' | 'date' | 'time' | 'number' | 'checkbox' | 'textarea';
  required: boolean;
  hint?: string | null;
}

export interface PersonalData {
  last_name: string | null;
  first_name: string | null;
  cnp: string | null;
  id_series_number: string | null;
  address: string | null;
  phone: string | null;
  email: string | null;
  incident_date: string | null;
  incident_time: string | null;
  lost_money: boolean;
  amount_lost: number | null;
  bank: string | null;
  additional_details: string | null;
}

export interface ReportIndicator {
  kind: 'url' | 'email' | 'phone' | 'iban' | 'amount';
  value: string;
  display: string;
  message_n: number | null;
}

export interface Incident {
  scenario_id: string;
  channel: Channel;
  channel_label: string;
  sender: { name: string | null; address: string | null; known_contact: boolean };
  verdict: Verdict;
  scam_type: string;
  scam_type_label: string;
  risk_score: number;
  first_alert: number | null;
  red_flags: { code: string; label: string }[];
  summary_ro: string;
  timeline: {
    n: number;
    author: 'sender' | 'reader';
    author_label: string;
    text: string;
    is_first_alert: boolean;
  }[];
  indicators: ReportIndicator[];
}

export interface FraudReportDraft {
  report_id: string;
  generated_at: string;
  recipient: string;
  incident: Incident;
  personal_data: PersonalData;
  personal_fields: PersonalField[];
}

export interface ReportSendResponse {
  sent: boolean;
  recipient: string;
  message_id: string;
  sent_at: string;
}

export interface AudioAuditResult {
  engine: 'standard' | 'dopplergeist';
  duration_s: number;
  risk: 'high' | 'medium' | 'low' | 'undetermined';
  flyovers: number;
  events: { t0: number; t1: number; fmin: number; fmax: number; speed_kmh: number | null; distance_m: number | null }[];
  rejected: number;
  status: string;
  limited: boolean;
  reasons: string[];
  spectrogram: string | null;
}
