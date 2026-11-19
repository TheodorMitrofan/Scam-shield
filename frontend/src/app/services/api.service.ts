import { Injectable, inject } from '@angular/core';
import { API_BASE } from '../api.config';
import {
  FraudReportDraft,
  PersonalData,
  ReportDraftRequest,
  ReportSendResponse,
} from '../models/report';
import { AnalysisResult, Scenario } from '../models/scenario';
import { AuthService } from './auth.service';

export interface SavedConversationDto {
  id: string;
  external_id: string;
  owner_username?: string | null;
  owner_role?: 'admin' | 'user' | null;
  scenario: Scenario;
  result: AnalysisResult;
}

/** CLAUDE.md §4.1 — same shape whether or not the user consented to saving. */
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

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

const CLIENT_ID_KEY = 'scamshield-client-id';

/** Thin fetch wrapper around the FastAPI backend. Message text is never logged here. */
@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly auth = inject(AuthService);

  health(): Promise<HealthResponse> {
    return this.request('GET', '/health');
  }

  validationSet(): Promise<Scenario[]> {
    return this.request('GET', '/scenarios/validation');
  }

  historyConversations(): Promise<SavedConversationDto[]> {
    return this.request('GET', '/history/conversations');
  }

  analyze(scenario: Scenario, save: boolean): Promise<AnalyzeResponse> {
    return this.request('POST', `/analyze?save=${save}`, scenario);
  }

  analyzeBatch(scenarios: Scenario[], save: boolean): Promise<AnalyzeResponse[]> {
    return this.request('POST', `/analyze/batch?save=${save}`, scenarios);
  }

  // Fraud report (CLAUDE.md §4.1) — only for risk_score ≥ 50 --------------------------------

  reportDraft(body: ReportDraftRequest): Promise<FraudReportDraft> {
    return this.request('POST', '/report/draft', body);
  }

  reportSend(report: FraudReportDraft, personal_data: PersonalData): Promise<ReportSendResponse> {
    return this.request('POST', '/report/send', { report, personal_data });
  }

  /** The „Sesizare” PDF as a Blob (not JSON, so it bypasses `request`). */
  async reportPdf(report: FraudReportDraft, personal_data: PersonalData): Promise<Blob> {
    let res: Response;
    try {
      res = await fetch(`${API_BASE}/report/pdf`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ report, personal_data }),
      });
    } catch {
      throw new ApiError(0, 'Serverul nu răspunde. Porniți backend-ul (port 8000).');
    }
    if (!res.ok) throw new ApiError(res.status, await this.errorDetail(res));
    return res.blob();
  }

  /** Anonymous id the backend gives us on the first saved conversation (opt-in history). */
  private get clientId(): string | null {
    try {
      return localStorage.getItem(CLIENT_ID_KEY);
    } catch {
      return null;
    }
  }

  private rememberClientId(res: unknown): void {
    const list = Array.isArray(res) ? res : [res];
    const id = list.find(
      (r) => r && typeof r === 'object' && 'client_id' in r && r.client_id,
    )?.client_id;
    if (!id) return;
    try {
      localStorage.setItem(CLIENT_ID_KEY, id);
    } catch {
      /* storage blocked: history just won't be grouped across reloads */
    }
  }

  private async request<T>(method: string, path: string, body?: unknown): Promise<T> {
    const headers: Record<string, string> = {};
    if (body !== undefined) headers['Content-Type'] = 'application/json';
    const user = this.auth.user();
    if (user) {
      headers['X-User-Id'] = user.id;
      headers['X-Client-Id'] = user.id;
    } else if (this.clientId) {
      headers['X-Client-Id'] = this.clientId;
    }

    let res: Response;
    try {
      res = await fetch(`${API_BASE}${path}`, {
        method,
        headers,
        body: body === undefined ? undefined : JSON.stringify(body),
      });
    } catch {
      throw new ApiError(0, 'Serverul de analiză nu răspunde. Porniți backend-ul (port 8000).');
    }
    if (!res.ok) throw new ApiError(res.status, await this.errorDetail(res));
    const data = (await res.json()) as T;
    this.rememberClientId(data);
    return data;
  }

  /** FastAPI errors: `detail` is a string, or a list of validation errors (422) with `msg`. */
  private async errorDetail(res: Response): Promise<string> {
    try {
      const j = await res.json();
      if (typeof j?.detail === 'string') return j.detail;
      if (Array.isArray(j?.detail) && j.detail.length) {
        return j.detail
          .map((d: { msg?: string }) => (d.msg ?? '').replace(/^Value error, /, ''))
          .join(' ');
      }
    } catch {
      /* non-JSON error body */
    }
    return `Eroare ${res.status}`;
  }
}
