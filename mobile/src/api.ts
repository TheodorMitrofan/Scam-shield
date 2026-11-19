import AsyncStorage from '@react-native-async-storage/async-storage';
import Constants from 'expo-constants';
import { Platform } from 'react-native';
import {
  AnalysisResult,
  AnalyzeResponse,
  AudioAuditResult,
  FraudReportDraft,
  HealthResponse,
  PersonalData,
  ReportSendResponse,
  Scenario,
} from './types';

const CLIENT_ID_KEY = 'scamshield-client-id';
const API_BASE_KEY = 'scamshield-api-base';
const AUDIO_BASE_KEY = 'scamshield-audio-base';

/** Detect the Mac/PC LAN IP from Expo's dev server URI so real iPhones/Androids connect over Wi-Fi. */
export function defaultHost(): string {
  const hostUri =
    Constants.expoConfig?.hostUri ??
    (Constants as unknown as { manifest2?: { extra?: { expoClient?: { hostUri?: string } } } })
      .manifest2?.extra?.expoClient?.hostUri;
  if (hostUri && typeof hostUri === 'string') {
    const host = hostUri.split(':')[0];
    if (host && host !== 'localhost' && host !== '127.0.0.1') return host;
  }
  return Platform.OS === 'android' ? '10.0.2.2' : 'localhost';
}

export function defaultApiBase(): string {
  return `http://${defaultHost()}:8000/api`;
}

export function defaultAudioBase(): string {
  return `http://${defaultHost()}:8002/api/audio`;
}

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

async function errorDetail(res: Response): Promise<string> {
  try {
    const j = await res.json();
    if (typeof j?.detail === 'string') return j.detail;
    if (Array.isArray(j?.detail) && j.detail.length) {
      return j.detail.map((d: { msg?: string }) => (d.msg ?? '').replace(/^Value error, /, '')).join(' ');
    }
  } catch {
    /* ignore */
  }
  return `Eroare ${res.status}`;
}

export async function getStoredApiUrls(): Promise<{ apiBase: string; audioBase: string }> {
  const [a, b] = await Promise.all([
    AsyncStorage.getItem(API_BASE_KEY),
    AsyncStorage.getItem(AUDIO_BASE_KEY),
  ]);
  return {
    apiBase: (a && a.trim()) || defaultApiBase(),
    audioBase: (b && b.trim()) || defaultAudioBase(),
  };
}

export async function setStoredApiUrls(apiBase: string, audioBase: string): Promise<void> {
  await Promise.all([
    AsyncStorage.setItem(API_BASE_KEY, apiBase.replace(/\/+$/, '')),
    AsyncStorage.setItem(AUDIO_BASE_KEY, audioBase.replace(/\/+$/, '')),
  ]);
}

async function request<T>(base: string, method: string, path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = {};
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  const cid = await AsyncStorage.getItem(CLIENT_ID_KEY);
  if (cid) headers['X-Client-Id'] = cid;

  let res: Response;
  try {
    res = await fetch(`${base}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError(0, `Serverul nu răspunde (${base}). Verificați backend-ul și Wi-Fi.`);
  }
  if (!res.ok) throw new ApiError(res.status, await errorDetail(res));
  const data = (await res.json()) as T;
  const list = Array.isArray(data) ? data : [data];
  const nextCid = list.find((r) => r && typeof r === 'object' && 'client_id' in r && r.client_id)?.client_id;
  if (typeof nextCid === 'string' && nextCid) {
    await AsyncStorage.setItem(CLIENT_ID_KEY, nextCid);
  }
  return data;
}

export const mobileApi = {
  health: (base: string) => request<HealthResponse>(base, 'GET', '/health'),
  validationSet: (base: string) => request<Scenario[]>(base, 'GET', '/scenarios/validation'),
  analyze: (base: string, scenario: Scenario, save: boolean) =>
    request<AnalyzeResponse>(base, 'POST', `/analyze?save=${save}`, scenario),
  analyzeBatch: (base: string, scenarios: Scenario[], save: boolean) =>
    request<AnalyzeResponse[]>(base, 'POST', `/analyze/batch?save=${save}`, scenarios),
  reportDraft: (base: string, scenario: Scenario, result?: AnalysisResult | null) =>
    request<FraudReportDraft>(base, 'POST', '/report/draft', { scenario, ...(result ? { result } : {}) }),
  reportSend: (base: string, report: FraudReportDraft, personal_data: PersonalData) =>
    request<ReportSendResponse>(base, 'POST', '/report/send', { report, personal_data }),

  async audioHealth(audioBase: string): Promise<{ status: string; demo_ready: string[] } | null> {
    try {
      const r = await fetch(`${audioBase}/health`);
      return r.ok ? ((await r.json()) as { status: string; demo_ready: string[] }) : null;
    } catch {
      return null;
    }
  },

  async audioAudit(
    audioBase: string,
    file: { uri: string; name: string; mimeType?: string },
    engine: 'standard' | 'dopplergeist' = 'standard',
  ): Promise<AudioAuditResult> {
    const fd = new FormData();
    fd.append('file', {
      uri: file.uri,
      name: file.name,
      type: file.mimeType || 'audio/wav',
    } as unknown as Blob);
    let res: Response;
    try {
      res = await fetch(`${audioBase}/audit?engine=${engine}`, { method: 'POST', body: fd });
    } catch {
      throw new ApiError(0, `Serviciul audio nu răspunde (${audioBase}).`);
    }
    if (!res.ok) throw new ApiError(res.status, await errorDetail(res));
    return (await res.json()) as AudioAuditResult;
  },
};
