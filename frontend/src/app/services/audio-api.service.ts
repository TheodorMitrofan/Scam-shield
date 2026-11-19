import { Injectable } from '@angular/core';
import { AUDIO_API_BASE } from '../api.config';

export type AuditRisk = 'high' | 'medium' | 'low' | 'undetermined';
export type AuditEngine = 'standard' | 'dopplergeist';

export interface AuditResult {
  engine: AuditEngine;
  duration_s: number;
  risk: AuditRisk;
  flyovers: number;
  /** Only candidates that passed the Doppler physics check (real aircraft). */
  events: { t0: number; t1: number; fmin: number; fmax: number; speed_kmh: number | null; distance_m: number | null }[];
  /** Candidates that looked tonal but failed the physics check (speech, music, hum). */
  rejected: number;
  status: string;
  /** Short or mostly gated recording: the check is only indicative. */
  limited: boolean;
  reasons: string[];
  spectrogram: string | null; // data:image/png;base64
}

export interface DemoFlight {
  id: string;
  type: string;
  prop: boolean;
  matched: boolean;
  points: [number, number][]; // [lat, lon]
}

export type DemoScenario = 'uk' | 'de' | 'us';

export interface DemoResult {
  ok: boolean;
  reason?: string;
  scenario: DemoScenario;
  country: string;
  place: string;
  conversation_label?: string;
  seed: number;
  runtime_s: number;
  recording_s: number;
  truth: { lat: number; lon: number };
  estimate: { lat: number; lon: number };
  error_m: number;
  region_radius_m: number;
  bbox: [number, number, number, number]; // lat_min, lat_max, lon_min, lon_max
  candidates_scored: number;
  events: { v_ms: number; d_m: number; t_cpa_s: number; f0_hz: number }[];
  matched_flights: { id: string; type: string }[];
  flights: DemoFlight[];
  spectrogram: string;
  heatmap: string;
}

/** Client for the separate audio service (port 8002). Not part of the scam detector. */
@Injectable({ providedIn: 'root' })
export class AudioApiService {
  async health(): Promise<{ status: string; demo_ready: boolean } | null> {
    try {
      const r = await fetch(`${AUDIO_API_BASE}/health`);
      return r.ok ? await r.json() : null;
    } catch {
      return null;
    }
  }

  /** Uploads the ORIGINAL file; the service decodes it with ffmpeg (same decoder for both engines). */
  async audit(file: Blob, name = 'recording', engine: AuditEngine = 'standard'): Promise<AuditResult> {
    const fd = new FormData();
    fd.append('file', file, name);
    return this.send(fetch(`${AUDIO_API_BASE}/audit?engine=${engine}`, { method: 'POST', body: fd }));
  }

  demo(scenario: DemoScenario): Promise<DemoResult> {
    return this.send(fetch(`${AUDIO_API_BASE}/demo?scenario=${scenario}`));
  }

  recordingUrl(scenario: DemoScenario): string {
    return `${AUDIO_API_BASE}/demo/${scenario}/recording.wav`;
  }

  private async send<T>(req: Promise<Response>): Promise<T> {
    let res: Response;
    try {
      res = await req;
    } catch {
      throw new Error('Serviciul audio nu răspunde. Porniți-l pe portul 8002.');
    }
    if (!res.ok) {
      let msg = `Eroare ${res.status}`;
      try {
        const j = await res.json();
        if (typeof j?.detail === 'string') msg = j.detail;
      } catch {
        /* non-JSON */
      }
      throw new Error(msg);
    }
    return res.json() as Promise<T>;
  }
}
