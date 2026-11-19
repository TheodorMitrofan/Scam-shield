import { Component, computed, inject, input, signal } from '@angular/core';
import { API_BASE } from '../../api.config';
import { AnalysisResult, Scenario } from '../../models/scenario';
import { evidenceSegments, flagsAt, isFirstAlert } from '../../services/result-utils';
import { UiLang } from '../../services/ui-lang';
import { UiPipe } from '../../services/ui.pipe';

/**
 * Renders `call_transcript` scenarios as a phone call with live captions.
 * Stage 4: when `scenario.audio` is set (uploaded .wav/.mp4), the same view shows a voice-message
 * player above the transcript, and per-message timestamps (start_s) when available.
 */
@Component({
  selector: 'app-call-view',
  imports: [UiPipe],
  templateUrl: './call-view.html',
  styleUrl: './call-view.scss',
})
export class CallView {
  readonly scenario = input.required<Scenario>();
  readonly result = input<AnalysisResult | null>(null);

  protected readonly caller = computed(
    () => this.scenario().sender.name ?? this.scenario().sender.address ?? 'Număr ascuns',
  );
  protected readonly audioSrc = computed(() => {
    const a = this.scenario().audio;
    return a ? `${API_BASE}/audio/${encodeURIComponent(a.audio_id)}` : null;
  });

  protected fmt(sec: number | undefined): string {
    if (sec == null) return '';
    const s = Math.max(0, Math.floor(sec));
    return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
  }

  protected readonly flagsAt = flagsAt;
  private readonly lang = inject(UiLang);
  /** Flag explanation in the chosen language (RO/EN toggle). */
  protected readonly flagLabel = (code: string) => this.lang.flag(code);
  /** Message text split into ordinary and dangerous pieces (detector evidence spans). */
  /** The dangerous word the user tapped: its explanation is shown under that message. */
  protected readonly explained = signal<{ n: number; flag: string } | null>(null);
  protected explain(n: number, flag: string): void {
    const e = this.explained();
    this.explained.set(e && e.n === n && e.flag === flag ? null : { n, flag });
  }
  protected segments(n: number, text: string) {
    return evidenceSegments(this.result(), n, text);
  }
  protected readonly isFirstAlert = isFirstAlert;
}
