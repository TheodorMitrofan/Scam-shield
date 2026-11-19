import { Component, inject, output } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ButtonModule } from 'primeng/button';
import { CheckboxModule } from 'primeng/checkbox';
import { IconFieldModule } from 'primeng/iconfield';
import { InputIconModule } from 'primeng/inputicon';
import { InputTextModule } from 'primeng/inputtext';
import { SelectModule } from 'primeng/select';
import { SelectButtonModule } from 'primeng/selectbutton';
import { TagModule } from 'primeng/tag';
import { TooltipModule } from 'primeng/tooltip';
import { CHANNELS, CHANNEL_LABEL, Scenario } from '../../models/scenario';
import { senderOf, tagOf } from '../../services/result-utils';
import { ChannelFilter, ScenarioStore, VerdictFilter } from '../../services/scenario-store';

/** Left column: search + filters, bulk actions and the grouped scenario cards. */
@Component({
  selector: 'app-inbox-list',
  imports: [
    FormsModule,
    ButtonModule,
    CheckboxModule,
    IconFieldModule,
    InputIconModule,
    InputTextModule,
    SelectModule,
    SelectButtonModule,
    TagModule,
    TooltipModule,
  ],
  templateUrl: './inbox-list.html',
  styleUrl: './inbox-list.scss',
})
export class InboxList {
  protected readonly store = inject(ScenarioStore);
  /** Emitted when a card is opened (used on mobile to switch to the detail view). */
  readonly opened = output<string>();

  protected readonly channelOptions: { label: string; value: ChannelFilter }[] = [
    { label: 'Toate canalele', value: 'all' },
    ...CHANNELS.map((c) => ({ label: CHANNEL_LABEL[c], value: c })),
  ];
  protected readonly verdictOptions: { label: string; value: VerdictFilter }[] = [
    { label: 'Toate', value: 'all' },
    { label: 'Țeapă', value: 'SCAM' },
    { label: 'Suspect', value: 'SUSPICIOUS' },
    { label: 'Sigur', value: 'SAFE' },
  ];

  protected readonly senderOf = senderOf;

  protected tag(s: Scenario) {
    return tagOf(s, this.store.results()[s.id]);
  }

  protected preview(s: Scenario): string {
    const first = s.messages.find((m) => m.from === 'sender') ?? s.messages[0];
    return first?.text.trim() || '(fără text)';
  }

  protected open(id: string): void {
    this.store.select(id);
    this.opened.emit(id);
  }

  protected markCheckedRead(): void {
    this.store.markRead(this.store.checkedIds());
  }

  protected removeChecked(): void {
    this.store.remove(this.store.checkedIds());
  }
}
