// Mirrors CLAUDE.md §4.2 "Fraud report" (backend/app/schemas/report.py).
import { AnalysisResult, Channel, Scenario, Verdict } from './scenario';

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
  incident_date: string | null; // YYYY-MM-DD
  incident_time: string | null; // HH:MM
  lost_money: boolean;
  amount_lost: number | null;
  bank: string | null;
  additional_details: string | null;
}

export interface ReportIndicator {
  kind: 'url' | 'email' | 'phone' | 'iban' | 'amount';
  value: string;
  display: string; // defanged — show this one
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

export interface ReportDraftRequest {
  scenario: Scenario;
  result?: AnalysisResult | null;
}

/** Brief: the report only exists for SCAM results. */
export const REPORT_MIN_SCORE = 50;
