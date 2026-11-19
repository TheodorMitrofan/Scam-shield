import { Component, computed, input } from '@angular/core';
import { AnalysisResult, Scenario } from '../../models/scenario';
import { flagLabel, flagsAt, isFirstAlert } from '../../services/result-utils';

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
  protected readonly flagLabel = flagLabel;
  protected readonly isFirstAlert = isFirstAlert;
}
