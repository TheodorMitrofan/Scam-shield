import { Component, computed, input } from '@angular/core';
import { AnalysisResult, Scenario, viewKindOf } from '../../models/scenario';
import { CallView } from '../call-view/call-view';
import { ChatView } from '../chat-view/chat-view';
import { EmailView } from '../email-view/email-view';

/** Picks the right renderer for a scenario's channel. Add new channel kinds here only. */
@Component({
  selector: 'app-conversation',
  imports: [ChatView, EmailView, CallView],
  template: `
    @switch (kind()) {
      @case ('email') {
        <app-email-view [scenario]="scenario()" [result]="result()" />
      }
      @case ('call') {
        <app-call-view [scenario]="scenario()" [result]="result()" />
      }
      @default {
        <app-chat-view [scenario]="scenario()" [result]="result()" />
      }
    }
  `,
})
export class Conversation {
  readonly scenario = input.required<Scenario>();
  readonly result = input<AnalysisResult | null>(null);

  protected readonly kind = computed(() =>
    // Audio scenarios (stage 4) always render as a call / voice message.
    this.scenario().audio ? 'call' : viewKindOf(this.scenario().channel),
  );
}
