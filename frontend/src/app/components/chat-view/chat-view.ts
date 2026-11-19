import { Component, computed, input } from '@angular/core';
import { AnalysisResult, CHANNEL_LABEL, Scenario } from '../../models/scenario';
import { flagsAt, isFirstAlert } from '../../services/result-utils';

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
  protected readonly initial = computed(
    () => this.title().match(/\p{L}/u)?.[0]?.toUpperCase() ?? '👤',
  );

  protected readonly flagsAt = flagsAt;
  protected readonly isFirstAlert = isFirstAlert;
}
