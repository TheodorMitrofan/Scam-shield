import { Component, computed, input } from '@angular/core';
import { AnalysisResult, CHANNEL_LABEL, Scenario } from '../../models/scenario';
import { flagLabel, flagsAt, isFirstAlert } from '../../services/result-utils';

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
  protected readonly flagLabel = flagLabel;
  protected readonly isFirstAlert = isFirstAlert;
}
