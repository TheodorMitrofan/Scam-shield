import { Component, computed, inject, input, signal } from '@angular/core';
import { AnalysisResult, Scenario } from '../../models/scenario';
import { evidenceSegments, flagsAt, isFirstAlert } from '../../services/result-utils';
import { UiLang } from '../../services/ui-lang';

/** Renders an `email` scenario like a mail client; each message is one e-mail in the thread. */
@Component({
  selector: 'app-email-view',
  templateUrl: './email-view.html',
  styleUrl: './email-view.scss',
})
export class EmailView {
  readonly scenario = input.required<Scenario>();
  readonly result = input<AnalysisResult | null>(null);

  /** The JSON format has no subject, so we show the first words of the first e-mail. */
  protected readonly subject = computed(() => {
    const t = (this.scenario().messages[0]?.text ?? '').trim();
    const first = t.split(/(?<=[.!?])\s/)[0] ?? '';
    return first.length > 70 ? first.slice(0, 67) + '…' : first || '(fără subiect)';
  });
  protected readonly senderName = computed(
    () => this.scenario().sender.name ?? this.scenario().sender.address ?? 'Necunoscut',
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
