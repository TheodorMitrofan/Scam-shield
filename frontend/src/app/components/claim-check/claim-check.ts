import { Component, OnInit, inject, signal } from '@angular/core';
import { ButtonModule } from 'primeng/button';
import { TagModule } from 'primeng/tag';
import { AUDIO_API_BASE } from '../../api.config';
import { AnalysisResult, Scenario } from '../../models/scenario';
import { ApiService } from '../../services/api.service';
import { VERDICT_LABEL } from '../../services/result-utils';

interface AreaCheck {
  label: string;
  match: boolean;
  best_score: number | null;
}

export interface ClaimResult {
  ok: boolean;
  reason?: string;
  simulated: boolean;
  transcript: string;
  transcript_parts?: string[];
  message_time_utc: string;
  duration_s: number;
  claimed: AreaCheck & { key: string };
  actual: AreaCheck;
  event: { t_cpa_s: number; speed_kmh: number; distance_m: number };
  spectrogram: string;
}

/**
 * „Nepotul e în Spania?” — a (simulated) voice message from a fake grandson who says he is in Madrid.
 * 1) the normal scam check on the transcript (main detector), 2) the audio service compares the aircraft
 * heard behind the voice with the air traffic at the claimed place, at the known message time.
 * City-level answer only — we never show where the other person is exactly.
 */
@Component({
  selector: 'app-claim-check',
  imports: [ButtonModule, TagModule],
  templateUrl: './claim-check.html',
  styleUrl: './claim-check.scss',
})
export class ClaimCheck implements OnInit {
  private readonly api = inject(ApiService);

  protected readonly recordingUrl = `${AUDIO_API_BASE}/claim/recording.wav`;
  protected readonly verdictLabel = VERDICT_LABEL;
  protected readonly loading = signal(true);
  protected readonly error = signal<string | null>(null);
  protected readonly claim = signal<ClaimResult | null>(null);
  protected readonly scam = signal<AnalysisResult | null>(null);
  protected readonly showDetails = signal(false);

  ngOnInit(): void {
    void this.load();
  }

  protected async load(): Promise<void> {
    this.loading.set(true);
    this.error.set(null);
    try {
      const r = await fetch(`${AUDIO_API_BASE}/claim`);
      if (!r.ok) throw new Error(String(r.status));
      const c = (await r.json()) as ClaimResult;
      this.claim.set(c);
      if (c.ok) {
        // Same scam detector as everywhere else, on the transcript of the voice message.
        const parts = c.transcript_parts?.length ? c.transcript_parts : [c.transcript];
        const scenario: Scenario = {
          id: 'VOCE',
          channel: 'whatsapp',
          sender: { name: null, address: '+40 7xx xxx 451', known_contact: false },
          messages: parts.map((text, i) => ({ n: i + 1, from: 'sender', text })),
        };
        try {
          this.scam.set((await this.api.analyze(scenario, false)).result);
        } catch {
          this.scam.set(null); // detector offline: the place check still stands on its own
        }
      }
    } catch {
      this.error.set('Serviciul audio nu răspunde. Porniți-l pe portul 8002.');
    } finally {
      this.loading.set(false);
    }
  }

  protected time(iso: string): string {
    return new Date(iso).toLocaleTimeString('ro-RO', { hour: '2-digit', minute: '2-digit' });
  }

}
