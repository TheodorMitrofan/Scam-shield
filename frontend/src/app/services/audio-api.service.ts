import { Injectable } from '@angular/core';
import { AUDIO_API_BASE } from '../api.config';

export type AuditRisk = 'high' | 'medium' | 'low' | 'undetermined';

export interface AuditResult {
  duration_s: number;
  risk: AuditRisk;
  flyovers: number;
  events: { t0: number; t1: number; fmin: number; fmax: number; trend: string; drop_pct: number }[];
  status: string;
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

export interface DemoResult {
  ok: boolean;
  reason?: string;
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

/** Client for the separate audio service (port 8001). Not part of the scam detector. */
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

  async audit(wav: Blob, name = 'recording.wav'): Promise<AuditResult> {
    const fd = new FormData();
    fd.append('file', wav, name.replace(/\.[^.]+$/, '') + '.wav');
    return this.send(fetch(`${AUDIO_API_BASE}/audit`, { method: 'POST', body: fd }));
  }

  demo(seed?: number): Promise<DemoResult> {
    return this.send(fetch(`${AUDIO_API_BASE}/demo${seed ? `?seed=${seed}` : ''}`));
  }

  private async send<T>(req: Promise<Response>): Promise<T> {
    let res: Response;
    try {
      res = await req;
    } catch {
      throw new Error('Serviciul audio nu răspunde. Porniți-l pe portul 8001.');
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
