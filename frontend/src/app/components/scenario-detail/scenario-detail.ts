import { Component, computed, inject, output, signal } from '@angular/core';
import { ButtonModule } from 'primeng/button';
import { TagModule } from 'primeng/tag';
import { TooltipModule } from 'primeng/tooltip';
import { REPORT_MIN_SCORE } from '../../models/report';
import { CHANNEL_LABEL } from '../../models/scenario';
import {
  VERDICT_LABEL,
  flagLabel,
  scamTypeLabel,
  senderOf,
  tagOf,
} from '../../services/result-utils';
import { ScenarioStore } from '../../services/scenario-store';
import { Conversation } from '../conversation/conversation';
import { ReportDialog } from '../report-dialog/report-dialog';

/** Right panel: header with position + actions, then the scenario rendered like its original app. */
@Component({
  selector: 'app-scenario-detail',
  imports: [ButtonModule, TagModule, TooltipModule, Conversation, ReportDialog],
  templateUrl: './scenario-detail.html',
  styleUrl: './scenario-detail.scss',
})
export class ScenarioDetail {
  protected readonly store = inject(ScenarioStore);
  /** Mobile only: go back to the list. */
  readonly back = output<void>();

  protected readonly channelLabel = CHANNEL_LABEL;
  protected readonly verdictLabel = VERDICT_LABEL;
  protected readonly flagLabel = flagLabel;
  protected readonly scamTypeLabel = scamTypeLabel;
  protected readonly reportMinScore = REPORT_MIN_SCORE;
  /** „Raportează frauda” dialog (only offered when risk ≥ 50). */
  protected readonly reportOpen = signal(false);
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
