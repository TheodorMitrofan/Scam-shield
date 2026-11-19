import { Injectable } from '@angular/core';
import { API_BASE } from '../api.config';
import { AnalysisResult, Scenario } from '../models/scenario';

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
  health(): Promise<HealthResponse> {
    return this.request('GET', '/health');
  }

  validationSet(): Promise<Scenario[]> {
    return this.request('GET', '/scenarios/validation');
  }

  analyze(scenario: Scenario, save: boolean): Promise<AnalyzeResponse> {
    return this.request('POST', `/analyze?save=${save}`, scenario);
  }

  analyzeBatch(scenarios: Scenario[], save: boolean): Promise<AnalyzeResponse[]> {
    return this.request('POST', `/analyze/batch?save=${save}`, scenarios);
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
    const id = list.find((r) => r && typeof r === 'object' && 'client_id' in r && r.client_id)?.client_id;
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
    if (this.clientId) headers['X-Client-Id'] = this.clientId;

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
    if (!res.ok) {
      let detail = `Eroare ${res.status}`;
      try {
        const j = await res.json();
        if (typeof j?.detail === 'string') detail = j.detail;
      } catch {
        /* non-JSON error body */
      }
      throw new ApiError(res.status, detail);
    }
    const data = (await res.json()) as T;
    this.rememberClientId(data);
    return data;
  }
}
