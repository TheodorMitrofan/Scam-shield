import { Component, computed, inject, output } from '@angular/core';
import { ButtonModule } from 'primeng/button';
import { TagModule } from 'primeng/tag';
import { TooltipModule } from 'primeng/tooltip';
import { CHANNEL_LABEL } from '../../models/scenario';
import { senderOf, tagOf } from '../../services/result-utils';
import { ScenarioStore } from '../../services/scenario-store';
import { Conversation } from '../conversation/conversation';

/** Right panel: header with position + actions, then the scenario rendered like its original app. */
@Component({
  selector: 'app-scenario-detail',
  imports: [ButtonModule, TagModule, TooltipModule, Conversation],
  templateUrl: './scenario-detail.html',
  styleUrl: './scenario-detail.scss',
})
export class ScenarioDetail {
  protected readonly store = inject(ScenarioStore);
  /** Mobile only: go back to the list. */
  readonly back = output<void>();

  protected readonly channelLabel = CHANNEL_LABEL;
  protected readonly tag = computed(() => {
    const s = this.store.selected();
    return s ? tagOf(s, this.store.selectedResult()) : null;
  });
  protected readonly sender = computed(() => {
    const s = this.store.selected();
    return s ? senderOf(s) : '';
  });

  protected markUnread(): void {
    const id = this.store.selectedId();
    if (id) this.store.markUnread(id);
  }

  protected remove(): void {
    const id = this.store.selectedId();
    if (id) this.store.remove([id]);
    this.back.emit();
  }
}
