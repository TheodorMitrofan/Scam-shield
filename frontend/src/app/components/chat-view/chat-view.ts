import { Component, computed, inject, input, signal } from '@angular/core';
import { AnalysisResult, CHANNEL_LABEL, Scenario } from '../../models/scenario';
import { evidenceSegments, flagsAt, isFirstAlert } from '../../services/result-utils';
import { UiLang } from '../../services/ui-lang';

/** Renders sms / whatsapp / chat scenarios as a phone messaging app. */
@Component({
  selector: 'app-chat-view',
  templateUrl: './chat-view.html',
  styleUrl: './chat-view.scss',
})
export class ChatView {
  readonly scenario = input.required<Scenario>();
  readonly result = input<AnalysisResult | null>(null);

  protected readonly label = computed(() => CHANNEL_LABEL[this.scenario().channel]);
  protected readonly title = computed(
    () => this.scenario().sender.name ?? this.scenario().sender.address ?? 'Necunoscut',
  );
  protected readonly subtitle = computed(() => {
    const s = this.scenario().sender;
    return s.name && s.address && s.address !== s.name ? s.address : null;
  });
  /** First letter of the sender's name; a generic person icon for bare numbers like "+40 7xx…". */
  protected readonly initial = computed(
    () => this.scenario().sender.name?.match(/\p{L}/u)?.[0]?.toUpperCase() ?? '👤',
  );

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
